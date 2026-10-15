from django.db import connections


# Bound IN lists even when the backend declares no parameter limit.
QUERY_BATCH_SIZE = 1000


def filter_in_batches(queryset, field, ids):
    """Yield rows with bounded IN lists on the queryset's database."""
    ids = list(ids)
    max_params = connections[queryset.db].features.max_query_params
    batch_size = min(QUERY_BATCH_SIZE, max_params or QUERY_BATCH_SIZE)
    for offset in range(0, len(ids), batch_size):
        yield from queryset.filter(**{f'{field}__in': ids[offset:offset + batch_size]})
