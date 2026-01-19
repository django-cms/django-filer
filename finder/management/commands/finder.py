from django.contrib.admin.sites import all_sites
from django.contrib.sites.models import Site
from django.core.files.storage import storages
from django.core.management.base import BaseCommand
from django.db.models.fields.related import ForeignKey, ManyToManyField

from finder.models.ambit import AmbitModel
from finder.models.file import FileModel as FinderFileModel
from finder.models.folder import FolderModel as FinderFolderModel, ROOT_FOLDER_NAME
from finder.models.inode import InodeModel


class Command(BaseCommand):
    help = "Finder management command."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand', required=True)
        subparsers.add_parser('reorganize', help="Iterates over all files and assign them to the model specfic to their mime-type.")
        subparsers.add_parser('reorder', help="Set order value for each file in all folders.")
        add_ambit_parser = subparsers.add_parser('add-root', help="Add named tree root.")
        add_ambit_parser.add_argument('slug', action='store', type=str)
        add_ambit_parser.add_argument('--values', action='store', nargs='*', type=str)
        edit_ambit_parser = subparsers.add_parser('edit-root', help="Edit named tree root.")
        edit_ambit_parser.add_argument('slug', action='store', type=str)
        edit_ambit_parser.add_argument('--values', action='store', nargs='*', type=str)
        delete_ambit_parser = subparsers.add_parser('delete-root', help="Delete named tree root.")
        delete_ambit_parser.add_argument('slug', action='store', type=str)

    def handle(self, verbosity, *args, **options):
        self.verbosity = verbosity

        subcommand = options.pop('subcommand', '')
        if subcommand == 'reorganize':
            self.reorganize()
        elif subcommand == 'reorder':
            self.reorder()
        elif subcommand == 'add-root':
            try:
                self.add_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while adding tree root: ‘{exc}’")
        elif subcommand == 'edit-root':
            try:
                self.edit_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while change tree root: ‘{exc}’")
        elif subcommand == 'delete-root':
            try:
                self.edit_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while deleting tree root: ‘{exc}’")
        else:
            self.stderr.write(f"Unknown subcommand ‘{subcommand}’")

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

    def add_ambit(self, **options):
        slug = options.pop('slug')
        values = dict(keyval.split('=') for keyval in options['values'])
        values['verbose_name'] = values.pop('name')
        if 'site' in values:
            values['site'] = Site.objects.get(id=values['site'])
        if admin_name := values.pop('admin', None):
            for admin_site in all_sites:
                if admin_site.name == admin_name:
                    values['admin_name'] = admin_name
                    break
            else:
                raise KeyError(f"No such admin site ‘{admin_name}’.")
        storage_name = values.pop('storage')
        if storage_name in storages.backends:
            values['_original_storage'] = storage_name
        storage_name = values.pop('sample_storage')
        if storage_name in storages.backends:
            values['_sample_storage'] = storage_name
        root_folder = FinderFolderModel.objects.create(name=ROOT_FOLDER_NAME)
        AmbitModel.objects.create(root_folder=root_folder, slug=slug, **values)
        self.stdout.write(f"Successfully created tree root with slug ‘{slug}’.")

    def edit_ambit(self, **options):
        slug = options.pop('slug')
        values = dict(keyval.split('=') for keyval in options['values'])
        if 'name' in values:
            values['verbose_name'] = values.pop('name')
        if 'site' in values:
            values['site'] = Site.objects.get(id=values['site'])
        if admin_name := values.pop('admin', None):
            for admin_site in all_sites:
                if admin_site.name == admin_name:
                    values['admin_name'] = admin_name
                    break
            else:
                raise KeyError(f"No such admin site ‘{admin_name}’.")
        if storage_name := values.pop('storage', None):
            if storage_name in storages.backends:
                values['_original_storage'] = storage_name
        if storage_name := values.pop('sample_storage', None):
            if storage_name in storages.backends:
                values['_sample_storage'] = storage_name
        if AmbitModel.objects.filter(slug=slug).update(**values) == 1:
            self.stdout.write(f"Successfully updated tree root with slug ‘{slug}’.")

    def delete_ambit(self, **options):
        slug = options.pop('slug')
        if AmbitModel.objects.filter(slug=slug).delete() == 1:
            self.stdout.write(f"Successfully deleted tree root with slug ‘{slug}’.")
