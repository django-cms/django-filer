from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_image', '0002_auto_20160621_1510'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='image',
            options={'verbose_name': 'image', 'verbose_name_plural': 'images'},
        ),
        migrations.AlterField(
            model_name='image',
            name='file_ptr',
            field=models.OneToOneField(primary_key=True, serialize=False, related_name='custom_image_image_file', parent_link=True, to='filer.File', on_delete=models.CASCADE),
        ),
    ]
    operations += [
        migrations.AlterModelOptions(
            name='image',
            options={'default_manager_name': 'objects', 'verbose_name': 'image', 'verbose_name_plural': 'images'},
        ),
    ]
