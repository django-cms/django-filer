.. _upgrading:

Upgrading
=========

Usually upgrade procedure is straightforward: update the package and run migrations. Some versions
require special attention from the developer and here we provide upgrade instructions for such cases.


from 0.9.1 to 0.9.2
-------------------

From 0.9.2 ``File.name`` field is ``null=False``.

.. warning::
    Data migration in 0.9.2 changes existing null values to empty string.


from 0.8.7 to 0.9
-----------------

0.9 introduces real separation of private and public files through multiple storage backends. Public files are placed
inside ``MEDIA_ROOT``, using Djangos default file storage. Private files are now placed in their own location.
Unfortunatly the default settings in django-filer 0.8.x made all new uploads "private", but still placed them inside
``MEDIA_ROOT`` in a subfolder called ``filer_private``. In most cases these files are actually meant to be public,
so they should be moved.

.. note:: **Quick and Dirty**: set ``FILER_0_8_COMPATIBILITY_MODE=True``. It will pick up the old style settings and
          configure storage backends the way they were in 0.8. This setting is only meant to easy migration and is
          not intended to be used long-term.


Manually (SQL)
..............

*faster for many large files*

Fire up the sql-console and change ``is_public`` to ``True`` on all files in the
``filer_file`` table (``UPDATE filer_file SET is_public=1 WHERE is_public=0;``). The files will still be in
``MEDIA_ROOT/filer_private/``, but serving them should already work. Then you can move the files
into ``filer_private`` in the filesystem and update the corresponding paths in the database.


Automatic (Django)
..................

Have filer move all files between storages. This might take a while, since django will read
each file into memory and write it to the new location. Especially if you are using an external storage backend
such as *Amazon S3*, this might not be an option.
Set ``FILER_0_8_COMPATIBILITY_MODE=True`` and make sure you can access public and private files. Then run this
snippet in the django shell::

    from filer.models import File
    import sys
    for f in File.objects.filter(is_public=False):
        sys.stdout.write(u'moving %s to public storage... ' % f.id)
        f.is_public = True
        f.save()
        sys.stdout.write(u'done\n')

After running the script you can delete the ``FILER_0_8_COMPATIBILITY_MODE`` setting. If you want to use secure
downloads see :ref:`secure_downloads`.


from pre-0.9a3 develop to 0.9
-----------------------------

In develop pre-0.9a3 file path was written in the database as relative path inside `filer` directory; since 0.9a3
this is no longer the case so file must be migrate to the new paths.
Same disclaimer as 0.8x migration applies: SQL migration is much faster for large datasets.


Manually (SQL)
..............

Use whatever tool to access you database console and insert the correct directory name at the start of the `file` field.
Example::

    UPDATE filer_file SET file= 'filer_public/' || file WHERE file LIKE '20%' AND is_public=True;
    UPDATE filer_file SET file= 'filer_private/' || file WHERE file LIKE '20%' AND is_public=False;

Then you will have to move by hand the files from the `MEDIA_ROOT/filer` directory to the new public and private storage
directories


Automatic (Django)
..................
Make sure the console user can access/write public and private files.
Please note that the `"filer/"` string below should be modified if your files are not saved in `MEDIA_ROOT/filer`
Then run this snippet in the django shell::

    from filer.models import File
    import sys
    for f in File.objects.filter(is_public=True):
        sys.stdout.write(u'moving %s to public storage... ' % f.id)
        f.is_public = False
        f.file.name = "filer/%s" % f.file.name
        f.save()
        f.is_public = True
        f.save()
        sys.stdout.write(u'done\n')
    for f in File.objects.filter(is_public=False):
        sys.stdout.write(u'moving %s to private storage... ' % f.id)
        f.is_public = True
        f.file.name = "filer/%s" % f.file.name
        f.save()
        f.is_public = False
        f.save()
        sys.stdout.write(u'done\n')

Double access modification is needed to enabled automatic file move.