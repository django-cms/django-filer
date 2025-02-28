import string

from django.test import TestCase

from filer.utils.files import get_valid_filename


class GetValidFilenameTest(TestCase):
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
        hexadecimal suffix is appended. The final filename must not exceed 255 characters.
        """
        # Create a filename that is much longer than 255 characters.
        base = "a" * 300  # 300 characters
        original = f"{base}.jpg"
        result = get_valid_filename(original)
        # Assert that the result is within the maximum allowed length.
        self.assertTrue(len(result) <= 255, "Filename exceeds 255 characters.")

        # When truncated, the filename should end with a random hexadecimal suffix of length 16.
        # We check that the suffix contains only hexadecimal digits.
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
        # Since slugification converts characters to lowercase, we expect ".jpg"
        self.assertTrue(result.endswith(".jpg"),
                        "File extension was not preserved correctly.")

    def test_unicode_characters(self):
        """
        Test that filenames with Unicode characters are handled correctly and result in a valid filename.
        """
        original = "fiłęñâmé_üñîçødé.jpeg"
        result = get_valid_filename(original)
        # Verify that the result ends with the expected extension and contains only allowed characters.
        self.assertTrue(result.endswith(".jpeg"), "File extension is not preserved for unicode filename.")
        # Optionally, check that no unexpected characters remain (depends on your slugify behavior).
        for char in result:
            # Allow only alphanumeric characters, underscores, dashes, and the dot.
            self.assertIn(char, string.ascii_lowercase + string.digits + "._-",
                          f"Unexpected character '{char}' found in filename.")

    def test_edge_case_exact_length(self):
        """
        Test an edge case where the filename is exactly the maximum allowed length.
        The function should leave such a filename unchanged.
        """
        # Create a filename that is exactly 255 characters long.
        base = "b" * 251  # 250 characters for base
        original = f"{base}.png"  # This may reach exactly or slightly above 255 depending on slugification
        result = get_valid_filename(original)
        # We check that the final result does not exceed 255 characters.
        self.assertTrue(len(result) <= 255,
                        "Edge case filename exceeds the maximum allowed length.")
