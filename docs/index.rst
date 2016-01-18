.. django-filer documentation master file

Welcome to django-filer's documentation!
========================================

.. only:: develop

   .. warning::
      This documentation refers to the development version of ``django-filer``.

      As this version has not been released yet, any part of the API maybe subject
      to modifications without notice, and this documentation may be outdated and
      not in sync with the code.


``django-filer`` is a file management application for django. It handles uploading
and organizing files and images in contrib.admin.

.. note:: upgrading from 0.8.7? Checkout :ref:`upgrading`.

+-----------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/filer_1.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/filer_2.png |
+-----------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------+

Filer detail view:

+----------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/detail_image.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/detail_file.png |
+----------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+

Filer picker widget:

+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_1.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_2.png |
+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_3.png |                                                                                                                       |
+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+

Custom model fields are provided for use in 3rd party apps as a replacement for 
the default ``FileField`` from django. Behind the scenes a ``ForeignKey`` to the 
File model is used.
       
Getting help
------------

* google group: http://groups.google.com/group/django-filer
* IRC: #django-filer on freenode.net


Contributing
------------

The code is hosted on github at http://github.com/divio/django-filer/
and is fully open source. We hope you choose to help us on the project! More 
information on how to contribute can be found in `contributing`_.


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
   development
   extending_filer
   running_tests
   dump_payload


.. _`contributing`: development/#contributing
