from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import BadRequest, ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.db.models import QuerySet, Subquery
from django.forms.renderers import DjangoTemplates
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.utils.decorators import method_decorator
from django.utils.html import strip_spaces_between_tags
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from finder.lookups import annotate_unified_queryset, lookup_by_label, sort_by_attribute
from finder.models.file import FileModel
from finder.models.folder import FolderModel
from finder.models.label import Label
from finder.models.realm import RealmModel


class FormRenderer(DjangoTemplates):
    def render(self, template_name, context, request=None):
        if template_name == 'django/forms/div.html':
            template_name = 'finder/forms/div.html'
        template = self.get_template(template_name)
        return template.render(context, request=request).strip()


class BrowserView(View):
    """
    The view for web component <finder-browser>.
    """
    action = None
    limit = 25

    def dispatch(self, request, *args, **kwargs):
        if self.action is None:
            return HttpResponseNotFound()
        action = getattr(self, self.action, None)
        if not callable(action):
            return HttpResponseBadRequest(f"Action {self.action} not allowed.")
        try:
            return JsonResponse(action(request, *args, **kwargs))
        except Exception as e:
            return HttpResponseBadRequest(str(e))

    def _get_children(cls, open_folders, parent):
        children = []
        for child in parent.subfolders:
            child_id = str(child.id)
            if child_id in open_folders:
                grandchildren = cls._get_children(open_folders, child)
            else:
                grandchildren = None
            children.append({
                'id': child_id,
                'name': child.name,
                'children': grandchildren,
                'is_open': grandchildren is not None,
                'has_subfolders': child.subfolders.exists(),
            })
        return children

    def _get_realm(self, request, slug):
        site = get_current_site(request)
        try:
            return RealmModel.objects.get(site=site, slug=slug)
        except RealmModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Realm named {slug} not found for {site.domain}.")

    @method_decorator(require_GET)
    def structure(self, request, slug):
        realm = self._get_realm(request, slug)
        root_folder_id = str(realm.root_folder.id)
        request.session.setdefault('finder.open_folders', [])
        request.session.setdefault('finder.last_folder', root_folder_id)
        last_folder_id = request.session['finder.last_folder']
        if is_open := realm.root_folder.subfolders.exists():
            # direct children of the root folder are open regardless of the `open_folders` session
            # in addition to that, also open all ancestors of the last opened folder
            open_folders = set(request.session['finder.open_folders'])
            try:
                ancestors = FolderModel.objects.get(id=last_folder_id).ancestors
            except FolderModel.DoesNotExist:
                pass
            if isinstance(ancestors, QuerySet):
                open_folders.update(map(str, ancestors.values_list('id', flat=True)))
            else:  # django-cte not installed
                open_folders.update(str(ancestor.id) for ancestor in ancestors)
            children = self._get_children(open_folders, realm.root_folder)
        else:
            children = None
        return {
            'root_folder': {
                'id': root_folder_id,
                'name': None,  # the root folder has no readable name
                'is_root': True,
                'is_open': is_open,
                'children': children,
                'has_subfolders': is_open,
            },
            'labels': [
                {'value': id, 'label': name, 'color': color}
                for id, name, color in Label.objects.values_list('id', 'name', 'color')
            ],
            'last_folder': request.session['finder.last_folder'],
            **self.list(request, request.session['finder.last_folder']),
        }

    @method_decorator(require_GET)
    def fetch(self, request, inode_id):
        """
        Open the given folder and fetch children data for the folder.
        """
        inode = FileModel.objects.get_inode(id=inode_id)
        inode_id = str(inode_id)
        if inode.is_folder:
            request.session.setdefault('finder.open_folders', [])
            if inode_id not in request.session['finder.open_folders']:
                request.session['finder.open_folders'].append(inode_id)
                request.session.modified = True
            return {
                'id': inode_id,
                'name': inode.name,
                'children': self._get_children(request.session['finder.open_folders'], inode),
                'is_open': True,
                'has_subfolders': inode.subfolders.exists(),
            }
        else:
            return inode.as_dict

    @method_decorator(require_GET)
    def open(self, request, folder_id):
        """
        Just open the folder.
        """
        folder_id = str(folder_id)
        request.session.setdefault('finder.open_folders', [])
        if folder_id not in request.session['finder.open_folders']:
            request.session['finder.open_folders'].append(folder_id)
            request.session.modified = True
        return {'id': folder_id}

    @method_decorator(require_GET)
    def close(self, request, folder_id):
        """
        Just close the folder.
        """
        folder_id = str(folder_id)
        try:
            request.session['finder.open_folders'].remove(folder_id)
        except (KeyError, ValueError):
            pass
        else:
            request.session.modified = True
        return {'id': folder_id}

    @method_decorator(require_GET)
    def list(self, request, folder_id):
        """
        List all the files of the given folder.
        """
        request.session['finder.last_folder'] = str(folder_id)
        offset = int(request.GET.get('offset', 0))
        recursive = 'recursive' in request.GET
        lookup = lookup_by_label(request)
        lookup['mime_types'] = request.GET.getlist('mimetypes')
        if recursive:
            descendants = FolderModel.objects.get(id=folder_id).descendants
            if isinstance(descendants, QuerySet):
                parent_ids = Subquery(descendants.values('id'))
            else:
                parent_ids = [descendant.id for descendant in descendants]
            unified_queryset = FileModel.objects.filter_unified(parent_id__in=parent_ids, is_folder=False, **lookup)
        else:
            unified_queryset = FileModel.objects.filter_unified(parent_id=folder_id, is_folder=False, **lookup)
        next_offset = offset + self.limit
        if next_offset >= unified_queryset.count():
            next_offset = None
        unified_queryset = sort_by_attribute(request, unified_queryset)
        annotate_unified_queryset(unified_queryset)
        return {
            'files': list(unified_queryset[offset:offset + self.limit]),
            'offset': next_offset,
            'recursive': recursive,
            'search_query': '',
        }

    @method_decorator(require_GET)
    def search(self, request, folder_id):
        """
        Search for files in either the descendants of given folder or in all folders.
        """
        search_query = request.GET.get('q')
        if not search_query:
            return HttpResponseBadRequest("No search query provided.")
        offset = int(request.GET.get('offset', 0))
        starting_folder = FolderModel.objects.get(id=folder_id)
        search_realm = request.COOKIES.get('django-finder-search-realm')
        if search_realm == 'everywhere':
            starting_folder = list(starting_folder.ancestors)[-1]
        if isinstance(starting_folder.descendants, QuerySet):
            parent_ids = Subquery(starting_folder.descendants.values('id'))
        else:  # django-cte not installed (slow)
            parent_ids = [descendant.id for descendant in starting_folder.descendants]

        lookup = {
            'parent_id__in': parent_ids,
            'name_lower__icontains': search_query,
        }
        unified_queryset = FileModel.objects.filter_unified(is_folder=False, **lookup)
        if offset + self.limit < unified_queryset.count():
            next_offset = offset + self.limit
        else:
            next_offset = None
        annotate_unified_queryset(unified_queryset)
        return {
            'files': unified_queryset[offset:next_offset],
            'offset': next_offset,
        }

    @method_decorator(require_POST)
    def upload(self, request, folder_id):
        """
        Upload a single file into the given folder.
        """
        if request.content_type != 'multipart/form-data' or 'upload_file' not in request.FILES:
            raise BadRequest("Bad form encoding or missing payload.")
        model = FileModel.objects.get_model_for(request.FILES['upload_file'].content_type)
        folder = FolderModel.objects.get(id=folder_id)
        file = model.objects.create_from_upload(
            request.FILES['upload_file'],
            folder=folder,
            owner=request.user,
        )
        form_class = file.get_form_class()
        form = form_class(instance=file, renderer=FormRenderer())
        response = {
            'file_info': file.as_dict,
            'form_html': mark_safe(strip_spaces_between_tags(form.as_div())),
        }
        return response

    @method_decorator(require_http_methods(['DELETE', 'POST']))
    def change(self, request, file_id):
        """
        Change some fields after uploading a single file.
        """
        file = FileModel.objects.get_inode(id=file_id)
        if request.method == 'DELETE':
            file.delete()
            return {'file_info': None}
        if request.content_type != 'multipart/form-data':
            raise BadRequest("Bad form encoding or missing payload.")
        form_class = file.get_form_class()
        form = form_class(instance=file, data=request.POST, renderer=FormRenderer())
        if form.is_valid():
            file = form.save()
            return {'file_info': file.as_dict}
        else:
            return {'form_html': mark_safe(strip_spaces_between_tags(form.as_div()))}

    @method_decorator(require_POST)
    def crop(self, request, image_id):
        image = FileModel.objects.get_inode(id=image_id, mime_types=['image/*'], is_folder=False)
        width, height = int(request.POST.get('width')), int(request.POST.get('height'))
        cropped_image_path = image.get_cropped_path(width, height)
        if not default_storage.exists(cropped_image_path):
            image.crop(cropped_image_path, width, height)
        cropped_image_url = default_storage.url(cropped_image_path)
        return {
            'image_id': image_id,
            'alt_text': image.meta_data.get('alt_text', image.name),
            'cropped_image_url': cropped_image_url,
            'width': width,
            'height': height,
        }
