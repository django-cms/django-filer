#-*- coding: utf-8 -*-
import os
from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.core.files.uploadedfile import SimpleUploadedFile


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
        else:
            # fallback for django 1.3
            data = request.raw_post_data
        upload = SimpleUploadedFile(name=filename, content=data)
    else:
        if len(request.FILES) == 1:
            # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
            # ID based on a random number, so it cannot be guessed here in the code.
            # Rather than editing Ajax Upload to pass the ID in the querystring, note that
            # each upload is a separate request so FILES should only have one entry.
            # Thus, we can just grab the first (and only) value in the dict.
            is_raw = False
            upload = request.FILES.values()[0]
            filename = upload.name
        else:
            raise UploadException("AJAX request not valid: Bad Upload")
    return upload, filename, is_raw


def get_valid_filename(s):
    """
    like the regular get_valid_filename, but also slugifies away
    umlauts and stuff.
    """
    s = get_valid_filename_django(s)
    filename, ext = os.path.splitext(s)
    filename = slugify(filename)
    ext = slugify(ext)
    if ext:
        return u"%s.%s" % (filename, ext)
    else:
        return u"%s" % (filename,)
