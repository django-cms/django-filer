from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from filer.models import File, Folder
from tests.helpers import create_superuser


SMALL_WIDTH = 2
LARGE_WIDTH = 16


def build_tree(name, width):
    # A root with `width` children, each with one grandchild.
    root = Folder.objects.create(name=name)
    expected = set()
    for index in range(width):
        child = Folder.objects.create(name=f'{name} child {index}', parent=root)
        grandchild = Folder.objects.create(name=f'{name} grandchild {index}', parent=child)
        expected.update((child.pk, grandchild.pk))
    return root, expected


def count_queries(func):
    with CaptureQueriesContext(connection) as queries:
        result = func()
    return result, len(queries)


class DescendantIdsTests(TestCase):
    def test_descendant_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, expected = build_tree(f'tree {width}', width)
            descendants, counts[width] = count_queries(root.get_descendants_ids)

            self.assertIsInstance(descendants, list)
            self.assertEqual(len(descendants), len(expected))
            self.assertEqual(set(descendants), expected)

        # Width must not add queries; only depth may.
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def test_leaf_has_no_descendants(self):
        leaf = Folder.objects.create(name='leaf')
        self.assertEqual(leaf.get_descendants_ids(), [])


class LimitedSearchQueryTests(TestCase):
    def setUp(self):
        create_superuser()
        self.client.login(username='admin', password='secret')

    def search(self, folder):
        url = reverse('admin:filer-directory_listing', args=(folder.pk,))
        return self.client.get(url, {'q': 'match', 'limit_search_to_folder': 'on'})

    def test_limited_search_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, expected = build_tree(f'tree {width}', width)
            deepest = Folder.objects.filter(pk__in=expected, children__isnull=True).first()
            match = File.objects.create(original_filename=f'match {width}.txt', folder=deepest)
            File.objects.create(original_filename=f'match outside {width}.txt')
            self.search(root)

            response, counts[width] = count_queries(lambda: self.search(root))

            files = [item for item in response.context['paginated_items'].object_list if isinstance(item, File)]
            self.assertEqual([file_obj.pk for file_obj in files], [match.pk])

        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])
