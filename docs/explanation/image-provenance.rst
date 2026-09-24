================
Image provenance
================

Images increasingly come from generative AI tools, and regulations such as `Article 50 of the
EU AI Act <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689>`_ require
transparency about AI-generated or AI-edited content. Two standards mark such images inside
the file:

* The **IPTC digital source type** (``Iptc4xmpExt:DigitalSourceType``), a property of the
  image's XMP metadata. Its value is a term of the `IPTC vocabulary
  <https://cv.iptc.org/newscodes/digitalsourcetype/>`_, e.g. ``trainedAlgorithmicMedia`` for
  an image created using generative AI.
* **C2PA Content Credentials**, a signed manifest store embedded in the file that records
  where the image comes from and how it was edited (see the `C2PA specification
  <https://spec.c2pa.org/>`_).

django-finder detects both when an image is uploaded, stores the result with the image, and
shows it in the admin. It never changes how an image looks.

.. note::

    django-finder provides information, not compliance. Whether and how you need to disclose
    AI-generated content depends on your role and use case; marking images on your site is up
    to your templates.


What is detected
================

Digital source type
    Read from the image's XMP packet, whichever way the property is written (as an
    attribute, as element text or as an ``rdf:resource`` reference) and whatever namespace
    prefix is used. A bare term such as ``trainedAlgorithmicMedia`` is expanded to the full
    IPTC URI. Values that are neither a term nor an ``http(s)`` URI are ignored. Supported
    formats: JPEG, PNG, GIF, WebP, and AVIF and HEIF if Pillow can open them.

Content Credentials
    Whether a C2PA manifest store is embedded in the file: JPEG (APP11 segments), PNG
    (``caBX`` chunk), GIF (``C2PA_GIF`` application extension), WebP (``C2PA`` chunk), AVIF
    and HEIF (C2PA ``uuid`` box). The manifest is **not** read and its signature is **not**
    validated: the information tells that credentials were present, not that they are
    genuine. Use a tool such as `Verify <https://verify.contentauthenticity.org/>`_ to inspect
    them. Manifests stored outside the file ("remote manifests") are not detected.

Detection is best effort: a malformed file never makes an upload fail, it simply yields no
provenance information. SVG images carry none.


When detection runs
===================

Provenance is detected in ``ImageFileModel.receive_file``, that is whenever a payload is
received: on upload, and when the file of an existing image is replaced. Replacing the file
replaces the provenance information, too.

Detection sees the file **as uploaded**, before any payload validator (see
:doc:`../how-to/validate-uploads`) rewrites it, and before django-finder re-encodes the
original (see below).


How it is stored
================

The result is kept in the image's ``meta_data`` JSON field, and only if the image states a
digital source type or embeds Content Credentials:

.. code-block:: python

    image.meta_data['provenance'] == {
        'digital_source_type': 'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia',
        'content_credentials': True,
        'ai_generated': True,
    }

``ai_generated`` is true for the IPTC terms ``trainedAlgorithmicMedia`` ("Created using
generative AI") and ``compositeWithTrainedAlgorithmicMedia`` ("Edited using generative AI").
Other terms, e.g. ``algorithmicMedia`` or ``compositeSynthetic``, do not count.

Image models offer the properties ``provenance`` (a ``Provenance`` with the fields
``digital_source_type`` and ``has_content_credentials``), ``is_ai_generated`` and
``digital_source_type_label``, a human-readable, translatable label such as "Original digital
capture".

Since ``meta_data`` is a field of every inode, filtering on it works across the unified
queryset of all file models::

    ImageFileModel.objects.filter(meta_data__provenance__ai_generated=True)
    ImageFileModel.objects.filter(meta_data__provenance__content_credentials=True)

The information stays with the image when it is copied, and whatever renditions are
generated from it.


What happens to the metadata in files
=====================================

.. list-table::
   :header-rows: 1

   * -
     - Digital source type (XMP)
     - Content Credentials (C2PA)
   * - Original, stored as uploaded
     - kept
     - kept
   * - Original, re-encoded by django-finder
     - kept
     - removed
   * - Thumbnails and other renditions
     - removed
     - removed
   * - ``meta_data`` of the image
     - kept
     - kept

Originals
    Usually the uploaded file is stored byte for byte, including XMP and C2PA manifests.
    However, a web image is re-encoded when its EXIF orientation is applied or when it is
    wider than ``PILImageModel.MAX_STORED_IMAGE_WIDTH``. django-finder then writes a minimal
    XMP packet into the new file that holds the digital source type and nothing else. A C2PA
    manifest cannot survive: its signature covers the original bytes. Since detection runs
    before, ``meta_data`` still records that the upload had Content Credentials.

Payload validators
    A sanitizing validator that strips metadata, such as django-filer's ``strip_exif``,
    removes it from the stored file, but not from ``meta_data``.

Thumbnails and renditions
    Renditions in the sample storage are re-encoded without metadata. This is intended for
    C2PA: a manifest signed for the original would not match a resized or cropped image. The
    provenance of a rendition is that of its image.


In the admin
============

* The change form of an image shows its **Provenance**: the origin, i.e. the label of the
  digital source type, and whether Content Credentials were found on upload.
* The list view shows the origin of AI-generated and AI-edited images below their name.
  Other digital source types are shown on the change form only.
* The filter menu, next to the tags, offers to list only images created or edited using
  generative AI, or only images uploaded with Content Credentials. The filter is kept in the
  cookie ``django-finder-provenance`` and applies to the admin and to the file select dialog,
  including their search.

django-finder never adds icons, labels or watermarks to the images themselves.


Disclosing AI-generated images on your site
===========================================

Use ``is_ai_generated`` in your templates to disclose AI-generated images the way your site
requires, e.g. in a caption:

.. code-block:: html+django

    <figure>
        <img src="{{ image_url }}" alt="{{ image.meta_data.alt_text }}">
        {% if image.is_ai_generated %}
            <figcaption>{{ image.digital_source_type_label }}</figcaption>
        {% endif %}
    </figure>

Remember that the information comes from the uploaded file: an image without metadata is not
necessarily a photograph, and metadata can be removed or set by anyone editing the file. Only
a validated C2PA manifest proves where an image comes from.


Scanning existing images
========================

Images uploaded before django-finder detected provenance have none recorded. Scan them with::

    ./manage.py finder detect-provenance [--dry-run]

The command reads the stored originals of all images without provenance information and adds
what it finds, without changing their modification date. ``--dry-run`` reports what would be
updated, ``-v 2`` lists the images. It can only find what the stored files still contain: if
an original was re-encoded or sanitized on upload, its Content Credentials are gone.

``filer_to_finder`` copies the provenance django-filer recorded for its images.
