.. _provenance:

Image provenance
================

.. versionadded:: 3.7

Images increasingly come from generative AI tools, and regulations such as
`Article 50 of the EU AI Act
<https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689>`_
require transparency about AI-generated or AI-edited content. Two standards
mark such images inside the file:

* The **IPTC digital source type** (``Iptc4xmpExt:DigitalSourceType``), a
  property of the image's XMP metadata. Its value is a term of the `IPTC
  vocabulary <https://cv.iptc.org/newscodes/digitalsourcetype/>`_, e.g.
  ``trainedAlgorithmicMedia`` for an image created using generative AI.
* **C2PA Content Credentials**, a signed manifest store embedded in the file
  that records where the image comes from and how it was edited (see the
  `C2PA specification <https://spec.c2pa.org/>`_).

django-filer detects both when an image is uploaded, stores the result with the
image, and shows it in the admin. It never changes how an image looks.

.. note::

    django-filer provides information, not compliance. Whether and how you
    need to disclose AI-generated content depends on your role and use case;
    marking images on your site is up to your templates.


What is detected
----------------

Digital source type
    Read from the image's XMP packet. All common ways of writing the property
    are understood (as an attribute, as element text or as an ``rdf:resource``
    reference), whatever namespace prefix is used. A bare term such as
    ``trainedAlgorithmicMedia`` is expanded to the full IPTC URI
    ``http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia``.
    Values that are neither a term nor an ``http(s)`` URI, and values longer
    than 255 characters, are ignored.

    Supported formats: JPEG, PNG, GIF, WebP, and AVIF and HEIF if Pillow can
    open them (see :ref:`installation_and_configuration`). For PNG and GIF,
    django-filer reads the XMP packet from the file itself, wherever it is
    stored, without decoding the image.

Content Credentials
    django-filer detects whether a C2PA manifest store is embedded in the
    file. It does **not** read the manifest or validate its signature: the
    information tells that credentials were present, not that they are
    genuine. Use a tool such as `Verify
    <https://verify.contentauthenticity.org/>`_ to inspect them.

    Supported formats: JPEG (APP11 segments), PNG (``caBX`` chunk), GIF
    (``C2PA_GIF`` application extension), WebP (``C2PA`` chunk), and AVIF and
    HEIF (C2PA ``uuid`` box). Manifests stored outside the file ("remote
    manifests") are not detected.

Detection is best effort: a malformed or unreadable file never makes an upload
fail, it simply yields no provenance information. SVG images carry none.


When detection runs
-------------------

* Provenance is detected whenever an image's file is set: on upload through the
  admin (drag and drop, the upload button or the change form), when an image
  is created in code, and when the file of an existing image is replaced.
  Replacing the file replaces the provenance information, too.
* Detection sees the file **as uploaded**, before any upload validator such as
  ``strip_exif`` changes it (see :ref:`validation`).
* Images uploaded before django-filer detected provenance have none recorded.
  Scan them with the ``filer_detect_provenance`` management command (see
  :ref:`provenance_command` below).


How it is stored
----------------

Every image model (``BaseImage`` and therefore any custom
``FILER_IMAGE_MODEL``) has two read-only fields:

``digital_source_type``
    The full IPTC URI, or an empty string if the image states none.

``has_content_credentials``
    ``True`` if the uploaded file embedded a C2PA manifest store.

Two properties make them easier to use:

``is_ai_generated``
    ``True`` if the digital source type states that the image was created or
    edited using generative AI, which are the IPTC terms
    ``trainedAlgorithmicMedia`` ("Created using generative AI") and
    ``compositeWithTrainedAlgorithmicMedia`` ("Edited using generative AI").
    Other terms, e.g. ``algorithmicMedia`` for purely algorithmic images not
    based on training data, or ``compositeSynthetic``, do not count.

``digital_source_type_label``
    A human-readable, translatable label for the digital source type, e.g.
    "Original digital capture". Terms outside the IPTC vocabulary are shown as
    they are.

The fields describe the image asset in the database. They stay with it no
matter which thumbnails or other variants are generated from it.

.. note::

    If you use a custom image model, run ``makemigrations`` for its app after
    upgrading: the fields are added to ``BaseImage``.


What happens to the metadata in files
-------------------------------------

.. list-table::
   :header-rows: 1

   * -
     - Digital source type (XMP)
     - Content Credentials (C2PA)
   * - Original, stored as uploaded
     - kept
     - kept
   * - Original, sanitized by ``strip_exif``
     - kept (unless disabled)
     - removed
   * - Thumbnails and other variants
     - removed
     - removed
   * - Database fields of the image
     - kept
     - kept

Originals
    By default, django-filer stores the uploaded file byte for byte. All
    metadata, including XMP and C2PA manifests, remains in the file served as
    the original, e.g. via its canonical URL or a download link.

``strip_exif``
    The optional ``strip_exif`` upload sanitizer removes metadata to protect
    privacy. It keeps the digital source type: it writes a minimal XMP packet
    back into the file that holds this one property and nothing else, so no
    other XMP information, such as creator names or locations, survives. Set
    ``FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE = False`` to remove it, too.

    C2PA manifests are always removed: their signature covers the original
    bytes, so a re-encoded file cannot carry them. Since detection runs before
    the sanitizer, ``has_content_credentials`` still records that the upload
    had them; the admin says "found on upload".

Thumbnails and variants
    Thumbnails are re-encoded by easy-thumbnails and carry no metadata. This
    is intended for C2PA: a manifest signed for the original would not match a
    resized, cropped or converted image, and cannot simply be copied. The
    provenance of a thumbnail is that of its image, which the database fields
    record.


In the admin
------------

* The image's change form shows the **Origin** (the label of the digital source
  type) and whether **Content Credentials** were found on upload.
* The directory listing's table view shows the origin of AI-generated and
  AI-edited images below their name. Other digital source types, e.g. an
  original digital capture, are shown on the change form only.
* The search options of the directory listing have a **Filter** section to list
  only images created or edited using generative AI, or only images uploaded
  with Content Credentials. The filter searches all folders unless "Limit the
  search to current folder" is checked, and can be combined with a search term.

django-filer never adds icons, labels or watermarks to the images themselves.


Disclosing AI-generated images on your site
-------------------------------------------

Use ``is_ai_generated`` in your templates to disclose AI-generated images the
way your site requires, e.g. in a caption:

.. code-block:: html+django

    <figure>
        <img src="{{ image.url }}" alt="{{ image.default_alt_text }}">
        {% if image.is_ai_generated %}
            <figcaption>{{ image.digital_source_type_label }}</figcaption>
        {% endif %}
    </figure>

To query images, filter on the fields. ``ai_digital_source_type_q()`` builds
the condition used by ``is_ai_generated``:

.. code-block:: python

    from filer.models import Image
    from filer.utils.provenance import ai_digital_source_type_q

    ai_images = Image.objects.filter(ai_digital_source_type_q())
    with_credentials = Image.objects.filter(has_content_credentials=True)

Remember that the information comes from the uploaded file: an image without
metadata is not necessarily a photograph, and metadata can be removed or set
by anyone editing the file. Only a validated C2PA manifest proves where an
image comes from.


.. _provenance_command:

Scanning existing images
------------------------

To detect the provenance of images uploaded before, run::

    ./manage.py filer_detect_provenance

The command reads the stored files and only **adds** missing information: it
never clears a digital source type or the Content Credentials flag, since
``strip_exif`` may have removed them from the stored file after they were
recorded. ``--dry-run`` reports what would be updated, ``-v 2`` lists the
images. Images whose files cannot be read are reported and skipped.

The command can only find what the stored files still contain. If
``strip_exif`` was active when older images were uploaded, it removed both
from their files, and the command cannot recover them.


Settings
--------

``FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE``
    Defaults to ``True``. Whether ``strip_exif`` writes the digital source type
    back into sanitized images.
