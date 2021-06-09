
wn.web
======

.. automodule:: wn.web

This module provides a RESTful API with `JSON:API`_ responses to
queries against a Wn database. This API implements the primary queries
of the Python API (see :ref:`primary-queries`). For instance, to
search all words in the ``ewn:2020`` lexicon with the form *jet* and
part-of-speech *v*, we can perform the following query::

  /lexicons/ewn:2020/words?form=jet&pos=v

This query would return the following response:

.. code-block:: javascript

   {
     "data": [
       {
         "id": "ewn-jet-v",
         "type": "word",
         "attributes": {
           "pos": "v",
           "lemma": "jet",
           "forms": ["jet", "jetted", "jetting"]
         },
         "links": {
           "self": "http://example.com/lexicons/ewn:2020/words/ewn-jet-v"
         },
         "relationships": {
           "senses": {
             "links": {"related": "http://example.com/lexicons/ewn:2020/words/ewn-jet-v/senses"}
           },
           "synsets": {
             "data": [
               {"type": "synset", "id": "ewn-01518922-v"},
               {"type": "synset", "id": "ewn-01946093-v"}
             ]
           },
           "lexicon": {
             "links": {"related": "http://example.com/lexicons/ewn:2020"}
           }
         },
         "included": [
           {
             "id": "ewn-01518922-v",
             "type": "synset",
             "attributes": {"pos": "v", "ili": "i29306"},
             "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-01518922-v"}
           },
           {
             "id": "ewn-01946093-v",
             "type": "synset",
             "attributes": {"pos": "v", "ili": "i31432"},
             "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-01946093-v"}
           }
         ]
       }
     ],
     "meta": {"total": 1}
   }

Currently, only ``GET`` requests are handled.

.. _JSON\:API: https://jsonapi.org


Installing Dependencies
-----------------------

By default, Wn does not install the requirements needed for this
module. Install them with the ``[web]`` extra:

.. code-block:: bash

   $ pip install wn[web]


Running and Deploying the Server
--------------------------------

This module does not provide an ASGI server, so one will need to be
installed and ran separately. Any ASGI-compliant server should
work.

For example, the `Uvicorn <https://www.uvicorn.org/>`_ server may be
used directly for local development, optionally with the ``--reload``
option for hot reloading:

.. code-block:: bash

   $ uvicorn --reload wn.web:app

For production, see Uvicorn's `documentation about deployment
<https://www.uvicorn.org/deployment/>`_.


Requests: API Endpoints
-----------------------

The module provides the following endpoints:

.. table::
   :width: 100%

   ======================================  ========================================================
   Endpoint                                Description
   ======================================  ========================================================
   ``/words``                              List words in all available lexicons
   ``/senses``                             List senses in all available lexicons
   ``/synsets``                            List synsets in all available lexicons
   ``/lexicons``                           List available lexicons
   ``/lexicons/:lex``                      Get lexicon with specifier ``:lex``
   ``/lexicons/:lex/words``                List words for lexicon with specifier ``:lex``
   ``/lexicons/:lex/words/:id/senses``     List senses for word ``:id`` in lexicon ``:lex``
   ``/lexicons/:lex/words/:id``            Get word with ID ``:id`` in lexicon ``:lex``
   ``/lexicons/:lex/senses``               List senses for lexicon with specifier ``:lex``
   ``/lexicons/:lex/senses/:id``           Get sense with ID ``:id`` in lexicon ``:lex``
   ``/lexicons/:lex/synsets``              List synsets for lexicon with specifier ``:lex``
   ``/lexicons/:lex/synsets/:id``          Get synset with ID ``:id`` in lexicon ``:lex``
   ``/lexicons/:lex/synsets/:id/members``  Get member senses for synset ``:id`` in lexicon ``:lex``
   ======================================  ========================================================


Requests: Query Parameters
--------------------------

``lang``
''''''''

Specifies the language in `BCP 47`_ of the lexicon(s) from which
results are returned.

.. _BCP 47: https://en.wikipedia.org/wiki/IETF_language_tag

Example::

  /words?lang=fr

Valid for::

  /lexicons
  /words
  /senses
  /synsets

``form``
''''''''

Specifies the word form of the objects that are returned.

Example::

  /words?form=chat

Valid for::

  /words
  /senses
  /synsets
  /lexicon/:lex/words
  /lexicon/:lex/senses
  /lexicon/:lex/synsets

``pos``
'''''''

Specifies the part-of-speech of the objects that are returned. Valid
values are given in :ref:`parts-of-speech`.

Example::

  /words?pos=v

Valid for::

  /words
  /senses
  /synsets
  /lexicon/:lex/words
  /lexicon/:lex/senses
  /lexicon/:lex/synsets

``ili``
'''''''

Specifies the interlingual index of a synset.

Example::

  /synsets?ili=i57031

Valid for::

  /synsets
  /lexicon/:lex/synsets

``page[offset]`` and ``page[limit]``
''''''''''''''''''''''''''''''''''''

Used for pagination: ``page[offset]`` specifies the starting index of
a set of results, and ``page[limit]`` specifies how many results from
the offset will be returned.

Example::

  /words?page[offset]=150

Valid for::

  /words
  /senses
  /synsets
  /lexicon/:lex/words
  /lexicon/:lex/senses
  /lexicon/:lex/synsets


Responses
---------

Responses are JSON data following the `JSON:API`_ specification. A
full description of JSON:API is left to the linked specification, but
a brief walkthrough is provided here. First, the top-level structure
of "to-one" responses (e.g., getting a single synset) is:

.. code-block:: javascript

   {
     "data": { ... },  // primary response data as a JSON object
     "meta": { ... }   // metadata for the response
   }

For "to-many" responses (e.g., getting a list of matching synsets), it
is the same as above except the ``data`` key maps to an array and it
includes pagination links:

.. code-block:: javascript

   {
     "data": [{ ... }, ...],  // primary response data as an array of objects
     "links": { ... },        // pagination links
     "meta": { ... }          // metadata; e.g., total number of results
   }

Each JSON:API *resource object* (the primary data given by the
``data`` key) has the following structure:

.. code-block:: javascript

   {
     "id": "...",               // Lexicon specifier or entity ID
     "type": "...",             // "lexicon", "word", "sense", or "synset"
     "attributes": { ... },     // Basic resource information
     "links": { "self": ... },  // URL for this specific resource
     "relationships": { ... },  // Word senses, synset members, other relations
     "included": [ ... ],       // Data for related resources
   }


Lexicons
''''''''

.. code-block:: javascript

   {
     "id": "ewn:2020",
     "type": "lexicon",
     "attributes": {
       "version": "2020",
       "label": "English WordNet",
       "language": "en",
       "license": "https://creativecommons.org/licenses/by/4.0/"
     },
     "links": {"self": "http://example.com/lexicons/ewn:2020"},
     "relationships": {
       "words": {"links": {"related": "http://example.com/lexicons/ewn:2020/words"}},
       "synsets": {"links": {"related": "http://example.com/lexicons/ewn:2020/synsets"}},
       "senses": {"links": {"related": "http://example.com/lexicons/ewn:2020/senses"}}
     }
   }


Words
'''''

.. code-block:: javascript

   {
     "id": "ewn-brick-v",
     "type": "word",
     "attributes": {"pos": "v", "lemma": "brick", "forms": ["brick"]},
     "links": {"self": "http://example.com/lexicons/ewn:2020/words/ewn-brick-v"},
     "relationships": {
       "senses": {"links": {"related": "http://example.com/lexicons/ewn:2020/words/ewn-brick-v/senses"}},
       "synsets": {"data": [{"type": "synset", "id": "ewn-90011761-v"}]},
       "lexicon": {"links": {"related": "http://example.com/lexicons/ewn:2020"}}
     },
     "included": [
       {
         "id": "ewn-90011761-v",
         "type": "synset",
         "attributes": {"pos": "v", "ili": null},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-90011761-v"}
       }
     ]
   }


Senses
''''''

.. code-block:: javascript

   {
     "id": "ewn-explain-v-00941308-01",
     "type": "sense",
     "links": {"self": "http://example.com/lexicons/ewn:2020/senses/ewn-explain-v-00941308-01"},
     "relationships": {
       "word": {"links": {"related": "http://example.com/lexicons/ewn:2020/words/ewn-explain-v"}},
       "synset": {"links": {"related": "http://example.com/lexicons/ewn:2020/synsets/ewn-00941308-v"}},
       "lexicon": {"links": {"related": "http://example.com/lexicons/ewn:2020"}},
       "derivation": {
         "data": [
           {"type": "sense", "id": "ewn-explanatory-s-01327635-01"},
           {"type": "sense", "id": "ewn-explanation-n-07247081-01"}
         ]
       }
     },
     "included": [
       {
         "id": "ewn-explanatory-s-01327635-01",
         "type": "sense",
         "links": {"self": "http://example.com/lexicons/ewn:2020/senses/ewn-explanatory-s-01327635-01"}
       },
       {
         "id": "ewn-explanation-n-07247081-01",
         "type": "sense",
         "links": {"self": "http://example.com/lexicons/ewn:2020/senses/ewn-explanation-n-07247081-01"}
       }
     ]
   }


Synsets
'''''''

.. code-block:: javascript

   {
     "id": "ewn-03204585-n",
     "type": "synset",
     "attributes": {"pos": "n", "ili": "i52917"},
     "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-03204585-n"},
     "relationships": {
       "members": {"links": {"related": "http://example.com/lexicons/ewn:2020/synsets/ewn-03204585-n/members"}},
       "words": {
         "data": [
           {"type": "word", "id": "ewn-dory-n"},
           {"type": "word", "id": "ewn-rowboat-n"},
           {"type": "word", "id": "ewn-dinghy-n"}
         ]
       },
       "lexicon": {"links": {"related": "http://example.com/lexicons/ewn:2020"}},
       "hypernym": {"data": [{"type": "synset", "id": "ewn-04252125-n"}]},
       "mero_part": {
         "data": [
           {"type": "synset", "id": "ewn-03911849-n"},
           {"type": "synset", "id": "ewn-04439177-n"}
         ]
       },
       "hyponym": {
         "data": [
           {"type": "synset", "id": "ewn-04122550-n"},
           {"type": "synset", "id": "ewn-04584425-n"}
         ]
       }
     },
     "included": [
       {
         "id": "ewn-dory-n",
         "type": "word",
         "attributes": {"pos": "n", "lemma": "dory", "forms": ["dory"]},
         "links": {"self": "http://example.com/lexicons/ewn:2020/words/ewn-dory-n"}
       },
       {
         "id": "ewn-rowboat-n",
         "type": "word",
         "attributes": {"pos": "n", "lemma": "rowboat", "forms": ["rowboat"]},
         "links": {"self": "http://example.com/lexicons/ewn:2020/words/ewn-rowboat-n"}
       },
       {
         "id": "ewn-dinghy-n",
         "type": "word",
         "attributes": {"pos": "n", "lemma": "dinghy", "forms": ["dinghy"]},
         "links": {"self": "http://example.com/lexicons/ewn:2020/words/ewn-dinghy-n"}
       },
       {
         "id": "ewn-04252125-n",
         "type": "synset",
         "attributes": {"pos": "n", "ili": "i59107"},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-04252125-n"}
       },
       {
         "id": "ewn-03911849-n",
         "type": "synset",
         "attributes": {"pos": "n", "ili": "i57094"},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-03911849-n"}
       },
       {
         "id": "ewn-04439177-n",
         "type": "synset",
         "attributes": {"pos": "n", "ili": "i60240"},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-04439177-n"}
       },
       {
         "id": "ewn-04122550-n",
         "type": "synset",
         "attributes": {"pos": "n", "ili": "i58319"},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-04122550-n"}
       },
       {
         "id": "ewn-04584425-n",
         "type": "synset",
         "attributes": {"pos": "n", "ili": "i61103"},
         "links": {"self": "http://example.com/lexicons/ewn:2020/synsets/ewn-04584425-n"}
       }
     ]
   }
