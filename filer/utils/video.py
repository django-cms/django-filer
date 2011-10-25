# encoding: utf-8
"""handles all conversion tasks - originally only video but now also for PDF"""

import os, sys, commands, os.path
from django.conf import settings

def convert_video(sourcefile, path, extension):
    """returns True, msg if error or False, msg if ok"""
    original_path, filename = os.path.split(sourcefile)
    if sourcefile is None:
        return True, "Sourcefile does not exist"
    filebase, original_ext = os.path.splitext(filename)
    convfilename = "%s.%s" % (filebase, extension)
    targetfile = os.path.join(path, convfilename)
    if not os.path.exists(path):
        os.makedirs(path)
    command_str = settings.FFMPEG_CMD
    ffmpeg = command_str % (commands.mkarg(sourcefile),  commands.mkarg(targetfile))
    #flvtool = "flvtool2 -U %s" % targetfile
    try:
        ffmpegresult = commands.getoutput(ffmpeg)
        # Check if file exists and is > 0 Bytes
        try:
            s = os.stat(targetfile)
            fsize = s.st_size
            if (fsize == 0):
                os.remove(targetfile)
                return True, ffmpegresult
        except:
            return True, ffmpegresult
        #flvresult = commands.getoutput(flvtool)
    except:
        return True, sys.exc_info[1]
    return False, ffmpegresult

def grab_poster(sourcefile, path):
    """returns True, msg if error or False, msg if ok"""
    original_path, filename = os.path.split(sourcefile)
    if sourcefile is None:
        return True, "Sourcefile does not exist"
    filebase, original_ext = os.path.splitext(filename)
    thumbnailfilename = "%s.png" % filebase
    thumbnailfile = os.path.join(path, thumbnailfilename)
    if not os.path.exists(path):
        os.makedirs(path)
    grabimage = settings.GRABIMG_CMD % (commands.mkarg(sourcefile), commands.mkarg(thumbnailfile))
    #flvtool = "flvtool2 -U %s" % targetfile
    try:
        grab = commands.getoutput(grabimage)
    except:
        return True, sys.exc_info[1]
    return False, grab
