from django.apps import AppConfig
from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _


class FinderConfig(AppConfig):
    name = 'finder'
    verbose_name = _("Finder")
    model_forms = {}

    def ready(self):
        self.register_finder_forms()

    def register_finder_forms(self):
        """
        For each model inheriting from AbstractFileModel, try to find the corresponding form class.
        This is required, so that the file browser can render the correct detail form for each file type.
        """

        from finder.models.file import FileModel

        for model in FileModel.get_models(include_proxy=True):
            for app in settings.INSTALLED_APPS:
                if not app.startswith(f'{self.name}.'):
                    continue
                try:
                    self.model_forms[model] = import_string(f'{app}.forms.{model.__name__[:-5]}Form')
                except ImportError:
                    pass
