from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0005_default_alt_text_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='Image',
            name='default_caption',
            field=models.TextField(null=True), # Use TextField to allow unlimited length
        ),
    ]