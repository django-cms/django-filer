from django.core.urlresolvers import reverse
from django.contrib.admin.util import unquote
from django.utils.translation import ugettext  as _
from django.http import HttpResponseRedirect
from django import forms
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.models import File

# forms
class FileAdminChangeFrom(forms.ModelForm):
    class Meta:
        model = File

#ModelAdmins
class FileAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('label',)
    list_per_page = 10
    search_fields = ['name', 'original_filename','sha1',]
    raw_id_fields = ('owner',)
    readonly_fields = ('sha1',)
    
    # save_as hack, because without save_as it is impossible to hide the 
    # save_and_add_another if save_as is False.
    # To show only save_and_continue and save in the submit row we need save_as=True
    # and in render_change_form() override add and change to False.
    save_as = True
    
    form = FileAdminChangeFrom
    fieldsets = (
        (None, {
            'fields': ('name', 'owner','description')
        }),
        (None, {
            'fields': ('is_public',)
        }),
        (_('Advanced'), {
            'fields': ('file','sha1',),
            'classes': ('collapse',),
        }),
    )
    def response_change(self, request, obj):
        '''
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        '''
        r = super(FileAdmin, self).response_change(request, obj)
        #print r['Location']
        if r['Location']:
            # it was a successful save
            if r['Location'] in ['../']:
                # this means it was a save: redirect to the directory view
                if obj.folder:
                    url = reverse('admin:filer-directory_listing', 
                                  kwargs={'folder_id': obj.folder.id})
                else:
                    url = reverse('admin:filer-directory_listing-unfiled_images')
                return HttpResponseRedirect(url)
            else:
                # this means it probably was a save_and_continue_editing
                pass
        return r
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FileAdmin, self).render_change_form(request=request, context=context, add=False, change=False, form_url=form_url, obj=obj)
    
    def delete_view(self, request, object_id, extra_context=None):
        '''
        Overrides the default to enable redirecting to the directory view after
        deletion of a image.
        
        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it impossible
        to find out the parent folder to redirect to.
        '''
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.folder
        except self.model.DoesNotExist:
            obj = None
        
        r = super(FileAdmin, self).delete_view(request=request, object_id=object_id, extra_context=extra_context)
        
        url = r.get("Location", None)
        if url in ["../../../../","../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing', 
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-unfiled_images')
            return HttpResponseRedirect(url)
        return r
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FileAdmin, self).get_urls()
        #from filer import views
        url_patterns = patterns('',
            #url(r'^(?P<image_id>\d+)/export/$', self.admin_site.admin_view(views.export_image), name='image_filer-export_image'),
        )
        url_patterns.extend(urls)
        return url_patterns
    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }
    #def has_change_permission(self, request, obj=None):
    #    return False
    #def add_view(self, request):
    #    return HttpResponseRedirect(reverse('admin:filer-directory_listing-root'))
    #def changelist_view(self, request, extra_context=None):
    #    return HttpResponseRedirect(reverse('admin:filer-directory_listing-root'))
