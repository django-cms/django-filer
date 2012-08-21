.. _permissions:

Permissions
===========

.. WARNING:: File download permissions are an experimental feature. The api may change at any time.

By default files can be uploaded and managed by all staff members based on the
standard django model permissions.

Activating permission checking with the ``FILER_ENABLE_PERMISSIONS`` setting enables
fine grained permissions based on individual folders.
Permissions can be set in the "Folder permissions" section in Django admin.

.. NOTE:: These permissions only concern editing files and folders in Django admin. All the files are
          still world downloadable by anyone who guesses the url. For real permission checks on downloads
          see the :ref:`secure_downloads` section.

.. _Django: http://djangoproject.com