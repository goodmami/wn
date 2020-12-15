.. raw:: html

    <style>.center {margin-left:20%}</style>


The Structure of a Wordnet
==========================
A **wordnet** is an online lexicon which is organized by concepts. 

The basic unit of a wordnet is the synonym set (**synset**), a group of words that all refer to the 
same concept. Words and synsets are linked by means of conceptual-semantic relations to form the 
structure of wordnet. 

Words, Senses, and Synsets
--------------------------
We all know that **words** are the basic building blocks of languages, a word is built up with two parts, 
its form and its meaning, but in natural languages, the word form and word meaning are not in an elegant 
one-to-one match, one word form may connect to many different meanings, so hereforth, we need **senses**, 
to work as the unit of word meanings, for example, the word *bank* has at least two senses:

1. bank\ :sup:`1`\: financial institution, like *City Bank*;
2. bank\ :sup:`2`\: sloping land, like *river bank*;

Since **synsets** are group of words sharing the same concept, bank\ :sup:`1`\ and bank\ :sup:`2`\ are members of 
two different synsets, although they have the same word form.

On the other hand, different word forms may also convey the same concept, such as *cab* and *taxi*, 
these word forms with the same concept are grouped together into one synset.

.. raw:: html
    :file: images/word-sense-synset.svg


.. role:: center
    :class: center

:center:`Figure: relations between words, senses and synsets`


Synset Relations
----------------
In wordnet, synsets are linked with each other to form various kinds of relations. For example, if 
the concept expressed by a synset is more general than a given synset, then it is in a 
*hypernym* relation with the given synset. As shown in the figure below, the synset with *car*, *auto* and *automobile* as its 
member is the *hypernym* of the other synset with *cab*, *taxi* and *hack*. Such relation which is built on 
the synset level is categorized as synset relations.

.. raw:: html
    :file: images/synset-synset.svg

:center:`Figure: example of synset relations`

Sense Relations
---------------

Some relations in wordnet are also built on sense level, which can be further divided into two types, 
relations that link sense with another sense, and relations that link sense with another synset.

.. note::  In wordnet, synset relation and sense relation can both employ a particular 
    relation type, such as `domain topic <https://globalwordnet.github.io/gwadoc/#domain_topic>`_.

**Sense-Sense**

Sense to sense relations emphasize the connections between different senses, especially when dealing 
with morphologically related words. For example, *behavioral* is the adjective to the noun *behavior*, 
which is known as in the *pertainym* relation with *behavior*, however, such relation doesn't exist between 
*behavioral* and *conduct*, which is a synonym of *behavior* and is in the same synset. Here *pertainym* 
is a sense-sense relation.

.. raw:: html
    :file: images/sense-sense.svg

:center:`Figure: example of sense-sense relations`

**Sense-Synset**

Sense-synset relations connect a particular sense with a synset. For example, *cursor* is a term in the 
*computer science* discipline, in wordnet, it is in the *has domain topic* relation with the 
*computer science* synset, but *pointer*, which is in the same synset with *cursor*, is not a term, thus 
has no such relation with *computer science* synset.

.. raw:: html
    :file: images/sense-synset.svg

:center:`Figure: example of sense-synset relations`

Other Information
-----------------
A wordnet should be built in an appropriate form, two schemas are accepted:

* XML schema based on the Lexical Markup Framework (LMF)
* JSON-LD using the Lexicon Model for Ontologies

The structure of a wordnet should contain below info:

**Definition**

Definition is used to define senses and synsets in a wordnet, it is given in the language 
of the wordnet it came from. 

**Example**

Example is used to clarify the senses and synsets in a wordnet, users can understand the definition 
more clearly with a given example.

**Metadata**

A wordnet has its own metadata, based on the `Dublin Core <https://dublincore.org/>`_, to state the 
basic info of it, below table lists all the items in the metadata of a wordnet:

+------------------+-----------+-----------+
| contributor      | Optional  |  str      |
+------------------+-----------+-----------+
| coverage         | Optional  |  str      |
+------------------+-----------+-----------+
| creator          | Optional  |  str      |
+------------------+-----------+-----------+
| date             | Optional  |  str      |
+------------------+-----------+-----------+
| description      | Optional  |  str      |
+------------------+-----------+-----------+
| format           | Optional  |  str      |
+------------------+-----------+-----------+
| identifier       | Optional  |  str      |
+------------------+-----------+-----------+
| publisher        | Optional  |  str      |
+------------------+-----------+-----------+
| relation         | Optional  |  str      |
+------------------+-----------+-----------+
| rights           | Optional  |  str      |
+------------------+-----------+-----------+
| source           | Optional  |  str      |
+------------------+-----------+-----------+
| subject          | Optional  |  str      |
+------------------+-----------+-----------+
| title            | Optional  |  str      |
+------------------+-----------+-----------+
| type             | Optional  |  str      |
+------------------+-----------+-----------+
| status           | Optional  |  str      |
+------------------+-----------+-----------+
| note             | Optional  |  str      |
+------------------+-----------+-----------+
| confidence       | Optional  |  float    |
+------------------+-----------+-----------+