Installation and Configuration
==============================

.. seealso::

   This guide is for installing and configuring the Wn software. For
   adding lexicons to the database, see :doc:`guides/lexicons`.


Installing from PyPI
--------------------

Install the latest release from `PyPI <https://pypi.org/project/wn>`_:

.. code-block:: bash

   pip install wn


The Data Directory
------------------

By default, Wn stores its data (such as downloaded LMF files and the
database file) in a ``.wn_data/`` directory under the user's home
directory. This directory can be changed (see `Configuration`_
below). Whenever Wn attempts to download a resource or access its
database, it will check for the existence of, and create if necessary,
this directory, the ``.wn_data/downloads/`` subdirectory, and the
``.wn_data/wn.db`` database file. The file system will look like
this::

    .wn_data/
    ├── downloads
    │   ├── ...
    │   └── ...
    └── wn.db

The ``...`` entries in the ``downloads/`` subdirectory represent the
files of resources downloaded from the web. Their filename is a hash
of the URL so that Wn can avoid downloading the same file twice.


Configuration
-------------

The :py:data:`wn.config` object contains the paths Wn uses for local
storage and information about resources available on the web. To
change the directory Wn uses for storing data locally, modify the
:python:`wn.config.data_directory` member:

.. code-block:: python

   import wn
   wn.config.data_directory = '~/Projects/wn_data'

There are some things to note:

- The downloads directory and database path are always relative to the
  data directory and cannot be changed directly.
- This change only affects subsequent operations, so any data in the
  previous location will not be moved nor deleted.
- This change only affects the current session. If you want a script
  or application to always use the new location, it must reset the
  data directory each time it is initialized.

You can also add project information for remote resources. First you
add a project, with a project ID, full name, and language code. Then
you create one or more versions for that project with a version ID,
resource URL, and license information. This may be done either through
the :py:data:`wn.config` object's
:py:meth:`~wn._config.WNConfig.add_project` and
:py:meth:`~wn._config.WNConfig.add_project_version` methods, or loaded
from a TOML_ file via the :py:data:`wn.config` object's
:py:meth:`~wn._config.WNConfig.load_index` method.

.. _TOML: https://toml.io

.. code-block:: python

   wn.config.add_project('ewn', 'English WordNet', 'en')
   wn.config.add_project_version(
       'ewn', '2020',
       'https://en-word.net/static/english-wordnet-2020.xml.gz',
       'https://creativecommons.org/licenses/by/4.0/',
   )


Rebuilding the Database
-----------------------

New versions of Wn may occasionally alter the database schema in a way
that makes an existing database incompatible with the code. You will
see an error like this (abbreviated):

>>> import wn
>>> wn.Wordnet("oewn:2024")
Traceback (most recent call last):
  [...]
wn.DatabaseError: Wn's schema has changed and is no longer compatible with the database.
Lexicons currently installed:
  odenet:1.4
  oewn:2023
  oewn:2024
  omw-arb:1.4
  [...]]
Run wn.reset_database(rebuild=True) to rebuild the database.

You can then run, as directed, :func:`wn.reset_database` with
``rebuild=True``, which will delete the database, initialize a new one,
and attempt to add all the lexicons that were previously added. You can
also run with ``rebuild=False`` to reinitialize the database without
re-adding lexicons, or alternatively simply delete the database file
from your filesystem. See the documentation for
:func:`wn.reset_database` for more information.


Installing From Source
----------------------

If you wish to install the code from the source repository (e.g., to
get an unreleased feature or to contribute toward Wn's development),
clone the repository and use `Hatch <https://hatch.pypa.io/>`_ to
start a virtual environment with Wn installed:

.. code-block:: console

   $ git clone https://github.com/goodmami/wn.git
   $ cd wn
   $ hatch shell
