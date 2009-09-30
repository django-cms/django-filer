try:
    import Image
    import ExifTags
except ImportError:
    try:
        from PIL import Image
        from PIL import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from filer.utils import pexif

def get_exif(im):
    try:
        exif_raw = im._getexif() or {}
    except:
        return {}
    ret={}
    for tag, value in exif_raw.items():
        decoded = ExifTags.TAGS.get(tag, tag)
        ret[decoded] = value
    return ret
def get_exif_for_file(file):
    im = Image.open(file,'r')
    return get_exif(im)
def get_subject_location(exif_data):
    try:
        r = ( int(exif_data['SubjectLocation'][0]), int(exif_data['SubjectLocation'][1]), )
    except:
        r = None
    return r

import StringIO
def set_exif_subject_location(xy, fd_source, out_path):
    try:
        img = pexif.JpegFile.fromFd(fd_source)
    except pexif.JpegFile.InvalidFile, e:
        im = Image.open(fd_source)
        #new_file_without_exif = StringIO.StringIO()
        new_file_without_exif = StringIO.StringIO()
        im.save(new_file_without_exif, format="JPEG")
        img = pexif.JpegFile.fromString(new_file_without_exif.getvalue())
        new_file_without_exif.close()
    img.exif.primary.ExtendedEXIF.SubjectLocation = xy
    img.writeFile(out_path)