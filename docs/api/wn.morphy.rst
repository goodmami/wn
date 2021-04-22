
wn.morphy
=========

.. automodule:: wn.morphy

System Flags
------------

The following flags may be passed to the ``system`` parameter of
:class:`Morphy` to adjust the patterns and behaviors it uses. Note
that in order to use these flags, the Morphy instance must be assigned
to the :class:`wn.Wordnet` instances after initialization:

>>> import wn
>>> from wn import morphy
>>> pwn = wn.Wordnet("pwn:3.0")
>>> pwn.lemmatizer = morphy.Morphy(pwn, system=morphy.NLTK)

.. data:: PWN

   Use the behavior implemented in the Princeton WordNet.

.. data:: NLTK

   Use the behavior implemented in the NLTK.

.. data:: WN

   Use the behavior created for Wn.

The Morphy Class
----------------

.. autoclass:: Morphy
