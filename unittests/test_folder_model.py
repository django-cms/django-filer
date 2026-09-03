"""
Tests for the invariants and the recursive operations of `FolderModel`.
"""
import pytest

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from finder.models.file import FileModel
from finder.models.folder import ROOT_FOLDER_NAME, TRASH_FOLDER_NAME, FolderModel
from finder.models.permission import DefaultAccessControlEntry, Privilege


@pytest.fixture
def populated_folder(ambit, admin_user, sub_folder):
    """
    Root
    └── Sub Folder
        ├── document.bin
        └── Nested Folder
            └── nested.bin
    """
    nested_folder = FolderModel.objects.create(parent=sub_folder, name="Nested Folder", owner=admin_user)
    for folder, file_name in [(sub_folder, 'document.bin'), (nested_folder, 'nested.bin')]:
        FileModel.objects.create_from_upload(
            ambit,
            SimpleUploadedFile(file_name, file_name.encode(), content_type='application/octet-stream'),
            folder=folder,
            owner=admin_user,
        )
    return sub_folder


class TestValidateConstraints:
    """The rules protecting the integrity of the folder tree."""

    def test_a_folder_may_not_become_its_own_descendant(self, ambit, admin_user, sub_folder):
        nested_folder = FolderModel.objects.create(parent=sub_folder, name="Nested Folder", owner=admin_user)
        sub_folder.parent = nested_folder
        with pytest.raises(ValidationError, match="A parent folder cannot become the descendant"):
            sub_folder.validate_constraints()

    def test_a_folder_may_not_be_its_own_parent(self, ambit, admin_user, sub_folder):
        sub_folder.parent = sub_folder
        with pytest.raises(ValidationError, match="A parent folder cannot become the descendant"):
            sub_folder.validate_constraints()

    @pytest.mark.parametrize('reserved_name', [ROOT_FOLDER_NAME, TRASH_FOLDER_NAME])
    def test_reserved_names_are_rejected(self, ambit, admin_user, reserved_name):
        folder = FolderModel(parent=ambit.root_folder, name=reserved_name, owner=admin_user)
        with pytest.raises(ValidationError, match=f"Folder name “{reserved_name}” is reserved."):
            folder.validate_constraints()

    def test_duplicate_names_within_a_folder_are_rejected(self, ambit, admin_user, sub_folder):
        duplicate = FolderModel(parent=ambit.root_folder, name=sub_folder.name, owner=admin_user)
        with pytest.raises(ValidationError, match="already exists in destination folder"):
            duplicate.validate_constraints()

    def test_a_valid_folder_passes(self, ambit, admin_user, sub_folder):
        folder = FolderModel(parent=ambit.root_folder, name="Another Folder", owner=admin_user)
        folder.validate_constraints()


class TestCopyTo:
    def test_copies_the_whole_subtree(self, ambit, admin_user, populated_folder):
        target_folder = FolderModel.objects.create(
            parent=ambit.root_folder, name="Target Folder", owner=admin_user,
        )
        copied_folder = populated_folder.copy_to(ambit, admin_user, target_folder)

        assert copied_folder.parent == target_folder
        assert copied_folder.name == populated_folder.name
        assert copied_folder.id != populated_folder.id

        copied_file = FileModel.objects.get(name='document.bin', parent=copied_folder)
        assert copied_file.id != FileModel.objects.get(name='document.bin', parent=populated_folder).id

        copied_nested_folder = FolderModel.objects.get(name="Nested Folder", parent=copied_folder)
        copied_nested_file = FileModel.objects.get(name='nested.bin', parent=copied_nested_folder)

        # the payload of every copied file is duplicated in the storage
        for file_obj, content in [(copied_file, b'document.bin'), (copied_nested_file, b'nested.bin')]:
            assert ambit.original_storage.exists(file_obj.file_path) is True
            with ambit.original_storage.open(file_obj.file_path) as handle:
                assert handle.read() == content

    def test_leaves_the_source_subtree_untouched(self, ambit, admin_user, populated_folder):
        target_folder = FolderModel.objects.create(
            parent=ambit.root_folder, name="Target Folder", owner=admin_user,
        )
        populated_folder.copy_to(ambit, admin_user, target_folder)

        assert FolderModel.objects.filter(id=populated_folder.id).exists() is True
        assert FileModel.objects.filter(name='document.bin', parent=populated_folder).count() == 1
        assert FolderModel.objects.filter(name="Nested Folder", parent=populated_folder).count() == 1

    def test_copy_under_a_different_name(self, ambit, admin_user, populated_folder):
        copied_folder = populated_folder.copy_to(ambit, admin_user, ambit.root_folder, name="Copy of Sub Folder")
        assert copied_folder.name == "Copy of Sub Folder"
        assert FileModel.objects.filter(name='document.bin', parent=copied_folder).count() == 1

    def test_a_folder_cannot_be_copied_into_its_own_descendant(self, ambit, admin_user, populated_folder):
        nested_folder = FolderModel.objects.get(name="Nested Folder", parent=populated_folder)
        with pytest.raises(RecursionError, match="cannot become the descendant of destination folder"):
            populated_folder.copy_to(ambit, admin_user, nested_folder)


class TestApplyDefaultAccessControlList:
    @pytest.fixture
    def source_acl(self, ambit, admin_user, staff_users):
        """A default ACL living on another folder, used as the list to apply."""
        source_folder = FolderModel.objects.create(
            parent=ambit.root_folder, name="Source Folder", owner=admin_user,
        )
        DefaultAccessControlEntry.objects.create(
            folder=source_folder, user=staff_users[0], privilege=Privilege.READ,
        )
        return source_folder.default_access_control_list.all()

    def test_creates_missing_entries(self, ambit, admin_user, sub_folder, staff_users, source_acl):
        sub_folder.apply_default_access_control_list(source_acl)
        entries = sub_folder.default_access_control_list.all()
        assert [(entry.user, entry.privilege) for entry in entries] == [(staff_users[0], Privilege.READ)]

    def test_updates_the_privilege_of_an_existing_entry(self, ambit, admin_user, sub_folder, staff_users, source_acl):
        existing = DefaultAccessControlEntry.objects.create(
            folder=sub_folder, user=staff_users[0], privilege=Privilege.FULL,
        )
        sub_folder.apply_default_access_control_list(source_acl)

        existing.refresh_from_db()
        assert existing.privilege == Privilege.READ
        assert sub_folder.default_access_control_list.count() == 1

    def test_keeps_an_entry_which_did_not_change(self, ambit, admin_user, sub_folder, staff_users, source_acl):
        unchanged = DefaultAccessControlEntry.objects.create(
            folder=sub_folder, user=staff_users[0], privilege=Privilege.READ,
        )
        sub_folder.apply_default_access_control_list(source_acl)

        assert list(sub_folder.default_access_control_list.values_list('id', flat=True)) == [unchanged.id]

    def test_removes_entries_which_are_no_longer_part_of_the_list(self, ambit, admin_user, sub_folder,
                                                                  staff_users, source_acl):
        obsolete = DefaultAccessControlEntry.objects.create(
            folder=sub_folder, user=staff_users[1], privilege=Privilege.READ_WRITE,
        )
        sub_folder.apply_default_access_control_list(source_acl)

        assert DefaultAccessControlEntry.objects.filter(id=obsolete.id).exists() is False
        assert sub_folder.default_access_control_list.count() == 1

    def test_a_user_without_admin_privilege_may_not_change_the_list(self, ambit, sub_folder, staff_users, source_acl):
        """The list is left untouched rather than raising, so that recursive application can skip subtrees."""
        sub_folder.apply_default_access_control_list(source_acl, user=staff_users[1])
        assert sub_folder.default_access_control_list.exists() is False

    def test_is_applied_recursively(self, ambit, admin_user, populated_folder, staff_users, source_acl):
        nested_folder = FolderModel.objects.get(name="Nested Folder", parent=populated_folder)
        populated_folder.apply_default_access_control_list(source_acl, recursive=True)

        assert populated_folder.default_access_control_list.count() == 1
        assert nested_folder.default_access_control_list.count() == 1
