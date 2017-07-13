# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template

register = template.Library()


@register.inclusion_tag('admin/djangocms_publisher/tools/submit_line.html', takes_context=True)
def djangocms_publisher_submit_row(context):
    """
    Displays the row of buttons for delete, save and draft/live logic.
    """
    # buttons = context.get('draft_workflow_buttons', {})
    obj = context.get('original')
    opts = context['opts']
    is_popup = context['is_popup']
    model_admin = context['adminform'].model_admin
    request = context['request']
    buttons = model_admin.publisher_get_buttons(request, obj)

    if is_popup:
        # Don't show any of this in popup mode
        buttons.pop('delete', None)
        buttons.pop('save_and_continue', None)
        # buttons.pop('save', None)

    ctx = {
        'opts': opts,
        'preserved_filters': context.get('preserved_filters'),
        'draft_workflow_buttons': buttons,
        'is_popup': is_popup,
        'request': request,
    }
    if obj is not None:
        ctx['original'] = obj

    return ctx
