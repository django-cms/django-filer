#-*- coding: utf-8 -*-
from django import forms
from django import template
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import unquote, get_deleted_objects
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext, ugettext_lazy
from filer import settings
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.admin.tools import popup_status, selectfolder_status, \
    userperms_for_request, check_folder_edit_permissions, check_files_edit_permissions
from filer.models import Folder, FolderRoot, UnfiledImages, \
    ImagesWithMissingData, File, tools
from filer.settings import FILER_STATICMEDIA_PREFIX, FILER_PAGINATE_BY
import urllib


class AddFolderPopupForm(forms.ModelForm):
    folder = forms.HiddenInput()

    class Meta:
        model = Folder
        fields = ('name',)


class FolderAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('name',)
    exclude = ('parent',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', 'files__name']
    raw_id_fields = ('owner',)
    save_as = True  # see ImageAdmin
    actions = ['move_to_clipboard', 'files_set_public', 'files_set_private', 'delete_files_or_folders']

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            return AddFolderPopupForm
        else:
            return super(FolderAdmin, self).get_form(
                                                request, obj=None, **kwargs)

    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        r = form.save(commit=False)
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            parent = Folder.objects.get(id=parent_id)
            r.parent = parent
        return r

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        """
        r = super(FolderAdmin, self).response_change(request, obj)
        if r['Location']:
            # it was a successful save
            if r['Location'] in ['../']:
                if obj.parent:
                    url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': obj.parent.id})
                else:
                    url = reverse('admin:filer-directory_listing-root')
                return HttpResponseRedirect(url)
            else:
                # this means it probably was a save_and_continue_editing
                pass
        return r

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FolderAdmin, self).render_change_form(
                        request=request, context=context, add=False,
                        change=False, form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a folder.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.
        """
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.parent
        except self.model.DoesNotExist:
            obj = None

        r = super(FolderAdmin, self).delete_view(
                    request=request, object_id=object_id,
                    extra_context=extra_context)
        url = r.get("Location", None)
        if url in ["../../../../", "../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            return HttpResponseRedirect(url)
        return r

    def icon_img(self, xs):
        return mark_safe(('<img src="%simg/icons/plainfolder_32x32.png" ' + \
                          'alt="Folder Icon" />') % FILER_STATICMEDIA_PREFIX)
    icon_img.allow_tags = True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FolderAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            # we override the default list view with our own directory listing
            # of the root directories
            url(r'^$', self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing-root'),
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
        )
        url_patterns.extend(urls)
        return url_patterns

    # custom views
    def directory_listing(self, request, folder_id=None, viewtype=None):
        clipboard = tools.get_user_clipboard(request.user)
        if viewtype == 'images_with_missing_data':
            folder = ImagesWithMissingData()
        elif viewtype == 'unfiled_images':
            folder = UnfiledImages()
        elif folder_id == None:
            folder = FolderRoot()
        else:
            try:
                folder = Folder.objects.get(id=folder_id)
            except Folder.DoesNotExist:
                raise Http404

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
        def filter_folder(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | \
                               Q(owner__username__icontains=term) | \
                               Q(owner__first_name__icontains=term) | \
                               Q(owner__last_name__icontains=term))
            return qs

        def filter_file(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | \
                               Q(original_filename__icontains=term) | \
                               Q(owner__username__icontains=term) | \
                               Q(owner__first_name__icontains=term) | \
                               Q(owner__last_name__icontains=term))
            return qs
        q = request.GET.get('q', None)
        if q:
            search_terms = urllib.unquote_plus(q).split(" ")
        else:
            search_terms = []
            q = ''
        limit_search_to_folder = request.GET.get('limit_search_to_folder',
                                                 False) in (True, 'on')

        if len(search_terms) > 0:
            if folder and limit_search_to_folder and not folder.is_root:
                folder_qs = folder.get_descendants()
                file_qs = File.objects.filter(
                                        folder__in=folder.get_descendants())
            else:
                folder_qs = Folder.objects.all()
                file_qs = File.objects.all()
            folder_qs = filter_folder(folder_qs, search_terms)
            file_qs = filter_file(file_qs, search_terms)

            show_result_count = True
        else:
            folder_qs = folder.children.all()
            file_qs = folder.files.all()
            show_result_count = False

        folder_qs = folder_qs.order_by('name')
        file_qs = file_qs.order_by('name')

        folder_children = []
        folder_files = []
        if folder.is_root:
            folder_children += folder.virtual_folders
        for f in folder_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    folder_children.append(f)
                else:
                    pass
            else:
                folder_children.append(f)
        for f in file_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    folder_files.append(f)
                else:
                    pass
            else:
                folder_files.append(f)
        try:
            permissions = {
                'has_edit_permission': folder.has_edit_permission(request),
                'has_read_permission': folder.has_read_permission(request),
                'has_add_children_permission': \
                                folder.has_add_children_permission(request),
            }
        except:
            permissions = {}
        folder_files.sort(cmp=lambda x, y: cmp(x.label.lower(),
                                               y.label.lower()))
        items = folder_children + folder_files
        paginator = Paginator(items, FILER_PAGINATE_BY)

        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1
       
        # Are we moving to clipboard?
        if request.method == 'POST' and '_save' not in request.POST:
            for f in folder_files:
                print f
                if "move-to-clipboard-%d" % (f.id,) in request.POST:
                    clipboard = tools.get_user_clipboard(request.user)
                    if f.has_edit_permission(request):
                        tools.move_file_to_clipboard([f], clipboard)
                        return HttpResponseRedirect(request.get_full_path())
                    else:
                        raise PermissionDenied

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, files_queryset=file_qs, folders_queryset=folder_qs)
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
            paginated_items = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginated_items = paginator.page(paginator.num_pages)
        return render_to_response(
            'admin/filer/folder/directory_listing.html',
            {
                'folder': folder,
                'clipboard_files': File.objects.filter(
                    in_clipboards__clipboarditem__clipboard__user=request.user
                    ).distinct(),
                'paginator': paginator,
                'paginated_items': paginated_items,
                'permissions': permissions,
                'permstest': userperms_for_request(folder, request),
                'current_url': request.path,
                'title': u'Directory listing for %s' % folder.name,
                'search_string': ' '.join(search_terms),
                'q': urllib.quote_plus(q),
                'show_result_count': show_result_count,
                'limit_search_to_folder': limit_search_to_folder,
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                # needed in the admin/base.html template for logout links
                'root_path': "/%s" % admin.site.root_path,
                'action_form': action_form,
                'actions_on_top': self.actions_on_top,
                'actions_on_bottom': self.actions_on_bottom,
                'actions_selection_counter': self.actions_selection_counter,
                'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(paginated_items.object_list)},
                'selection_note_all': selection_note_all % {'total_count': paginator.count},
                'media': self.media,
                'enable_permissions': settings.FILER_ENABLE_PERMISSIONS
        }, context_instance=RequestContext(request))

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
                # Reminder that something needs to be selected or nothing will happen
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
                folders_queryset = folders_queryset.filter(pk__in=selected_folders)

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
        del actions['delete_selected']
        return actions

    def move_to_clipboard(self, request, files_queryset, folders_queryset):
        """
        Action which moves the selected files and files in selected folders to clipboard.
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None
        
        clipboard = tools.get_user_clipboard(request.user)

        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        files_count = [0] # We define it like that so that we can modify it inside the move_files function

        def move_files(files):
            tools.move_file_to_clipboard(files, clipboard)
            files_count[0] += len(files)

        def move_folders(folders):
            for f in folders:
                move_files(f.files)
                move_folders(f.children.all())
        
        move_files(files_queryset)
        move_folders(folders_queryset)

        self.message_user(request, _("Successfully moved %(count)d files to clipboard.") % {
            "count": files_count[0],
        })

        return None

    move_to_clipboard.short_description = ugettext_lazy("Move selected files to clipboard")

    def files_set_public_or_private(self, request, set_public, files_queryset, folders_queryset):
        """
        Action which enables or disables permissions for selected files and files in selected folders to clipboard (set them private or public).
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None
        
        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        files_count = [0] # We define it like that so that we can modify it inside the set_files function

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
            self.message_user(request, _("Successfully disabled permissions for %(count)d files.") % {
                "count": files_count[0],
            })
        else:
            self.message_user(request, _("Successfully enabled permissions for %(count)d files.") % {
                "count": files_count[0],
            })

        return None

    def files_set_private(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, False, files_queryset, folders_queryset)

    files_set_private.short_description = ugettext_lazy("Enable permissions for selected files")

    def files_set_public(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, True, files_queryset, folders_queryset)

    files_set_public.short_description = ugettext_lazy("Disable permissions for selected files")

    def delete_files_or_folders(self, request, files_queryset, folders_queryset):
        """
        Action which deletes the selected files and/or folders.
    
        This action first displays a confirmation page whichs shows all the
        deleteable files and/or folders, or, if the user has no permission on one of the related
        childs (foreignkeys), a "permission denied" message.
    
        Next, it delets all selected files and/or folders and redirects back to the folder.
        """
        opts = self.model._meta
        app_label = opts.app_label
    
        # Check that the user has delete permission for the actual model
        if not self.has_delete_permission(request):
            raise PermissionDenied
    
        # Populate deletable_objects, a data structure of all related objects that
        # will also be deleted.
        # Hopefully this also checks for necessary permissions.
        # TODO: Check if permissions are really verified
        deletable_files, perms_needed_files = get_deleted_objects(files_queryset, files_queryset.model._meta, request.user, self.admin_site, levels_to_root=2)
        deletable_folders, perms_needed_folders = get_deleted_objects(folders_queryset, folders_queryset.model._meta, request.user, self.admin_site, levels_to_root=2)

        all_deletable_objects = [deletable_files, deletable_folders]
        all_perms_needed = perms_needed_files.union(perms_needed_folders)

        # The user has already confirmed the deletion.
        # Do the deletion and return a None to display the change list view again.
        if request.POST.get('post'):
            if all_perms_needed:
                raise PermissionDenied
            n = files_queryset.count() + folders_queryset.count()
            if n:
                for f in files_queryset:
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                for f in folders_queryset:
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                self.message_user(request, _("Successfully deleted %(count)d files and/or folders.") % {
                    "count": n,
                })
            # Return None to display the change list page again.
            return None
    
        context = {
            "title": _("Are you sure?"),
            "deletable_objects": all_deletable_objects,
            'files_queryset': files_queryset,
            'folders_queryset': folders_queryset,
            "perms_lacking": all_perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
    
        # Display the confirmation page
        return render_to_response([
            "admin/filer/delete_selected_confirmation.html"
        ], context, context_instance=template.RequestContext(request))
    
    delete_files_or_folders.short_description = ugettext_lazy("Delete selected files and/or folders")
