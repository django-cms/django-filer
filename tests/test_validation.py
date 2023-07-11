import os

import django.core
from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

from filer.models import File, Folder
from filer.validation import FileValidationError, validate_upload
from tests.helpers import create_superuser


class TestValidators(TestCase):

    def setUp(self) -> None:
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.folder = Folder.objects.create(name='foo')

    def tearDown(self) -> None:
        self.folder.delete()

    svg_file = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "
http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" baseProfile="full" width="50" height="50" xmlns="http://www.w3.org/2000/svg">
   <polygon id="triangle" points="0,0 0,50 50,0" fill="#009900"
stroke="#004400"/>
   {}
</svg>"""

    def test_html_upload_fails(self):
        html_file = 'test_file.html'
        filename = os.path.join(
            settings.FILE_UPLOAD_TEMP_DIR,
            html_file
        )

        with open(filename, 'wb') as fh:
            fh.write(b"<html><script>alert('hello filer');</script></html>")
        self.assertEqual(File.objects.count(), 0)

        with open(filename, 'rb') as fh:
            file_obj = django.core.files.File(fh)
            url = reverse('admin:filer-ajax_upload', kwargs={'folder_id': self.folder.pk})
            post_data = {
                'Filename': html_file,
                'Filedata': file_obj,
                'jsessionid': self.client.session.session_key
            }
            response = self.client.post(url, post_data)

        self.assertContains(response, "HTML upload denied by site security policy")
        self.assertEqual(File.objects.count(), 0)

    def test_svg_upload_fails(self):
        for attack, expected_files in [
            ("""<a href="javascript : alert('ing');">test</a>""", 0),
            ('<script>alert(document.domain);</script>', 0),
            ("""<circle onclick="console.log('test')" cx="300" cy="225" r="100" fill="red"/>""", 0),
            ("", 1)
        ]:
            svg_file = 'test_file.svg'
            filename = os.path.join(
                settings.FILE_UPLOAD_TEMP_DIR,
                svg_file
            )

        # create svg file with atack vector
        with open(filename, 'w') as fh:
            fh.write(self.svg_file.format(attack))
        n = File.objects.count()

        with open(filename, 'rb') as fh:
            file_obj = django.core.files.File(fh)
            url = reverse('admin:filer-ajax_upload', kwargs={'folder_id': self.folder.pk})
            post_data = {
                'Filename': svg_file,
                'Filedata': file_obj,
                'jsessionid': self.client.session.session_key
            }
            response = self.client.post(url, post_data)
        if expected_files == 0:
            self.assertContains(response, "Rejected due to potential cross site scripting vulnerability")
        self.assertEqual(File.objects.count(), n + expected_files)

    def test_deny_validator(self):
        from filer.validation import deny

        self.assertRaisesRegex(
            FileValidationError,
            "HTML upload denied by site security policy",
            deny,
            "test.html",
            None,
            None,
            "text/html",
        )

        self.assertRaisesRegex(
            FileValidationError,
            "MY_FUNNY_EXT upload denied by site security policy",
            deny,
            "test.my_funny_ext",
            None,
            None,
            "text/html",
        )

        self.assertRaisesRegex(
            FileValidationError,
            "Upload denied by site security policy",
            deny,
            "test",
            None,
            None,
            "text/html",
        )


class TestWhitelist(TestCase):
    def setUp(self) -> None:
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.folder = Folder.objects.create(name='foo')
        self.config = apps.get_app_config("filer")
        self.MIME_TYPE_WHITELIST = self.config.MIME_TYPE_WHITELIST

    def tearDown(self) -> None:
        self.folder.delete()
        self.config.MIME_TYPE_WHITELIST = self.MIME_TYPE_WHITELIST

    def set_whitelist(self, whitelist):
        self.config.MIME_TYPE_WHITELIST = whitelist

    def test_no_whitelist(self):
        self.set_whitelist([])
        for i in range(10):
            mime_type = get_random_string(6) + "/" + get_random_string(5)

            # If this throws an error, the test fails
            validate_upload(f"test.{mime_type.split('/')[-1]}", None, None, mime_type)

    def test_whitelist(self):
        self.set_whitelist(["text/*", "image/x-png"])

        expectation = {
            "text/plain": "ok",
            "text/html": "fail",  # OK by whitelist but blocked by html validator
            "image/x-png": "ok",
            "image/jpeg": "fail",
        }

        for mime_type, expected_result in expectation.items():
            if expected_result == "ok":
                try:
                    validate_upload("test-file", None, None, mime_type)
                except FileValidationError:
                    self.assertFalse(f"Mime type {mime_type} expected to pass")
            else:
                with self.assertRaises(FileValidationError):
                    validate_upload("test-file", None, None, mime_type)
