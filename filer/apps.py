from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FilerConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'filer'
    verbose_name = _("Filer")

    def ready(self):
        """Resolve dotted path file validators"""

        import importlib

        from filer.settings import FILE_VALIDATORS

        self.FILE_VALIDATORS = {}
        for mime_type, validators in FILE_VALIDATORS.items():
            functions = []
            for item in validators:
                if callable(item):
                    functions.append(item)
                else:
                    split = item.rsplit(".", 1)
                    module = importlib.import_module(split[0])
                    functions.append(getattr(module, split[-1]))
            self.FILE_VALIDATORS[mime_type] = functions
