from functools import lru_cache, partial

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _, ngettext

from finder.models.ambit import AmbitModel
from finder.models.inode import DiscardedInode, InodeManager, InodeManagerMixin, InodeModel
from finder.models.permission import DefaultAccessControlEntry as DefaultACE, Privilege

ROOT_FOLDER_NAME = '__root__'
TRASH_FOLDER_NAME = '__trash__'


class FolderModelManager(InodeManagerMixin, models.Manager):
    def get_trash_folder(self, ambit, owner):
        try:
            trash_folder = ambit.trash_folders.get(owner=owner)
        except FolderModel.DoesNotExist:
            trash_folder = self.create(parent=None, owner=owner, name=TRASH_FOLDER_NAME)
            ambit.trash_folders.add(trash_folder)
        return trash_folder


class FolderModel(InodeModel):
    is_folder = True
    folderitem_component = None

    class Meta:
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")
        default_permissions = []
        constraints = [models.UniqueConstraint(fields=['parent', 'name'], name='unique_subfolder')]

    objects = FolderModelManager()

    def __str__(self):
        if self.is_root:
            return gettext("Root")
        if self.is_trash:
            return gettext("Trash")
        return self.name

    @lru_cache
    def get_ambit(self):
        if self.is_trash:
            return AmbitModel.objects.get(trash_folders=self)
        return self.get_root_folder().ambit

    @lru_cache
    def get_root_folder(self):
        if self.is_root:
            return self
        if isinstance(self.ancestors, models.QuerySet):
            count = self.ancestors.count()
            return self.ancestors[count - 1]
        return list(self.ancestors)[-1]

    @property
    def folder(self):
        return self

    @property
    def subfolders(self):
        return FolderModel.objects.filter(parent=self)

    @property
    def num_children(self):
        num_children = sum(
            inode_model.objects.filter(parent=self).count()
            for inode_model in InodeModel.get_models(include_folder=True)
        )
        return num_children

    @cached_property
    def ancestors(self):
        """
        Returns a queryset of all ancestor folders including the current folder.
        """
        def make_ascendant_cte(cte):
            return self.__class__.objects.filter(
                id=self.id,
            ).values('id', 'parent_id').union(
                cte.join(
                    self.__class__,
                    id=cte.col.parent_id
                ).values('id', 'parent_id'),
                all=True,
            )

        try:
            from django_cte import CTE, with_cte
        except ImportError:
            # traversing the tree folder by folder (slow)
            folder, ancestors = self, []
            while folder:
                ancestors.append(folder)
                folder = folder.parent
            return ancestors
        else:
            # traversing the tree using a recursive CTE (fast)
            ascendant_cte = CTE.recursive(make_ascendant_cte)
            return with_cte(
                ascendant_cte,
                select=ascendant_cte.join(self.__class__, id=ascendant_cte.col.id),
            )

    @cached_property
    def descendants(self):
        """
        Returns an iterable of all descendant folders including the current folder.
        If django-cte is installed return a CTE queryset. Otherwise, return a generator containing the descendant
        folders of the current folder.
        """
        def traverse(parent):
            yield parent
            for inode in parent.subfolders:
                if inode.is_folder:
                    yield from traverse(inode)

        def make_descendant_cte(cte):
            return self.__class__.objects.filter(
                id=self.id,
            ).values('id').union(
                cte.join(
                    self.__class__,
                    parent_id=cte.col.id
                ).values('id'),
                all=True,
            )

        try:
            from django_cte import CTE, with_cte
        except ImportError:
            # traversing the tree folder by folder (slow)
            return traverse(self)
        else:
            # traversing the tree using a recursive CTE (fast)
            descendant_cte = CTE.recursive(make_descendant_cte)
            return with_cte(
                descendant_cte,
                select=descendant_cte.join(self.__class__, id=descendant_cte.col.id)
            )

    @property
    def is_root(self):
        return self.parent is None and self.name == ROOT_FOLDER_NAME

    @property
    def is_trash(self):
        return self.parent is None and self.name == TRASH_FOLDER_NAME

    @cached_property
    def summary(self):
        num_inodes = self.num_children
        num_folders = self._meta.model.objects.filter(parent_id=self.id).count()
        num_files = num_inodes - num_folders
        return ", ".join((
            ngettext("{} Folder", "{} Folders", num_folders).format(num_folders),
            ngettext("{} File", "{} Files", num_files).format(num_files),
        ))

    @lru_cache
    def as_dict(self, ambit):
        return {
            **super().as_dict(ambit),
            'is_folder': True,
            'has_subfolders': self.subfolders.exists(),
        }

    def has_permission(self, user, privilege):
        if self.is_trash and self.owner == user:
            return True
        return super().has_permission(user, privilege)

    def get_download_url(self, ambit):
        return None

    def get_thumbnail_url(self, ambit):
        return staticfiles_storage.url('finder/icons/folder.svg')

    def get_sample_url(self, ambit):
        return None

    def listdir(self, **lookup):
        """
        List all inodes belonging to this folder.
        """
        return self._meta.model.objects.filter_unified(parent=self, **lookup)

    def move_inodes(self, user, inode_ids):
        """
        Move all Inodes with the given IDs to the end of the current folder.
        """
        def storage_transfer(entry, source_ambit):
            if entry['is_folder']:
                for child_entry in FolderModel.objects.get(id=entry['id']).listdir():
                    storage_transfer(child_entry, source_ambit)
                if target_ambit.id != source_ambit.id:
                    # delete pinned folder entry for the moved folder if it is moved to a different ambit
                    PinnedFolder.objects.exclude(ambit=target_ambit).filter(folder_id=entry['id']).delete()
            elif target_ambit.original_storage.deconstruct() != source_ambit.original_storage.deconstruct():
                # move payload from source_ambit to target_ambit and delete from source_ambit
                file_path = '{id}/{file_name}'.format(**entry)
                if source_ambit.original_storage.exists(file_path):
                    with source_ambit.original_storage.open(file_path, 'rb') as readhandle:
                        target_ambit.original_storage.save(file_path, readhandle)
                    source_ambit.original_storage.delete(file_path)

        if not self.has_permission(user, Privilege.WRITE):
            msg = gettext("You do not have permission to move these items to folder “{folder}”.")
            raise PermissionDenied(msg.format(folder=self.name))

        update_inodes, parent_ids = [], set()
        target_ambit = self.get_ambit()
        entries = FolderModel.objects.filter_unified(
            id__in=inode_ids,
            user=user,
            has_read_permission=True,
            has_write_permission=True,
        )
        default_access_control_list = [ace.as_dict for ace in self.default_access_control_list.all()]
        for ordering, entry in enumerate(entries, self.get_max_ordering() + 1):
            parent_ids.add(entry['parent'])
            try:
                DiscardedInode.objects.get(inode=entry['id']).delete()
            except DiscardedInode.DoesNotExist:
                pass
            proxy_obj = InodeManager.get_proxy_object(entry)
            proxy_obj.parent = self
            proxy_obj.ordering = ordering
            proxy_obj.validate_constraints()
            update_inodes.append(proxy_obj)

        parent_folder_qs = FolderModel.objects.filter(id__in=parent_ids)
        parent_ambits = {folder.id: folder.get_ambit() for folder in parent_folder_qs}

        with transaction.atomic():
            update_fields = ['parent', 'ordering']
            for model in InodeModel.get_models(include_folder=True):
                model.objects.bulk_update(filter(lambda obj: isinstance(obj, model), update_inodes), update_fields)
            for inode in update_inodes:
                inode.update_access_control_list(default_access_control_list)
                entry = next(filter(lambda e: e['id'] == inode.id, entries))
                transaction.on_commit(partial(storage_transfer, entry, parent_ambits[entry['parent']]))

            for folder in parent_folder_qs:
                folder.reorder()

    def copy_to(self, source_ambit, user, folder, skip_permission_check=False, **kwargs):
        """
        Copies the folder to a destination folder and returns it.
        """
        if not skip_permission_check and not folder.has_permission(user, Privilege.WRITE):
            msg = gettext("You do not have permission to copy folder “{source}” to folder “{target}”.")
            raise PermissionDenied(msg.format(source=self.name, target=folder.name))

        for ancestor in folder.ancestors:
            if ancestor.id == self.id:
                msg = gettext(
                    "Folder named “{source}” can not become the descendant of destination folder “{target}”."
                )
                raise RecursionError(msg.format(source=self.name, target=folder.name))

        kwargs.setdefault('name', self.name)
        kwargs.update(parent=folder, owner=user)
        obj = self._meta.model.objects.create(**kwargs)
        for inode in self.listdir():
            inode.copy_to(source_ambit, user, obj, skip_permission_check=True, owner=obj.owner)
        return obj

    def validate_constraints(self):
        super().validate_constraints()
        parent = self.parent
        while parent is not None:
            if parent.id == self.id:
                msg = gettext("A parent folder can not become the descendant of a destination folder.")
                raise ValidationError(msg)
            parent = parent.parent
        if self.parent.listdir(name=self.name).exists():
            msg = gettext("Folder named “{name}” already exists in destination folder.")
            raise ValidationError(msg.format(name=self.name))
        if self.name in [ROOT_FOLDER_NAME, TRASH_FOLDER_NAME]:
            msg = gettext("Folder name “{name}” is reserved.")
            raise ValidationError(msg.format(name=self.name))

    def reorder(self, target_id=None, inode_ids=[], insert_after=True):
        """
        Set `ordering` index based on their natural ordering index.
        """

        def insert(new_order):
            inodes_order.update({id: nord for nord, id in enumerate(inode_ids, new_order)})
            return new_order + len(inode_ids)

        inodes_order, new_order = {}, 1
        target_id = str(target_id) if target_id else None
        for inode in self.listdir().order_by('ordering'):
            inode_id = str(inode['id'])
            if not insert_after and inode_id == target_id:
                new_order = insert(new_order)
            if inode_id not in inode_ids:
                inodes_order[inode_id] = new_order
                new_order += 1
            if insert_after and inode_id == target_id:
                new_order = insert(new_order)

        default_access_control_list = [ace.as_dict for ace in self.default_access_control_list.all()]
        update_inodes, former_parents = [], set()
        update_fields = ['parent', 'ordering']
        for model in InodeModel.get_models(include_folder=True):
            for inode in model.objects.filter(pk__in=inodes_order.keys()):
                ordering = inodes_order[str(inode.id)]
                if inode.parent != self:
                    former_parents.add(inode.parent)
                    inode.parent = self
                    inode.update_access_control_list(default_access_control_list)
                    update_inodes.append(inode)
                if inode.ordering != ordering:
                    inode.ordering = ordering
                    update_inodes.append(inode)
            model.objects.bulk_update(filter(lambda obj: isinstance(obj, model), update_inodes), update_fields)

        for folder in former_parents:
            folder.reorder()

    def get_max_ordering(self):
        """
        Get the maximum ordering index of all inodes in this folder.
        """
        queryset = self.subfolders.values_list('ordering', flat=True).union(*[
            model.objects.filter(parent=self).values_list('ordering', flat=True) for model in InodeModel.get_models()
        ])
        return max(queryset) if queryset.exists() else 0

    def retrieve(self, path):
        """
        Retrieve an inode specified by the given path object.
        """
        if isinstance(path, str):
            path = path.split('/')
        for part in path:
            if entry := self.listdir(name=part).first():
                proxy_obj = InodeManagerMixin.get_proxy_object(entry)
                return proxy_obj.retrieve(path[1:])
            return None
        else:
            return self

    def update_default_access_control_list(self, next_acl):
        default_acl_qs = self.default_access_control_list.all()
        entry_ids, update_entries, create_entries = [], [], []
        for ace in next_acl:
            if entry := next(filter(lambda entry: entry == ace, default_acl_qs), None):
                if entry.privilege != ace['privilege']:
                    entry.privilege = ace['privilege']
                    update_entries.append(entry)
                else:
                    entry_ids.append(entry.id)
            else:
                create_kwargs = {'folder': self, 'privilege': ace['privilege']}
                if ace['type'] == 'everyone':
                    pass  # user and group are already None
                elif ace['type'] == 'group':
                    create_kwargs['group_id'] = ace['principal']
                elif ace['type'] == 'user':
                    create_kwargs['user_id'] = ace['principal']
                else:
                    raise ValueError(f"Unknown access control type {ace['type']}")
                create_entries.append(default_acl_qs.model(**create_kwargs))
        DefaultACE.objects.bulk_update(update_entries, ['privilege'])
        DefaultACE.objects.bulk_create(create_entries)
        entry_ids.extend([*(entry.id for entry in update_entries), *(entry.id for entry in create_entries)])
        default_acl_qs.exclude(id__in=entry_ids).delete()

    def transfer_access_control_list(self, parent_folder):
        super().transfer_access_control_list(parent_folder)
        DefaultACE.objects.bulk_create([
            DefaultACE(folder=self, user=a.user, group=a.group, privilege=a.privilege)
            for a in parent_folder.default_access_control_list.all()
        ])


class PinnedFolder(models.Model):
    ambit = models.ForeignKey(
        AmbitModel,
        related_name='+',
        on_delete=models.CASCADE,
        editable=False,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='+',
        on_delete=models.CASCADE,
        editable=False,
    )
    folder = models.ForeignKey(
        FolderModel,
        related_name='pinned_folders',
        on_delete=models.CASCADE,
        editable=False,
    )
    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("Pinned Folder")
        verbose_name_plural = _("Pinned Folders")
        constraints = [
            models.UniqueConstraint(fields=['owner', 'folder'], name='unique_pinned_folder')
        ]

    def __repr__(self):
        return f'<PinnedFolder(owner={self.owner}, folder="{self.folder}")>'
