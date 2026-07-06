"""Tests for filer.utils.compatibility."""
import django
from django.test import TestCase

from filer.utils.compatibility import (
    get_delete_permission,
    string_concat,
    truncate_words,
)


class TruncateWordsTests(TestCase):
    """Tests for truncate_words."""

    def test_truncate_no_truncation_needed(self):
        result = truncate_words('hello world', 10)
        self.assertEqual(result, 'hello world')

    def test_truncate_with_truncation(self):
        result = truncate_words('one two three four five', 3)
        self.assertEqual(result, 'one two three ...')

    def test_truncate_custom_end_text(self):
        result = truncate_words('one two three four five', 3, end_text='>>')
        self.assertEqual(result, 'one two three >>')

    def test_truncate_empty_end_text(self):
        result = truncate_words('one two three four five', 3, end_text='')
        self.assertEqual(result, 'one two three')

    def test_truncate_single_word(self):
        result = truncate_words('hello', 1)
        self.assertEqual(result, 'hello')

    def test_truncate_zero_words(self):
        result = truncate_words('hello world', 0)
        self.assertEqual(result, '' if django.VERSION > (5, 0) else ' ...')

    def test_truncate_empty_string(self):
        result = truncate_words('', 5)
        self.assertEqual(result, '')


class StringConcatTests(TestCase):
    """Tests for string_concat."""

    def test_concat_two_strings(self):
        result = string_concat('hello ', 'world')
        # format_lazy returns a lazy object; force evaluation
        self.assertIn('hello', str(result))
        self.assertIn('world', str(result))

    def test_concat_single_string(self):
        result = string_concat('hello')
        self.assertIn('hello', str(result))

    def test_concat_empty(self):
        result = string_concat()
        self.assertEqual(str(result), '')

    def test_concat_three_strings(self):
        result = string_concat('a', 'b', 'c')
        self.assertIn('a', str(result))
        self.assertIn('b', str(result))
        self.assertIn('c', str(result))


class GetDeletePermissionTests(TestCase):
    """Tests for get_delete_permission."""

    def test_get_delete_permission(self):
        from filer.models.filemodels import File
        result = get_delete_permission(File._meta)
        self.assertEqual(result, 'filer.delete_file')
