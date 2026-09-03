import logging

from django.core.exceptions import BadRequest, ValidationError, ObjectDoesNotExist, PermissionDenied
from django.db.models import BooleanField, QuerySet, Subquery, Value
from django.forms.renderers import DjangoTemplates
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.utils.html import strip_spaces_between_tags
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from finder.lookups import annotate_unified_queryset, lookup_by_tag, sort_by_attribute
from finder.models.ambit import AmbitModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel
from finder.models.filetag import FileTag
from finder.models.permission import AccessControlEntry, Privilege


logger = logging.getLogger(__name__)


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
    limit = 100

    def dispatch(self, request, *args, **kwargs):
        if self.action is None:
            return HttpResponseNotFound()
        action = getattr(self, self.action, None)
        if not callable(action):
            return HttpResponseBadRequest(f"Action {self.action} not allowed.")
        try:
            return JsonResponse(action(request, *args, **kwargs))
        except ObjectDoesNotExist as e:
            return HttpResponseNotFound(str(e))
        except (PermissionDenied, PermissionError) as e:
            return HttpResponseForbidden(str(e))
        except ValidationError as e:
            return JsonResponse({'error': e.messages}, status=422)
        except Exception as e:
            return HttpResponseBadRequest(str(e))

    @classmethod
    def _get_children(cls, ambit, can_view_subquery, open_folders, parent):
        children = []
        for subfolder in parent.subfolders.annotate(can_view=can_view_subquery).filter(can_view=True):
            child = subfolder.as_dict(ambit)
            if str(subfolder.id) in open_folders:
                child.update(
                    children=cls._get_children(ambit, can_view_subquery, open_folders, subfolder),
                    is_open=True,
                )
            else:
                child.update(children=None, is_open=False)
            children.append(child)
        return children

    @classmethod
    def _get_can_view_subquery(cls, user):
        if user.is_superuser:
            return Value(True, output_field=BooleanField())
        else:
            return AccessControlEntry.objects.privilege_subquery_exists(user, Privilege.READ)

    #: Sent both when an ambit does not exist and when it may not be read, so that the
    #: response cannot be used to find out which ambits a site has configured.
    access_denied_message = _("You do not have permission to browse this folder tree.")

    def _get_ambit(self, request, slug):
        """
        Look up an ambit by its slug, refusing anonymously.

        The reason is written to the log rather than to the response: telling a caller
        that a slug does not exist, while an existing one it may not read is refused
        differently, would let it enumerate the ambits of a site.
        """
        try:
            ambit = AmbitModel.objects.get(slug=slug)
        except AmbitModel.DoesNotExist:
            logger.warning(
                "No ambit named “%s”. It is the `ambit` of the model field rendering the "
                "widget, or FINDER_DEFAULT_AMBIT if the field declares none. Run "
                "`manage.py finder list-ambits` to see the configured ones.", slug,
            )
            raise PermissionDenied(self.access_denied_message)
        if not ambit.root_folder.has_permission(request.user, Privilege.READ):
            logger.warning("“%s” may not read the root folder of ambit “%s”.", request.user, slug)
            raise PermissionDenied(self.access_denied_message)
        return ambit

    @staticmethod
    def _get_last_folder(ambit, folder_id):
        """
        The folder the browser reopens on, falling back to the root folder of `ambit`.

        `finder.last_folder` is one session key shared by every ambit, and it outlives the
        folder it names: deleting and recreating an ambit, or opening the browser for a
        different one, leaves an id behind which does not belong here. Without this the
        request fails with a bare 404, because listing that folder raises `DoesNotExist`.
        """
        if folder_id:
            try:
                folder = FolderModel.objects.get(id=folder_id)
            except (FolderModel.DoesNotExist, ValidationError, ValueError):
                pass
            else:
                if folder.get_ambit().id == ambit.id:
                    return folder
        return ambit.root_folder

    @method_decorator(require_GET)
    def structure(self, request, slug=None):
        ambit = self._get_ambit(request, slug)
        request.session.setdefault('finder.open_folders', [])
        last_folder = self._get_last_folder(ambit, request.GET.get('folder') or request.session.get('finder.last_folder'))
        last_folder_id = str(last_folder.id)
        request.session['finder.last_folder'] = last_folder_id
        if is_open := ambit.root_folder.subfolders.exists():
            # direct children of the root folder are open regardless of the session variable `open_folders`.
            # in addition to that, also open all ancestors of the last opened folder
            open_folders = {last_folder_id, *request.session['finder.open_folders']}
            ancestors = last_folder.ancestors
            can_view_subquery = self._get_can_view_subquery(request.user)
            if isinstance(ancestors, QuerySet):  # pragma: with django-cte
                open_folders.update(map(str, ancestors.values_list('id', flat=True)))
            else:  # pragma: without django-cte
                open_folders.update(str(ancestor.id) for ancestor in ancestors)
            children = self._get_children(ambit, can_view_subquery, open_folders, ambit.root_folder)
        else:
            children = None
        return {
            'root_folder': {
                **ambit.root_folder.as_dict(ambit),
                'name': None,  # the root folder has no readable name
                'is_root': True,
                'is_open': is_open,
                'children': children,
            },
            'tags': [
                {'value': id, 'label': label, 'color': color}
                for id, label, color in FileTag.objects.values_list('id', 'label', 'color')
            ],
            'last_folder': last_folder_id,
            **self.list(request, last_folder_id),
        }

    @method_decorator(require_GET)
    def fetch(self, request, inode_id):
        """
        Open the given folder and fetch children data for the given folder.
        """
        inode = FileModel.objects.get_inode(id=inode_id)
        ambit = inode.folder.get_ambit()
        inode_id = str(inode_id)
        if inode.is_folder:
            can_view_subquery = self._get_can_view_subquery(request.user)
            request.session.setdefault('finder.open_folders', [])
            if inode_id not in request.session['finder.open_folders']:
                request.session['finder.open_folders'].append(inode_id)
                request.session.modified = True
            open_folders = request.session['finder.open_folders']
            return {
                'id': inode_id,
                'name': inode.name,
                'children': self._get_children(ambit, can_view_subquery, open_folders, inode),
                'is_open': True,
                'has_subfolders': inode.subfolders.exists(),
            }
        else:
            return inode.as_dict(ambit)

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
        lookup = {
            **lookup_by_tag(request),
            'user': request.user,
            'can_view': True,
            'mime_types': request.GET.getlist('mimetypes'),
        }
        current_folder = FolderModel.objects.get(id=folder_id)
        if recursive:
            if isinstance(current_folder.descendants, QuerySet):
                parent_ids = Subquery(current_folder.descendants.values('id'))
            else:
                parent_ids = [descendant.id for descendant in current_folder.descendants]
            unified_queryset = FileModel.objects.filter_unified(parent_id__in=parent_ids, is_folder=False, **lookup)
        else:
            unified_queryset = FileModel.objects.filter_unified(parent_id=folder_id, is_folder=False, **lookup)
        next_offset = offset + self.limit
        if next_offset >= unified_queryset.count():
            next_offset = None

        ambit = current_folder.get_ambit()
        unified_queryset = sort_by_attribute(request, unified_queryset)
        annotate_unified_queryset(ambit, unified_queryset)
        return {
            'files': list(unified_queryset[offset:offset + self.limit]),
            'has_upload_permission': current_folder.has_permission(request.user, Privilege.WRITE),
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
        search_zone = request.COOKIES.get('django-finder-search-zone')
        if search_zone == 'everywhere':
            starting_folder = list(starting_folder.ancestors)[-1]
        if isinstance(starting_folder.descendants, QuerySet):  # pragma: with django-cte
            parent_ids = Subquery(starting_folder.descendants.values('id'))
        else:  # pragma: without django-cte
            parent_ids = [descendant.id for descendant in starting_folder.descendants]

        ambit = starting_folder.get_ambit()
        lookup = {
            'parent_id__in': parent_ids,
            'name_lower__icontains': search_query,
        }
        unified_queryset = FileModel.objects.filter_unified(is_folder=False, **lookup)
        if offset + self.limit < unified_queryset.count():
            next_offset = offset + self.limit
        else:
            next_offset = None
        annotate_unified_queryset(ambit, unified_queryset)
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
        current_folder = FolderModel.objects.get(id=folder_id)
        if not current_folder.has_permission(request.user, Privilege.WRITE):
            raise PermissionDenied("Permission denied to upload file.")
        ambit = current_folder.get_ambit()
        file = model.objects.create_from_upload(
            ambit,
            request.FILES['upload_file'],
            folder=current_folder,
            owner=request.user,
        )
        form_class = file.get_form_class()
        form = form_class(instance=file, renderer=FormRenderer())
        response = {
            'file_info': file.as_dict(ambit),
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
        ambit = file.folder.get_ambit()
        form_class = file.get_form_class()
        form = form_class(instance=file, data=request.POST, renderer=FormRenderer())
        if form.is_valid():
            file = form.save()
            file.as_dict.cache_clear()
            return {'file_info': file.as_dict(ambit)}
        else:
            return {'form_html': mark_safe(strip_spaces_between_tags(form.as_div()))}

    @method_decorator(require_POST)
    def crop(self, request, image_id):
        """
        Widgets using the <finder-file-select> use this endpoint to fetch a cropped version of the image.
        """
        image = FileModel.objects.get_inode(id=image_id, mime_types=['image/*'], is_folder=False)
        ambit = image.folder.get_ambit()
        width, height = request.POST.get('width'), request.POST.get('height')
        width = int(width) if str(width).isdigit() else None
        height = int(height) if str(height).isdigit() else None
        if width is None and height is None:
            raise ValidationError(gettext("At least one of width or height must be given."))
        if width is None:
            width = round(height * image.width / image.height)
        if height is None:
            height = round(width / image.width * image.height)
        cropped_image_path = f'{image.id}/{image.get_cropped_filename(width, height)}'
        if not ambit.sample_storage.exists(cropped_image_path):
            image.crop(ambit, cropped_image_path, width, height)
        return {
            'image_id': image_id,
            'cropped_image_url': ambit.sample_storage.url(cropped_image_path),
            'width': width,
            'height': height,
            'meta_data': image.get_meta_data(),
        }
