# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import itertools
import os
import re
from collections import OrderedDict

from django import forms
from django.conf import settings as django_settings
from django.conf.urls import url
from django.contrib import messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models, router
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.http import urlquote, urlunquote
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy, ungettext

from .. import settings
from ..models import (
    File, Folder, FolderPermission, FolderRoot, ImagesWithMissingData,
    UnsortedImages, tools,
)
from ..settings import FILER_IMAGE_MODEL, FILER_PAGINATE_BY
from ..thumbnail_processors import normalize_subject_location
from ..utils.compatibility import (
    capfirst, get_delete_permission, quote, reverse, unquote,
)
from ..utils.filer_easy_thumbnails import FilerActionThumbnailer
from ..utils.loader import load_model
from . import views
from .forms import CopyFilesAndFoldersForm, RenameFilesForm, ResizeImagesForm
from .patched.admin_utils import get_deleted_objects
from .permissions import PrimitivePermissionAwareModelAdmin
from .tools import (
    AdminContext, admin_url_params_encoded, check_files_edit_permissions,
    check_files_read_permissions, check_folder_edit_permissions,
    check_folder_read_permissions, popup_status, userperms_for_request,
)


Image = load_model(FILER_IMAGE_MODEL)


class AddFolderPopupForm(forms.ModelForm):
    folder = forms.HiddenInput()

    class Meta(object):
        model = Folder
        fields = ('name',)


class FolderAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('name',)
    exclude = ('parent',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', ]
    raw_id_fields = ('owner',)
    save_as = True  # see ImageAdmin
    actions = ['delete_files_or_folders', 'move_files_and_folders',
               'copy_files_and_folders', 'resize_images', 'rename_files']

    directory_listing_template = 'admin/filer/folder/directory_listing.html'
    order_by_file_fields = ('_file_size', 'original_filename', 'name', 'owner',
                            'uploaded_at', 'modified_at')

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        parent_id = request.GET.get('parent_id', None)
        if not parent_id:
            parent_id = request.POST.get('parent_id', None)
        if parent_id:
            return AddFolderPopupForm
        else:
            folder_form = super(FolderAdmin, self).get_form(
                request, obj=None, **kwargs)

            def folder_form_clean(form_obj):
                cleaned_data = form_obj.cleaned_data
                folders_with_same_name = self.get_queryset(request).filter(
                    parent=form_obj.instance.parent,
                    name=cleaned_data['name'])
                if form_obj.instance.pk:
                    folders_with_same_name = folders_with_same_name.exclude(
                        pk=form_obj.instance.pk)
                if folders_with_same_name.exists():
                    raise ValidationError(
                        'Folder with this name already exists.')
                return cleaned_data

            # attach clean to the default form rather than defining a new form class
            folder_form.clean = folder_form_clean
            return folder_form

    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        r = form.save(commit=False)
        parent_id = request.GET.get('parent_id', None)
        if not parent_id:
            parent_id = request.POST.get('parent_id', None)
        if parent_id:
            parent = self.get_queryset(request).get(id=parent_id)
            r.parent = parent
        return r

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        """
        if (
            request.POST
            and '_continue' not in request.POST
            and '_saveasnew' not in request.POST
            and '_addanother' not in request.POST
        ):

            if obj.parent:
                url = reverse('admin:filer-directory_listing',
                              kwargs={'folder_id': obj.parent.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            url = "{0}{1}".format(
                url,
                admin_url_params_encoded(request),
            )
            return HttpResponseRedirect(url)
        return super(FolderAdmin, self).response_change(request, obj)

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        info = self.model._meta.app_label, self.model._meta.model_name
        extra_context = {'show_delete': True,
                         'history_url': 'admin:%s_%s_history' % info,
                         'is_popup': popup_status(request),
                         'filer_admin_context': AdminContext(request)}
        context.update(extra_context)
        return super(FolderAdmin, self).render_change_form(
            request=request, context=context, add=add,
            change=change, form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a folder.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.

        The delete_view breaks with polymorphic models if the cascade will
        try delete objects that are of different polymorphic types
        (AttributeError: 'File' object has no attribute 'file_ptr').
        The default implementation of the delete_view is hard to override
        without just copying the whole big thing. Since we've already done
        the overriding work on the delete_files_or_folders admin action, we
        can re-use that here instead.
        """
        try:
            obj = self.get_queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.parent
        except self.model.DoesNotExist:
            parent_folder = None

        if request.POST:
            self.delete_files_or_folders(
                request,
                files_queryset=File.objects.none(),
                folders_queryset=self.get_queryset(request).filter(id=object_id)
            )
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                              kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            url = "{0}{1}".format(
                url,
                admin_url_params_encoded(request),
            )
            return HttpResponseRedirect(url)

        return self.delete_files_or_folders(
            request,
            files_queryset=File.objects.none(),
            folders_queryset=self.get_queryset(request).filter(id=object_id)
        )

    def icon_img(self, xs):
        return mark_safe(('<img src="%simg/icons/plainfolder_32x32.png" '
                          'alt="Folder Icon" />') % django_settings.MEDIA_ROOT)
    icon_img.allow_tags = True

    def get_urls(self):
        return [
            # we override the default list view with our own directory listing
            # of the root directories
            url(r'^$',
                self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing-root'),

            url(r'^last/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'last'},
                name='filer-directory_listing-last'),

            url(r'^(?P<folder_id>\d+)/list/$',
                self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing'),

            url(r'^(?P<folder_id>\d+)/make_folder/$',
                self.admin_site.admin_view(views.make_folder),
                name='filer-directory_listing-make_folder'),
            url(r'^make_folder/$',
                self.admin_site.admin_view(views.make_folder),
                name='filer-directory_listing-make_root_folder'),

            url(r'^images_with_missing_data/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'images_with_missing_data'},
                name='filer-directory_listing-images_with_missing_data'),

            url(r'^unfiled_images/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'unfiled_images'},
                name='filer-directory_listing-unfiled_images'),
        ] + super(FolderAdmin, self).get_urls()

    # custom views
    def directory_listing(self, request, folder_id=None, viewtype=None):
        clipboard = tools.get_user_clipboard(request.user)
        if viewtype == 'images_with_missing_data':
            folder = ImagesWithMissingData()
        elif viewtype == 'unfiled_images':
            folder = UnsortedImages()
        elif viewtype == 'last':
            last_folder_id = request.session.get('filer_last_folder_id')
            try:
                self.get_queryset(request).get(id=last_folder_id)
            except self.model.DoesNotExist:
                url = reverse('admin:filer-directory_listing-root')
                url = "%s%s" % (url, admin_url_params_encoded(request))
            else:
                url = reverse('admin:filer-directory_listing', kwargs={'folder_id': last_folder_id})
                url = "%s%s" % (url, admin_url_params_encoded(request))
            return HttpResponseRedirect(url)
        elif folder_id is None:
            folder = FolderRoot()
        else:
            folder = get_object_or_404(self.get_queryset(request), id=folder_id)
        request.session['filer_last_folder_id'] = folder_id

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)

        # Remove action checkboxes if there aren't any actions available.
        list_display = list(self.list_display)
        if not actions:
            try:
                list_display.remove('action_checkbox')
            except ValueError:
                pass

        # search
        q = request.GET.get('q', None)
        if q:
            search_terms = urlunquote(q).split(" ")
            search_mode = True
        else:
            search_terms = []
            q = ''
            search_mode = False
        # Limit search results to current folder.
        limit_search_to_folder = request.GET.get('limit_search_to_folder',
                                                 False) in (True, 'on')

        if len(search_terms) > 0:
            if folder and limit_search_to_folder and not folder.is_root:
                # Do not include current folder itself in search results.
                folder_qs = folder.get_descendants(include_self=False)
                # Limit search results to files in the current folder or any
                # nested folder.
                file_qs = File.objects.filter(
                    folder__in=folder.get_descendants(include_self=True))
            else:
                folder_qs = self.get_queryset(request)
                file_qs = File.objects.all()
            folder_qs = self.filter_folder(folder_qs, search_terms)
            file_qs = self.filter_file(file_qs, search_terms)

            show_result_count = True
        else:
            folder_qs = folder.children.all()
            file_qs = folder.files.all()
            show_result_count = False

        folder_qs = folder_qs.order_by('name')
        order_by = request.GET.get('order_by', None)
        if order_by is not None:
            order_by = order_by.split(',')
            order_by = [field for field in order_by
                        if re.sub(r'^-', '', field) in self.order_by_file_fields]
            if len(order_by) > 0:
                file_qs = file_qs.order_by(*order_by)

        folder_children = []
        folder_files = []
        if folder.is_root and not search_mode:
            virtual_items = folder.virtual_folders
        else:
            virtual_items = []

        perms = FolderPermission.objects.get_read_id_list(request.user)
        root_exclude_kw = {'parent__isnull': False, 'parent__id__in': perms}
        if perms != 'All':
            file_qs = file_qs.filter(models.Q(folder__id__in=perms) | models.Q(owner=request.user))
            folder_qs = folder_qs.filter(models.Q(id__in=perms) | models.Q(owner=request.user))
        else:
            root_exclude_kw.pop('parent__id__in')
        if folder.is_root:
            folder_qs = folder_qs.exclude(**root_exclude_kw)

        folder_children += folder_qs
        folder_files += file_qs

        try:
            permissions = {
                'has_edit_permission': folder.has_edit_permission(request),
                'has_read_permission': folder.has_read_permission(request),
                'has_add_children_permission':
                    folder.has_add_children_permission(request),
            }
        except:  # noqa
            permissions = {}

        if order_by is None or len(order_by) == 0:
            folder_files.sort()

        items = folder_children + folder_files
        paginator = Paginator(items, FILER_PAGINATE_BY)

        # Are we moving to clipboard?
        if request.method == 'POST' and '_save' not in request.POST:
            # TODO: Refactor/remove clipboard parts
            for f in folder_files:
                if "move-to-clipboard-%d" % (f.id,) in request.POST:
                    clipboard = tools.get_user_clipboard(request.user)
                    if f.has_edit_permission(request):
                        tools.move_file_to_clipboard([f], clipboard)
                        return HttpResponseRedirect(request.get_full_path())
                    else:
                        raise PermissionDenied

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        # Actions with no confirmation
        if (
            actions and request.method == 'POST'
            and 'index' in request.POST
            and '_save' not in request.POST
        ):
            if selected:
                response = self.response_action(request, files_queryset=file_qs, folders_queryset=folder_qs)
                if response:
                    return response
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)

        # Actions with confirmation
        if (
            actions and request.method == 'POST'
            and helpers.ACTION_CHECKBOX_NAME in request.POST
            and 'index' not in request.POST
            and '_save' not in request.POST
        ):
            if selected:
                response = self.response_action(request, files_queryset=file_qs, folders_queryset=folder_qs)
                if response:
                    return response

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None

        selection_note_all = ungettext('%(total_count)s selected',
            'All %(total_count)s selected', paginator.count)

        # If page request (9999) is out of range, deliver last page of results.
        try:
            paginated_items = paginator.page(request.GET.get('page', 1))
        except PageNotAnInteger:
            paginated_items = paginator.page(1)
        except EmptyPage:
            paginated_items = paginator.page(paginator.num_pages)

        context = self.admin_site.each_context(request)
        context.update({
            'folder': folder,
            'clipboard_files': File.objects.filter(
                in_clipboards__clipboarditem__clipboard__user=request.user
            ).distinct(),
            'paginator': paginator,
            'paginated_items': paginated_items,
            'virtual_items': virtual_items,
            'uploader_connections': settings.FILER_UPLOADER_CONNECTIONS,
            'permissions': permissions,
            'permstest': userperms_for_request(folder, request),
            'current_url': request.path,
            'title': _('Directory listing for %(folder_name)s') % {'folder_name': folder.name},
            'search_string': ' '.join(search_terms),
            'q': urlquote(q),
            'show_result_count': show_result_count,
            'folder_children': folder_children,
            'folder_files': folder_files,
            'limit_search_to_folder': limit_search_to_folder,
            'is_popup': popup_status(request),
            'filer_admin_context': AdminContext(request),
            # needed in the admin/base.html template for logout links
            'root_path': reverse('admin:index'),
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
            'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(paginated_items.object_list)},
            'selection_note_all': selection_note_all % {'total_count': paginator.count},
            'media': self.media,
            'enable_permissions': settings.FILER_ENABLE_PERMISSIONS,
            'can_make_folder': request.user.is_superuser or (folder.is_root and settings.FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS) or permissions.get("has_add_children_permission"),
        })
        return render(request, self.directory_listing_template, context)

    def filter_folder(self, qs, terms=()):
        # Source: https://github.com/django/django/blob/1.7.1/django/contrib/admin/options.py#L939-L947  flake8: noqa
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        for term in terms:
            filters = models.Q()
            for filter_ in self.search_fields:
                filters |= models.Q(**{construct_search(filter_): term})
            for filter_ in self.get_owner_filter_lookups():
                filters |= models.Q(**{filter_: term})
            qs = qs.filter(filters)
        return qs

    def filter_file(self, qs, terms=()):
        for term in terms:
            filters = (models.Q(name__icontains=term)
                       | models.Q(description__icontains=term)
                       | models.Q(original_filename__icontains=term))
            for filter_ in self.get_owner_filter_lookups():
                filters |= models.Q(**{filter_: term})
            qs = qs.filter(filters)
        return qs

    @property
    def owner_search_fields(self):
        """
        Returns all the fields that are CharFields except for password from the
        User model.  For the built-in User model, that means username,
        first_name, last_name, and email.
        """
        try:
            from django.contrib.auth import get_user_model
        except ImportError:  # Django < 1.5
            from django.contrib.auth.models import User
        else:
            User = get_user_model()
        return [
            field.name for field in User._meta.fields
            if isinstance(field, models.CharField) and field.name != 'password'
        ]

    def get_owner_filter_lookups(self):
        return [
            'owner__{field}__icontains'.format(field=field)
            for field in self.owner_search_fields
        ]

    def response_action(self, request, files_queryset, folders_queryset):
        """
        Handle an admin action. This is called if a request is POSTed to the
        changelist; it returns an HttpResponse if the action was handled, and
        None otherwise.
        """

        # There can be multiple action forms on the page (at the top
        # and bottom of the change list, for example). Get the action
        # whose button was pushed.
        try:
            action_index = int(request.POST.get('index', 0))
        except ValueError:
            action_index = 0

        # Construct the action form.
        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        # Use the action whose button was pushed
        try:
            data.update({'action': data.getlist('action')[action_index]})
        except IndexError:
            # If we didn't get an action from the chosen form that's invalid
            # POST data, so by deleting action it'll fail the validation check
            # below. So no need to do anything here
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields['action'].choices = self.get_action_choices(request)

        # If the form's valid we can handle the action.
        if action_form.is_valid():
            action = action_form.cleaned_data['action']
            select_across = action_form.cleaned_data['select_across']
            func, name, description = self.get_actions(request)[action]

            # Get the list of selected PKs. If nothing's selected, we can't
            # perform an action on it, so bail. Except we want to perform
            # the action explicitly on all objects.
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
            if not selected and not select_across:
                # Reminder that something needs to be selected or nothing
                # will happen
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)
                return None

            if not select_across:
                selected_files = []
                selected_folders = []

                for pk in selected:
                    if pk[:5] == "file-":
                        selected_files.append(pk[5:])
                    else:
                        selected_folders.append(pk[7:])

                # Perform the action only on the selected objects
                files_queryset = files_queryset.filter(pk__in=selected_files)
                folders_queryset = folders_queryset.filter(
                    pk__in=selected_folders)

            response = func(self, request, files_queryset, folders_queryset)

            # Actions may return an HttpResponse, which will be used as the
            # response from the POST. If not, we'll be a good little HTTP
            # citizen and redirect back to the changelist page.
            if isinstance(response, HttpResponse):
                return response
            else:
                return HttpResponseRedirect(request.get_full_path())
        else:
            msg = _("No action selected.")
            self.message_user(request, msg)
            return None

    def get_actions(self, request):
        if settings.FILER_ENABLE_PERMISSIONS:
            actions = OrderedDict()
            actions['files_set_public'] = self.get_action('files_set_public')
            actions['files_set_private'] = self.get_action('files_set_private')
            actions.update(super(FolderAdmin, self).get_actions(request))
        else:
            actions = super(FolderAdmin, self).get_actions(request)

        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def move_to_clipboard(self, request, files_queryset, folders_queryset):
        """
        Action which moves the selected files and files in selected folders
        to clipboard.
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None

        clipboard = tools.get_user_clipboard(request.user)

        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        # TODO: Display a confirmation page if moving more than X files to
        # clipboard?

        # We define it like that so that we can modify it inside the
        # move_files function
        files_count = [0]

        def move_files(files):
            files_count[0] += tools.move_file_to_clipboard(files, clipboard)

        def move_folders(folders):
            for f in folders:
                move_files(f.files)
                move_folders(f.children.all())

        move_files(files_queryset)
        move_folders(folders_queryset)

        self.message_user(request, _("Successfully moved %(count)d files to "
                                     "clipboard.") % {"count": files_count[0]})

        return None

    move_to_clipboard.short_description = ugettext_lazy(
        "Move selected files to clipboard")

    def files_set_public_or_private(self, request, set_public, files_queryset,
                                    folders_queryset):
        """
        Action which enables or disables permissions for selected files and
        files in selected folders to clipboard (set them private or public).
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        permissions_enabled = settings.FILER_ENABLE_PERMISSIONS

        if request.method != 'POST' or not permissions_enabled:
            return None

        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        # We define it like that so that we can modify it inside the
        # set_files function
        files_count = [0]

        def set_files(files):
            for f in files:
                if f.is_public != set_public:
                    f.is_public = set_public
                    f.save()
                    files_count[0] += 1

        def set_folders(folders):
            for f in folders:
                set_files(f.files)
                set_folders(f.children.all())

        set_files(files_queryset)
        set_folders(folders_queryset)

        if set_public:
            self.message_user(request, _("Successfully disabled permissions for %(count)d files.") % {"count": files_count[0], })
        else:
            self.message_user(request, _("Successfully enabled permissions for %(count)d files.") % {"count": files_count[0], })

        return None

    def files_set_private(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, False, files_queryset,
                                                folders_queryset)

    files_set_private.short_description = ugettext_lazy(
        "Enable permissions for selected files")

    def files_set_public(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, True, files_queryset,
                                                folders_queryset)

    files_set_public.short_description = ugettext_lazy(
        "Disable permissions for selected files")

    def delete_files_or_folders(self, request, files_queryset, folders_queryset):
        """
        Action which deletes the selected files and/or folders.

        This action first displays a confirmation page whichs shows all the
        deleteable files and/or folders, or, if the user has no permission on
        one of the related childs (foreignkeys), a "permission denied" message.

        Next, it deletes all selected files and/or folders and redirects back to
        the folder.
        """
        opts = self.model._meta
        app_label = opts.app_label

        # Check that the user has delete permission for the actual model
        if not self.has_delete_permission(request):
            raise PermissionDenied

        current_folder = self._get_current_action_folder(
            request, files_queryset, folders_queryset)

        all_protected = []

        # Populate deletable_objects, a data structure of all related objects
        # that will also be deleted. Hopefully this also checks for necessary
        # permissions.
        # TODO: Check if permissions are really verified
        using = router.db_for_write(self.model)
        deletable_files, model_count_files, perms_needed_files, protected_files = get_deleted_objects(files_queryset, files_queryset.model._meta, request.user, self.admin_site, using)
        deletable_folders, model_count_folder, perms_needed_folders, protected_folders = get_deleted_objects(folders_queryset, folders_queryset.model._meta, request.user, self.admin_site, using)
        all_protected.extend(protected_files)
        all_protected.extend(protected_folders)

        all_deletable_objects = [deletable_files, deletable_folders]
        all_perms_needed = perms_needed_files.union(perms_needed_folders)

        # The user has already confirmed the deletion. Do the deletion and
        # return a None to display the change list view again.
        if request.POST.get('post'):
            if all_perms_needed:
                raise PermissionDenied
            n = files_queryset.count() + folders_queryset.count()
            if n:
                # delete all explicitly selected files
                for f in files_queryset:
                    self.log_deletion(request, f, force_text(f))
                    f.delete()
                # delete all files in all selected folders and their children
                # This would happen automatically by ways of the delete
                # cascade, but then the individual .delete() methods won't be
                # called and the files won't be deleted from the filesystem.
                folder_ids = set()
                for folder in folders_queryset:
                    folder_ids.add(folder.id)
                    folder_ids.update(
                        folder.get_descendants().values_list('id', flat=True))
                for f in File.objects.filter(folder__in=folder_ids):
                    self.log_deletion(request, f, force_text(f))
                    f.delete()
                # delete all folders
                for f in folders_queryset:
                    self.log_deletion(request, f, force_text(f))
                    f.delete()
                self.message_user(request, _("Successfully deleted %(count)d files and/or folders.") % {"count": n, })
            # Return None to display the change list page again.
            return None

        if all_perms_needed or all_protected:
            title = _("Cannot delete files and/or folders")
        else:
            title = _("Are you sure?")

        context = self.admin_site.each_context(request)
        context.update({
            "title": title,
            "instance": current_folder,
            "breadcrumbs_action": _("Delete files and/or folders"),
            "deletable_objects": all_deletable_objects,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": all_perms_needed,
            "protected": all_protected,
            "opts": opts,
            'is_popup': popup_status(request),
            'filer_admin_context': AdminContext(request),
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

        # Display the destination folder selection page
        return render(
            request,
            "admin/filer/delete_selected_files_confirmation.html",
            context
        )

    delete_files_or_folders.short_description = ugettext_lazy(
        "Delete selected files and/or folders")

    # Copied from django.contrib.admin.util
    def _format_callback(self, obj, user, admin_site, perms_needed):
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta
        if has_admin:
            admin_url = reverse('%s:%s_%s_change'
                                % (admin_site.name,
                                   opts.app_label,
                                   opts.object_name.lower()),
                                None, (quote(obj._get_pk_val()),))
            p = get_delete_permission(opts)
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return mark_safe('%s: <a href="%s">%s</a>' %
                             (escape(capfirst(opts.verbose_name)),
                              admin_url,
                              escape(obj)))
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return '%s: %s' % (capfirst(opts.verbose_name), force_text(obj))

    def _check_copy_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
        except PermissionDenied:
            return True
        return False

    def _check_move_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
            check_files_edit_permissions(request, files_queryset)
            check_folder_edit_permissions(request, folders_queryset)
        except PermissionDenied:
            return True
        return False

    def _get_current_action_folder(self, request, files_queryset,
                                   folders_queryset):
        if files_queryset:
            return files_queryset[0].folder
        elif folders_queryset:
            return folders_queryset[0].parent
        else:
            return None

    def _list_folders_to_copy_or_move(self, request, folders):
        for fo in folders:
            yield self._format_callback(fo, request.user, self.admin_site, set())
            children = list(self._list_folders_to_copy_or_move(request, fo.children.all()))
            children.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(fo.files)])
            if children:
                yield children

    def _list_all_to_copy_or_move(self, request, files_queryset, folders_queryset):
        to_copy_or_move = list(self._list_folders_to_copy_or_move(request, folders_queryset))
        to_copy_or_move.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(files_queryset)])
        return to_copy_or_move

    def _list_all_destination_folders_recursive(self, request, folders_queryset, current_folder, folders, allow_self, level):
        for fo in folders:
            if not allow_self and fo in folders_queryset:
                # We do not allow moving to selected folders or their descendants
                continue

            if not fo.has_read_permission(request):
                continue

            # We do not allow copying/moving back to the folder itself
            enabled = (allow_self or fo != current_folder) and fo.has_add_children_permission(request)
            yield (fo, (mark_safe(("&nbsp;&nbsp;" * level) + force_text(fo)), enabled))
            for c in self._list_all_destination_folders_recursive(request, folders_queryset, current_folder, fo.children.all(), allow_self, level + 1):
                yield c

    def _list_all_destination_folders(self, request, folders_queryset, current_folder, allow_self):
        root_folders = self.get_queryset(request).filter(parent__isnull=True).order_by('name')
        return list(self._list_all_destination_folders_recursive(request, folders_queryset, current_folder, root_folders, allow_self, 0))

    def _move_files_and_folders_impl(self, files_queryset, folders_queryset, destination):
        for f in files_queryset:
            f.folder = destination
            f.save()
        for f in folders_queryset:
            f.move_to(destination, 'last-child')
            f.save()

    def move_files_and_folders(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_move_perms(request, files_queryset, folders_queryset)
        to_move = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)
        folders = self._list_all_destination_folders(request, folders_queryset, current_folder, False)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            try:
                destination = self.get_queryset(request).get(pk=request.POST.get('destination'))
            except self.model.DoesNotExist:
                raise PermissionDenied
            folders_dict = dict(folders)
            if destination not in folders_dict or not folders_dict[destination][1]:
                raise PermissionDenied
            # We count only topmost files and folders here
            n = files_queryset.count() + folders_queryset.count()
            conflicting_names = [folder.name for folder in self.get_queryset(request).filter(parent=destination, name__in=folders_queryset.values('name'))]
            if conflicting_names:
                messages.error(request, _("Folders with names %s already exist at the selected "
                                          "destination") % ", ".join(conflicting_names))
            elif n:
                self._move_files_and_folders_impl(files_queryset, folders_queryset, destination)
                self.message_user(request, _("Successfully moved %(count)d files and/or folders to folder '%(destination)s'.") % {
                    "count": n,
                    "destination": destination,
                })
            return None

        context = self.admin_site.each_context(request)
        context.update({
            "title": _("Move files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Move files and/or folders"),
            "to_move": to_move,
            "destination_folders": folders,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

        # Display the destination folder selection page
        return render(request, "admin/filer/folder/choose_move_destination.html", context)

    move_files_and_folders.short_description = ugettext_lazy("Move selected files and/or folders")

    def _rename_file(self, file_obj, form_data, counter, global_counter):
        original_basename, original_extension = os.path.splitext(file_obj.original_filename)
        if file_obj.name:
            current_basename, current_extension = os.path.splitext(file_obj.name)
        else:
            current_basename = ""
            current_extension = ""
        file_obj.name = form_data['rename_format'] % {
            'original_filename': file_obj.original_filename,
            'original_basename': original_basename,
            'original_extension': original_extension,
            'current_filename': file_obj.name or "",
            'current_basename': current_basename,
            'current_extension': current_extension,
            'current_folder': getattr(file_obj.folder, 'name', ''),
            'counter': counter + 1,  # 1-based
            'global_counter': global_counter + 1,  # 1-based
        }
        file_obj.save()

    def _rename_files(self, files, form_data, global_counter):
        n = 0
        for f in sorted(files):
            self._rename_file(f, form_data, n, global_counter + n)
            n += 1
        return n

    def _rename_folder(self, folder, form_data, global_counter):
        return self._rename_files_impl(folder.files.all(), folder.children.all(), form_data, global_counter)

    def _rename_files_impl(self, files_queryset, folders_queryset, form_data, global_counter):
        n = 0

        for f in folders_queryset:
            n += self._rename_folder(f, form_data, global_counter + n)

        n += self._rename_files(files_queryset, form_data, global_counter + n)

        return n

    def rename_files(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_move_perms(request, files_queryset, folders_queryset)
        to_rename = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = RenameFilesForm(request.POST)
            if form.is_valid():
                if files_queryset.count() + folders_queryset.count():
                    n = self._rename_files_impl(files_queryset, folders_queryset, form.cleaned_data, 0)
                    self.message_user(request, _("Successfully renamed %(count)d files.") % {
                        "count": n,
                    })
                return None
        else:
            form = RenameFilesForm()

        context = self.admin_site.each_context(request)
        context.update({
            "title": _("Rename files"),
            "instance": current_folder,
            "breadcrumbs_action": _("Rename files"),
            "to_rename": to_rename,
            "rename_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

        # Display the rename format selection page
        return render(request, "admin/filer/folder/choose_rename_format.html", context)

    rename_files.short_description = ugettext_lazy("Rename files")

    def _generate_new_filename(self, filename, suffix):
        basename, extension = os.path.splitext(filename)
        return basename + suffix + extension

    def _copy_file(self, file_obj, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable (for different storage backends) way to overwrite files
            raise NotImplementedError

        # We are assuming here that we are operating on an already saved database objects with current database state available

        filename = self._generate_new_filename(file_obj.file.name, suffix)

        # Due to how inheritance works, we have to set both pk and id to None
        file_obj.pk = None
        file_obj.id = None
        file_obj.save()
        file_obj.folder = destination
        file_obj._file_data_changed_hint = False  # no need to update size, sha1, etc.
        file_obj.file = file_obj._copy_file(filename)
        file_obj.original_filename = self._generate_new_filename(file_obj.original_filename, suffix)
        file_obj.save()

    def _copy_files(self, files, destination, suffix, overwrite):
        for f in files:
            self._copy_file(f, destination, suffix, overwrite)
        return len(files)

    def _get_available_name(self, destination, name):
        count = itertools.count(1)
        original = name
        while destination.contains_folder(name):
            name = "%s_%s" % (original, next(count))
        return name

    def _copy_folder(self, folder, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable (for different storage backends) way to overwrite files
            raise NotImplementedError

        # TODO: Should we also allow not to overwrite the folder if it exists, but just copy into it?

        # TODO: Is this a race-condition? Would this be a problem?
        foldername = self._get_available_name(destination, folder.name)

        old_folder = Folder.objects.get(pk=folder.pk)

        # Due to how inheritance works, we have to set both pk and id to None
        folder.pk = None
        folder.id = None
        folder.name = foldername
        folder.insert_at(destination, 'last-child', True)  # We save folder here

        for perm in FolderPermission.objects.filter(folder=old_folder):
            perm.pk = None
            perm.id = None
            perm.folder = folder
            perm.save()

        return 1 + self._copy_files_and_folders_impl(old_folder.files.all(), old_folder.children.all(), folder, suffix, overwrite)

    def _copy_files_and_folders_impl(self, files_queryset, folders_queryset, destination, suffix, overwrite):
        n = self._copy_files(files_queryset, destination, suffix, overwrite)

        for f in folders_queryset:
            n += self._copy_folder(f, destination, suffix, overwrite)

        return n

    def copy_files_and_folders(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_copy_perms(request, files_queryset, folders_queryset)
        to_copy = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)
        folders = self._list_all_destination_folders(request, folders_queryset, current_folder, False)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = CopyFilesAndFoldersForm(request.POST)
            if form.is_valid():
                try:
                    destination = self.get_queryset(request).get(pk=request.POST.get('destination'))
                except self.model.DoesNotExist:
                    raise PermissionDenied
                folders_dict = dict(folders)
                if destination not in folders_dict or not folders_dict[destination][1]:
                    raise PermissionDenied
                if files_queryset.count() + folders_queryset.count():
                    # We count all files and folders here (recursivelly)
                    n = self._copy_files_and_folders_impl(files_queryset, folders_queryset, destination, form.cleaned_data['suffix'], False)
                    self.message_user(request, _("Successfully copied %(count)d files and/or folders to folder '%(destination)s'.") % {
                        "count": n,
                        "destination": destination,
                    })
                return None
        else:
            form = CopyFilesAndFoldersForm()

        try:
            selected_destination_folder = int(request.POST.get('destination', 0))
        except ValueError:
            if current_folder:
                selected_destination_folder = current_folder.pk
            else:
                selected_destination_folder = 0

        context = self.admin_site.each_context(request)
        context.update({
            "title": _("Copy files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Copy files and/or folders"),
            "to_copy": to_copy,
            "destination_folders": folders,
            "selected_destination_folder": selected_destination_folder,
            "copy_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

        # Display the destination folder selection page
        return render(request, "admin/filer/folder/choose_copy_destination.html", context)

    copy_files_and_folders.short_description = ugettext_lazy("Copy selected files and/or folders")

    def _check_resize_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
            check_files_edit_permissions(request, files_queryset)
        except PermissionDenied:
            return True
        return False

    def _list_folders_to_resize(self, request, folders):
        for fo in folders:
            children = list(self._list_folders_to_resize(request, fo.children.all()))
            children.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(fo.files) if isinstance(f, Image)])
            if children:
                yield self._format_callback(fo, request.user, self.admin_site, set())
                yield children

    def _list_all_to_resize(self, request, files_queryset, folders_queryset):
        to_resize = list(self._list_folders_to_resize(request, folders_queryset))
        to_resize.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(files_queryset) if isinstance(f, Image)])
        return to_resize

    def _new_subject_location(self, original_width, original_height, new_width, new_height, x, y, crop):
        # TODO: We could probably do even better, but this method knows nothing
        # about actual thumbnailing algorithm details.
        # It's better to reset subject location to the central point of the new
        # image if the image is being cropped. The originally specified subject
        # location could be outside of the new image.
        if crop:
            return int(new_width / 2), int(new_height / 2)
        else:
            # Calculate scaling factor of the new image compared to old.
            scale = min(new_width / original_width, new_height / original_height)
            return int(scale * x), int(scale * y)

    def _resize_image(self, image, form_data):
        original_width = float(image.width)
        original_height = float(image.height)
        thumbnailer = FilerActionThumbnailer(file=image.file, name=image.file.name, source_storage=image.file.source_storage, thumbnail_storage=image.file.source_storage)
        # This should overwrite the original image
        new_image = thumbnailer.get_thumbnail({
            'size': tuple(int(form_data[d] or 0) for d in ('width', 'height')),
            'crop': form_data['crop'],
            'upscale': form_data['upscale'],
            'subject_location': image.subject_location,
        })
        image.file.file = new_image.file
        # Since only file data was changed, there is no way for file field to know about the change.
        # To update size, sha1, width and height fields let's call file_data_changed callback directly.
        image.file_data_changed()
        image.save()

        subject_location = normalize_subject_location(image.subject_location)
        if subject_location:
            (x, y) = subject_location
            x = float(x)
            y = float(y)
            new_width = float(image.width)
            new_height = float(image.height)
            (new_x, new_y) = self._new_subject_location(original_width, original_height, new_width, new_height, x, y, form_data['crop'])
            image.subject_location = "%d,%d" % (new_x, new_y)
            image.save()

    def _resize_images(self, files, form_data):
        n = 0
        for f in files:
            if isinstance(f, Image):
                self._resize_image(f, form_data)
                n += 1
        return n

    def _resize_folder(self, folder, form_data):
        return self._resize_images_impl(folder.files.all(), folder.children.all(), form_data)

    def _resize_images_impl(self, files_queryset, folders_queryset, form_data):
        n = self._resize_images(files_queryset, form_data)

        for f in folders_queryset:
            n += self._resize_folder(f, form_data)

        return n

    def resize_images(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_resize_perms(request, files_queryset, folders_queryset)
        to_resize = self._list_all_to_resize(request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = ResizeImagesForm(request.POST)
            if form.is_valid():
                if form.cleaned_data.get('thumbnail_option'):
                    form.cleaned_data['width'] = form.cleaned_data['thumbnail_option'].width
                    form.cleaned_data['height'] = form.cleaned_data['thumbnail_option'].height
                    form.cleaned_data['crop'] = form.cleaned_data['thumbnail_option'].crop
                    form.cleaned_data['upscale'] = form.cleaned_data['thumbnail_option'].upscale
                if files_queryset.count() + folders_queryset.count():
                    # We count all files here (recursivelly)
                    n = self._resize_images_impl(files_queryset, folders_queryset, form.cleaned_data)
                    self.message_user(request, _("Successfully resized %(count)d images.") % {"count": n, })
                return None
        else:
            form = ResizeImagesForm()

        context = self.admin_site.each_context(request)
        context.update({
            "title": _("Resize images"),
            "instance": current_folder,
            "breadcrumbs_action": _("Resize images"),
            "to_resize": to_resize,
            "resize_form": form,
            "cmsplugin_enabled": 'cmsplugin_filer_image' in django_settings.INSTALLED_APPS,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        })

        # Display the resize options page
        return render(request, "admin/filer/folder/choose_images_resize_options.html", context)

    resize_images.short_description = ugettext_lazy("Resize selected images")
