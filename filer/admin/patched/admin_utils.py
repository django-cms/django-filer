# -*- coding: utf-8 -*-
"""
Copy of ``django.contrib.admin.utils.get_deleted_objects`` and a subclass of
``django.contrib.admin.utils.NestedObjects`` that work with djongo_polymorphic querysets.
Ultimatly these should go directly into django_polymorphic or, in a more generic way, into django itself.

This code has been copied from
django 1.4. ``get_deleted_objects`` and ``NestedObjects`` have not changed compared to 1.3.1.

At all locations where something has been changed, there are inline comments in the code.
"""
from django.contrib.admin.utils import NestedObjects, quote
from django.contrib.auth import get_permission_codename
from django.utils.text import capfirst
from django.utils.html import format_html
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import force_text



def get_deleted_objects(objs, opts, user, admin_site, using):
    """
    Find all objects related to ``objs`` that should also be deleted. ``objs``
    must be a homogenous iterable of objects (e.g. a QuerySet).

    Returns a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.

    """
    # --- begin patch ---
    collector = PolymorphicAwareNestedObjects(using=using)
    # --- end patch ---
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta

        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
                                   force_text(obj))

        if has_admin:
            try:
                admin_url = reverse('%s:%s_%s_change'
                                    % (admin_site.name,
                                       opts.app_label,
                                       opts.model_name),
                                    None, (quote(obj._get_pk_val()),))
            except NoReverseMatch:
                # Change url doesn't exist -- don't display link to edit
                return no_edit_link

            p = '%s.%s' % (opts.app_label,
                           get_permission_codename('delete', opts))
            # Additional change: also check for individual object permission
            if not user.has_perm(p, obj) and not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return format_html('{}: <a href="{}">{}</a>',
                               capfirst(opts.verbose_name),
                               admin_url,
                               obj)
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return no_edit_link

    to_delete = collector.nested(format_callback)

    protected = [format_callback(obj) for obj in collector.protected]

    model_count = {model._meta.verbose_name_plural: len(objs) for model, objs in collector.model_objs.items()}

    return to_delete, model_count, perms_needed, protected


class PolymorphicAwareNestedObjects(NestedObjects):

    def _nested(self, obj, seen, format_callback):
        if obj in seen:
            return []
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            children.extend(self._nested(child, seen, format_callback))
        if hasattr(obj, 'is_in_trash') and obj.is_in_trash():
            ret = []
        else:
            if format_callback:
                ret = [format_callback(obj)]
            else:
                ret = [obj]
        if children:
            ret.append(children)
        return ret

    def collect(self, objs, source_attr=None, **kwargs):
        if hasattr(objs, 'non_polymorphic'):
            # .filter() is needed, because there may already be
            #   cached polymorphic results in the queryset
            objs = objs.non_polymorphic().filter()
        return super(PolymorphicAwareNestedObjects, self).collect(
            objs, source_attr=source_attr, **kwargs)
