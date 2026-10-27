from django.db import migrations, models
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


class Migration(migrations.Migration):
    dependencies = [('filer', '0018_alter_file_options')]

    operations = [
        migrations.RunPython(check_duplicate_roots, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.UniqueConstraint(
                fields=['name'], condition=Q(parent__isnull=True),
                name='filer_unique_root_folder_name',
            ),
        ),
    ]
