from django.core.management.base import BaseCommand
from django.db.models.fields.related import ForeignKey, ManyToManyField

from finder.models.file import FileModel
from finder.models.inode import InodeModel


class Command(BaseCommand):
    help = "Iterates over all files and assign them to the model specfic to their mime-type."

    def handle(self, verbosity, *args, **options):
        self.verbosity = verbosity
        self.stdout.write("Reorganize files in django-filer (finder branch)")
        self.reorganize()

    def reorganize(self):
        for inode_model in InodeModel.concrete_inode_models:
            if inode_model.is_folder:
                continue
            for file in inode_model.objects.all():
                file_model = FileModel.objects.get_model_for(file.mime_type)
                if not issubclass(file_model, file.__class__):
                    self.stdout.write(f"Reorganize file {file}")
                    if not file_model.objects.filter(id=file.id).exists():
                        kwargs = {}
                        for attr in file._meta.get_fields():
                            if isinstance(attr, ForeignKey):
                                kwargs[attr.name] = getattr(file, attr.name)
                            elif not isinstance(attr, ManyToManyField):
                                kwargs[attr.name] = attr.value_from_object(file)
                        file_model.objects.create(**kwargs)
                    file.delete()
