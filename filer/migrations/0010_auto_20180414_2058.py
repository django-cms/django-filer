import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0009_auto_20171220_1635'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='file_ptr',
            field=models.OneToOneField(primary_key=True, serialize=False, related_name='filer_image_file', parent_link=True, to='filer.File', on_delete=django.db.models.deletion.CASCADE, auto_created=False),
        ),
    ]
