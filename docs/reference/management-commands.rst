===================
Management commands
===================

``finder``
==========

.. code-block:: shell

    ./manage.py finder <subcommand> [options]

``list-ambits``
    Print every configured ambit with its slug, name, site, admin site and storages.

``add-ambit <slug> [--values key=value ...]``
    Create an ambit. Recognised keys: ``name``, ``storage``, ``sample_storage``, ``site``,
    ``admin``.

``edit-ambit <slug> [--values key=value ...]``
    Change an existing ambit. Same keys as ``add-ambit``.

``delete-ambit <slug> [--erase-files]``
    Delete an ambit. With ``--erase-files``, also remove its payloads from storage.

``reorganize <slug>``
    Reassign every file in the ambit to the model matching its MIME type. Run after adding a
    contrib app to an installation that already holds files.

``reorder <slug>``
    Recompute the ``ordering`` value of every file in every folder of the ambit.

See :doc:`../how-to/manage-ambits`.


``filer_to_finder``
===================

.. code-block:: shell

    ./manage.py filer_to_finder <ambit-slug>

Copy folders and files out of an existing django-filer installation into the given ambit.
See :doc:`../how-to/migrate-from-filer`.

.. todo::

   Document the exit codes, the ``--verbosity`` behaviour and whether either command is safe
   to re-run.
