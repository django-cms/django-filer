# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os, shutil

from django.core.management import call_command
from django.utils.module_loading import import_string
from django.utils.six import StringIO

from filer.models.filemodels import File
from filer.settings import DEFAULT_FILER_STORAGES

from .server_backends import BaseServerBackendTestCase


class FilerCheckTestCase(BaseServerBackendTestCase):
    def test_delete_missing(self):
        out = StringIO()
        self.assertTrue(os.path.exists(self.filer_file.file.path))
        file_pk = self.filer_file.id
        call_command('filer_check', stdout=out, missing=True)
        self.assertEqual('', out.getvalue())

        os.remove(self.filer_file.file.path)
        call_command('filer_check', stdout=out, missing=True)
        self.assertEqual("None/testimage.jpg\n", out.getvalue())
        self.assertIsInstance(File.objects.get(id=file_pk), File)

        call_command('filer_check', delete_missing=True, interactive=False, verbosity=0)
        with self.assertRaises(File.DoesNotExist):
            File.objects.get(id=file_pk)

    def test_delete_orphans(self):
        out = StringIO()
        self.assertTrue(os.path.exists(self.filer_file.file.path))
        call_command('filer_check', stdout=out, orphans=True)
        self.assertEqual('', out.getvalue())

        # add an orphan file to our storage
        storage = import_string(DEFAULT_FILER_STORAGES['public']['main']['ENGINE'])()
        filer_public = os.path.join(storage.base_location, DEFAULT_FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX'])
        if os.path.isdir(filer_public):
            shutil.rmtree(filer_public)
        os.mkdir(filer_public)
        orphan_file = os.path.join(filer_public, 'hello.txt')
        with open(orphan_file, 'w') as fh:
            fh.write("I don't belong here!")
        call_command('filer_check', stdout=out, orphans=True)
        self.assertEqual("filer_public/hello.txt\n", out.getvalue())
        self.assertTrue(os.path.exists(orphan_file))

        call_command('filer_check', delete_orphans=True, interactive=False, verbosity=0)
        self.assertFalse(os.path.exists(orphan_file))
