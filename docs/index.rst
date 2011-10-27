.. django-filer documentation master file

Welcome to django-filer's documentation!
========================================

``django-filer`` is a file management application for django. It handles uploading
and organizing files, images and videos in contrib.admin.

.. figure:: _static/directory_view_1_screenshot.png
   :scale: 50 %
   :alt: directory view screenshot

   Directory list view with clipboard. New uploads are added to the clipboard 
   and can then be filed into folders.

Custom model fields are provided for use in 3rd party apps as a replacement for 
the default ``FileField`` from django. Behind the scenes a ``ForeignKey`` to the 
File model is used.

.. figure:: _static/default_admin_file_widget.png
   :alt: admin widget screenshot

   Default admin widget for file fields

Getting help
------------

* google group: http://groups.google.com/group/django-filer
* IRC: #django-filer on freenode.net

.. _contributing:

Contributing
------------

The code is hosted on github at http://github.com/stefanfoulis/django-filer/ 
and is fully open source. We hope you choose to help us on the project! More 
about `how to contribute <https://github.com/stefanfoulis/django-filer/wiki/Contributing>`_ 
can be found on `the wiki <https://github.com/stefanfoulis/django-filer/wiki/>`_.

Contents
========

.. toctree::
   :maxdepth: 1

   getting_started
   installation
   usage
   permissions
   server
   settings
   running_tests
