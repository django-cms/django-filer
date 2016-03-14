# -*- coding: utf-8 -*-

# https://gist.github.com/114831
# recursive_dictionary.py
#   Created 2009-05-20 by Jannis Andrija Schnitzer.
#
# Copyright (c) 2009 Jannis Andrija Schnitzer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import

from django.utils import six

__author__ = 'jannis@itisme.org (Jannis Andrija Schnitzer)'


class RecursiveDictionary(dict):
    """RecursiveDictionary provides the methods rec_update and iter_rec_update
    that can be used to update member dictionaries rather than overwriting
    them."""
    def rec_update(self, other, **third):
        """Recursively update the dictionary with the contents of other and
        third like dict.update() does - but don't overwrite sub-dictionaries.

        Example:
        >>> d = RecursiveDictionary({'foo': {'bar': 42}})
        >>> d.rec_update({'foo': {'baz': 36}})
        >>> d
        {'foo': {'baz': 36, 'bar': 42}}
        """
        try:
            iterator = six.iteritems(other)
        except AttributeError:
            iterator = other
        self.iter_rec_update(iterator)
        self.iter_rec_update(six.iteritems(third))

    def iter_rec_update(self, iterator):
        for (key, value) in iterator:
            if key in self and\
               isinstance(self[key], dict) and isinstance(value, dict):
                self[key] = RecursiveDictionary(self[key])
                self[key].rec_update(value)
            else:
                self[key] = value


# changed version
class RecursiveDictionaryWithExcludes(RecursiveDictionary):
    """
    Same as RecursiveDictionary, but respects a list of keys that should be excluded from recursion
    and handled like a normal dict.update()
    """
    def __init__(self, *args, **kwargs):
        self.rec_excluded_keys = kwargs.pop('rec_excluded_keys', ())
        super(RecursiveDictionaryWithExcludes, self).__init__(*args, **kwargs)

    def iter_rec_update(self, iterator):
        for (key, value) in iterator:
            if key in self and\
               isinstance(self[key], dict) and isinstance(value, dict) and\
               key not in self.rec_excluded_keys:
                self[key] = RecursiveDictionaryWithExcludes(self[key],
                    rec_excluded_keys=self.rec_excluded_keys)
                self[key].rec_update(value)
            else:
                self[key] = value
