#-*- coding: utf-8 -*-
try:
    from PIL import Image
    from PIL import ExifTags
except ImportError:
    try:
        import Image
        import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")


def get_exif(im):
    try:
        exif_raw = im._getexif() or {}
    except:
        return {}
    ret = {}
    for tag, value in exif_raw.items():
        decoded = ExifTags.TAGS.get(tag, tag)
        ret[decoded] = value
    return ret


def get_exif_for_file(file_obj):
    im = Image.open(file_obj, 'r')
    return get_exif(im)


def get_subject_location(exif_data):
    try:
        r = (int(exif_data['SubjectLocation'][0]), int(exif_data['SubjectLocation'][1]),)
    except:
        r = None
    return r
