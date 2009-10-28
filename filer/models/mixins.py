from filer.models.defaults import DEFAULT_ICON_SIZES
from filer import context_processors

class IconsMixin(object):
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in DEFAULT_ICON_SIZES:
                r[size] = "%sicons/%s_%sx%s.png" % (context_processors.media(None)['FILER_MEDIA_URL'], self._icon, size, size)
        return r