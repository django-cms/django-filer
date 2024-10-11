from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views import View

from finder.models.folder import FolderModel, RealmModel


class BrowserView(View):
    """
    The view for web component <finder-browser>.
    """
    action = None

    def get(self, request, *args, **kwargs):
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

    def list(self, request, folder_id):
        """
        List all the files of the given folder.
        """
        folder = FolderModel.objects.get(id=folder_id)
        request.session['finder.last_folder'] = str(folder_id)

        folder.listdir(is_folder=False)

        return {
            'files': [{
                'id': str(file.id),
                'name': file.name,
                'mime_type': file.mime_type,
                'browser_component': file.casted.browser_component,
                'thumbnail_url': file.casted.get_thumbnail_url(),
                'sample_url': getattr(file.casted, 'get_sample_url', lambda: None)(),
                'labels': file.serializable_value('labels'),
            } for file in folder.listdir(is_folder=False)]
        }
