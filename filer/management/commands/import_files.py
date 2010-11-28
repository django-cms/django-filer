import os
from optparse import make_option

from django.core.management.base import BaseCommand, NoArgsCommand
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.filemodels import File
from filer.models.imagemodels import Image

from filer.settings import FILER_IS_PUBLIC_DEFAULT

class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path')
        self.verbosity = int(kwargs.get('verbosity', 1))
        self.file_created = 0
        self.image_created = 0
        self.folder_created = 0
    
    def import_file(self, file, folder):
        """
        Create a File or an Image into the given folder
        
        """
        try:
            iext = os.path.splitext(file.name)[1].lower()
        except:
            iext = ''
        if iext in ['.jpg', '.jpeg', '.png', '.gif']:
            obj, created = Image.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.image_created += 1
        else:
            obj, created = File.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.file_created += 1
        if self.verbosity >= 2:
            print u"file_created #%s / image_created #%s -- file : %s -- created : %s" % (self.file_created,
                                                        self.image_created,
                                                        obj, created)  
        return obj
    
    def root_folder(self, root):
        """
        Retrieve or create the root folder.
        """
        name = os.path.basename(root)
        if root != self.path:
            parent_name = os.path.basename(os.path.dirname(root))
        else:
            parent_name = None
        obj, created = Folder.objects.get_or_create(parent__name=parent_name,
                                                    name=name)
        if self.verbosity >= 2:
            print u"root : %s -- created : %s" % (obj, created) 
        return obj
    
    def create_folder(self, parent, name):
        """
        Retrieve or create a folder.
        """
        obj, created = Folder.objects.get_or_create(name=name, parent=parent)
        self.folder_created += 1
        
        if self.verbosity >= 2:
            print u"folder_created #%s folder : %s -- created : %s" % (self.folder_created,
                                                                       obj, created) 
        return obj
            
    def walker(self, path=None):
        """
        This method walk a directory structure and create the
        Folders and Files as they appear.
        """
        path = path or self.path
        # prevent trailing slashes and other inconsistencies on path.
        # cast to unicode so that os.walk returns path names in unicode
        # (prevents encoding/decoding errors)
        path = unicode(os.path.normpath(path))
        if self.verbosity >= 1:
            print u"Import the folders and files in %s" % path
        for root, dirs, files in os.walk(path):
            root_folder = self.root_folder(root)
            #print  files , "files"
            for file in files:
                dj_file = DjangoFile(open(os.path.join(root, file)),
                                     name=file)
                self.import_file(file=dj_file, folder=root_folder)
            for dir in dirs:
                self.create_folder(parent=root_folder, name=dir)
        if self.verbosity >= 1:
            print u"folder_created #%s / file_created #%s / image_created #%s "% (self.folder_created,
                                                                                 self.file_created,
                                                                                 self.image_created)

class Command(NoArgsCommand):
    option_list = BaseCommand.option_list + (
        make_option('--path',
            action='store',
            dest='path',
            default=False,
            help='Import files located in the path into django-filer'),
        )

    def handle_noargs(self, **options):
        file_importer = FileImporter(**options)
        file_importer.walker()
