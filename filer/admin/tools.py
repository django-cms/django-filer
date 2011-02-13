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


# Simple upload: keep last 5 folders that were either changed or Upload was started from them
def register_recent_folder(folder_id, request):
    if folder_id == None or folder_id == "": 
        return
    folder_id = "%s" % folder_id
    hist = request.session.get('filer_recent_uploads', None)
    if hist == None:
        hist = folder_id
    else:
        hist = [ fid for fid in hist.split(',') if fid != '' ]
        if folder_id in hist:
            hist.remove(folder_id)
        hist.insert(0, folder_id)
        hist= ','.join(hist[:5])

    request.session['filer_recent_uploads'] = hist
