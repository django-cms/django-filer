from functools import cached_property

from django.utils.html import format_html
from django.utils.text import format_lazy

from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from finder.admin.file import FileAdmin
from finder.contrib.image.forms import ImageFileForm
from finder.contrib.image.models import ImageFileModel


@admin.register(ImageFileModel)
class ImageAdmin(FileAdmin):

    @cached_property
    def form(self):
        attrs, extra_fields = {}, []
        alt_text_field = ImageFileForm.declared_fields['alt_text']
        meta_data_fields = list(ImageFileForm._meta.entangled_fields['meta_data'])
        index = meta_data_fields.index('alt_text')
        if settings.USE_I18N and len(settings.LANGUAGES) > 1:
            for code, language in settings.LANGUAGES:
                if code != settings.LANGUAGE_CODE:
                    field_name = f'alt_text_{code}'
                    label = format_lazy(_("{field} ({language})"), field=alt_text_field.label, language=language)
                    attrs[field_name] = alt_text_field.__class__(**dict(alt_text_field.__dict__, label=label))
                    extra_fields.append(field_name)
                    index += 1
                    meta_data_fields.insert(index, field_name)

        attrs['Meta'] = type('Meta', (ImageFileForm.Meta,), {
            'entangled_fields': {'meta_data': meta_data_fields},
            'fields': ImageFileForm._meta.fields + extra_fields,
        })
        return type(ImageFileForm.__name__, ImageFileForm.__mro__, attrs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and 'provenance' in obj.meta_data:
            readonly_fields.append('provenance')
        return readonly_fields

    @admin.display(description=_("Provenance"))
    def provenance(self, obj):
        provenance = obj.provenance
        return format_html(
            '<table><tr><th>{0}</th><td>{1}</td></tr><tr><th>{2}</th><td>{3}</td></tr></table>',
            _("Origin"),
            obj.digital_source_type_label or '–',
            _("Content Credentials"),
            _("found on upload, not verified") if provenance.has_content_credentials else '–',
        )

    def get_editor_settings(self, request, inode):
        return {
            **super().get_editor_settings(request, inode),
            'replace_file': True,
            'download_file': True,
            'view_original': True,
        }
