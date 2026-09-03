"""
Tests for the storage helpers. `delete_directory` is used whenever an inode is erased, and it has to
tolerate storages which do not know directories, plus files vanishing underneath it.
"""
import pytest
import uuid

from django.core.files.base import ContentFile

from finder.storages import copy_to_local, delete_directory


@pytest.fixture
def storage(ambit):
    return ambit.original_storage


@pytest.fixture
def inode_id():
    """Payloads are stored below a directory named after the id of the inode owning them."""
    return str(uuid.uuid4())


@pytest.fixture
def populated_directory(storage, inode_id):
    """
    <inode_id>/
    ├── one.bin
    ├── two.bin
    └── nested/
        └── three.bin
    """
    storage.save(f'{inode_id}/one.bin', ContentFile(b'one'))
    storage.save(f'{inode_id}/two.bin', ContentFile(b'two'))
    storage.save(f'{inode_id}/nested/three.bin', ContentFile(b'three'))
    return inode_id


class TestFinderSystemStorage:
    """The payload of an inode is sharded over two directory levels derived from its id. Changing that
    layout makes every already stored file unreachable."""

    def test_path_is_sharded_by_the_inode_id(self, storage):
        inode_id = 'a1b2c3d4-0000-4000-8000-000000000000'
        path = storage.path(f'{inode_id}/picture.png')
        assert path.endswith(f'/a1/b2/{inode_id}/picture.png')

    def test_url_is_sharded_by_the_inode_id(self, storage):
        inode_id = 'a1b2c3d4-0000-4000-8000-000000000000'
        assert storage.url(f'{inode_id}/picture.png').endswith(f'/a1/b2/{inode_id}/picture.png')

    def test_a_directory_without_a_file_name(self, storage):
        """`delete_directory` addresses the directory of an inode without naming a file in it."""
        inode_id = 'a1b2c3d4-0000-4000-8000-000000000000'
        assert storage.path(inode_id).endswith(f'/a1/b2/{inode_id}')

    def test_names_not_starting_with_an_inode_id_are_rejected(self, storage):
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            storage.path('somedir/picture.png')


class TestDeleteDirectory:
    def test_removes_files_and_subdirectories(self, storage, populated_directory):
        delete_directory(storage, populated_directory)

        assert storage.exists(f'{populated_directory}/one.bin') is False
        assert storage.exists(f'{populated_directory}/two.bin') is False
        assert storage.exists(f'{populated_directory}/nested/three.bin') is False
        assert storage.exists(populated_directory) is False

    def test_trailing_slashes_are_ignored(self, storage, populated_directory):
        delete_directory(storage, f'{populated_directory}/')
        assert storage.exists(populated_directory) is False

    def test_unknown_directory_is_not_an_error(self, storage):
        """Not every storage can tell whether a directory exists, so a missing one is simply ignored."""
        delete_directory(storage, str(uuid.uuid4()))

    def test_leaves_other_directories_alone(self, storage, populated_directory):
        other_id = str(uuid.uuid4())
        storage.save(f'{other_id}/keep.bin', ContentFile(b'keep'))

        delete_directory(storage, populated_directory)

        assert storage.exists(f'{other_id}/keep.bin') is True

    def test_tolerates_entries_vanishing_while_deleting(self, storage, populated_directory):
        """Another process may have removed an entry between listing and deleting it."""
        deleted = []

        def delete(name):
            deleted.append(name)
            raise FileNotFoundError(name)

        storage.delete = delete
        try:
            delete_directory(storage, populated_directory)
        finally:
            del storage.delete

        assert f'{populated_directory}/one.bin' in deleted
        assert f'{populated_directory}/nested/three.bin' in deleted
        assert populated_directory in deleted


class TestCopyToLocal:
    def test_copies_the_payload_into_a_temporary_file(self, storage, inode_id):
        storage.save(f'{inode_id}/movie.mp4', ContentFile(b'\x00\x01\x02' * 1000))

        with copy_to_local(storage, f'{inode_id}/movie.mp4') as local_file:
            local_file.seek(0)
            assert local_file.read() == b'\x00\x01\x02' * 1000

    def test_keeps_the_suffix_of_the_source(self, storage, inode_id):
        """ffmpeg picks its demuxer by suffix, so the temporary file has to keep it."""
        storage.save(f'{inode_id}/sound.ogg', ContentFile(b'audio'))

        with copy_to_local(storage, f'{inode_id}/sound.ogg') as local_file:
            assert local_file.name.endswith('.ogg')

    def test_missing_source_raises(self, storage, inode_id):
        with pytest.raises(FileNotFoundError):
            copy_to_local(storage, f'{inode_id}/no-such-file.mp4')
