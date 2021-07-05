from django.conf import settings
from django.template import Library
from distutils.version import LooseVersion
import django
import pytz
import datetime
import filer

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

@register.inclusion_tag('admin/filer/submit_line.html', takes_context=True)
def submit_row(context):
    """
    Displays the row of buttons for delete and save.
    """
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    save_as = context['save_as']
    ctx = {
        'opts': opts,
        'obj': context.get('original'),
        'show_delete_link': not is_popup and context['has_delete_permission'] and change and context.get('show_delete', True),
        'show_save_as_new': not is_popup and change and save_as,
        'show_save_and_add_another': context['has_add_permission'] and not is_popup and (not save_as or context['add']),
        'show_save_and_continue': not is_popup and context['has_change_permission'],
        'is_popup': is_popup,
        'show_save': True,
        'preserved_filters': context.get('preserved_filters'),
    }
    if context.get('original') is not None:
        ctx['original'] = context['original']
    return ctx



@register.simple_tag(takes_context=True)
def get_popup_params(context, sep='?'):
    is_popup = context.get('is_popup', False)
    select_folder = context.get('select_folder', False)
    current_site = context.get('current_site', False)
    file_type = context.get('file_type', None)
    params = ''
    if is_popup:
        params += '%s_popup=1' % sep
        if select_folder:
            params += '&select_folder=1'
        if current_site:
            params += '&current_site=%s' % current_site
        if file_type:
            params += '&file_type=%s' % file_type

    return params


@register.filter
def is_restricted_for_user(filer_obj, user):
    return (filer_obj.is_readonly_for_user(user) or
            filer_obj.is_restricted_for_user(user))


@register.filter
def is_readonly_for_user(filer_obj, user):
    return filer_obj.is_readonly_for_user(user)


@register.filter
def can_change_folder(folder, user):
    return folder.has_change_permission(user)


@register.filter
def pretty_display(filer_obj):
    if isinstance(filer_obj, filer.models.Folder):
        return '/%s' % '/'.join(filer_obj.get_ancestors(include_self=True)
                                    .values_list('name', flat=True))
    if isinstance(filer_obj, filer.models.File):
        name = filer_obj.actual_name
        if not filer_obj.folder_id:
            return '/%s' % name
        return '/%s' % '/'.join(
            list(filer.models.Folder.all_objects.get(id=filer_obj.folder_id)
                    .get_ancestors(include_self=True)
                    .values_list('name', flat=True)) + [name])
    return ''


def _build_timezone_dict():
    offset_with_timezone = {}
    for zone in pytz.common_timezones:
        timezone_obj = pytz.timezone(zone)
        zone_offset = datetime.datetime.now(timezone_obj).strftime("%z")
        offset_with_timezone[zone_offset] = timezone_obj
    return offset_with_timezone

_OFFSETS_WITH_TIMEZONES = _build_timezone_dict()

@register.simple_tag(takes_context=True)
def client_timezone(context, date):
    gmt_offset = context.get('request').COOKIES.get('gmt_offset', None)
    if not gmt_offset:
        return date
    client_timezone = _OFFSETS_WITH_TIMEZONES.get(gmt_offset, None)
    if not client_timezone:
        return date
    return date.astimezone(client_timezone)
