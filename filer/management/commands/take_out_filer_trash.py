from django.core.management.base import BaseCommand
# make sure cms is loaded first
import cms
from filer.models import File, Folder
from filer import settings as filer_settings
from datetime import datetime, timedelta


class Command(BaseCommand):

    help = "Hard-deletes old files and folders from filer trash."

    def handle(self, *args, **options):
        no_of_sec = filer_settings.FILER_TRASH_CLEAN_INTERVAL
        time_threshold = datetime.now() - timedelta(seconds=no_of_sec)
        files_ids = File.trash.filter(deleted_at__lt=time_threshold)\
            .values_list('id', flat=True)
        folder_ids = Folder.trash.filter(deleted_at__lt=time_threshold)\
            .order_by('tree_id', '-level').values_list('id', flat=True)

        if not folder_ids and not files_ids:
            self.stdout.write("No old files or folders.\n")
            return

        for file_id in files_ids:
            a_file = File.trash.get(id=file_id)
            self.stdout.write("Deleting file %s: %s\n" % (
                file_id, repr(a_file.file.name)))
            try:
                a_file.delete(to_trash=False)
            except Exception as e:
                self.stderr.write("%s\n" % str(e))

        for folder_id in folder_ids:
            a_folder = Folder.trash.get(id=folder_id)
            ancestors = a_folder.get_ancestors(include_self=True)
            path = repr('/'.join(ancestors.values_list('name', flat=True)))
            if File.all_objects.filter(folder=folder_id).exists():
                self.stdout.write("Cannot delete folder %s: %s since is "
                                  "not empty.\n" % (folder_id, path))
                continue
            self.stdout.write(
                "Deleting folder %s: %s\n" % (folder_id, path))
            try:
                a_folder.delete(to_trash=False)
            except Exception as e:
                self.stderr.write("%s\n" % str(e))
