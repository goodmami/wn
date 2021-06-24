
wn.taxonomy
===========

.. automodule:: wn.taxonomy


Overview
--------

Among the valid synset relations for wordnets (see
:data:`wn.constants.SYNSET_RELATIONS`), those used for describing
*is-a* `taxonomies <https://en.wikipedia.org/wiki/Taxonomy>`_ are
given special treatment and they are generally the most
well-developed relations in any wordnet. Typically these are the
``hypernym`` and ``hyponym`` relations, which encode *is-a-type-of*
relationships (e.g., a *hermit crab* is a type of *decapod*, which is
a type of *crustacean*, etc.). They also include ``instance_hypernym``
and ``instance_hyponym``, which encode *is-an-instance-of*
relationships (e.g., *Oregon* is an instance of *American state*).

The taxonomy forms a multiply-inheriting hierarchy with the synsets as
nodes. In the English wordnets, such as the Princeton WordNet, nearly
all nominal synsets form such a hierarchy with single root node, while
verbal synsets form many smaller hierarchies without a common
root. Other wordnets may have different properties, but as many are
based off of the Princeton WordNet, they tend to follow this
structure.

Functions to find paths within the taxonomies form the basis of all
:mod:`wordnet similarity measures <wn.similarity>`. For instance, the
:ref:`leacock-chodorow-similarity` measure uses both
:func:`shortest_path` and (indirectly) :func:`taxonomy_depth`.


Wordnet-level Functions
-----------------------

Root and leaf synsets in the taxonomy are those with no ancestors
(``hypernym``, ``instance_hypernym``, etc.) or hyponyms (``hyponym``,
``instance_hyponym``, etc.), respectively.

Finding root and leaf synsets
'''''''''''''''''''''''''''''

.. autofunction:: roots
.. autofunction:: leaves

Computing the taxonomy depth
''''''''''''''''''''''''''''

The taxonomy depth is the maximum depth from a root node to a leaf
node within synsets for a particular part of speech.

.. autofunction:: taxonomy_depth


Synset-level Functions
----------------------

.. autofunction:: hypernym_paths
.. autofunction:: min_depth
.. autofunction:: max_depth
.. autofunction:: shortest_path
.. autofunction:: common_hypernyms
.. autofunction:: lowest_common_hypernyms
