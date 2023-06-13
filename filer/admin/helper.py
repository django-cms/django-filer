"""Determine if django CMS is installed and if it comes with its own iconset"""
from django.conf import settings

ICON_CSS_LIB = "filer/css/admin_filer.icons.css"
if "cms" in settings.INSTALLED_APPS:
    try:
        from cms import __version__
        from cms.utils.urlutils import static_with_version

        if __version__ >= "4":
            ICON_CSS_LIB = static_with_version("cms/css/cms.admin.css")
    except (ModuleNotFoundError, ImportError):
        pass
