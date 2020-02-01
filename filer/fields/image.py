from .. import settings
from .file import AdminFileFormField, AdminFileWidget, FilerFileField


class AdminImageWidget(AdminFileWidget):
    pass


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = settings.FILER_IMAGE_MODEL
