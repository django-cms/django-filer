#-*- coding: utf-8 -*-
from django.http import HttpResponseBadRequest
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms


class UploadFileForm(forms.Form):
    upload = forms.FileField

class UploadException(Exception):
    pass

def handle_upload(request):
    if not request.method == "POST":
        raise UploadException("AJAX request not valid: must be POST")
    if request.is_ajax():
        # the file is stored raw in the request
        is_raw = True
        filename = request.GET.get('qqfile', '')
        upload = SimpleUploadedFile(name=filename, content=request.raw_post_data)
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