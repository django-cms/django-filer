#-*- coding: utf-8 -*-
import os
from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from filer.utils.zip import unzip

def generic_handle_file(file, original_filename):
    """
    Handels a file, regardless if a package or a single file and returns
    a list of files. can recursively unpack packages.
    """
    files = []
    filetype = os.path.splitext(original_filename)[1].lower()
    if filetype=='.zip':
        unpacked_files = unzip(file)
        for ufile, ufilename in unpacked_files:
            files += generic_handle_file(ufile, ufilename)
    else:
        files.append( (file,original_filename) )
    return files


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
        return u"%s.%s" % (filename, ext)
    else:
        return u"%s" % (filename,)
