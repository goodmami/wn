Installation, Setup, and Configuration
======================================

Installation
------------

.. code-block:: bash

   pip install wn

Setup
-----

By default, data is stored in the home directory under `.wn_data`.
This directory contains download caches and the wordnet database.  The
database is intialized automatically when it is not found in the data
directory.

Configuration
-------------

.. code-block:: python

   import wn
   wn.config.data_directory = '...'
   wn.config.add_project(...)
   wn.config.add_project_version(...)
