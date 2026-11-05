"""Tests for filer.utils.zip."""

import io
import zipfile

from django.test import TestCase

from filer.utils.zip import unzip


class UnzipTests(TestCase):
    """Tests for the unzip utility."""

    def _make_zip(self, files):
        """Create an in-memory zip file with given {name: content} dict."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        buffer.seek(0)
        return buffer

    def test_unzip_single_file(self):
        zip_buf = self._make_zip({'hello.txt': 'Hello, world!'})
        result = unzip(zip_buf)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], 'hello.txt')
        self.assertEqual(result[0][0].read(), b'Hello, world!')

    def test_unzip_multiple_files(self):
        zip_buf = self._make_zip({'a.txt': 'A', 'b.txt': 'B'})
        result = unzip(zip_buf)
        self.assertEqual(len(result), 2)
        names = {r[1] for r in result}
        self.assertEqual(names, {'a.txt', 'b.txt'})

    def test_unzip_skips_meta_files(self):
        """Files starting with '__' should be skipped."""
        zip_buf = self._make_zip({
            '__meta.txt': 'meta',
            'real.txt': 'real content',
            '__MACOSX/._thing': 'junk',
        })
        result = unzip(zip_buf)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], 'real.txt')
        self.assertEqual(result[0][0].read(), b'real content')
