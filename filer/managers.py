from __future__ import absolute_import, unicode_literals

from django.db import models
from django.db.models import Q
from mptt.managers import TreeManager

from . import settings as filer_settings

try:
    from polymorphic.managers import PolymorphicManager
except ImportError:
    # django-polymorphic < 0.8
    from polymorphic import PolymorphicManager


class FolderManager(TreeManager):
    def virtual_folders(self):
        return []

    def root_folder(self):
        return []

    def children_for(self, folder):
        pass


class FolderPermissionManager(models.Manager):
    """
    Theses methods are called by introspection from "has_generic_permisison" on
    the folder model.
    """
    def get_read_id_list(self, user):
        """
        Give a list of a Folders where the user has read rights or the string
        "All" if the user has all rights.
        """
        return self.__get_id_list(user, "can_read")

    def get_edit_id_list(self, user):
        return self.__get_id_list(user, "can_edit")

    def get_add_children_id_list(self, user):
        return self.__get_id_list(user, "can_add_children")

    def __get_id_list(self, user, attr):
        from .models.foldermodels import Folder

        if user.is_superuser or not filer_settings.FILER_ENABLE_PERMISSIONS:
            return 'All'
        allow_list = set()
        deny_list = set()
        group_ids = user.groups.all().values_list('id', flat=True)
        q = Q(user=user) | Q(group__in=group_ids) | Q(everybody=True)
        perms = self.filter(q).order_by('folder__tree_id', 'folder__level',
                                        'folder__lft')
        for perm in perms:
            p = getattr(perm, attr)

            if p is None:
                # Not allow nor deny, we continue with the next permission
                continue

            if not perm.folder:
                assert perm.type == self.model.ALL

                all_folder_ids = Folder.objects.all().values_list('id', flat=True)
                if p == self.model.ALLOW:
                    allow_list.update(all_folder_ids)
                else:
                    deny_list.update(all_folder_ids)

                continue

            folder_id = perm.folder.id

            if p == self.model.ALLOW:
                allow_list.add(folder_id)
            else:
                deny_list.add(folder_id)

            if perm.type == self.model.CHILDREN:
                # FIXME: use Folder.objects.children_for(perm.folder) instead
                folder_children_ids = perm.folder.get_descendants().values_list('id', flat=True)
                if p == self.model.ALLOW:
                    allow_list.update(folder_children_ids)
                else:
                    deny_list.update(folder_children_ids)

        # Deny has precedence over allow
        return allow_list - deny_list


class FileManager(PolymorphicManager):
    def in_folder(self, folder):
        pass

    def find_all_duplicates(self):
        r = {}
        for file_obj in self.all():
            if file_obj.sha1:
                q = self.filter(sha1=file_obj.sha1)
                if len(q) > 1:
                    r[file_obj.sha1] = q
        return r

    def find_duplicates(self, file_obj):
        return [i for i in self.exclude(pk=file_obj.pk).filter(sha1=file_obj.sha1)]
