#-*- coding: utf-8 -*-
import os
import mimetypes
from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import ugettext_lazy as _
from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.video import convert_video, grab_poster, get_dimensions, get_format_name


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
        if not ( self.original_width or self.original_height or \
                 self.width or self.height ):
            self.set_initial_dimensions()
        super(Video, self).save(*args, **kwargs)

    def _check_validity(self):
        if not self.name:
            return False
        return True

    @property
    def formats(self):
        _formats = []
        for ext in filer_settings.FILER_VIDEO_FORMATS:
            try:
                url = self.file.get_format_url(ext)
                filepath = self.file.get_format_filepath(ext)
                _formats.append({'url': url, 'format':ext, 'filepath':filepath})
            except Exception, e:
                pass
        return _formats

    def original_format(self):
        url = self.file.storage.url(self.file.name)
        name, ext = os.path.splitext(self.file.name)
        mimetype = mimetypes.guess_type(self.file.name)[0]
        fmt = ext.replace('.', '')
        return {'url': url, 'format': fmt, 'mimetype': mimetype}

    def formats_html5(self):
        """ 
        Subset of video formats to use with HTML5 browsers 
        """
        HTML5_FORMATS = {'mp4': 'video/mp4', 'ogv':'video/ogg', 'webm': 'video/webm'}
        _formats = []
        for entry in self.formats:
            fmt = entry['format']
            if fmt in HTML5_FORMATS:
                _formats.append({'format': fmt, 'url': entry['url'], 'mimetype': HTML5_FORMATS[fmt]})
        return _formats

    def format_flash(self):
        """ 
        Returns the flash video file if available 
        """
        for entry in self.formats:
            if entry['format'] == 'flv':
                return {'format': entry['format'], 'url': entry['url']}
        return {}

    @property
    def poster(self):
        """
        Image file to use as poster in the video display
        """
        try:
            ext = 'png'
            url = self.file.get_format_url(ext)
            filepath = self.file.get_format_filepath(ext)
            return {'url': url, 'format':ext, 'filepath':filepath}
        except Exception, e:
            return {'url': '', 'format':ext, 'filepath':''}

    def convert(self):
        """
        Conversion of video file to alternative formats and capture of 
        poster image file
        """
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

    def _move_file(self):
        """
        Move the file from src to dst.
        """
        src_file_name = self.file.name
        dst_file_name = self._meta.get_field('file').generate_filename(
                                                self, self.original_filename)

        if self.is_public:
            src_storage = self.file.storages['private']
            dst_storage = self.file.storages['public']
            src_fmt_storage = self.file.format_storages['private']
            dst_fmt_storage = self.file.format_storages['public']
        else:
            src_storage = self.file.storages['public']
            dst_storage = self.file.storages['private']
            src_fmt_storage = self.file.format_storages['public']
            dst_fmt_storage = self.file.format_storages['private']
        extensions = [f['format'] for f in self.formats]
        if self.poster['filepath']:
            extensions.append('png')

        # delete the thumbnail
        # We are toggling the is_public to make sure that easy_thumbnails can
        # delete the thumbnails
        self.is_public = not self.is_public
        self.file.delete_thumbnails()
        self.is_public = not self.is_public
        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = src_storage.open(src_file_name)
        src_file.open()
        newfile = dst_storage.save(dst_file_name,
                                     ContentFile(src_file.read()))
        src_storage.delete(src_file_name)
        for ext in extensions:
            src_fmt_name = get_format_name(src_file_name, ext)
            dst_fmt_name = get_format_name(newfile, ext)
            src_file = src_fmt_storage.open(src_fmt_name)
            src_file.open()
            dst_fmt_storage.save(dst_fmt_name,
                                         ContentFile(src_file.read()))
            src_file.close()
            src_fmt_storage.delete(src_fmt_name)
        self.file = newfile

    def _copy_file(self, destination, overwrite=False):
        """
        Copies the file to a destination files and returns it.
        """
        if overwrite:
            # If the destination file already exists default storage backend
            # does not overwrite it but generates another filename.
            # TODO: Find a way to override this behavior.
            raise NotImplementedError

        src_file_name = self.file.name
        stg_type = 'public' if self.is_public else 'private'
        storage = self.file.storages[stg_type]
        fmt_storage = self.file.format_storages[stg_type]
        extensions = [f['format'] for f in self.formats]
        if self.poster['filepath']:
            extensions.append('png')

        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = storage.open(src_file_name)
        src_file.open()
        newfile = storage.save(destination, ContentFile(src_file.read()))

        for ext in extensions:
            src_fmt_name = get_format_name(src_file_name, ext)
            dst_fmt_name = get_format_name(newfile, ext)
            src_file = fmt_storage.open(src_fmt_name)
            src_file.open()
            fmt_storage.save(dst_fmt_name, ContentFile(src_file.read()))
            src_file.close()

        return newfile