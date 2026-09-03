"""
Create the ambit a project starts out with.

Without one, the first form rendering a finder widget fails with
``AmbitModel.DoesNotExist``. Set ``FINDER_CREATE_DEFAULT_AMBIT = False`` before applying
this migration to configure the ambits by hand with ``manage.py finder add-ambit``.
"""

from django.conf import settings
from django.db import migrations, router

# `finder.models.folder.ROOT_FOLDER_NAME` at the time of this migration. Spelled out
# rather than imported, so that a later rename cannot rewrite history.
ROOT_FOLDER_NAME = '__root__'

# `finder.models.permission.Privilege.READ_WRITE`
PRIVILEGE_READ_WRITE = 3


def create_default_ambit(apps, schema_editor):
    if not getattr(settings, 'FINDER_CREATE_DEFAULT_AMBIT', True):
        return

    using = schema_editor.connection.alias
    AmbitModel = apps.get_model('finder', 'AmbitModel')
    if not router.allow_migrate_model(using, AmbitModel):
        return
    if AmbitModel.objects.using(using).exists():
        return

    FolderModel = apps.get_model('finder', 'FolderModel')
    AccessControlEntry = apps.get_model('finder', 'AccessControlEntry')
    DefaultAccessControlEntry = apps.get_model('finder', 'DefaultAccessControlEntry')

    # read from django.conf so a test can override it, but fall back to finder's own
    # default rather than repeating it here
    from finder.settings import FINDER_DEFAULT_AMBIT

    slug = getattr(settings, 'FINDER_DEFAULT_AMBIT', FINDER_DEFAULT_AMBIT)
    root_folder = FolderModel.objects.using(using).create(name=ROOT_FOLDER_NAME)
    AmbitModel.objects.using(using).create(
        root_folder=root_folder,
        slug=slug,
        verbose_name=slug.capitalize(),
    )
    # grant read/write to everyone, as `manage.py finder add-ambit` does
    AccessControlEntry.objects.using(using).create(
        inode=root_folder.id,
        privilege=PRIVILEGE_READ_WRITE,
    )
    DefaultAccessControlEntry.objects.using(using).create(
        folder=root_folder,
        privilege=PRIVILEGE_READ_WRITE,
    )


def remove_default_ambit(apps, schema_editor):
    """
    Reversing this migration deliberately keeps the ambit.

    By the time it is reversed the root folder may hold files, and the file models live in
    the `finder.contrib.*` applications, which this migration cannot see. Rather than risk
    orphaning payloads in storage, the row is left behind; re-applying the migration finds
    an ambit and does nothing.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('finder', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_ambit, remove_default_ambit),
    ]
