

<p align="center">
  <img src="https://raw.githubusercontent.com/goodmami/wn/main/docs/_static/wn-logo.svg" alt="Wn logo">
  <br>
  <strong>a Python library for wordnets</strong>
  <br>
  <a href="https://pypi.org/project/wn/"><img src="https://img.shields.io/pypi/v/wn.svg?style=flat-square" alt="PyPI link"></a>
  <img src="https://img.shields.io/pypi/pyversions/wn.svg?style=flat-square" alt="Python Support">
  <a href="https://github.com/goodmami/wn/actions?query=workflow%3A%22tests%22"><img src="https://github.com/goodmami/wn/workflows/tests/badge.svg" alt="tests"></a>
  <a href="https://wn.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/wn/badge/?version=latest&style=flat-square" alt="Documentation Status"></a>
  <br>
  <a href="https://github.com/goodmami/wn#available-wordnets">Available Wordnets</a>
  | <a href="https://wn.readthedocs.io/">Documentation</a>
  | <a href="https://wn.readthedocs.io/en/latest/faq.html">FAQ</a>
  | <a href="https://wn.readthedocs.io/en/latest/guides/nltk-migration.html">Migrating from NLTK</a>
  | <a href="https://github.com/goodmami/wn/projects">Roadmap</a>
</p>

---

Wn is a Python library for exploring information in wordnets. Install
it from PyPI:

```console
$ pip install wn
```

Then download some data and start exploring:

```python
>>> import wn
>>> wn.download('ewn:2020')    # Install the English WordNet 2020 (only once)
Download complete (13643357 bytes)
Added ewn:2020 (English WordNet)
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
>>> import wn
>>> wn.synsets('chat')                      # all installed wordnets
>>> wn.synsets('chat', lang='en')           # limit to one language
>>> wn.synsets('chat', lexicon='ewn:2020')  # limit to one wordnet
```

## Available Wordnets

The following wordnets are indexed by Wn and ready to be installed:

| Name                        | ID       | Versions       | Language         |
| --------------------------- | -------- | -------------- | ---------------- |
| [Open English WordNet]      | `ewn`    | `2019`, `2020` | English [en]     |
| [Princeton WordNet]         | `pwn`    | `3.0`, `3.1`   | English [en]     |
| [Open Multilingual Wordnet] | `omw`    | `1.3`          | multiple [[mul]] |
| [Open German WordNet]       | `odenet` | `1.3`          | German [de]      |

[Open English WordNet]: https://github.com/globalwordnet/english-wordnet
[Princeton WordNet]: https://wordnet.princeton.edu/
[Open Multilingual Wordnet]: https://lr.soh.ntu.edu.sg/omw/omw
[Open German WordNet]: https://github.com/hdaSprachtechnologie/odenet
[mul]: https://iso639-3.sil.org/code/mul

The Open Multilingual Wordnet installs the following lexicons (from
[here](https://github.com/bond-lab/omw-data/releases/tag/v1.3)) which
can also be downloaded and installed independently:

| Name                             | ID      | Versions   | Language                   |
| -------------------------------- | ------- | ---------- | -------------------------- |
| Albanet                          | `alswn` | `1.3+omw`  | Albanian [als]             |
| Arabic WordNet (AWN v2)          | `arbwn` | `1.3+omw`  | Arabic [arb]               |
| BulTreeBank Wordnet (BTB-WN)     | `bulwn` | `1.3+omw`  | Bulgarian [bg]             |
| Chinese Open Wordnet             | `cmnwn` | `1.3+omw`  | Mandarin (Simplified) [zh] |
| Croatian Wordnet                 | `hrvwn` | `1.3+omw`  | Croatian [hr]              |
| DanNet                           | `danwn` | `1.3+omw`  | Danish [da]                |
| FinnWordNet                      | `finwn` | `1.3+omw`  | Finnish [fi]               |
| Greek Wordnet                    | `ellwn` | `1.3+omw`  | Greek [el]                 |
| Hebrew Wordnet                   | `hebwn` | `1.3+omw`  | Hebrew [he]                |
| IceWordNet                       | `islwn` | `1.3+omw`  | Icelandic [is]             |
| Italian Wordnet                  | `iwn`   | `1.3+omw`  | Italian [it]               |
| Japanese Wordnet                 | `jpnwn` | `1.3+omw`  | Japanese [jp]              |
| Lithuanian  WordNet              | `litwn` | `1.3+omw`  | Lithuanian [lt]            |
| Multilingual Central Repository  | `catwn` | `1.3+omw`  | Catalan [ca]               |
| Multilingual Central Repository  | `euswn` | `1.3+omw`  | Basque [eu]                |
| Multilingual Central Repository  | `glgwn` | `1.3+omw`  | Galician [gl]              |
| Multilingual Central Repository  | `spawn` | `1.3+omw`  | Spanish [es]               |
| MultiWordNet                     | `itawn` | `1.3+omw`  | Italian [it]               |
| Norwegian Wordnet                | `nobwn` | `1.3+omw`  | Norwegian (Bokmål) [nb]    |
| Norwegian Wordnet                | `nnown` | `1.3+omw`  | Norwegian (Nynorsk) [nn]   |
| Open Dutch WordNet               | `nldwn` | `1.3+omw`  | Dutch [nl]                 |
| OpenWN-PT                        | `porwn` | `1.3+omw`  | Portuguese [pt]            |
| plWordNet                        | `polwn` | `1.3+omw`  | Polish [pl]                |
| Romanian Wordnet                 | `ronwn` | `1.3+omw`  | Romanian [ro]              |
| Slovak WordNet                   | `slkwn` | `1.3+omw`  | Slovak [sk]                |
| sloWNet                          | `slvwn` | `1.3+omw`  | Slovenian [sl]             |
| Swedish (SALDO)                  | `swewn` | `1.3+omw`  | Swedish [sv]               |
| Thai Wordnet                     | `thawn` | `1.3+omw`  | Thai [th]                  |
| WOLF (Wordnet Libre du Français) | `frawn` | `1.3+omw`  | French [fr]                |
| Wordnet Bahasa                   | `indwn` | `1.3+omw`  | Indonesian [id]            |
| Wordnet Bahasa                   | `zsmwn` | `1.3+omw`  | Malaysian [zsm]            |

The project index list is defined in [wn/index.toml](https://github.com/goodmami/wn/blob/main/wn/index.toml).

