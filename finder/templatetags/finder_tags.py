from django import template

from finder.models.file import FileModel

register = template.Library()


@register.simple_tag
def download_url(file_id):
    try:
        finder_file = FileModel.objects.get_inode(id=file_id, is_folder=False)
    except FileModel.DoesNotExist:
        return ''
    ambit = finder_file.get_ambit()
    return finder_file.get_download_url(ambit)
