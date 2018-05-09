# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools

from .compat import PARLER_IS_INSTALLED


def get_related_objects(obj, excludes=None, using='default'):
    """
    Given a model instance will find all fields that have a ForeignKey,
    OneToOne or ManyToMany relationship to it.
    Returns a generator that yields all related model instances.
    """
    querysets = []
    for related_field in get_related_fields(obj._meta.model):
        querysets.append(
            related_field.field.model.objects.filter(
                **{related_field.field.name: obj}
            )
        )
    return itertools.chain(*[queryset.iterator() for queryset in querysets])


def update_one_to_many_relation(old_obj, new_obj, field, exclude):
    # A ForeignKey pointing to this model.
    if PARLER_IS_INSTALLED:
        from parler.models import TranslatableModelMixin
        # Don't update the relationship from the transated model to the master.
        if (
            field.field.name == 'master' and
            issubclass(field.model, TranslatableModelMixin) and
            field.model._parler_meta.root_model == field.field.model
        ):
            return 0
    model = field.field.model
    field_name = field.field.name
    queryset = model.objects.filter(**{field_name: old_obj})
    if model in exclude and field_name in exclude[model]:
        q_list = exclude[model][field_name]
        if q_list is True:
            # Ignore the whole field
            return 0
        for q in q_list:
            queryset = queryset.exclude(q)
    count = queryset.update(**{field_name: new_obj})
    return count


def update_one_to_one_relation(old_obj, new_obj, field, exclude):
    # A OneToOne pointing to this model.
    return update_one_to_many_relation(old_obj=old_obj, new_obj=new_obj, field=field, exclude=exclude)


def update_many_to_many_relation(old_obj, new_obj, field, exclude):
    # A ManyToMany pointing to this model.
    model = field.through
    field_name = field.field.name
    queryset = model.objects.all()
    if model in exclude and field_name in exclude[model]:
        q_list = exclude[model][field_name]
        if q_list is True:
            # Ignore the whole field
            return 0
        for q in q_list:
            queryset = queryset.exclude(q)

    queryset = model.objects
    from_field_name = field.field.m2m_field_name()
    to_field_name = field.field.m2m_reverse_field_name()
    if field.model == field.field.model:
        # This is a ManyToMany to itself. We should exclude our selves as the
        # source.
        queryset = queryset.exclude(
            **{'{}__in'.format(from_field_name): [old_obj, new_obj]}
        )
    count = (
        queryset
        .filter(**{to_field_name: old_obj})
        .update(**{to_field_name: new_obj})
    )
    return count


def update_relations(old_obj, new_obj, exclude=None):
    """
    Given an obj and a new_obj (must be the same model) will change all
    relationships pointing to obj to point to new_obj.
    Some things are not allowed.
     - An external model that has rows with a OneToOne to both the draft and
       live of the same object. This will cause a unique constraint error.
     - ManyToMany that link to both the draft and live version.
     - ForeignKey to this model with a unqique constraint on it (essentially a
       OneToOne) and rows for both draft and live of the same object.
    """
    # TODO: If there is are relations to obj that are linking to both the live
    #       and draft versions this may cause an error at db levels because of
    #       unique constraints.
    # DONE: [WORKS!] Check if this works with ManyToMany
    # TODO: Check if this works with GenericForeignKeys
    # DONE: [WORKS!] Check if this works with OneToOne
    # DONE: [WORKS!] Check if this work withs django-parler translated models
    # TODO: Check if this work withs django-hvad translated models
    # Mindbender: One of the related_fields will be the field that points from
    # the draft version to the live version. But since we filter the qs it does
    # not matter. It would only be a problem if we'd have a draft that points to
    # itself as live.
    assert old_obj.__class__ == new_obj.__class__
    exclude = exclude or {}
    count = 0
    for field in get_related_fields(old_obj._meta.model):
        kwargs = dict(
            old_obj=old_obj,
            new_obj=new_obj,
            field=field,
            exclude=exclude,
        )
        if field.one_to_many:
            # A ForeignKey pointing to this model.
            count += update_one_to_many_relation(**kwargs)
        elif field.one_to_one:
            count += update_one_to_one_relation(**kwargs)
        elif field.many_to_many:
            # A ManyToMany pointing to this model.
            count += update_many_to_many_relation(**kwargs)
    return count


def get_related_fields(model):
    # Get a list of all fields from all models that point to this model.
    # get_candidate_relations_to_delete() correctly excludes the parent_link
    # relations from models with multi-table inheritance as long as they are
    # correctly defined (with the parent_link=True parameter if the
    # OneToOne for the link is manually defined).
    return model._meta._get_fields(
        forward=False,
        reverse=True,
        include_hidden=True,
    )


def ignore_stuff_to_dict(ignore):
    stuff = {}
    for row in ignore:
        if len(row) == 2:
            model, field_name = row
            excludes_q = True
        elif len(row) == 3:
            model, field_name, excludes_q = row
        fields = stuff.setdefault(model, {})
        if excludes_q is True:
            fields[field_name] = True
        else:
            excludes = fields.setdefault(field_name, [])
            excludes.append(excludes_q)
    return stuff
