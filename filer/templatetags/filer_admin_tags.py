from math import ceil

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import FileSystemStorage
from django.template import Library
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import escapejs, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.engine import NoSourceGenerator
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.options import ThumbnailOptions

from filer import settings
from filer.admin.tools import admin_url_params, admin_url_params_encoded
from filer.models.imagemodels import BaseImage
from filer.settings import DEFERRED_THUMBNAIL_SIZES


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
    # This solution is user-friendly when there's only 2 choices
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
    permission_method_name = f'has_{action}_permission'
    permission_method = getattr(item, permission_method_name, None)
    request = context.get('request')

    if not permission_method or not request:
        return False
    # Call the permission method.
    # This amounts to calling `item.has_X_permission(request)`
    return permission_method(request)


def file_icon_context(file, detail, width, height):
    mime_maintype, mime_subtype = file.mime_maintype, file.mime_subtype
    context = {
        'mime_maintype': mime_maintype,
        'mime_type': file.mime_type,
    }
    height, width, context = get_aspect_ratio_and_download_url(context, detail, file, height, width)
    # returned context if icon is not available
    not_available_context = {
        'icon_url': staticfiles_storage.url('filer/icons/file-missing.svg'),
        'alt_text': _("File is missing"),
        'width': width,
        'height': width,  # The icon is a square
    }
    # Check if file exists for performance reasons (only on FileSystemStorage)
    if file.file and isinstance(file.file.source_storage, FileSystemStorage) and not file.file.exists():
        return not_available_context

    if isinstance(file, BaseImage):
        thumbnailer = get_thumbnailer(file)

        # SVG files may contain multiple vector graphics, and width and height are not available for them. If file does
        # not have width or height just ignore the thumbnail icon. Otherwise, continue with the standard procedure.
        if file.width == 0.0 or file.height == 0.0:
            icon_url = staticfiles_storage.url('filer/icons/file-unknown.svg')
        else:
            if detail:
                opts = {'size': (width, height), 'upscale': True}
            else:
                opts = {'size': (width, height), 'crop': True}
            thumbnail_options = ThumbnailOptions(opts)
            # Optimize directory listing:
            if width == height and width in DEFERRED_THUMBNAIL_SIZES and hasattr(file, "thumbnail_name"):
                # Get name of thumbnail from easy-thumbnail
                configured_name = thumbnailer.get_thumbnail_name(thumbnail_options, transparent=file._transparent)
                # If the name was annotated: Thumbnail exists and we can use it
                if configured_name == file.thumbnail_name:
                    icon_url = file.file.thumbnail_storage.url(configured_name)
                    if mime_subtype != 'svg+xml' and file.thumbnailx2_name:
                        context['highres_url'] = file.file.thumbnail_storage.url(file.thumbnailx2_name)
                else:  # Probably does not exist, defer creation
                    icon_url = reverse("admin:filer_file_fileicon", args=(file.pk, width))
                context['alt_text'] = file.default_alt_text
            else:
                # Try creating thumbnails / take existing ones
                try:
                    icon_url = thumbnailer.get_thumbnail(thumbnail_options).url
                    context['alt_text'] = file.default_alt_text
                    if mime_subtype != 'svg+xml':
                        thumbnail_options['size'] = 2 * width, 2 * height
                        context['highres_url'] = thumbnailer.get_thumbnail(thumbnail_options).url
                except (InvalidImageFormatError, NoSourceGenerator):
                    # This is caught by file.exists() for file storage systems
                    # For remote storage systems we catch the error to avoid second trip
                    # to the storage system
                    return not_available_context
    elif mime_maintype in ['audio', 'font', 'video']:
        icon_url = staticfiles_storage.url(f'filer/icons/file-{mime_maintype}.svg')
        height = width  # icon is a square
    elif mime_maintype == 'application' and mime_subtype in ['zip', 'pdf']:
        icon_url = staticfiles_storage.url(f'filer/icons/file-{mime_subtype}.svg')
        height = width  # icon is a square
    else:
        icon_url = staticfiles_storage.url('filer/icons/file-unknown.svg')
        height = width  # icon is a square
    context.update(width=width, height=height, icon_url=icon_url)
    return context


def get_aspect_ratio_and_download_url(context, detail, file, height, width):
    # Get download_url and aspect ratio right for detail view
    if detail:
        context['download_url'] = file.url
        if isinstance(file, BaseImage):
            # only check for file width, if the file
            # is actually an image and not on other files
            # because they don't really have width or height
            if file.width:
                width, height = 210, ceil(210 / file.width * file.height)
                context['sidebar_image_ratio'] = file.width / 210
    return height, width, context


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
    # Cache since it is called repeatedly by templates
    if not hasattr(file, "_file_icon_url_cache"):
        context = file_icon_context(file, False, 80, 80)
        file._file_icon_url_cache = escapejs(context.get('highres_url', context['icon_url']))
    return file._file_icon_url_cache


@register.simple_tag
def icon_css_library():
    html = ""
    for lib in settings.ICON_CSS_LIB:
        html += f'<link rel="stylesheet" type="text/css" href="{static(lib)}">'
    return mark_safe(html)
