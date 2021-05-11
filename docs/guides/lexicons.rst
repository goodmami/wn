Working with Lexicons
=====================

Terminology
-----------

In Wn, the following terminology is used:

:lexicon: An inventory of words, senses, synsets, relations, etc. that
          share a namespace (i.e., that can refer to each other).
:wordnet: A group of lexicons (but usually just one).
:resource: A file containing lexicons.
:package: A directory containing a resource and optionally some
          metadata files.
:collection: A directory containing packages and optionally some
             metadata files.
:project: A general term for a resource, package, or collection,
          particularly pertaining to its creation, maintenance, and
          distribution.

In general, each resource contains one lexicon. For large projects
like the `Open English WordNet`_, that lexicon is also a wordnet on
its own. For a collection like the `Open Multilingual Wordnet`_, most
lexicons do not include relations as they instead use those from the
`Princeton WordNet`_. As such, a wordnet for these sub-projects is
best thought of as the grouping of the lexicon with the Princeton
WordNet's lexicon.

.. _Open English WordNet: https://en-word.net
.. _Open Multilingual Wordnet: https://lr.soh.ntu.edu.sg/omw/omw
.. _Princeton WordNet: https://wordnet.princeton.edu/

.. _lexicon-specifiers:

Lexicon and Project Specifiers
------------------------------

Wn uses *lexicon specifiers* to deal with the possibility of having
multiple lexicons and multiple versions of lexicons loaded in the same
database. The specifiers are the joining of a lexicon's name (ID) and
version, delimited by ``:``. Here are the possible forms:

.. code-block:: none

    *           -- any/all lexicons
    id          -- the most recently added lexicon with the given id
    id:*        -- all lexicons with the given id
    id:version  -- the lexicon with the given id and version
    *:version   -- all lexicons with the given version

For example, if both the ``2020`` and ``2019`` versions of the `Open
English Wordnet`_ were installed, in that
order, then ``ewn`` would specify the ``2019`` version, ``ewn:*``
would specify both versions, and ``ewn:2020`` would specify the
``2020`` version.

The same format is used for *project specifiers*, which refer to
projects. In most cases the project specifier is the same as the
lexicon specifier (e.g., ``ewn:2020`` refers both to the project to be
downloaded and the lexicon that is installed), but sometimes it is
not. The 1.3 release of the `Open Multilingual Wordnet`_, for
instance, has the project specifier ``omw:1.3`` but it installs a
number of lexicons with their own lexicon specifiers
(``zsmwn:1.3+omw``, ``cmnwn:1.3+omw``, etc.). When only an id is given
(e.g., ``ewn``), a project specifier gets the *first* version listed
in the index (in the default index, the first version is the latest
release).

Downloading Lexicons
--------------------

Use :py:func:`wn.download` to download lexicons from the web given
either an indexed project identifier (and optionally a version) or the
URL of a resource, package, or collection.

>>> import wn
>>> wn.download('ewn')  # get the latest Open English WordNet
>>> wn.download('ewn:2019')  # get the 2019 version
>>> # download from a URL
>>> wn.download('https://github.com/bond-lab/omw-data/releases/download/v1.3/omw-1.3.tar.xz')

The resource, package, or collection may contain multiple
lexicons. The IDs in the lexicons are what's saved to disk, not the
project identifier.

Adding Local Lexicons
---------------------

Lexicons can be added from local files with :py:func:`wn.add`:

>>> wn.add('~/data/omw/nob/nobwn.xml')

Or, with the directory as a package:

>>> wn.add('~/data/omw/nob/')

Listing Installed Lexicons
--------------------------

If you wish to see which lexicons have been added to the database, :py:func:`wn.lexicons()` returns the list of :py:class:`wn.Lexicon` objects that describe each one.

>>> for lex in wn.lexicons():
...     print(f'{lex.id}:{lex.version}\t{lex.label}')
...
nobwn:1.3+omw	Norwegian Wordnet
pwn:3.0	Princeton WordNet 3.0
ewn:2020	English WordNet
ewn:2019	English WordNet

Removing Lexicons
-----------------

Lexicons can be removed from the database with :py:func:`wn.remove`:

>>> wn.remove('nobwn:1.3+omw')

Note that this removes a single lexicon and not a project, so if, for
instance, you've installed a multi-lexicon project like ``omw``, you
will need to remove each lexicon individually or use a star specifier:

>>> wn.remove('*:1.3+omw')

WN-LMF Files, Packages, and Collections
---------------------------------------

Wn can handle projects with 3 levels of structure:

* WN-LMF XML files
* WN-LMF packages
* WN-LMF collections

WN-LMF XML Files
''''''''''''''''

A WN-LMF XML file is a file with a ``.xml`` extension that is valid
according to the `WN-LMF specification
<https://github.com/globalwordnet/schemas/>`_.

WN-LMF Packages
'''''''''''''''

If one needs to distribute metadata or additional files along with
WN-LMF XML file, a WN-LMF package allows them to include the files in
a directory. The directory should contain exactly one ``.xml`` file,
which is the WN-LMF XML file. In addition, it may contain additional
files and Wn will recognize three of them:

:``LICENSE`` (``.txt`` | ``.md`` | ``.rst`` ): the full text of the license
:``README`` (``.txt`` | ``.md`` | ``.rst`` ): the project README
:``citation.bib``: a BibTeX file containing academic citations for the project


.. code-block::

   alswn/
   ├── alswn.xml
   ├── LICENSE.txt
   └── README.md


.. code-block::

   collection/
   ├── alswn
   │   ├── alswn.xml
   │   ├── LICENSE.txt
   │   └── README.md
   ├── litwn
   │   ├── citation.bib
   │   ├── LICENSE
   │   └── litwn.xml
   ├── citation.bib
   ├── LICENSE
   └── README.md
