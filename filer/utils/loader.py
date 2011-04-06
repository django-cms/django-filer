#-*- coding: utf-8 -*-
import inspect

from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module

def load(klass, superklass):
    """
    will return an instance of klass, no matter if klass is:
    * already an instance of klass
    * is a subclass of superklass
    * is a string containing the path to a class. e.g 'my.app.MyClass'
    """
    if isinstance(klass, superklass):
        return klass
    elif inspect.isclass(klass) and issubclass(klass, superklass):
        return klass()
    elif issubclass(klass.__class__, superklass):
        return klass
    if isinstance(klass, str) or isinstance(klass, unicode):
        import_path = str(klass)
        try:
            dot = import_path.rindex('.')
        except ValueError:
            raise ImproperlyConfigured("%s isn't a %s module." % (import_path, superklass))
        module, classname = import_path[:dot], import_path[dot+1:]
        try:
            mod = import_module(module)
        except ImportError, e:
            raise ImproperlyConfigured('Error importing module %s: "%s"' % (module, e))
        try:
            return getattr(mod, classname)()
        except AttributeError:
            raise ImproperlyConfigured('%s module "%s" does not define a "%s" class.' % (superklass, module, classname))