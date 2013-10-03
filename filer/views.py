#-*- coding: utf-8 -*-
def popup_status(request):
    return ('_popup' in request.REQUEST or 'pop' in request.REQUEST)


def selectfolder_status(request):
    return ('select_folder' in request.REQUEST)


def popup_param(request, separator="?"):
    if popup_status(request):
        return "%s_popup=1" % separator
    else:
        return ""


def selectfolder_param(request, separator="&"):
    if selectfolder_status(request):
        return "%sselect_folder=1" % separator
    else:
        return ""
