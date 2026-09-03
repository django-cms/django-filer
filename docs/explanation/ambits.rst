======
Ambits
======

An ambit is a self-contained folder tree. It owns one root folder, one trash folder per user,
its own vocabulary of tags, and its own pair of storage backends.

Ambits are what make django-finder usable in a multi-tenant setting, which the single global
folder tree of django-filer could not do. Several ambits can coexist in one installation, and
each can be restricted to a ``django.contrib.sites`` site, to a particular admin site, or to
neither. All ambits a user may see appear in the admin's left sidebar, and the ambit's slug is
part of the URL of every folder inside it.

Because storages are configured per ambit rather than globally, one library can live on the
local filesystem while another lives in an S3 bucket, with different retention, different
access rules and different URLs — without either knowing about the other.


Why they are created from the command line
==========================================

An ambit is infrastructure: it names storage backends that must already exist in the
``STORAGES`` setting, and creating one creates a root folder that everything else hangs off.
Making that an admin form would invite creating an ambit pointing at a storage that is not
configured. So ambits are created with ``manage.py finder add-ambit`` instead — see
:doc:`../how-to/manage-ambits`.

A consequence worth knowing: a fresh installation has no ambit at all, and the admin has
nothing to show until you create one.

.. todo::

   Explain the interaction between ambits and ``FINDER_DEFAULT_AMBIT``, and what happens when
   a ``FinderFileField`` names an ambit that does not exist.

.. todo::

   Describe what copying or moving a file between ambits does — it crosses a storage
   boundary, so the payload is copied rather than relinked.
