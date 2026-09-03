=============
Template tags
=============

.. code-block:: html+django

    {% load finder_tags %}


``download_url``
================

.. code-block:: html+django

    {% download_url file_id %}

Returns the URL of the original payload of the file with the given UUID, or the empty string
if no such file exists. The ambit is resolved from the file's folder.

.. todo::

   This is the only template tag django-finder ships. There is no tag for rendering a
   thumbnail or an image at a chosen size, which is the most obvious thing a template author
   would reach for — see :doc:`browser-api` for the HTTP endpoint that does it. Decide
   whether a ``{% thumbnail %}``-style tag belongs here, and document it or say why not.
