from functools import lru_cache

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _, ngettext


try:
    from django_cte import CTEManager as ModelManager
except ImportError:
    ModelManager = models.Manager

from .inode import InodeManagerMixin, InodeModel
from.realm import RealmModel


class FolderModelManager(InodeManagerMixin, ModelManager):
    def get_root_folder(self, realm):
        try:
            return realm.root_folder
        except FolderModel.DoesNotExist:
            realm.root_folder = self.create(parent=None, name='__root__')
            return realm.root_folder

    def get_trash_folder(self, realm, owner):
        try:
            trash_folder = realm.trash_folders.get(owner=owner)
        except FolderModel.DoesNotExist:
            trash_folder = self.create(parent=None, owner=owner, name='__trash__')
            realm.trash_folders.add(trash_folder)
        return trash_folder


class FolderModel(InodeModel):
    is_folder = True
    folderitem_component = None

    class Meta:
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")
        default_permissions = ['read', 'write']
        constraints = [models.UniqueConstraint(fields=['parent', 'name'], name='unique_realm')]

    objects = FolderModelManager()

    def __str__(self):
        if self.is_root:
            return gettext("Root")
        if self.is_trash:
            return gettext("Trash")
        return self.name

    @property
    def cast(self):
        raise NotImplementedError
        return self

    @lru_cache
    def get_realm(self):
        if isinstance(self.ancestors, models.QuerySet):
            return self.ancestors.last().realm
        return list(self.ancestors)[-1].realm

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
            from django_cte import With
        except ImportError:
            # traversing the tree folder by folder (slow)
            folder, ancestors = self, []
            while folder:
                ancestors.append(folder)
                folder = folder.parent
            return ancestors
        else:
            # traversing the tree using a recursive CTE (fast)
            ascendant_cte = With.recursive(make_ascendant_cte)
            ancestor_qs = ascendant_cte.join(
                self.__class__, id=ascendant_cte.col.id
            ).with_cte(ascendant_cte)
            return ancestor_qs

    @cached_property
    def descendants(self):
        """
        Returns an iterable of all descendant folders including the current folder.
        If django-cte is installed return a CTE queryset. Otherwise, return a generator containing the descendant
        folders of the current folder.
        """
        def traverse(parent):
            yield parent
            for inode in FolderModel.objects.filter(parent=parent):
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
            from django_cte import With
        except ImportError:
            # traversing the tree folder by folder (slow)
            return traverse(self)
        else:
            # traversing the tree using a recursive CTE (fast)
            descendant_cte = With.recursive(make_descendant_cte)
            return descendant_cte.join(
                self.__class__, id=descendant_cte.col.id
            ).with_cte(descendant_cte)

    @property
    def is_root(self):
        return self.parent is None and self.name == '__root__'

    @property
    def is_trash(self):
        return self.parent is None and self.name == '__trash__'

    @cached_property
    def summary(self):
        num_inodes = self.num_children
        num_folders = self._meta.model.objects.filter(parent_id=self.id).count()
        num_files = num_inodes - num_folders
        return ", ".join((
            ngettext("{} Folder", "{} Folders", num_folders).format(num_folders),
            ngettext("{} File", "{} Files", num_files).format(num_files),
        ))

    def get_download_url(self):
        return None

    def get_thumbnail_url(self):
        return staticfiles_storage.url('filer/icons/folder.svg')

    def listdir(self, **lookup):
        """
        List all inodes belonging to this folder.
        """
        return self._meta.model.objects.filter_unified(parent=self, **lookup)

    def copy_to(self, folder, **kwargs):
        """
        Copies the folder to a destination folder and returns it.
        """
        for ancestor in folder.ancestors:
            if ancestor.id == self.id:
                msg = "Folder named “{source}” can not become the descendant of destination folder “{target}”."
                raise RecursionError(gettext(msg).format(source=self.name, target=folder.name))

        kwargs.setdefault('name', self.name)
        kwargs.setdefault('owner', self.owner)
        kwargs.update(parent=folder)
        obj = self._meta.model.objects.create(**kwargs)
        for inode in self.listdir():
            inode.copy_to(obj, owner=obj.owner)
        return obj

    def validate_constraints(self):
        super().validate_constraints()
        parent = self.parent
        while parent is not None:
            if parent.id == self.id:
                msg = gettext("A parent folder can not become the descendant of a destination folder.")
                raise ValidationError(msg)
            parent = parent.parent
        if next(self.parent.listdir(name=self.name), None):
            msg = gettext("Folder named “{name}” already exists in destination folder.")
            raise ValidationError(msg.format(name=self.name))
        if self.name in ['__root__', '__trash__']:
            msg = gettext("Folder name “{name}” is reserved.")
            raise ValidationError(msg.format(name=self.name))

    def retrieve(self, path):
        """
        Retrieve an inode specified by the given path object.
        """
        if isinstance(path, str):
            path = path.split('/')
        for part in path:
            if entry := self.listdir(name=part).first():
                proxy_obj = InodeModel.objects.get_proxy_object(entry)
                return proxy_obj.retrieve(path[1:])
            return None
        else:
            return self


class PinnedFolder(models.Model):
    realm = models.ForeignKey(
        RealmModel,
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
