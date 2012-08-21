.. _upgrading:

Upgrading
=========


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
``filer_file`` table (``UPDATE filer_file SET is_public=0 WHERE is_public=1;``). The files will still be in
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
