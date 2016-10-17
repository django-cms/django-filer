from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..utils.compatibility import python_2_unicode_compatible


@python_2_unicode_compatible
class ThumbnailOption(models.Model):
    """
    This class defines the option use to create the thumbnail.
    """
    name = models.CharField(_("name"), max_length=100)
    width = models.IntegerField(_("width"), help_text=_('width in pixel.'))
    height = models.IntegerField(_("height"), help_text=_('height in pixel.'))
    crop = models.BooleanField(_("crop"), default=True)
    upscale = models.BooleanField(_("upscale"), default=True)

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
        return {"size": (self.width, self.height), "width": self.width,
                "height": self.height, "crop": self.crop, "upscale": self.upscale}
