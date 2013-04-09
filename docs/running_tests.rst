.. _running tests:

Running tests
=============


django-filer is continuously being tested on `travis-ci <https://travis-ci.org/stefanfoulis/django-filer>`_.

The simplest way to run the testsuite locally is to checkout the sourcecode, make sure you have ``PIL`` installed and
run::

    python setup.py test


It is also possible to invoke the test script directly. Just make sure the test dependencies have been installed::

    runtests.py


The recommended way to test locally is with `tox <http://tox.readthedocs.org/en/latest/>`_. Once ``tox`` is installed,
simply running the ``tox`` command inside the package root. You don't need to bother with any virtualenvs, it will be
done for you. Tox will setup multiple virtual environments with different python and django versions to test against::

    # run all tests in all default environments
    tox
    # run testsuite with django-dev/python 2.7 and django-1.4/python 2.6
    tox -e py27-django-dev,py26-django14
    # run a specific testcase in all environemnts
    tox -- filer.FilerApiTests.test_create_folder_structure
    # run a test class in specific environments
    tox -e py27-django-dev,py26-django14 -- filer.FilerApiTests

``--verbosity=3`` and ``--failfast`` are also supported.

To speed things up a bit use `detox <http://pypi.python.org/pypi/detox/>`_. ``detox`` runs each testsuite in a
separate process in parallel.
