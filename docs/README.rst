============================
django-finder documentation
============================

The documentation follows the `Diátaxis <https://diataxis.fr/>`_ framework. Before adding a
page, decide which of the four kinds it is, and put it in the matching directory:

``tutorials/``
    Learning-oriented. A lesson the reader follows from start to finish. It must work if
    typed verbatim.

``how-to/``
    Task-oriented. A recipe for one goal, for someone who already has a working setup.

``reference/``
    Information-oriented. What something *is*. No tutorials, no opinions.

``explanation/``
    Understanding-oriented. Why the software is the way it is. No instructions.

A page that wants to be two of these is two pages.


Build the documentation locally
===============================

Install the dependencies into a virtual environment:

.. code-block:: shell

    cd docs
    make install

Start the development server, which rebuilds and reloads on every change:

.. code-block:: shell

    make run

Then open http://0.0.0.0:8001/.

To reproduce what CI does — a full build with warnings treated as errors:

.. code-block:: shell

    make strict

Every build target uses the virtualenv created by ``make install`` when it exists, and falls
back to whatever ``sphinx-build`` is on your ``PATH`` otherwise. Override it explicitly with
``make html SPHINXBUILD=/path/to/sphinx-build``.


Unwritten sections
==================

Gaps are marked with ``.. todo::`` directives and are rendered in the built output, because
``todo_include_todos`` is on. Search for them before starting work:

.. code-block:: shell

    grep -rn "todo::" .


Spelling
========

``sphinxcontrib.spelling`` is configured but only runs under the ``spelling`` builder, not
during the HTML build. It needs the `enchant <https://www.abisource.com/projects/enchant/>`_
library:

.. code-block:: shell

    brew install enchant  # macOS
    make spelling


Contribute
==========

If you find anything that could be improved, please open a pull request against the
``finder`` branch.
