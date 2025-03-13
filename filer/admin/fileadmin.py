import mimetypes

from django import forms
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.admin.utils import unquote
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext as _

from easy_thumbnails.engine import NoSourceGenerator
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.models import Thumbnail as EasyThumbnail
from easy_thumbnails.options import ThumbnailOptions

from .. import settings
from ..models import BaseImage, File
from ..settings import DEFERRED_THUMBNAIL_SIZES
from ..utils.loader import load_model
from .permissions import PrimitivePermissionAwareModelAdmin
from .tools import AdminContext, admin_url_params_encoded, popup_status


Image = load_model(settings.FILER_IMAGE_MODEL)


class FileAdminChangeFrom(forms.ModelForm):
    class Meta:
        model = File
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "file" in self.fields:
            self.fields["file"].widget = forms.FileInput()

    def clean(self):
        from ..validation import validate_upload
        cleaned_data = super().clean()
        if "file" in self.changed_data and cleaned_data["file"]:
            mime_type = mimetypes.guess_type(cleaned_data["file"].name)[0] or 'application/octet-stream'
            file = cleaned_data["file"]
            file.open("w+")  # Allow for sanitizing upload
            file.seek(0)
            validate_upload(
                file_name=cleaned_data["file"].name,
                file=file.file,
                owner=cleaned_data.get("owner"),
                mime_type=mime_type,
            )
            file.open("r")
        return self.cleaned_data


class FileAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('label',)
    list_per_page = 10
    search_fields = ['name', 'original_filename', 'sha1', 'description']
    autocomplete_fields = ['owner']
    readonly_fields = ('sha1', 'display_canonical')

    form = FileAdminChangeFrom

    @classmethod
    def build_fieldsets(cls, extra_main_fields=(), extra_advanced_fields=(),
                        extra_fieldsets=()):
        fieldsets = (
            (None, {
                'fields': (
                    'name',
                    'owner',
                    'description',
                ) + extra_main_fields,
            }),
            (_('Advanced'), {
                'fields': (
                    'file',
                    'sha1',
                    'display_canonical',
                ) + extra_advanced_fields,
                'classes': ('collapse',),
            }),
        ) + extra_fieldsets
        if settings.FILER_ENABLE_PERMISSIONS:
            fieldsets = fieldsets + (
                (None, {
                    'fields': ('is_public',)
                }),
            )
        return fieldsets

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        """
        if (
            request.POST
            and '_continue' not in request.POST
            and '_saveasnew' not in request.POST
            and '_addanother' not in request.POST
            and '_edit_from_widget' not in request.POST
        ):
            # Popup in pick mode or normal mode. In both cases we want to go
            # back to the folder list view after save. And not the useless file
            # list view.
            if obj.folder:
                url = reverse('admin:filer-directory_listing',
                              kwargs={'folder_id': obj.folder.id})
            else:
                url = reverse(
                    'admin:filer-directory_listing-unfiled_images')
            url = "{}{}".format(
                url,
                admin_url_params_encoded(request),
            )
            return HttpResponseRedirect(url)

        # Add media to context to allow default django js inclusions in django/filer/base_site.html ({{ media.js }})
        # This is required by popup_handling.js used in popup_response
        template_response = super().response_change(request, obj)
        if hasattr(template_response, 'context_data'):
            template_response.context_data["media"] = self.media
        return template_response

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        context.update({
            'show_delete': True,
            'history_url': admin_urlname(self.opts, 'history'),
            'expand_image_url': None,
            'is_popup': popup_status(request),
            'filer_admin_context': AdminContext(request),
        })
        if obj and obj.mime_maintype == 'image' and obj.file.exists():
            if 'svg' in obj.mime_type:
                context['expand_image_url'] = reverse(admin_urlname(Image._meta, 'expand'), args=(obj.pk,))
            else:
                context['expand_image_url'] = obj.file.url
        return super().render_change_form(
            request=request, context=context, add=add, change=change,
            form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a image.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.
        """
        try:
            obj = self.get_queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.folder
        except self.model.DoesNotExist:
            parent_folder = None

        if request.POST:
            # Return to folder listing, since there is no usable file listing.
            super().delete_view(
                request=request, object_id=object_id,
                extra_context=extra_context)
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                              kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-unfiled_images')
            url = "{}{}".format(
                url,
                admin_url_params_encoded(request)
            )
            return HttpResponseRedirect(url)

        return super().delete_view(
            request=request, object_id=object_id,
            extra_context=extra_context)

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

    def display_canonical(self, instance):
        canonical = instance.canonical_url
        if canonical:
            return mark_safe(f'<a href="{canonical}">{canonical}</a>')
        else:
            return '-'
    display_canonical.allow_tags = True
    display_canonical.short_description = _('canonical URL')

    def get_urls(self):
        return super().get_urls() + [
            path("icon/<int:file_id>/<int:size>",
                 self.admin_site.admin_view(self.icon_view),
                 name=f"filer_{self.model._meta.model_name}_fileicon")
        ]

    def icon_view(self, request, file_id: int, size: int) -> HttpResponse:
        if size not in DEFERRED_THUMBNAIL_SIZES:
            # Only allow icon sizes relevant for the admin
            raise Http404
        file = get_object_or_404(File, pk=file_id)
        if not isinstance(file, BaseImage):
            raise Http404()

        try:
            thumbnailer = get_thumbnailer(file)
            thumbnail_options = ThumbnailOptions({'size': (size, size), "crop": True})
            thumbnail = thumbnailer.get_thumbnail(thumbnail_options, generate=True)
            # Touch thumbnail to allow it to be prefetched for directory listing
            EasyThumbnail.objects.filter(name=thumbnail.name).update(modified=now())
            return HttpResponseRedirect(thumbnail.url)
        except (InvalidImageFormatError, NoSourceGenerator):
            return HttpResponseRedirect(staticfiles_storage.url('filer/icons/file-missing.svg'))


FileAdmin.fieldsets = FileAdmin.build_fieldsets()
