from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.util import unquote
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import admin
from django import forms
from django.db.models import Q
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.models import Folder, FolderRoot, UnfiledImages, ImagesWithMissingData, File
from filer.admin.tools import popup_status, selectfolder_status, userperms_for_request
from filer.models import tools
from filer.settings import FILER_STATICMEDIA_PREFIX


# Forms
class AddFolderPopupForm(forms.ModelForm):
    folder = forms.HiddenInput()
    class Meta:
        model = Folder
        fields = ('name',)

# ModelAdmins
class FolderAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('name',)
    exclude = ('parent',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', 'files__name' ]
    raw_id_fields = ('owner',)
    save_as = True # see ImageAdmin
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            return AddFolderPopupForm
        else:
            return super(FolderAdmin, self).get_form(request, obj=None, **kwargs)
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
        '''
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        '''
        r = super(FolderAdmin, self).response_change(request, obj)
        if r['Location']:
            #print r['Location']
            #print obj
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
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FolderAdmin, self).render_change_form(request=request, context=context, add=False, change=False, form_url=form_url, obj=obj)
    
    def delete_view(self, request, object_id, extra_context=None):
        '''
        Overrides the default to enable redirecting to the directory view after
        deletion of a folder.
        
        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it impossible
        to find out the parent folder to redirect to.
        '''
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.parent
        except self.model.DoesNotExist:
            obj = None
        
        r = super(FolderAdmin, self).delete_view(request=request, object_id=object_id, extra_context=extra_context)
        url = r.get("Location", None)
        if url in ["../../../../","../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing', 
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            return HttpResponseRedirect(url)
        return r
    def icon_img(self, xs):
        return mark_safe('<img src="%simg/icons/plainfolder_32x32.png" alt="Folder Icon" />' % FILER_STATICMEDIA_PREFIX)
    icon_img.allow_tags = True
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FolderAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            # we override the default list view with our own directory listing of the root directories
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
            
        # search
        def filter_folder(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term)  )  
            return qs
        def filter_file(qs, terms=[]):
            for term in terms:
                qs = qs.filter( Q(name__icontains=term) | Q(original_filename__icontains=term ) | Q(owner__username__icontains=term) | Q(owner__first_name__icontains=term) | Q(owner__last_name__icontains=term) )
            return qs
        q = request.GET.get('q', None)
        if q:
            search_terms = q.split(" ")
        else:
            search_terms = []
        limit_search_to_folder = request.GET.get('limit_search_to_folder', False) in (True, 'on')
    
        if len(search_terms)>0:
            if folder and limit_search_to_folder and not folder.is_root:
                folder_qs = folder.get_descendants()
                file_qs = File.objects.filter(folder__in=folder.get_descendants())
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
                    #print "%s has read permission for %s" % (request.user, f)
                    folder_children.append(f)
                else:
                    pass#print "%s has NO read permission for %s" % (request.user, f)
            else:
                folder_children.append(f) 
        for f in file_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    #print "%s has read permission for %s" % (request.user, f)
                    folder_files.append(f)
                else:
                    pass#print "%s has NO read permission for %s" % (request.user, f)
            else:
                folder_files.append(f)
        try:
            permissions = {
                'has_edit_permission': folder.has_edit_permission(request),
                'has_read_permission': folder.has_read_permission(request),
                'has_add_children_permission': folder.has_add_children_permission(request),
            }
        except:
            permissions = {}
        #folder_children = folder_children.sort(cmp=lambda x,y: cmp(x.name.lower(), y.name.lower()))
        folder_files.sort(cmp=lambda x, y: cmp(x.label.lower(), y.label.lower()))
        return render_to_response('admin/filer/folder/directory_listing.html', {
                'folder':folder,
                'folder_children':folder_children,
                'folder_files':folder_files,
                'permissions': permissions,
                'permstest': userperms_for_request(folder, request),
                'current_url': request.path,
                'title': u'Directory listing for %s' % folder.name,
                'search_string': ' '.join(search_terms),
                'show_result_count': show_result_count,
                'limit_search_to_folder': limit_search_to_folder,
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                'root_path': "/%s" % admin.site.root_path, # needed in the admin/base.html template for logout links and stuff 
            }, context_instance=RequestContext(request))
