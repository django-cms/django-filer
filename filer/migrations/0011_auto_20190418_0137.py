# Generated by Django 2.2 on 2019-04-25 11:29
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0010_auto_20180414_2058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='level',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='folder',
            name='lft',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='folder',
            name='rght',
            field=models.PositiveIntegerField(editable=False),
        ),
        # migrations.AlterIndexTogether(
        #     name='folder',
        #     index_together={('tree_id', 'lft')},
        # ),
    ]
