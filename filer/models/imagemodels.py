from datetime import datetime
from PIL import Image as PILImage

from django.utils.translation import ugettext_lazy as _
from django.core import urlresolvers
from django.db import models
from easy_thumbnails.files import Thumbnailer
from filer.models.filemodels import File
from filer.utils.pil_exif import get_exif_for_file
from filer import settings as filer_settings
from django.conf import settings



class Image(File):
    SIDEBAR_IMAGE_WIDTH = 210
    DEFAULT_THUMBNAILS = {
        'admin_clipboard_icon': {'size': (32,32), 'crop':True, 'upscale':True},
        'admin_sidebar_preview': {'size': (SIDEBAR_IMAGE_WIDTH,10000),},
        'admin_directory_listing_icon': {'size': (48,48), 'crop':True, 'upscale':True},
        'admin_tiny_icon': {'size': (32,32), 'crop':True, 'upscale':True},
    }
    file_type = 'image'
    _icon = "image"
    
    _height = models.IntegerField(null=True, blank=True) 
    _width = models.IntegerField(null=True, blank=True)
    
    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True, editable=False)
    
    default_alt_text = models.CharField(max_length=255, blank=True, null=True)
    default_caption = models.CharField(max_length=255, blank=True, null=True)
    
    author = models.CharField(max_length=255, null=True, blank=True)
    
    must_always_publish_author_credit = models.BooleanField(default=False)
    must_always_publish_copyright = models.BooleanField(default=False)
    
    subject_location = models.CharField(max_length=64, null=True, blank=True, default=None)
    
    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(int(year), int(month), int(day),
                                               int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = datetime.now()
        self.has_all_mandatory_data = self._check_validity()
        try:
            # do this more efficient somehow?
            self._width, self._height = PILImage.open(self.file).size
        except Exception, e:
            # probably the image is missing. nevermind.
            pass
        
        super(Image, self).save(*args, **kwargs)    
    
    def _check_validity(self):
        if not self.name:# or not self.contact:
            return False
        return True
    
    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width)/float(self.SIDEBAR_IMAGE_WIDTH)
        else:
            return 1.0
        

        
    def _get_exif(self):
        if hasattr(self, '_exif_cache'):
            return self._exif_cache
        else:
            if self.file:
                self._exif_cache = get_exif_for_file(self.file.path)
            else:
                self._exif_cache = {}
        return self._exif_cache
    exif = property(_get_exif)
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
    @property
    def label(self):
        if self.name in ['', None]:
            return self.original_filename or 'unnamed file'
        else:
            return self.name
    @property
    def width(self):
        return self._width or 0
    @property
    def height(self):
        return self._height or 0
    @property
    def icons(self):
        _icons = {}
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            try:
                thumbnail_options = {
                    'size':(int(size),int(size)),
                    'crop': True,
                    'upscale':True,
                    }
                thumb = self.file.get_thumbnail(thumbnail_options)
                _icons[size] = thumb.url
            except Exception, e:
                # swallow the the exception to avoid to bubble it up
                # in the template {{ image.icons.48 }}
                pass
        return _icons
        
    @property
    def thumbnails(self):
        _thumbnails = {}
        for name, opts in Image.DEFAULT_THUMBNAILS.items():
            try:
                _thumbnails[name] = self.file.get_thumbnail(opts).url
            except:
                # swallow the the exception to avoid to bubble it up
                # in the template {{ image.icons.48 }}
                pass
        return _thumbnails
    
    @property
    def absolute_image_url(self):
        return self.url
    @property
    def rel_image_url(self):
        'return the image url relative to MEDIA_URL'
        try:
            rel_url = u"%s" % self.file.url
            if rel_url.startswith(settings.MEDIA_URL):
                before, match, rel_url = rel_url.partition(settings.MEDIA_URL)
            return rel_url
        except Exception, e:
            return ''
    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_image_change', args=(self.id,))
    @property
    def easy_thumbnails_relative_name(self):
        """
        Return the relative url of the image so easy_thumbnails<=1.0-alpha-16 can work with this model as
        if it were a file field.
        """
        return self.rel_image_url

    @property
    def easy_thumbnails_thumbnailer(self):
        """
        Return the relative url of the image so easy_thumbnails>=1.0-alpha-17 can work with this model as
        if it were a file field.
        """
        tn = Thumbnailer(file=self.file.file, name=self.file.name,
                         source_storage=self.file.source_storage,
                         thumbnail_storage=self.file.thumbnail_storage)
        return tn

    class Meta:
        app_label = 'filer'
        verbose_name = _('Image')
        verbose_name_plural = _('Images')
