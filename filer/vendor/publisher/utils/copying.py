# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from .compat import CMS_IS_INSTALLED, PARLER_IS_INSTALLED

DEFAULT_COPY_EXCLUDE_FIELDS = (
    'pk',
    'id',
    'publisher_is_published_version',
    'publisher_published_version',
    'publisher_draft_version',
    'publisher_published_at',
    'publisher_deletion_requested',
)


if CMS_IS_INSTALLED:
    from cms.models.fields import PlaceholderField

    def is_placeholder_field(field):
        return isinstance(field, PlaceholderField)
else:
    def is_placeholder_field(field):
        return False


def get_fields_to_copy(obj, exclude_fields=None):
    all_exclude_fields = set(DEFAULT_COPY_EXCLUDE_FIELDS)
    if exclude_fields:
        all_exclude_fields |= set(exclude_fields)

    fields = {}
    for field in obj._meta._get_fields(forward=True, reverse=False):
        if (
            not field.concrete or
            field.auto_created or
            field.name in all_exclude_fields
        ):
            continue
        elif (
            field.is_relation and
            (field.one_to_one or field.many_to_many or field.one_to_many)
        ):
            # Can't copy a OneToOne, it'll cause a unique constraint error.
            # many_to_many are up to the user.
            # one_to_many are up to the user.
            continue
        elif is_placeholder_field(field):
            # Don't copy PlaceholderFields
            continue
        else:
            # Non-relation fields.
            # many_to_one: ForeignKeys to other models
            fields[field.name] = getattr(obj, field.name)
    return fields


def copy_object(new_obj, old_obj, exclude_fields=None):
    fields_to_copy = get_fields_to_copy(old_obj, exclude_fields=exclude_fields)
    for name, value in fields_to_copy.items():
        setattr(new_obj, name, value)


def copy_parler_translations(
    new_obj,
    old_obj,
    extra_exclude_fields=None,
    extra_values=None,
    delete_removed_translations=True,
):
    # get_or_create all translations from the old model and apply them
    # to the new.
    exclude_fields = {'master', 'language_code'}
    if extra_exclude_fields:
        exclude_fields |= set(extra_exclude_fields)

    old_languages = set()
    for old_translation in old_obj.translations.all():
        old_languages.add(old_translation.language_code)
        fields_to_copy = get_fields_to_copy(
            old_translation,
            exclude_fields=exclude_fields,
        )
        if extra_values is not None:
            fields_to_copy.update(extra_values)
        new_translation, created = new_obj.translations.update_or_create(
            language_code=old_translation.language_code,
            defaults=fields_to_copy,
        )
        if hasattr(new_obj, 'publisher_copy_parler_translation_relations'):
            new_obj.publisher_copy_parler_translation_relations(
                old_translation=old_translation,
                new_translation=new_translation,
            )
    if delete_removed_translations:
        new_obj.translations.exclude(language_code__in=old_languages).delete()


def copy_placeholder(old_placeholder, new_placeholder):
    # stolen from cms.models.pagemodel.Page._copy_contents()
    from cms.models.pluginmodel import CMSPlugin
    from cms.utils.copy_plugins import copy_plugins_to

    for plugin in CMSPlugin.objects.filter(placeholder=new_placeholder).order_by('-depth'):
        inst, cls = plugin.get_plugin_instance()
        if inst and getattr(inst, 'cmsplugin_ptr_id', False):
            inst.cmsplugin_ptr = plugin
            inst.cmsplugin_ptr._no_reorder = True
            inst.delete(no_mp=True)
        else:
            plugin._no_reorder = True
            plugin.delete(no_mp=True)

    plugins = old_placeholder.get_plugins_list()
    copy_plugins_to(plugins, new_placeholder)
