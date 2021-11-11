from django.db import models
from django.utils.translation import gettext_lazy as _


class ThumbnailOption(models.Model):
    """
    This class defines the option use to create the thumbnail.
    """
    name = models.CharField(
        _("Name"),
        max_length=100,
    )

    width = models.IntegerField(
        _("Width"),
        help_text=_("Width in pixel."),
    )

    height = models.IntegerField(
        _("Height"),
        help_text=_("Height in pixel."),
    )

    crop = models.BooleanField(
        _("Crop"),
        default=True,
    )

    upscale = models.BooleanField(
        _("Upscale"),
        default=True,
    )

    class Meta:
        app_label = 'filer'
        ordering = ('width', 'height')
        verbose_name = _("thumbnail option")
        verbose_name_plural = _("thumbnail options")

    def __str__(self):
        return '%s -- %s x %s' % (self.name, self.width, self.height)

    @property
    def as_dict(self):
        """
        This property returns a dictionary suitable for Thumbnailer.get_thumbnail()

        Sample code:
            # thumboption_obj is a ThumbnailOption instance
            # filerimage is a Image instance
            option_dict = thumboption_obj.as_dict
            thumbnailer = filerimage.easy_thumbnails_thumbnailer
            thumb_image = thumbnailer.get_thumbnail(option_dict)
        """
        return {
            'size': (self.width, self.height),
            'width': self.width,
            'height': self.height,
            'crop': self.crop,
            'upscale': self.upscale,
        }
