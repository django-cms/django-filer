from __future__ import absolute_import, unicode_literals

from django.db import models
from django.db.models import Q
from mptt.managers import TreeManager
from mptt.querysets import TreeQuerySet
from polymorphic.query import PolymorphicQuerySet

from . import settings as filer_settings

try:
    from polymorphic.managers import PolymorphicManager
except ImportError:
    # django-polymorphic < 0.8
    from polymorphic import PolymorphicManager


class FolderQuerySet(TreeQuerySet):
    def filter_for_user(self, user):
        from .models.foldermodels import FolderPermission

        perms = FolderPermission.objects.get_read_id_list(user)
        if perms == 'All':
            return self.all()
        return self.filter(Q(id__in=perms) | Q(owner=user))


class FolderManager(TreeManager):
    _queryset_class = FolderQuerySet

    def filter_for_user(self, user):
        return self.get_queryset().filter_for_user(user)

    @property
    def root_folder(self):
        from .models.virtualitems import FolderRoot

        return FolderRoot()


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

        # try to return from cache
        try:
            return user._filer_folder_perms[attr]
        except AttributeError:
            pass

        id_lists = {
            'can_read': (set(), set()),
            'can_edit': (set(), set()),
            'can_add_children': (set(), set()),
        }
        group_ids = user.groups.all().values_list('id', flat=True)
        q = Q(user=user) | Q(group__in=group_ids) | Q(everybody=True)
        perms = self.filter(q).order_by('folder__tree_id', 'folder__level',
                                        'folder__lft')
        for perm in perms:
            if not perm.folder:
                assert perm.type == self.model.ALL

                ids = Folder.objects.all().values_list('id', flat=True)
            elif perm.type == self.model.CHILDREN:
                ids = perm.folder.get_descendants().values_list('id', flat=True)
            else:
                ids = [perm.folder.id]

            for p_attr in id_lists.keys():
                p = getattr(perm, p_attr)
                if p == self.model.ALLOW:
                    id_lists[p_attr][0].update(ids)
                else:
                    id_lists[p_attr][1].update(ids)

        # cache inside user instance (deny has precedence over allow)
        user._filer_folder_perms = {p_attr: p_lists[0] - p_lists[1] for p_attr, p_lists in id_lists.items()}

        return user._filer_folder_perms[attr]


class FileQuerySet(PolymorphicQuerySet):
    def filter_for_user(self, user):
        from .models.foldermodels import FolderPermission

        perms = FolderPermission.objects.get_read_id_list(user)
        if perms == 'All':
            return self.all()
        return self.filter(Q(folder__id__in=perms) | Q(owner=user))


class FileManager(PolymorphicManager):
    _queryset_class = FileQuerySet
    queryset_class = FileQuerySet  # for PolymorphicManager

    def filter_for_user(self, user):
        return self.get_queryset().filter_for_user(user)

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
