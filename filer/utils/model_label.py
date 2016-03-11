# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.utils import six


def get_model_label(model):
    """
    Take a model class or model label and return its model label.

    >>> get_model_label(MyModel)
    "myapp.MyModel"

    >>> get_model_label("myapp.MyModel")
    "myapp.MyModel"
    """
    if isinstance(model, six.string_types):
        return model
    else:
        return "%s.%s" % (
            model._meta.app_label,
            model.__name__
        )
