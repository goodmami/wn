# Change Log

## [Unreleased]

### Added

* `wn.constants.SENSE_SYNSET_RELATIONS`
* `wn.Sense.frames()` ([#65])
* `wn.Sense.adjposition()` ([#65])
* `wn.ILI` class ([#23])
* `wn.Wordnet.ili()` ([#23])
* `wn.Wordnet.ilis()` ([#23])
* `wn.ili()` ([#23])
* `wn.ilis()` ([#23])
* `wn.constants.ILI_STATUSES` ([#23])
* `wn.Pronunciation` ([#7])
* `wn.Form.pronunciations()` ([#7])
* `wn.Tag` ([#65])
* `wn.Form.id` ([#7])
* `wn.Form.tags()` ([#65])
* `wn.Count` ([#65])
* `wn.Sense.counts()` ([#65])
* Index entries of different types; default is `'wordnet'`, `'ili'` is
  also available ([#23])
* A CILI index entry ([#23])
* `wn.project.Package.type` property ([#23])
* Support for detecting and loading ILI tab-separated-value exports;
  not directly accessible through the public API at this time ([#23])
* Support for adding ILI resources to the database ([#23])
* `wn.Lexicon.modified()` ([#17])
* `wn.WnWarning` (related to [#92])
* `wn.Lexicon.requires()`
* `wn.Lexicon.extends()` ([#99])
* `wn.Lexicon.extensions()` ([#99])
* `wn.lmf` WN-LMF 1.1 support ([#7])
   - `<Requires>`
   - `<LexiconExtension>`, `<Extends>`, `<ExternalSynset>`,
     `<ExternalLexicalEntry>`, `<ExternalSense>`,
     `<ExternalLemma>`, `<ExternalForm>`
   - `subcat` on `<Sense>`
   - `members` on `<Synset>`
   - `lexfile` on `<Synset>`
   - `<Pronunciation>`
   - `id` on `<Form>`
* `wn.Synset.lexfile()`

### Fixed

* Adding a wordnet with sense relations with invalid target IDs now
  raises an error instead of ignoring the relation.
* Detect LMF-vs-CILI projects even when files are uncompressed ([#104])

### Changed

* Syntactic behaviour is now stored in the database, and exported to
  XML ([#65])
* Adjpositions are now stored in the database, and exported to XML ([#65])
* `wn.Synset.ili` now returns an `ILI` object
* `wn.remove()` now takes a `progess_handler` parameter
* `wn.util.ProgressBar` uses a simpler formatting string with two new
  computed variables
* Wordform tags are now stored in the database (the table was already
  present in the schema, just unused), and exported to XML ([#65])
* Sense counts are now stored in the database (the table was already
  present in the schema, just unused) and exported to XML ([#65])
* Syntactic Behaviours are now exported to XML ([#65])
* Definition source senses are now stored in the database and exported
  to XML ([#65])
* ILI definitions are now exported to XML ([#65])
* `wn.project.is_package_directory()` and
  `wn.project.is_collection_directory()` now detect
  packages/collection with ILI resource files ([#23])
* `wn.project.iterpackages()` now includes ILI packages
* `wn.Wordnet` now sets the default `expand` value to a lexicon's
  dependencies if they are specified (related to [#92])
* Lexicon requirements and extensions are now modeled by the database
  ([#89], [#99])
* Wordform pronunciations are now stored in the database and exported
  to XML ([#7])
* Lexicographer files via the `lexfile` attribute are now stored in
  the database and exported ([#7])
* Wordform ids are now stored in the database and exported to XML
  ([#7])
* Relation type tables are combined for synsets and senses ([#75])

### Schema

* Parts of speech are stored as text
* SyntacticBehaviour (previously unused) no longer requires an ID and
  does not use it in the primary key
* Added table for adjposition values ([#65])
* ILIs now have an integer rowid and a status ([#23])
* Proposed ILIs also have an integer rowid for metadata access
* Added more indexes and `ON DELETE` actions to speed up `wn.remove()`
* All extendable tables are now linked to their lexicon ([#91])
* Added rowid to tables with metadata
* Added source-sense to definitions table ([#65])
* Preemptively added a `modified` column to `lexicons` table ([#17])
* Added a table for lexicon dependencies ([#7], [#89])
* Added a table for lexicon extensions ([#99])
* Added `logo` column to `lexicons` table ([#89])
* Added a `synset_rank` column to `senses` table ([#89])
* Added a `pronunciations` table ([#89])
* Added `lexfile` column to `synsets` table ([#89])
* Added an `id` column to `forms` table ([#89])


## [v0.5.1]

**Release date: 2021-01-29**

### Fixed

* `wn.lmf` specifies `utf-8` when opening files ([#95])
* `wn.lmf.dump()` casts attribute values to strings


## [v0.5.0]

**Release date: 2021-01-28**

### Added

* `wn.Lexicon.specifier()`
* `wn.config.allow_multithreading` ([#86])
* `wn.util` module for public-API utilities
* `wn.util.ProgressHandler` ([#87])
* `wn.util.ProgressBar` ([#87])

### Removed

* `wn.Wordnet.lang`

### Changed

* `wn.Synset.get_related()` does same-lexicon traversals first, then
  ILI expansions ([#90])
* `wn.Synset.get_related()` only targets the source synset lexicon in
  default mode ([#90], [#92])
* `wn.Wordnet` has a "default mode", when no lexicon or language is
  selected, which searches any lexicon but relation traversals only
  target the lexicon of the source synset ([#92]) is used for the
  lexicon id ([#92])
* `wn.Wordnet` has an empty expand set when a lexicon or language is
  specified and no expand set is specified ([#92])
* `wn.Wordnet` now allows versions in lexicon specifiers when the id
  is `*` (e.g., `*:1.3+omw`)
* `wn.Wordnet` class signature has `lexicon` first, `lang` is
  keyword-only ([#93])
* `lang` and `lexicon` parameters are keyword-only on `wn.lexicons()`,
  `wn.word()`, `wn.words()`, `wn.sense()`, `wn.senses()`,
  `wn.synset()`, `wn.synsets()`, and the `translate()` methods of
  `wn.Word`, `wn.Sense`, and `wn.Synset` ([#93])


## [v0.4.1]

**Release date: 2021-01-19**

### Removed

* `wn.config.database_filename` (only `wn.config.data_directory` is
  configurable now)

### Changed

* Schema validation is now done when creating a new connection,
  instead of on import of `wn`
* One connection is shared per database path, rather than storing
  connections on the modeling classes ([#81])

### Fixed

* More robustly check for LMF validity ([#83])


## [v0.4.0]

**Release date: 2020-12-29**

### Added

* `wn.export()` to export lexicon(s) from the database ([#15])
* `wn.lmf.dump()` to dump WN-LMF lexicons to disk ([#15])
* `metadata` method on `wn.Word`, `wn.Sense`, and `wn.Synset`
* `lexicalized` method on `wn.Sense` and `wn.Synset`
* `wn.Form` class ([#79])
* `--verbose` / `-v` option for the command-line interface ([#71])

### Changed

* `wn.Lexicon.metadata` is now a method
* `wn.Word.lemma()` returns a `wn.Form` object ([#79])
* `wn.Word.forms()` returns a list of `wn.Form` objects ([#79])
* `wn.project.iterpackages()` raises `wn.Error` on decompression
  problems ([#77])
* `wn.lmf.LMFError` now inherits from `wn.Error`
* `wn.lmf.scan_lexicons()` raises `LMFError` on XML parsing errors
  ([#77])
* `wn.download()` reraises caught `wn.Error` with more informative
  message ([#77])
* `wn.add()` improve error message when lexicons are already added
  ([#77])
* Basic logging added for `wn.download()` and `wn.add()` ([#71])
* `Synset.get_related()` and `Sense.get_related()` may take a `'*'`
  parameter to get all relations
* `wn.Wordnet` objects keep an open connection to the database ([#81])

### Fixed

* `wn.projects.iterpackages()` tries harder to prevent potential race
  conditions when reading temporary files ([#76])
* `wn.Lexicon.metadata` now returns a dictionary ([#78])


## [v0.3.0]

**Release date: 2020-12-16**

### Added

* `add` parameter to `wn.download()` ([#73])
* `--no-add` option to `wn download` command ([#73])
* `progress_handler` parameter to `wn.download()` ([#70])
* `progress_handler` parameter to `wn.add()` ([#70])

### Fixed

* `Synset.shortest_path()` no longer includes starting node ([#63])
* `Synset.closure()`/`Sense.closure()` may take multiple relations
  ([#74])
* `Synset.hypernym_paths(simulate_root=True)` returns just the fake
  root node if no paths were found (related to [#64])
* `wn.lexicons()` returns empty list on unknown lang/lexicon ([#59])

### Changed

* Renamed `lgcode` parameter to `lang` throughout ([#66])
* Renamed `Wordnet.lgcode` property to `Wordnet.lang` ([#66])
* Renamed `--lgcode` command-line option to `--lang` ([#66])
* Use better-performing/less-safe database options when adding
  lexicons ([#69])


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


[v0.5.1]: ../../releases/tag/v0.5.1
[v0.5.0]: ../../releases/tag/v0.5.0
[v0.4.1]: ../../releases/tag/v0.4.1
[v0.4.0]: ../../releases/tag/v0.4.0
[v0.3.0]: ../../releases/tag/v0.3.0
[v0.2.0]: ../../releases/tag/v0.2.0
[v0.1.1]: ../../releases/tag/v0.1.1
[v0.1.0]: ../../releases/tag/v0.1.0
[unreleased]: ../../tree/main

[#7]: https://github.com/goodmami/wn/issues/7
[#15]: https://github.com/goodmami/wn/issues/15
[#17]: https://github.com/goodmami/wn/issues/17
[#23]: https://github.com/goodmami/wn/issues/23
[#47]: https://github.com/goodmami/wn/issues/47
[#58]: https://github.com/goodmami/wn/issues/58
[#59]: https://github.com/goodmami/wn/issues/59
[#60]: https://github.com/goodmami/wn/issues/60
[#61]: https://github.com/goodmami/wn/issues/61
[#63]: https://github.com/goodmami/wn/issues/63
[#64]: https://github.com/goodmami/wn/issues/64
[#65]: https://github.com/goodmami/wn/issues/65
[#66]: https://github.com/goodmami/wn/issues/66
[#69]: https://github.com/goodmami/wn/issues/69
[#70]: https://github.com/goodmami/wn/issues/70
[#71]: https://github.com/goodmami/wn/issues/71
[#73]: https://github.com/goodmami/wn/issues/73
[#74]: https://github.com/goodmami/wn/issues/74
[#75]: https://github.com/goodmami/wn/issues/75
[#76]: https://github.com/goodmami/wn/issues/76
[#77]: https://github.com/goodmami/wn/issues/77
[#78]: https://github.com/goodmami/wn/issues/78
[#79]: https://github.com/goodmami/wn/issues/79
[#81]: https://github.com/goodmami/wn/issues/81
[#83]: https://github.com/goodmami/wn/issues/83
[#86]: https://github.com/goodmami/wn/issues/86
[#87]: https://github.com/goodmami/wn/issues/87
[#89]: https://github.com/goodmami/wn/issues/89
[#90]: https://github.com/goodmami/wn/issues/90
[#91]: https://github.com/goodmami/wn/issues/91
[#92]: https://github.com/goodmami/wn/issues/92
[#93]: https://github.com/goodmami/wn/issues/93
[#95]: https://github.com/goodmami/wn/issues/95
[#99]: https://github.com/goodmami/wn/issues/99
[#104]: https://github.com/goodmami/wn/issues/104
