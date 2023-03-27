from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0004_unique_clipboard_per_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='Image',
            name='default_alt_text',
            field=models.TextField(), # Use TextField to allow unlimited length
        ),
    ]