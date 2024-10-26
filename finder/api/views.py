from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import BadRequest, ObjectDoesNotExist
from django.db.models import QuerySet, Subquery
from django.db.models.functions import Lower
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View

from finder.models.file import AbstractFileModel
from finder.models.folder import FolderModel, RealmModel
from finder.models.label import Label


class BrowserView(View):
    """
    The view for web component <finder-browser>.
    """
    action = None
    sorting_map = {
        'name_asc': (Lower('name').asc(), lambda file: file['name'].lower(), False),
        'name_desc': (Lower('name').desc(), lambda file: file['name'].lower(), True),
        'date_asc': ('last_modified_at', lambda file: file['last_modified_at'], False),
        'date_desc': ('-last_modified_at', lambda file: file['last_modified_at'], True),
        'size_asc': ('file_size', lambda file: file.get('file_size', 0), False),
        'size_desc': ('-file_size', lambda file: file.get('file_size', 0), True),
        'type_asc': ('mime_type', lambda file: file.get('mime_type', ''), False),
        'type_desc': ('-mime_type', lambda file: file.get('mime_type', ''), True),
    }

    def dispatch(self, request, *args, **kwargs):
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

    def structure(self, request, realm):
        site = get_current_site(request)
        try:
            realm = RealmModel.objects.get(site=site, slug=realm)
        except RealmModel.DoesNotExist:
            raise ObjectDoesNotExist(f"Realm {realm} not found for {site.domain}.")
        root_folder = FolderModel.objects.get_root_folder(realm)
        root_folder_id = str(root_folder.id)
        request.session.setdefault('finder.open_folders', [])
        request.session.setdefault('finder.last_folder', root_folder_id)
        if is_open := root_folder.subfolders.exists():
            # direct children of the root folder are open regardless of the `open_folders` session
            children = self._get_children(request.session['finder.open_folders'], root_folder)
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
            'last_folder': request.session['finder.last_folder'],
            **self.list(request, request.session['finder.last_folder']),
        }

    def fetch(self, request, folder_id):
        """
        Open the given folder and fetch children data for the folder.
        """
        folder = FolderModel.objects.get(id=folder_id)
        folder_id = str(folder_id)
        request.session.setdefault('finder.open_folders', [])
        if folder_id not in request.session['finder.open_folders']:
            request.session['finder.open_folders'].append(folder_id)
            request.session.modified = True

        return {
            'id': folder_id,
            'name': folder.name,
            'children': self._get_children(request.session['finder.open_folders'], folder),
            'is_open': True,
            'has_subfolders': folder.subfolders.exists(),
        }

    def open(self, request, folder_id):
        """
        Just open the folder.
        """
        folder_id = str(folder_id)
        request.session.setdefault('finder.open_folders', [])
        if folder_id not in request.session['finder.open_folders']:
            request.session['finder.open_folders'].append(folder_id)
            request.session.modified = True

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

    def filter_lookup(self, request):
        """
        Get the lookup for filtering files by labels.
        """
        lookup = {}
        if filter := request.COOKIES.get('django-finder-filter'):
            allowed_labels = Label.objects.values_list('id', flat=True)
            try:
                if label_ids := [int(v) for v in filter.split(',') if int(v) in allowed_labels]:
                    lookup['labels__in'] = label_ids
                    request.COOKIES['django-finder-filter'] = ','.join(map(str, label_ids))
                else:
                    raise ValueError
            except ValueError:
                request.COOKIES.pop('django-finder-filter', None)
        return lookup

    def list(self, request, folder_id):
        """
        List all the files of the given folder.
        """
        folder = FolderModel.objects.get(id=folder_id)
        lookup = self.filter_lookup(request)
        request.session['finder.last_folder'] = str(folder_id)
        return {
            'files': [{
                'id': str(file.id),
                'name': file.name,
                'mime_type': file.mime_type,
                'browser_component': file.cast.browser_component,
                'thumbnail_url': file.cast.get_thumbnail_url(),
                'sample_url': getattr(file.cast, 'get_sample_url', lambda: None)(),
                'labels': file.serializable_value('labels'),
            } for file in folder.listdir(is_folder=False, **lookup)]
        }

    def search(self, request, folder_id):
        """
        Search for files in either the descendants of given folder or in all folders.
        """
        search_query = request.GET.get('q')
        if not search_query:
            return HttpResponseBadRequest("No search query provided.")
        starting_folder = FolderModel.objects.get(id=folder_id)
        search_realm = request.COOKIES.get('django-finder-search-realm')
        if search_realm == 'everywhere':
            starting_folder = starting_folder.ancestors[-1]
        if isinstance(starting_folder.descendants, QuerySet):
            parent_ids = Subquery(starting_folder.descendants.values('id'))
        else:
            parent_ids = [descendant.id for descendant in starting_folder.descendants]

        lookup = {
            'parent_id__in': parent_ids,
            'name__icontains': search_query,
            **self.filter_lookup(request),
        }

        sorting = self.sorting_map.get(request.COOKIES.get('django-finder-sorting'))

        files = []
        for file_model in InodeModel.get_models():
            queryset = file_model.objects.filter(**lookup)
            if sorting:
                queryset = queryset.order_by(sorting[0])
            files.extend([{
                'id': str(file.id),
                'name': file.name,
                'mime_type': file.mime_type,
                'last_modified_at': file.last_modified_at,
                'browser_component': file.cast.browser_component,
                'thumbnail_url': file.cast.get_thumbnail_url(),
                'sample_url': getattr(file.cast, 'get_sample_url', lambda: None)(),
                'labels': file.serializable_value('labels'),
            } for file in queryset.distinct()])
        if sorting:
            files.sort(key=sorting[1], reverse=sorting[2])
        return {'files': files}

    def upload(self, request, folder_id):
        """
        Upload a single file into the given folder.
        """
        if request.method != 'POST':
            raise BadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if request.content_type != 'multipart/form-data' or 'upload_file' not in request.FILES:
            raise BadRequest("Bad form encoding or missing payload.")
        model = FileModel.objects.get_model_for(request.FILES['upload_file'].content_type)
        folder = FolderModel.objects.get(id=folder_id)
        file = model.objects.create_from_upload(
            request.FILES['upload_file'],
            folder=folder,
            owner=request.user,
        )
        return {
            'uploaded_file': {
                'id': str(file.id),
                'name': file.name,
                'mime_type': file.mime_type,
                'last_modified_at': file.last_modified_at,
                'browser_component': file.cast.browser_component,
                'thumbnail_url': file.cast.get_thumbnail_url(),
                'sample_url': getattr(file.cast, 'get_sample_url', lambda: None)(),
                'labels': file.serializable_value('labels'),
            }
        }
