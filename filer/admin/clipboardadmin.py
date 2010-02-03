import os
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.util import unquote, flatten_fieldsets, get_deleted_objects, model_ngettext, model_format_dict
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import admin
from django import forms
from django.db.models import Q
from django.contrib.admin.models import User
from django.conf import settings
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.models import Clipboard, ClipboardItem, File, Image
from filer.utils.files import generic_handle_file
from filer.admin.tools import *
from filer.models import tools

# forms... sucks, types should be automatic
class UploadFileForm(forms.ModelForm):
    class Meta:
        model=File
class UploadImageFileForm(forms.ModelForm):
    class Meta:
        model=Image


# ModelAdmins
class ClipboardItemInline(admin.TabularInline):
    model = ClipboardItem
class ClipboardAdmin(admin.ModelAdmin):
    model = Clipboard
    inlines = [ ClipboardItemInline, ]
    filter_horizontal = ('files',)
    raw_id_fields = ('user',)
    verbose_name = "DEBUG Clipboard"
    verbose_name_plural = "DEBUG Clipboards"
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(ClipboardAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            #url(r'^([0-9]+)/move-page/$', self.admin_site.admin_view(self.move_entity), name='%s_%s' % (info, 'move_page') ),
            url(r'^operations/paste_clipboard_to_folder/$', self.admin_site.admin_view(views.paste_clipboard_to_folder), name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$', self.admin_site.admin_view(views.discard_clipboard), name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$', self.admin_site.admin_view(views.delete_clipboard), name='filer-delete_clipboard'),
            url(r'^operations/move_file_to_clipboard/$', self.admin_site.admin_view(self.move_file_to_clipboard), name='filer-move_file_to_clipboard'),
            # upload does it's own permission stuff (because of the stupid flash missing cookie stuff)
            url(r'^operations/upload/$', self.ajax_upload, name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns
    #def has_add_permission(self, request):
    #    return False
    #def has_change_permission(self, request, obj=None):
    #    return False
    #def has_delete_permission(self, request, obj=None):
    #    return False
    
    def ajax_upload(self, request, folder_id=None):
        """
        receives an upload from the flash uploader and fixes the session
        because of the missing cookie. Receives only one file at the time, 
        althow it may be a zip file, that will be unpacked.
        """
        try:
            #print request.POST
            # flashcookie-hack (flash does not submit the cookie, so we send the
            # django sessionid over regular post
            #print "ajax upload view"
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
            #print "imported session store"
            #session_key = request.POST.get('jsessionid')
            session_key = request.POST.get('jsessionid')
            #print "session_key: %s" % session_key
            request.session = engine.SessionStore(session_key)
            #print "got session object"
            request.user = User.objects.get(id=request.session['_auth_user_id'])
            #print "got user"
            #print request.session['_auth_user_id']
            #print session_key
            #print engine
            #print request.user
            #print request.session
            # upload and save the file
            if not request.method == 'POST':
                return HttpResponse("must be POST")
            original_filename = request.POST.get('Filename')
            file = request.FILES.get('Filedata')
            #print request.FILES
            #print original_filename, file
            #print "get clipboad"
            clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=request.user)
            #print "handle files"
            files = generic_handle_file(file, original_filename)
            file_items = []
            #print "loop files"
            for ifile, iname in files:
                try:
                    iext = os.path.splitext(iname)[1].lower()
                except:
                    iext = ''
                #print "inaem: %s iext: %s" % (iname, iext)
                #print "extension: ", iext
                if iext in ['.jpg','.jpeg','.png','.gif']:
                    uploadform = UploadImageFileForm({'original_filename':iname,'owner': request.user.pk}, {'_file':ifile})
                else:
                    uploadform = UploadFileForm({'original_filename':iname,'owner': request.user.pk}, {'_file':ifile})
                if uploadform.is_valid():
                    #print 'uploadform is valid'
                    try:
                        file = uploadform.save(commit=False)
                        file.save()
                        file_items.append(file)
                        bi = ClipboardItem(clipboard=clipboard, file=file)
                        bi.save()
                    except Exception, e:
                        #print "some exception"
                        #print e
                        pass
                    #print "save %s" % image
                    #sprint image
                else:
                    pass#print uploadform.errors
                #print "what up?"
        except Exception, e:
            #print e
            pass
        #print file_items
        return render_to_response('admin/filer/tools/clipboard/clipboard_item_rows.html', {'items': file_items }, context_instance=RequestContext(request))
    def move_file_to_clipboard(self, request):
        #print "move file"
        if request.method=='POST':
            file_id = request.POST.get("file_id", None)
            clipboard = tools.get_user_clipboard(request.user)
            if file_id:
                file = File.objects.get(id=file_id)
                if file.has_edit_permission(request):
                    tools.move_file_to_clipboard([file], clipboard)
                else:
                    raise PermissionDenied
        return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )
    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

