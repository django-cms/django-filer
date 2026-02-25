from django.contrib.auth import get_user_model

from django.contrib.admin.sites import all_sites
from django.contrib.sites.models import Site
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from django.db.models.fields.related import ForeignKey, ManyToManyField

from finder.models.ambit import AmbitModel
from finder.models.file import FileModel as FinderFileModel
from finder.models.folder import FolderModel as FinderFolderModel, ROOT_FOLDER_NAME
from finder.models.inode import InodeManager, InodeModel
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege


class Command(BaseCommand):
    help = "Finder management command."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand', required=True)
        reorganize_parser = subparsers.add_parser('reorganize', help="Iterates over all files and assign them to the model specfic to their mime-type.")
        reorganize_parser.add_argument('slug', action='store', type=str)
        reorder_parser = subparsers.add_parser('reorder', help="Set order values for each file in all folders.")
        reorder_parser.add_argument('slug', action='store', type=str)
        subparsers.add_parser('list-ambits', help="List all configured ambits.")
        add_ambit_parser = subparsers.add_parser('add-ambit', help="Add a named ambit to hold tree roots.")
        add_ambit_parser.add_argument('slug', action='store', type=str)
        add_ambit_parser.add_argument('--values', action='store', nargs='*', type=str)
        edit_ambit_parser = subparsers.add_parser('edit-ambit', help="Edit a named ambit.")
        edit_ambit_parser.add_argument('slug', action='store', type=str)
        edit_ambit_parser.add_argument('--values', action='store', nargs='*', type=str)
        delete_ambit_parser = subparsers.add_parser('delete-ambit', help="Delete a named ambit.")
        delete_ambit_parser.add_argument('slug', action='store', type=str)
        delete_ambit_parser.add_argument('--erase-files', action='store_true', help="Erase files from storage.")

    def handle(self, verbosity, *args, **options):
        self.verbosity = verbosity

        subcommand = options.pop('subcommand', '')
        if subcommand == 'reorganize':
            self.reorganize(**options)
        elif subcommand == 'reorder':
            self.reorder(**options)
        elif subcommand == 'list-ambits':
            self.list_ambits()
        elif subcommand == 'add-ambit':
            try:
                self.add_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while adding ambit: ‘{exc}’")
        elif subcommand == 'edit-ambit':
            try:
                self.edit_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while changing ambit: ‘{exc}’")
        elif subcommand == 'delete-ambit':
            try:
                self.delete_ambit(**options)
            except Exception as exc:
                self.stderr.write(f"Error while deleting ambit: ‘{exc}’")
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

    def reorder(self, **options):
        self.stdout.write("Reorder files in django-filer (finder branch)")
        sum_reorders = 0
        for folder in FinderFolderModel.objects.all():
            num_reorders = folder.reorder()
            if self.verbosity > 1 and num_reorders > 0:
                sum_reorders += num_reorders
                self.stdout.write(f"Reordered {num_reorders} items in folder ‘{folder}’.")
        if sum_reorders == 0:
            self.stdout.write("No folder required any reordering.")

    def list_ambits(self):
        for ambit in AmbitModel.objects.all():
            self.stdout.write(f"Slug: {ambit.slug}, Name: {ambit.verbose_name}, Site: {ambit.site}, Admin: {ambit.admin_name}, Storage: {ambit.original_storage}, Sample Storage: {ambit.sample_storage}")

    def add_ambit(self, **options):
        slug = options.pop('slug')
        values = dict(keyval.split('=') for keyval in options['values'])
        values['verbose_name'] = values.pop('name', slug.capitalize())
        if 'site' in values:
            values['site'] = Site.objects.get(id=values['site'])
        if admin_name := values.pop('admin', None):
            for admin_site in all_sites:
                if admin_site.name == admin_name:
                    values['admin_name'] = admin_name
                    break
            else:
                raise CommandError(f"No such admin site ‘{admin_name}’.")
        storage_name = values.pop('storage', None)
        if storage_name not in storages.backends:
            raise CommandError(f"Storage backend ‘{storage_name}’ is not configured.")
        values['_original_storage'] = storage_name
        storage_name = values.pop('sample_storage', None)
        if storage_name not in storages.backends:
            raise CommandError(f"Storage backend ‘{storage_name}’ is not configured.")
        values['_sample_storage'] = storage_name
        root_folder = FinderFolderModel.objects.create(name=ROOT_FOLDER_NAME)
        # create ACL and default ACL with RW-permission for everyone
        AccessControlEntry.objects.create(inode=root_folder.id, privilege=Privilege.READ_WRITE)
        DefaultAccessControlEntry.objects.create(folder=root_folder, privilege=Privilege.READ_WRITE)
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
                raise CommandError(f"No such admin site ‘{admin_name}’.")
        if storage_name := values.pop('storage', None):
            if storage_name in storages.backends:
                values['_original_storage'] = storage_name
        if storage_name := values.pop('sample_storage', None):
            if storage_name in storages.backends:
                values['_sample_storage'] = storage_name
        if AmbitModel.objects.filter(slug=slug).update(**values) == 1:
            self.stdout.write(f"Successfully updated tree root with slug ‘{slug}’.")

    def delete_ambit(self, **options):
        def delete_recursive(folder):
            for subfolder in folder.subfolders.all():
                delete_recursive(subfolder)
            for file in folder.listdir(is_folder=False):
                proxy_obj = InodeManager.get_proxy_object(file)
                if erase_files:
                    proxy_obj.erase_and_delete(ambit)
                else:
                    proxy_obj.delete()
            folder.delete()

        slug = options.pop('slug')
        ambit = AmbitModel.objects.get(slug=slug)
        erase_files = options.get('erase_files', False)
        delete_recursive(ambit.root_folder)
        ambit.delete()
        self.stdout.write(f"Successfully deleted tree root with slug ‘{slug}’.")
