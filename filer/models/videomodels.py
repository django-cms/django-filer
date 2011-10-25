#-*- coding: utf-8 -*-
import os
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer import settings as filer_settings
from filer.models.filemodels import File

VIDEO_STATUS_TYPE = (
    ('new','New'),
    ('process','Being precessed'),
    ('ok', 'Converted successfully'),
    ('error', 'Conversion failed'),
)

class Video(File):
    file_type = 'Video'
    _icon = "video"

    _height = models.IntegerField(null=True, blank=True)
    _width = models.IntegerField(null=True, blank=True)

    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                      editable=False)

    default_alt_text = models.CharField(_('default alt text'), max_length=255, blank=True, null=True)
    default_caption = models.CharField(_('default caption'), max_length=255, blank=True, null=True)

    author = models.CharField(_('author'), max_length=255, null=True, blank=True)

    must_always_publish_author_credit = models.BooleanField(_('must always publish author credit'), default=False)
    must_always_publish_copyright = models.BooleanField(_('must always publish copyright'), default=False)

    conversion_status = models.CharField(max_length=50, choices=VIDEO_STATUS_TYPE, default='new')
    conversion_output = models.TextField(blank=True)

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
      iext = os.path.splitext(iname)[1].lower()
      return iext in filer_settings.FILER_SOURCE_VIDEO_FORMATS

    @property
    def width(self):
        return self._width or 0

    @property
    def height(self):
        return self._height or 0

    def save(self, *args, **kwargs):
        self.has_all_mandatory_data = self._check_validity()
        # TODO try to get metadata like width/height 
        super(Image, self).save(*args, **kwargs)

    @property
    def formats(self):
        _formats = {}
        for ext in filer_settings.FILER_VIDEO_FORMATS:
            try:
                _formats[ext] = self.file.get_format_url(ext)
            except Exception, e:
                pass
        return _formats

    def convert(self):
        original_path = self.file.storage.path(self.file.name)
        original_path, filename = os.path.split(original_path) #os.path.dirname(kwargs['file'].path_full)
        extension = os.path.splitext(filename)[1]
        from video import convert_video
        path = os.path.split(self.file.formats_storage.path(self.file.name))[0]
        return convert_video(original_path, path, filename, extension)

    class Meta:
        app_label = 'filer'
        verbose_name = _('video')
        verbose_name_plural = _('videos')

    def get_video_flv_url(self):
        return self.file.formats_storage.url(self.flv())
        
    def flv(self):
        path = self.file.name
        path, filename = os.path.split(path) #os.path.dirname(kwargs['file'].path_full)
        basename = os.path.splitext(filename)[0]
        return os.path.join(path, basename + '.flv')

def thumbnail_path(self):
    original_path = self.formats_storage.path(self.name)
    original_path, filename = os.path.split(original_path) #os.path.dirname(kwargs['file'].path_full)
    basename = os.path.splitext(filename)[0]
    return os.path.join(original_path, basename + '.png')
