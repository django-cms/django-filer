Running tests
=============

There is a minimal project and buildout configuration to get the tests up and 
running.
In the source checkout run::

  python bootstrap.py
  ./bin/buildout

This will setup buildout and install all the needed dependencies in a isolated
invironment.

Then you can run the testsuite with::

  ./bin/django test filer

