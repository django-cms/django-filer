"""Tests for filer.server.views."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser

Image = load_model(filer_settings.FILER_IMAGE_MODEL)


class ServeProtectedFileTests(TestCase):
    """Tests for the serve_protected_file view."""

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        file_obj = SimpleUploadedFile(
            name='test_file.txt',
            content=b'Hello, world!',
            content_type='text/plain')
        self.filer_file = File.objects.create(
            owner=self.superuser,
            is_public=False,
            file=file_obj,
            original_filename='test_file.txt',
        )
        self.file_url = self.filer_file.file.url

    def tearDown(self):
        self.filer_file.delete()

    def test_serve_protected_file_authenticated(self):
        """Authenticated superuser can access protected file."""
        response = self.client.get(self.file_url)
        self.assertEqual(response.status_code, 200, f"Got {response.status_code} for {self.file_url}")
        self.assertIn(b'Hello, world!', response.content)

    def test_serve_protected_file_unauthenticated(self):
        """Unauthenticated user cannot access protected file."""
        self.client.logout()
        response = self.client.get(self.file_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_protected_file_nonexistent(self):
        """Requesting a non-existent file returns 404."""
        response = self.client.get('/filer_private/nonexistent_file.txt')
        self.assertEqual(response.status_code, 404)

    def test_serve_protected_file_url_matches_but_not_in_db(self):
        """URL matches the routing pattern but File lookup in DB fails."""
        # Construct a URL that Django will route to the view
        base = filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url
        response = self.client.get(f'/{base.lstrip("/")}2025/07/06/no_such_file.txt')
        self.assertEqual(response.status_code, 404)


class ServeProtectedFileDebugTests(TestCase):
    """Debug-mode behavior for serve_protected_file."""

    def setUp(self):
        self.superuser = create_superuser()

        file_obj = SimpleUploadedFile(
            name='test_file.txt',
            content=b'Hello, world!',
            content_type='text/plain')
        self.filer_file = File.objects.create(
            owner=self.superuser,
            is_public=False,
            file=file_obj,
            original_filename='test_file.txt',
        )
        self.file_url = self.filer_file.file.url

    def tearDown(self):
        self.filer_file.delete()

    @override_settings(DEBUG=True)
    def test_unauthenticated_debug_returns_403(self):
        """In DEBUG mode, unauthorized access returns 403 PermissionDenied."""
        response = self.client.get(self.file_url)
        self.assertEqual(response.status_code, 403)


class ServeProtectedThumbnailTests(TestCase):
    """Tests for serve_protected_thumbnail view."""

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        pil_image = create_image(mode='RGB', size=(200, 100))
        buffer = BytesIO()
        pil_image.save(buffer, format='JPEG')
        buffer.seek(0)

        file_obj = SimpleUploadedFile(
            name='test_thumb.jpg',
            content=buffer.read(),
            content_type='image/jpeg')
        self.filer_image = Image.objects.create(
            owner=self.superuser,
            is_public=False,
            file=file_obj,
            original_filename='test_thumb.jpg',
            mime_type='image/jpeg',
        )
        self.file_url = self.filer_image.file.url

    def tearDown(self):
        self.filer_image.delete()

    def test_serve_thumbnail_invalid_path_returns_404(self):
        """Requesting a thumbnail with no __ delimiter returns 404."""
        response = self.client.get('/filer_private_thumbnails/no_delimiter.jpg')
        self.assertEqual(response.status_code, 404)

    def test_serve_thumbnail_nonexistent_source_returns_404(self):
        """Thumbnail referencing non-existent source file returns 404."""
        response = self.client.get('/filer_private_thumbnails/nonexistent__100x100_q85.jpg')
        self.assertEqual(response.status_code, 404)

    def test_serve_thumbnail_unauthenticated_returns_404(self):
        """Unauthenticated user cannot access thumbnail."""
        self.client.logout()
        thumb_url = self.filer_image.file.url.replace(
            filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url,
            filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url)
        thumb_url = thumb_url.rsplit('.', 1)[0] + '__100x100_q85.jpg'
        response = self.client.get(thumb_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_thumbnail_authenticated(self):
        """Authenticated superuser can access a generated protected thumbnail."""
        # Generate a real thumbnail via easy_thumbnails
        thumbnailer = self.filer_image.easy_thumbnails_thumbnailer
        thumbnail = thumbnailer.get_thumbnail({'size': (100, 100)})
        # The thumbnail name is relative to the storage; prepend the base URL
        thumb_url = '/' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/') + thumbnail.name

        response = self.client.get(thumb_url)
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200, got {response.status_code} for {thumb_url}"
        )
        self.assertIn(response['Content-Type'], ['image/jpeg', 'image/webp'])
