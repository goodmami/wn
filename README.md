# Wn: A Python Library for Wordnets

Wn is a Python library for using wordnets. For example:

```python
>>> import wn
>>> wn.download('ewn:2020')    # Install the English Wordnet 2020 (only once)
Download complete (13643357 bytes)
Checking /tmp/tmpgspkay6m.xml
Reading /tmp/tmpgspkay6m.xml
Building: [###############################] (1337590/1337590)
>>> ss = wn.synsets('win')[0]  # Get the first synset for 'win'
>>> ss.definition()            # Get the synset's definition
'be the winner in a contest or competition; be victorious'
```

Unlike previous implementations, Wn uses a SQLite database to store
wordnet data, which can make it much faster: Wn is 5x faster than the
NLTK to list all English synsets, and almost 20x faster if you include
the startup time. Some operations, particularly path operations that
require multiple SQL queries, may be slower.

Wn is also multilingual from the start. English is not the
default. Instead, all wordnets are searched unless one (or more) are
specified:

```python
>>> from nltk.corpus import wordnet as nltk_wn
>>> nltk_wn.synsets('chat')                 # only English
>>> nltk_wn.synsets('chat', lang='fra')     # only French
>>> import wn
>>> wn.synsets('chat')                      # all installed wordnets
>>> wn.synsets('chat', lgcode='en')         # limit to one language
>>> wn.synsets('chat', lexicon='ewn:2020')  # limit to one wordnet
```

## Installation

Currently Wn is only available via this repository:

```console
pip install git+https://github.com/goodmami/wn.git
```

You can also clone the repository and use
[flit](https://flit.readthedocs.io/) to install it:

```console
git clone https://github.com/goodmami/wn.git
cd wn
pip install flit  # if you don't have it
flit install
```

## Documentation

The documentation is hosted [here](https://goodmami.github.io/wn),
although it's not very useful yet.

## Available Wordnets

The following wordnets are indexed by Wn and ready to be installed:

| Name            | ID  | Versions   |
| --------------- | --- | ---------- |
| English Wordnet | ewn | 2019, 2020 |

(more coming soon)

## Migrating from the NLTK's wordnet Module

Some operations keep a compatible API with the NLTK's `wordnet`
module, but most will need some translation.

| Operation                   | `nltk.corpus.wordnet as wn`   | `pwn = wn.Wordnet('pwn', '3.0')` |
| --------------------------- | ----------------------------- | -------------------------------- |
| Lookup Synsets by word form | `wn.synsets("chat")`          | `pwn.synsets("chat")`            |
|                             | `wn.synsets("chat", pos="v")` | `pwn.synsets("chat", pos="v")`   |
| Lookup Synsets by POS       | `wn.all_synsets(pos="v")`     | `pwn.synsets(pos="v")`           |

(this table is incomplete)
