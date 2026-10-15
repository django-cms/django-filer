def walk_tree_levels(roots, children):
    """Yield keyed levels once, including roots, even with overlaps or cycles."""
    level = dict(roots)
    seen = set(level)
    while level:
        yield level
        level = {pk: obj for pk, obj in children(level) if pk not in seen}
        seen.update(level)
