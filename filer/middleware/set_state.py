# encoding: utf-8

class GetSelectionState(object):
    """ This middleware checks for select_folder parameter in the URL query
    and saves the state in session.
    Is responsibilty of javascript dismissRelatedImageLookupPopup / dismissRelatedFolderLookupPopup
    to call reset_selection view to reset parameter in the session
    """
    def process_request(self, request):
        if request.GET.get("select_folder",False):
            request.session["select_folder"] = True
        if request.GET.get("_popup",False):
            request.session["_popup"] = True
        if request.GET.get("pop",False):
            request.session["_popup"] = True
