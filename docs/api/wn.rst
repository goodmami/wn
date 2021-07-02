
wn
===

.. automodule:: wn


Project Management Functions
----------------------------

.. autofunction:: download
.. autofunction:: add
.. autofunction:: remove
.. autofunction:: export
.. autofunction:: projects


Wordnet Query Functions
-----------------------

.. autofunction:: word
.. autofunction:: words
.. autofunction:: sense
.. autofunction:: senses
.. autofunction:: synset
.. autofunction:: synsets
.. autofunction:: ili
.. autofunction:: ilis
.. autofunction:: lexicons


The Wordnet Class
-----------------

.. autoclass:: Wordnet

   .. automethod:: word
   .. automethod:: words
   .. automethod:: sense
   .. automethod:: senses
   .. automethod:: synset
   .. automethod:: synsets
   .. automethod:: ili
   .. automethod:: ilis
   .. automethod:: lexicons
   .. automethod:: expanded_lexicons


The Word Class
--------------

.. autoclass:: Word

   .. attribute:: id

      The identifier used within a lexicon.

   .. attribute:: pos

      The part of speech of the Word.

   .. automethod:: lemma
   .. automethod:: forms
   .. automethod:: senses
   .. automethod:: synsets
   .. automethod:: metadata
   .. automethod:: derived_words
   .. automethod:: translate


The Form Class
''''''''''''''

.. class:: Form

   The return value of :meth:`Word.lemma` and the members of the list
   returned by :meth:`Word.forms` are :class:`Form` objects. These are
   a basic subclass of Python's :class:`str` class with an additional
   attribute, :attr:`script`, and methods :meth:`pronunciations` and
   :meth:`tags`. Form objects without any specified script behave
   exactly as a regular string (they are equal and hash to the same
   value), but if two Form objects are compared and they have
   different script values, then they are unequal and hash
   differently, even if the string itself is identical. When comparing
   a Form object to a regular string, the script value is ignored.

   >>> inu = wn.words('犬', lexicon='wnja')[0]
   >>> inu.forms()[3]
   'いぬ'
   >>> inu.forms()[3].script
   'hira'

   The :attr:`script` is often unspecified (i.e., ``None``) and this
   carries the implicit meaning that the form uses the canonical
   script for the word's language or wordnet, whatever it may be.

   .. attribute:: script

      The script of the word form. This should be an `ISO 15924
      <https://en.wikipedia.org/wiki/ISO_15924>`_ code, or ``None``.

   .. method:: pronunciations

      Return the list of :class:`Pronunciation` objects.

   .. method:: tags

      Return the list of :class:`Tag` objects.


The Pronunciation Class
'''''''''''''''''''''''

.. autoclass:: Pronunciation

   .. attribute:: value

      The encoded pronunciation.

   .. attribute:: variety

      The language variety this pronunciation belongs to.

   .. attribute:: notation

      The notation used to encode the pronunciation. For example: the
      International Phonetic Alphabet (IPA).

   .. attribute:: phonemic

      :python:`True` when the encoded pronunciation is a generalized
      phonemic description, or :python:`False` for more precise
      phonetic transcriptions.

   .. attribute:: audio

      A URI to an associated audio file.


The Tag Class
'''''''''''''

.. autoclass:: Tag

   .. attribute:: tag

      The text value of the tag.

   .. attribute:: category

      The category, or kind, of the tag.


The Sense Class
---------------

.. autoclass:: Sense

   .. attribute:: id

      The identifier used within a lexicon.

   .. automethod:: word
   .. automethod:: synset
   .. automethod:: examples
   .. automethod:: lexicalized
   .. automethod:: adjposition
   .. automethod:: frames
   .. automethod:: counts
   .. automethod:: metadata
   .. automethod:: relations
   .. automethod:: get_related
   .. automethod:: get_related_synsets
   .. automethod:: closure
   .. automethod:: relation_paths
   .. automethod:: translate


The Count Class
'''''''''''''''

.. autoclass:: Count

   Some wordnets store computed counts of senses across some corpus or
   corpora. This class models those counts. It is a subtype of
   :class:`int` with one additional method, :meth:`metadata`, which
   may be used to give information about the source of the count (if
   provided by the wordnet).

   .. automethod:: metadata


The Synset Class
----------------

.. autoclass:: Synset

   .. attribute:: id

      The identifier used within a lexicon.

   .. attribute:: pos

      The part of speech of the Synset.

   .. attribute:: ili

      The interlingual index of the Synset.

   .. automethod:: definition
   .. automethod:: examples
   .. automethod:: senses
   .. automethod:: lexicalized
   .. automethod:: lexfile
   .. automethod:: metadata
   .. automethod:: words
   .. automethod:: lemmas
   .. automethod:: hypernyms
   .. automethod:: hyponyms
   .. automethod:: holonyms
   .. automethod:: meronyms
   .. automethod:: relations
   .. automethod:: get_related
   .. automethod:: closure
   .. automethod:: relation_paths
   .. automethod:: translate

   .. The taxonomy methods below have been moved to wn.taxonomy

   .. method:: hypernym_paths(simulate_root=False)

      Shortcut for :func:`wn.taxonomy.hypernym_paths`.

   .. method:: min_depth(simulate_root=False)

      Shortcut for :func:`wn.taxonomy.min_depth`.

   .. method:: max_depth(simulate_root=False)

      Shortcut for :func:`wn.taxonomy.max_depth`.

   .. method:: shortest_path(other, simulate_root=False)

      Shortcut for :func:`wn.taxonomy.shortest_path`.

   .. method:: common_hypernyms(other, simulate_root=False)

      Shortcut for :func:`wn.taxonomy.common_hypernyms`.

   .. method:: lowest_common_hypernyms(other, simulate_root=False)

      Shortcut for :func:`wn.taxonomy.lowest_common_hypernyms`.


The ILI Class
-------------

.. autoclass:: ILI

   .. attribute:: id

      The interlingual index identifier. Unlike ``id`` attributes for
      :class:`Word`, :class:`Sense`, and :class:`Synset`, ILI
      identifers may be ``None`` (see the *proposed* :attr:`status`).

   .. attribute:: status

      The known status of the interlingual index. Loading an
      interlingual index into the database provides the following
      explicit, authoritative status values:

      - ``active`` -- the ILI is in use
      - ``provisional`` -- the ILI is being staged for permanent
        inclusion
      - ``deprecated`` -- the ILI is, or should be, no longer in use

      Without an interlingual index loaded, ILIs present in loaded
      lexicons get an implicit, temporary status from the following:

      - ``presupposed`` -- a synset uses the ILI, assuming it exists
        in an ILI file
      - ``proposed`` -- a synset introduces a concept not yet in an
        ILI and is suggesting that one should be added for it in the
        future

   .. automethod:: definition
   .. automethod:: metadata


The Lexicon Class
-----------------

.. autoclass:: Lexicon

   .. automethod:: metadata
   .. automethod:: specifier
   .. automethod:: modified
   .. automethod:: requires
   .. automethod:: extends
   .. automethod:: extensions


The wn.config Object
--------------------

Wn's data storage and retrieval can be configured through the
:data:`wn.config` object.

.. seealso::

   :doc:`../setup` describes how to configure Wn using the
   :data:`wn.config` instance.

.. autodata:: config

It is an instance of the :class:`~wn._config.WNConfig` class, which is
defined in a non-public module and is not meant to be instantiated
directly. Configuration should occur through the single
:data:`wn.config` instance.

.. autoclass:: wn._config.WNConfig

   .. autoattribute:: data_directory
   .. autoattribute:: database_path
   .. attribute:: allow_multithreading

      If set to :python:`True`, the database connection may be shared
      across threads. In this case, it is the user's responsibility to
      ensure that multiple threads don't try to write to the database
      at the same time. The default is :python:`False`.

   .. autoattribute:: downloads_directory
   .. automethod:: add_project
   .. automethod:: add_project_version
   .. automethod:: get_project_info
   .. automethod:: get_cache_path
   .. automethod:: update
   .. automethod:: load_index


Exceptions
----------

.. autoexception:: Error
.. autoexception:: DatabaseError
.. autoexception:: WnWarning
