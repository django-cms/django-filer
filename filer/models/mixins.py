# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib.staticfiles.templatetags.staticfiles import static

from ..settings import FILER_ADMIN_ICON_SIZES


class IconsMixin(object):
    """
    Can be used on any model that has a _icon attribute. will return a dict
    containing urls for icons of different sizes with that name.
    """
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in FILER_ADMIN_ICON_SIZES:
                try:
                    r[size] = static("filer/icons/%s_%sx%s.png" % (
                        self._icon, size, size))
                except ValueError:
                    # Do not raise an exception while trying to call static()
                    # on non-existent icon file. This avoids the issue with
                    # rendering parts of the template as empty blocks that
                    # happens on an attempt to access object 'icons' attribute
                    # in template.
                    pass
        return r
