# Change Log

## [Unreleased]

### Added

* `wn.config.get_cache_path()` returns the path of a cached resource
* `wn.projects()` returns the info about known projects ([#60])

### Changed

* On import, Wn now raises an error if the database has an outdated
  schema ([#61])
* `wn.config.get_project_info()` now includes a `cache` key


## [v0.1.1]

**Release date: 2020-11-26**

### Added

* Command-line interface for downloading and listing lexicons ([#47])

### Fixed

* Cast `pathlib.Path` to `str` for `sqlite3.connect()` ([#58])
* Pass `lgcode` to `Wordnet` object in `wn.synset()`


## [v0.1.0]

**Release date: 2020-11-25**

This is the initial release of the new Wn library. On PyPI it replaces
the https://github.com/nltk/wordnet/ code which had been effectively
abandoned, but this is an entirely new codebase.

[v0.1.1]: ../../releases/tag/v0.1.1
[v0.1.0]: ../../releases/tag/v0.1.0
[unreleased]: ../../tree/main

[#47]: https://github.com/goodmami/wn/issues/47
[#58]: https://github.com/goodmami/wn/issues/58
[#60]: https://github.com/goodmami/wn/issues/60
[#61]: https://github.com/goodmami/wn/issues/61
