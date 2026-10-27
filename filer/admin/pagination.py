from itertools import chain
from operator import index

from django.utils.functional import cached_property


class FolderItems:
    """A folders-first sequence that fetches only the requested page."""

    ordered = True

    def __init__(self, folders, files):
        self._folders = folders
        self._files = files

    @cached_property
    def folder_count(self):
        return self._folders.count()

    @cached_property
    def file_count(self):
        return self._files.count()

    def __len__(self):
        return self.folder_count + self.file_count

    def __iter__(self):
        return chain(self._folders, self._files)

    def __getitem__(self, key):
        if not isinstance(key, slice):
            position = index(key)
            if position < 0:
                position += len(self)
            if not 0 <= position < len(self):
                raise IndexError('Folder item index out of range')
            if position < self.folder_count:
                return self._folders[position]
            return self._files[position - self.folder_count]

        start, stop, step = key.indices(len(self))
        if step != 1:
            # General slicing fallback; paginator pages use unit steps.
            return list(self)[key]
        if start >= stop:
            return []

        # Split pages crossing the boundary without evaluating either full queryset.
        folders = self._folders[start:min(stop, self.folder_count)] if start < self.folder_count else ()
        files = self._files[max(0, start - self.folder_count):stop - self.folder_count] if stop > self.folder_count else ()
        return list(chain(folders, files))
