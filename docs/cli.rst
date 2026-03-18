Command Line Interface
======================

Some of Wn's functionality is exposed via the command line.

Global Options
--------------

.. option:: -d DIR, --dir DIR

   Change to use ``DIR`` as the data directory prior to invoking any
   commands.


Subcommands
-----------

download
--------

Download and add projects to the database given one or more project
specifiers or URLs.

.. code-block:: console

   $ python -m wn download oewn:2021 omw:1.4 cili
   $ python -m wn download https://en-word.net/static/english-wordnet-2021.xml.gz

.. option:: --index FILE

   Use the index at ``FILE`` to resolve project specifiers.

   .. code-block:: console

      $ python -m wn download --index my-index.toml mywn

.. option:: --no-add

   Download and cache the remote file, but don't add it to the
   database.


cache
-----

View the files in the download cache. The ``download`` command caches the (often
compressed) files to the filesystem prior to adding to Wn's database. The files
are renamed with a hash of the URL to avoid name clashes, but this also makes it
hard to determine what a particular file is. This command cross-references the
downloaded files with what is in the index. An optional project specifier
argument can help narrow down the results.

.. code-block:: console

   $ python -m wn cache  # many results; abbreviated here
   af909070c29845b952d1799551bffc302e28d2c5        own-en  1.0.0   https://github.com/own-pt/openWordnet-PT/releases/download/v1.0.0/own-en.tar.gz
   e25af66e46775b00d689619787013e6a35e5cbf7        oewn    2025    https://en-word.net/static/english-wordnet-2025.xml.gz
   5a26d97a0081996db4cd621638a8a9b0da09aa25        odenet  1.4     https://github.com/hdaSprachtechnologie/odenet/releases/download/v1.4/odenet-1.4.tar.xz
   [...]
   $ python -m wn cache "oewn:2025*" # narrowed results
   e25af66e46775b00d689619787013e6a35e5cbf7        oewn    2025    https://en-word.net/static/english-wordnet-2025.xml.gz
   0f5371187dcfe7e05f2a93ab85b4e1168859a5c2        oewn    2025+   https://en-word.net/static/english-wordnet-2025-plus.xml.gz

.. option:: --full-paths-only

   Only print the full path of each cache file. This can be useful when one
   wants to pipe the results to other commands. For example, on Unix-like
   systems, the following will delete matching cache entries:

   .. code-block:: console

      $ python -m wn cache --full-paths-only "omw*:1.4" | xargs rm


lexicons
--------

The ``lexicons`` subcommand lets you quickly see what is installed:

.. code-block:: console

   $ python -m wn lexicons
   omw-en	1.4	[en]	OMW English Wordnet based on WordNet 3.0
   omw-sk	1.4	[sk]	Slovak WordNet
   omw-pl	1.4	[pl]	plWordNet
   omw-is	1.4	[is]	IceWordNet
   omw-zsm	1.4	[zsm]	Wordnet Bahasa (Malaysian)
   omw-sl	1.4	[sl]	sloWNet
   omw-ja	1.4	[ja]	Japanese Wordnet
   ...

.. option:: -l LG, --lang LG
.. option:: --lexicon SPEC

   The ``--lang`` or ``--lexicon`` option can help you narrow down
   the results:

   .. code-block:: console

      $ python -m wn lexicons --lang en
      oewn	2021	[en]	Open English WordNet
      omw-en	1.4	[en]	OMW English Wordnet based on WordNet 3.0
      $ python -m wn lexicons --lexicon "omw-*"
      omw-en	1.4	[en]	OMW English Wordnet based on WordNet 3.0
      omw-sk	1.4	[sk]	Slovak WordNet
      omw-pl	1.4	[pl]	plWordNet
      omw-is	1.4	[is]	IceWordNet
      omw-zsm	1.4	[zsm]	Wordnet Bahasa (Malaysian)


projects
--------

The ``projects`` subcommand lists all known projects in Wn's
index. This is helpful to see what is available for downloading.

.. code-block::

   $ python -m wn projects
   ic      cili    1.0     [---]   Collaborative Interlingual Index
   ic      oewn    2025+   [en]    Open English WordNet
   ic      oewn    2025    [en]    Open English WordNet
   ic      oewn    2024    [en]    Open English WordNet
   ic      oewn    2023    [en]    Open English WordNet
   ic      oewn    2022    [en]    Open English WordNet
   ic      oewn    2021    [en]    Open English WordNet
   ic      ewn     2020    [en]    Open English WordNet
   ic      ewn     2019    [en]    Open English WordNet
   ic      odenet  1.4     [de]    Open German WordNet
   i-      odenet  1.3     [de]    Open German WordNet
   ic      omw     2.0     [mul]   Open Multilingual Wordnet
   ic      omw     1.4     [mul]   Open Multilingual Wordnet
   ...


validate
--------

Given a path to a WN-LMF XML file, check the file for structural
problems and print a report.

.. code-block::

   $ python -m wn validate english-wordnet-2021.xml

.. option:: --select CHECKS

   Run the checks with the given comma-separated list of check codes
   or categories.

   .. code-block::

      $ python -m wn validate --select E W201 W204 deWordNet.xml

.. option:: --output-file FILE

   Write the report to FILE as a JSON object instead of printing the
   report to stdout.
