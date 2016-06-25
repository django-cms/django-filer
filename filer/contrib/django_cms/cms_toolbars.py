# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER, ADMINISTRATION_BREAK
from cms.toolbar.items import Break, SideframeItem
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool

SHORTCUTS_BREAK = 'Shortcuts Break'


@toolbar_pool.register
class FilerToolbar(CMSToolbar):
    """
    Adds a Filer menu-item into django CMS's "ADMIN" (first) menu.
    """
    @staticmethod
    def get_insert_position(admin_menu, item_name):
        """
        Ensures that there is a SHORTCUTS_BREAK and returns a position for an
        alphabetical position against all items between this break, and the
        ADMINISTRATION_BREAK.
        """
        start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)
        if not start:
            end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
            admin_menu.add_break(SHORTCUTS_BREAK, position=end.index)
            start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)
        end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)

        items = admin_menu.get_items()[start.index + 1: end.index]
        for idx, item in enumerate(items):
            if force_text(item_name.lower()) < force_text(item.name.lower()):
                return idx + start.index + 1
        return end.index

    def populate(self):
        admin_menu = self.toolbar.get_or_create_menu(
            ADMIN_MENU_IDENTIFIER)
        admin_menu.add_sideframe_item(
            _('Media library'),
            url=reverse('admin:filer_folder_changelist'),
            position=self.get_insert_position(
                admin_menu, _('Media library'))
        )
