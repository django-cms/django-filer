# -*- coding: utf-8 -*-
from django.template import Library

from filer.utils.compatibility import LTE_DJANGO_1_8, LTE_DJANGO_1_7


register = Library()


def filer_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context['action_index'] = context.get('action_index', -1) + 1
    return context
filer_actions = register.inclusion_tag("admin/filer/actions.html", takes_context=True)(filer_actions)


@register.inclusion_tag('admin/filer/widgets/lookup.html', takes_context=True)
def render_filer_lookup_button(context):
    context['IS_DJANGO_18'] = LTE_DJANGO_1_8 and not LTE_DJANGO_1_7
    return context
