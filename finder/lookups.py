import json

from finder.models.inode import InodeManager
from finder.models.filetag import LabelTag


def annotate_unified_queryset(ambit, queryset):
    """
    Annotates the given queryset with additional fields for the frontend.
    This step must be applied after filtering and sorting.
    """
    label_tags = {str(lt['id']): lt for lt in LabelTag.objects.values('id', 'label', 'color')}
    for entry in queryset:
        proxy_obj = InodeManager.get_proxy_object(entry)
        entry.update(
            download_url=proxy_obj.get_download_url(ambit),
            thumbnail_url=proxy_obj.get_thumbnail_url(ambit),
            preview_url=proxy_obj.get_preview_url(ambit),
            sample_url=proxy_obj.get_sample_url(ambit),
            summary=proxy_obj.summary,
            folderitem_component=proxy_obj.folderitem_component,
        )
        if tag_ids := entry.pop('tag_ids', None):
            entry['label_tags'] = [label_tags[id] for id in tag_ids if id in label_tags]
        entry.pop('name_lower', None)  # only used for searching


def lookup_by_tag(request):
    lookup = {}
    if filter := request.COOKIES.get('django-finder-filter'):
        allowed_tags = LabelTag.objects.values_list('id', flat=True)
        include_tags, exclude_tags = [], []
        try:
            for key, value in json.loads(filter).items():
                if int(key) in allowed_tags:
                    if value:
                        include_tags.append(int(key))
                    else:
                        exclude_tags.append(int(key))
        except ValueError:
            pass
        if include_tags:
            lookup['tags__in'] = include_tags
        if exclude_tags:
            lookup['tags__not_in'] = exclude_tags
    return lookup


def lookup_by_read_permission(request):
    return {'user': request.user, 'has_read_permission': True}


def sort_by_attribute(request, unified_queryset):
    sorting_map = {
        'name_asc': 'name_lower',
        'name_desc': '-name_lower',
        'date_asc': 'last_modified_at',
        'date_desc': '-last_modified_at',
        'size_asc': 'file_size',
        'size_desc': '-file_size',
        'type_asc': 'mime_type',
        'type_desc': '-mime_type',
    }

    sorting = sorting_map.get(request.COOKIES.get('django-finder-sorting'), 'ordering')
    return unified_queryset.order_by(sorting)
