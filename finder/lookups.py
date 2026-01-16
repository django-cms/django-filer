from finder.models.inode import InodeManager
from finder.models.label import Label


def annotate_unified_queryset(ambit, queryset):
    """
    Annotates the given queryset with additional fields for the frontend.
    This step must be applied after filtering and sorting.
    """
    labels = Label.objects.values_list('id', 'name', 'color')
    for entry in queryset:
        proxy_obj = InodeManager.get_proxy_object(entry)
        entry.update(
            download_url=proxy_obj.get_download_url(ambit),
            thumbnail_url=proxy_obj.get_thumbnail_url(ambit),
            sample_url=proxy_obj.get_sample_url(ambit),
            summary=proxy_obj.summary,
            folderitem_component=proxy_obj.folderitem_component,
        )
        if label_ids := entry.pop('label_ids', None):
            label_ids = list(map(int, label_ids.split(',')))
            entry['labels'] = [
                {'id': id, 'name': name, 'color': color}
                for id, name, color in labels if id in label_ids
            ]
        entry.pop('name_lower', None)  # only used for searching


def lookup_by_label(request):
    lookup = {}
    if filter := request.COOKIES.get('django-finder-filter'):
        allowed_labels = Label.objects.values_list('id', flat=True)
        try:
            if label_ids := [int(v) for v in filter.split(',') if int(v) in allowed_labels]:
                lookup['labels__in'] = label_ids
        except ValueError:
            pass
    return lookup


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
