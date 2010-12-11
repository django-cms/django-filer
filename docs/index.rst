.. django-filer documentation master file, created by
   sphinx-quickstart on Tue Nov 16 22:05:55 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to django-filer's documentation!
========================================

``django-filer`` is a file management application for django. It handles uploading
and organizing files and images in contrib.admin.

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

Contributing
------------

The code is hosted on github at http://github.com/stefanfoulis/django-filer/ 
and is fully open source. We hope you choose to help us on the project! More 
about `how to contribute <https://github.com/stefanfoulis/django-filer/wiki/Contributing>`_ 
can be found on `the wiki <https://github.com/stefanfoulis/django-filer/wiki/>`_.

Contents
========

.. toctree::
   :maxdepth: 2

   getting_started
   running_tests
