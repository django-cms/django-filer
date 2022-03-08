Management commands
===================

Generating thumbnails
---------------------

**django-filer** generates preview thumbnails of the images which are displayed in the admin.
Usually these are generated on the fly when images are uploaded. If however you have imported the 
images programmatically you may want to generate the thumbnails eagerly utilizing a management 
command.

To generate them, use::

    ./manage.py generate_thumbnails


Filesystem Checks
-----------------

**django-filer** offers a few commands to check the integrity of the database against the files
stored on disk. By invoking::

    ./manage.py filer_check --missing

all files which are referenced by the database, but missing on disk are reported.

Invoking::

    ./manage.py filer_check --delete-missing

deletes those file references from the database.

Invoking::

    ./manage.py filer_check --orphans

lists all files found on disk belonging to the configured storage engine, but which
are not referenced by the database.

Invoking::

    ./manage.py filer_check --delete-orphans

deletes those orphaned files from disk.
