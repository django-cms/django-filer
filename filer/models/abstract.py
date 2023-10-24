import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

import easy_thumbnails.utils
from easy_thumbnails.VIL import Image as VILImage
from PIL.Image import MAX_IMAGE_PIXELS

from .. import settings as filer_settings
from ..utils.compatibility import PILImage
from ..utils.filer_easy_thumbnails import FilerThumbnailer
from ..utils.pil_exif import get_exif_for_file
from .filemodels import File


logger = logging.getLogger(__name__)


# We can never exceed the max pixel value set by Pillow's PIL Image MAX_IMAGE_PIXELS
# as if we allow it, it will fail while thumbnailing (first in the admin thumbnails
# and then in the page itself.
# Refer this https://github.com/python-pillow/Pillow/blob/b723e9e62e4706a85f7e44cb42b3d838dae5e546/src/PIL/Image.py#L3148
FILER_MAX_IMAGE_PIXELS = min(
    getattr(settings, "FILER_MAX_IMAGE_PIXELS", MAX_IMAGE_PIXELS),
    MAX_IMAGE_PIXELS,
)


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

    _transparent = models.BooleanField(
        null=False,
        default=False,
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
        from ..settings import IMAGE_MIME_TYPES
        maintype, subtype = mime_type.split('/')
        return maintype == 'image' and subtype in IMAGE_MIME_TYPES

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
                    self._transparent = True
                else:
                    pil_image = PILImage.open(imgfile)
                    self._width, self._height = pil_image.size
                    self._transparent = easy_thumbnails.utils.is_transparent(pil_image)
                imgfile.seek(0)
            except Exception:
                if post_init is False:
                    # in case `imgfile` could not be found, unset dimensions
                    # but only if not initialized by loading a fixture file
                    self._width, self._height = None, None
                    self._transparent = False
        return attrs_updated

    def clean(self):
        # We check the Image size and calculate the pixel before
        # the image gets attached to a folder and saved. We also
        # send the error msg in the JSON and also post the message
        # so that they know what is wrong with the image they uploaded
        if not self.file:
            return

        if self._width is None or self._height is None:
            # If image size exceeds Pillow's max image size, Pillow will not return width or height
            pixels = 2 * FILER_MAX_IMAGE_PIXELS + 1
            aspect = 16 / 9
        else:
            width, height = max(1, self.width), max(1, self.height)
            pixels: int = width * height
            aspect: float = width / height
        res_x: int = int((FILER_MAX_IMAGE_PIXELS * aspect) ** 0.5)
        res_y: int = int(res_x / aspect)
        if pixels > 2 * FILER_MAX_IMAGE_PIXELS:
            msg = _(
                "Image format not recognized or image size exceeds limit of %(max_pixels)d million "
                "pixels by a factor of two or more. Before uploading again, check file format or resize "
                "image to %(width)d x %(height)d resolution or lower."
            ) % dict(max_pixels=FILER_MAX_IMAGE_PIXELS // 1000000, width=res_x, height=res_y)
            raise ValidationError(str(msg), code="image_size")

        if pixels > FILER_MAX_IMAGE_PIXELS:
            msg = _(
                "Image size (%(pixels)d million pixels) exceeds limit of %(max_pixels)d "
                "million pixels. Before uploading again, resize image to %(width)d x %(height)d "
                "resolution or lower."
            ) % dict(pixels=pixels // 1000000, max_pixels=FILER_MAX_IMAGE_PIXELS // 1000000,
                     width=res_x, height=res_y)
            raise ValidationError(str(msg), code="image_size")

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
        required_thumbnails = {
            size: {
                'size': (int(size), int(size)),
                'crop': True,
                'upscale': True,
                'subject_location': self.subject_location,
            }
            for size in filer_settings.FILER_ADMIN_ICON_SIZES}
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
