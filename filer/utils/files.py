import mimetypes
import os
import uuid

from django.http.multipartparser import ChunkIter, SkipFile, StopFutureHandlers, StopUpload, exhaust
from django.template.defaultfilters import slugify as slugify_django
from django.utils.encoding import force_str
from django.utils.text import get_valid_filename as get_valid_filename_django


class UploadException(Exception):
    pass


def handle_upload(request):
    if not request.method == 'POST':
        raise UploadException("XMLHttpRequest not valid: must be POST")
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # the file is stored raw in the request
        is_raw = True
        filename = request.GET.get('qqfile', False) or request.GET.get('filename', False) or ''

        try:
            content_length = int(request.headers['content-length'])
        except (IndexError, TypeError, ValueError):
            content_length = None

        if content_length < 0:
            # This means we shouldn't continue...raise an error.
            raise UploadException("Invalid content length: %r" % content_length)

        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        upload_handlers = request.upload_handlers
        for handler in upload_handlers:
            handler.handle_raw_input(request,
                                     request.META,
                                     content_length,
                                     None,
                                     None)
            pass

        # For compatibility with low-level network APIs (with 32-bit integers),
        # the chunk size should be < 2^31, but still divisible by 4.
        possible_sizes = [x.chunk_size for x in upload_handlers if x.chunk_size]
        chunk_size = min([2 ** 31 - 4] + possible_sizes)

        stream = ChunkIter(request, chunk_size)
        counters = [0] * len(upload_handlers)

        try:
            for handler in upload_handlers:
                try:
                    handler.new_file(None, filename,
                                     None, content_length, None)
                except StopFutureHandlers:
                    break

            for chunk in stream:
                for i, handler in enumerate(upload_handlers):
                    chunk_length = len(chunk)
                    chunk = handler.receive_data_chunk(chunk,
                                                       counters[i])
                    counters[i] += chunk_length
                    if chunk is None:
                        # If the chunk received by the handler is None, then don't continue.
                        break

        except SkipFile:
            # Just use up the rest of this file...
            exhaust(stream)
        except StopUpload as e:
            if not e.connection_reset:
                exhaust(request)
        else:
            # Make sure that the request data is all fed
            exhaust(request)

        # Signal that the upload has completed.
        for handler in upload_handlers:
            retval = handler.upload_complete()
            if retval:
                break

        for i, handler in enumerate(upload_handlers):
            file_obj = handler.file_complete(counters[i])
            if file_obj:
                upload = file_obj
                break
    else:
        if len(request.FILES) == 1:
            upload, filename, is_raw, mime_type = handle_request_files_upload(request)
        else:
            raise UploadException("XMLHttpRequest request not valid: Bad Upload")
    return upload, filename, is_raw, mime_type


def handle_request_files_upload(request):
    """
    Handle request.FILES if len(request.FILES) == 1.
    Returns tuple(upload, filename, is_raw, mime_type) where upload is file itself.
    """
    # FILES is a dictionary in Django but Ajax Upload gives the uploaded file
    # an ID based on a random number, so it cannot be guessed here in the code.
    # Rather than editing Ajax Upload to pass the ID in the querystring,
    # note that each upload is a separate request so FILES should only
    # have one entry.
    # Thus, we can just grab the first (and only) value in the dict.
    is_raw = False
    upload = list(request.FILES.values())[0]
    filename = upload.name
    _, iext = os.path.splitext(filename)
    mime_type = upload.content_type.lower()
    extensions = mimetypes.guess_all_extensions(mime_type)
    if mime_type != 'application/octet-stream' and extensions and iext.lower() not in extensions:
        msg = "MIME-Type '{mimetype}' does not correspond to file extension of {filename}."
        raise UploadException(msg.format(mimetype=mime_type, filename=filename))
    return upload, filename, is_raw, mime_type


def slugify(string):
    return slugify_django(force_str(string))


def _ensure_safe_length(filename, max_length=155, random_suffix_length=16):
    """
    Ensures that the filename does not exceed the maximum allowed length.
    If it does, the function truncates the filename and appends a random hexadecimal
    suffix of length `random_suffix_length` to ensure uniqueness and compliance with
    database constraints - even after markers for a thumbnail are added.

    Parameters:
        filename (str): The filename to check.
        max_length (int): The maximum allowed length for the filename.
        random_suffix_length (int): The length of the random suffix to append.

    Returns:
        str: The safe filename.


    Reference issue: https://github.com/django-cms/django-filer/issues/1270
    """

    if len(filename) <= max_length:
        return filename

    keep_length = max_length - random_suffix_length
    random_suffix = uuid.uuid4().hex[:random_suffix_length]
    return filename[:keep_length] + random_suffix


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
        valid_filename = "{}.{}".format(filename, ext)
    else:
        valid_filename = "{}".format(filename)

    # Ensure the filename meets the maximum length requirements.
    return _ensure_safe_length(valid_filename)
