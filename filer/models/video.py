# encoding: utf-8
"""handles all conversion tasks - originally only video but now also for PDF"""

import os, sys, commands, os.path
from django.conf import settings
#from filebrowser.views import filebrowser_post_upload
from imagemodels import Video

def is_widescreen(path, full=False):
    path = os.path.dirname(path) if full else path
    return 'widescreen' in os.path.split(path) #lol


#@receiver(post_save, sender=Video)
#def post_upload_callback(sender, **kwargs):
    #"""
    #Receiver function called each time an upload has finished.

    #kwargs['path'] is the URL path, not the FS path
    #"""
    #if kwargs['file'].filetype == "Video" and kwargs['file'].extension != '.flv':
        #path = os.path.dirname(kwargs['file'].path_full)
        #task = VideoTask(path=path, filename=kwargs['file'].filename, extension=kwargs['file'].extension, status='new')
        #task.save()
    ##elif kwargs['file'].filetype == "Document" and kwargs['file'].extension == '.pdf':
        ##path = os.path.dirname(kwargs['file'].path_full)
        ##task = PdfTask(path=path, filename=kwargs['file'].filename, extension=kwargs['file'].extension, status='new')
        ##task.save()
# FIXME HOOK
#filebrowser_post_upload.connect(post_upload_callback)

# Podia estar no método save do modelo :-P
#from django.db.models.signals import post_save
#from django.dispatch import receiver
#@receiver(post_save, sender=Video)
#def pre_save_callback(sender, instance, **kwargs):
    #path = instance.original.path
    #path, filename = os.path.split(path) #os.path.dirname(kwargs['file'].path_full)
    #extension = os.path.splitext(filename)[1]
    #task = VideoTask(path=path, filename=filename, extension=extension, status='new')
    #task.save()

def convert_video(original_path, path, filename, extension):
    """returns True, msg if error or False, msg if ok"""
    sourcefile = os.path.join(original_path, filename)
    if sourcefile is None:
        return True, "Sourcefile does not exist"
    filebase = filename[:-len(extension)]
    flvfilename = "%s.flv" % filebase
    thumbnailfilename = "%s.png" % filebase
    targetfile = os.path.join(path, flvfilename)
    thumbnailfile = os.path.join(path, thumbnailfilename)

    if not os.path.exists(path):
        os.makedirs(path)
    command_str = settings.FFMPEG_WIDE_CMD if is_widescreen(path) else settings.FFMPEG_CMD
    ffmpeg = command_str % (commands.mkarg(sourcefile),  commands.mkarg(targetfile))
    grabimage = settings.GRABIMG_CMD % (commands.mkarg(sourcefile), commands.mkarg(thumbnailfile))
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
        grab = commands.getoutput(grabimage)
    except:
        return True, sys.exc_info[1]
    return False, "\n".join([ffmpegresult, grab])

