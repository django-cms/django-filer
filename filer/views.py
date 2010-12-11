from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseServerError
from django.core.exceptions import PermissionDenied

from models import Folder, Image, Clipboard, File
from models import tools

from django import forms
from django.conf import settings as django_settings
from settings import static_server, FILER_STATICMEDIA_PREFIX
import os, posixpath


class NewFolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name', )

def popup_status(request):
    return request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop')
def selectfolder_status(request):
    return request.REQUEST.has_key('select_folder')
def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""
def _userperms(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append( p )
    return r
    
@login_required
def edit_folder(request, folder_id):
    # TODO: implement edit_folder view
    folder = None
    return render_to_response('admin/filer/folder/folder_edit.html', {
            'folder':folder,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
        }, context_instance=RequestContext(request))

@login_required
def edit_image(request, folder_id):
    # TODO: implement edit_image view
    folder = None
    return render_to_response('filer/image_edit.html', {
            'folder':folder,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
        }, context_instance=RequestContext(request))

@login_required
def make_folder(request, folder_id=None):
    if not folder_id:
        folder_id = request.REQUEST.get('parent_id', None)
    if folder_id:
        folder = Folder.objects.get(id=folder_id)
    else:
        folder = None
        
    if request.user.is_superuser:
        pass
    elif folder == None:
        # regular users may not add root folders
        raise PermissionDenied
    elif not folder.has_add_children_permission(request):
        # the user does not have the permission to add subfolders
        raise PermissionDenied
    
    if request.method == 'POST':
        new_folder_form = NewFolderForm(request.POST)
        if new_folder_form.is_valid():
            new_folder = new_folder_form.save(commit=False)
            new_folder.parent = folder
            new_folder.owner = request.user
            new_folder.save()
            #print u"Saving folder %s as child of %s" % (new_folder, folder)
            return HttpResponse('<script type="text/javascript">opener.dismissPopupAndReload(window);</script>')
    else:
        #print u"New Folder GET, parent %s" % folder
        new_folder_form = NewFolderForm()
    return render_to_response('admin/filer/folder/new_folder_form.html', {
            'new_folder_form': new_folder_form,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
    }, context_instance=RequestContext(request))

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = Image
        #fields = ('file',)
        

@login_required
def upload(request):
    return render_to_response('filer/upload.html', {
                    'title': u'Upload files',
                    'is_popup': popup_status(request),
                    }, context_instance=RequestContext(request))


@login_required
def paste_clipboard_to_folder(request):
    if request.method == 'POST':
        folder = Folder.objects.get( id=request.POST.get('folder_id') )
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        if folder.has_add_children_permission(request):
            tools.move_files_from_clipboard_to_folder(clipboard, folder)
            tools.discard_clipboard(clipboard)
        else:
            raise PermissionDenied
    return HttpResponseRedirect( '%s%s' % (request.REQUEST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def discard_clipboard(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.discard_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def delete_clipboard(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.delete_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )


@login_required
def clone_files_from_clipboard_to_folder(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        folder = Folder.objects.get( id=request.POST.get('folder_id') )
        tools.clone_files_from_clipboard_to_folder(clipboard, folder)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def serve_protected_file(request, file_id):
    """
    Serve protected files to authenticated users with read permissions.
    """
    thefile = File.objects.get(id = file_id)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        raise PermissionDenied
    if static_server != None:
        #print "thefile.url", thefile.url
        #print "thefile.file.url", thefile.file.url
        direct_url = thefile.file.url
        return static_server.serve(request, direct_url, thefile.file.name, thefile.file.path, thefile.file.size)
    return HttpResponseServerError('Misconfigured. Can not serve protected files.')

def serve_protected_thumbnail(request, file_id, file_name):
    """
    Serve protected thumbnails.
    If the user isn't authenticated or doesn't have read permissions,
    redirect to a static image.
    """
    if not request.user.is_authenticated():
        newurl = posixpath.join(FILER_STATICMEDIA_PREFIX, "icons/image_32x32.png")
        return HttpResponseRedirect(newurl)
    return serve_protected_thumbnail_auth(request, file_id, file_name)

@login_required
def serve_protected_thumbnail_auth(request, file_id, file_name):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    thefile = File.objects.get(id = file_id)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        newurl = posixpath.join(FILER_STATICMEDIA_PREFIX, "icons/image_32x32.png")
        return HttpResponseRedirect(newurl)
    if static_server != None:
        try:
            # we don't care about the options because they're in file_name
            # so we just pass the required size option
            name = thefile.file.get_thumbnail_name(thumbnail_options = { 'size': (1,1)})
            media_path = posixpath.join(posixpath.dirname(name), file_name)
            full_path = posixpath.join(django_settings.MEDIA_ROOT, media_path)
            direct_url = posixpath.join(django_settings.MEDIA_URL, media_path)
            size = os.path.getsize(full_path) # XXX: Should convert full_path from posix to os.path format
            return static_server.serve(request, direct_url, media_path, full_path, size)
        except Exception as e:
            print " *** ", e
            raise Http404('File not found')
    return HttpResponseServerError('Misconfigured. Can not serve protected files.')

def direct_file_access(request, path):
    if static_server != None:
        return static_server.direct_access(request, path)
    return HttpResponseServerError('Misconfigured. Can not serve protected files.')
