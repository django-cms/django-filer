# encoding: utf-8
"""
Interface with FFMPEG for operations on video files. The actions performed
include conversion of video formats, extraction of information and creation
of poster image file.
"""
import commands
import os
import re
import sys
import traceback
from filer import settings as filer_settings

FFMPEG_DIMENSIONS_RE = re.compile(r'Stream.*Video.*([0-9]{3,})x([0-9]{3,})')


def get_dimensions(sourcefile):
    """Returns the video dimensions for a video file"""
    ffmpeg = filer_settings.FFMPEG_CHECK_CMD % {'input_file': commands.mkarg(sourcefile)}
    try:
        ffmpegresult = commands.getoutput(ffmpeg)
        return get_dimensions_from_output(ffmpegresult)
    except:
        return 0, 0


def get_dimensions_from_output(ffmpeg_output):
    """ Returns the video dimensions from the output of FFMPEG """
    dim_match = FFMPEG_DIMENSIONS_RE.search(ffmpeg_output)
    if dim_match and len(dim_match.groups()) == 2:
        return int(dim_match.groups()[0]), int(dim_match.groups()[1])
    else:
        return 0, 0


def get_size_arg(dimensions):
    if not dimensions:
        return ''
    return filer_settings.FFMPEG_SIZE_ARGUMENT % {'dimensions': commands.mkarg(dimensions)}


def execute_ffmpeg_command(com, targetfile):
    try:
        ffmpegresult = commands.getoutput(com)
        # Check if file exists and is > 0 Bytes
        try:
            s = os.stat(targetfile)
            fsize = s.st_size
            if (fsize == 0):
                os.remove(targetfile)
                return True, "\n".join([com, ffmpegresult])
        except:
            return True, "\n".join([com, ffmpegresult])
    except:
        return True, traceback.format_exc()
    return False, ffmpegresult


def convert_video(sourcefile, path, extension, dimensions):
    """returns True, msg if error or False, msg if ok"""
    original_path, filename = os.path.split(sourcefile)
    if sourcefile is None:
        return True, "Sourcefile does not exist"
    filebase, original_ext = os.path.splitext(filename)
    convfilename = "%s.%s" % (filebase, extension)
    targetfile = os.path.join(path, convfilename)
    if not os.path.exists(path):
        os.makedirs(path)
    cmd_options = {'input_file': commands.mkarg(sourcefile),
                   'format': commands.mkarg(extension),
                   'dimensions': get_size_arg(dimensions),
                   'target_file': commands.mkarg(targetfile)
                   }
    ffmpeg = filer_settings.FFMPEG_CMD % cmd_options
    return execute_ffmpeg_command(ffmpeg, targetfile)


def grab_poster(sourcefile, path, dimensions):
    """returns True, msg if error or False, msg if ok"""
    original_path, filename = os.path.split(sourcefile)
    if sourcefile is None:
        return True, "Sourcefile does not exist"
    filebase, original_ext = os.path.splitext(filename)
    thumbnailfilename = "%s.png" % filebase
    thumbnailfile = os.path.join(path, thumbnailfilename)
    if not os.path.exists(path):
        os.makedirs(path)
    cmd_options = {'input_file': commands.mkarg(sourcefile),
                   'target_file': commands.mkarg(thumbnailfile),
                   'dimensions': get_size_arg(dimensions)
                   }
    grabimage = filer_settings.GRABIMG_CMD % cmd_options
    return execute_ffmpeg_command(grabimage, thumbnailfile)
