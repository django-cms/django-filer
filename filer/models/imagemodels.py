#-*- coding: utf-8 -*-
import logging

try:
    from PIL import Image as PILImage
except ImportError:
    try:
        import Image as PILImage
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from datetime import datetime
from django.core import urlresolvers
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.filer_easy_thumbnails import FilerThumbnailer
from filer.utils.pil_exif import get_exif_for_file
import os

logger = logging.getLogger("filer")

class Image(File):
    SIDEBAR_IMAGE_WIDTH = 210
    DEFAULT_THUMBNAILS = {
        'admin_clipboard_icon': {'size': (32, 32), 'crop': True,
                                 'upscale': True},
        'admin_sidebar_preview': {'size': (SIDEBAR_IMAGE_WIDTH, 10000)},
        'admin_directory_listing_icon': {'size': (48, 48),
                                         'crop': True, 'upscale': True},
        'admin_tiny_icon': {'size': (32, 32), 'crop': True, 'upscale': True},
    }
    file_type = 'Image'
    _icon = "image"

    _height = models.IntegerField(null=True, blank=True)
    _width = models.IntegerField(null=True, blank=True)

    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                      editable=False)

    default_alt_text = models.CharField(_('default alt text'), max_length=255, blank=True, null=True)
    default_caption = models.CharField(_('default caption'), max_length=255, blank=True, null=True)

    author = models.CharField(_('author'), max_length=255, null=True, blank=True)

    must_always_publish_author_credit = models.BooleanField(_('must always publish author credit'), default=False)
    must_always_publish_copyright = models.BooleanField(_('must always publish copyright'), default=False)

    subject_location = models.CharField(_('subject location'), max_length=64, null=True, blank=True,
                                        default=None)

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
      # This was originally in admin/clipboardadmin.py  it was inside of a try
      # except, I have moved it here outside of a try except because I can't
      # figure out just what kind of exception this could generate... all it was
      # doing for me was obscuring errors...
      # --Dave Butler <croepha@gmail.com>
      iext = os.path.splitext(iname)[1].lower()
      return iext in ['.jpg', '.jpeg', '.png', '.gif']

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(
                                       int(year), int(month), int(day),
                                       int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = datetime.now()
        self.has_all_mandatory_data = self._check_validity()
        try:
            # do this more efficient somehow?
            self.file.seek(0)
            self._width, self._height = PILImage.open(self.file).size
        except Exception:
            # probably the image is missing. nevermind.
            pass
        super(Image, self).save(*args, **kwargs)

    def _check_validity(self):
        if not self.name:
            return False
        return True

    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width) / float(self.SIDEBAR_IMAGE_WIDTH)
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

    def has_generic_permission(self, request, permission_type):
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
            return self.folder.has_generic_permission(request, permission_type)
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
                    'size': (int(size), int(size)),
                    'crop': True,
                    'upscale': True,
                    'subject_location': self.subject_location}
                thumb = self.file.get_thumbnail(thumbnail_options)
                _icons[size] = thumb.url
            except Exception, e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while generating icons: %s',e)
                if filer_settings.FILER_DEBUG:
                    raise e
        return _icons

    @property
    def thumbnails(self):
        _thumbnails = {}
        for name, opts in Image.DEFAULT_THUMBNAILS.items():
            try:
                opts.update({'subject_location': self.subject_location})
                thumb = self.file.get_thumbnail(opts)
                _thumbnails[name] = thumb.url
            except Exception,e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while generating thumbnail: %s',e)
                if filer_settings.FILER_DEBUG:
                    raise e
        return _thumbnails

    @property
    def easy_thumbnails_thumbnailer(self):
        tn = FilerThumbnailer(
            file=self.file.file, name=self.file.name,
            source_storage=self.file.source_storage,
            thumbnail_storage=self.file.thumbnail_storage,
            thumbnail_basedir=self.file.thumbnail_basedir)
        return tn

    class Meta:
        app_label = 'filer'
        verbose_name = _('image')
        verbose_name_plural = _('images')
