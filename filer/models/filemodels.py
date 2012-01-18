import os
import hashlib
from django.utils.translation import ugettext_lazy as _
from django.core import urlresolvers
from django.db import models
from django.contrib.auth import models as auth_models

from django.conf import settings
from filer.models.filer_file_storage import get_directory_name
from filer.models.foldermodels import Folder
from filer.models import mixins
from filer import settings as filer_settings

from easy_thumbnails.fields import ThumbnailerField

class FileManager(models.Manager):
    def find_all_duplicates(self):
        r = {}
        for file in self.all():
            if file.sha1:
                q = self.filter(sha1=file.sha1)
                if len(q) > 1:
                    r[file.sha1] = [i.subtype() for i in q]
        return r
    def find_duplicates(self, file):
        return [i.subtype() for i in self.exclude(pk=file.pk).filter(sha1=file.sha1)]

class File(models.Model, mixins.IconsMixin):
    _icon = "file"
    folder = models.ForeignKey(Folder, related_name='all_files', null=True, blank=True, verbose_name=_('folder'))
    file = ThumbnailerField(upload_to=get_directory_name, null=True, blank=True, max_length=255, verbose_name=_('file'))
    _file_type_plugin_name = models.CharField("file_type_plugin_name", max_length=128, null=True, blank=True, editable=False)
    _file_size = models.IntegerField(null=True, blank=True)
    
    sha1 = models.CharField(max_length=40, blank=True, default='')
    
    has_all_mandatory_data = models.BooleanField(default=False, editable=False)
    
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('name'))
    description = models.TextField(null=True, blank=True, verbose_name=_('description'))
    
    owner = models.ForeignKey(auth_models.User, related_name='owned_%(class)ss', null=True, blank=True, verbose_name=_('Owner'))
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    is_public = models.BooleanField(default=False, verbose_name=_('is public'))
    
    objects = FileManager()
    
    def __init__(self, *args, **kwargs):
        super(File, self).__init__(*args, **kwargs)
        self._old_is_public = self.is_public
        
    def delete_thumbnails(self):
        """
        Delete all the thumbnails related to `instance.file`
        """
        for thumb in self.file.get_source_cache().thumbnails.all():
            os.remove(os.path.join(settings.MEDIA_ROOT, thumb.name))
            thumb.delete()
            
    def _move_file(self, src_filer_prefix, dst_filer_prefix):
        """
        Move the file from src to dst. If `os.dirname(dst)` does not exist it
        creates all the required directory.
        """
        src = self.file.name
        dst = src.replace(src_filer_prefix,
                           dst_filer_prefix)
        new_name = self.file.storage.save(dst, self.file)
        self.file.delete(save=False)
        self.file = new_name
    
    def generate_sha1(self):
        sha = hashlib.sha1()
        self.file.seek(0)
        sha.update(self.file.read())
        self.sha1 = sha.hexdigest()
    
    def save(self, *args, **kwargs):
        # check if this is a subclass of "File" or not and set
        # _file_type_plugin_name
        if self.__class__ == File:
            # what should we do now?
            # maybe this has a subclass, but is being saved as a File instance
            # anyway. do we need to go check all possible subclasses?
            pass
        elif issubclass(self.__class__, File):
            self._file_type_plugin_name = self.__class__.__name__
        # cache the file size
        try:
            self._file_size = self.file.size
        except:
            pass
        if self._old_is_public != self.is_public and \
                                  self.pk:
            if self.is_public:
                self._move_file(filer_settings.FILER_PRIVATEMEDIA_PREFIX,
                               filer_settings.FILER_PUBLICMEDIA_PREFIX)
            else:
                self._move_file(filer_settings.FILER_PUBLICMEDIA_PREFIX,
                               filer_settings.FILER_PRIVATEMEDIA_PREFIX)
            self._old_is_public = self.is_public
        try:
            self.generate_sha1()
        except Exception,e:
            print e, type(3)
        super(File, self).save(*args, **kwargs)

    @property
    def label(self):
        if self.name in ['', None]:
            text = self.original_filename or 'unnamed file'
        else:
            text = self.name
        text = u"%s" % (text,)
        return text
    
    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')
    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')
    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')
    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        image. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated() or not user.is_staff:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, type)
        else:
            return False
    
    def __unicode__(self):
        if self.name in ('', None):
            text = u"%s" % (self.original_filename,)
        else:
            text = u"%s" % (self.name,)
        return text

    
    def subtype(self):
        #print "get subtype"
        if not self._file_type_plugin_name:
            r = self
        else:
            try:
                r = getattr(self, self._file_type_plugin_name.lower())
            except Exception, e:
                #print e
                r = self
        #print u"get subtype: %s %s" % (r, self._file_type_plugin_name)
        return r
    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_file_change', args=(self.id,))
    @property
    def url(self):
        '''
        to make the model behave like a file field
        '''
        try:
            r = self.file.url
        except:
            r = ''
        return r
    @property
    def path(self):
        try:
            return self.file.path
        except:
            return ""
    @property
    def size(self):
        return self._file_size or 0
    
    @property
    def logical_folder(self):
        """
        if this file is not in a specific folder return the Special "unfiled"
        Folder object
        """
        if not self.folder:
            from filer.models.virtualitems import UnfiledImages
            return UnfiledImages()
        else:
            return self.folder
    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.folder:
            folder_path.extend(self.folder.get_ancestors())
        folder_path.append(self.logical_folder)
        return folder_path
    @property
    def duplicates(self):
        return File.objects.find_duplicates(self)
    
    class Meta:
        app_label = 'filer'
        verbose_name = _('File')
        verbose_name_plural = _('Files')
