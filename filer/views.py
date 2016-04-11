#-*- coding: utf-8 -*-
def popup_status(request):
    return ('_popup' in request.GET or '_popup' in request.POST
            or 'pop' in request.GET or 'pop' in request.POST)


def selectfolder_status(request):
    return 'select_folder' in request.GET or 'select_folder' in request.POST


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

def current_site_param(request, separator="&"):
    current_site = get_param_from_request(request, 'current_site')
    if current_site:
        return '%scurrent_site=%s' % (separator, current_site)
    return ""


def get_param_from_request(request, param, default=None):
    return request.POST.get(param) or request.GET.get(param) or default
