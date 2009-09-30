import os
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.sessions.models import Session
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from models import Folder, Image, Clipboard, ClipboardItem, File
from models import tools
from models import FolderRoot, UnfiledImages, ImagesWithMissingData
from django.contrib.auth.models import User

from django import forms

from django.contrib import admin

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
    folder=None
    return render_to_response('admin/filer/folder/folder_edit.html', {
            'folder':folder,
            'is_popup': request.REQUEST.has_key('_popup') or request.REQUEST.has_key('pop'),
        }, context_instance=RequestContext(request))

@login_required
def edit_image(request, folder_id):
    # TODO: implement edit_image view
    folder=None
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
        model=Image
        #fields = ('file',)
        
from filer.utils.files import generic_handle_file

@login_required
def upload(request):
    return render_to_response('filer/upload.html', {
                    'title': u'Upload files',
                    'is_popup': popup_status(request),
                    }, context_instance=RequestContext(request))


@login_required
def paste_clipboard_to_folder(request):
    if request.method=='POST':
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
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.discard_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

@login_required
def delete_clipboard(request):
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        tools.delete_clipboard(clipboard)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )


@login_required
def clone_files_from_clipboard_to_folder(request):
    if request.method=='POST':
        clipboard = Clipboard.objects.get( id=request.POST.get('clipboard_id') )
        folder = Folder.objects.get( id=request.POST.get('folder_id') )
        tools.clone_files_from_clipboard_to_folder(clipboard, folder)
    return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )

class ImageExportForm(forms.Form):
    FORMAT_CHOICES = (
        ('jpg', 'jpg'),
        ('png', 'png'),
        ('gif', 'gif'),
        #('tif', 'tif'),
    )
    format = forms.ChoiceField(choices=FORMAT_CHOICES)
    
    crop = forms.BooleanField(required=False)
    upscale = forms.BooleanField(required=False)
    
    width = forms.IntegerField()
    height = forms.IntegerField()
    
"""  
import filters
@login_required
def export_image(request, image_id):
    image = Image.objects.get(id=image_id)
    
    if request.method=='POST':
        form = ImageExportForm(request.POST)
        if form.is_valid():
            resize_filter = filters.ResizeFilter()
            im = filters.Image.open(image.file.path)
            format = form.cleaned_data['format']
            if format=='png':
                mimetype='image/jpg'
                pil_format = 'PNG'
            #elif format=='tif':
            #    mimetype='image/tiff'
            #    pil_format = 'TIFF'
            elif format=='gif':
                mimetype='image/gif'
                pil_format = 'GIF'
            else:
                mimetype='image/jpg'
                pil_format = 'JPEG'
            im = resize_filter.render(im,
                    size_x=int(form.cleaned_data['width']), 
                    size_y=int(form.cleaned_data['height']), 
                    crop=form.cleaned_data['crop'],
                    upscale=form.cleaned_data['upscale']
            )
            response = HttpResponse(mimetype='%s' % mimetype)
            response['Content-Disposition'] = 'attachment; filename=exported_image.%s' % format
            im.save(response, pil_format)
            return response
    else:
        form = ImageExportForm(initial={'crop': True, 'width': image.file.width, 'height':image.file.height})
    return render_to_response('filer/image_export_form.html', {
            'form': form,
            'image': image
    }, context_instance=RequestContext(request)) 
"""