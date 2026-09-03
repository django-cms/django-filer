"""
Tests for `FinderFileField` and `FinderFolderField`, the fields other applications use to refer to inodes.

Since these references are no real foreign keys, the database cannot enforce them: whenever an inode is
deleted, django-finder must apply the declared `on_delete` behaviour itself. This is the contract
third-party applications rely upon.
"""
import pytest
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import F, UUIDField
from django.db.models.functions import Cast

from finder.models.fields import FinderBaseModelField, FinderFileField
from finder.models.file import FileModel
from finder.models.folder import FolderModel

from .testapp.models import (
    REPLACEMENT_FILE_ID, SampleAppModel1, SampleAppModel2, SampleAppModel3, SampleAppModel4, SampleAppModel7,
    SampleAppModel8, SampleAppModel9,
)


@pytest.fixture
def public_file(public_ambit, admin_user):
    def build(name='referenced.bin'):
        uploaded_file = SimpleUploadedFile(name, b'\x00' * 10, content_type='application/octet-stream')
        return FileModel.objects.create_from_upload(
            public_ambit, uploaded_file, folder=public_ambit.root_folder, owner=admin_user,
        )

    return build


def raw_reference(model, obj, field_name='file'):
    """Read the stored UUID rather than the inode it resolves to."""
    return model.objects.filter(id=obj.id).annotate(
        raw_value=Cast(F(field_name), output_field=UUIDField()),
    ).values_list('raw_value', flat=True).first()


def test_on_delete_must_be_callable():
    with pytest.raises(TypeError, match="on_delete must be callable."):
        FinderFileField('PROTECT')


class TestUpdateOrDeleteReferringModels:
    """`FinderBaseModelField.update_or_delete_referring_models` is what actually enforces `on_delete`."""

    def test_set_null_clears_the_reference(self, public_file):
        file_obj = public_file()
        obj = SampleAppModel7.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        obj.refresh_from_db()
        assert obj.file is None

    def test_set_replaces_the_reference_by_the_declared_value(self, public_file):
        file_obj = public_file()
        obj = SampleAppModel9.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        assert raw_reference(SampleAppModel9, obj) == REPLACEMENT_FILE_ID

    def test_set_default_resets_the_reference_to_the_field_default(self, public_file):
        file_obj = public_file()
        obj = SampleAppModel2.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        obj.refresh_from_db()
        assert obj.file is None

    def test_cascade_deletes_the_referring_object(self, public_file):
        file_obj = public_file('picture.bin')
        obj = SampleAppModel3.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        assert SampleAppModel3.objects.filter(id=obj.id).exists() is False

    def test_do_nothing_keeps_the_dangling_reference(self, public_file):
        file_obj = public_file()
        obj = SampleAppModel8.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        assert raw_reference(SampleAppModel8, obj) == file_obj.id

    def test_protect_keeps_the_reference(self, public_file):
        """`update_or_delete_referring_models` never deletes a protected reference — the caller has to
        refuse the deletion instead, which the folder admin does."""
        file_obj = public_file()
        obj = SampleAppModel1.objects.create(file=file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        assert raw_reference(SampleAppModel1, obj) == file_obj.id

    def test_objects_referring_to_other_inodes_are_untouched(self, public_file):
        file_obj, other_file_obj = public_file('one.bin'), public_file('two.bin')
        obj = SampleAppModel7.objects.create(file=other_file_obj.id)

        FinderBaseModelField.update_or_delete_referring_models([file_obj.id])

        assert raw_reference(SampleAppModel7, obj) == other_file_obj.id


class TestGetReferencedInodes:
    def test_reports_model_field_and_on_delete_per_reference(self, public_file):
        file_obj = public_file()
        SampleAppModel1.objects.create(file=file_obj.id)

        referenced = list(FinderBaseModelField.get_referenced_inodes([file_obj.id]))

        assert referenced == [{
            'model_name': 'SampleAppModel1',
            'field_name': 'file',
            'on_delete': 'PROTECT',
            'inode_id': file_obj.id,
        }]

    def test_collects_references_across_models(self, public_ambit, admin_user, public_file):
        file_obj = public_file()
        folder_obj = FolderModel.objects.create(
            parent=public_ambit.root_folder, name="Referenced Folder", owner=admin_user,
        )
        SampleAppModel1.objects.create(file=file_obj.id)
        SampleAppModel7.objects.create(file=file_obj.id)
        SampleAppModel4.objects.create(folder=folder_obj.id)

        referenced = FinderBaseModelField.get_referenced_inodes([file_obj.id, folder_obj.id])

        assert {(ref['model_name'], ref['on_delete']) for ref in referenced} == {
            ('SampleAppModel1', 'PROTECT'),
            ('SampleAppModel7', 'SET_NULL'),
            ('SampleAppModel4', 'PROTECT'),
        }

    def test_unreferenced_inodes_yield_nothing(self, public_file):
        file_obj = public_file()
        assert list(FinderBaseModelField.get_referenced_inodes([file_obj.id])) == []


class TestFromDbValue:
    """Reading a reference back resolves it into the inode itself, or into None if it is gone."""

    def test_file_reference_resolves_to_the_file(self, public_file):
        file_obj = public_file()
        obj = SampleAppModel1.objects.create(file=file_obj.id)

        obj = SampleAppModel1.objects.get(id=obj.id)
        assert isinstance(obj.file, FileModel)
        assert obj.file.id == file_obj.id

    def test_dangling_file_reference_resolves_to_none(self, db, public_ambit):
        obj = SampleAppModel1.objects.create(file=uuid.uuid4())
        assert SampleAppModel1.objects.get(id=obj.id).file is None

    def test_file_reference_of_a_foreign_mime_type_resolves_to_none(self, public_file):
        """`SampleAppModel3.file` only accepts images, so a reference to a binary file does not resolve."""
        file_obj = public_file()
        obj = SampleAppModel3.objects.create(file=file_obj.id)
        assert SampleAppModel3.objects.get(id=obj.id).file is None

    def test_empty_file_reference_stays_none(self, db, public_ambit):
        obj = SampleAppModel1.objects.create()
        assert SampleAppModel1.objects.get(id=obj.id).file is None

    def test_folder_reference_resolves_to_the_folder(self, public_ambit, admin_user):
        folder_obj = FolderModel.objects.create(
            parent=public_ambit.root_folder, name="Referenced Folder", owner=admin_user,
        )
        obj = SampleAppModel4.objects.create(folder=folder_obj.id)

        obj = SampleAppModel4.objects.get(id=obj.id)
        assert isinstance(obj.folder, FolderModel)
        assert obj.folder.id == folder_obj.id

    def test_dangling_folder_reference_resolves_to_none(self, db, public_ambit):
        obj = SampleAppModel4.objects.create(folder=uuid.uuid4())
        assert SampleAppModel4.objects.get(id=obj.id).folder is None

    def test_empty_folder_reference_stays_none(self, db, public_ambit):
        obj = SampleAppModel4.objects.create()
        assert SampleAppModel4.objects.get(id=obj.id).folder is None
