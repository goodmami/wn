

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
  |  <a href="https://github.com/goodmami/wn#citation">Citation</a>
</p>

---

Wn is a Python library for exploring information in wordnets.

## Installation

Install it from PyPI using **pip**:

```sh
pip install wn
```

or **uv**:

```
uv add wn
```

> [!IMPORTANT]
> Existing users of Wn may encounter an error about an incompatible database schema.
> The remedy is to rebuild the database. There is a new function to help with this:
> ```pycon
> >>> wn.reset_database(rebuild=True)  # re-add any indexed lexicons
> ```
> or
> ```pycon
> >>> wn.reset_database()  # initialize without re-adding; start from scratch
> ```

## Getting Started

First, download some data:

```sh
python -m wn download oewn:2025+  # the Open English WordNet 2025+
```

Now start exploring:

```python
>>> import wn
>>> en = wn.Wordnet('oewn:2025+')       # Create Wordnet object to query
>>> ss = en.synsets('win', pos='v')[0]  # Get the first synset for 'win'
>>> ss.definition()                     # Get the synset's definition
'be the winner in a contest or competition; be victorious'
```

## Features

- Multilingual by design; first-class support for wordnets in any language
- Interlingual queries via the [Collaborative Interlingual Index](https://github.com/globalwordnet/cili/)
- Six [similarity metrics](https://wn.readthedocs.io/en/latest/api/wn.similarity.html)
- Functions for [exploring taxonomies](https://wn.readthedocs.io/en/latest/api/wn.taxonomy.html)
- Support for [lemmatization] ([Morphy] for English is built-in) and unicode [normalization]
- Full support of the [WN-LMF 1.4](https://globalwordnet.github.io/schemas/) format, including word pronunciations and lexicon extensions
- SQL-based backend offers very fast startup and improved performance on many kinds of queries

[lemmatization]: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#lemmatization
[normalization]: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#normalization
[Morphy]: https://wn.readthedocs.io/en/latest/api/wn.morphy.html


## Available Wordnets

Any WN-LMF-formatted wordnet can be added to Wn's database from a local
file or remote URL, but Wn also maintains an index (see
[wn/index.toml](https://github.com/goodmami/wn/blob/main/wn/index.toml))
of available projects, similar to a package manager for software, to aid
in the discovery and downloading of new wordnets. The projects in this
index are listed below.

### English Wordnets

There are several English wordnets available. In general it is
recommended to use the latest [Open English Wordnet], but if you have
stricter compatibility needs for, e.g., experiment replicability, you
may try the [OMW English Wordnet based on WordNet 3.0] (compatible with
the Princeton WordNet 3.0 and with the [NLTK]), or [OpenWordnet-EN] (for
use with the Portuguese wordnet [OpenWordnet-PT]).

| Name                                         | Specifier              | # Synsets | Notes |
| -------------------------------------------- | ---------------------- | --------: | ----- |
| [Open English WordNet]                       | `oewn:2025+`<br/> `oewn:2025`</br> `oewn:2024`<br/> `oewn:2023`<br/> `oewn:2022`<br/> `oewn:2021`<br/> `ewn:2020`<br/> `ewn:2019` | 120564<br/>107519<br/>120630<br/>120135<br/>120068<br/>120039<br/>120053<br/>117791 | ← Recommended<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;<br/>&nbsp;<br/>&nbsp; |
| [OMW English Wordnet based on WordNet 1.5]   | `omw-en15:2.0`   | 91591 |  |
| [OMW English Wordnet based on WordNet 1.6]   | `omw-en16:2.0`   | 99642 |  |
| [OMW English Wordnet based on WordNet 1.7]   | `omw-en17:2.0`   | 109377 |  |
| [OMW English Wordnet based on WordNet 1.7.1] | `omw-en171:2.0`  | 111223 |  |
| [OMW English Wordnet based on WordNet 2.0]   | `omw-en20:2.0`   | 115424 |  |
| [OMW English Wordnet based on WordNet 2.1]   | `omw-en21:2.0`   | 117597 |  |
| [OMW English Wordnet based on WordNet 3.0]   | `omw-en:2.0`</br> `omw-en:1.4` | 117659</br> 117659 | Included with `omw:2.0`<br/> Included with `omw:1.4` |
| [OMW English Wordnet based on WordNet 3.1]   | `omw-en31:2.0`</br> `omw-en31:1.4` | 117791</br> 117791 |  |
| [OpenWordnet-EN]                             | `own-en:1.0.0`   | 117659 | Included with `own:1.0.0` |

[Open English WordNet]: https://en-word.net
[Open Multilingual Wordnet]: https://github.com/omwn
[OMW English Wordnet based on WordNet 1.5]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 1.6]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 1.7]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 1.7.1]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 2.0]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 2.1]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 3.0]: https://github.com/omwn/omw-data
[OMW English Wordnet based on WordNet 3.1]: https://github.com/omwn/omw-data
[OpenWordnet-EN]: https://github.com/own-pt/openWordnet-PT
[OpenWordnet-PT]: https://github.com/own-pt/openWordnet-PT
[NLTK]: https://www.nltk.org/

### Other Wordnets and Collections

These are standalone non-English wordnets and collections. The wordnets
of each collection are listed further down.

| Name                                       | Specifier                     | # Synsets       | Language         |
| ------------------------------------------ | ----------------------------- | --------------: | ---------------- |
| [Open Multilingual Wordnet]                | `omw:1.4`                     | n/a             | multiple [[mul]] |
| [Open German WordNet]                      | `odenet:1.4`<br/>`odenet:1.3` | 36268<br/>36159 | German [de]      |
| [Open Wordnets for Portuguese and English] | `own:1.0.0`                   | n/a             | multiple [[mul]] |
| [KurdNet]                                  | `kurdnet:1.0`                 |            2144 | Kurdish [ckb]    |

[Open English WordNet]: https://github.com/globalwordnet/english-wordnet
[Open Multilingual Wordnet]: https://github.com/omwn
[OMW English Wordnet based on WordNet 3.0]: https://github.com/omwn
[OMW English Wordnet based on WordNet 3.1]: https://github.com/omwn
[Open German WordNet]: https://github.com/hdaSprachtechnologie/odenet
[Open Wordnets for Portuguese and English]: https://github.com/own-pt
[mul]: https://iso639-3.sil.org/code/mul
[KurdNet]: https://sinaahmadi.github.io/resources/kurdnet.html

### Open Multilingual Wordnet (OMW) Collection

The *Open Multilingual Wordnet* collection (`omw:1.4`) installs the
following lexicons (from
[here](https://github.com/omwn/omw-data/releases/tag/v1.4)) which can
also be downloaded and installed independently:

| Name                                     | Specifier                        | # Synsets          | Language                         |
| ---------------------------------------- | -------------------------------- | -----------------: | -------------------------------- |
| Albanet                                  | `omw-sq:2.0`<br/> `omw-sq:1.4`   |     4679<br/> 4675 | Albanian [sq]                    |
| Arabic WordNet (AWN v2)                  | `omw-arb:2.0`<br/> `omw-arb:1.4` |     9916<br/> 9916 | Arabic [arb]                     |
| BulTreeBank Wordnet (BTB-WN)             | `omw-bg:2.0`<br/> `omw-bg:1.4`   |     4959<br/> 4959 | Bulgarian [bg]                   |
| Chinese Open Wordnet                     | `omw-cmn:2.0`<br/> `omw-cmn:1.4` |   42300<br/> 42312 | Mandarin (Simplified) [cmn-Hans] |
| Croatian Wordnet                         | `omw-hr:2.0`<br/> `omw-hr:1.4`   |   23115<br/> 23120 | Croatian [hr]                    |
| DanNet                                   | `omw-da:2.0`<br/> `omw-da:1.4`   |     4476<br/> 4476 | Danish [da]                      |
| FinnWordNet                              | `omw-fi:2.0`<br/> `omw-fi:1.4`   | 116763<br/> 116763 | Finnish [fi]                     |
| Greek Wordnet                            | `omw-el:2.0`<br/> `omw-el:1.4`   |   18113<br/> 18049 | Greek [el]                       |
| Hebrew Wordnet                           | `omw-he:2.0`<br/> `omw-he:1.4`   |     5448<br/> 5448 | Hebrew [he]                      |
| IceWordNet                               | `omw-is:2.0`<br/> `omw-is:1.4`   |     4951<br/> 4951 | Icelandic [is]                   |
| Italian Wordnet                          | `omw-iwn:2.0`<br/> `omw-iwn:1.4` |   15563<br/> 15563 | Italian [it]                     |
| Japanese Wordnet                         | `omw-ja:2.0`<br/> `omw-ja:1.4`   |  117659<br/> 57184 | Japanese [ja]                    |
| Lithuanian  WordNet                      | `omw-lt:2.0`<br/> `omw-lt:1.4`   |     9462<br/> 9462 | Lithuanian [lt]                  |
| Multilingual Central Repository          | `omw-ca:2.0`<br/> `omw-ca:1.4`   |   60765<br/> 45826 | Catalan [ca]                     |
| Multilingual Central Repository          | `omw-eu:2.0`<br/> `omw-eu:1.4`   |   29420<br/> 29413 | Basque [eu]                      |
| Multilingual Central Repository          | `omw-gl:2.0`<br/> `omw-gl:1.4`   |   34776<br/> 19312 | Galician [gl]                    |
| Multilingual Central Repository          | `omw-es:2.0`<br/> `omw-es:1.4`   |   78948<br/> 38512 | Spanish [es]                     |
| MultiWordNet                             | `omw-it:2.0`<br/> `omw-it:1.4`   |   35001<br/> 35001 | Italian [it]                     |
| Norwegian Wordnet                        | `omw-nb:2.0`<br/> `omw-nb:1.4`   |     4455<br/> 4455 | Norwegian (Bokmål) [nb]          |
| Norwegian Wordnet                        | `omw-nn:2.0`<br/> `omw-nn:1.4`   |     3671<br/> 3671 | Norwegian (Nynorsk) [nn]         |
| OMW English Wordnet based on WordNet 3.0 | `omw-en:2.0`<br/> `omw-en:1.4`   | 117659<br/> 117659 | English [en]                     |
| Open Dutch WordNet                       | `omw-nl:2.0`<br/> `omw-nl:1.4`   |   30177<br/> 30177 | Dutch [nl]                       |
| OpenWN-PT                                | `omw-pt:2.0`<br/> `omw-pt:1.4`   |   43895<br/> 43895 | Portuguese [pt]                  |
| plWordNet                                | `omw-pl:2.0`<br/> `omw-pl:1.4`   |   33826<br/> 33826 | Polish [pl]                      |
| Romanian Wordnet                         | `omw-ro:2.0`<br/> `omw-ro:1.4`   |   58754<br/> 56026 | Romanian [ro]                    |
| Slovak WordNet                           | `omw-sk:2.0`<br/> `omw-sk:1.4`   |   18507<br/> 18507 | Slovak [sk]                      |
| sloWNet                                  | `omw-sl:2.0`<br/> `omw-sl:1.4`   |   42590<br/> 42583 | Slovenian [sl]                   |
| Swedish (SALDO)                          | `omw-sv:2.0`<br/> `omw-sv:1.4`   |     6796<br/> 6796 | Swedish [sv]                     |
| Thai Wordnet                             | `omw-th:2.0`<br/> `omw-th:1.4`   |   73350<br/> 73350 | Thai [th]                        |
| WOLF (Wordnet Libre du Français)         | `omw-fr:2.0`<br/> `omw-fr:1.4`   |   59091<br/> 59091 | French [fr]                      |
| Wordnet Bahasa                           | `omw-id:2.0`<br/> `omw-id:1.4`   |   46774<br/> 38085 | Indonesian [id]                  |
| Wordnet Bahasa                           | `omw-zsm:2.0`<br/> `omw-zsm:1.4` |   36911<br/> 36911 | Malaysian [zsm]                  |

### Open Wordnet (OWN) Collection

The *Open Wordnets for Portuguese and English* collection (`own:1.0.0`)
installs the following lexicons (from
[here](https://github.com/own-pt/openWordnet-PT/releases/tag/v1.0.0))
which can also be downloaded and installed independently:

| Name           | Specifier      | # Synsets | Language        |
| -------------- | -------------- | --------: | --------------- |
| OpenWordnet-PT | `own-pt:1.0.0` |     52670 | Portuguese [pt] |
| OpenWordnet-EN | `own-en:1.0.0` |    117659 | English [en]    |

### Collaborative Interlingual Index

While not a wordnet, the [Collaborative Interlingual Index] (CILI)
represents the interlingual backbone of many wordnets. Wn, including
interlingual queries, will function without CILI loaded, but adding it
to the database makes available the full list of concepts, their status
(active, deprecated, etc.), and their definitions.

| Name                               | Specifier  | # Concepts |
| ---------------------------------- | ---------- | ---------: |
| [Collaborative Interlingual Index] | `cili:1.0` |     117659 |

[Collaborative Interlingual Index]: https://github.com/globalwordnet/cili/


## Changes to the Index

### `ewn` → `oewn`

The 2021 version of the *Open English WordNet* (`oewn:2021`) has
changed its lexicon ID from `ewn` to `oewn`, so the index is updated
accordingly. The previous versions are still available as `ewn:2019`
and `ewn:2020`.

### `pwn` → `omw-en`, `omw-en31`

The wordnet formerly called the *Princeton WordNet* (`pwn:3.0`,
`pwn:3.1`) is now called the *OMW English Wordnet based on WordNet
3.0* (`omw-en`) and the *OMW English Wordnet based on WordNet 3.1*
(`omw-en31`). This is more accurate, as it is a OMW-produced
derivative of the original WordNet data, and it also avoids license or
trademark issues.

### `*wn` → `omw-*` for OMW wordnets

All OMW wordnets have changed their ID scheme from `...wn` to `omw-..` and the version no longer
includes `+omw` (e.g., `bulwn:1.3+omw` is now `omw-bg:1.4`).

## Citation
Michael Wayne Goodman and Francis Bond. 2021. [Intrinsically Interlingual: The Wn Python Library for Wordnets](https://aclanthology.org/2021.gwc-1.12/) In *Proceedings of the 11th Global Wordnet Conference*, pages 100–107, University of South Africa (UNISA). Global Wordnet Association.
