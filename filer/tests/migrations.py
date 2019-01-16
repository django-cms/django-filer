# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from unittest import skipIf

import django
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO


class MigrationsTests(TestCase):
    @skipIf(django.get_version() < '1.7',
            'migrations not supported in django < 1.7')
    def test_makemigrations(self):
        out = StringIO()
        call_command('makemigrations', dry_run=True, no_input=True, stdout=out)
        output = out.getvalue()
        self.assertEqual(output, 'No changes detected\n')
