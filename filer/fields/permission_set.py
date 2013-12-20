# -*- coding: utf-8 -*-
from django.db import models


class PermissionSetField(models.TextField):
    description = "A set of allow/deny values for users and groups"

    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        kwargs['default'] = ''
        super(PermissionSetField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(PermissionSetField, self).deconstruct()
        del kwargs['blank']
        del kwargs['default']
        return name, path, args, kwargs

    def to_python(self, value):
        from filer.models import PermissionSet
        if isinstance(value, PermissionSet):
            return value
        if value is None:
            return PermissionSet()
        return PermissionSet.from_txt(value)

    def get_prep_value(self, value):
        return value.to_txt()

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return field_class, args, kwargs
