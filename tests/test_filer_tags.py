"""Tests for filer.templatetags.filer_tags."""

from django.test import TestCase

from filer.templatetags.filer_tags import filesize


class FileSizeTests(TestCase):
    """Tests for the filesize template filter."""

    def test_filesize_auto1024_bytes(self):
        self.assertEqual(filesize(500, format='auto1024'), '500 B')

    def test_filesize_auto1024_kib(self):
        # Whole-number values drop the ".0"
        self.assertEqual(filesize(2048, format='auto1024'), '2 KiB')

    def test_filesize_auto1024_mib(self):
        self.assertEqual(filesize(3 * 1024 * 1024, format='auto1024'), '3 MiB')

    def test_filesize_auto1024_gib(self):
        self.assertEqual(filesize(2 * 1024 * 1024 * 1024, format='auto1024'), '2 GiB')

    def test_filesize_auto1024_fractional(self):
        result = filesize(1500, format='auto1024')
        self.assertTrue(result.startswith('1.'), f"Expected fractional KiB, got '{result}'")
        self.assertIn('KiB', result)

    def test_filesize_auto1024_tib(self):
        self.assertEqual(filesize(3 * 1024 * 1024 * 1024 * 1024, format='auto1024'), '3 TiB')

    def test_filesize_auto1000_bytes(self):
        self.assertEqual(filesize(500, format='auto1000'), '500 B')

    def test_filesize_auto1000_kb(self):
        self.assertEqual(filesize(2000, format='auto1000'), '2 kB')

    def test_filesize_auto1000_mb(self):
        self.assertEqual(filesize(3_000_000, format='auto1000'), '3 MB')

    def test_filesize_auto1024long_bytes(self):
        self.assertEqual(filesize(500, format='auto1024long'), '500 bytes')

    def test_filesize_auto1024long_kib(self):
        self.assertEqual(filesize(2048, format='auto1024long'), '2 kibibytes')

    def test_filesize_auto1024long_mib(self):
        self.assertEqual(filesize(3 * 1024 * 1024, format='auto1024long'), '3 mebibytes')

    def test_filesize_auto1000long_bytes(self):
        self.assertEqual(filesize(500, format='auto1000long'), '500 bytes')

    def test_filesize_auto1000long_kb(self):
        self.assertEqual(filesize(2000, format='auto1000long'), '2 kilobytes')

    def test_filesize_auto1000long_mb(self):
        self.assertEqual(filesize(3_000_000, format='auto1000long'), '3 megabytes')

    def test_filesize_auto1000long_singular(self):
        self.assertEqual(filesize(1000, format='auto1000long'), '1 kilobyte')

    def test_filesize_exact_kb(self):
        self.assertAlmostEqual(filesize(2000, format='kB'), 2.0)

    def test_filesize_exact_mb(self):
        self.assertAlmostEqual(filesize(3_000_000, format='MB'), 3.0)

    def test_filesize_exact_gb(self):
        self.assertAlmostEqual(filesize(5_000_000_000, format='GB'), 5.0)

    def test_filesize_exact_kib(self):
        self.assertAlmostEqual(filesize(2048, format='KiB'), 2.0)

    def test_filesize_exact_mib(self):
        self.assertAlmostEqual(filesize(3 * 1024 * 1024, format='MiB'), 3.0)

    def test_filesize_exact_gib(self):
        self.assertAlmostEqual(filesize(2 * 1024 * 1024 * 1024, format='GiB'), 2.0)

    def test_filesize_zero_auto1024(self):
        self.assertEqual(filesize(0, format='auto1024'), '0 B')

    def test_filesize_zero_kb(self):
        self.assertEqual(filesize(0, format='kB'), 0)

    def test_filesize_zero_mb(self):
        self.assertEqual(filesize(0, format='MB'), 0)

    def test_filesize_zero_kib(self):
        self.assertEqual(filesize(0, format='KiB'), 0)

    def test_filesize_invalid_type_returns_original(self):
        self.assertEqual(filesize('not a number', format='auto1024'), 'not a number')

    def test_filesize_none_returns_none(self):
        self.assertIsNone(filesize(None, format='auto1024'))

    def test_filesize_invalid_format_returns_original(self):
        self.assertEqual(filesize(100, format='invalid'), 100)

    def test_filesize_two_char_invalid_returns_original(self):
        self.assertEqual(filesize(100, format='ab'), 100)

    def test_filesize_two_char_not_in_formats(self):
        self.assertEqual(filesize(100, format='xB'), 100)

    def test_filesize_three_char_format(self):
        self.assertAlmostEqual(filesize(2048, format='KiB'), 2.0)

    def test_filesize_small_number(self):
        self.assertEqual(filesize(1, format='auto1024'), '1 B')

    def test_filesize_10_bytes(self):
        self.assertEqual(filesize(10, format='auto1024'), '10 B')

    def test_filesize_three_char_non_i_format_returns_original(self):
        # A 3-char format like 'k B' where second char is not 'i' should return original
        # But 'k B' has first char 'k' in filesize_formats, second char ' ' != 'i'
        # Actually 'kBB' would work: len 3, first='k' in formats, second='B' != 'i'
        self.assertEqual(filesize(100, format='kBB'), 100)

    def test_filesize_two_char_B_but_bad_first_char(self):
        # 'XB': len 2, last='B', but 'X' not in filesize_formats
        self.assertEqual(filesize(100, format='XB'), 100)
