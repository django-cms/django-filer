import os

from django.conf import settings
from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from django.urls import reverse

from filer import settings as filer_settings
from filer.models.clipboardmodels import Clipboard
from filer.models.filemodels import File
from filer.models.foldermodels import Folder, FolderPermission
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import SettingsOverride, create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)


class Mock():
    pass


class FolderPermissionsTestCase(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        self.unauth_user = User.objects.create(username='unauth_user')

        self.owner = User.objects.create(username='owner')

        perms = Permission.objects.filter(codename="change_folder")
        perms |= Permission.objects.filter(codename="can_use_directory_listing")
        self.test_user1 = User.objects.create(username='test1', password='secret', is_staff=True)
        self.test_user1.set_password("secret")
        self.test_user1.save()
        self.test_user2 = User.objects.create(username='test2', password='secret')
        self.test_user1.user_permissions.add(*perms)
        self.test_user2.user_permissions.add(*perms)

        self.group1 = Group.objects.create(name='name1')
        self.group2 = Group.objects.create(name='name2')

        self.test_user1.groups.add(self.group1)
        self.test_user2.groups.add(self.group2)

        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        # This is actually a "file" for filer considerations
        self.image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=self.file)
        self.clipboard = Clipboard.objects.create(user=self.superuser)
        self.clipboard.append_file(self.image)

        self.folder = Folder.objects.create(name='test_folder')

        self.folder_perm = Folder.objects.create(name='test_folder2')

    def tearDown(self):
        self.file.close()
        self.image.delete()

    def test_folder_all(self):
        folder = Folder.objects.create(name="test_folder3")
        self.assertEqual(str(folder), "/test_folder3")

    def test_superuser_has_rights(self):
        request = Mock()
        setattr(request, 'user', self.superuser)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_unlogged_user_has_no_rights(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True
            request = Mock()
            setattr(request, 'user', self.unauth_user)

            result = self.folder.has_read_permission(request)
            self.assertEqual(result, False)
        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_user_cannot_see_other_users_files(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            url = reverse("admin:filer-directory_listing-unfiled_images")
            response = self.client.get(url)
            self.assertContains(response, self.image_name)
            loginok = self.client.login(username=self.test_user1.username, password="secret")
            self.assertTrue(loginok, "Could not login 'test_user1'")
            response = self.client.get(url)
            self.assertNotContains(response, self.image_name)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_unlogged_user_has_rights_when_permissions_disabled(self):
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_owner_user_has_rights(self):
        # Set owner as the owner of the folder.
        self.folder.owner = self.owner
        request = Mock()
        setattr(request, 'user', self.owner)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_combined_groups(self):
        request1 = Mock()
        setattr(request1, 'user', self.test_user1)
        request2 = Mock()
        setattr(request2, 'user', self.test_user2)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request1), False)
            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # Direct ORM writes bypass the permission admin cache invalidation.
            cache.clear()
            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), True)

            self.test_user1.groups.add(self.group2)
            self.test_user2.groups.add(self.group1)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')
            delattr(self.folder_perm, 'permission_cache')
            cache.clear()

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_read_permission(request1), True)
            self.assertEqual(self.folder_perm.has_read_permission(request2), True)

            self.assertEqual(self.folder_perm.pretty_logical_path, "/test_folder2")
        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            cache.clear()

    def test_overlapped_groups_deny1(self):
        # Tests overlapped groups with explicit deny

        request1 = Mock()
        setattr(request1, 'user', self.test_user1)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # Direct ORM writes bypass the permission admin cache invalidation.
            cache.clear()
            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.test_user1.groups.filter(pk=self.group1.pk).exists(), True)
            self.assertEqual(self.test_user1.groups.filter(pk=self.group2.pk).exists(), False)

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_edit_permission(request1), False)

            self.assertEqual(self.test_user1.groups.count(), 1)

            self.test_user1.groups.add(self.group2)

            self.assertEqual(self.test_user1.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_edit_permission(request1), False)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            cache.clear()

    def test_overlapped_groups_deny2(self):
        # Tests overlapped groups with explicit deny
        # Similar test to test_overlapped_groups_deny1, only order of groups is different

        request2 = Mock()
        setattr(request2, 'user', self.test_user2)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # Direct ORM writes bypass the permission admin cache invalidation.
            cache.clear()
            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.test_user2.groups.filter(pk=self.group2.pk).exists(), True)
            self.assertEqual(self.test_user2.groups.filter(pk=self.group1.pk).exists(), False)

            self.assertEqual(self.folder_perm.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_edit_permission(request2), False)

            self.assertEqual(self.test_user2.groups.count(), 1)

            self.test_user2.groups.add(self.group1)

            self.assertEqual(self.test_user2.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder_perm.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_edit_permission(request2), False)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            cache.clear()

    def test_overlapped_groups1(self):
        # Tests overlapped groups without explicit deny

        request1 = Mock()
        setattr(request1, 'user', self.test_user1)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=None, can_read=FolderPermission.ALLOW, can_add_children=None)
            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # Direct ORM writes bypass the permission admin cache invalidation.
            cache.clear()
            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.test_user1.groups.filter(pk=self.group1.pk).exists(), True)
            self.assertEqual(self.test_user1.groups.filter(pk=self.group2.pk).exists(), False)

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_edit_permission(request1), False)

            self.assertEqual(self.test_user1.groups.count(), 1)

            self.test_user1.groups.add(self.group2)

            self.assertEqual(self.test_user1.groups.count(), 2)

            # Group changes also invalidate cached empty permission sets.
            cache.clear()
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_edit_permission(request1), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            cache.clear()

    def test_overlapped_groups2(self):
        # Tests overlapped groups without explicit deny
        # Similar test to test_overlapped_groups1, only order of groups is different

        request2 = Mock()
        setattr(request2, 'user', self.test_user2)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=None, can_read=FolderPermission.ALLOW, can_add_children=None)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # Direct ORM writes bypass the permission admin cache invalidation.
            cache.clear()
            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.test_user2.groups.filter(pk=self.group2.pk).exists(), True)
            self.assertEqual(self.test_user2.groups.filter(pk=self.group1.pk).exists(), False)

            self.assertEqual(self.folder_perm.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_edit_permission(request2), False)

            self.assertEqual(self.test_user2.groups.count(), 1)

            self.test_user2.groups.add(self.group1)

            self.assertEqual(self.test_user2.groups.count(), 2)

            # Group changes also invalidate cached empty permission sets.
            cache.clear()
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder_perm.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_edit_permission(request2), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            cache.clear()

    def test_folder_who_owner(self):
        perm = FolderPermission.objects.create(
            user=self.owner,
            folder=Folder.objects.create(name="folder4"),
            type=FolderPermission.CHILDREN,
            can_edit=FolderPermission.DENY,
            can_read=FolderPermission.ALLOW,
            can_add_children=FolderPermission.ALLOW,
        )
        self.assertEqual(perm.who, "User: owner")
        self.assertEqual(perm.pretty_logical_path, "/folder4")
        self.assertEqual(perm.what, "E̶d̶i̶t̶, Read, Add children")

    def test_folder_who_group(self):
        perm = FolderPermission.objects.create(
            group=self.group1,
        )
        self.assertEqual(perm.who, "Group: name1")

    def test_folder_who_everybody(self):
        perm = FolderPermission.objects.create(
            everybody=True,
        )
        self.assertEqual(perm.who, "Everybody")
        self.assertEqual(perm.pretty_logical_path, "All Folders")
        self.assertEqual(perm.__str__(), "All Folders")

    def test_folder_who_nobody(self):
        perm = FolderPermission.objects.create()
        self.assertEqual(perm.who, "–")

    def test_delete_action_requires_edit_permission(self):
        # A staff user with only read access to a folder (can_read=ALLOW,
        # can_edit=DENY) plus the model-level delete permissions must NOT be
        # able to delete files/folders through the bulk delete action.
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        target_file = None
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            # Grant the model-level delete permissions to test_user1.
            delete_perms = Permission.objects.filter(
                codename__in=("delete_folder", "delete_file", "delete_image")
            )
            self.test_user1.user_permissions.add(*delete_perms)

            # Read allowed / edit denied on *all* folders. Using an "everybody"
            # permission means no FolderPermission row is attached to the target
            # folder itself, so the only thing that can block the deletion is
            # the missing edit permission (which is what we are testing).
            FolderPermission.objects.create(
                type=FolderPermission.ALL, everybody=True,
                can_edit=FolderPermission.DENY,
                can_read=FolderPermission.ALLOW,
                can_add_children=FolderPermission.DENY,
            )

            # A folder (owned by someone else) containing a file. test_user1 can
            # read it but must not be able to delete it.
            target = Folder.objects.create(name="readonly_target", owner=self.superuser)
            with open(self.filename, "rb") as opened_file:
                target_file = DjangoFile(opened_file, name="inside.jpg")
                inside = Image.objects.create(
                    owner=self.superuser, original_filename="inside.jpg",
                    file=target_file, folder=target,
                )

            self.assertTrue(
                self.client.login(username=self.test_user1.username, password="secret")
            )

            url = reverse('admin:filer-directory_listing-root')
            response = self.client.post(url, {
                'action': 'delete_files_or_folders',
                'post': 'yes',
                helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % target.id],
            })
            self.assertEqual(response.status_code, 403)
            # Neither the folder nor the file it contains may be deleted.
            self.assertTrue(Folder.objects.filter(pk=target.pk).exists())
            self.assertTrue(Image.objects.filter(pk=inside.pk).exists())
        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
            if target_file is not None:
                target_file.close()
            cache.clear()

    def test_folderpermission_is_copied(self):
        source_folder = Folder.objects.create(name="source")
        destination_folder = Folder.objects.create(name="destination")
        perm = FolderPermission.objects.create(
            user=self.owner,
            folder=source_folder,
            type=FolderPermission.CHILDREN,
            can_edit=FolderPermission.ALLOW,
            can_read=FolderPermission.DENY,
            can_add_children=FolderPermission.ALLOW,
        )
        self.assertEqual(FolderPermission.objects.count(), 1)
        url = reverse('admin:filer-directory_listing-root')
        self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': 'test',
            'destination': destination_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'folder-%d' % (source_folder.id,),
        })
        self.assertEqual(FolderPermission.objects.count(), 2)
        copied_folder = destination_folder.children.first()
        self.assertEqual(copied_folder.name, source_folder.name)
        new_perm = FolderPermission.objects.get(folder=copied_folder)
        self.assertEqual(perm.user, new_perm.user)
        self.assertEqual(perm.type, new_perm.type)
        self.assertEqual(perm.can_edit, new_perm.can_edit)
        self.assertEqual(perm.can_read, new_perm.can_read)
        self.assertEqual(perm.can_add_children, new_perm.can_add_children)


class AdminReadPermissionsTestCase(TestCase):
    """
    Regression tests for read permission checks on admin listings and views.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        cache.clear()
        self.owner = create_superuser()

        # A staff user with all the global filer permissions, but without any
        # FolderPermission granting access to self.secret_folder.
        self.staff = User.objects.create_user(
            username='staff', password='secret', is_staff=True, is_active=True)
        perms = Permission.objects.filter(codename__in=(
            'change_folder', 'can_use_directory_listing', 'add_file',
            'change_file', 'view_file', 'add_image', 'change_image', 'view_image',
        ))
        self.staff.user_permissions.add(*perms)
        self.staff = User.objects.get(pk=self.staff.pk)

        self.secret_folder = Folder.objects.create(name='secret', owner=self.owner)
        self.readable_folder = Folder.objects.create(name='readable', owner=self.owner)
        FolderPermission.objects.create(
            folder=self.readable_folder, user=self.staff,
            type=FolderPermission.CHILDREN, can_read=FolderPermission.ALLOW)

        self.filename = os.path.join(os.path.dirname(__file__), 'admin_perm_test.jpg')
        create_image().save(self.filename, 'JPEG')
        self.secret_file = self._create_image(self.secret_folder)
        self.readable_file = self._create_image(self.readable_folder)
        self.unfiled_file = self._create_image(None)

    def tearDown(self):
        cache.clear()
        for image in Image.objects.all():
            image.delete()
        Folder.objects.all().delete()
        os.remove(self.filename)

    def _create_image(self, folder):
        with open(self.filename, 'rb') as fh:
            return Image.objects.create(
                owner=self.owner, folder=folder, is_public=False,
                original_filename='admin_perm_test.jpg',
                file=DjangoFile(fh, name='admin_perm_test.jpg'))

    def _icon_url(self, image):
        return reverse('admin:filer_image_fileicon',
                       kwargs={'file_id': image.pk, 'size': 80})

    def _change_url(self, image):
        opts = Image._meta
        return reverse(
            f'admin:{opts.app_label}_{opts.model_name}_change', args=[image.pk])

    # -- icon_view ---------------------------------------------------------

    def test_icon_view_denied_for_unreadable_folder(self):
        """A staff user without read permission must not get the thumbnail
        redirect, which leaks the file name and its private storage path."""
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._icon_url(self.secret_file))
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('Location', response)

    def test_icon_view_allowed_for_readable_folder(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._icon_url(self.readable_file))
            self.assertEqual(response.status_code, 302)

    def test_icon_view_allowed_for_unfiled_file(self):
        """Unfiled files are listed for everyone by the directory listing, so
        their icons must keep working."""
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._icon_url(self.unfiled_file))
            self.assertEqual(response.status_code, 302)

    def test_icon_view_allowed_when_permissions_disabled(self):
        """No behaviour change for the default configuration."""
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=False):
            cache.clear()
            self.client.login(username='staff', password='secret')
            for image in (self.secret_file, self.readable_file, self.unfiled_file):
                response = self.client.get(self._icon_url(image))
                self.assertEqual(response.status_code, 302)

    def test_icon_view_allowed_for_superuser(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='admin', password='secret')
            response = self.client.get(self._icon_url(self.secret_file))
            self.assertEqual(response.status_code, 302)

    # -- change view / has_view_permission ---------------------------------

    def test_change_view_denied_for_unreadable_folder(self):
        """Global filer.change_image must not grant read access to a file in a
        folder the user has no read permission on."""
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._change_url(self.secret_file))
            self.assertEqual(response.status_code, 403)

    def test_change_view_allowed_for_readable_folder(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._change_url(self.readable_file))
            self.assertEqual(response.status_code, 200)

    def test_change_view_allowed_for_unfiled_file(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.client.login(username='staff', password='secret')
            response = self.client.get(self._change_url(self.unfiled_file))
            self.assertEqual(response.status_code, 200)

    def test_change_view_allowed_when_permissions_disabled(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=False):
            cache.clear()
            self.client.login(username='staff', password='secret')
            for image in (self.secret_file, self.readable_file, self.unfiled_file):
                response = self.client.get(self._change_url(image))
                self.assertEqual(response.status_code, 200)

    def test_has_view_permission(self):
        from django.contrib import admin as django_admin

        model_admin = django_admin.site._registry[Image]
        request = Mock()
        request.user = self.staff
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.assertFalse(model_admin.has_view_permission(request, self.secret_file))
            self.assertTrue(model_admin.has_view_permission(request, self.readable_file))
            self.assertTrue(model_admin.has_view_permission(request, self.unfiled_file))
            # The changelist must stay reachable
            self.assertTrue(model_admin.has_view_permission(request))

    def test_has_view_permission_requires_global_permission(self):
        """Folder read permission alone must not grant admin access."""
        from django.contrib import admin as django_admin

        model_admin = django_admin.site._registry[Image]
        self.staff.user_permissions.clear()
        request = Mock()
        request.user = get_user_model().objects.get(pk=self.staff.pk)
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            cache.clear()
            self.assertFalse(model_admin.has_view_permission(request, self.readable_file))

    def _changelist_url(self, model):
        opts = model._meta
        return reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')

    def test_changelists_filter_results_and_counts(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            File.objects.create(name='secret-document', folder=self.secret_folder, owner=self.owner)
            readable = File.objects.create(name='readable-document', folder=self.readable_folder, owner=self.owner)
            for model in (File, Image):
                for params in ({}, {'_popup': '1'}):
                    with self.subTest(model=model, params=params):
                        response = self.client.get(self._changelist_url(model), params)
                        self.assertEqual(response.status_code, 200)
                        expected = {self.readable_file.pk, self.unfiled_file.pk}
                        if model is File:
                            expected.add(readable.pk)
                        cl = response.context['cl']
                        self.assertEqual({obj.pk for obj in cl.result_list}, expected)
                        self.assertEqual(cl.result_count, len(expected))
                        self.assertEqual(cl.full_result_count, len(expected))
                        self.assertNotContains(response, 'secret-document')

    def test_changelist_search_cannot_probe_unreadable_files(self):
        Image.objects.filter(pk=self.secret_file.pk).update(
            name='secret-payroll', original_filename='confidential-original.jpg',
            description='confidential-description', sha1='a' * 40,
        )
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                for term in ('secret-payroll', 'confidential-original', 'confidential-description', 'a' * 40):
                    with self.subTest(model=model, term=term):
                        response = self.client.get(self._changelist_url(model), {'q': term, '_popup': '1'})
                        self.assertEqual(response.status_code, 200)
                        cl = response.context['cl']
                        self.assertEqual(list(cl.result_list), [])
                        self.assertEqual(cl.result_count, 0)
                        self.assertEqual(cl.full_result_count, 2)

    def test_changelist_allows_owned_files_and_readable_descendants(self):
        child = Folder.objects.create(name='readable-child', parent=self.readable_folder, owner=self.owner)
        child_file = self._create_image(child)
        Image.objects.filter(pk=self.secret_file.pk).update(owner=self.staff)
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                with self.subTest(model=model):
                    response = self.client.get(self._changelist_url(model))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        {obj.pk for obj in response.context['cl'].result_list},
                        {self.secret_file.pk, self.readable_file.pk, self.unfiled_file.pk, child_file.pk},
                    )

    def test_changelist_explicit_deny_overrides_read_grant(self):
        FolderPermission.objects.create(
            folder=self.readable_folder, everybody=True,
            type=FolderPermission.THIS, can_read=FolderPermission.DENY,
        )
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                with self.subTest(model=model):
                    response = self.client.get(self._changelist_url(model))
                    self.assertEqual(response.status_code, 200)
                    cl = response.context['cl']
                    self.assertEqual({obj.pk for obj in cl.result_list}, {self.unfiled_file.pk})
                    self.assertEqual(cl.full_result_count, 1)

    def test_changelist_requires_global_model_permission(self):
        self.staff.user_permissions.clear()
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                for params in ({}, {'_popup': '1'}):
                    with self.subTest(model=model, params=params):
                        response = self.client.get(self._changelist_url(model), params)
                        self.assertEqual(response.status_code, 403)

    def test_unreadable_object_views_keep_returning_forbidden(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                opts = model._meta
                for view in ('change', 'history', 'delete'):
                    with self.subTest(model=model, view=view):
                        url = reverse(f'admin:{opts.app_label}_{opts.model_name}_{view}', args=[self.secret_file.pk])
                        self.assertEqual(self.client.get(url).status_code, 403)

    def test_changelist_with_view_only_permission(self):
        self.staff.user_permissions.set(Permission.objects.filter(codename__in=('view_file', 'view_image')))
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            for model in (File, Image):
                with self.subTest(model=model):
                    response = self.client.get(self._changelist_url(model))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        {obj.pk for obj in response.context['cl'].result_list},
                        {self.readable_file.pk, self.unfiled_file.pk},
                    )

    def test_changelist_unrestricted_for_superuser_or_disabled_permissions(self):
        for enabled, user in ((True, self.owner), (False, self.staff)):
            with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=enabled):
                self.client.force_login(user)
                for model in (File, Image):
                    with self.subTest(enabled=enabled, model=model):
                        response = self.client.get(self._changelist_url(model))
                        self.assertEqual(response.status_code, 200)
                        cl = response.context['cl']
                        self.assertEqual({obj.pk for obj in cl.result_list}, {
                            self.secret_file.pk, self.readable_file.pk, self.unfiled_file.pk,
                        })
                        self.assertEqual(cl.full_result_count, 3)

    def test_unreadable_directory_does_not_disclose_names(self):
        parent = Folder.objects.create(name='secret-parent', owner=self.owner)
        self.secret_folder.parent = parent
        self.secret_folder.save()
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            url = reverse('admin:filer-directory_listing', args=[self.secret_folder.pk])
            for params in ({}, {'_popup': '1'}, {'q': 'secret'}):
                with self.subTest(params=params):
                    response = self.client.get(url, params)
                    self.assertEqual(response.status_code, 403)
                    self.assertNotContains(response, 'secret-parent', status_code=403)
                    self.assertNotContains(response, 'Directory listing for secret', status_code=403)

    def test_last_directory_falls_back_when_read_permission_revoked(self):
        session = self.client.session
        session['filer_last_folder_id'] = self.secret_folder.pk
        session.save()
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            response = self.client.get(reverse('admin:filer-directory_listing-last'))
            self.assertRedirects(response, reverse('admin:filer-directory_listing-root'))

    def test_readable_directory_hides_unreadable_ancestors(self):
        self.secret_folder.name = 'unreadable-ancestor-name'
        self.secret_folder.save()
        self.readable_folder.parent = self.secret_folder
        self.readable_folder.save()
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            url = reverse('admin:filer-directory_listing', args=[self.readable_folder.pk])
            response = self.client.get(url)
            self.assertContains(response, 'Directory listing for readable')
            self.assertNotContains(response, self.secret_folder.name)
            self.assertNotContains(response, f'/folder/{self.secret_folder.pk}/list/')
            for url in (self._change_url(self.readable_file), reverse(
                'admin:filer_folder_change', args=[self.readable_folder.pk],
            )):
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, self.secret_folder.name)
            for list_type in ('tb', 'th'):
                with self.subTest(list_type=list_type):
                    response = self.client.get(reverse('admin:filer-directory_listing-root'), {
                        '_popup': '1', '_pick': 'folder', '_list_type': list_type,
                    })
                    self.assertContains(response, 'readable')
                    self.assertContains(response, 'data-label="/readable"')
                    self.assertNotContains(response, self.secret_folder.name)

    def test_directory_access_for_owner_superuser_and_disabled_permissions(self):
        url = reverse('admin:filer-directory_listing', args=[self.secret_folder.pk])
        for enabled, user in ((True, self.owner), (False, self.staff)):
            with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=enabled):
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertContains(response, 'Directory listing for secret')
        self.secret_folder.owner = self.staff
        self.secret_folder.save()
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.client.force_login(self.staff)
            self.assertContains(self.client.get(url), 'Directory listing for secret')
