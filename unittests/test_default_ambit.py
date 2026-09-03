"""
The data migration which gives a fresh project a usable ambit, and the system checks
guarding its configuration.
"""

from importlib import import_module
from pathlib import Path

import pytest

from django.apps import apps as global_apps
from django.db import connection

from finder.models.ambit import AmbitModel
from finder.models.folder import FolderModel, ROOT_FOLDER_NAME
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege
from finder import checks
from finder.settings import FINDER_DEFAULT_AMBIT

migration = import_module('finder.migrations.0002_default_ambit')

pytestmark = pytest.mark.django_db


class FakeSchemaEditor:
    """`RunPython` hands the operation a schema editor; only its connection is used."""
    connection = connection


def apply_migration():
    migration.create_default_ambit(global_apps, FakeSchemaEditor)


class TestCreateDefaultAmbit:

    def test_it_creates_a_usable_ambit(self, settings):
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        assert not AmbitModel.objects.exists()
        apply_migration()

        ambit = AmbitModel.objects.get()
        assert ambit.slug == FINDER_DEFAULT_AMBIT
        assert ambit.verbose_name == FINDER_DEFAULT_AMBIT.capitalize()
        assert ambit.root_folder.name == ROOT_FOLDER_NAME
        assert ambit.root_folder.is_root
        # the root folder is usable straight away, as after `manage.py finder add-ambit`
        assert AccessControlEntry.objects.filter(
            inode=ambit.root_folder.id, privilege=Privilege.READ_WRITE,
        ).exists()
        assert DefaultAccessControlEntry.objects.filter(
            folder=ambit.root_folder, privilege=Privilege.READ_WRITE,
        ).exists()

    def test_an_existing_ambit_is_left_alone(self, settings, ambit):
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        apply_migration()
        assert list(AmbitModel.objects.values_list('slug', flat=True)) == [ambit.slug]

    def test_it_is_idempotent(self, settings):
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        apply_migration()
        apply_migration()
        assert AmbitModel.objects.count() == 1
        assert FolderModel.objects.filter(name=ROOT_FOLDER_NAME).count() == 1

    def test_the_opt_out_is_honoured(self, settings):
        settings.FINDER_CREATE_DEFAULT_AMBIT = False
        apply_migration()
        assert not AmbitModel.objects.exists()

    def test_it_uses_the_default_storage_aliases(self, settings):
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        apply_migration()
        ambit = AmbitModel.objects.get()
        assert ambit._original_storage == 'finder_public'
        assert ambit._sample_storage == 'finder_public_samples'

    def test_the_slug_follows_the_setting(self, settings):
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        settings.FINDER_DEFAULT_AMBIT = 'public'
        apply_migration()
        assert AmbitModel.objects.get().slug == 'public'

    def test_reversing_keeps_the_ambit(self, settings):
        """Files may already live in the root folder, so the reverse operation is a no-op."""
        settings.FINDER_CREATE_DEFAULT_AMBIT = True
        apply_migration()
        migration.remove_default_ambit(global_apps, FakeSchemaEditor)
        assert AmbitModel.objects.count() == 1

    def test_the_migration_is_reversible(self):
        """A `RunPython` without a reverse callable would block `migrate finder 0001`."""
        operation = migration.Migration.operations[0]
        assert operation.reversible


class TestSystemChecks:
    """
    The checks validate settings only. They deliberately do not report a missing ambit:
    a check runs before `migrate`, against a database which may not exist yet.
    """

    def test_a_valid_slug_passes(self):
        from finder import checks

        assert checks.check_default_ambit_slug(None) == []

    def test_an_unusable_slug_is_an_error(self, monkeypatch):
        from finder import checks

        monkeypatch.setattr(checks, 'FINDER_DEFAULT_AMBIT', 'not a slug')
        assert [error.id for error in checks.check_default_ambit_slug(None)] == ['finder.E001']

    def test_derived_storages_raise_no_warning(self):
        from finder import checks

        assert checks.check_ambit_storages(None) == []

    def test_the_checks_are_registered(self):
        from django.core.checks import registry

        registered = {check.__name__ for check in registry.registry.get_checks()}
        assert {'check_default_ambit_slug', 'check_ambit_storages'} <= registered


class TestDerivedStorages:
    """
    `finder_public` and `finder_public_samples` are derived from the `default` storage
    when the project does not declare them, so that an ambit always refers to a
    `FinderSystemStorage`. A plain one would not shard payloads by UUID.
    """

    def test_the_aliases_resolve(self):
        from django.core.files.storage import storages
        from finder.storages import FinderSystemStorage

        for alias in ['finder_public', 'finder_public_samples']:
            assert isinstance(storages[alias], FinderSystemStorage)

    def test_they_live_below_the_default_storage(self, settings):
        from django.core.files.storage import storages

        storage = storages['finder_public']
        assert storage.location == str(Path(settings.MEDIA_ROOT) / 'finder_public')
        assert storage.base_url == f"{settings.MEDIA_URL.rstrip('/')}/finder_public/"

    def test_overwriting_is_allowed(self):
        from django.core.files.storage import storages

        assert storages['finder_public']._allow_overwrite is True

    def test_payloads_are_sharded(self):
        from django.core.files.storage import storages

        name = 'e5298124-fd37-4248-905a-654a302e4a7e/img.png'
        assert storages['finder_public'].path(name).endswith(
            'finder_public/e5/29/e5298124-fd37-4248-905a-654a302e4a7e/img.png'
        )

    def test_a_declared_storage_is_left_alone(self, settings):
        from finder.storages import configure_default_storages

        settings.STORAGES = {
            **settings.STORAGES,
            'finder_public': settings.STORAGES['finder_test'],
            'finder_public_samples': settings.STORAGES['finder_test_samples'],
        }
        assert configure_default_storages() == []

    def test_a_remote_default_cannot_be_derived_from(self, settings):
        """Only a filesystem default carries a location to put a subdirectory under."""
        from finder.storages import configure_default_storages

        storages_setting = {k: v for k, v in settings.STORAGES.items()
                            if k not in ['finder_public', 'finder_public_samples']}
        storages_setting['default'] = {'BACKEND': 'django.core.files.storage.InMemoryStorage'}
        settings.STORAGES = storages_setting
        assert configure_default_storages() == []
        assert [warning.id for warning in checks.check_ambit_storages(None)] == ['finder.W001']
