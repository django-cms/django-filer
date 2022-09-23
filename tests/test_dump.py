import json
import os
import tempfile
from io import StringIO

from django.conf import settings
from django.core.files import File as DjangoFile
from django.core.management import call_command
from django.test import TestCase

from filer import settings as filer_settings
from filer.models import Folder
from filer.models.filemodels import File
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import SettingsOverride, create_folder_structure, create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)


class DumpDataTests(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()
        pass

    def create_filer_image(self, folder=None):
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=file_obj, folder=folder)
        return image

    def create_filer_file(self, folder=None):
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        fileobj = File.objects.create(owner=self.superuser,
                                      original_filename=self.image_name,
                                      file=file_obj, folder=folder)
        return fileobj

    def test_dump_data_base(self):
        """
        Testing the case of dump full and empty dataset
        """
        fileobj = self.create_filer_file()
        jdata, jdata2 = StringIO(), StringIO()
        call_command("dumpdata", "filer", stdout=jdata)
        fileobj.delete()
        call_command("dumpdata", "filer", stdout=jdata2)
        data = json.loads(jdata.getvalue())
        data2 = json.loads(jdata2.getvalue())
        self.assertEqual(len(data), 1)
        self.assertEqual(len(data2), 0)

    def test_dump_load_data(self):
        """
        Testing the dump / load with no dump of file content data
        """
        # Initialize the test data
        create_folder_structure(1, 1)
        fileobj = self.create_filer_file(Folder.objects.all()[0])

        self.assertEqual(Image.objects.count(), 0)
        image = self.create_filer_image()
        image.save()
        image_size = image._width, image._height
        self.assertEqual(Image.objects.count(), 1)

        jdata = StringIO()

        # Dump the current data
        fobj = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        call_command("dumpdata", "filer", stdout=jdata, indent=3)

        # Delete database and filesystem data
        complete = os.path.join(fileobj.file.storage.location, fileobj.path)
        os.unlink(complete)
        fileobj.delete()

        # Dump data to json file
        fobj.write(jdata.getvalue().encode('utf-8'))
        fobj.seek(0)

        # Load data back
        call_command("loaddata", fobj.name, stdout=jdata)

        # Database data is restored
        self.assertEqual(Folder.objects.all().count(), 1)
        self.assertEqual(File.objects.all().count(), 2)
        self.assertEqual(File.objects.all()[0].original_filename, self.image_name)
        self.assertEqual(Image.objects.count(), 1)

        fileobj = File.objects.all()[0]
        image = Image.objects.all()[0]
        self.assertEqual(image._width, image_size[0])
        self.assertEqual(image._height, image_size[1])

        complete = os.path.join(fileobj.file.storage.location, fileobj.path)
        # Filesystem data is not
        self.assertFalse(os.path.exists(complete))

    def test_dump_load_data_content(self):
        """
        Testing the dump / load with full dump of file content data
        """
        with SettingsOverride(filer_settings, FILER_DUMP_PAYLOAD=True):
            # Initialize the test data
            create_folder_structure(1, 1)
            fileobj = self.create_filer_file(Folder.objects.all()[0])
            jdata = StringIO()

            # Dump the current data
            fobj = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
            call_command("dumpdata", "filer", stdout=jdata, indent=3)

            # Delete database and filesystem data and
            complete = os.path.join(fileobj.file.storage.location, fileobj.path)
            os.unlink(complete)
            fileobj.delete()

            # Dump data to json file
            fobj.write(jdata.getvalue().encode('utf-8'))
            fobj.seek(0)

            # Load data back
            call_command("loaddata", fobj.name, stdout=jdata)

            # Database data is restored
            self.assertEqual(Folder.objects.all().count(), 1)
            self.assertEqual(File.objects.all().count(), 1)
            self.assertEqual(File.objects.all()[0].original_filename, self.image_name)

            fileobj = File.objects.all()[0]
            complete = os.path.join(fileobj.file.storage.location, fileobj.path)
            # Filesystem data too!
            self.assertTrue(os.path.exists(complete))
