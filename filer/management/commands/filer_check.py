import os

from django.core.files.storage import DefaultStorage
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from filer import settings as filer_settings


class Command(BaseCommand):
    help = "Look for orphaned files in media folders."
    storage = DefaultStorage()
    prefix = filer_settings.FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX']

    def add_arguments(self, parser):
        parser.add_argument(
            '--orphans',
            action='store_true',
            dest='orphans',
            default=False,
            help="Walk through the media folders and look for orphaned files.",
        )
        parser.add_argument(
            '--delete-orphans',
            action='store_true',
            dest='delete_orphans',
            default=False,
            help="Delete orphaned files from their media folders.",
        )
        parser.add_argument(
            '--missing',
            action='store_true',
            dest='missing',
            default=False,
            help="Verify media folders and report about missing files.",
        )
        parser.add_argument(
            '--delete-missing',
            action='store_true',
            dest='delete_missing',
            default=False,
            help="Delete references in database if files are missing in media folder.",
        )
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            default=True,
            help="Do NOT prompt the user for input of any kind."
        )

    def handle(self, *args, **options):
        if options['missing']:
            self.verify_references(options)
        if options['delete_missing']:
            if options['interactive']:
                msg = "\nThis will delete entries from your database. Are you sure you want to do this?\n\n" \
                      "Type 'yes' to continue, or 'no' to cancel: "
                if input(msg) != 'yes':
                    self.stdout.write("Aborted: Delete missing file entries from database.")
                    return
            self.verify_references(options)

        if options['orphans']:
            self.verify_storages(options)
        if options['delete_orphans']:
            if options['interactive']:
                msg = "\nThis will delete orphaned files from your storage. Are you sure you want to do this?\n\n" \
                      "Type 'yes' to continue, or 'no' to cancel: "
                if input(msg) != 'yes':
                    self.stdout.write("Aborted: Delete orphaned files from storage.")
                    return
            self.verify_storages(options)

    def verify_references(self, options):
        from filer.models.filemodels import File

        for file in File.objects.all():
            if not file.file.storage.exists(file.file.name):
                if options['delete_missing']:
                    file.delete()
                    msg = "Delete missing file reference '{}/{}' from database."
                else:
                    msg = "Referenced file '{}/{}' is missing in media folder."
                if options['verbosity'] > 2:
                    self.stdout.write(msg.format(str(file.folder), str(file)))
                elif options['verbosity']:
                    self.stdout.write(os.path.join(str(file.folder), str(file)))

    def verify_storages(self, options):
        from filer.models.filemodels import File

        def walk(prefix):
            child_dirs, files = storage.listdir(prefix)
            for filename in files:
                relfilename = os.path.join(prefix, filename)
                if not File.objects.filter(file=relfilename).exists():
                    if options['delete_orphans']:
                        storage.delete(relfilename)
                        msg = "Deleted orphaned file '{}'"
                    else:
                        msg = "Found orphaned file '{}'"
                    if options['verbosity'] > 2:
                        self.stdout.write(msg.format(relfilename))
                    elif options['verbosity']:
                        self.stdout.write(relfilename)

            for child in child_dirs:
                walk(os.path.join(prefix, child))

        filer_public = filer_settings.FILER_STORAGES['public']['main']
        storage = import_string(filer_public['ENGINE'])()
        walk(filer_public['UPLOAD_TO_PREFIX'])
