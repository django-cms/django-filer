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
from django.urls import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
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
    _filename_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.ico']

    _height = models.IntegerField(null=True, blank=True)
    _width = models.IntegerField(null=True, blank=True)

    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                      editable=False)

    default_alt_text = models.CharField(
        _('default alt text'), max_length=255, blank=True, null=True,
        help_text=_('Describes the essence of the image for users who have '
                    'images turned off in their browser, or are visually '
                    'impaired and using a screen reader; and it is used to '
                    'identify images to search engines.'))
    default_caption = models.CharField(
        _('default caption'), max_length=255, blank=True, null=True,
        help_text=_('Caption text is displayed directly below an image '
                    'plugin to add context; there is a 140-character limit,'
                    ' including spaces; for images fewer than 200 pixels '
                    'wide, the caption text is only displayed on hover.'))
    default_credit = models.CharField(
        _('default credit text'), max_length=255, blank=True, null=True,
        help_text=_('Credit text gives credit to the owner or licensor of '
                    'an image; it is displayed below the image plugin, or '
                    'below the caption text on an image plugin, if that '
                    'option is selected; it is displayed along the bottom '
                    'of an image in the photo gallery plugin; there is a '
                    '30-character limit, including spaces.'))

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
      return iext in Image._filename_extensions

    def clean(self):
        if self.default_credit:
            self.default_credit = self.default_credit.strip()
        if self.default_alt_text:
            self.default_alt_text = self.default_alt_text.strip()
        if self.default_caption:
            self.default_caption = self.default_caption.strip()

        if len(self.default_credit or '') > 30:
            raise ValidationError(
                "Ensure default credit text has at most 30 characters ("
                "%s characters found)." % len(self.default_credit))
        if len(self.default_caption or '') > 140:
            raise ValidationError(
                "Ensure default caption text has at most 140 characters ("
                "%s characters found)." % len(self.default_caption))
        super(Image, self).clean()

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    if getattr(settings, "USE_TZ", False):
                        tz = timezone.get_current_timezone()
                        self.date_taken = timezone.make_aware(datetime(
                            int(year), int(month), int(day),
                            int(hour), int(minute), int(second)), tz)
                    else:
                        self.date_taken = datetime(
                            int(year), int(month), int(day),
                            int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = timezone.now()
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

    def _generate_thumbnails(self, required_thumbnails):
        _thumbnails = {}
        if self.is_in_trash():
            return _thumbnails
        for name, opts in list(required_thumbnails.items()):
            try:
                opts.update({'subject_location': self.subject_location})
                thumb = self.file.get_thumbnail(opts)
                _thumbnails[name] = thumb.url
            except Exception as e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while generating thumbnail: %s',e)
                if filer_settings.FILER_DEBUG:
                    raise e
        return _thumbnails

    @property
    def icons(self):
        required_thumbnails = dict(
            (size, {'size': (int(size), int(size)),
                    'crop': True,
                    'upscale': True,
                    'subject_location': self.subject_location})
            for size in filer_settings.FILER_ADMIN_ICON_SIZES)
        return self._generate_thumbnails(required_thumbnails)

    @property
    def thumbnails(self):
        return self._generate_thumbnails(Image.DEFAULT_THUMBNAILS)

    @property
    def easy_thumbnails_thumbnailer(self):
        return self.file

    class Meta:
        app_label = 'filer'
        verbose_name = _('image')
        verbose_name_plural = _('images')
