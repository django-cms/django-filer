from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TestAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'tests.utils.test_app'
    verbose_name = _("Test app")
