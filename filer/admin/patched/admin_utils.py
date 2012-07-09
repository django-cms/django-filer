#-*- coding: utf-8 -*-
"""
Copy of ``django.contrib.admin.utils.get_deleted_objects`` and a subclass of
``django.contrib.admin.utils.NestedObjects`` that work with djongo_polymorphic querysets.
Ultimatly these should go directly into django_polymorphic or, in a more generic way, into django itself.

This code has been copied from
django 1.4. ``get_deleted_objects`` and ``NestedObjects`` have not changed compared to 1.3.1.

At all locations where something has been changed, there are inline comments in the code.
"""
from django.contrib.admin.util import NestedObjects, quote
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.encoding import force_unicode
from django.core.urlresolvers import reverse


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

        if has_admin:
            admin_url = reverse('%s:%s_%s_change'
            % (admin_site.name,
               opts.app_label,
               opts.object_name.lower()),
                None, (quote(obj._get_pk_val()),))
            p = '%s.%s' % (opts.app_label,
                           opts.get_delete_permission())
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
                # Display a link to the admin page.
            return mark_safe(u'%s: <a href="%s">%s</a>' %
                             (escape(capfirst(opts.verbose_name)),
                              admin_url,
                              escape(obj)))
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return u'%s: %s' % (capfirst(opts.verbose_name),
                                force_unicode(obj))

    to_delete = collector.nested(format_callback)

    protected = [format_callback(obj) for obj in collector.protected]

    return to_delete, perms_needed, protected


class PolymorphicAwareNestedObjects(NestedObjects):
     def collect(self, objs, source_attr=None, **kwargs):
        if hasattr(objs, 'non_polymorphic'):
            # .filter() is needed, because there may already be cached polymorphic results in the queryset
            objs = objs.non_polymorphic().filter()
        return super(PolymorphicAwareNestedObjects, self).collect(objs, source_attr=source_attr, **kwargs)

