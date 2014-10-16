#-*- coding: utf-8 -*-
from django import template
from django.contrib.admin import helpers
from django.contrib.admin.util import quote, unquote, capfirst
from django.contrib import messages
from django.utils.http import urlquote
from filer.admin.patched.admin_utils import get_deleted_objects
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse, resolve
from django.db import router
from django.db.models import Q, Count
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext, ugettext_lazy
from filer import settings
from filer.admin.forms import (CopyFilesAndFoldersForm, ResizeImagesForm,
                               RenameFilesForm)
from filer.admin.common_admin import FolderPermissionModelAdmin
from filer.views import (popup_status, popup_param, selectfolder_status,
                         selectfolder_param, current_site_param)
from filer.admin.tools import (folders_available, files_available,
                               has_admin_role, has_role_on_site,
                               has_admin_role_on_site,
                               get_admin_sites_for_user,
                               has_multi_file_action_permission,
                               is_valid_destination,)
from filer.models import (Folder, FolderRoot, UnfiledImages, File, tools,
                          ImagesWithMissingData, Image,
                          Archive)
from filer.settings import FILER_STATICMEDIA_PREFIX, FILER_PAGINATE_BY
from filer.utils.filer_easy_thumbnails import FilerActionThumbnailer
from filer.utils.multi_model_qs import MultiMoldelQuerysetChain
from filer.thumbnail_processors import normalize_subject_location
from django.conf import settings as django_settings
import json
import os
import itertools
import inspect


class FolderAdmin(FolderPermissionModelAdmin):
    list_display = ('name',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', 'files__name']
    save_as = True  # see ImageAdmin

    actions_affecting_position = [
        'move_to_clipboard',
        'delete_files_or_folders',
        'move_files_and_folders',
    ]

    actions = [
        'disable_restriction',
        'enable_restriction',
        'copy_files_and_folders',
        'extract_files', ] + actions_affecting_position

    # form fields
    exclude = ('parent', 'owner', 'folder_type')
    raw_id_fields = ('owner', )

    def get_readonly_fields(self, request, obj=None):
        self.readonly_fields = [ro_field
                                for ro_field in self.readonly_fields]
        self._make_restricted_field_readonly(request.user, obj)
        return super(FolderAdmin, self).get_readonly_fields(
            request, obj)

    def _get_sites_available_for_user(self, user):
        if user.is_superuser:
            return Site.objects.all()
        admin_sites = [site.id
                       for site in get_admin_sites_for_user(user)]
        return Site.objects.filter(id__in=admin_sites)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
            Filters sites available to the user based on his roles on sites
        """
        formfield = super(FolderAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)
        if request and db_field.rel.to is Site:
            formfield.queryset = self._get_sites_available_for_user(
                request.user)
        return formfield

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
            Filters sites available to the user based on his roles on sites
        """
        formfield = super(FolderAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)
        if request and db_field.rel.to is Site:
            formfield.queryset = self._get_sites_available_for_user(
                request.user)
        return formfield

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.

        Sets the parent folder and owner for the folder that will be edited
            in the form
        """

        folder_form = super(FolderAdmin, self).get_form(
            request, obj=obj, **kwargs)
        # do show share sites field only for superusers
        if not request.user.is_superuser:
            folder_form.base_fields.pop('shared', None)

        # check if site field should be visible in the form or not
        is_core_folder = False
        if obj and obj.pk:
            # change view
            parent_id = obj.parent_id
            is_core_folder = obj.is_core()
        else:
            # add view
            parent_id = request.REQUEST.get('parent_id', None) or None
            folder_form.base_fields.pop('restricted', None)

        # shouldn't show site field if has parent or is core folder
        pop_site_fields = parent_id or is_core_folder
        if pop_site_fields:
            folder_form.base_fields.pop('site', None)
            folder_form.base_fields.pop('shared', None)

        def clean(form_instance):
            # make sure owner and parent are passed to the model clean method
            current_folder = form_instance.instance
            if not current_folder.owner:
                current_folder.owner = request.user
            if parent_id:
                current_folder.parent = Folder.objects.get(id=parent_id)
            return form_instance.cleaned_data

        folder_form.clean = clean
        return folder_form

    def icon_img(self, xs):
        return mark_safe(('<img src="%simg/icons/plainfolder_32x32.png" ' +
                          'alt="Folder Icon" />') % FILER_STATICMEDIA_PREFIX)
    icon_img.allow_tags = True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FolderAdmin, self).get_urls()
        url_patterns = patterns('',
            # we override the default list view with our own directory listing
            # of the root directories
            url(r'^$', self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing-root'),
            url(r'^(?P<folder_id>\d+)/list/$',
                self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing'),
            url(r'^make_folder/$',
                self.admin_site.admin_view(self.make_folder),
                name='filer-directory_listing-make_root_folder'),
            url(r'^images_with_missing_data/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'images_with_missing_data'},
                name='filer-directory_listing-images_with_missing_data'),
            url(r'^unfiled_images/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'unfiled_images'},
                name='filer-directory_listing-unfiled_images'),
            url(r'^destination_folders/$',
                self.admin_site.admin_view(self.destination_folders),
                name='filer-destination_folders'),
        )
        url_patterns.extend(urls)
        return url_patterns

    def add_view(self, request, *args, **kwargs):
        raise PermissionDenied

    def make_folder(self, request, folder_id=None, *args, **kwargs):
        response = super(FolderAdmin, self).add_view(request, *args, **kwargs)

        # since filer overwrites django's dismissPopup we need to make sure
        #   that the response from django's add_view is the
        #   dismiss popup response so we can overwrite it
        # since only save button appears its enough to make sure that the
        #   request is a POST from a popup view and the response is a
        #   successed HttpResponse
        if (request.method == 'POST' and "_popup" in request.POST and
            response.status_code == 200 and
            not isinstance(response, TemplateResponse) and
            not isinstance(response, HttpResponseRedirect)):
            return HttpResponse('<script type="text/javascript">' +
                                'opener.dismissPopupAndReload(window);' +
                                '</script>')
        return response

    def delete_view(self, request, object_id, extra_context=None):
        # override delete view since we need to hide already trashed
        #   files/folders
        opts = self.model._meta
        obj = self.get_object(request, unquote(object_id))

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r '
                            'does not exist.') % {
                                'name': force_unicode(opts.verbose_name),
                                'key': escape(object_id)})
        if obj.parent:
            redirect_url = reverse('admin:filer-directory_listing',
                kwargs={'folder_id': obj.parent_id})
        else:
            redirect_url = reverse('admin:filer-directory_listing-root')
        redirect_url = "%s%s%s%s" % (redirect_url, popup_param(request),
                            selectfolder_param(request, "&"),
                            current_site_param(request),)

        setattr(request, 'current_dir_list_folder',
                obj.parent or FolderRoot())

        response = self.delete_files_or_folders(
            request,
            File.objects.get_empty_query_set(),
            Folder.objects.filter(id=obj.id))

        if response is None:
            return HttpResponseRedirect(redirect_url)
        return response

    # custom views
    def directory_listing(self, request, folder_id=None, viewtype=None):
        user = request.user
        clipboard = tools.get_user_clipboard(user)
        if viewtype == 'images_with_missing_data':
            folder = ImagesWithMissingData()
        elif viewtype == 'unfiled_images':
            folder = UnfiledImages()
        elif folder_id is None:
            folder = FolderRoot()
        else:
            try:
                folder = Folder.objects.get(id=folder_id)
                if not self.can_view_folder_content(request, folder):
                    raise PermissionDenied
            except Folder.DoesNotExist:
                raise Http404

        setattr(request, 'current_dir_list_folder', folder)
        # search
        q = request.GET.get('q', None)
        if q:
            search_terms = q.split(" ")
        else:
            search_terms = []
            q = ''

        # Check actions to see if any are available on this changelist
        # do not let any actions available if we're in search view since
        #   there is no way to detect the current folder
        actions = {}
        if not search_terms:
            actions = self.get_actions(request)

        # Remove action checkboxes if there aren't any actions available.
        list_display = list(self.list_display)
        if not actions:
            try:
                list_display.remove('action_checkbox')
            except ValueError:
                pass

        limit_search_to_folder = request.GET.get('limit_search_to_folder',
                                                 False) in (True, 'on')

        if len(search_terms) > 0:
            if folder and limit_search_to_folder and not folder.is_root:
                descendants = folder.get_descendants(
                    include_self=True).filter(deleted_at__isnull=True)
                folder_qs = folders_available(
                    request, descendants.exclude(id=folder.id))
                file_qs = files_available(
                    request, File.objects.filter(folder__in=descendants))
            else:
                folder_qs = folders_available(request, Folder.objects.all())
                file_qs = files_available(request, File.objects.all())

            def folder_search_qs(qs, terms=[]):
                for term in terms:
                    qs = qs.filter(Q(name__icontains=term) |
                                   Q(owner__username__icontains=term) |
                                   Q(owner__first_name__icontains=term) |
                                   Q(owner__last_name__icontains=term))
                return qs

            def file_search_qs(qs, terms=[]):
                for term in terms:
                    qs = qs.filter(Q(name__icontains=term) |
                                   Q(description__icontains=term) |
                                   Q(original_filename__icontains=term) |
                                   Q(owner__username__icontains=term) |
                                   Q(owner__first_name__icontains=term) |
                                   Q(owner__last_name__icontains=term))
                return qs

            folder_qs = folder_search_qs(folder_qs, search_terms)
            file_qs = file_search_qs(file_qs, search_terms)
            show_result_count = True
        else:
            folder_qs = folders_available(request, folder.children.all())
            file_qs = files_available(request, folder.files.all())
            show_result_count = False

        folder_qs = folder_qs.order_by('name')
        file_qs = file_qs.order_by('name')
        if show_result_count:
            show_result_count = {
                'files_found': file_qs.count(),
                'folders_found': folder_qs.count(),
            }

        items = MultiMoldelQuerysetChain([folder_qs, file_qs])
        paginator = Paginator(items, FILER_PAGINATE_BY)

        # Are we moving to clipboard?
        if request.method == 'POST' and '_save' not in request.POST:
            for f in file_qs:
                if "move-to-clipboard-%d" % (f.id,) in request.POST:
                    if (f.is_readonly_for_user(user) or
                            f.is_restricted_for_user(user)):
                        raise PermissionDenied
                    tools.move_file_to_clipboard(request, [f], clipboard)
                    return HttpResponseRedirect(request.get_full_path())

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request,
                    files_queryset=file_qs,
                    folders_queryset=folder_qs)
                if response:
                    return response
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)

        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request,
                    files_queryset=file_qs,
                    folders_queryset=folder_qs)
                if response:
                    return response

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = \
                self.get_action_choices(request)
        else:
            action_form = None
        selection_note_all = ungettext('%(total_count)s selected',
            'All %(total_count)s selected', paginator.count)

        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        # If page request (9999) is out of range, deliver last page of results.
        try:
            paginated_items = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginated_items = paginator.page(paginator.num_pages)
        response = render_to_response(
            'admin/filer/folder/directory_listing.html',
            {
                'folder': folder,
                'user_clipboard': clipboard,
                'clipboard_files': clipboard.files.distinct(),
                'current_site': request.REQUEST.get('current_site', None),
                'paginator': paginator,
                'paginated_items': paginated_items,
                'current_url': request.path,
                'title': u'Directory listing for %s' % folder.name,
                'search_string': ' '.join(search_terms),
                'q': q,
                'show_result_count': show_result_count,
                'limit_search_to_folder': limit_search_to_folder,
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                # needed in the admin/base.html template for logout links
                'root_path': reverse('admin:index'),
                'action_form': action_form,
                'actions_on_top': self.actions_on_top,
                'actions_on_bottom': self.actions_on_bottom,
                'actions_selection_counter': self.actions_selection_counter,
                'selection_note': _('0 of %(cnt)s selected') % {
                    'cnt': len(paginated_items.object_list)},
                'selection_note_all': selection_note_all % {
                    'total_count': paginator.count},
                'media': self.media,
        }, context_instance=RequestContext(request))
        return response

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
                # Reminder that something needs to be selected or
                #       nothing will happen
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
        actions = super(FolderAdmin, self).get_actions(request)

        def pop_actions(*actions_to_remove):
            for action in actions_to_remove:
                actions.pop(action, None)

        pop_actions('delete_selected')

        if not self.has_delete_permission(request, None):
            pop_actions(*self.actions_affecting_position)

        current_folder = getattr(request, 'current_dir_list_folder', None)
        if not current_folder:
            return actions

        if current_folder.is_root:
            pop_actions('extract_files')

        if (not current_folder.is_root and
                current_folder.is_readonly_for_user(request.user)):
            return {}

        if isinstance(current_folder, UnfiledImages):
            pop_actions('enable_restriction', 'copy_files_and_folders',
                        'disable_restriction')
            return actions

        # actions are available for descendants not for current folder
        if not (current_folder.can_change_restricted(request.user) and
                not current_folder.restricted):
            pop_actions('enable_restriction', 'disable_restriction')

        if (actions and current_folder.is_restricted_for_user(request.user)):
            # allow only copy
            if 'copy_files_and_folders' in actions:
                return {'copy_files_and_folders':
                            actions['copy_files_and_folders']}

        return actions

    def move_to_clipboard(self, request, files_queryset, folders_queryset):
        """
        Action which moves the selected files to clipboard.
        """
        if request.method != 'POST':
            return None

        if not has_multi_file_action_permission(
                request, files_queryset,
                Folder.objects.get_empty_query_set()):
            raise PermissionDenied

        clipboard = tools.get_user_clipboard(request.user)
        # We define it like that so that we can modify it inside the
        #       move_files function
        files_count = [0]

        def move_files(files):
            files_count[0] += tools.move_file_to_clipboard(
                request, files, clipboard)

        move_files(files_queryset)
        if files_count[0] > 0:
            self.message_user(request,
                _("Successfully moved %(count)d files to clipboard.") % {
                    "count": files_count[0], })
        else:
            self.message_user(request,
                _("No files were moved to clipboard."))
        return None

    move_to_clipboard.short_description = ugettext_lazy(
        "Move selected files to clipboard")

    def delete_files_or_folders(self, request,
                                files_queryset, folders_queryset):
        """
        Action which deletes the selected files and/or folders.

        This action first displays a confirmation page whichs shows all the
        deleteable files and/or folders, or, if the user has no permission
        on one of the related childs (foreignkeys), a "permission denied"
        message.

        Next, it delets all selected files and/or folders and redirects back
        to the folder.
        """

        # Check that the user has delete permission for the actual model
        if not self.has_delete_permission(request):
            raise PermissionDenied

        if not has_multi_file_action_permission(
                request, files_queryset, folders_queryset):
            raise PermissionDenied

        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(
            request, files_queryset, folders_queryset)

        all_protected = []

        # Populate deletable_objects, a data structure of all related
        # objects that will also be deleted.
        # Hopefully this also checks for necessary permissions.
        # TODO: Check if permissions are really verified
        (args, varargs, keywords, defaults) = \
            inspect.getargspec(get_deleted_objects)
        if 'levels_to_root' in args:
            # Django 1.2
            deletable_files, perms_needed_files = get_deleted_objects(
                files_queryset, files_queryset.model._meta, request.user,
                self.admin_site, levels_to_root=2)
            deletable_folders, perms_needed_folders = get_deleted_objects(
                folders_queryset, folders_queryset.model._meta, request.user,
                self.admin_site, levels_to_root=2)
        else:
            # Django 1.3
            using = router.db_for_write(self.model)
            deletable_files, perms_needed_files, protected_files = \
                get_deleted_objects(
                    files_queryset, files_queryset.model._meta,
                    request.user, self.admin_site, using)
            deletable_folders, perms_needed_folders, protected_folders = \
                get_deleted_objects(
                    folders_queryset, folders_queryset.model._meta,
                    request.user, self.admin_site, using)
            all_protected.extend(protected_files)
            all_protected.extend(protected_folders)

        all_deletable_objects = [deletable_files, deletable_folders]
        all_perms_needed = perms_needed_files.union(perms_needed_folders)

        # The user has already confirmed the deletion.
        # Do the deletion and return a None to display the change list
        #       view again.
        if request.POST.get('post'):
            if all_perms_needed:
                raise PermissionDenied
            n = files_queryset.count() + folders_queryset.count()
            if n:
                # delete all explicitly selected files
                for f in files_queryset:
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                # delete all folders
                for f_id in folders_queryset.values_list('id', flat=True):
                    f = Folder.objects.get(id=f_id)
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                self.message_user(request,
                    _("Successfully deleted %(count)d files "
                      "and/or folders.") % {"count": n, })
            # Return None to display the change list page again.
            return None

        if all_perms_needed or all_protected:
            title = _("Cannot delete files and/or folders")
        else:
            title = _("Are you sure?")

        context = {
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
            'select_folder': selectfolder_status(request),
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/delete_selected_files_confirmation.html"
        ], context, context_instance=template.RequestContext(request))

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
            p = '%s.%s' % (opts.app_label,
                           opts.get_delete_permission())
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return mark_safe(u'%s: <a href="%s">%s</a>' %
                             (escape(capfirst(opts.verbose_name)),
                              admin_url,
                              escape(obj.actual_name)))
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return u'%s: %s' % (capfirst(opts.verbose_name),
                                force_unicode(obj.actual_name))

    def _get_current_action_folder(self, request, files_qs, folders_qs):
        current_folder = getattr(request, 'current_dir_list_folder', None)
        if current_folder:
            return current_folder

        if files_qs:
            return files_qs[0].folder
        elif folders_qs:
            return folders_qs[0].parent
        else:
            return None

    def _list_folders_to_copy_or_move(self, request, folders):
        for fo in folders:
            yield self._format_callback(
                fo, request.user, self.admin_site, set())
            children = list(self._list_folders_to_copy_or_move(
                request, fo.children.all()))
            children.extend([self._format_callback(
                                f, request.user, self.admin_site, set())
                             for f in sorted(fo.files)])
            if children:
                yield children

    def _list_all_to_copy_or_move(self, request,
                                  files_queryset, folders_queryset):
        to_copy_or_move = list(self._list_folders_to_copy_or_move(
            request, folders_queryset))
        to_copy_or_move.extend([self._format_callback(
                                    f, request.user, self.admin_site, set())
                                for f in sorted(files_queryset)])
        return to_copy_or_move

    def _move_files_and_folders_impl(self, files_queryset, folders_queryset,
                                     destination):
        for f in files_queryset:
            f.folder = destination
            f.save()
        for f_id in folders_queryset.values_list('id', flat=True):
            f = Folder.objects.get(id=f_id)
            f.parent = destination
            f.save()

    def _as_folder(self, request_data, param):
        try:
            return Folder.objects.get(id=int(request_data.get(param, None)))
        except (Folder.DoesNotExist, ValueError, TypeError):
            return None

    def _clean_destination(self, request, current_folder,
                           selected_folders):
        destination = self._as_folder(request.POST, 'destination')
        if not destination:
            raise PermissionDenied
        # check destination permissions
        if not is_valid_destination(request, destination):
            raise PermissionDenied
        # don't allow copy/move from folder to the same folder
        if (hasattr(current_folder, 'pk') and
                destination.pk == current_folder.pk):
            raise PermissionDenied
        # don't allow selected folders to be copied/moved inside
        #   themselves or inside any of their descendants
        mgr = Folder._tree_manager
        destination_in_selected = mgr.get_queryset_descendants(
            selected_folders, include_self=True
        ).filter(id=destination.pk).exists()
        if destination_in_selected:
            raise PermissionDenied
        return destination

    def destination_folders(self, request):
        all_required = all((
            request.method == 'GET',
            request.is_ajax(),
            request.user.is_authenticated(),
            'parent' in request.GET
        ))
        if not all_required:
            raise PermissionDenied

        def _valid_candidates(request, folders_qs):
            # don't show orphaned/core/shared/restricted or selected folders
            return folders_available(request, folders_qs) \
                .valid_destinations(request.user) \
                .unrestricted(request.user) \
                .exclude(id__in=selected_ids)

        current_folder = self._as_folder(request.GET, 'current_folder')
        parent = self._as_folder(request.GET, 'parent')
        selected_ids = filter(
            None,
            map(lambda f_id: f_id or None,
                json.loads(request.GET.get('selected_folders') or ''))
        )
        candidates = Folder.objects.filter(parent=parent)
        fancytree_candidates = []
        for folder in _valid_candidates(request, candidates):
            has_children = _valid_candidates(
                request, Folder.objects.filter(parent=folder)
            ).exists()
            # don't allow move/copy files&folders to itself
            disabled = current_folder and current_folder.pk == folder.pk
            fancytree_candidates.append({
                'title': folder.name,
                'key': "%d" % folder.pk,
                'folder': has_children,
                'lazy': has_children,
                'hideCheckbox': disabled,
                'unselectable': disabled,
                'icon': folder.icons.get('32', '')
            })

        return HttpResponse(
            json.dumps(fancytree_candidates), content_type="application/json")

    def move_files_and_folders(self, request,
                               selected_files, selected_folders):
        opts = self.model._meta
        app_label = opts.app_label

        if not has_multi_file_action_permission(
                request, selected_files, selected_folders):
            raise PermissionDenied

        if selected_folders.filter(parent=None).exists():
            messages.error(request, "To prevent potential problems, users "
                "are not allowed to move root folders. You may copy folders "
                "and files.")
            return

        current_folder = self._get_current_action_folder(
            request, selected_files, selected_folders)
        to_move = self._list_all_to_copy_or_move(
            request, selected_files, selected_folders)

        if request.method == 'POST' and request.POST.get('post'):
            destination = self._clean_destination(
                request, current_folder, selected_folders)

            # all folders need to belong to the same site as the
            #   destination site folder
            sites_from_folders = \
                set(selected_folders.values_list('site_id', flat=True)) | \
                set(selected_files.exclude(folder__isnull=True).\
                        values_list('folder__site_id', flat=True))

            if (sites_from_folders and
                    None in sites_from_folders):
                messages.error(request, "Some of the selected files/folders "
                    "do not belong to any site. Folders need to be assigned "
                    "to a site before you can move files/folders from it.")
                return
            elif len(sites_from_folders) > 1:
                # it gets here if selection is made through a search view
                messages.error(request, "You cannot move files/folders that "
                    "belong to several sites. Select files/folders that "
                    "belong to only one site.")
                return
            elif (sites_from_folders and
                    sites_from_folders.pop() != destination.site.id):
                messages.error(request, "Selected files/folders need to "
                    "belong to the same site as the destination folder.")
                return

            if not self._are_candidate_names_valid(
                request, selected_files, selected_folders, destination):
                return

            # We count only topmost files and folders here
            n = selected_files.count() + selected_folders.count()
            if n:
                self._move_files_and_folders_impl(
                    selected_files, selected_folders, destination)
                self.message_user(request,
                     _("Successfully moved %(count)d files and/or "
                       "folders to folder '%(destination)s'.") % {
                            "count": n,
                            "destination": destination,
                        })
            return None

        context = {
            "title": _("Move files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Move files and/or folders"),
            "to_move": to_move,
            "files_queryset": selected_files,
            "folders_queryset": selected_folders,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/folder/choose_move_destination.html"
        ], context, context_instance=template.RequestContext(request))

    move_files_and_folders.short_description = ugettext_lazy(
        "Move selected files and/or folders")

    def extract_files(self, request, files_queryset, folder_queryset):
        success_format = "Successfully extracted archive {}."

        files_queryset = files_queryset.filter(
            polymorphic_ctype=ContentType.objects.get_for_model(Archive).id)
        # cannot extract in unfiled files folder
        if files_queryset.filter(folder__isnull=True).exists():
            raise PermissionDenied

        if not has_multi_file_action_permission(request, files_queryset,
                Folder.objects.get_empty_query_set()):
            raise PermissionDenied

        def is_valid_archive(filer_file):
            is_valid = filer_file.is_valid()
            if not is_valid:
                error_format = u"{} is not a valid zip file"
                message = error_format.format(filer_file.actual_name)
                messages.error(request, _(message))
            return is_valid

        def has_collisions(filer_file):
            collisions = filer_file.collisions()
            if collisions:
                error_format = u"Files/Folders from {archive} with names:"
                error_format += u"{names} already exist."
                names = u", ".join(collisions)
                archive = filer_file.actual_name
                message = error_format.format(
                    archive=archive,
                    names=names,
                )
                messages.error(request, _(message))
            return len(collisions) > 0

        for f in files_queryset:
            if not is_valid_archive(f) or has_collisions(f):
                continue
            f.extract()
            message = success_format.format(f.actual_name)
            self.message_user(request, _(message))

    extract_files.short_description = ugettext_lazy(
        "Extract selected zip files")

    def _copy_file(self, file_obj, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable
            #       (for different storage backends) way to overwrite files
            raise NotImplementedError

        # We are assuming here that we are operating on an already saved
        #       database objects with current database state available

        # Due to how inheritance works, we have to set both pk and id to None
        file_obj.pk = None
        file_obj.id = None
        file_obj.restricted = False
        file_obj.folder = destination
        # add suffix to actual name
        if file_obj.name in ('', None):
            file_obj.original_filename = self._generate_name(
                file_obj.original_filename, suffix)
        else:
            file_obj.name = self._generate_name(file_obj.name, suffix)
        new_path = file_obj.file.field.upload_to(file_obj, file_obj.actual_name)
        file_obj.file = file_obj._copy_file(new_path)
        file_obj.save()

    def _copy_files(self, files, destination, suffix, overwrite):
        for f in files:
            self._copy_file(f, destination, suffix, overwrite)
        return len(files)

    def _copy_folder(self, folder, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable
            #   (for different storage backends) way to overwrite files
            raise NotImplementedError

        foldername = self._generate_name(folder.name, suffix)
        old_folder = Folder.objects.get(pk=folder.pk)

        # Due to how inheritance works, we have to set both pk and id to None
        # lft and rght need to be reset since otherwise will see this node
        # as 'already set up for insertion' and will not recalculate tree
        # values
        folder.pk = folder.id = folder.lft = folder.rght = None
        folder.restricted = False
        folder.name = foldername
        folder.parent = destination
        folder.save()

        return 1 + self._copy_files_and_folders_impl(
            old_folder.files.all(), old_folder.children.all(),
            folder, suffix, overwrite)

    def _copy_files_and_folders_impl(self, files_queryset, folders_queryset,
                                     destination, suffix, overwrite):

        n = self._copy_files(files_queryset, destination, suffix, overwrite)

        for f_id in folders_queryset.values_list('id', flat=True):
            f = Folder.objects.get(id=f_id)
            destination = Folder.objects.get(id=destination.id)
            n += self._copy_folder(f, destination, suffix, overwrite)

        return n

    def _generate_name(self, filename, suffix):
        if not suffix:
            return filename
        basename, extension = os.path.splitext(filename)
        return basename + suffix + extension

    def _are_candidate_names_valid(
            self, request, file_qs, folder_qs, destination, suffix=None):
        candidate_folder_names = [self._generate_name(name, suffix)
                                  for name in folder_qs.values_list(
                                    'name', flat=True)]
        candidate_file_names = [
            self._generate_name(file_obj.actual_name, suffix)
            for file_obj in file_qs]

        existing_names = [f.actual_name
                          for f in destination.entries_with_names(
                            candidate_folder_names + candidate_file_names)]

        if existing_names:
            messages.error(request,
                _(u"File or folders with names %s already exist at the "
                  "selected destination") % u", ".join(existing_names))
            return False
        return True

    def copy_files_and_folders(self, request,
                               files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(
            request, files_queryset, folders_queryset)
        to_copy = self._list_all_to_copy_or_move(
            request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            form = CopyFilesAndFoldersForm(request.POST)
            if form.is_valid():
                destination = self._clean_destination(
                    request, current_folder, folders_queryset)

                suffix = form.cleaned_data['suffix']
                if not self._are_candidate_names_valid(
                    request, files_queryset, folders_queryset,
                    destination, suffix): return

                if files_queryset.count() + folders_queryset.count():
                    # We count all files and folders here (recursivelly)
                    n = self._copy_files_and_folders_impl(
                        files_queryset, folders_queryset, destination,
                        suffix, False)
                    self.message_user(request,
                        _("Successfully copied %(count)d files and/or "
                          "folders to folder '%(destination)s'.") % {
                                "count": n,
                                "destination": destination,
                            })
                return None
        else:
            form = CopyFilesAndFoldersForm()

        try:
            selected_destination_folder = \
                int(request.POST.get('destination', 0))
        except ValueError:
            if current_folder:
                selected_destination_folder = current_folder.pk
            else:
                selected_destination_folder = 0
        context = {
            "title": _("Copy files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Copy files and/or folders"),
            "to_copy": to_copy,
            "selected_destination_folder": selected_destination_folder,
            "copy_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/folder/choose_copy_destination.html"
        ], context, context_instance=template.RequestContext(request))

    copy_files_and_folders.short_description = ugettext_lazy(
        "Copy selected files and/or folders")

    def files_toggle_restriction(self, request, restriction,
                                 files_qs, folders_qs):
        """
        Action which enables or disables restriction for files/folders.
        """
        if request.method != 'POST':
            return None
        # cannot restrict/unrestrict unfiled files
        if files_qs.filter(folder__isnull=True).exists():
            raise PermissionDenied

        if not has_multi_file_action_permission(
                request, files_qs, folders_qs):
            raise PermissionDenied

        count = [0]

        def set_files_or_folders(filer_obj):
            for f in filer_obj:
                if f.restricted != restriction:
                    f.restricted = restriction
                    f.save()
                    count[0] += 1

        set_files_or_folders(files_qs)
        set_files_or_folders(folders_qs)
        count = count[0]
        if restriction:
            self.message_user(request,
                _("Successfully enabled restriction for %(count)d files "
                  "and/or folders.") % {"count": count,})
        else:
            self.message_user(request,
                _("Successfully disabled restriction for %(count)d files "
                  "and/or folders.") % {"count": count,})

        return None

    def enable_restriction(self, request, files_qs, folders_qs):
        return self.files_toggle_restriction(
            request, True, files_qs, folders_qs)

    enable_restriction.short_description = ugettext_lazy(
        "Enable restriction for selected and/or folders")

    def disable_restriction(self, request, files_qs, folders_qs):
        return self.files_toggle_restriction(
            request, False, files_qs, folders_qs)

    disable_restriction.short_description = ugettext_lazy(
        "Disable restriction for selected and/or folders")

'''
    def _rename_file(self, file_obj, form_data, counter, global_counter):
        original_basename, original_extension = os.path.splitext(
            file_obj.original_filename)
        if file_obj.name:
            current_basename, current_extension = os.path.splitext(
                file_obj.name)
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
                'current_folder': file_obj.folder.name,
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
        return self._rename_files_impl(
            folder.files.all(), folder.children.all(),
            form_data, global_counter)

    def _rename_files_impl(self, files_queryset, folders_queryset,
                           form_data, global_counter):
        n = 0

        for f in folders_queryset:
            n += self._rename_folder(f, form_data, global_counter + n)

        n += self._rename_files(files_queryset, form_data, global_counter + n)

        return n

    def rename_files(self, request, files_queryset, folders_queryset):
        # this logic needs to be suplimented with folder type permission layer
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(
            request, files_queryset, folders_queryset)
        to_rename = self._list_all_to_copy_or_move(
            request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            form = RenameFilesForm(request.POST)
            if form.is_valid():
                if files_queryset.count() + folders_queryset.count():
                    n = self._rename_files_impl(
                        files_queryset, folders_queryset,
                        form.cleaned_data, 0)
                    self.message_user(request,
                        _("Successfully renamed %(count)d files.") % {
                            "count": n,
                        })
                return None
        else:
            form = RenameFilesForm()

        context = {
            "title": _("Rename files"),
            "instance": current_folder,
            "breadcrumbs_action": _("Rename files"),
            "to_rename": to_rename,
            "rename_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the rename format selection page
        return render_to_response([
            "admin/filer/folder/choose_rename_format.html"
        ], context, context_instance=template.RequestContext(request))

    rename_files.short_description = ugettext_lazy("Rename files")

    def _list_folders_to_resize(self, request, folders):
        for fo in folders:
            children = list(self._list_folders_to_resize(
                request, fo.children.all()))
            children.extend([self._format_callback(
                                f, request.user, self.admin_site, set())
                             for f in sorted(fo.files)
                             if isinstance(f, Image)])
            if children:
                yield self._format_callback(
                    fo, request.user, self.admin_site, set())
                yield children

    def _list_all_to_resize(self, request, files_queryset, folders_queryset):
        to_resize = list(self._list_folders_to_resize(
            request, folders_queryset))
        to_resize.extend([self._format_callback(
                            f, request.user, self.admin_site, set())
                          for f in sorted(files_queryset)
                          if isinstance(f, Image)])
        return to_resize

    def _new_subject_location(self, original_width, original_height,
                              new_width, new_height, x, y, crop):
        # TODO: We could probably do better
        return (round(new_width / 2), round(new_height / 2))

    def _resize_image(self, image, form_data):
        original_width = float(image.width)
        original_height = float(image.height)
        thumbnailer = FilerActionThumbnailer(
            file=image.file.file,
            name=image.file.name,
            source_storage=image.file.source_storage,
            thumbnail_storage=image.file.source_storage)
        # This should overwrite the original image
        new_image = thumbnailer.get_thumbnail({
            'size': (form_data['width'], form_data['height']),
            'crop': form_data['crop'],
            'upscale': form_data['upscale'],
            'subject_location': image.subject_location,
        })
        from django.db.models.fields.files import ImageFieldFile
        image.file.file = new_image.file
        image.generate_sha1()
        image.save()  # Also gets new width and height

        subject_location = normalize_subject_location(image.subject_location)
        if subject_location:
            (x, y) = subject_location
            x = float(x)
            y = float(y)
            new_width = float(image.width)
            new_height = float(image.height)
            (new_x, new_y) = self._new_subject_location(
                original_width, original_height, new_width, new_height,
                x, y, form_data['crop'])
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
        return self._resize_images_impl(
            folder.files.all(), folder.children.all(), form_data)

    def _resize_images_impl(self, files_queryset,
                            folders_queryset, form_data):
        n = self._resize_images(files_queryset, form_data)

        for f in folders_queryset:
            n += self._resize_folder(f, form_data)

        return n

    def resize_images(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(
            request, files_queryset, folders_queryset)
        to_resize = self._list_all_to_resize(
            request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            form = ResizeImagesForm(request.POST)
            if form.is_valid():
                if form.cleaned_data.get('thumbnail_option'):
                    form.cleaned_data['width'] = \
                        form.cleaned_data['thumbnail_option'].width
                    form.cleaned_data['height'] = \
                        form.cleaned_data['thumbnail_option'].height
                    form.cleaned_data['crop'] = \
                        form.cleaned_data['thumbnail_option'].crop
                    form.cleaned_data['upscale'] = \
                        form.cleaned_data['thumbnail_option'].upscale
                if files_queryset.count() + folders_queryset.count():
                    # We count all files here (recursivelly)
                    n = self._resize_images_impl(
                        files_queryset, folders_queryset, form.cleaned_data)
                    self.message_user(request,
                        _("Successfully resized %(count)d images.") % {
                            "count": n,
                        })
                return None
        else:
            form = ResizeImagesForm()

        context = {
            "title": _("Resize images"),
            "instance": current_folder,
            "breadcrumbs_action": _("Resize images"),
            "to_resize": to_resize,
            "resize_form": form,
            "cmsplugin_enabled": ('cmsplugin_filer_image'
                                  in django_settings.INSTALLED_APPS),
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "opts": opts,
            "root_path": reverse('admin:index'),
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the resize options page
        return render_to_response([
            "admin/filer/folder/choose_images_resize_options.html"
        ], context, context_instance=template.RequestContext(request))

    resize_images.short_description = ugettext_lazy("Resize selected images")

    def files_set_public_or_private(self, request, set_public,
                                    files_queryset, folders_queryset):
        """
        Action which enables or disables permissions for selected
            files and files in selected folders to clipboard
            (set them private or public).
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None

        # We define it like that so that we can modify it inside the
        #       set_files function
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
            self.message_user(request,
                _("Successfully disabled permissions for %(count)d files.") % {
                    "count": files_count[0], })
        else:
            self.message_user(request,
                _("Successfully enabled permissions for %(count)d files.") % {
                    "count": files_count[0], })

        return None

    def files_set_private(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(
            request, False, files_queryset, folders_queryset)

    files_set_private.short_description = ugettext_lazy(
        "Enable permissions for selected files")

    def files_set_public(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(
            request, True, files_queryset, folders_queryset)

    files_set_public.short_description = ugettext_lazy(
        "Disable permissions for selected files")
'''
