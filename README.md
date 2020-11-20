# Wn: A Python Library for Wordnets

[![PyPI Version](https://img.shields.io/pypi/v/wn.svg)](https://pypi.org/project/wn/)
![Python Support](https://img.shields.io/pypi/pyversions/wn.svg)
[![Documentation Status](https://readthedocs.org/projects/wn/badge/?version=latest)](https://wn.readthedocs.io/en/latest/?badge=latest)

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

The documentation is hosted [here](https://wn.readthedocs.io/).

## Available Wordnets

The following wordnets are indexed by Wn and ready to be installed:

| Name                       | ID    | Versions       | Language         |
| -------------------------- | ----- | -------------- | ---------------- |
| Open English Wordnet       | `ewn` | `2019`, `2020` | English [en]     |
| Princeton WordNet          | `pwn` | `3.0`, `3.1`   | English [en]     |
| Open Multilingual Wordnet  | `omw` | `1.3`          | multiple [[mul]] |

[mul]: https://iso639-3.sil.org/code/mul

The Open Multilingual Wordnet installs the following lexicons (from
[here](https://github.com/bond-lab/omw-data/releases/tag/v1.3)) which
can also be downloaded and installed independently:

| Name                             | ID      | Versions   | Language |
| -------------------------------- | ------- | ---------- | -------- |
| Albanet                          | `alswn` | `1.3+omw`  | [als]    |
| Arabic WordNet (AWN v2)          | `arbwn` | `1.3+omw`  | [arb]    |
| BulTreeBank Wordnet (BTB-WN)     | `bulwn` | `1.3+omw`  | [bg]     |
| Chinese Open Wordnet             | `cmnwn` | `1.3+omw`  | [zh]     |
| Croatian Wordnet                 | `hrvwn` | `1.3+omw`  | [hr]     |
| DanNet                           | `danwn` | `1.3+omw`  | [da]     |
| FinnWordNet                      | `finwn` | `1.3+omw`  | [fi]     |
| Greek Wordnet                    | `ellwn` | `1.3+omw`  | [el]     |
| Hebrew Wordnet                   | `hebwn` | `1.3+omw`  | [he]     |
| IceWordNet                       | `islwn` | `1.3+omw`  | [is]     |
| Italian Wordnet                  | `iwn`   | `1.3+omw`  | [it]     |
| Japanese Wordnet                 | `jpnwn` | `1.3+omw`  | [jp]     |
| Lithuanian  WordNet              | `litwn` | `1.3+omw`  | [lt]     |
| Multilingual Central Repository  | `catwn` | `1.3+omw`  | [ca]     |
| Multilingual Central Repository  | `euswn` | `1.3+omw`  | [es]     |
| Multilingual Central Repository  | `glgwn` | `1.3+omw`  | [eu]     |
| Multilingual Central Repository  | `spawn` | `1.3+omw`  | [gl]     |
| MultiWordNet                     | `itawn` | `1.3+omw`  | [it]     |
| Norwegian Wordnet                | `nnown` | `1.3+omw`  | [nb]     |
| Norwegian Wordnet                | `nobwn` | `1.3+omw`  | [nn]     |
| Open Dutch WordNet               | `nldwn` | `1.3+omw`  | [nl]     |
| OpenWN-PT                        | `porwn` | `1.3+omw`  | [pt]     |
| plWordNet                        | `polwn` | `1.3+omw`  | [pl]     |
| Romanian Wordnet                 | `ronwn` | `1.3+omw`  | [ro]     |
| Slovak WordNet                   | `slkwn` | `1.3+omw`  | [sk]     |
| sloWNet                          | `slvwn` | `1.3+omw`  | [sl]     |
| Swedish (SALDO)                  | `swewn` | `1.3+omw`  | [sv]     |
| Thai Wordnet                     | `thawn` | `1.3+omw`  | [th]     |
| WOLF (Wordnet Libre du Français) | `frawn` | `1.3+omw`  | [fr]     |
| Wordnet Bahasa                   | `indwn` | `1.3+omw`  | [id]     |
| Wordnet Bahasa                   | `zsmwn` | `1.3+omw`  | [zsm]    |

The project index list is defined in [wn/index.toml](wn/index.toml).

## Migrating from the NLTK's wordnet Module

Some operations keep a compatible API with the NLTK's `wordnet`
module, but most will need some translation.

| Operation                   | `nltk.corpus.wordnet as wn`   | `pwn = wn.Wordnet('pwn', '3.0')` |
| --------------------------- | ----------------------------- | -------------------------------- |
| Lookup Synsets by word form | `wn.synsets("chat")`          | `pwn.synsets("chat")`            |
|                             | `wn.synsets("chat", pos="v")` | `pwn.synsets("chat", pos="v")`   |
| Lookup Synsets by POS       | `wn.all_synsets(pos="v")`     | `pwn.synsets(pos="v")`           |

(this table is incomplete)
