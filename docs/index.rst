.. django-filer documentation master file

Welcome to django-filer's documentation!
========================================

``django-filer`` is a file management application for django. It handles uploading
and organizing files and images in contrib.admin.


.. warning::
   This documentation refers to development version of ``django-filer``.
   
   As this version has not been released yet, any part of the API maybe subject
   to modifications without notice, and this documentation may be outdated and
   not in sync with the code.

   
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

   installation
   upgrading
   usage
   permissions
   secure_downloads
   settings
   extending_filer
   running_tests
