import logging

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.VIL import Image as VILImage

from .. import settings as filer_settings
from ..utils.compatibility import PILImage
from ..utils.filer_easy_thumbnails import FilerThumbnailer
from ..utils.pil_exif import get_exif_for_file
from .filemodels import File


logger = logging.getLogger(__name__)


class BaseImage(File):
    SIDEBAR_IMAGE_WIDTH = 210
    DEFAULT_THUMBNAILS = {
        'admin_clipboard_icon': {'size': (32, 32), 'crop': True,
                                 'upscale': True},
        'admin_sidebar_preview': {'size': (SIDEBAR_IMAGE_WIDTH, 0), 'upscale': True},
        'admin_directory_listing_icon': {'size': (48, 48),
                                         'crop': True, 'upscale': True},
        'admin_tiny_icon': {'size': (32, 32), 'crop': True, 'upscale': True},
    }
    file_type = 'Image'
    _icon = "image"

    _height = models.FloatField(
        null=True,
        blank=True,
    )

    _width = models.FloatField(
        null=True,
        blank=True,
    )

    default_alt_text = models.CharField(
        _("default alt text"),
        max_length=255,
        blank=True,
        null=True,
    )

    default_caption = models.CharField(
        _("default caption"),
        max_length=255,
        blank=True,
        null=True,
    )

    subject_location = models.CharField(
        _("subject location"),
        max_length=64,
        blank=True,
        default='',
    )

    file_ptr = models.OneToOneField(
        to='filer.File',
        parent_link=True,
        related_name='%(app_label)s_%(class)s_file',
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'filer'
        verbose_name = _("image")
        verbose_name_plural = _("images")
        abstract = True
        default_manager_name = 'objects'

    @classmethod
    def matches_file_type(cls, iname, ifile, mime_type):
        # source: https://www.freeformatter.com/mime-types-list.html
        image_subtypes = ['gif', 'jpeg', 'png', 'x-png', 'svg+xml']
        maintype, subtype = mime_type.split('/')
        return maintype == 'image' and subtype in image_subtypes

    def file_data_changed(self, post_init=False):
        attrs_updated = super().file_data_changed(post_init=post_init)
        if attrs_updated:
            try:
                try:
                    imgfile = self.file.file
                except ValueError:
                    imgfile = self.file_ptr.file
                imgfile.seek(0)
                if self.mime_type == 'image/svg+xml':
                    self._width, self._height = VILImage.load(imgfile).size
                else:
                    self._width, self._height = PILImage.open(imgfile).size
                imgfile.seek(0)
            except Exception:
                if post_init is False:
                    # in case `imgfile` could not be found, unset dimensions
                    # but only if not initialized by loading a fixture file
                    self._width, self._height = None, None
        return attrs_updated

    def save(self, *args, **kwargs):
        self.has_all_mandatory_data = self._check_validity()
        super().save(*args, **kwargs)

    def _check_validity(self):
        if not self.name:
            return False
        return True

    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width) / float(self.SIDEBAR_IMAGE_WIDTH)
        else:
            return 1.0

    @cached_property
    def exif(self):
        try:
            return get_exif_for_file(self.file)
        except Exception:
            return {}

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
        if not user.is_authenticated:
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
        return self._width or 0.0

    @property
    def height(self):
        return self._height or 0.0

    def _generate_thumbnails(self, required_thumbnails):
        _thumbnails = {}
        for name, opts in required_thumbnails.items():
            try:
                opts.update({'subject_location': self.subject_location})
                thumb = self.file.get_thumbnail(opts)
                _thumbnails[name] = thumb.url
            except Exception as e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while generating thumbnail: %s', e)
                if filer_settings.FILER_DEBUG:
                    raise
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
        return self._generate_thumbnails(BaseImage.DEFAULT_THUMBNAILS)

    @property
    def easy_thumbnails_thumbnailer(self):
        tn = FilerThumbnailer(
            file=self.file, name=self.file.name,
            source_storage=self.file.source_storage,
            thumbnail_storage=self.file.thumbnail_storage,
            thumbnail_basedir=self.file.thumbnail_basedir)
        return tn
