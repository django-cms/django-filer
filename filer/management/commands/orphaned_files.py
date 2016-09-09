# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import DefaultStorage
from filer.settings import DEFAULT_FILER_STORAGES


class Command(BaseCommand):
    help = _("Look for orphaned files in media folders.")
    storage = DefaultStorage()
    prefix = DEFAULT_FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX']

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help=_("Delete found orphaned files in media folders."),
        )

    def handle(self, *args, **options):
        from filer.models.filemodels import File

        def walk(absdir, reldir):
            child_dirs, files = self.storage.listdir(absdir)
            for filename in files:
                relfilename = os.path.join(reldir, filename)
                try:
                    File.objects.get(file=relfilename)
                except File.DoesNotExist:
                    absfilename = os.path.join(absdir, filename)
                    if options['delete']:
                        self.storage.delete(absfilename)
                        msg = _("Deleted orphanded file '{filename}'")
                    else:
                        msg = _("Found orphanded file '{filename}'")
                    if options['verbosity']:
                        self.stdout.write(msg.format(filename=absfilename))

            for child in child_dirs:
                walk(os.path.join(absdir, child), os.path.join(reldir, child))

        walk(os.path.join(settings.MEDIA_ROOT, self.prefix), self.prefix)
