def popup_status(request):
    return request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop')
def selectfolder_status(request):
    return request.REQUEST.has_key('select_folder')
def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""
def userperms_for_request(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append( p )
    return r