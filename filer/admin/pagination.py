from contextlib import suppress
from itertools import chain
from operator import index

from django.core.paginator import Paginator
from django.db.models import Count, Window
from django.utils.functional import cached_property


class FolderItems:
    """
    A folders-first sequence that fetches only the requested page.

    Folders and files are both sliced in the database. :meth:`load` reads each
    total from a window annotation on its page query, so a page usually needs
    no separate count.
    """

    ordered = True

    def __init__(self, folders, files):
        self._folders = folders
        self._files = files
        self._page = None

    @cached_property
    def folder_count(self):
        # Only queried if no page load could determine the total.
        return self._folders.count()

    @cached_property
    def file_count(self):
        # Only queried if no page load could determine the total.
        return self._files.count()

    def _counted_slice(self, queryset, start, stop, count_attr):
        """Slice ``queryset`` and set ``count_attr`` from the same query."""
        items = list(queryset.annotate(_filer_total=Window(Count('pk')))[start:stop])
        if items:
            total = getattr(items[0], '_filer_total', None)
            if total is not None:
                setattr(self, count_attr, total)
        elif start == 0:
            setattr(self, count_attr, 0)
        # Otherwise the slice lies past the last item; count lazily.
        return items

    def load(self, start, stop):
        """Fetch ``self[start:stop]``, taking the totals from the page queries."""
        if start == 0:
            folders = self._counted_slice(self._folders, start, stop, 'folder_count')
        elif start < self.folder_count:
            # Past page one the folder count is needed to place the page, and
            # an empty counted slice would not yield it. Pages after the first
            # usually hold files only, so count first.
            folders = list(self._folders[start:stop])
        else:
            folders = []
        files = []
        file_stop = stop - self.folder_count
        if file_stop > 0:
            files = self._counted_slice(self._files, max(0, start - self.folder_count), file_stop, 'file_count')
        self._page = (start, stop, folders + files)

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
            return list(self)[key]
        if start >= stop:
            return []
        if self._page:
            page_start, page_stop, page_items = self._page
            if page_start <= start and stop <= page_stop:
                return page_items[start - page_start:stop - page_start]

        # Split pages crossing the boundary without evaluating either full queryset.
        folders = self._folders[start:min(stop, self.folder_count)] if start < self.folder_count else ()
        files = self._files[max(0, start - self.folder_count):stop - self.folder_count] if stop > self.folder_count else ()
        return list(chain(folders, files))


class FolderPaginator(Paginator):
    """Loads the requested page before the total is needed, so counting is free."""

    def validate_number(self, number):
        # Page.next_page_number() and previous_page_number() validate too;
        # only the first lookup should load a page.
        if 'count' not in self.__dict__:
            with suppress(TypeError, ValueError):
                bottom = (int(number) - 1) * self.per_page
                if bottom >= 0:
                    self.object_list.load(bottom, bottom + self.per_page + self.orphans)
        return super().validate_number(number)
