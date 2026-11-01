from contextlib import nullcontext

from django.db import IntegrityError, migrations, models, transaction
from django.db.models import Count, Q


def check_duplicate_roots(apps, schema_editor):
    if not schema_editor.connection.features.supports_partial_indexes:
        return
    Folder = apps.get_model('filer', 'Folder')
    duplicates = (Folder.objects.using(schema_editor.connection.alias)
                  .filter(parent__isnull=True).order_by().values('name')
                  .annotate(total=Count('pk')).filter(total__gt=1))
    if duplicates.exists():
        raise RuntimeError(
            'Duplicate root folder names exist. Rename the conflicting root folders '
            'before applying filer migration 0019_unique_root_folder_name.'
        )


class AddRootFolderNameConstraint(migrations.AddConstraint):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        connection = schema_editor.connection
        # Recover the transaction before querying after a failed DDL statement.
        # Backends without transactional DDL must execute outside a savepoint.
        context = (
            transaction.atomic(using=connection.alias)
            if connection.features.can_rollback_ddl and not schema_editor.collect_sql
            else nullcontext()
        )
        try:
            with context:
                super().database_forwards(app_label, schema_editor, from_state, to_state)
        except IntegrityError:
            # A root name may have been duplicated since the initial check.
            check_duplicate_roots(to_state.apps, schema_editor)
            raise


class Migration(migrations.Migration):
    dependencies = [('filer', '0018_alter_file_options')]

    operations = [
        migrations.RunPython(check_duplicate_roots, migrations.RunPython.noop),
        AddRootFolderNameConstraint(
            model_name='folder',
            constraint=models.UniqueConstraint(
                fields=['name'], condition=Q(parent__isnull=True),
                name='filer_unique_root_folder_name',
            ),
        ),
    ]
