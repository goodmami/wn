# Wn: A Python Library for Wordnets

Wn is a Python library for using wordnets. For example:

```python
>>> import wn
>>> wn.download('ewn', '2020')  # Install the English Wordnet 2020
>>> ss = wn.synsets('win')[0]   # Get the first synset for 'win'
>>> ss.definition()             # Get the synset's definition
'be the winner in a contest or competition; be victorious'
```

Unlike previous implementations, Wn uses a SQLite database to store
wordnet data, which can make it much faster: Wn is 5x faster than the
NLTK to list all English synsets, and almost 20x faster if you include
the startup time.

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

## Documentation

The documentation is not yet hosted, but you can build it with Sphinx:

```console
pip install sphinx sphinx-copybutton furo
cd docs/
make html
cd _build/html
python -m http.server
```


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
