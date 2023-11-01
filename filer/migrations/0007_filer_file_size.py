from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('filer', '0006_default_caption_text_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='File',
            name='file',
            field=models.MultiStorageFileField(max_length=1024),
        ),
    ]
