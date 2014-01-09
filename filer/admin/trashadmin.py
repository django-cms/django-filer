from django.db import models
from django.contrib import admin
from django.utils.encoding import force_unicode
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from filer.utils.multi_model_qs import MultiMoldelQuerysetChain
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from filer.settings import FILER_PAGINATE_BY
import filer, json


class Trash(models.Model):
    """Dummy model without any associated db table.
    It's only purpose is to provide an additional
    entry in the admin index.
    """
    class Meta:
        verbose_name_plural = 'Deleted Files and Folders'
        permissions = ()
        app_label = 'filer'


class TrashAdmin(admin.ModelAdmin):

    class Meta:
        model = Trash

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(TrashAdmin, self).get_urls()
        url_patterns = patterns('',
            url(r'^(?P<filer_model>\w+)/(?P<filer_obj_id>\d+)/$',
                self.admin_site.admin_view(self.restorable_item_view),
                name='filer_trash_item'),
            url(r'^file/check/(?P<file_id>\d+)/$',
                self.admin_site.admin_view(self.file_check),
                name='filer_trash_file_check'),
            )
        url_patterns.extend(urls)
        return url_patterns

    def queryset(self, request):
        files_q = Q(folder__deleted_at__isnull=True)
        folders_q = Q(Q(parent=None) | Q(parent__deleted_at__isnull=True))
        file_qs = filer.models.filemodels.File.trash.filter(files_q)
        folder_qs = filer.models.foldermodels.Folder.trash.filter(folders_q)
        return MultiMoldelQuerysetChain([
            folder_qs.order_by('-deleted_at'),
            file_qs.order_by('-deleted_at')])

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def restorable_item_view(self, request, filer_model, filer_obj_id):
        opts = self.model._meta
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        if filer_model not in ['file', 'folder']:
            raise Http404

        filer_model_cls = getattr(filer.models, filer_model.capitalize())
        try:
            filer_object = filer_model_cls.trash.get(id=filer_obj_id)
        except filer_model_cls.DoesNotExist, e:
            raise Http404

        if hasattr(filer_object, 'get_descendants'):
            descendants = filer_object.get_descendants(include_self=True).\
                select_related('parent').filter(deleted_at__isnull=False)
        else:
            descendants = []

        context = {
            'module_name': force_unicode(opts.verbose_name_plural),
            'media': self.media,
            'opts': opts,
            'app_label': opts.app_label,
            'current_item': filer_object,
            'current_item_type': filer_model,
            'descendants': descendants
        }
        return render_to_response('admin/filer/trash/item_restore.html',
           context, context_instance=RequestContext(request))

    def file_check(self, request, file_id):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        try:
            file_obj = filer.models.filemodels.File.trash.get(id=file_id)
        except filer.models.filemodels.File.DoesNotExist, e:
            raise Http404

        data = {}
        file_exists = file_obj.file.storage.exists(file_obj.path)
        data['exists'] = file_exists
        if file_exists:
            # a bit of hack to force getting url even if it's in trash
            file_obj.deleted_at = None
            data['file_url'] = file_obj.url
        return HttpResponse(json.dumps(data), content_type="application/json")

    def changelist_view(self, request, extra_context=None):
        opts = self.model._meta

        if not self.has_change_permission(request, None):
            raise PermissionDenied

        items = self.queryset(request)
        paginator = Paginator(items, FILER_PAGINATE_BY)

        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        # If page request is out of range, deliver last page of results.
        try:
            paginated_items = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginated_items = paginator.page(paginator.num_pages)

        context = {
            'module_name': force_unicode(opts.verbose_name_plural),
            'media': self.media,
            'opts': opts,
            'app_label': opts.app_label,
            'paginator': paginator,
            'paginated_items': paginated_items,
        }
        context.update(extra_context or {})
        return render_to_response('admin/filer/trash/directory_listing.html',
           context, context_instance=RequestContext(request))
