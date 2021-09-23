#-*- coding: utf-8 -*-
import logging
import botocore.exceptions
import urllib.parse
import mimetypes

from django.core.files.storage import FileSystemStorage
from django.utils.encoding import smart_str

try:
    from storages.backends.s3boto import S3BotoStorage
except ImportError:
    from storages.backends.s3boto3 import S3Boto3Storage as S3BotoStorage


logger = logging.getLogger(__name__)


class PublicFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer public directory

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    is_secure = False


class PrivateFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer private directory.
    This directory should NOT be served directly by the web server.

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    is_secure = True


def filepath_to_url(path):
    if path is None:
        return path
    return urllib.parse.quote(smart_str(path).replace("\\", "/"), safe="/~!*()")


class PatchedS3BotoStorage(S3BotoStorage):

    def url(self, name):
        if self.custom_domain:
            name = filepath_to_url(self._normalize_name(self._clean_name(name)))
            return "%s://%s/%s" % ('https' if self.secure_urls else 'http',
                                   self.custom_domain, name)
        return self.connection.generate_url(
            self.querystring_expire,
            method='GET', bucket=self.bucket.name, key=self._encode_name(name),
            query_auth=self.querystring_auth, force_http=not self.secure_urls)

    def has_public_read(self, object_key):
        old_acl = object_key.Acl().grants
        if not old_acl:
            return False
        for right in old_acl:
            if (
                'AllUsers' in right.get('Grantee', {}).get('URI', '') and
                right.get('Permission', '').upper() == 'READ'
            ):
                return True
        return False

    def copy(self, src_name, dst_name):
        src_path = self._normalize_name(self._clean_name(src_name))
        dst_path = self._normalize_name(self._clean_name(dst_name))
        copy_source = {
            'Bucket': self.bucket.name,
            'Key': src_path
        }
        source_obj = self.bucket.Object(src_path)
        try:
            extra_args = {
                'ContentType': source_obj.content_type
            }
        except botocore.exceptions.ClientError as error:
            logger.warning("Copy: source error: %s", error)
            return False
        # we cannot preserve acl in boto3, but we can give public read
        if self.has_public_read(source_obj):
            extra_args['ACL'] = 'public-read'
        self.bucket.copy(copy_source, dst_path, extra_args)

    def get_object_parameters(self, name):
        mime_type = mimetypes.guess_type(name)[0] or "text/plain"
        return {'ContentType': mime_type}
