from math import ceil

from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import Library
from django.utils.html import escapejs, format_html_join
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.files import get_thumbnailer

from filer import settings
from filer.admin.tools import admin_url_params, admin_url_params_encoded
from filer.models.imagemodels import BaseImage


register = Library()

assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


def filer_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context['action_index'] = context.get('action_index', -1) + 1
    return context


filer_actions = register.inclusion_tag(
    "admin/filer/actions.html", takes_context=True)(filer_actions)


@register.inclusion_tag(
    'admin/filer/folder/list_type_switcher.html',
    takes_context=True,
)
def filer_folder_list_type_switcher(context):
    choice_list = settings.FILER_FOLDER_ADMIN_LIST_TYPE_CHOICES
    current_list_type = context['list_type']
    # This solution is user friendly when there's only 2 choices
    # If there will be more list types then please change this switcher to more
    # proper widget (like for e.g. select list)
    next_list_type = next(
        iter(choice_list[choice_list.index(current_list_type) + 1:]),
        choice_list[0],
    )

    context['url'] = admin_url_params_encoded(
        context['request'],
        params={'_list_type': next_list_type},
    )
    context['tooltip_text'] = settings.FILER_FOLDER_ADMIN_LIST_TYPE_SWITCHER_SETTINGS[next_list_type]['tooltip_text']
    context['icon'] = settings.FILER_FOLDER_ADMIN_LIST_TYPE_SWITCHER_SETTINGS[next_list_type]['icon']
    return context


@register.simple_tag(takes_context=True)
def filer_admin_context_url_params(context, first_separator='?'):
    return admin_url_params_encoded(
        context['request'], first_separator=first_separator)


@register.simple_tag(takes_context=True)
def filer_admin_context_hidden_formfields(context):
    request = context.get('request')
    return format_html_join(
        '\n',
        '<input type="hidden" name="{0}" value="{1}">',
        admin_url_params(request).items(),
    )


@assignment_tag(takes_context=True)
def filer_has_permission(context, item, action):
    """Does the current user (taken from the request in the context) have
    permission to do the given action on the given item.

    """
    permission_method_name = 'has_{action}_permission'.format(action=action)
    permission_method = getattr(item, permission_method_name, None)
    request = context.get('request')

    if not permission_method or not request:
        return False
    # Call the permission method.
    # This amounts to calling `item.has_X_permission(request)`
    return permission_method(request)


def file_icon_context(file, detail, width, height):
    if not file.file.exists():
        return {
            'icon_url': staticfiles_storage.url('filer/icons/file-missing.svg'),
            'alt_text': _("File is missing"),
            'width': width,
            'height': height,
        }
    mime_maintype, mime_subtype = file.mime_maintype, file.mime_subtype
    context = {
        'mime_maintype': mime_maintype,
        'mime_type': file.mime_type,
    }
    if detail:
        context['download_url'] = file.url
    if isinstance(file, BaseImage):
        thumbnailer = get_thumbnailer(file)

        # SVG files may contain multiple vector graphics, and width and height are not available for them. If file does
        # not have width or height just ignore the thumbnail icon. Otherwise, continue with the standard procedure.
        if file.width == 0.0 or file.height == 0.0:
            icon_url = staticfiles_storage.url('filer/icons/file-unknown.svg')
        else:
            if detail:
                width, height = 210, ceil(210 / file.width * file.height)
                context['sidebar_image_ratio'] = file.width / 210
                opts = {'size': (width, height), 'upscale': True}
            else:
                opts = {'size': (width, height), 'crop': True}
            icon_url = thumbnailer.get_thumbnail(opts).url
            context['alt_text'] = file.default_alt_text
            if mime_subtype != 'svg+xml':
                opts['size'] = 2 * width, 2 * height
                context['highres_url'] = thumbnailer.get_thumbnail(opts).url
    elif mime_maintype in ['audio', 'font', 'video']:
        icon_url = staticfiles_storage.url('filer/icons/file-{}.svg'.format(mime_maintype))
    elif mime_maintype == 'application' and mime_subtype in ['zip', 'pdf']:
        icon_url = staticfiles_storage.url('filer/icons/file-{}.svg'.format(mime_subtype))
    else:
        icon_url = staticfiles_storage.url('filer/icons/file-unknown.svg')
    context.update(width=width, height=height, icon_url=icon_url)
    return context


@register.inclusion_tag('admin/filer/templatetags/file_icon.html')
def file_icon(file, detail=False, size=None):
    """
    This templatetag returns a rendered `<img src="..." srcset="..." width="..." height="..." class="..." />
    to be used for rendering thumbnails of files in the directory listing or in the corresponding detail
    views for that image.
    """
    if size:
        width, height = (int(s) for s in size.split('x'))
    else:
        width, height = (75, 75) if detail else (40, 40)
    return file_icon_context(file, detail, width, height)


@register.simple_tag
def file_icon_url(file):
    context = file_icon_context(file, False, 80, 80)
    return escapejs(context.get('highres_url', context['icon_url']))
