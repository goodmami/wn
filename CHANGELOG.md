# Change Log

## [Unreleased]

### Added

* `add` parameter to `wn.download()` ([#73])
* `--no-add` option to `wn download` command ([#73])
* `progress_handler` parameter to `wn.download()` ([#70])
* `progress_handler` parameter to `wn.add()` ([#70])

### Fixed

* `Synset.shortest_path()` no longer includes starting node ([#63])
* `Synset.closure()`/`Sense.closure()` may take multiple relations
  ([#74])

### Changed

* Renamed `lgcode` parameter to `lang` throughout ([#66])
* Renamed `Wordnet.lgcode` property to `Wordnet.lang` ([#66])
* Renamed `--lgcode` command-line option to `--lang` ([#66])


## [v0.2.0]

**Release date: 2020-12-02**

### Added

* `wn.config.get_cache_path()` returns the path of a cached resource
* `wn.projects()` returns the info about known projects ([#60])
* `projects` subcommand to command-line interface ([#60])
* Open German WordNet 1.3 to the index

### Changed

* On import, Wn now raises an error if the database has an outdated
  schema ([#61])
* `wn.config.get_project_info()` now includes a `cache` key
* Output of `lexicons` CLI subcommand now tab-delimited


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

[v0.2.0]: ../../releases/tag/v0.2.0
[v0.1.1]: ../../releases/tag/v0.1.1
[v0.1.0]: ../../releases/tag/v0.1.0
[unreleased]: ../../tree/main

[#47]: https://github.com/goodmami/wn/issues/47
[#58]: https://github.com/goodmami/wn/issues/58
[#60]: https://github.com/goodmami/wn/issues/60
[#61]: https://github.com/goodmami/wn/issues/61
[#63]: https://github.com/goodmami/wn/issues/63
[#66]: https://github.com/goodmami/wn/issues/66
[#70]: https://github.com/goodmami/wn/issues/70
[#73]: https://github.com/goodmami/wn/issues/73
[#74]: https://github.com/goodmami/wn/issues/74
