============
Contrib apps
============

Each contrib app registers one or more file models for a family of MIME types. Add the app to
``INSTALLED_APPS`` to enable it; see :doc:`../how-to/install-file-type-support` for the
dependencies each one needs.


``finder.contrib.archive``
==========================

``application/zip``, ``application/x-tar``, ``application/x-gzip``. Stores the archive and
shows an icon; no extraction.


``finder.contrib.audio``
========================

``audio/mpeg``, ``audio/ogg``, ``audio/wav``, ``audio/x-wav``, ``audio/opus``. Generates a
playable excerpt through ``get_sample_url`` using ffmpeg, starting at ``sample_start`` in the
file's metadata.


``finder.contrib.common``
=========================

PDF, spreadsheets, plain text, source code and word processor documents. Each is a separate
model with its own icon.


``finder.contrib.image``
========================

Not an app in its own right — it holds ``ImageFileModel``, the concrete model carrying
``width``, ``height``, the crop box (``crop_x``, ``crop_y``, ``crop_size``) and ``gravity``,
plus the cropping geometry shared by the backends below.

``finder.contrib.image.pil``
    ``image/avif``, ``image/gif``, ``image/jpeg``, ``image/png``, ``image/webp``. Uses
    Pillow. Re-orients by EXIF on upload and downscales anything wider than 3840 pixels.

``finder.contrib.image.svg``
    ``image/svg+xml``.


``finder.contrib.video``
========================

``video/mp4``. Generates a poster frame and a short clip with ffmpeg, from ``sample_start``
in the file's metadata.

.. todo::

   List the exact MIME types registered by each model in ``finder.contrib.common``, and
   confirm the video app's claim to handle only ``video/mp4`` — the old README advertised
   webm and ogv as well.
