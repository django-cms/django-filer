Dump payload
============

**django-filer** stores the meta-data of each file in the database, while the files payload is
stored on disk. This is fine, since large binary data shall only exceptionally be stored in a
relational database. The consequence however is, that when invoking ``manage dumpdata`` only the
meta-data is dumped, while the payload remains on disk. During backups this can be a problem, since
the payload must be handled though other means, for example ``tar`` or ``zip``.

**django-filer** has a feature, which allows to dump the files payload together with their
meta-data. This is achieved by converting the payload into a BASE64 string which in consequence is
added to the dumped data. The advantage is, that the dumped file can be imported without having to
fiddle with zip, tar and file pathes.

In order to activate this feature, add::

	FILER_DUMP_PAYLOAD = True

to the projects ``settings.py`` file.

If the content has been dumped together with the payload, the files are restored when using
``manage.py loaddata``. If the payload is missing, only the meta-data is restored. This is the
default behavior.

Other benefits
--------------
 * It simplifies backups and migrations, since the data entered into the content management system
   is dumped into one single file.
 * If the directory ``filer_public`` is missing, **django-filer** rebuilds the file tree from
   scratch. This can be used to get rid of zombie files, such as generated thumbnails which are not
   used any more.
 * When dumping the filers content, you get warned about missing files.
 * When dumping the filers content, the checksum of the dumped file is compared to that generated
   during the primary file upload. In case the checksum diverges, you will be warned.
 * Only the uploaded file is dumped. Thumbnails derived from the uploaded files will be regenerated
   by **django-filer** when required. This saves some space during backups.

Reloading a dump back to the database
.....................................
If you dumped a whole database, and not only a partial application, then you may encounter problems
with primary key conflicts during an import::

	Could not load contenttypes.ContentType(...)

To circumvent this, first you must flush the whole database's content. Using the management command
``./manage.py flush``, does not truncate all tables: This is because the content in the table
``django_content_type`` is reset to the state after initializing the database using
``./manage.py syncdb`` and thus is not empty.

Therefore, to flush the database's content, use::

	./manage.py sqlflush | ./manage.py dbshell

Now the dump can be loaded using::

	./manage.py loaddata <dumpfile>
