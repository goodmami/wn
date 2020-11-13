Working with Lexicons
=====================

.. _lexicon-specifiers:

Lexicon Specifiers
------------------

``id:version``

Downloading Lexicons
--------------------

.. code-block:: python

   import wn
   wn.download(lexicon)

Adding Local Lexicons
---------------------

.. code-block:: python

   import wn
   wn.add(path)

Listing Installed Lexicons
--------------------------

.. code-block:: python

   import wn
   wn.lexicons()


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
