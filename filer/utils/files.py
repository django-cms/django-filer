#-*- coding: utf-8 -*-
import os
import mimetypes

from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.core.files.uploadedfile import SimpleUploadedFile

from filer.settings import FILER_FILE_MODELS
from filer.utils.loader import load_object


import imghdr

class UploadException(Exception):
    pass


def handle_upload(request):
    if not request.method == "POST":
        raise UploadException("AJAX request not valid: must be POST")
    if request.is_ajax():
        # the file is stored raw in the request
        is_raw = True
        filename = request.GET.get('qqfile', False) or request.GET.get('filename', False) or ''
        if hasattr(request, 'body'):
            # raw_post_data was depreciated in django 1.4:
            # https://docs.djangoproject.com/en/dev/releases/1.4/#httprequest-raw-post-data-renamed-to-httprequest-body
            data = request.body
        elif hasattr(request, 'raw_post_data'):
            # fallback for django 1.3
            data = request.raw_post_data
        else:
            raise UploadException("Request is not valid: there is no request body.")
        mime_type = mimetypes.guess_type(filename)[0] or "text/plain"
        upload = SimpleUploadedFile(name=filename, content=data, content_type=mime_type)
    else:
        if len(request.FILES) == 1:
            # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
            # ID based on a random number, so it cannot be guessed here in the code.
            # Rather than editing Ajax Upload to pass the ID in the querystring, note that
            # each upload is a separate request so FILES should only have one entry.
            # Thus, we can just grab the first (and only) value in the dict.
            is_raw = False
            upload = list(request.FILES.values())[0]
            filename = upload.name
        else:
            raise UploadException("AJAX request not valid: Bad Upload")
    return upload, filename, is_raw


def get_valid_filename(s):
    """
    like the regular get_valid_filename, but also slugifies away
    umlauts and stuff.
    """
    if not s:
        return ''
    s = get_valid_filename_django(s)
    filename, ext = os.path.splitext(s)
    filename = slugify(filename)
    ext = slugify(ext)
    if ext:
        return "%s.%s" % (filename, ext)
    else:
        return "%s" % (filename,)


def matching_file_subtypes(filename, file_pointer, request):
    """
    Returns a list of valid subtypes for a given file.
    """
    types = list(map(load_object, FILER_FILE_MODELS))

    def _match_subtype(subtype):
        is_match = subtype.matches_file_type(filename, file_pointer, request)
        return is_match
    type_matches = list(filter(_match_subtype, types))
    return type_matches


def truncate_filename(upload, maxlen=None):
    """
    Return truncated filename
    Pre-extension filename will be less than or equals maxlen(if passed)
    """
    title, extension = os.path.splitext(upload.name)
    filename = '{title}.{ext}'.format(title=title[:maxlen],
                                      ext=extension.lstrip('.') or
                                      imghdr.what(upload))
    return filename

