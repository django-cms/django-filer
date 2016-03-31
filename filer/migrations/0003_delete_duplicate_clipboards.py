# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def delete_extra_clipboards(apps, schema_editor):
    """
    Delete duplicate clipboards (keep the one with the most files) so a unique
    user constraint can be added.
    """
    User = apps.get_model("auth", "User")

    users = (User.objects.all()
             .annotate(nr_clipboards=models.Count('filer_clipboards'))
             .filter(nr_clipboards__gt=1))

    if not users:
        print "Nobody has more than one clipboard. Nothing to do here."
        return

    for user in users:
        clipboards = user.filer_clipboards.all()
        print "Removing duplicate clipboards for {}, id {} (has {})".format(
            user, user.id, len(clipboards))
        clipboard_to_stay = max(clipboards, key=lambda c: c.clipboarditem_set.all().count())
        for clipboard in clipboards:
            if clipboard != clipboard_to_stay:
                print "Deleting clipboard with id {}".format(clipboard.id)
                clipboard.delete()


def show_rollback_info_message(apps, schema_editor):
    print "Clipboards do not need to be changed."


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0002_auto_20150928_1109'),
    ]

    operations = [
        migrations.RunPython(delete_extra_clipboards,
                             show_rollback_info_message)
    ]
