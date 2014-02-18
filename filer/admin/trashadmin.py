from django.db import models
from django.contrib import admin
from django.utils.encoding import force_unicode
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse, Http404
from filer.utils.multi_model_qs import MultiMoldelQuerysetChain
from filer.settings import FILER_PAGINATE_BY
import filer
import json
import logging

logger = logging.getLogger(__name__)


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
            url(r'^(?P<filer_model>\w+)/(?P<filer_obj_id>\d+)/restore/$',
                self.admin_site.admin_view(self.restore_items),
                name='filer_restore_items'),
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

    def _check_restore_view_valid(self, request, filer_model, filer_obj_id):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        if filer_model not in ['file', 'folder']:
            logger.warning(
                'Restorable view for model %s is not available' % filer_model)
            raise Http404

        filer_model_cls = getattr(filer.models, filer_model.capitalize())
        try:
            filer_object = filer_model_cls.trash.get(id=filer_obj_id)
        except filer_model_cls.DoesNotExist, e:
            raise Http404

        # should not allow view for items that do not have alive container
        container_attr = 'folder' if filer_model == 'file' else 'parent'
        try:
            getattr(filer_object, container_attr)
        except filer.models.Folder.DoesNotExist, e:
            raise PermissionDenied

        return filer_model_cls, filer_object

    def restorable_item_view(self, request, filer_model, filer_obj_id):
        opts = self.model._meta
        filer_model_cls, filer_object = self._check_restore_view_valid(
            request, filer_model, filer_obj_id)

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
            'descendants': descendants,
            'title': u'Restore %s %s' % (
                filer_model.capitalize(), force_unicode(filer_object)),
        }
        return render_to_response('admin/filer/trash/item_restore.html',
           context, context_instance=RequestContext(request))

    def restore_items(self, request, filer_model, filer_obj_id):
        filer_model_cls, filer_object = self._check_restore_view_valid(
            request, filer_model, filer_obj_id)

        if request.method == 'POST' and request.POST.get('post'):
            filer_object.restore()

            if filer_model_cls is filer.models.Folder:
                return redirect(
                    filer_object.get_admin_directory_listing_url_path())
            else:
                if not filer_object.folder_id:
                    # clipboard files
                    return redirect('admin:filer-directory_listing-root')
                return redirect(filer_object.get_admin_url_path())

        raise PermissionDenied

    def file_check(self, request, file_id):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        try:
            file_obj = filer.models.filemodels.File.trash.get(id=file_id)
        except filer.models.filemodels.File.DoesNotExist, e:
            raise Http404

        data = {}
        file_exists = file_obj.file.storage.exists(file_obj.file.name)
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
            'title': u'Deleted Files and Folders',
        }
        context.update(extra_context or {})
        return render_to_response('admin/filer/trash/directory_listing.html',
           context, context_instance=RequestContext(request))
