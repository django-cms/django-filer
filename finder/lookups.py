from finder.models.inode import InodeManager
from finder.models.filetag import FileTag


def annotate_unified_queryset(ambit, queryset):
    """
    Annotates the given queryset with additional fields for the frontend.
    This step must be applied after filtering and sorting.
    """
    tags = FileTag.objects.values_list('id', 'label', 'color')
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
        if getattr(proxy_obj, 'is_ai_generated', False):
            # images created or edited using generative AI show their origin in the list
            entry['origin'] = str(proxy_obj.digital_source_type_label)
        if tag_ids := entry.pop('tag_ids', None):
            tag_ids = list(map(int, tag_ids.split(',')))
            entry['tags'] = [
                {'id': id, 'label': label, 'color': color}
                for id, label, color in tags if id in tag_ids
            ]
        entry.pop('name_lower', None)  # only used for searching


def lookup_by_tag(request):
    lookup = {}
    if filter := request.COOKIES.get('django-finder-filter'):
        allowed_tags = FileTag.objects.values_list('id', flat=True)
        try:
            if tag_ids := [int(v) for v in filter.split(',') if int(v) in allowed_tags]:
                lookup['tags__in'] = tag_ids
        except ValueError:
            pass
    return lookup


def lookup_by_provenance(request):
    """
    Filter images created or edited using generative AI (`ai`) and/or uploaded with
    C2PA Content Credentials (`c2pa`).
    """
    lookup = {}
    if filter := request.COOKIES.get('django-finder-provenance'):
        if provenance := [v for v in filter.split(',') if v in ('ai', 'c2pa')]:
            lookup['provenance'] = provenance
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
