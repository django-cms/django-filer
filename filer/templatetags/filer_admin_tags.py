# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.template import Library
from django.utils.html import mark_safe
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


@register.simple_tag(takes_context=True)
def filer_admin_context_url_params(context, first_separator='?'):
    return admin_url_params_encoded(
        context['request'], first_separator=first_separator)


@register.simple_tag(takes_context=True)
def filer_admin_context_hidden_formfields(context):
    request = context.get('request')
    fields = [
        '<input type="hidden" name="{0}" value="{1}">'.format(fieldname, value)
        for fieldname, value in admin_url_params(request).items()
    ]
    return mark_safe('\n'.join(fields))
