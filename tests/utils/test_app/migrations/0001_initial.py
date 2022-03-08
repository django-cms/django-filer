import django.db.models.deletion
from django.db import migrations, models

import filer.fields.file
import filer.fields.folder
import filer.fields.image
from filer.settings import FILER_IMAGE_MODEL


class Migration(migrations.Migration):

    if FILER_IMAGE_MODEL.startswith('custom_image'):
        dependencies = [
            ('filer', '0001_initial'),
            ('custom_image', '0001_initial'),
        ]
    else:
        dependencies = [
            ('filer', '0001_initial'),
        ]

    operations = [
        migrations.CreateModel(
            name='MyModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('folder', filer.fields.folder.FilerFolderField(related_name='test_folder', to='filer.Folder', on_delete=django.db.models.deletion.CASCADE)),
                ('general', filer.fields.file.FilerFileField(related_name='test_file', to='filer.File', on_delete=django.db.models.deletion.CASCADE)),
                ('image', filer.fields.image.FilerImageField(related_name='test_image', to=FILER_IMAGE_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
