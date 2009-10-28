from filer.settings import FILER_ADMIN_ICON_SIZES, FILER_MEDIA_PREFIX

class IconsMixin(object):
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in FILER_ADMIN_ICON_SIZES:
                r[size] = "%sicons/%s_%sx%s.png" % (FILER_MEDIA_PREFIX, self._icon, size, size)
        return r