=============================
Install file type support
=============================

django-finder distinguishes files by MIME type, and each family of types lives in its own
contrib app with its own dependencies. A minimal installation that only tells files and
folders apart needs nothing beyond Django.

Add the app to ``INSTALLED_APPS`` and install its dependencies:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - App
     - Handles
     - Needs
   * - ``finder.contrib.archive``
     - zip, tar, gzip
     - nothing
   * - ``finder.contrib.audio``
     - mpeg, ogg, wav, opus
     - ``ffmpeg-python`` and an ``ffmpeg`` binary
   * - ``finder.contrib.common``
     - PDF, spreadsheets, text, office documents
     - nothing
   * - ``finder.contrib.image.pil``
     - avif, gif, jpeg, png, webp
     - ``Pillow``
   * - ``finder.contrib.image.svg``
     - svg
     - see below
   * - ``finder.contrib.video``
     - mp4
     - ``ffmpeg-python`` and an ``ffmpeg`` binary

The corresponding extras are declared in ``pyproject.toml``:

.. code-block:: shell

    pip install -e '.[image,svg,audio,video]'

Anything whose MIME type matches no installed app falls back to
:class:`~finder.models.file.FileModel`, which stores the file and shows a generic icon.

.. todo::

   The SVG row is in flux. On the ``finder`` branch ``finder.contrib.image.svg`` needs
   ``reportlab`` and ``svglib``; the ``feat/simple-svg`` branch removes that requirement and
   handles SVG geometry without a renderer. The ``feat/validator-compat`` branch additionally
   makes ``py-svg-hush`` load-bearing, because SVG uploads are sanitized by default and the
   validator fails closed without it. Rewrite this row once both have landed.

.. todo::

   ``finder.contrib.common`` registers several models (PDF, spreadsheet, text, code, word
   processor). List the exact MIME types per model, from
   ``finder/contrib/common/models.py``.
