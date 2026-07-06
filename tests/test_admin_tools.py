"""Tests for filer.admin.tools."""

from django.test import TestCase, RequestFactory

from filer.admin.tools import (
    AdminContext,
    admin_url_params,
    admin_url_params_encoded,
    check_files_edit_permissions,
    check_files_read_permissions,
    check_folder_edit_permissions,
    check_folder_read_permissions,
    popup_pick_type,
    popup_status,
    userperms_for_request,
)


class CheckPermissionTests(TestCase):
    """Tests for permission check functions."""

    def test_check_files_edit_permissions_passes(self):
        mock_file = type('obj', (), {'has_edit_permission': lambda self, r: True})()
        check_files_edit_permissions(None, [mock_file])  # should not raise

    def test_check_files_edit_permissions_fails(self):
        from django.core.exceptions import PermissionDenied
        mock_file = type('obj', (), {'has_edit_permission': lambda self, r: False})()
        with self.assertRaises(PermissionDenied):
            check_files_edit_permissions(None, [mock_file])

    def test_check_files_read_permissions_passes(self):
        mock_file = type('obj', (), {'has_read_permission': lambda self, r: True})()
        check_files_read_permissions(None, [mock_file])

    def test_check_files_read_permissions_fails(self):
        from django.core.exceptions import PermissionDenied
        mock_file = type('obj', (), {'has_read_permission': lambda self, r: False})()
        with self.assertRaises(PermissionDenied):
            check_files_read_permissions(None, [mock_file])

    def test_check_folder_edit_permissions_passes(self):
        mock_folder = type('obj', (), {
            'has_edit_permission': lambda self, r: True,
            'files': [],
            'children': type('obj', (), {'all': lambda self: []})(),
        })()
        check_folder_edit_permissions(None, [mock_folder])

    def test_check_folder_read_permissions_passes(self):
        mock_folder = type('obj', (), {
            'has_read_permission': lambda self, r: True,
            'files': [],
            'children': type('obj', (), {'all': lambda self: []})(),
        })()
        check_folder_read_permissions(None, [mock_folder])


class UserPermsForRequestTests(TestCase):
    """Tests for userperms_for_request."""

    def test_userperms(self):
        mock_item = type('obj', (), {
            'has_read_permission': lambda self, r: True,
            'has_edit_permission': lambda self, r: True,
            'has_add_children_permission': lambda self, r: False,
        })()
        result = userperms_for_request(mock_item, None)
        self.assertEqual(set(result), {'read', 'edit'})


class PopupTests(TestCase):
    """Tests for popup_status and popup_pick_type."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_popup_status_with_popup_var(self):
        request = self.factory.get('/?pop=1')
        self.assertTrue(popup_status(request))

    def test_popup_status_with_is_popup_var(self):
        request = self.factory.get('/?_popup=1')
        self.assertTrue(popup_status(request))

    def test_popup_status_without(self):
        request = self.factory.get('/')
        self.assertFalse(popup_status(request))

    def test_popup_pick_type_valid(self):
        request = self.factory.get('/?_pick=file')
        self.assertEqual(popup_pick_type(request), 'file')

    def test_popup_pick_type_invalid(self):
        request = self.factory.get('/?_pick=malicious')
        self.assertIsNone(popup_pick_type(request))

    def test_popup_pick_type_folder(self):
        request = self.factory.get('/?_pick=folder')
        self.assertEqual(popup_pick_type(request), 'folder')


class AdminUrlParamsTests(TestCase):
    """Tests for admin_url_params and admin_url_params_encoded."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_no_params(self):
        request = self.factory.get('/')
        params = admin_url_params(request)
        self.assertEqual(params, {})

    def test_with_popup(self):
        request = self.factory.get('/?pop=1')
        params = admin_url_params(request)
        self.assertEqual(params, {'_popup': '1'})

    def test_with_pick(self):
        request = self.factory.get('/?_pick=file')
        params = admin_url_params(request)
        self.assertEqual(params, {'_pick': 'file'})

    def test_encoded_no_params(self):
        request = self.factory.get('/')
        result = admin_url_params_encoded(request)
        self.assertEqual(result, '')

    def test_encoded_with_params(self):
        request = self.factory.get('/?pop=1&_pick=file')
        result = admin_url_params_encoded(request)
        self.assertIn('_pick=file', result)
        self.assertIn('_popup=1', result)


class AdminContextTests(TestCase):
    """Tests for AdminContext."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_popup_key(self):
        request = self.factory.get('/?pop=1')
        ctx = AdminContext(request)
        self.assertTrue(ctx['popup'])

    def test_popup_key_false(self):
        request = self.factory.get('/')
        ctx = AdminContext(request)
        self.assertFalse(ctx['popup'])

    def test_pick_key(self):
        request = self.factory.get('/?_pick=file')
        ctx = AdminContext(request)
        self.assertEqual(ctx['pick'], 'file')

    def test_pick_file_via_dict_access(self):
        request = self.factory.get('/?_pick=file')
        ctx = AdminContext(request)
        self.assertTrue(ctx['pick_file'])
        self.assertFalse(ctx['pick_folder'])

    def test_pick_folder_via_dict_access(self):
        request = self.factory.get('/?_pick=folder')
        ctx = AdminContext(request)
        self.assertTrue(ctx['pick_folder'])
        self.assertFalse(ctx['pick_file'])

    def test_missing_attribute_raises(self):
        request = self.factory.get('/')
        ctx = AdminContext(request)
        with self.assertRaises(AttributeError):
            _ = ctx.nonexistent

    def test_popup_as_attribute(self):
        # Note: __getattr__ uses self.get('popup'), which won't trigger __missing__
        # So ctx.popup returns None via attribute access. Use ctx['popup'] instead.
        request = self.factory.get('/?pop=1')
        ctx = AdminContext(request)
        self.assertTrue(ctx['popup'])
        # Attribute access returns None since 'popup' key is not in the dict
        self.assertIsNone(ctx.popup)

    def test_missing_key_returns_false_popup(self):
        request = self.factory.get('/')
        ctx = AdminContext(request)
        self.assertFalse(ctx['popup'])

    def test_missing_key_returns_empty_pick(self):
        request = self.factory.get('/')
        ctx = AdminContext(request)
        self.assertEqual(ctx['pick'], '')
