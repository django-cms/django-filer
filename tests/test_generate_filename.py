"""Tests for filer.utils.generate_filename."""


from django.test import TestCase

from filer.utils.generate_filename import by_date, prefixed_factory, randomized


class ByDateTests(TestCase):
    """Tests for by_date upload_to function."""

    def test_by_date_returns_path(self):
        result = by_date(None, 'myfile.txt')
        parts = result.split('/')
        self.assertEqual(len(parts), 4)  # YYYY/MM/DD/filename
        self.assertEqual(parts[3], 'myfile.txt')

    def test_by_date_cleans_filename(self):
        result = by_date(None, 'My File (1).txt')
        self.assertNotIn(' ', result)
        self.assertNotIn('(', result)


class RandomizedTests(TestCase):
    """Tests for randomized upload_to function."""

    def test_randomized_returns_uuid_path(self):
        result = randomized(None, 'myfile.txt')
        parts = result.split('/')
        self.assertEqual(len(parts), 4)  # xx/yy/uuid/filename
        uuid_part = parts[2]
        self.assertEqual(len(uuid_part), 36)  # UUID string length
        self.assertEqual(parts[3], 'myfile.txt')

    def test_randomized_cleans_filename(self):
        result = randomized(None, 'Bad File.txt')
        self.assertNotIn(' ', result)


class PrefixedFactoryTests(TestCase):
    """Tests for prefixed_factory."""

    def test_with_string_upload_to(self):
        # upload_to returns a directory; Django appends the filename later
        factory = prefixed_factory('uploads/', 'prefix')
        result = factory(None, 'file.txt')
        self.assertEqual(result, 'prefix/uploads/')

    def test_with_callable_upload_to(self):
        def custom_upload_to(instance, filename):
            return f'custom/{filename}'

        factory = prefixed_factory(custom_upload_to, 'prefix')
        result = factory(None, 'file.txt')
        self.assertEqual(result, 'prefix/custom/file.txt')

    def test_empty_prefix_returns_upload_to(self):
        factory = prefixed_factory('uploaded/', '')
        result = factory(None, 'file.txt')
        self.assertEqual(result, 'uploaded/')

    def test_no_prefix(self):
        factory = prefixed_factory('uploaded/', None)
        result = factory(None, 'file.txt')
        self.assertEqual(result, 'uploaded/')
