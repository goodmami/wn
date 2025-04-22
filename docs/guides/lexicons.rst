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
lexicons do not include relations as they are instead expected to use
those from the OMW's included English wordnet, which is derived from
the `Princeton WordNet`_. As such, a wordnet for these sub-projects is
best thought of as the grouping of the lexicon with the lexicon
providing the relations.

.. _Open English WordNet: https://en-word.net
.. _Open Multilingual Wordnet: https://github.com/omwn/
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

For example, if ``ewn:2020`` was installed followed by ``ewn:2019``,
then ``ewn`` would specify the ``2019`` version, ``ewn:*`` would
specify both versions, and ``ewn:2020`` would specify the ``2020``
version.

The same format is used for *project specifiers*, which refer to
projects as defined in Wn's index. In most cases the project specifier
is the same as the lexicon specifier (e.g., ``ewn:2020`` refers both
to the project to be downloaded and the lexicon that is installed),
but sometimes it is not. The 1.4 release of the `Open Multilingual
Wordnet`_, for instance, has the project specifier ``omw:1.4`` but it
installs a number of lexicons with their own lexicon specifiers
(``omw-zsm:1.4``, ``omw-cmn:1.4``, etc.). When only an id is given
(e.g., ``ewn``), a project specifier gets the *first* version listed
in the index (in the default index, conventionally, the first version
is the latest release).

.. _lexicon-filters:

Filtering Queries with Lexicons
-------------------------------

Queries against the database will search all installed lexicons unless
they are filtered by ``lang`` or ``lexicon`` arguments:

>>> import wn
>>> len(wn.words())
1538449
>>> len(wn.words(lang="en"))
318289
>>> len(wn.words(lexicon="oewn:2024"))
161705

The ``lexicon`` parameter can also take multiple specifiers so you can
include things like lexicon extensions or to explicitly include
multiple lexicons:

>>> len(wn.words(lexicon="oewn:2024 omw-en:1.4"))
318289

If a lexicon selected by the ``lexicon`` or ``lang`` arguments
specifies a dependency, the dependency is automatically added as an
*expand* lexicon. Explicitly set :python:`expand=''` to disable this
behavior:

>>> wn.lexicons(lexicon="omw-es:1.4")[0].requires()  # omw-es requires omw-en
{'omw-en:1.4': <Lexicon omw-en:1.4 [en]>}
>>> es = wn.Wordnet("omw-es:1.4")
>>> es.lexicons()
[<Lexicon omw-es:1.4 [es]>]
>>> es.expanded_lexicons()  # omw-en automatically added
[<Lexicon omw-en:1.4 [en]>]
>>> es_no_en = wn.Wordnet("omw-es:1.4", expand='')
>>> es_no_en.lexicons()
[<Lexicon omw-es:1.4 [es]>]
>>> es_no_en.expanded_lexicons()  # no expand lexicons
[]

Also see :ref:`cross-lingual-relation-traversal` for
selecting expand lexicons for relations.

The objects returned by queries retain the "lexicon configuration"
used, which includes the lexicons and expand lexicons. This
configuration determines which lexicons are searched during secondary
queries. The lexicon configuration also stores a flag indicating
whether no lexicon filters were used at all, which triggers
:ref:`default mode <default-mode>` secondary queries.

.. _default-mode:

Default Mode Queries
--------------------

A special "default mode" is activated when making a module-function
query (:func:`wn.words`, :func:`wn.synsets`, etc.) or instantiating a
:class:`wn.Wordnet` object with no ``lexicon`` or ``lang`` argument
(so-named because the mode is triggered by using the default values of
``lexicon`` and ``lang``):

>>> w = wn.Wordnet()
>>> wn.words("pineapple")  # for example

Default-mode causes the following behavior:

1. Primary queries search any installed lexicon
2. Secondary queries only search the lexicon of the primary entity
   (e.g., :meth:`Synset.words` only finds words from the same lexicon
   as the synset). If the lexicon has any extensions or is itself an
   extension, any extension/base lexicons are also included.
3. If the ``expand`` argument is :python:`None` (always true for
   module functions like :func:`wn.synsets`), all installed lexicons
   are used as expand lexicons for relations queries.

.. warning::

   Default-mode queries are not reproducible as the results can change
   as lexicons are added or removed from the database. For anything
   more than a casual query, it is highly suggested to instead create
   a :class:`wn.Wordnet` object with fully-specified ``lexicon`` and
   ``expand`` arguments.

Downloading Lexicons
--------------------

Use :py:func:`wn.download` to download lexicons from the web given
either an indexed project specifier or the URL of a resource, package,
or collection.

>>> import wn
>>> wn.download('odenet')  # get the latest Open German WordNet
>>> wn.download('odenet:1.3')  # get the 1.3 version
>>> # download from a URL
>>> wn.download('https://github.com/omwn/omw-data/releases/download/v1.4/omw-1.4.tar.xz')

The project specifier is only used to retrieve information from Wn's
index. The lexicon IDs of the corresponding resource files are what is
stored in the database.

Adding Local Lexicons
---------------------

Lexicons can be added from local files with :py:func:`wn.add`:

>>> wn.add('~/data/omw-1.4/omw-nb/omw-nb.xml')

Or with the parent directory as a package:

>>> wn.add('~/data/omw-1.4/omw-nb/')

Or with the grandparent directory as a collection (installing all
packages contained by the collection):

>>> wn.add('~/data/omw-1.4/')

Or from a compressed archive of one of the above:

>>> wn.add('~/data/omw-1.4/omw-nb/omw-nb.xml.xz')
>>> wn.add('~/data/omw-1.4/omw-nb.tar.xz')
>>> wn.add('~/data/omw-1.4.tar.xz')

Listing Installed Lexicons
--------------------------

If you wish to see which lexicons have been added to the database,
:py:func:`wn.lexicons()` returns the list of :py:class:`wn.Lexicon`
objects that describe each one.

>>> for lex in wn.lexicons():
...     print(f'{lex.id}:{lex.version}\t{lex.label}')
...
omw-en:1.4	OMW English Wordnet based on WordNet 3.0
omw-nb:1.4	Norwegian Wordnet (Bokmål)
odenet:1.3	Offenes Deutsches WordNet
ewn:2020	English WordNet
ewn:2019	English WordNet

Removing Lexicons
-----------------

Lexicons can be removed from the database with :py:func:`wn.remove`:

>>> wn.remove('omw-nb:1.4')

Note that this removes a single lexicon and not a project, so if, for
instance, you've installed a multi-lexicon project like ``omw``, you
will need to remove each lexicon individually or use a star specifier:

>>> wn.remove('omw-*:1.4')

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

   omw-sq/
   ├── omw-sq.xml
   ├── LICENSE.txt
   └── README.md

WN-LMF Collections
''''''''''''''''''

In some cases a project may manage multiple resources and distribute
them as a collection. A collection is a directory containing
subdirectories which are WN-LMF packages. The collection may contain
its own README, LICENSE, and citation files which describe the project
as a whole.

.. code-block::

   omw-1.4/
   ├── omw-sq
   │   ├── oms-sq.xml
   │   ├── LICENSE.txt
   │   └── README.md
   ├── omw-lt
   │   ├── citation.bib
   │   ├── LICENSE
   │   └── omw-lt.xml
   ├── ...
   ├── citation.bib
   ├── LICENSE
   └── README.md
