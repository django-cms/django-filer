from filer.models.foldermodels import Folder
from django.db.models import Count


class TreeCorruption(Exception):
    pass


class TreeChecker(object):

    ordering = ['tree_id', 'lft', 'rght']

    def __init__(self):
        self.full_rebuild = False
        self.corrupted_folders = {}
        self.corruption_check_done = False

    def find_corruptions(self):
        self.check_corruptions()
        if (self.full_rebuild or self.corrupted_folders):
            raise TreeCorruption()

    def _build_diff_msg(self, expected, actual):
        attr_idx = {'lft':0, 'rght':1, 'level':2, 'tree_id':3}
        expected, actual = list(expected), list(actual)
        diff = []
        for attr, idx in attr_idx.items():
            if expected[idx] != actual[idx]:
                diff.append('wrong %s value: expected %s, actual %s' % (
                    attr, expected[idx], actual[idx]))
        return '; '.join(diff)

    def _get_parents_names(self, folder, names):
        names.insert(0, folder.name)
        if folder.parent:
            self._get_parents_names(folder.parent, names)

    def _get_folder_path(self, pk):
        folder = Folder.objects.get(pk=pk)
        names = []
        self._get_parents_names(folder, names)
        return '/'.join(names)

    def get_corrupted_root_nodes(self):
        if not self.corruption_check_done:
            self.check_corruptions()
        corrupted_trees = Folder.objects.filter(
            pk__in=self.corrupted_folders.keys()).\
            values_list('tree_id', flat=True).distinct()
        return Folder.objects.filter(
            parent__isnull=True, tree_id__in=corrupted_trees)

    def check_tree(self, pk, lft, tree_id, level=0):
        """
            * checks if a certain folder tree is corrupted or not.
            * uses the same logic as django-mptt's rebuild tree
        """
        rght = lft + 1
        child_ids = Folder.objects.filter(parent__pk=pk).\
            order_by(*self.ordering).values_list('pk', flat=True)

        for child_id in child_ids:
            rght = self.check_tree(child_id, rght, tree_id, level + 1)

        folder = Folder.objects.get(pk=pk)
        expected = (lft, rght, level, tree_id)
        actual = (folder.lft, folder.rght, folder.level, folder.tree_id)
        if expected != actual:
            self.corrupted_folders.setdefault(
                pk, self._build_diff_msg(expected, actual))
        return rght + 1

    def check_corruptions(self):
        """
            * checks folder tree corruptions
            * based on django-mptt's rebuild method
            * checks if there are multiple root folders with the
        same tree id(fixing this will require a full rebuild)
        """
        tree_duplicates = Folder.objects.filter(parent=None).\
            values_list('tree_id').\
            annotate(count=Count('id')).filter(count__gt=1)
        if len(tree_duplicates) > 0:
            self.full_rebuild = True
            self.corruption_check_done = True
            return

        pks = Folder.objects.filter(parent=None).\
            order_by(*self.ordering).values_list('pk', flat=True)
        idx = 0
        for pk in pks:
            idx += 1
            self.check_tree(pk, 1, Folder.objects.get(pk=pk).tree_id)

        self.corruption_check_done = True

    def rebuild(self):
        if not self.corruption_check_done:
            self.check_corruptions()

        if self.full_rebuild:
            Folder._tree_manager.rebuild()
        elif self.corrupted_folders:
            for folder in self.get_corrupted_root_nodes():
                # since we use an older version of djang-mptt and method
                #   partial_rebuild does not exist ...
                Folder._tree_manager._rebuild_helper(
                    folder.pk, 1, folder.tree_id)
