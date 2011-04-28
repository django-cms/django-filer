.. _running tests:

Running tests
=============

There is a minimal project and buildout configuration to get the tests up and 
running.
In the source checkout switch to the ``tests`` directory and run::

  python bootstrap.py
  ./bin/buildout

This will setup buildout and install all the needed dependencies in a isolated
environment.

Run the tests::

  ./bin/django test filer

