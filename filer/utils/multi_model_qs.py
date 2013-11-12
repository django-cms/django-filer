import itertools


class MultiMoldelQuerysetChain(object):
    """
    Allows passing a list of different models querysets to a paginator without
    transforming them into one list.
    """

    def __init__(self, qsets):
        self._qsets = qsets
        self._offsets = []
        offset = 0
        for q in qsets:
            self._offsets.append(offset)
            offset += q.count()
        self.length = offset

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._get_slice(key)
        elif isinstance(key, (int, long)):
            return self._get_item(key)
        else:
            raise TypeError("QuerysetChain index must be int or slice not {}".format(type(key)))

    def _get_item(self, key):
        if key < 0:
            raise IndexError("index out of bounds {}".format(key))
        for index, offset in enumerate(self._offsets):
            qset = self._qsets[index]
            if key-offset < qset.count():
                return qset[key-offset]
        raise IndexError("index out of bounds {}".format(key))

    def _get_slice(self, key):
        assert key.start is not None
        assert key.stop is not None
        assert key.step is None
        slices = (self.slice(qs, key.start-offset, key.stop-offset)
                  for qs, offset in itertools.izip(self._qsets, self._offsets))
        return reduce(lambda s1, s2: s1+s2, slices)

    def slice(self, qset, start, stop):
        start, stop = max(start, 0), max(stop, 0)
        return list(qset[start:stop])

    def __len__(self):
        return self.length
