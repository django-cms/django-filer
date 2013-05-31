#-*- coding: utf-8 -*-
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import filepath_to_uri


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


try:
    from storages.backends.s3boto import S3BotoStorage

    class PatchedS3BotoStorage(S3BotoStorage):

        def url(self, name):
            name = filepath_to_uri(self._normalize_name(self._clean_name(name)))
            if self.custom_domain:
                return "%s://%s/%s" % ('https' if self.secure_urls else 'http',
                                       self.custom_domain, name)
            return self.connection.generate_url(self.querystring_expire,
                method='GET', bucket=self.bucket.name, key=self._encode_name(name),
                query_auth=self.querystring_auth, force_http=not self.secure_urls)

        def copy(self, src_name, dst_name):
            src_path = self._normalize_name(self._clean_name(src_name))
            dst_path = self._normalize_name(self._clean_name(dst_name))
            self.bucket.copy_key(dst_path, self.bucket.name, src_path)


except ImportError:
    pass
