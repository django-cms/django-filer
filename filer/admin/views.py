# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import forms
from django.contrib.admin import widgets
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from .. import settings as filer_settings
from ..models import Clipboard, Folder, FolderRoot, tools
from .tools import AdminContext, admin_url_params_encoded, popup_status


class NewFolderForm(forms.ModelForm):
    class Meta(object):
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
                new_folder.parent = folder
                new_folder.owner = request.user
                new_folder.save()
                return render(request, 'admin/filer/dismiss_popup.html')
    else:
        new_folder_form = NewFolderForm()
    return render(request, 'admin/filer/folder/new_folder_form.html', {
        'opts': Folder._meta,
        'new_folder_form': new_folder_form,
        'is_popup': popup_status(request),
        'filer_admin_context': AdminContext(request),
    })


@login_required
def paste_clipboard_to_folder(request):
    if True:
        # TODO: cleanly remove Clipboard code if it is no longer needed
        return HttpResponseBadRequest('not implemented anymore')

    if request.method == 'POST':
        folder = Folder.objects.get(id=request.POST.get('folder_id'))
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        if folder.has_add_children_permission(request):
            tools.move_files_from_clipboard_to_folder(clipboard, folder)
            tools.discard_clipboard(clipboard)
        else:
            raise PermissionDenied
    redirect = request.GET.get('redirect_to', '')
    if not redirect:
        redirect = request.POST.get('redirect_to', '')
    return HttpResponseRedirect(
        '{0}?order_by=-modified_at{1}'.format(
            redirect,
            admin_url_params_encoded(request, first_separator='&'),
        )
    )


@login_required
def discard_clipboard(request):
    if True:
        # TODO: cleanly remove Clipboard code if it is no longer needed
        return HttpResponseBadRequest('not implemented anymore')

    if request.method == 'POST':
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        tools.discard_clipboard(clipboard)
    return HttpResponseRedirect(
        '{0}{1}'.format(
            request.POST.get('redirect_to', ''),
            admin_url_params_encoded(request, first_separator='&'),
        )
    )


@login_required
def delete_clipboard(request):
    if True:
        # TODO: cleanly remove Clipboard code if it is no longer needed
        return HttpResponseBadRequest('not implemented anymore')

    if request.method == 'POST':
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        tools.delete_clipboard(clipboard)
    return HttpResponseRedirect(
        '{0}{1}'.format(
            request.POST.get('redirect_to', ''),
            admin_url_params_encoded(request, first_separator='&'),
        )
    )
