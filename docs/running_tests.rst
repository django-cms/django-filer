.. _running tests:

Running tests
=============


django-filer is continuously being tested on `travis-ci <https://travis-ci.org/divio/django-filer>`_.

There is no easy way to run test suite on any python version you have installed without using ``tox``.

The recommended way to test locally is with `tox <https://tox.readthedocs.io/en/latest/>`_. Once ``tox`` is installed,
simply running the ``tox`` command inside the package root. You don't need to bother with any virtualenvs, it will be
done for you. Tox will setup multiple virtual environments with different python and django versions to test against::

    # run all tests in all default environments
    tox
    # run tests on particular versions
    tox -e py27-dj18,py34-dj_master
    # run a test class in specific environment
    tox -e py27-dj18 -- test filer.tests.models.FilerApiTests
    # run a specific testcase in specific environment
    tox -e py27-dj18 -- test filer.tests.models.FilerApiTests.test_create_folder_structure

Other test runner options are also supported, see
`djangocms-helper <https://djangocms-helper.readthedocs.io/en/develop/>`_
documentation for details.

To speed things up a bit use `detox <http://pypi.python.org/pypi/detox/>`_. ``detox`` runs each testsuite in a
separate process in parallel. Detox also supports using ``pyenv`` to install multiple python versions.
