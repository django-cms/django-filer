#-*- coding: utf-8 -*-
import os
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.video import convert_video, grab_poster, get_dimensions


VIDEO_STATUS_TYPE = (
    ('new', _('New')),
    ('process', _('Being precessed')),
    ('ok', _('Converted successfully')),
    ('error', _('Conversion failed')),
)


class Video(File):
    file_type = 'Video'
    _icon = "video"

    original_height = models.IntegerField(null=True, blank=True, default=0)
    original_width = models.IntegerField(null=True, blank=True, default=0)

    height = models.IntegerField(null=True, blank=True, default=0)
    width = models.IntegerField(null=True, blank=True, default=0)

    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                      editable=False)

    default_alt_text = models.CharField(_('default alt text'), max_length=255, blank=True, null=True)
    default_caption = models.CharField(_('default caption'), max_length=255, blank=True, null=True)

    author = models.CharField(_('author'), max_length=255, null=True, blank=True)

    must_always_publish_author_credit = models.BooleanField(_('must always publish author credit'), default=False)
    must_always_publish_copyright = models.BooleanField(_('must always publish copyright'), default=False)

    conversion_status = models.CharField(max_length=50, choices=VIDEO_STATUS_TYPE, default='new')
    conversion_output = models.TextField(blank=True)

    class Meta:
        app_label = 'filer'
        verbose_name = _('video')
        verbose_name_plural = _('videos')

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        iext = os.path.splitext(iname)[1].lower().lstrip('.')
        return iext in filer_settings.FILER_SOURCE_VIDEO_FORMATS

    def set_initial_dimensions(self):
        sourcefile = self.file.storage.path(self.file.name)
        x, y = get_dimensions(sourcefile)
        self.original_width = x
        self.original_height = y
        self.width = x
        self.height = y

    def save(self, *args, **kwargs):
        self.has_all_mandatory_data = self._check_validity()
        if not self.original_width and not self.original_height:
            self.set_initial_dimensions()
        super(Video, self).save(*args, **kwargs)

    def _check_validity(self):
        if not self.name:
            return False
        return True

    @property
    def formats(self):
        _formats = {}
        for ext in filer_settings.FILER_VIDEO_FORMATS:
            try:
                _formats[ext] = self.file.get_format_url(ext)
            except Exception, e:
                pass
        return _formats

    def formats_html5(self):
        """ Video formats supported by HTML5 browsers """
        HTML5_FORMATS = ('mp4', 'ogv', 'webm')
        _formats = []
        for format, url in self.formats.items():
            if format in HTML5_FORMATS:
                _formats.append({'format': format, 'url': url})
        return _formats

    def format_flash(self):
        """ Returns flash video file if available """
        return self.formats.get('flv', None)

    @property
    def poster(self):
        try:
            return self.file.get_poster_url()
        except Exception, e:
            return ""

    def convert(self):
        original_path = self.file.storage.path(self.file.name)
        path = os.path.split(self.file.format_storage.path(self.file.name))[0]
        # loop in all
        output = []
        error = False
        #only set new dimensions if diferent from the original and not zero
        if self.width and self.height and (
                (self.width, self.height) != (self.original_width, self.original_height)):
            new_dimensions = "%sx%s" % (self.width, self.height)
        else:
            new_dimensions = filer_settings.FFMPEG_TARGET_DIMENSIONS
            if new_dimensions:
                self.width, self.height = new_dimensions.split('x')
        for extension in filer_settings.FILER_VIDEO_FORMATS:
            res, out = convert_video(original_path, path, extension, new_dimensions)
            error = error or res
            output.append(out)
        res, out = grab_poster(original_path, path, new_dimensions)
        error = error or res
        output.append(out)
        return error, "\n".join(output)
