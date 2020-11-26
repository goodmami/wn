# Change Log

## [Unreleased]

### Fixed

* Cast `pathlib.Path` to `str` for `sqlite3.connect()` ([#58])
* Pass `lgcode` to `Wordnet` object in `wn.synset()`


## [v0.1.0]

**Release date: 2020-11-25**

This is the initial release of the new Wn library. On PyPI it replaces
the https://github.com/nltk/wordnet/ code which had been effectively
abandoned, but this is an entirely new codebase.

[v0.1.0]: ../../releases/tag/v0.1.0
[unreleased]: ../../tree/main

[#58]: https://github.com/goodmami/wn/issues/58
