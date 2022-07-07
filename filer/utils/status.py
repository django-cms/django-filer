import gc
import requests
from collections import defaultdict

from django.contrib.sites.models import Site

from filer.models import File, Folder


def chunked_items(qs, size=100):
    pk = 0
    last_pk = qs.order_by('-pk')[0].pk
    queryset = qs.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:size]:
            pk = row.pk
            yield row
        gc.collect()


class FileStats(object):

    def __init__(self, total):
        self.private = defaultdict(list)
        self.private.setdefault('total' , 0)
        self.public = defaultdict(list)
        self.public.setdefault('total' , 0)

        self.current_item = None
        self.current_stats = None
        self.index = 0
        self.total = total

    def set_current(self, asset, public=True):
        self.current_item = asset
        self.current_stats = self.public if public else self.private
        self.current_stats['total'] += 1
        self.index += 1

    def mark_current(self, marker):
        self.current_stats[marker].append(self.current_item)

    def progress(self):
        return "Checked {current} of {total} files".format(
            current=self.index, total=self.total)

    def summary(self):
        data = {
            "total_checked": self.index,
            "total_initial": self.total,
            "total_private": self.private['total'],
            "total_public": self.public['total'],
        }
        for prefix in ('public', 'private'):
            data.update({
                "{prefix}_{marker}".format(prefix=prefix, marker=k): len(v)
                for k, v in list(getattr(self, prefix).items())
                if k != 'total'
            })
        return data

    def full_summary(self):
        data = self.summary()
        for prefix in ('public', 'private'):
            data.update({
                "{prefix}_{marker}".format(prefix=prefix, marker=k): v
                for k, v in list(getattr(self, prefix).items())
                if k != 'total'
            })
        return data

    def as_string(self, full=False):
        to_title = lambda x: x.capitalize().replace('_', ' ')
        join = lambda x: '\n\t' + '\n\t'.join(x)

        data = self.full_summary() if full else self.summary()
        return '\n'.join(sorted([
            "%s %s" % (to_title(k), join(v) if hasattr(v, '__iter__') else v)
            for k, v in list(data.items())]))


class FileChecker(object):

    def __init__(self, filer_file):
        self._file = filer_file
        self._logical_path = ''

    @property
    def storage(self):
        return self._file.file.storage

    @property
    def file_path(self):
        return self._file.file.name

    @property
    def logical_path(self):
        if not self._logical_path:
            self._logical_path = self._file.pretty_logical_path
        return self._logical_path

    def exists(self):
        return self.storage.exists(self.file_path)

    def path_logical(self):
        return self.file_path.endswith(self.logical_path)

    def accessible(self):
        try:
            response = requests.head(self._file.url)
        except requests.exceptions.RequestException as exc:
            return False
        return response.status_code == requests.codes.ok

    def as_string(self):
        return "%s: %s" % (self._file.pk, self.logical_path, )

    @classmethod
    def check_all(cls, log_progress=None):
        stats = FileStats(File.objects.count())
        log_progress = log_progress or (lambda x: None)

        for _file in chunked_items(File.objects.all()):
            asset = cls(_file)
            stats.set_current(asset.as_string(), _file.is_public)

            if not asset.path_logical():
                stats.mark_current('path_mismatch')
            if not asset.accessible():
                stats.mark_current('not_accessible')
            if not asset.exists():
                stats.mark_current('missing')
            log_progress(stats)

        return stats

    @classmethod
    def check_site(cls, site_id, log_progress=None):
        folders = Folder.objects.filter(site_id=site_id).values_list('pk', flat=True)
        files = File.objects.filter(folder_id__in=folders)

        stats = FileStats(files.count())
        log_progress = log_progress or (lambda x: None)

        for _file in chunked_items(files):
            asset = cls(_file)
            stats.set_current(f'{asset.as_string()} url:{_file.url}', _file.is_public)

            if not asset.path_logical():
                stats.mark_current('path_mismatch')
            if not asset.accessible():
                stats.mark_current('not_accessible')
            if not asset.exists():
                stats.mark_current('missing')
            log_progress(stats)

        return stats

