import os
from django.core.management.base import NoArgsCommand
from filer.models.videomodels import Video


class Command(NoArgsCommand):
    help = "Deletes video formats that no longer have an original file."
    requires_model_validation = False

    def handle_noargs(self, **options):
        self.clean_up()

    def clean_up(self):
        top = None
        for field in Video._meta.fields:
            if field.name == 'file':
                for storage in field.format_storages:
                    original_storage = field.storages[storage]
                    format_storage = field.format_storages[storage]
                    top = format_storage.location
                    for root, dirs, files in os.walk(top, topdown=False):
                        subpath = os.path.relpath(root, top)
                        orig_dirs, orig_files = original_storage.listdir(subpath)
                        orig_files = set([os.path.basename(of) for of in orig_files])
                        files = set([os.path.basename(f) for f in files])
                        for f in files.difference(orig_files):
                            p = format_storage.path(os.path.join(subpath, f))
                            os.remove(p)
