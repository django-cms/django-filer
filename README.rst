============
Django Filer
============

|pypi| |python| |django| |coverage|

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

Documentation
=============

Please head over to the separate `documentation <https://django-filer.readthedocs.io/en/latest/index.html>`_
for all the details on how to install, configure and use django-filer.

Upgrading
=========

Version 3.3
-----------

django-filer version 3 contains a change in security policy for file uploads.
**By default, binary file or files of unknown type are not allowed to be uploaded.**
To allow upload of binary files in your project, add

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = [
        "application/octet-stream",
    ]

to your project's settings. Be aware that binary files always are a security risk.
See the documentation for more information on how to configure file upload validators,
e.g., running files through a virus checker.


.. |pypi| image:: https://badge.fury.io/py/django-filer.svg
    :target: http://badge.fury.io/py/django-filer
.. |coverage| image:: https://codecov.io/gh/django-cms/django-filer/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/django-cms/django-filer
.. |python| image:: https://img.shields.io/badge/python-3.10+-blue.svg
    :target: https://pypi.org/project/django-filer/
.. |django| image:: https://img.shields.io/badge/django-3.2+-blue.svg
    :target: https://www.djangoproject.com/
