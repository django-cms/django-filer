from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CustomImageConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'tests.utils.custom_image'
    verbose_name = _("Custom Image")
