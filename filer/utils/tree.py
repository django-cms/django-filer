from .queries import filter_in_batches


def walk_tree_levels(roots, children):
    """Yield keyed levels once, including roots, even with overlaps or cycles."""
    level = dict(roots)
    seen = set(level)
    while level:
        yield level
        level = {pk: obj for pk, obj in children(level) if pk not in seen}
        seen.update(level)


def walk_folder_levels(roots, queryset, link):
    """
    Yield folder levels below ``roots`` (a ``{pk: row}`` dict), one query per
    level. Children are ``queryset`` rows by name; ``link(row, level)`` turns
    a row into a ``(pk, row)`` pair, or returns ``None`` to prune its subtree.
    """
    def children(level):
        for row in filter_in_batches(queryset.order_by('name'), 'parent_id', level):
            item = link(row, level)
            if item is not None:
                yield item

    yield from walk_tree_levels(roots, children)
