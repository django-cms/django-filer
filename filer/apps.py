import mimetypes

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _


class FilerConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'filer'
    verbose_name = _("Filer")

    def register_optional_heif_supprt(self):
        try:  # pragma:  no cover
            from pillow_heif import register_heif_opener

            from .settings import IMAGE_EXTENSIONS, IMAGE_MIME_TYPES

            # Register with easy_thumbnails
            register_heif_opener()
            HEIF_EXTENSIONS = [".heic", ".heics", ".heif", ".heifs", ".hif"]
            # Add extensions to python mimetypes which filer uses
            for ext in HEIF_EXTENSIONS:
                mimetypes.add_type("image/heic", ext)
            # Mark them as images
            IMAGE_EXTENSIONS += HEIF_EXTENSIONS
            IMAGE_MIME_TYPES.append("heic")
        except (ModuleNotFoundError, ImportError):
            # No heif support installed
            pass

    def register_optional_avif_support(self):
        """Pillow decodes AVIF itself since Pillow 11.3 (its wheels bundle libaom and
        dav1d). For older Pillow versions the optional pillow-avif-plugin package
        provides the same plugin."""
        from PIL import Image

        try:  # pragma: no cover
            import pillow_avif  # noqa: F401
        except (ModuleNotFoundError, ImportError):
            # No pillow-avif-plugin installed: Pillow's own AVIF plugin (if any) is used
            pass

        # registered_extensions() imports Pillow's plugins. Pillow only registers the
        # extensions if the AVIF codec actually is available.
        if ".avif" not in Image.registered_extensions():  # pragma: no cover
            # No AVIF support: leave avif files as plain files, they could not be
            # thumbnailed anyway
            return

        from .settings import IMAGE_EXTENSIONS, IMAGE_MIME_TYPES

        AVIF_EXTENSIONS = [".avif", ".avifs"]
        # Add extensions to python mimetypes which filer uses
        for ext in AVIF_EXTENSIONS:
            mimetypes.add_type("image/avif", ext)
        # Mark them as images
        for ext in AVIF_EXTENSIONS:
            if ext not in IMAGE_EXTENSIONS:
                IMAGE_EXTENSIONS.append(ext)
        if "avif" not in IMAGE_MIME_TYPES:
            IMAGE_MIME_TYPES.append("avif")

    def resolve_validators(self):
        """Resolve dotted path file validators"""

        import importlib

        from filer.settings import FILE_VALIDATORS, FILER_MIME_TYPE_WHITELIST

        if (
            not isinstance(FILER_MIME_TYPE_WHITELIST, (list, tuple)) or  # noqa W504
            any(map(lambda x: not isinstance(x, str), FILER_MIME_TYPE_WHITELIST))
        ):  # pragma: no cover
            raise ImproperlyConfigured(
                "filer: setting FILER_MIME_TYPE_WHITELIST needs to be a list or tuple of strings"
            )
        self.MIME_TYPE_WHITELIST = FILER_MIME_TYPE_WHITELIST
        self.FILE_VALIDATORS = {}
        for mime_type, validators in FILE_VALIDATORS.items():
            functions = []
            for item in validators:
                if callable(item):  # pragma: no cover
                    functions.append(item)
                else:
                    split = item.rsplit(".", 1)
                    try:
                        module = importlib.import_module(split[0])
                        functions.append(getattr(module, split[-1]))
                    except (ImportError, ModuleNotFoundError, AttributeError):
                        raise ImproperlyConfigured(f"""filer: could not import validator "{item}".""")
            self.FILE_VALIDATORS[mime_type] = functions

    def ready(self):
        # Make webp MIME type known to python (needed for python < 3.11)
        mimetypes.add_type("image/webp", ".webp")
        # Make avif MIME type known to python (needed for older python versions)
        mimetypes.add_type("image/avif", ".avif")
        #
        self.resolve_validators()
        self.register_optional_heif_supprt()
        self.register_optional_avif_support()
