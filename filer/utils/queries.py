from django.db import connections


# Bound IN lists even when the backend declares no parameter limit.
QUERY_BATCH_SIZE = 1000


def batched_querysets(queryset, field, ids):
    """Yield one queryset per bounded IN list on the queryset's database."""
    ids = list(ids)
    max_params = connections[queryset.db].features.max_query_params
    batch_size = min(QUERY_BATCH_SIZE, max_params or QUERY_BATCH_SIZE)
    for offset in range(0, len(ids), batch_size):
        yield queryset.filter(**{f'{field}__in': ids[offset:offset + batch_size]})


def filter_in_batches(queryset, field, ids):
    """Yield rows with bounded IN lists on the queryset's database."""
    for batch in batched_querysets(queryset, field, ids):
        yield from batch


def chunked_by_pk(queryset, size=None):
    """
    Yield lists of at most ``size`` rows in primary key order, one query per
    list. Rows are fetched by key rather than by offset, so callers may
    delete each list before the next one is read.
    """
    size = size or QUERY_BATCH_SIZE
    queryset = queryset.order_by('pk')
    last = None
    while True:
        rows = queryset if last is None else queryset.filter(pk__gt=last)
        chunk = list(rows[:size])
        if not chunk:
            return
        yield chunk
        last = chunk[-1].pk
