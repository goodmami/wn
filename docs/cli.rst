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
   ic	cili	1.0	[---]	Collaborative Interlingual Index
   ic	oewn	2023	[en]	Open English WordNet
   ic	oewn	2022	[en]	Open English WordNet
   ic	oewn	2021	[en]	Open English WordNet
   ic	ewn	2020	[en]	Open English WordNet
   ic	ewn	2019	[en]	Open English WordNet
   i-	odenet	1.4	[de]	Open German WordNet
   ic	odenet	1.3	[de]	Open German WordNet
   ic	omw	1.4	[mul]	Open Multilingual Wordnet
   ic	omw-en	1.4	[en]	OMW English Wordnet based on WordNet 3.0
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
