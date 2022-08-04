from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExtendedAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'tests.utils.extended_app'
    verbose_name = _("Extended App")
