import os
#import zipfile
# zipfile.open() is only available in Python 2.6, so we use the future version
from django.core.files.uploadedfile import SimpleUploadedFile
from filer.utils import zipfile

def unzip(file):
    """
    Take a path to a zipfile and checks if it is a valid zip file
    and returns...
    """
    files = []
    # TODO: implement try-except here
    zip = zipfile.ZipFile(file)
    bad_file = zip.testzip()
    if bad_file:
        raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)
    infolist = zip.infolist()
    print infolist
    for zipinfo in infolist:
        print "handling %s" % zipinfo.filename
        if zipinfo.filename.startswith('__'): # do not process meta files
            continue
        thefile = SimpleUploadedFile(name=zipinfo.filename, content=zip.read(zipinfo))
        files.append( (thefile, zipinfo.filename) )
    zip.close()
    return files
