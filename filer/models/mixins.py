#-*- coding: utf-8 -*-
from filer.settings import FILER_ADMIN_ICON_SIZES, FILER_STATICMEDIA_PREFIX


class IconsMixin(object):
    """
    Can be used on any model that has a _icon attribute. will return a dict
    containing urls for icons of different sizes with that name.
    """
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in FILER_ADMIN_ICON_SIZES:
                r[size] = "%sicons/%s_%sx%s.png" % (
                            FILER_STATICMEDIA_PREFIX, self._icon, size, size)
        return r


class PermissionRefreshMixin(object):
    def refresh_permissions_from_model_workaround(self, recursively=True):
        """
        This is a workaround method while we still have the Permission model.
        See filer.models.permissionmodels.Permission for details.
        """
        # TODO: remove with Permission Model refactor
        from .permissionmodels import PermissionSet
        subject = self
        old_who_can_read_local = subject.who_can_read_local.clone()
        old_who_can_edit_local = subject.who_can_edit_local.clone()
        subject.who_can_read_local = PermissionSet()
        subject.who_can_edit_local = PermissionSet()

        for permission in subject.permission_set.all():
            if permission.can_read_bool in (True, False):
                subject.who_can_read_local.add_permission(
                    permission.who, permission.get_who_id(), permission.can_read_bool)
            if permission.can_edit_bool in (True, False):
                subject.who_can_edit_local.add_permission(
                    permission.who, permission.get_who_id(), permission.can_edit_bool)

        if old_who_can_read_local == subject.who_can_read_local and old_who_can_edit_local == subject.who_can_edit_local:
            # nothing has changed. we can stop here
            return

        # the local permissions have changed. let's update the aggregated permissions and
        # tell our descendants about the change
        self.refresh_aggregated_permissions(recursively=recursively)


    def refresh_aggregated_permissions(self, save=True, recursively=True):
        """
        Refreshes the aggregated permission based on the parents aggregated permissions.
        This method is usually called when the permissions of an ancestor have changed.
        """
        from filer.models import FolderRoot
        assert not (save is False and recursively is True)
        subject = self
        old_who_can_read = subject.who_can_read.clone()
        old_who_can_edit = subject.who_can_edit.clone()
        old_who_can_read_local = subject.who_can_read_local.clone()
        old_who_can_edit_local = subject.who_can_edit_local.clone()
        if subject.owner_id:
            subject.who_can_read_local.add_user_id(subject.owner_id, True)
            subject.who_can_edit_local.add_user_id(subject.owner_id, True)
        parent = self.parent or FolderRoot()
        subject.who_can_read = subject.who_can_read_local.inherit_from(parent.who_can_read)
        subject.who_can_edit = subject.who_can_edit_local.inherit_from(parent.who_can_edit)

        local_has_changed = old_who_can_read_local != subject.who_can_read_local\
            or old_who_can_edit_local != subject.who_can_edit_local
        aggregate_has_changed = old_who_can_read != subject.who_can_read \
                or old_who_can_edit != subject.who_can_edit

        if local_has_changed or aggregate_has_changed:
            if save:
                subject.save(refresh_metadata=False, refresh_aggregated_permissions=False)
            if aggregate_has_changed and recursively and hasattr(subject, 'children'):
                for folder in subject.children.all():
                    folder.parent = subject  # prevent another db query
                    folder.refresh_aggregated_permissions(recursively=recursively)
                for file_obj in subject.files.all():
                    file_obj.folder = subject
                    file_obj.refresh_aggregated_permissions(recursively=False)