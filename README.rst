============
Django Filer
============

|PyPiVersion| |TestCoverage| |PyVersion| |DjVersion| |CmsVersion|

**django Filer** is a file management application for django that makes
handling of files and images a breeze.

.. note::

        This project is endorsed by the `django CMS Association <https://www.django-cms.org/en/about-us/>`_.
        That means that it is officially accepted by the dCA as being in line with our roadmap vision and development/plugin policy.
        Join us on `Slack <https://www.django-cms.org/slack/>`_.

.. We're using absolute image url below, because relative paths won't work on
   pypi. github would render relative paths correctly.

+-------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/filer_2.png        | .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/filer_3.png        |
+-------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/detail_image.png   | .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/detail_file.png    |
+-------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/file_picker_1.png  | .. image:: https://raw.githubusercontent.com/django-cms/django-filer/master/docs/_static/file_picker_3.png  |
+-------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------+


*******************************************
Contribute to this project and win rewards
*******************************************

Because this is a an open-source project, we welcome everyone to
`get involved in the project <https://www.django-cms.org/en/contribute/>`_ and
`receive a reward <https://www.django-cms.org/en/bounty-program/>`_ for their contribution.
Become part of a fantastic community and help us make django CMS the best CMS in the world.

We'll be delighted to receive your
feedback in the form of issues and pull requests. Before submitting your
pull request, please review our `contribution guidelines
<http://docs.django-cms.org/en/latest/contributing/index.html>`_.

We're grateful to all contributors who have helped create and maintain this package.
Contributors are listed at the `contributors <https://github.com/django-cms/django-filer/graphs/contributors>`_
section.

Known limitations
=================

Large folder trees on SQLite and Oracle
---------------------------------------

Some directory listing queries pass a list of folder ids to the database as a
single ``IN (...)`` clause:

* searching with "limit search to current folder" passes the ids of all
  subfolders of the current folder, and
* with ``FILER_ENABLE_PERMISSIONS``, listings for users who are not superusers
  pass the ids of all folders the user may read.

These lists grow with the number of folders, and some databases cap them:

* **SQLite** before 3.32 allows at most 999 parameters per query (32,766 from
  3.32 on). Larger lists fail with ``too many SQL variables``.
* **Oracle** allows at most 1,000 items in an ``IN`` list. Larger lists fail
  with ``ORA-01795``.

On these databases, the affected listings fail once a folder tree (or a user's
readable folders) passes roughly a thousand folders. PostgreSQL (65,535
parameters) and MySQL have far higher limits. Admin actions (move, copy,
delete, …) split their queries into batches and are not affected.

Documentation
=============

Please head over to the separate `documentation <https://django-filer.readthedocs.io/en/latest/index.html>`_
for all the details on how to install, configure and use django-filer.


.. |PyPiVersion| image:: https://img.shields.io/pypi/v/django-filer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-filer
    :alt: Latest PyPI version

.. |PyVersion| image:: https://img.shields.io/pypi/pyversions/django-filer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-filer
    :alt: Python versions

.. |DjVersion| image:: https://img.shields.io/pypi/frameworkversions/django/django-filer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-filer
    :alt: Django versions

.. |CmsVersion| image:: https://img.shields.io/pypi/frameworkversions/django-cms/django-filer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/django-filer
    :alt: django CMS versions

.. |TestCoverage| image:: https://codecov.io/gh/django-cms/django-filer/graph/badge.svg?token=O64yNt6pgo
    :target: https://codecov.io/gh/django-cms/django-filer
    :alt: Test coverage

.. |License| image:: https://img.shields.io/github/license/django-cms/django-filer.svg?style=flat-square
   :target: https://pypi.python.org/pypi/django-filer/
    :alt: License
