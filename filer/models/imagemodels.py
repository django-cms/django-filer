import os
import StringIO
from datetime import datetime, date
from django.utils.translation import ugettext_lazy as _
from django.core import urlresolvers
from django.db import models
from django.contrib.auth import models as auth_models
from filer.models.filemodels import File
from filer.utils.pil_exif import get_exif_for_file, set_exif_subject_location
from filer.settings import FILER_ADMIN_ICON_SIZES, FILER_PUBLICMEDIA_PREFIX, FILER_PRIVATEMEDIA_PREFIX, FILER_STATICMEDIA_PREFIX
from django.conf import settings

from sorl.thumbnail.main import DjangoThumbnail, build_thumbnail_name
from sorl.thumbnail.fields import ALL_ARGS

from PIL import Image as PILImage

class Image(File):
    SIDEBAR_IMAGE_WIDTH = 210
    DEFAULT_THUMBNAILS = {
        'admin_clipboard_icon': {'size': (32,32), 'options': ['crop','upscale']},
        'admin_sidebar_preview': {'size': (SIDEBAR_IMAGE_WIDTH,10000), 'options': []},
        'admin_directory_listing_icon': {'size': (48,48), 'options': ['crop','upscale']},
        'admin_tiny_icon': {'size': (32,32), 'options': ['crop','upscale']},
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
    
    def _check_validity(self):
        if not self.name:# or not self.contact:
            return False
        return True
    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width)/float(self.SIDEBAR_IMAGE_WIDTH)
        else:
            return 1.0
    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal',None)
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
        #if not self.contact:
        #    self.contact = self.owner
        self.has_all_mandatory_data = self._check_validity()
        try:
            if self.subject_location:
                parts = self.subject_location.split(',')
                pos_x = int(parts[0])
                pos_y = int(parts[1])
                                                  
                sl = (int(pos_x), int(pos_y) )
                exif_sl = self.exif.get('SubjectLocation', None)
                if self._file and not sl == exif_sl:
                    #self._file.open()
                    fd_source = StringIO.StringIO(self._file.read())
                    #self._file.close()
                    set_exif_subject_location(sl, fd_source, self._file.path)
        except:
            # probably the image is missing. nevermind
            pass
        try:
            # do this more efficient somehow?
            self._width, self._height = PILImage.open(self._file).size
        except Exception, e:
            # probably the image is missing. nevermind.
            pass
        super(Image, self).save(*args, **kwargs)
        
    def _get_exif(self):
        if hasattr(self, '_exif_cache'):
            return self._exif_cache
        else:
            if self._file:
                self._exif_cache = get_exif_for_file(self._file.path)
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
        if self.name in ['',None]:
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
        if not getattr(self, '_icon_thumbnails_cache', False):
            r = {}
            for size in FILER_ADMIN_ICON_SIZES:
                try:
                    args = {'size': (int(size),int(size)), 'options': ['crop','upscale']}
                    # Build the DjangoThumbnail kwargs.
                    kwargs = {}
                    for k, v in args.items():
                        kwargs[ALL_ARGS[k]] = v
                    # Build the destination filename and return the thumbnail.
                    name_kwargs = {}
                    for key in ['size', 'options', 'quality', 'basedir', 'subdir',
                                'prefix', 'extension']:
                        name_kwargs[key] = args.get(key)
                    source = self._file
                    dest = build_thumbnail_name(source.name, **name_kwargs)
                    r[size] = unicode(DjangoThumbnail(source, relative_dest=dest, **kwargs))
                except Exception, e:
                    pass
            setattr(self, '_icon_thumbnails_cache', r)
        return getattr(self, '_icon_thumbnails_cache')
    def _build_thumbnail(self, args):
        try:
            # Build the DjangoThumbnail kwargs.
            kwargs = {}
            for k, v in args.items():
                kwargs[ALL_ARGS[k]] = v
            # Build the destination filename and return the thumbnail.
            name_kwargs = {}
            for key in ['size', 'options', 'quality', 'basedir', 'subdir',
                        'prefix', 'extension']:
                name_kwargs[key] = args.get(key)
            source = self._file
            dest = build_thumbnail_name(source.name, **name_kwargs)
            return DjangoThumbnail(source, relative_dest=dest, **kwargs)
        except:
            return os.path.normpath(u"%s/icons/missingfile_%sx%s.png" % (FILER_STATICMEDIA_PREFIX, 32, 32,))
    @property
    def thumbnails(self):
        # we build an extra dict here mainly
        # to prevent the default errors to 
        # get thrown and to add a default missing
        # image (not yet)
        if not hasattr(self, '_thumbnails'):
            tns = {}
            for name, opts in Image.DEFAULT_THUMBNAILS.items():
                tns[name] = unicode(self._build_thumbnail(opts))
            self._thumbnails = tns
        return self._thumbnails
    
    @property
    def absolute_image_url(self):
        return self.url
    @property
    def rel_image_url(self):
        'return the image url relative to MEDIA_URL'
        try:
            rel_url = u"%s" % self._file.url
            if rel_url.startswith(settings.MEDIA_URL):
                before, match, rel_url = rel_url.partition(settings.MEDIA_URL)
            return rel_url
        except Exception, e:
            return ''
    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_image_change', args=(self.id,))
    def __unicode__(self):
        # this simulates the way a file field works and
        # allows the sorl thumbnail tag to use the Image model
        # as if it was a image field
        return self.rel_image_url
    class Meta:
        app_label = 'filer'
        verbose_name = _('Image')
        verbose_name_plural = _('Images')
