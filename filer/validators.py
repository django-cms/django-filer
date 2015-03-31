# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from magic import from_buffer
    def get_mime_type(fp):
        return from_buffer(fp.read(1024), mime=True)
except ImportError:
    import warnings
    warnings.warn((
        'Can not import python-magic. '
        'Mime detection will be based on file\'s extension : this is not safe at all.'
        'Please install python-magic for better mime type detection based on file\'s content.'
    ))
    
    from mimetypes import guess_type
    def get_mime_type(fp):
        (mime, encoding) = guess_type(fp.name, strict=False)
        return mime

try:
    from django.utils.deconstruct import deconstructible
except ImportError:
    def deconstructible(cls):
        return cls

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

@deconstructible
class FileMimetypeValidator(object):
    """
    Validates that a file has a correct mimetype.
    Value can be :
        * an integer : pk of the File instance to validate
        * a File instance
        * a File instance #TODO : File ?
        * a ChunkFile File instance (part of a file during the upload process)
    raises ValidationError if file's mimetype is not valid
    """
    def __init__(self, mimetypes):
        self.mimetypes = mimetypes

    def __call__(self, value):
        if not value:
            return

        if type(value) == int:
            from filer.models import File
            try:
                f = File.objects.get(pk=value)
            except File.DoesNotExist:
                raise ValidationError(_('This value is not a valid file'))
            fp = f.file
        elif hasattr(value, 'name') and hasattr(value, 'read') and callable(value.read):
            #we only need .name and .read(). If this object have this attr and this method, 
            #it's ok
            fp = value
        elif hasattr(value, 'file'):
            fp = value.file
        else:
            raise ValidationError(_('This value is not a valid file'))

        try:
            mime = get_mime_type(fp)
        except AttributeError:
            mime = None

        if not mime:
            raise ValidationError(_('This value is not a valid file'))

        wildcard_mime = '%s/*' % mime.split('/')[0]

        if mime not in self.mimetypes and wildcard_mime not in self.mimetypes:
            msg = _('%(file)s is not a valid file. Allowed file types are : %(types)s') % {
                'file': fp.name,
                'types': ', '.join(self.mimetypes),
            }
            raise ValidationError(msg)

    def __eq__(self, other):
        return self.mimetypes == other.mimetypes


validate_images = FileMimetypeValidator(['image/*',])
validate_videos = FileMimetypeValidator(['video/*',])
validate_audios = FileMimetypeValidator(['audio/*',])

validate_documents = FileMimetypeValidator([
    #Main document mimetypes for CSV, DOC, XLS, PPT, ODT, ODS, ODP, PDF
    'application/msword', 
    'application/pdf',
    'application/vnd.ms-excel', 
    'application/vnd.ms-powerpoint',
    'application/vnd.oasis.opendocument.text', 
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation',
    'text/csv',])

validate_html5_images = FileMimetypeValidator([
    #Main supported mime types for web image content : SVG, JPEG, PNG, GIF
    'image/svg+xml', #http://caniuse.com/#feat=svg
    'image/jpeg', 'image/png', 'image/gif'])

validate_html5_videos = FileMimetypeValidator([
    #Main supported mime types for web video content : OGV, MP4, WEBM
    'video/ogg', #http://caniuse.com/#search=ogg
    'video/mp4', #http://caniuse.com/#search=mp4
    'video/webm',#http://caniuse.com/#search=webm
    ])

validate_html5_audios = FileMimetypeValidator([
    #Main supported mime types for web audio content : AAC, OGG, MP4, MP3, WAV, WEBM
    'audio/aac', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav', 'audio/webm',])
