from django.db import models
from django.contrib import admin
from django.utils.encoding import force_unicode
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from filer.utils.multi_model_qs import MultiMoldelQuerysetChain
from django.shortcuts import render_to_response
from django.template import RequestContext
from filer.settings import FILER_PAGINATE_BY
import filer


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
            url(r'^folder/(?P<folder_id>\d+)/$',
                self.admin_site.admin_view(self.folder_view),
                name='filer_trash_folder'),
            url(r'^file/(?P<file_id>\d+)/$',
                self.admin_site.admin_view(self.file_view),
                name='filer_trash_file'),
            url(r'^folder/(?P<folder_id>\d+)/restore/$',
                self.admin_site.admin_view(self.restore_folder_view),
                name='filer_trash_folder_restore'),
            url(r'^file/(?P<file_id>\d+)/restore/$',
                self.admin_site.admin_view(self.restore_file_view),
                name='filer_trash_file_restore'),
            )
        url_patterns.extend(urls)
        return url_patterns

    def queryset(self, request):
        files_q = Q(folder__deleted_at__isnull=True)
        folders_q = Q(Q(parent=None) | Q(parent__deleted_at__isnull=True))
        file_qs = filer.models.filemodels.File.trash.filter(files_q)
        folder_qs = filer.models.foldermodels.Folder.trash.filter(folders_q)
        return MultiMoldelQuerysetChain([folder_qs, file_qs])

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def restore_folder_view(self, request, folder_id):
        raise PermissionDenied

    def restore_file_view(self, request, file_id):
        raise PermissionDenied

    def folder_view(self, request, folder_id):
        raise PermissionDenied

    def file_view(self, request, file_id):
        raise PermissionDenied

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
