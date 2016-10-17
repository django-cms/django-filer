# -*- coding: utf-8 -*-
"""
This function is snatched from
https://github.com/ojii/django-load/blob/3058ab9d9d4875589638cc45e84b59e7e1d7c9c3/django_load/core.py#L49
local changes:

* added check for basestring to allow values that are already an object
  or method.

"""
from __future__ import absolute_import

from django.utils import six

from .compatibility import import_module


def load_object(import_path):
    """
    Loads an object from an 'import_path', like in MIDDLEWARE_CLASSES and the
    likes.

    Import paths should be: "mypackage.mymodule.MyObject". It then imports the
    module up until the last dot and tries to get the attribute after that dot
    from the imported module.

    If the import path does not contain any dots, a TypeError is raised.

    If the module cannot be imported, an ImportError is raised.

    If the attribute does not exist in the module, a AttributeError is raised.
    """
    if not isinstance(import_path, six.string_types):
        return import_path
    if '.' not in import_path:
        raise TypeError(
            "'import_path' argument to 'django_load.core.load_object' must "
            "contain at least one dot.")
    module_name, object_name = import_path.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, object_name)


def storage_factory(klass, location, base_url):
    """
    This factory returns an instance of the storage class provided.
    args:

    * klass: must be inherit from ``django.core.files.storage.Storage``
    * location: is a string representing the PATH similar to MEDIA_ROOT
    * base_url: is a string representing the URL similar to MEDIA_URL
    """
    return klass(location=location, base_url=base_url)
