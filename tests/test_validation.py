import os

from django.conf import settings
import django.core
from django.test import TestCase
from django.urls import reverse

from filer.models import File, Folder
from tests.helpers import create_superuser


class TestValidators(TestCase):

    def setUp(self) -> None:
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.folder = Folder.objects.create(name='foo')

    def create_svg_attack(self, file_pointer, mode=0):
        attack = [
            """<a href="javascript : alert('ing');">test</a>""",
            '<script>alert(document.domain);</script>',
            """<circle onclick="console.log('test')" cx="300" cy="225" r="100" fill="red"/>""",
        ]
        file_pointer.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "
http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" baseProfile="full" width="50" height="50" xmlns="http://www.w3.org/2000/svg">
   <polygon id="triangle" points="0,0 0,50 50,0" fill="#009900"
stroke="#004400"/>
   {}
</svg>""".format(attack[mode]))

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
        for attack in range(3):
            svg_file = f'test_file_{attack}.svg'
            filename = os.path.join(
                settings.FILE_UPLOAD_TEMP_DIR,
                svg_file
            )

        with open(filename, 'w') as fh:
            self.create_svg_attack(fh, attack)
        self.assertEqual(File.objects.count(), 0)

        with open(filename, 'rb') as fh:
            file_obj = django.core.files.File(fh)
            url = reverse('admin:filer-ajax_upload', kwargs={'folder_id': self.folder.pk})
            post_data = {
                'Filename': svg_file,
                'Filedata': file_obj,
                'jsessionid': self.client.session.session_key
            }
            response = self.client.post(url, post_data)

        self.assertContains(response, "Rejected due to potential cross site scripting vulnerability")
        self.assertEqual(File.objects.count(), 0)

    def test_deny_validator(self):
        from filer.validation import deny, FileValidationError

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
