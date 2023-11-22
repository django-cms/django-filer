from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

try:
    from django_cte import CTEManager as ModelManager
except ImportError:
    ModelManager = models.Manager

from .inode import InodeManagerMixin, InodeModel


class FolderModelManager(InodeManagerMixin, ModelManager):
    def get_root_folder(self, current_site):
        root_folder, _ = self.get_or_create(parent=None, site=current_site, name='__root__')
        return root_folder

    def get_trash_folder(self, current_site, owner):
        trash_folder, _ = self.get_or_create(parent=None, site=current_site, owner=owner, name='__trash__')
        return trash_folder


class FolderModel(InodeModel):
    is_folder = True

    site = models.CharField(
        _("Site"),
        default='admin',
        editable=False,
        max_length=200,
    )

    class Meta:
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")
        default_permissions = ['read', 'write']
        unique_together = [('parent', 'name')]

    objects = FolderModelManager()

    def __str__(self):
        if self.is_root:
            return gettext("Root")
        if self.is_trash:
            return gettext("Trash")
        return self.name

    @property
    def folder(self):
        return self

    @property
    def num_children(self):
        num_children = sum(inode_model.objects.filter(parent=self).count() for inode_model in InodeModel.all_models)
        return num_children

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
        return gettext("{num_folders} Folders, {num_files} Files".format(num_folders=num_folders, num_files=num_files))

    def get_download_url(self):
        return None

    def get_thumbnail_url(self):
        return staticfiles_storage.url('filer/icons/folder.svg')

    def listdir(self, **lookup):
        return self._meta.model.objects.filter_inodes(parent=self, **lookup)

    def copy_to(self, folder, **kwargs):
        """
        Copies the folder to a destination folder and returns it.
        """
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


class PinnedFolder(models.Model):
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
