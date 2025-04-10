import os

from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from PIL import UnidentifiedImageError

from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.loader import load_model


class Command(BaseCommand):
    help = "Check for orphaned files, missing file references, and set image dimensions."

    def add_arguments(self, parser):
        parser.add_argument(
            '--orphans',
            action='store_true',
            dest='orphans',
            default=False,
            help="Scan media folders for orphaned files.",
        )
        parser.add_argument(
            '--delete-orphans',
            action='store_true',
            dest='delete_orphans',
            default=False,
            help="Delete orphaned files from storage.",
        )
        parser.add_argument(
            '--missing',
            action='store_true',
            dest='missing',
            default=False,
            help="Check file references and report missing files.",
        )
        parser.add_argument(
            '--delete-missing',
            action='store_true',
            dest='delete_missing',
            default=False,
            help="Delete database entries if files are missing in the media folder.",
        )
        parser.add_argument(
            '--image-dimensions',
            action='store_true',
            dest='image_dimensions',
            default=False,
            help="Set image dimensions if they are not set.",
        )
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            default=True,
            help="Do not prompt the user for any interactive input.",
        )

    def handle(self, *args, **options):
        if options['missing']:
            self.verify_references(options)
        if options['delete_missing']:
            if options['interactive']:
                if input(
                    "\nThis will delete missing file references from the database.\n"
                    "Type 'yes' to continue, or 'no' to cancel: "
                ) != 'yes':
                    self.stdout.write("Aborted: Missing file references were not deleted.\n")
                    self.stdout.flush()
                    return
            self.verify_references(options)

        if options['orphans'] or options['delete_orphans']:
            if options['delete_orphans'] and options['interactive']:
                if input(
                    "\nThis will delete orphaned files from storage.\n"
                    "Type 'yes' to continue, or 'no' to cancel: "
                ) != 'yes':
                    self.stdout.write("Aborted: Orphaned files were not deleted.\n")
                    self.stdout.flush()
                    return
            self.verify_storages(options)

        if options['image_dimensions']:
            self.image_dimensions(options)

    def verify_references(self, options):
        """
        Checks that every file reference in the database exists in storage.
        If a file is missing, either report it or delete the reference based on the provided options.
        """
        for file in File.objects.all():
            if not file.file.storage.exists(file.file.name):
                if options['delete_missing']:
                    file.delete()
                    verbose_msg = f"Deleted missing file reference '{file.folder}/{file}' from the database."
                else:
                    verbose_msg = f"File reference '{file.folder}/{file}' is missing in storage."
                if options.get('verbosity', 1) > 2:
                    self.stdout.write(verbose_msg + "\n")
                    self.stdout.flush()
                elif options.get('verbosity'):
                    self.stdout.write(os.path.join(str(file.folder), str(file)) + "\n")
                    self.stdout.flush()

    def verify_storages(self, options):
        """
        Scans all storages defined in FILER_STORAGES (e.g., public and private)
        for orphaned files, then reports or deletes them based on the options.
        """

        def walk(storage, prefix, label_prefix):
            # If the directory does not exist, there is nothing to scan
            if not storage.exists(prefix):
                return
            child_dirs, files = storage.listdir(prefix)
            for filename in files:
                actual_path = os.path.join(prefix, filename)
                relfilename = os.path.join(label_prefix, filename)
                if not File.objects.filter(file=actual_path).exists():
                    if options['delete_orphans']:
                        storage.delete(actual_path)
                        message = f"Deleted orphaned file '{relfilename}'"
                    else:
                        message = f"Found orphaned file '{relfilename}'"
                    if options.get('verbosity', 1) > 2:
                        self.stdout.write(message + "\n")
                        self.stdout.flush()
                    elif options.get('verbosity'):
                        self.stdout.write(relfilename + "\n")
                        self.stdout.flush()
            for child in child_dirs:
                walk(storage, os.path.join(prefix, child), os.path.join(label_prefix, child))

        # Loop through each storage configuration (e.g., public, private, etc.)
        for storage_name, storage_config in filer_settings.FILER_STORAGES.items():
            storage_settings = storage_config.get('main')
            if not storage_settings:
                continue
            storage = import_string(storage_settings['ENGINE'])()
            if storage_settings.get('OPTIONS', {}).get('location'):
                storage.location = storage_settings['OPTIONS']['location']
            # Set label_prefix: for public and private storages, use their names.
            label_prefix = storage_name if storage_name in ['public', 'private'] else storage_settings.get('UPLOAD_TO_PREFIX', '')
            walk(storage, storage_settings.get('UPLOAD_TO_PREFIX', ''), label_prefix)

    def image_dimensions(self, options):
        """
        For images without set dimensions (_width == 0 or None), try to read their dimensions
        and save them, handling SVG files and possible image errors.
        """
        from django.db.models import Q

        import easy_thumbnails
        from easy_thumbnails.VIL import Image as VILImage

        from filer.utils.compatibility import PILImage

        ImageModel = load_model(filer_settings.FILER_IMAGE_MODEL)
        images_without_dimensions = ImageModel.objects.filter(Q(_width=0) | Q(_width__isnull=True))
        self.stdout.write(f"Setting dimensions for {images_without_dimensions.count()} images" + "\n")
        self.stdout.flush()
        for image in images_without_dimensions:
            file_holder = image.file_ptr if getattr(image, 'file_ptr', None) else image
            try:
                imgfile = file_holder.file
                imgfile.seek(0)
            except FileNotFoundError:
                continue
            if image.file.name.lower().endswith('.svg'):
                # For SVG files, use VILImage (invalid SVGs do not throw errors)
                with VILImage.load(imgfile) as vil_image:
                    image._width, image._height = vil_image.size
            else:
                try:
                    with PILImage.open(imgfile) as pil_image:
                        image._width, image._height = pil_image.size
                        image._transparent = easy_thumbnails.utils.is_transparent(pil_image)
                except UnidentifiedImageError:
                    continue
            image.save()
