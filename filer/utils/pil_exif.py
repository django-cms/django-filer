# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.core.files.storage import default_storage as storage

from ..utils.compatibility import PILExifTags, PILImage


def get_exif(im):
    try:
        exif_raw = im._getexif() or {}
    except:  # noqa
        return {}
    ret = {}
    for tag, value in list(exif_raw.items()):
        decoded = PILExifTags.TAGS.get(tag, tag)
        ret[decoded] = value
    return ret


def get_exif_for_file(file_obj):
    im = PILImage.open(storage.open(file_obj.name), 'r')
    return get_exif(im)


def get_subject_location(exif_data):
    try:
        r = (int(exif_data['SubjectLocation'][0]), int(exif_data['SubjectLocation'][1]),)
    except:  # noqa
        r = None
    return r
