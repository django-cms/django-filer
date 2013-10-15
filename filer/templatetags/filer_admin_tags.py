import django
from django.conf import settings
from django.template import Library
from distutils.version import LooseVersion

register = Library()

def filer_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context['action_index'] = context.get('action_index', -1) + 1
    return context
filer_actions = register.inclusion_tag("admin/filer/actions.html", takes_context=True)(filer_actions)


# Shamelessly taken from django-cms
# This will go away when django < 1.4 compatibility will be dropped
if LooseVersion(django.get_version()) < LooseVersion('1.4'):
    ADMIN_ICON_BASE = "%sadmin/img/admin/" % settings.STATIC_URL
    ADMIN_CSS_BASE = "%sadmin/css/" % settings.STATIC_URL
    ADMIN_JS_BASE = "%sadmin/js/" % settings.STATIC_URL
else:
    ADMIN_ICON_BASE = "%sadmin/img/" % settings.STATIC_URL
    ADMIN_CSS_BASE = "%sadmin/css/" % settings.STATIC_URL
    ADMIN_JS_BASE = "%sadmin/js/" % settings.STATIC_URL

@register.simple_tag
def admin_icon_base():
    return ADMIN_ICON_BASE

@register.simple_tag
def admin_css_base():
    return ADMIN_CSS_BASE

@register.simple_tag
def admin_js_base():
    return ADMIN_JS_BASE


@register.simple_tag(takes_context=True)
def get_popup_params(context, sep='?'):
    is_popup = context.get('is_popup', False)
    select_folder = context.get('select_folder', False)
    current_site = context.get('current_site', False)
    params = ''
    if is_popup:
        params += '%s_popup=1' % sep
        if select_folder:
            params += '&select_folder=1'
        if current_site:
            params += '&current_site=%s' % current_site
    return params


@register.filter
def is_restricted_for_user(filer_obj, user):
    return filer_obj.is_restricted_for_user(user)
