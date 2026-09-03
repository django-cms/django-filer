from django.apps import AppConfig
from django.core import checks
from django.utils.translation import gettext_lazy as _


class FinderConfig(AppConfig):
    name = 'finder'
    verbose_name = _("Finder")

    #: Storage aliases which had to be derived from the `default` one, for `finder.checks`.
    derived_storages = ()

    def ready(self):
        from finder.checks import check_ambit_storages, check_default_ambit_slug
        from finder.storages import configure_default_storages

        self.__class__.derived_storages = tuple(configure_default_storages())
        checks.register(check_default_ambit_slug)
        checks.register(check_ambit_storages)
