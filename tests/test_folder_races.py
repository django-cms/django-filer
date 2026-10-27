from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin import helpers
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from filer.admin.folderadmin import FolderAdmin
from filer.models import File, Folder, FolderRoot
from tests.helpers import create_superuser


class FolderRaceTests(TestCase):
    def setUp(self):
        self.user = create_superuser()
        self.client.force_login(self.user)
        self.folder_admin = FolderAdmin(Folder, admin.site)

    @skipUnlessDBFeature('supports_partial_indexes')
    def test_root_uniqueness_also_covers_bulk_inserts(self):
        Folder.objects.create(name='same')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Folder.objects.bulk_create([Folder(name='same')])
        parent = Folder.objects.create(name='parent')
        Folder.objects.create(name='same', parent=parent)

    @skipUnlessDBFeature('supports_partial_indexes')
    def test_move_to_root_cannot_duplicate_name(self):
        Folder.objects.create(name='same')
        parent = Folder.objects.create(name='parent')
        child = Folder.objects.create(name='same', parent=parent)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Folder.objects.filter(pk=child.pk).update(parent=None)

    def test_creation_handles_name_taken_after_validation(self):
        for parent in (None, Folder.objects.create(name='parent')):
            if parent is None and not connection.features.supports_partial_indexes:
                continue
            with self.subTest(parent=parent):
                def take_name(name):
                    Folder.objects.create(name=name, parent=parent)
                    return False

                target = Folder if parent else FolderRoot
                data = {'name': 'raced'}
                if parent:
                    data['parent_id'] = parent.pk
                with patch.object(target, 'contains_folder', side_effect=take_name):
                    response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'), data)
                self.assertContains(response, 'Folder with this name already exists.')
                self.assertEqual(Folder.objects.filter(parent=parent, name='raced').count(), 1)

    def test_creation_does_not_hide_unrelated_integrity_errors(self):
        with patch.object(Folder, 'save', side_effect=IntegrityError('unrelated')):
            with self.assertRaisesMessage(IntegrityError, 'unrelated'):
                self.client.post(reverse('admin:filer-directory_listing-make_root_folder'), {'name': 'new'})

    def test_copy_retries_without_merging_into_concurrent_folder(self):
        source = Folder.objects.create(name='source', owner=self.user)
        Folder.objects.create(name='child', parent=source)
        destination = Folder.objects.create(name='destination')
        original = self.folder_admin._get_available_name
        for owner in (self.user, None):
            with self.subTest(owner=owner):
                destination.children.all().delete()
                winners = []

                def take_name(parent, name):
                    available = original(parent, name)
                    if not winners:
                        winners.append(Folder.objects.create(name=available, parent=parent, owner=owner))
                    return available

                with patch.object(self.folder_admin, '_get_available_name', side_effect=take_name):
                    self.assertEqual(self.folder_admin._copy_folder(source, destination, '', False), 2)
                self.assertFalse(winners[0].children.exists())
                copied = destination.children.get(name='source_1')
                self.assertEqual(copied.owner, self.user)
                self.assertEqual(copied.children.get().name, 'child')

    def test_copy_does_not_retry_unrelated_integrity_errors(self):
        source = Folder.objects.create(name='source')
        destination = Folder.objects.create(name='destination')
        with patch.object(Folder, 'save', side_effect=IntegrityError('unrelated')):
            with self.assertRaisesMessage(IntegrityError, 'unrelated'):
                self.folder_admin._copy_folder(source, destination, '', False)

    def test_move_conflict_rolls_back_files_and_returns_error(self):
        source = Folder.objects.create(name='source')
        child = Folder.objects.create(name='child', parent=source)
        destination = Folder.objects.create(name='destination')
        file = File.objects.create(name='file', folder=source)
        original = FolderAdmin._move_files_and_folders_impl

        def take_name(instance, files, folders, target):
            Folder.objects.create(name=child.name, parent=target)
            return original(instance, files, folders, target)

        with patch.object(FolderAdmin, '_move_files_and_folders_impl', new=take_name):
            response = self.client.post(
                reverse('admin:filer-directory_listing', kwargs={'folder_id': source.pk}),
                {'action': 'move_files_and_folders', 'post': 'yes', 'destination': destination.pk,
                 helpers.ACTION_CHECKBOX_NAME: [f'file-{file.pk}', f'folder-{child.pk}']},
                follow=True,
            )
        self.assertContains(response, 'already exist at the selected destination')
        file.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(file.folder, source)
        self.assertEqual(child.parent, source)


@skipUnlessDBFeature('supports_partial_indexes')
class RootMigrationTests(TransactionTestCase):
    def test_existing_duplicates_require_manual_resolution(self):
        executor = MigrationExecutor(connection)
        before = [('filer', '0018_alter_file_options')]
        after = [('filer', '0019_unique_root_folder_name')]
        executor.migrate(before)
        old_folder = executor.loader.project_state(before).apps.get_model('filer', 'Folder')
        try:
            old_folder.objects.create(name='duplicate')
            duplicate = old_folder.objects.create(name='duplicate')
            executor = MigrationExecutor(connection)
            with self.assertRaisesMessage(RuntimeError, 'Rename the conflicting root folders'):
                executor.migrate(after)
            duplicate.name = 'renamed'
            duplicate.save()
            executor.migrate(after)
            with self.assertRaises(IntegrityError), transaction.atomic():
                old_folder.objects.create(name='duplicate')
        finally:
            old_folder.objects.all().delete()
            MigrationExecutor(connection).migrate(after)
