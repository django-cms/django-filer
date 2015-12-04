# -*- coding: utf-8 -*-
from distutils.version import LooseVersion

import django
from django.template import Library


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
    version = LooseVersion(django.get_version())
    is_18_and_up = version >= LooseVersion('1.8')
    context['IS_DJANGO_18'] = is_18_and_up and  version < LooseVersion('1.9')
    return context
