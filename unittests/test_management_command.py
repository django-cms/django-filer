import pytest

from io import StringIO

from django.contrib.sites.models import Site
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from finder.contrib.image.pil.models import PILImageModel
from finder.models.ambit import AmbitModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel, ROOT_FOLDER_NAME
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege


@pytest.fixture
def finder_command():
    def call(*args, **options):
        stdout, stderr = StringIO(), StringIO()
        call_command('finder', *args, stdout=stdout, stderr=stderr, **options)
        return stdout.getvalue(), stderr.getvalue()

    return call


def test_unknown_subcommand(db, finder_command):
    with pytest.raises(CommandError, match="invalid choice: 'no-such-subcommand'"):
        finder_command('no-such-subcommand')


def test_list_ambits(db, finder_command, ambit, alternative_ambit):
    stdout, stderr = finder_command('list-ambits')
    assert stderr == ''
    assert f"Slug: {ambit.slug}, Name: {ambit.verbose_name}" in stdout
    assert f"Slug: {alternative_ambit.slug}" in stdout


def test_add_ambit(db, finder_command):
    stdout, stderr = finder_command(
        'add-ambit', 'extra',
        '--values', 'name=Extra Ambit', 'storage=finder_test', 'sample_storage=finder_test_samples',
    )
    assert stderr == ''
    assert stdout.strip() == "Successfully created ambit with slug ‘extra’."

    ambit_obj = AmbitModel.objects.get(slug='extra')
    assert ambit_obj.verbose_name == "Extra Ambit"
    assert ambit_obj._original_storage == 'finder_test'
    assert ambit_obj._sample_storage == 'finder_test_samples'
    assert ambit_obj.root_folder.name == ROOT_FOLDER_NAME
    assert ambit_obj.root_folder.parent is None
    # everybody may read and write in the root folder of a fresh ambit
    ace = AccessControlEntry.objects.get(inode=ambit_obj.root_folder.id)
    assert (ace.user, ace.group, ace.privilege) == (None, None, Privilege.READ_WRITE)
    default_ace = DefaultAccessControlEntry.objects.get(folder=ambit_obj.root_folder)
    assert (default_ace.user, default_ace.group, default_ace.privilege) == (None, None, Privilege.READ_WRITE)


def test_add_ambit_without_verbose_name(db, finder_command):
    finder_command(
        'add-ambit', 'extra',
        '--values', 'storage=finder_test', 'sample_storage=finder_test_samples',
    )
    assert AmbitModel.objects.get(slug='extra').verbose_name == "Extra"


def test_add_ambit_with_site_and_admin(db, finder_command):
    site = Site.objects.get_current()
    finder_command(
        'add-ambit', 'extra',
        '--values', f'site={site.id}', 'admin=admin',
        'storage=finder_test', 'sample_storage=finder_test_samples',
    )
    ambit_obj = AmbitModel.objects.get(slug='extra')
    assert ambit_obj.site == site
    assert ambit_obj.admin_name == 'admin'


def test_add_ambit_with_unknown_admin_site(db, finder_command):
    stdout, stderr = finder_command(
        'add-ambit', 'extra',
        '--values', 'admin=no-such-admin', 'storage=finder_test', 'sample_storage=finder_test_samples',
    )
    assert stderr.strip() == "Error while adding ambit: ‘No such admin site ‘no-such-admin’.’"
    assert AmbitModel.objects.filter(slug='extra').exists() is False


@pytest.mark.parametrize('storage_values', [
    ['storage=no-such-storage', 'sample_storage=finder_test_samples'],
    ['storage=finder_test', 'sample_storage=no-such-storage'],
])
def test_add_ambit_with_unknown_storage(db, finder_command, storage_values):
    stdout, stderr = finder_command('add-ambit', 'extra', '--values', *storage_values)
    assert stderr.strip() == "Error while adding ambit: ‘Storage backend ‘no-such-storage’ is not configured.’"
    assert AmbitModel.objects.filter(slug='extra').exists() is False


def test_add_ambit_without_storage(db, finder_command):
    """Omitting the storages is no longer an error: they fall back to the default alias."""
    stdout, stderr = finder_command('add-ambit', 'extra', '--values')
    assert stderr.strip() == ''
    ambit_obj = AmbitModel.objects.get(slug='extra')
    assert ambit_obj._original_storage == 'default'
    assert ambit_obj._sample_storage == 'default'


def test_edit_ambit(db, finder_command, ambit):
    site = Site.objects.get_current()
    stdout, stderr = finder_command(
        'edit-ambit', ambit.slug,
        '--values', 'name=Renamed', f'site={site.id}', 'admin=admin',
        'storage=finder_alternative', 'sample_storage=finder_alternative_samples',
    )
    assert stderr == ''
    assert stdout.strip() == f"Successfully updated ambit with slug ‘{ambit.slug}’."
    ambit.refresh_from_db()
    assert ambit.verbose_name == "Renamed"
    assert ambit.site == site
    assert ambit.admin_name == 'admin'
    assert ambit._original_storage == 'finder_alternative'
    assert ambit._sample_storage == 'finder_alternative_samples'


def test_edit_ambit_keeps_unknown_storages(db, finder_command, ambit):
    finder_command(
        'edit-ambit', ambit.slug,
        '--values', 'storage=no-such-storage', 'sample_storage=no-such-storage',
    )
    ambit.refresh_from_db()
    assert ambit._original_storage == 'finder_test'
    assert ambit._sample_storage == 'finder_test_samples'


def test_edit_ambit_with_unknown_admin_site(db, finder_command, ambit):
    stdout, stderr = finder_command('edit-ambit', ambit.slug, '--values', 'admin=no-such-admin')
    assert stderr.strip() == "Error while changing ambit: ‘No such admin site ‘no-such-admin’.’"


def test_edit_unknown_ambit(db, finder_command, ambit):
    stdout, stderr = finder_command('edit-ambit', 'no-such-ambit', '--values', 'name=Renamed')
    assert stdout == ''
    assert stderr == ''


def test_delete_ambit(db, finder_command, ambit, sub_folder, uploaded_file, admin_user):
    nested_file = FileModel.objects.create_from_upload(
        ambit,
        SimpleUploadedFile('nested.bin', b'\x00' * 10, content_type='application/octet-stream'),
        folder=sub_folder,
        owner=admin_user,
    )
    stdout, stderr = finder_command('delete-ambit', ambit.slug)
    assert stderr == ''
    assert stdout.strip() == f"Successfully deleted ambit with slug ‘{ambit.slug}’."
    assert AmbitModel.objects.filter(slug=ambit.slug).exists() is False
    assert FolderModel.objects.filter(id=sub_folder.id).exists() is False
    assert FileModel.objects.filter(id=uploaded_file.id).exists() is False
    assert FileModel.objects.filter(id=nested_file.id).exists() is False
    # without --erase-files, the payload remains in the storage
    assert ambit.original_storage.exists(nested_file.file_path) is True


def test_delete_ambit_and_erase_files(db, finder_command, ambit, uploaded_file):
    assert ambit.original_storage.exists(uploaded_file.file_path) is True
    finder_command('delete-ambit', ambit.slug, '--erase-files')
    assert AmbitModel.objects.filter(slug=ambit.slug).exists() is False
    assert ambit.original_storage.exists(uploaded_file.file_path) is False


def test_delete_unknown_ambit(db, finder_command, ambit):
    stdout, stderr = finder_command('delete-ambit', 'no-such-ambit')
    assert "Error while deleting ambit:" in stderr
    assert AmbitModel.objects.filter(slug=ambit.slug).exists() is True


def test_reorganize_moves_file_to_its_specific_model(db, finder_command, ambit, admin_user):
    """A PNG stored as generic file is moved over to the model handling web images."""
    file_obj = FileModel.objects.create_from_upload(
        ambit,
        SimpleUploadedFile('picture.png', b'\x89PNG\r\n\x1a\n', content_type='application/octet-stream'),
        folder=ambit.root_folder,
        owner=admin_user,
        mime_type='image/png',
    )
    stdout, stderr = finder_command('reorganize', ambit.slug)
    assert stderr == ''
    assert "Reorganize file ‘picture.png’" in stdout
    assert FileModel.objects.filter(id=file_obj.id).exists() is False
    image_obj = PILImageModel.objects.get(id=file_obj.id)
    assert image_obj.name == 'picture.png'
    assert image_obj.file_name == file_obj.file_name
    assert image_obj.parent == ambit.root_folder
    assert image_obj.owner == admin_user


def test_reorganize_keeps_matching_files(db, finder_command, ambit, uploaded_file):
    stdout, stderr = finder_command('reorganize', ambit.slug)
    assert "Reorganize file ‘" not in stdout
    assert FileModel.objects.filter(id=uploaded_file.id).exists() is True


def test_reorder_without_gaps(db, finder_command, ambit, uploaded_file):
    stdout, stderr = finder_command('reorder', ambit.slug)
    assert stderr == ''
    assert "No folder required any reordering." in stdout


def test_reorder_closes_gaps(db, finder_command, ambit, admin_user, uploaded_file):
    second_file = FileModel.objects.create_from_upload(
        ambit,
        SimpleUploadedFile('second.bin', b'\x00' * 10, content_type='application/octet-stream'),
        folder=ambit.root_folder,
        owner=admin_user,
    )
    FileModel.objects.filter(id=second_file.id).update(ordering=17)

    stdout, stderr = finder_command('reorder', ambit.slug, verbosity=2)
    assert stderr == ''
    assert "Reordered 1 items in folder ‘Root’." in stdout
    assert "No folder required any reordering." not in stdout
    second_file.refresh_from_db()
    assert second_file.ordering == 2
