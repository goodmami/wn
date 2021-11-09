

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
|                             | `oewn`   | `2021`         | English [en]     |
| [Open Multilingual Wordnet] | `omw`    | `1.4`          | multiple [[mul]] |
| [Open German WordNet]       | `odenet` | `1.3`, `1.4`   | German [de]      |

[Open English WordNet]: https://github.com/globalwordnet/english-wordnet
[Open Multilingual Wordnet]: https://lr.soh.ntu.edu.sg/omw/omw
[Open German WordNet]: https://github.com/hdaSprachtechnologie/odenet
[mul]: https://iso639-3.sil.org/code/mul

The Open Multilingual Wordnet installs the following lexicons (from
[here](https://github.com/bond-lab/omw-data/releases/tag/v1.3)) which
can also be downloaded and installed independently:

| Name                                     | ID         | Versions | Language                         |
| ---------------------------------------- | ---------- | -------- | -------------------------------- |
| Albanet                                  | `omw-sq`   | `1.4`    | Albanian [sq]                    |
| Arabic WordNet (AWN v2)                  | `omw-arb`  | `1.4`    | Arabic [arb]                     |
| BulTreeBank Wordnet (BTB-WN)             | `omw-bg`   | `1.4`    | Bulgarian [bg]                   |
| Chinese Open Wordnet                     | `omw-cmn`  | `1.4`    | Mandarin (Simplified) [cmn-Hans] |
| Croatian Wordnet                         | `omw-hr`   | `1.4`    | Croatian [hr]                    |
| DanNet                                   | `omw-da`   | `1.4`    | Danish [da]                      |
| FinnWordNet                              | `omw-fi`   | `1.4`    | Finnish [fi]                     |
| Greek Wordnet                            | `omw-el`   | `1.4`    | Greek [el]                       |
| Hebrew Wordnet                           | `omw-he`   | `1.4`    | Hebrew [he]                      |
| IceWordNet                               | `omw-is`   | `1.4`    | Icelandic [is]                   |
| Italian Wordnet                          | `omw-iwn`  | `1.4`    | Italian [it]                     |
| Japanese Wordnet                         | `omw-ja`   | `1.4`    | Japanese [ja]                    |
| Lithuanian  WordNet                      | `omw-lt`   | `1.4`    | Lithuanian [lt]                  |
| Multilingual Central Repository          | `omw-ca`   | `1.4`    | Catalan [ca]                     |
| Multilingual Central Repository          | `omw-eu`   | `1.4`    | Basque [eu]                      |
| Multilingual Central Repository          | `omw-gl`   | `1.4`    | Galician [gl]                    |
| Multilingual Central Repository          | `omw-es`   | `1.4`    | Spanish [es]                     |
| MultiWordNet                             | `omw-it`   | `1.4`    | Italian [it]                     |
| Norwegian Wordnet                        | `omw-nb`   | `1.4`    | Norwegian (Bokmål) [nb]          |
| Norwegian Wordnet                        | `omw-nn`   | `1.4`    | Norwegian (Nynorsk) [nn]         |
| OMW English Wordnet based on WordNet 3.0 | `omw-en`   | `1.4`    | English [en]                     |
| OMW English Wordnet based on WordNet 3.1 | `omw-en31` | `1.4`    | English [en]                     |
| Open Dutch WordNet                       | `omw-nl`   | `1.4`    | Dutch [nl]                       |
| OpenWN-PT                                | `omw-pt`   | `1.4`    | Portuguese [pt]                  |
| plWordNet                                | `omw-pl`   | `1.4`    | Polish [pl]                      |
| Romanian Wordnet                         | `omw-ro`   | `1.4`    | Romanian [ro]                    |
| Slovak WordNet                           | `omw-sk`   | `1.4`    | Slovak [sk]                      |
| sloWNet                                  | `omw-sl`   | `1.4`    | Slovenian [sl]                   |
| Swedish (SALDO)                          | `omw-sv`   | `1.4`    | Swedish [sv]                     |
| Thai Wordnet                             | `omw-th`   | `1.4`    | Thai [th]                        |
| WOLF (Wordnet Libre du Français)         | `omw-fr`   | `1.4`    | French [fr]                      |
| Wordnet Bahasa                           | `omw-id`   | `1.4`    | Indonesian [id]                  |
| Wordnet Bahasa                           | `omw-zsm`  | `1.4`    | Malaysian [zsm]                  |

The project index list is defined in [wn/index.toml](https://github.com/goodmami/wn/blob/main/wn/index.toml).

## Changes to the Index

### ewn → oewn

The 2021 version of the *Open English WordNet* (`oewn:2021`) has
changed its lexicon ID from `ewn` to `oewn`, so the index is updated
accordingly. The previous versions are still available as `ewn:2019`
and `ewn:2020`.

### pwn → omw-en, omw-en31

The wordnet formerly called the *Princeton WordNet* (`pwn:3.0`,
`pwn:3.1`) is now called the *OMW English Wordnet based on WordNet
3.0* (`omw-en`) and the *OMW English Wordnet based on WordNet 3.1*
(`omw-en31`). This is more accurate, as it is a OMW-produced
derivative of the original WordNet data, and it also avoids license or
trademark issues.

### `*wn` → `omw-*` for OMW wordnets

All OMW wordnets have changed their ID scheme from `*wn` (e.g.,
`bulwn`) to `omw-*` (e.g., `omw-bg`) and the version no longer
includes `+omw`.
