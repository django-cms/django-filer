### {{{ http://code.activestate.com/recipes/496741/ (r1) }}}
### {{{ Merged with ProxyTypes 0.9 }}}
class AbstractProxy(object):
    __slots__ = ["__weakref__"]

    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "__subject__"), name)
    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "__subject__"), name)
    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "__subject__"), name, value)

    def __nonzero__(self):
        return bool(object.__getattribute__(self, "__subject__"))
    def __str__(self):
        return str(object.__getattribute__(self, "__subject__"))
    def __repr__(self):
        return repr(object.__getattribute__(self, "__subject__"))

    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', 
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__', 
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__', 
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__', 
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__', 
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', 
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', 
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__', 
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__', 
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__', 
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', 
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__', 
        '__truediv__', '__xor__', 'next',
    ]

    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""

        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, "__subject__"), name)(*args, **kw)
            return method

        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an 
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        theclass.__init__(ins, obj, *args, **kwargs)
        return ins

### {{{ From ProxyTypes 0.9 }}}
class ObjectProxy(AbstractProxy):
    __slots__ = ["__subject__"]
    def __init__(self, obj):
        object.__setattr__(self, "__subject__", obj)

class AbstractWrapper(AbstractProxy):
    """Mixin to allow extra behaviors and attributes on proxy instance"""
    __slots__ = ()

    def __getattribute__(self, attr):
        if attr.startswith('__'):
            subject = object.__getattribute__(self, '__subject__')
            if attr=='__subject__':
                return subject
            return getattr(subject, attr)
        return object.__getattribute__(self, attr)

    def __getattr__(self, attr):
        return getattr(object.__getattribute__(self, '__subject__'), attr)

    def __setattr__(self, attr, val):
        if (
            attr=='__subject__'
            or hasattr(type(self), attr) and not attr.startswith('__')
        ):
            object.__setattr__(self, attr, val)
        else:
            setattr(self.__subject__, attr, val)

    def __delattr__(self, attr):
        if (
            attr=='__subject__'
            or hasattr(type(self), attr) and not attr.startswith('__')
        ):
            object.__delattr__(self, attr)
        else:
            delattr(self.__subject__, attr)

class ObjectWrapper(ObjectProxy, AbstractWrapper):      __slots__ = ()

### Inline test
if __name__ == "__main__":
    class xA:
        def __init__(self):
            self._miki = "miki xA"

        @property
        def miki(self):
            return self._miki

        def funky(self):
            return "funky() xA"

    class xAProxy(ObjectProxy):
        __slots__ = ()
        def __init__(self, oInstance):
            ObjectProxy.__init__(self, oInstance)

        @property
        def miki(self):
            return "I am A proxy"

        def funky(self):
            return "funky() A proxy"

    class xAWrapper(ObjectWrapper):
        __slots__ = ()
        def __init__(self, oInstance):
            ObjectProxy.__init__(self, oInstance)

        @property
        def miki(self):
            return "I am A wrapper"

        def funky(self):
            return "funky() A wrapper"

    a = xA()
    p = xAProxy(a)
    w = xAWrapper(a)

    def expect(call, result, succeed=True):
        exec ("rv = %s" % call)
        comment = "" if rv==result else (" != %s%s" % (result, " (not expected)" if succeed else " (expected)"))
        print "%s %s:\t%s%s" % ("T" if (rv==result) == succeed else "F", call, rv, comment)

    expect("a.miki", "miki xA")
    expect("p.miki", "I am A proxy", succeed=False)
    expect("w.miki", "I am A wrapper")
    expect("p._miki", "miki xA")
    expect("w._miki", "miki xA")
    expect("a.funky()", "funky() xA")
    expect("p.funky()", "funky() A proxy", succeed=False)
    expect("w.funky()", "funky() A wrapper")

