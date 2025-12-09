from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models.fields.related import ForeignKey, ManyToManyField

from finder.models.file import FileModel as FinderFileModel
from finder.models.folder import FolderModel as FinderFolderModel
from finder.models.inode import InodeModel


class Command(BaseCommand):
    help = "Iterates over all files and assign them to the model specfic to their mime-type."

    def add_arguments(self, parser):
        parser.add_argument('subcommand', action='store', nargs='+', type=str)

    def handle(self, verbosity, subcommand, *args, **options):
        self.verbosity = verbosity
        for subcmd in subcommand:
            if subcmd == 'reorganize':
                self.reorganize()
            elif subcmd == 'reorder':
                self.reorder()
            else:
                self.stderr.write(f"Unknown subcommand ‘{subcmd}’")

    def reorganize(self):
        self.stdout.write("Reorganize files in django-filer (finder branch)")
        for inode_model in InodeModel.get_models():
            for file in inode_model.objects.all():
                file_model = FinderFileModel.objects.get_model_for(file.mime_type)
                if not issubclass(file_model, file.__class__):
                    self.stdout.write(f"Reorganize file ‘{file}’")
                    if not file_model.objects.filter(id=file.id).exists():
                        kwargs = {}
                        for attr in file._meta.get_fields():
                            if isinstance(attr, ForeignKey):
                                kwargs[attr.name] = getattr(file, attr.name)
                            elif not isinstance(attr, ManyToManyField):
                                kwargs[attr.name] = attr.value_from_object(file)
                        file_model.objects.create(**kwargs)
                    file.delete()

    def reorder(self):
        self.stdout.write("Reorder files in django-filer (finder branch)")
        sum_reorders = 0
        for folder in FinderFolderModel.objects.all():
            num_reorders = folder.reorder()
            if num_reorders > 0:
                sum_reorders += num_reorders
                self.stdout.write(f"Reordered {num_reorders} inodes in folder ‘{folder}’.")
        if sum_reorders == 0:
            self.stdout.write("No folder required any reordering.")
