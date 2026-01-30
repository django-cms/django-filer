from types import MethodType
import re

from django.conf import settings
from django.contrib.admin import ModelAdmin, site, sites
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from django.http import Http404
from django.http.response import HttpResponsePermanentRedirect
from django.urls import Resolver404, resolve, reverse
from django.views.decorators.common import no_append_slash

from finder.models.ambit import AmbitModel
from finder.models.permission import Privilege


def get_ambit_queryset(admin_name, current_site):
    return AmbitModel.objects.filter(
        Q(site=current_site) | Q(site__isnull=True),
        Q(admin_name=admin_name) | Q(admin_name__isnull=True),
    )


@no_append_slash
def catch_all_view(self, request, url):
    urlconf = getattr(request, "urlconf", None)
    if settings.APPEND_SLASH and not url.endswith("/"):
        try:
            match = resolve(f'{request.path_info}/', urlconf)
        except Resolver404:
            pass
        else:
            if getattr(match.func, "should_append_slash", True):
                return HttpResponsePermanentRedirect(
                    request.get_full_path(force_append_slash=True)
                )
    current_site = get_current_site(request)
    if m := re.match(r'finder/([A-Za-z0-9_]+)/$', url):
        try:
            ambit = get_ambit_queryset(self.name, current_site).get(slug=m.group(1))
        except AmbitModel.DoesNotExist:
            raise Http404
        return HttpResponsePermanentRedirect(f'{request.path_info}{ambit.root_folder.id}')
    if m := re.match(
        r'finder/([A-Za-z0-9_]+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(.*)$',
        url
    ):
        try:
            request._ambit = get_ambit_queryset(self.name, current_site).get(slug=m.group(1))
        except AmbitModel.DoesNotExist:
            raise Http404
        url = reverse('admin:finder_inodemodel_change', args=(m.group(2),), current_app=self.name)
        match = resolve(url, urlconf)
        return match.func(request, m.group(2))
    raise Http404


def register_ambit_admins(ambit_models):
    for admin_site in sites.all_sites:
        registered_model_names = [model.__name__ for model in admin_site._registry.keys()]
        for ambit_model in ambit_models:
            if ambit_model.slug in registered_model_names or ambit_model.admin_name not in [admin_site.name, None]:
                continue

            # create a proxy model for each AmbitModel object and register it within the admin site
            class Meta:
                app_label = AmbitModel._meta.app_label
                proxy = True
                managed = False
                verbose_name = verbose_name_plural = ambit_model.verbose_name

            proxy_model = type(
                ambit_model.slug,
                (AmbitModel,),
                {'Meta': Meta, '__module__': AmbitModel.__module__}
            )
            admin_site.register(proxy_model, admin_class=ModelAdmin)


def get_app_list(self, request, app_label=None):
    current_site = get_current_site(request)
    ambit_models = get_ambit_queryset(self.name, current_site)
    register_ambit_admins(ambit_models)
    app_dict = self._build_app_dict(request)

    # override the 'Finder' app to only show the ambit proxy models
    app_dict['finder'] = {
        'name': 'Finder',
        'app_label': 'finder',
        'app_url': reverse('admin:app_list', kwargs={'app_label': 'finder'}, current_app=self.name),
        'has_module_perms': True,
        'models': [],
    }
    url_parts = reverse('admin:finder_foldermodel_changelist', current_app=self.name).split('/')
    for model, model_admin in self._registry.items():
        if model._meta.proxy_for_model is not AmbitModel:
            continue
        root_folder = AmbitModel.objects.get(slug=model._meta.model_name).root_folder
        if not root_folder.has_permission(request.user, Privilege.READ):
            continue
        parts = [model._meta.model_name if part == 'foldermodel' else part for part in url_parts]
        if parts[-1] != '':
            parts.append('')
        app_dict[model._meta.app_label]['models'].append({
            'model': model,
            'name': model._meta.verbose_name,
            'object_name': model._meta.model_name,
            'perms': {'add': False, 'change': False, 'delete': False, 'view': True},
            'add_url': None,
            'admin_url': '/'.join(parts),
            'view_only': True,
        })

    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
    for app in app_list:
        app['models'].sort(key=lambda x: x['name'])
    return app_list


site.catch_all_view = MethodType(catch_all_view, site)
site.get_app_list = MethodType(get_app_list, site)
