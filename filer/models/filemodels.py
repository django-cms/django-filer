from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth import models as auth_models

from django.conf import settings
from filer.models.safe_file_storage import SafeFilenameFileSystemStorage
from filer.models.foldermodels import Folder
from filer import context_processors

fs = SafeFilenameFileSystemStorage()

IMAGE_FILER_UPLOAD_ROOT = getattr(settings,'IMAGE_FILER_UPLOAD_ROOT', 'catalogue')
DEFAULT_ICON_SIZES = (
        '32','48','64',
)
    

class File(models.Model):
    _icon = "file"
    folder = models.ForeignKey(Folder, related_name='files', null=True, blank=True)
    file_field = models.FileField(upload_to=IMAGE_FILER_UPLOAD_ROOT, storage=fs, null=True, blank=True,max_length=255)
    _file_type = models.CharField(null=True, blank=True, max_length=16)
    _file_size = models.IntegerField(null=True, blank=True)
    has_all_mandatory_data = models.BooleanField(default=False, editable=False)
    
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    
    owner = models.ForeignKey(auth_models.User, related_name='owned_%(class)ss', null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    # TODO: Factor out customer specific fields... maybe a m2m?
    #can_use_for_web = models.BooleanField(default=True)
    #can_use_for_print = models.BooleanField(default=True)
    #can_use_for_teaching = models.BooleanField(default=True)
    #can_use_for_research = models.BooleanField(default=True)
    #can_use_for_private_use = models.BooleanField(default=True)
    #usage_restriction_notes = models.TextField(null=True, blank=True)
    #notes = models.TextField(null=True, blank=True)
    #contact = models.ForeignKey(auth_models.User, related_name='contact_of_files', null=True, blank=True)
    
    @property
    def label(self):
        if self.name in ['',None]:
            return self.original_filename or 'unnamed file'
        else:
            return self.name
    
    @property
    def icons(self):
        print "icons"
        r = {}
        if getattr(self, '_icon', False):
            for size in DEFAULT_ICON_SIZES:
                print "   %s" % (size,)
                print "   %s" % context_processors.media(None)['FILER_MEDIA_URL']
                r[size] = "%sicons/%s_%sx%s.png" % (context_processors.media(None)['FILER_MEDIA_URL'], self._icon, size, size)
        print r
        return r
    
    def __unicode__(self):
        if self.name in ('', None):
            text = u"%s" % (self.original_filename,)
        else:
            text = u"%s" % (self.name,)
        return text
    
    class Meta:
        app_label = 'filer'