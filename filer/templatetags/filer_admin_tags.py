# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.template import Library
from django.utils.html import format_html_join

from .. import settings
from ..admin.tools import admin_url_params, admin_url_params_encoded

register = Library()


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
    context['tooltip_text'] = settings.FILER_FOLDER_ADMIN_LIST_TYPE_SWITCHER_SETTINGS[next_list_type]['tooltip_text']  # noqa: E501
    context['icon'] = settings.FILER_FOLDER_ADMIN_LIST_TYPE_SWITCHER_SETTINGS[next_list_type]['icon']  # noqa: E501
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


@register.assignment_tag(takes_context=True)
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
