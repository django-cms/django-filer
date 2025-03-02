import string

from django.test import TestCase
from filer.utils.files import get_valid_filename


class GetValidFilenameTest(TestCase):

    def setUp(self):
        """
        Set up the test case by reading the configuration settings for the maximum filename length.
        """
        self.max_length = 155
        self.random_suffix_length = 16

    def test_short_filename_remains_unchanged(self):
        """
        Test that a filename under the maximum length remains unchanged.
        """
        original = "example.jpg"
        result = get_valid_filename(original)
        self.assertEqual(result, "example.jpg")

    def test_long_filename_is_truncated_and_suffix_appended(self):
        """
        Test that a filename longer than the maximum allowed length is truncated and a random
        hexadecimal suffix of length 16 is appended, resulting in exactly 255 characters.
        """
        base = "a" * 300  # 300 characters base
        original = f"{base}.jpg"
        result = get_valid_filename(original)
        self.assertEqual(
            len(result),
            self.max_length,
            "Filename length should be exactly 255 characters."
        )
        # Verify that the last 16 characters form a valid hexadecimal string.
        random_suffix = result[-16:]
        valid_hex_chars = set(string.hexdigits)
        self.assertTrue(all(c in valid_hex_chars for c in random_suffix),
                        "The suffix is not a valid hexadecimal string.")

    def test_filename_with_extension_preserved(self):
        """
        Test that the file extension is preserved (and slugified) after processing.
        """
        original = "This is a test IMAGE.JPG"
        result = get_valid_filename(original)
        self.assertTrue(result.endswith(".jpg"),
                        "File extension was not preserved correctly.")

    def test_unicode_characters(self):
        """
        Test that filenames with Unicode characters are handled correctly.
        """
        original = "fiłęñâmé_üñîçødé.jpeg"
        result = get_valid_filename(original)
        self.assertTrue(result.endswith(".jpeg"),
                        "File extension is not preserved for unicode filename.")
        # Verify that the resulting filename contains only allowed characters.
        allowed_chars = set(string.ascii_lowercase + string.digits + "._-")
        for char in result:
            self.assertIn(char, allowed_chars,
                          f"Unexpected character '{char}' found in filename.")

    def test_edge_case_exact_length(self):
        """
        Test that a filename exactly at the maximum allowed length remains unchanged.
        """
        extension = ".png"
        base_length = 155 - len(extension)
        base = "b" * base_length
        original = f"{base}{extension}"
        result = get_valid_filename(original)
        self.assertEqual(
            len(result),
            self.max_length,
            "Filename with length exactly 255 should remain unchanged."
        )
        self.assertEqual(result, original,
                         "Filename with length exactly 255 should not be modified.")

    def test_edge_case_filenames(self):
        """
        Test filenames at various boundary conditions to ensure correct behavior.
        """
        max_length = self.max_length
        random_suffix_length = self.random_suffix_length
        extension = ".jpg"

        # Test case 1: Filename with length exactly max_length - 1.
        base_length = max_length - 1 - len(extension)
        base = "c" * base_length
        original = f"{base}{extension}"
        result = get_valid_filename(original)
        self.assertEqual(result, original,
                         "Filename with length max_length-1 should remain unchanged.")

        # Test case 2: Filename with length exactly equal to max_length - random_suffix_length.
        base_length = max_length - random_suffix_length - len(extension)
        base = "d" * base_length
        original = f"{base}{extension}"
        result = get_valid_filename(original)
        self.assertEqual(result, original,
                         "Filename with length equal to max_length - random_suffix_length should remain unchanged.")

        # Test case 3: Filename with length exactly equal to max_length - random_suffix_length - 1.
        base_length = max_length - random_suffix_length - 1 - len(extension)
        base = "e" * base_length
        original = f"{base}{extension}"
        result = get_valid_filename(original)
        self.assertEqual(result, original,
                         "Filename with length equal to max_length - random_suffix_length - 1 should remain unchanged.")
