import io
import json
import os

import django.core
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

from PIL import Image

from filer.models import File, Folder
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from filer.validation import FileValidationError, sanitize_svg, strip_exif, validate_svg, validate_upload
from tests.helpers import create_superuser


FilerImage = load_model(FILER_IMAGE_MODEL)


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
        config = apps.get_app_config("filer")
        svg_validation = config.FILE_VALIDATORS["image/svg+xml"]
        config.FILE_VALIDATORS["image/svg+xml"] = [validate_svg]

        for attack, expected_files in [
            ("""<a href="javascript: alert('ing');">test</a>""", 0),
            ('<script>alert(document.domain);</script>', 0),
            ('&#x3c;script>alert(document.domain);</script>', 0),
            ("""<circle onclick="console.log('test')" cx="300" cy="225" r="100" fill="red"/>""", 0),
            ("", 1)
        ]:
            svg_file = 'test_file.svg'
            filename = os.path.join(
                settings.FILE_UPLOAD_TEMP_DIR,
                svg_file
            )

            # create svg file with attack vector
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

        config.FILE_VALIDATORS["image/svg+xml"] = svg_validation

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

    def test_browser_rendered_xml_formats_denied(self):
        # Formats that a browser may render and execute JavaScript from must be
        # rejected by default, just like text/html.
        for mime_type in (
            "application/xhtml+xml",
            "application/xml",
            "text/xml",
            "application/xslt+xml",
        ):
            with self.assertRaises(FileValidationError):
                validate_upload("test-file", None, self.superuser, mime_type)

    def test_svg_validator_rejects_non_svg_file(self):
        non_svg_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        file_obj = io.BytesIO(non_svg_content)

        with self.assertRaisesRegex(
            FileValidationError,
            "Rejected due to incompatible format",
        ):
            sanitize_svg("test_file.svg", file_obj, self.superuser, "image/svg+xml")

    def test_svg_sanitizer(self):
        for attack, disallowed in [
            ("""<a href="javascript: alert('ing');">test</a>""", "javascript:"),
            ('<script>alert(document.domain);</script>', "alert"),
            ("""<circle onclick="console.log('test')" cx="300" cy="225" r="100" fill="red"/>""", "onclick"),
        ]:
            svg_file = 'test_file.svg'
            filename = os.path.join(
                settings.FILE_UPLOAD_TEMP_DIR,
                svg_file
            )

            # create svg file with attack vector
            with open(filename, 'w') as fh:
                fh.write(self.svg_file.format(attack))

            with open(filename, 'rb') as fh:
                file_obj = django.core.files.File(fh)
                url = reverse('admin:filer-ajax_upload', kwargs={'folder_id': self.folder.pk})
                post_data = {
                    'Filename': svg_file,
                    'Filedata': file_obj,
                    'jsessionid': self.client.session.session_key
                }
                response = self.client.post(url, post_data)
            result = json.loads(response.content.decode("utf-8"))
            file_id = result["file_id"]
            img = File.objects.get(pk=file_id)
            content = img.file.file.read().decode("utf-8")
            self.assertNotIn(disallowed, content)

    def _jpeg_with_exif(self):
        image = Image.new("RGB", (8, 8), color=(255, 0, 0))
        exif = image.getexif()
        exif[0x010F] = "DjangoFiler"  # Make
        exif[0x0110] = "TestCamera"  # Model
        exif[0x8298] = "Copyright (c) nobody"  # Copyright

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif.tobytes(), quality=88)
        buffer.seek(0)
        return buffer

    def test_strip_exif_removes_metadata(self):
        source = self._jpeg_with_exif()
        self.assertTrue(Image.open(source).getexif(), "fixture must contain EXIF")
        source.seek(0)

        strip_exif("photo.jpg", source, self.superuser, "image/jpeg")

        stripped = Image.open(source)
        self.assertEqual(stripped.format, "JPEG")
        self.assertEqual(stripped.size, (8, 8))
        self.assertFalse(stripped.getexif())
        self.assertNotIn("exif", stripped.info)

    def test_strip_exif_webp_removes_metadata(self):
        image = Image.new("RGB", (8, 8), color=(0, 0, 255))
        exif = image.getexif()
        exif[0x010F] = "DjangoFiler"  # Make
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", exif=exif.tobytes())
        buffer.seek(0)

        # Sanity check: the fixture really carries EXIF.
        self.assertTrue(Image.open(buffer).getexif(), "fixture must contain EXIF")
        buffer.seek(0)

        strip_exif("photo.webp", buffer, self.superuser, "image/webp")

        stripped = Image.open(buffer)
        self.assertEqual(stripped.format, "WEBP")
        self.assertEqual(stripped.size, (8, 8))
        self.assertFalse(stripped.getexif())
        self.assertNotIn("exif", stripped.info)

    def test_strip_exif_preserves_progressive_jpeg(self):
        image = Image.new("RGB", (8, 8), color=(0, 0, 255))
        exif = image.getexif()
        exif[0x010F] = "DjangoFiler"  # Make -- forces a re-encode
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif.tobytes(), progressive=True)
        buffer.seek(0)

        # Sanity check: the fixture really is progressive.
        self.assertTrue(Image.open(buffer).info.get("progression"))
        buffer.seek(0)

        strip_exif("photo.jpg", buffer, self.superuser, "image/jpeg")

        stripped = Image.open(buffer)
        self.assertFalse(stripped.getexif())  # EXIF gone
        self.assertTrue(stripped.info.get("progression"))  # still progressive

    def test_strip_exif_preserves_icc_profile(self):
        # A minimal but valid ICC profile blob (sRGB) generated by Pillow.
        from PIL import ImageCms

        srgb = ImageCms.createProfile("sRGB")
        icc_bytes = ImageCms.ImageCmsProfile(srgb).tobytes()

        image = Image.new("RGB", (8, 8), color=(255, 0, 0))
        exif = image.getexif()
        exif[0x010F] = "DjangoFiler"  # Make -- forces a re-encode
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif.tobytes(), icc_profile=icc_bytes)
        buffer.seek(0)

        strip_exif("photo.jpg", buffer, self.superuser, "image/jpeg")

        stripped = Image.open(buffer)
        self.assertFalse(stripped.getexif())  # EXIF gone
        self.assertEqual(stripped.info.get("icc_profile"), icc_bytes)  # ICC kept

    def test_strip_exif_noop_without_metadata(self):
        image = Image.new("RGB", (4, 4), color=(0, 128, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        original = buffer.getvalue()
        buffer.seek(0)

        strip_exif("plain.png", buffer, self.superuser, "image/png")

        self.assertEqual(buffer.getvalue(), original)

    def test_strip_exif_removes_png_text_chunks(self):
        from PIL import PngImagePlugin

        image = Image.new("RGB", (4, 4), color=(0, 128, 0))
        info = PngImagePlugin.PngInfo()
        info.add_text("Author", "Jane Doe")
        info.add_text("Comment", "secret location")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", pnginfo=info)
        buffer.seek(0)

        # Sanity check: the fixture really carries text metadata.
        self.assertTrue(Image.open(buffer).text)
        buffer.seek(0)

        strip_exif("tagged.png", buffer, self.superuser, "image/png")

        stripped = Image.open(buffer)
        self.assertEqual(stripped.format, "PNG")
        self.assertEqual(stripped.size, (4, 4))
        self.assertFalse(stripped.text)

    def test_strip_exif_rejects_non_image(self):
        garbage = io.BytesIO(b"this is definitely not an image")
        with self.assertRaisesRegex(
            FileValidationError,
            "Rejected due to incompatible format",
        ):
            strip_exif("notes.txt", garbage, self.superuser, "image/jpeg")


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


class TestDeclaredMimeTypeIsNotTrusted(TestCase):
    """The MIME type of an upload is derived from its file name, never taken from
    the client-supplied Content-Type of the multipart part. Otherwise a made-up
    Content-Type would match neither FILE_VALIDATORS nor the extension
    consistency check, and the file would be stored (and served) under the type
    derived from its name -- bypassing deny_html/sanitize_svg."""

    html_payload = b"<html><script>alert(document.domain);</script></html>"

    def setUp(self) -> None:
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.folder = Folder.objects.create(name='foo')
        self.config = apps.get_app_config("filer")

    def tearDown(self) -> None:
        self.folder.delete()

    def upload(self, name, payload, content_type, client=None):
        upload = SimpleUploadedFile(name, payload, content_type=content_type)
        url = reverse('admin:filer-ajax_upload', kwargs={'folder_id': self.folder.pk})
        return (client or self.client).post(url, {'Filename': name, 'Filedata': upload})

    def test_html_upload_with_unknown_content_type_denied(self):
        for content_type in (
            "image/x-not-a-real-type",
            "application/x-does-not-exist",
            "image/png",  # known type, but inconsistent with the file name
        ):
            with self.subTest(content_type=content_type):
                response = self.upload("evil.html", self.html_payload, content_type)

                self.assertContains(response, "HTML upload denied by site security policy")
                self.assertEqual(File.objects.count(), 0)

    def test_svg_upload_with_unknown_content_type_is_sanitized(self):
        svg = TestValidators.svg_file.format(
            '<script>alert(document.domain);</script>'
        ).encode("utf-8")

        self.upload("evil.svg", svg, "image/x-not-a-real-type")

        self.assertEqual(File.objects.count(), 1)
        file_obj = File.objects.get()
        self.assertEqual(file_obj.mime_type, "image/svg+xml")
        with file_obj.file.open("rb") as fh:
            self.assertNotIn(b"<script>", fh.read())

    def test_unknown_content_type_does_not_bypass_whitelist(self):
        whitelist = self.config.MIME_TYPE_WHITELIST
        self.config.MIME_TYPE_WHITELIST = ["image/*"]
        try:
            response = self.upload("evil.html", self.html_payload, "image/x-not-a-real-type")
        finally:
            self.config.MIME_TYPE_WHITELIST = whitelist

        self.assertContains(response, "denied by site security policy")
        self.assertEqual(File.objects.count(), 0)

    def test_stored_mime_type_matches_validated_mime_type(self):
        self.upload("hello.txt", b"hello", "image/x-not-a-real-type")

        self.assertEqual(File.objects.get().mime_type, "text/plain")

    def test_malformed_content_type_does_not_raise(self):
        # A Content-Type without a slash used to reach mime_type.split('/') and
        # raise ValueError -> HTTP 500
        response = self.upload("evil.html", self.html_payload, "bogus")

        self.assertContains(response, "HTML upload denied by site security policy")
        self.assertEqual(File.objects.count(), 0)

    def test_unknown_extension_is_denied_by_default(self):
        # Falls back to application/octet-stream, which the default validators deny
        response = self.upload("payload.unknown-ext", b"data", "image/x-not-a-real-type")

        self.assertContains(response, "denied by site security policy")
        self.assertEqual(File.objects.count(), 0)

    def test_upload_requires_csrf_token(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.login(username='admin', password='secret')

        response = self.upload("hello.txt", b"hello", "text/plain", client=client)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(File.objects.count(), 0)

    def test_upload_requires_staff_user(self):
        user = User.objects.create_user(username="joe", password="secret", is_staff=False)
        user.user_permissions.add(Permission.objects.get(codename="add_file"))
        client = self.client_class()
        client.login(username="joe", password="secret")

        response = client.post(
            reverse('admin:filer-ajax_upload'),
            {'Filename': 'hello.txt', 'Filedata': SimpleUploadedFile("hello.txt", b"hello")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(File.objects.count(), 0)


class TestMimeTypeParsing(TestCase):
    def test_malformed_mime_type_does_not_raise(self):
        file_obj = File(mime_type="bogus")

        self.assertEqual(file_obj.mime_maintype, "bogus")
        self.assertEqual(file_obj.mime_subtype, "")
        self.assertFalse(FilerImage.matches_file_type("bogus", None, "bogus"))
