from pathlib import Path

from django.contrib.admin import site
from django.core.management.base import BaseCommand

from filer.models.filemodels import Folder as FilerFolder
from filer.models.imagemodels import Image as FilerImage

from finder.models.file import FileModel as FinderFile
from finder.models.folder import FolderModel as FinderFolder
from finder.contrib.image.models import ImageModel as FinderImage


class Command(BaseCommand):
    help = "Migrate files from django-filer to finder branch."

    def handle(self, verbosity, *args, **options):
        self.verbosity = verbosity
        self.stdout.write("Migrate django-filer to version 4 (Finder)")
        self.forward()

    def forward(self):
        for filer_folder in FilerFolder.objects.filter(parent__isnull=True):
            self.migrate_folder(filer_folder, FinderFolder.objects.get_root_folder(site))

    def migrate_folder(self, filer_folder, finder_parent):
        try:
            finder_folder = next(finder_parent.listdir(name=filer_folder.name, is_folder=True))
        except StopIteration:
            finder_folder = FinderFolder.objects.create(
                name=filer_folder.name,
                parent=finder_parent,
                created_at=filer_folder.created_at,
                last_modified_at=filer_folder.modified_at,
                owner_id=filer_folder.owner_id,
            )
            self.stdout.write(f"Create folder {finder_folder} in {finder_parent}")

        allowed_image_types = ['image/gif', 'image/jpeg', 'image/png', 'image/webp', 'image/svg+xml']
        for filer_file in filer_folder.files.all():
            if isinstance(filer_file, FilerImage) and filer_file.mime_type in allowed_image_types:
                self.migrate_image(filer_file, finder_folder)
            else:
                self.migrate_file(filer_file, finder_folder)

        for child in filer_folder.children.all():
            self.migrate_folder(child, finder_folder)

    def migrate_file(self, filer_file, finder_parent):
        path = Path(filer_file.file.name)
        inode_id = path.parent.stem
        try:
            finder_file = next(FinderFile.objects.filter_inodes(id=inode_id))
        except StopIteration:
            FinderFile.objects.create(
                id=inode_id,
                name=filer_file.name if filer_file.name else filer_file.original_filename,
                file_name=path.name,
                parent=finder_parent,
                created_at=filer_file.uploaded_at,
                last_modified_at=filer_file.modified_at,
                sha1=filer_file.sha1,
                mime_type=filer_file.mime_type,
                file_size=filer_file._file_size,
                owner_id=filer_file.owner_id,
            )
        else:
            if filer_file.modified_at > finder_file.last_modified_at:
                finder_file.name = filer_file.name if filer_file.name else filer_file.original_filename
                finder_file.file_name = path.name
                finder_file.last_modified_at = filer_file.modified_at
                finder_file.sha1 = filer_file.sha1
                finder_file.mime_type = filer_file.mime_type
                finder_file.file_size = filer_file._file_size
                finder_file.owner_id = filer_file.owner_id
                finder_file.save()

    def migrate_image(self, filer_image, finder_parent):
        path = Path(filer_image.file.name)
        inode_id = path.parent.stem
        meta_data = {'alt_text': getattr(filer_image, 'default_alt_text', '')}
        try:
            center_x, center_y = map(float, filer_image.subject_location.split(','))
            # since Filer does not store the area of interest, we assume it is 10px
            meta_data['crop_x'] = center_x - 5
            meta_data['crop_y'] = center_y - 5
            meta_data['crop_size'] = 10
        except ValueError:
            pass
        try:
            finder_image = next(FinderImage.objects.filter_inodes(id=inode_id))
        except StopIteration:
            FinderImage.objects.create(
                id=inode_id,
                name=filer_image.name if filer_image.name else filer_image.original_filename,
                file_name=path.name,
                parent=finder_parent,
                created_at=filer_image.uploaded_at,
                last_modified_at=filer_image.modified_at,
                sha1=filer_image.sha1,
                mime_type=filer_image.mime_type,
                file_size=filer_image._file_size,
                owner_id=filer_image.owner_id,
                width=filer_image.width,
                height=filer_image.height,
                meta_data=meta_data,
            )
        else:
            if True or filer_image.modified_at > finder_image.last_modified_at:
                finder_image.name = filer_image.name if filer_image.name else filer_image.original_filename
                finder_image.file_name = path.name
                finder_image.last_modified_at = filer_image.modified_at
                finder_image.sha1 = filer_image.sha1
                finder_image.mime_type = filer_image.mime_type
                finder_image.file_size = filer_image._file_size
                finder_image.owner_id = filer_image.owner_id
                finder_image.width = filer_image.width
                finder_image.height = filer_image.height
                finder_image.meta_data.update(meta_data)
                finder_image.save()
