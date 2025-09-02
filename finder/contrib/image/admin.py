from functools import cached_property

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

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            replace_file= True,
            download_file=True,
            view_original=True,
        )
        return settings
