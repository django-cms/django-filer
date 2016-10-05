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
