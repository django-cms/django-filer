from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseBadRequest
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from .. import settings as filer_settings
from ..models import Folder, FolderRoot
from .tools import AdminContext, popup_status


class NewFolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name',)
        widgets = {
            'name': widgets.AdminTextInputWidget,
        }


@login_required
def make_folder(request, folder_id=None):
    if not folder_id:
        folder_id = request.GET.get('parent_id')
    if not folder_id:
        folder_id = request.POST.get('parent_id')
    if folder_id:
        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            raise PermissionDenied
    else:
        folder = None

    if request.user.is_superuser:
        pass
    elif folder is None:
        # regular users may not add root folders unless configured otherwise
        if not filer_settings.FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS:
            raise PermissionDenied
    elif not folder.has_add_children_permission(request):
        # the user does not have the permission to add subfolders
        raise PermissionDenied

    if request.method == 'POST':
        new_folder_form = NewFolderForm(request.POST)
        if new_folder_form.is_valid():
            new_folder = new_folder_form.save(commit=False)
            if (folder or FolderRoot()).contains_folder(new_folder.name):
                new_folder_form._errors['name'] = new_folder_form.error_class(
                    [_('Folder with this name already exists.')])
            else:
                context = admin.site.each_context(request)
                new_folder.parent = folder
                new_folder.owner = request.user
                new_folder.save()
                return TemplateResponse(request, 'admin/filer/dismiss_popup.html', context)
    else:
        new_folder_form = NewFolderForm()

    context = admin.site.each_context(request)
    context.update({
        'opts': Folder._meta,
        'new_folder_form': new_folder_form,
        'is_popup': popup_status(request),
        'filer_admin_context': AdminContext(request),
    })
    return TemplateResponse(request, 'admin/filer/folder/new_folder_form.html', context)


# The clipboard operations are no longer part of the file browser. The views are
# kept - and answer 400 - so that projects still linking to them do not run into
# a NoReverseMatch.
@login_required
def paste_clipboard_to_folder(request):
    return HttpResponseBadRequest('not implemented anymore')


@login_required
def discard_clipboard(request):
    return HttpResponseBadRequest('not implemented anymore')


@login_required
def delete_clipboard(request):
    return HttpResponseBadRequest('not implemented anymore')
