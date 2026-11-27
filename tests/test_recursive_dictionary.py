"""Tests for filer.utils.recursive_dictionary."""

from django.test import TestCase

from filer.utils.recursive_dictionary import RecursiveDictionary, RecursiveDictionaryWithExcludes


class RecursiveDictionaryTests(TestCase):
    """Tests for RecursiveDictionary."""

    def test_basic_update(self):
        d = RecursiveDictionary({'a': 1})
        d.rec_update({'b': 2})
        self.assertEqual(d, {'a': 1, 'b': 2})

    def test_recursive_merge(self):
        d = RecursiveDictionary({'foo': {'bar': 42}})
        d.rec_update({'foo': {'baz': 36}})
        self.assertEqual(d, {'foo': {'baz': 36, 'bar': 42}})

    def test_overwrite_non_dict(self):
        d = RecursiveDictionary({'foo': {'bar': 42}})
        d.rec_update({'foo': 'replaced'})
        self.assertEqual(d, {'foo': 'replaced'})

    def test_update_with_kwargs(self):
        d = RecursiveDictionary({'a': 1})
        d.rec_update({}, b=2, c=3)
        self.assertEqual(d, {'a': 1, 'b': 2, 'c': 3})

    def test_update_with_iterable(self):
        d = RecursiveDictionary()
        d.rec_update([('a', 1), ('b', 2)])
        self.assertEqual(d, {'a': 1, 'b': 2})

    def test_deep_nesting(self):
        d = RecursiveDictionary({'a': {'b': {'c': 1}}})
        d.rec_update({'a': {'b': {'d': 2}}})
        self.assertEqual(d, {'a': {'b': {'c': 1, 'd': 2}}})


class RecursiveDictionaryWithExcludesTests(TestCase):
    """Tests for RecursiveDictionaryWithExcludes."""

    def test_excluded_key_not_merged(self):
        d = RecursiveDictionaryWithExcludes(
            {'settings': {'a': 1, 'b': 2}},
            rec_excluded_keys=('settings',)
        )
        d.rec_update({'settings': {'a': 99, 'c': 3}})
        # 'settings' is excluded from recursion, so it gets overwritten entirely
        self.assertEqual(d, {'settings': {'a': 99, 'c': 3}})

    def test_non_excluded_key_merged(self):
        d = RecursiveDictionaryWithExcludes(
            {'nested': {'a': 1}, 'excluded': {'x': 2}},
            rec_excluded_keys=('excluded',)
        )
        d.rec_update({'nested': {'b': 2}, 'excluded': {'x': 99}})
        self.assertEqual(d['nested'], {'a': 1, 'b': 2})  # merged
        self.assertEqual(d['excluded'], {'x': 99})  # overwritten entirely

    def test_no_excluded_keys_defaults_to_normal(self):
        d = RecursiveDictionaryWithExcludes({'foo': {'bar': 1}})
        d.rec_update({'foo': {'baz': 2}})
        self.assertEqual(d, {'foo': {'bar': 1, 'baz': 2}})

    def test_excluded_key_with_non_dict_value(self):
        d = RecursiveDictionaryWithExcludes(
            {'settings': 'not-a-dict'},
            rec_excluded_keys=('settings',)
        )
        d.rec_update({'settings': 'new-value'})
        self.assertEqual(d, {'settings': 'new-value'})
