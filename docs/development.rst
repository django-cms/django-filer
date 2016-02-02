.. _development:

Developement
============

Working on front-end
--------------------

To started development fron-end part of ``django-filer`` simply install all the packages over npm:

``npm install``

To compile and watch scss, run javascript unit-tests, jshint and jscs watchers:

``gulp``

To compile scss to css:

``gulp sass``

To run sass watcher:

``gulp sass:watch``

To run javascript linting and code styling analysis:

``gulp lint``

To run javascript linting and code styling analysis watcher:

``gulp lint:watch``

To run javascript linting:

``gulp jshint``

To run javascript code style analysis:

``gulp jscs``

To fix javascript code style errors:

``gulp jscs:fix``

To run javascript unit-tests:

``gulp tests:unit``


Contributing
------------

Claiming Issues
...............

Since github issues does not support assigning an issue to a non collaborator (yet), please just add a comment on the issue to claim it.

Code Guidelines
...............

The code should be `PEP8`_ compliant. With the exception that the line width is not limited to 80, but to 120 characters.

The `flake8`_ command can be very helpful (we run it as a separate env through `Tox` on `Travis`). If you want to check your changes for code style::

    $ flake8

This runs the checks without line widths and other minor checks, it also ignores source files in the `migrations` and `tests` and some other folders.

This is the last command to run before submitting a PR (that will run tests in all tox environments)::

    $ tox

Another useful tool is `reindent`_. It fixes whitespace and indentation stuff::

    $ reindent -n filer/models/filemodels.py


Workflow
........

Fork -> Code -> Pull request

django-filer uses the excellent `branching model <http://nvie.com/posts/a-successful-git-branching-model/>`_ from `nvie`_.
It is highly recommended to use the `git flow <http://github.com/nvie/gitflow>`_ extension that makes working with this branching model very easy.

* fork `django-filer`_ on github
* clone your fork ``git clone git@github.com:username/django-filer.git``
* ``cd django-filer``
* initialize git flow: ``git flow init`` (choose all the defaults)
* ``git flow feature start my_feature_name`` creates a new branch called ``feature/my_feature_name`` based on ``develop``
* ...code... ...code... ..commit.. ..commit..
* ``git flow feature publish`` creates a new branch remotely and pushes your changes
* navigate to the feature branch on github and create a pull request to the ``develop`` branch on ``divio/django-filer``
* after reviewing the changes may be merged into ``develop`` and then eventually into ``master`` for the release.

If the feature branch is long running, it is good practice to merge in the current state of the ``develop`` branch into the feature branch sometimes. This keeps the feature branch up to date and reduces the likeliness of merge conflicts once it is merged back into develop.


.. _`PEP8`: http://www.python.org/dev/peps/pep-0008
.. _`flake8`: http://pypi.python.org/pypi/flake8
.. _`reindent`: http://pypi.python.org/pypi/Reindent
.. _`nvie`: http://nvie.com
.. _`django-filer`: http://github.com/divio/django-filer
