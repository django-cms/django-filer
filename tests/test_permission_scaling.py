from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.db.models.sql.compiler import SQLCompiler
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from filer import settings as filer_settings
from filer.cache import clear_folder_permission_cache
from filer.models import Folder, FolderPermission
from tests.helpers import SettingsOverride


PERMISSION_NAMES = ('read', 'edit', 'add_children')
MAX_COLD_QUERIES = 2


class PermissionScalingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username='reader')
        clear_folder_permission_cache(self.user)
        self.addCleanup(clear_folder_permission_cache, self.user)
        permissions = patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
        permissions.start()
        self.addCleanup(permissions.stop)

        self.root = Folder.objects.create(name='root')
        self.child = Folder.objects.create(name='child', parent=self.root)
        self.leaf = Folder.objects.create(name='leaf', parent=self.child)
        self.sibling = Folder.objects.create(name='sibling', parent=self.root)
        self.other = Folder.objects.create(name='other')
        self.other_leaf = Folder.objects.create(name='other leaf', parent=self.other)

    def assert_cold_ids(self, expected, permission='read', max_queries=MAX_COLD_QUERIES):
        # Each measurement starts cold, independently of earlier permission checks.
        clear_folder_permission_cache(self.user)
        get_ids = getattr(FolderPermission.objects, f'get_{permission}_id_list')
        with CaptureQueriesContext(connection) as queries:
            actual = get_ids(self.user)

        self.assertEqual(actual, expected)
        self.assertLessEqual(len(queries), max_queries)

    @contextmanager
    def _folder_rows(self):
        rows = []
        results_iter = SQLCompiler.results_iter

        def record_rows(compiler, *args, **kwargs):
            for row in results_iter(compiler, *args, **kwargs):
                if compiler.query.model is Folder:
                    rows.append(row)
                yield row

        # Count actual database rows, including values_list queries.
        with patch.object(SQLCompiler, 'results_iter', record_rows):
            yield rows

    def test_subtree_rows_are_bounded(self):
        FolderPermission.objects.create(
            user=self.user, folder=self.child, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW,
        )
        for size in (16, 128):
            with self.subTest(unrelated_folders=size):
                Folder.objects.bulk_create([
                    Folder(name=f'unrelated {size}-{index}', parent=self.other)
                    for index in range(size)
                ])
                clear_folder_permission_cache(self.user)
                with self._folder_rows() as rows:
                    actual = FolderPermission.objects.get_read_id_list(self.user)

                self.assertEqual(actual, {self.child.pk, self.leaf.pk})
                self.assertLessEqual(len(rows), len(actual))
                self.assertTrue(all(row[0] in actual for row in rows))

    def test_global_allow_loads_ids(self):
        FolderPermission.objects.create(
            user=self.user, type=FolderPermission.ALL,
            can_read=FolderPermission.ALLOW,
        )
        expected = set(Folder.objects.values_list('pk', flat=True))
        with self._folder_rows() as rows:
            self.assert_cold_ids(expected)

        self.assertEqual(len(rows), len(expected))
        self.assertTrue(all(len(row) == 1 for row in rows))

    def test_global_deny_skips_folders(self):
        for grant in (FolderPermission.ALLOW, FolderPermission.DENY):
            FolderPermission.objects.create(
                user=self.user, type=FolderPermission.ALL, can_read=grant,
            )
        with self.assertNumQueries(1):
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), set())

    def test_permission_scopes(self):
        scopes = (
            (FolderPermission.THIS, self.child, {self.child.pk}, 1),
            (FolderPermission.CHILDREN, self.child, {self.child.pk, self.leaf.pk}, 3),
            (FolderPermission.ALL, None, {
                self.root.pk, self.child.pk, self.leaf.pk,
                self.sibling.pk, self.other.pk, self.other_leaf.pk,
            }, 2),
        )
        for scope, folder, expected, max_queries in scopes:
            for permission in PERMISSION_NAMES:
                with self.subTest(scope=scope, permission=permission):
                    FolderPermission.objects.all().delete()
                    FolderPermission.objects.create(
                        user=self.user, folder=folder, type=scope,
                        **{f'can_{permission}': FolderPermission.ALLOW},
                    )
                    self.assert_cold_ids(expected, permission, max_queries)

    def test_deny_overrides_allow(self):
        FolderPermission.objects.create(
            user=self.user, type=FolderPermission.ALL,
            can_read=FolderPermission.ALLOW,
        )
        FolderPermission.objects.create(
            user=self.user, folder=self.child, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.DENY,
        )
        FolderPermission.objects.create(
            user=self.user, folder=self.leaf, type=FolderPermission.THIS,
            can_read=FolderPermission.ALLOW,
        )
        self.assert_cold_ids({
            self.root.pk, self.sibling.pk, self.other.pk, self.other_leaf.pk,
        }, max_queries=4)

    def test_this_deny_stays_local(self):
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW,
        )
        FolderPermission.objects.create(
            user=self.user, folder=self.child, type=FolderPermission.THIS,
            can_read=FolderPermission.DENY,
        )
        self.assert_cold_ids({self.root.pk, self.leaf.pk, self.sibling.pk}, max_queries=4)

    def test_global_deny(self):
        FolderPermission.objects.create(
            user=self.user, type=FolderPermission.ALL,
            can_read=FolderPermission.DENY,
        )
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW,
        )
        self.assert_cold_ids(set())

    def test_permission_recipients(self):
        member_group = Group.objects.create(name='members')
        other_group = Group.objects.create(name='others')
        other_user = get_user_model().objects.create(username='other reader')
        self.user.groups.add(member_group)
        for recipient, folder in (
            ({'user': self.user}, self.root),
            ({'group': member_group}, self.child),
            ({'everybody': True}, self.sibling),
            ({'user': other_user}, self.other),
            ({'group': other_group}, self.other_leaf),
        ):
            FolderPermission.objects.create(
                **recipient, folder=folder, type=FolderPermission.THIS,
                can_read=FolderPermission.ALLOW,
            )

        # An unrelated user's denial must not cancel a matching grant.
        FolderPermission.objects.create(
            user=other_user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.DENY,
        )
        self.assert_cold_ids({self.root.pk, self.child.pk, self.sibling.pk})

    def test_attributes_are_separate(self):
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW, can_edit=FolderPermission.DENY,
        )
        FolderPermission.objects.create(
            user=self.user, folder=self.child, type=FolderPermission.THIS,
            can_read=None, can_edit=FolderPermission.ALLOW,
            can_add_children=FolderPermission.ALLOW,
        )
        expectations = {
            'read': ({self.root.pk, self.child.pk, self.leaf.pk, self.sibling.pk}, 4),
            'edit': (set(), 4),
            'add_children': ({self.child.pk}, 1),
        }
        for permission, (expected, max_queries) in expectations.items():
            with self.subTest(permission=permission):
                self.assert_cold_ids(expected, permission, max_queries)

    def test_no_applicable_grants(self):
        self.assert_cold_ids(set())
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=None,
        )
        other_user = get_user_model().objects.create(username='other reader')
        FolderPermission.objects.create(
            user=other_user, type=FolderPermission.ALL,
            can_read=FolderPermission.ALLOW,
        )
        self.assert_cold_ids(set())

    def test_permission_bypasses(self):
        for permission in PERMISSION_NAMES:
            get_ids = getattr(FolderPermission.objects, f'get_{permission}_id_list')
            with self.subTest(permission=permission, bypass='disabled'):
                with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=False):
                    with self.assertNumQueries(0):
                        self.assertEqual(get_ids(self.user), 'All')

            with self.subTest(permission=permission, bypass='superuser'):
                self.user.is_superuser = True
                with self.assertNumQueries(0):
                    self.assertEqual(get_ids(self.user), 'All')
                self.user.is_superuser = False

    def test_deep_grants_are_bounded(self):
        for depth in (4, 16):
            with self.subTest(depth=depth):
                FolderPermission.objects.all().delete()
                parent = None
                expected = set()
                for index in range(depth):
                    parent = Folder.objects.create(name=f'depth {depth}-{index}', parent=parent)
                    expected.add(parent.pk)
                    FolderPermission.objects.create(
                        user=self.user, folder=parent, type=FolderPermission.CHILDREN,
                        can_read=FolderPermission.ALLOW,
                    )
                self.assert_cold_ids(expected)

    def test_wide_grants_are_bounded(self):
        expected = {self.root.pk, self.child.pk, self.leaf.pk, self.sibling.pk}
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW,
        )
        for index in range(16):
            folder = Folder.objects.create(name=f'wide {index}', parent=self.root)
            expected.add(folder.pk)
            FolderPermission.objects.create(
                user=self.user, folder=folder, type=FolderPermission.CHILDREN,
                can_read=FolderPermission.ALLOW,
            )
        # Width does not add queries below the database parameter limit.
        self.assert_cold_ids(expected, max_queries=4)

    def test_descendants_are_batched(self):
        roots = Folder.objects.bulk_create([Folder(name=f'root {index}') for index in range(5)])
        children = Folder.objects.bulk_create([Folder(name='child', parent=root) for root in roots])
        FolderPermission.objects.bulk_create([
            FolderPermission(
                user=self.user, folder=root, type=FolderPermission.CHILDREN,
                can_read=FolderPermission.ALLOW,
            )
            for root in roots
        ])
        expected = {folder.pk for folder in roots + children}
        # Two levels of five parents require three batches each, plus grants.
        # Patch the class because Django 6 exposes a read-only property.
        with patch.object(type(connection.features), 'max_query_params', 2), self.assertNumQueries(7):
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), expected)

    def test_cyclic_subtree_terminates(self):
        Folder.objects.filter(pk=self.root.pk).update(parent=self.leaf)
        FolderPermission.objects.create(
            user=self.user, folder=self.root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW,
        )
        self.assert_cold_ids(
            {self.root.pk, self.child.pk, self.leaf.pk, self.sibling.pk}, max_queries=4,
        )
