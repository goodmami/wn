# Change Log

## [Unreleased][unreleased]


## [v0.9.5]

**Release date: 2023-12-05**

### Python Support

* Removed support for Python 3.7 ([#191])
* Added support for Python 3.12 ([#191])

### Index

* Added `oewn:2023` ([#194])


## [v0.9.4]

**Release date: 2023-05-07**

### Index

* Added `oewn:2022` ([#181])


## [v0.9.3]

**Release date: 2022-11-13**

### Python Support

* Removed support for Python 3.6
* Added support for Python 3.11

### Fixed

* `wn.Synset.relations()` no longer raises a `KeyError` when no
  relation types are given and relations are found via ILI ([#177])


## [v0.9.2]

**Release date: 2022-10-02**

### Provisional Changes

* The `editor` installation extra installs the `wn-editor`
  package. This is not a normal way of using extras, as it installs a
  dependent and not a dependency, and may be removed. ([#17])

### Fixed

* `wn.download()` no longer uses Python features unavailable in 3.7
  when recovering from download errors
* `Sense.synset()` now creates a `Synset` properly linked to the same
  `Wordnet` object ([#157], [#168])
* `Sense.word()` now creates a `Word` properly linked to the same
  `Wordnet` object ([#157])
* `Synset.relations()` uses the correct relation type for those
  obtained from expand lexicons ([#169])


## [v0.9.1]

**Release date: 2021-11-23**

### Fixed

* Correctly add syntactic behaviours for WN-LMF 1.1 lexicons ([#156])


## [v0.9.0]

**Release date: 2021-11-17**

### Added

* `wn.constants.REVERSE_RELATIONS`
* `wn.validate` module ([#143])
* `validate` subcommand ([#143])
* `wn.Lexicon.describe()` ([#144])
* `wn.Wordnet.describe()` ([#144])
* `wn.ConfigurationError`
* `wn.ProjectError`

### Fixed

* WN-LMF 1.0 Syntactic Behaviours with no `senses` are now assigned to
  all senses in the lexical entry. If a WN-LMF 1.1 lexicon extension
  puts Syntactic Behaviour elements on lexical entries (which it
  shouldn't) it will only be assigned to senses and external senses
  listed.
* `wn.Form` now always hashes like `str`, so things like
  `set.__contains__` works as expected.
* `wn.download()` raises an exception on bad responses ([#147]])
* Avoid returning duplicate matches when a lemmatizer is used ([#154])

### Removed

* `wn.lmf.dump()` no longer has the `version` parameter

### Changed

* `wn.lmf.load()`
  - returns a dictionary for the resource instead of a
    list of lexicons, now including the WN-LMF version, as below:
    ```python
    {
        'lmf_version': '...',
        'lexicons': [...]
    }
    ```
  - returned lexicons are modeled with Python lists and dicts instead
    of custom classes ([#80])
* `wn.lmf.scan_lexicons()` only returns info about present lexicons,
  not element counts ([#113])
* Improper configurations (e.g., invalid data directory, malformed
  index) now raise a `wn.ConfigurationError`
* Attempting to get an unknown project or version now raises
  `wn.ProjectError` instead of `wn.Error` or `KeyError`
* Projects and versions in the index now take an `error` key. Calling
  `wn.config.get_project_info()` on such an entry will raise
  `wn.ProjectError`. Such entries may not also specify a url. The
  entry can still be viewed without triggering the error via
  `wn.config.index`. ([#146])
* Project versions in the index may specify multiple, space-separated
  URLs on the url key. If one fails, the next will be attempted when
  downloading. ([#142])
* `wn.config.get_project_info()` now returns a `resource_urls` key
  mapped to a list of URLs instead of `resource_url` mapped to a
  single URL. ([#142])
* `wn.config.get_cache_path()` now only accepts URL arguments
* The `lexicon` parameter in many functions now allows glob patterns
  like `omw-*:1.4` ([#155])

### Index

* Added `oewn:2021` new ID, previously `ewn` ([#152])
* Added `own`, `own-pt`, and `own-en` ([#97])
* Added `odenet:1.4`
* Added `omw:1.4`, including `omw-en`, formerly `pwn:3.0` ([#152])
* Added `omw-en31:1.4`, formerly `pwn:3.1` ([#152])
* Removed `omw:1.3`, `pwn:3.0`, and `pwn:3.1` ([#152])
* Added `kurdnet:1.0` ([#140])


## [v0.8.3]

**Release date: 2021-11-03**

### Fixed

* `wn.lmf` now serialized DC and non-DC metadata correctly ([#148])


## [v0.8.2]

**Release date: 2021-11-01**

This release only resolves some dependency issues with the previous
release.


## [v0.8.1]

**Release date: 2021-10-29**

Note: the release on PyPI was yanked because a dependency was not
specified properly.

### Fixed

* `wn.lmf` uses `https://` for the `dc` namespace instead of
  `http://`, following the DTD


## [v0.8.0]

**Release date: 2021-07-07**

### Added

* `wn.ic` module ([#40]
* `wn.taxonomy` module ([#125])
* `wn.similarity.res` Resnik similarity ([#122])
* `wn.similarity.jcn` Jiang-Conrath similarity ([#123])
* `wn.similarity.lin` Lin similarity ([#124])
* `wn.util.synset_id_formatter` ([#119])

### Changed

* Taxonomy methods on `wn.Synset` are moved to `wn.taxonomy`, but
  shortcut methods remain for compatibility ([#125]).
* Similarity metrics in `wn.similarity` now raise an error when
  synsets come from different parts of speech.


## [v0.7.0]

**Release date: 2021-06-09**

### Added

* Support for approximate word searches; on by default, configurable
  only by instantiating a `wn.Wordnet` object ([#105])
* `wn.morphy` ([#19])
* `wn.Wordnet.lemmatizer` attribute ([#8])
* `wn.web` ([#116])
* `wn.Sense.relations()` ([#82])
* `wn.Synset.relations()` ([#82])

### Changed

* `wn.lmf.load()` now takes a `progress_handler` parameter ([#46])
* `wn.lmf.scan_lexicons()` no longer returns sets of relation types or
  lexfiles; `wn.add()` now gets these from loaded lexicons instead
* `wn.util.ProgressHandler`
  - Now has a `refresh_interval` parameter; updates only trigger a
    refresh after the counter hits the threshold set by the interval
  - The `update()` method now takes a `force` parameter to trigger a
    refresh regardless of the refresh interval
* `wn.Wordnet`
  - Initialization now takes a `normalizer` parameter ([#105])
  - Initialization now takes a `lemmatizer` parameter ([#8])
  - Initialization now takes a `search_all_forms` parameter ([#115])
  - `Wordnet.words()`, `Wordnet.senses()` and `Wordnet.synsets()` now
    use any specified lemmatization or normalization functions to
    expand queries on word forms ([#105])

### Fixed

* `wn.Synset.ili` for proposed ILIs now works again (#117)


## [v0.6.2]

**Release date: 2021-03-22**

### Fixed

* Disable `sqlite3` progress reporting after `wn.remove()` ([#108])


## [v0.6.1]

**Release date: 2021-03-05**

### Added

* `wn.DatabaseError` as a more specific error type for schema changes
  ([#106])


## [v0.6.0]

**Release date: 2021-03-04**

**Notice:** This release introduces backwards-incompatible changes to
the schema that require users upgrading from previous versions to
rebuild their database.

### Added

* For WN-LMF 1.0 support ([#65])
  - `wn.Sense.frames()`
  - `wn.Sense.adjposition()`
  - `wn.Tag`
  - `wn.Form.tags()`
  - `wn.Count`
  - `wn.Sense.counts()`
* For ILI modeling ([#23])
  - `wn.ILI` class
  - `wn.Wordnet.ili()`
  - `wn.Wordnet.ilis()`
  - `wn.ili()`
  - `wn.ilis()`
  - `wn.project.Package.type` property
  - Index entries of different types; default is `'wordnet'`, `'ili'`
    is also available
  - Support for detecting and loading ILI tab-separated-value exports;
    not directly accessible through the public API at this time
  - Support for adding ILI resources to the database
  - A CILI index entry ([#23])
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
  - New relations
* Other WN-LMF 1.1 support
  - `wn.Lexicon.requires()`
  - `wn.Lexicon.extends()` ([#99])
  - `wn.Lexicon.extensions()` ([#99])
  - `wn.Pronunciation` ([#7])
  - `wn.Form.pronunciations()` ([#7])
  - `wn.Form.id` ([#7])
  - `wn.Synset.lexfile()`
* `wn.constants.SENSE_SYNSET_RELATIONS`
* `wn.WnWarning` (related to [#92])
* `wn.Lexicon.modified()` ([#17])

### Fixed

* Adding a wordnet with sense relations with invalid target IDs now
  raises an error instead of ignoring the relation.
* Detect LMF-vs-CILI projects even when files are uncompressed ([#104])

### Changed

* WN-LMF 1.0 entities now modeled and exported to XML ([#65]):
  - Syntactic behaviour ([#65])
  - Adjpositions ([#65])
  - Form tags
  - Sense counts
  - Definition source senses
  - ILI definitions
* WN-LMF 1.1 entities now modeled and exported to XML ([#89]):
  - Lexicon requirements and extensions ([#99])
  - Form pronunciations
  - Lexicographer files via the `lexfile` attribute
  - Form ids
* `wn.Synset.ili` now returns an `ILI` object
* `wn.remove()` now takes a `progess_handler` parameter
* `wn.util.ProgressBar` uses a simpler formatting string with two new
  computed variables
* `wn.project.is_package_directory()` and
  `wn.project.is_collection_directory()` now detect
  packages/collection with ILI resource files ([#23])
* `wn.project.iterpackages()` now includes ILI packages
* `wn.Wordnet` now sets the default `expand` value to a lexicon's
  dependencies if they are specified (related to [#92])

### Schema

* General changes:
  - Parts of speech are stored as text
  - Added indexes and `ON DELETE` actions to speed up `wn.remove()`
  - All extendable tables are now linked to their lexicon ([#91])
  - Added rowid to tables with metadata
  - Preemptively added a `modified` column to `lexicons` table ([#17])
  - Preemptively added a `normalized_form` column to `forms` ([#105])
  - Relation type tables are combined for synsets and senses ([#75])
* ILI-related changes ([#23]):
  - ILIs now have an integer rowid and a status
  - Proposed ILIs also have an integer rowid for metadata access
  - Added a table for ILI statuses
* WN-LMF 1.0 changes ([#65]):
  - SyntacticBehaviour (previously unused) no longer requires an ID and
    does not use it in the primary key
  - Added table for adjposition values
  - Added source-sense to definitions table
* WN-LMF 1.1 changes ([#7], [#89]):
  - Added a table for lexicon dependencies
  - Added a table for lexicon extensions ([#99])
  - Added `logo` column to `lexicons` table
  - Added a `synset_rank` column to `senses` table
  - Added a `pronunciations` table
  - Added column for lexicographer files to the `synsets` table
  - Added a table for lexicographer file names
  - Added an `id` column to `forms` table


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


[v0.9.5]: ../../releases/tag/v0.9.5
[v0.9.4]: ../../releases/tag/v0.9.4
[v0.9.3]: ../../releases/tag/v0.9.3
[v0.9.2]: ../../releases/tag/v0.9.2
[v0.9.1]: ../../releases/tag/v0.9.1
[v0.9.0]: ../../releases/tag/v0.9.0
[v0.8.3]: ../../releases/tag/v0.8.3
[v0.8.2]: ../../releases/tag/v0.8.2
[v0.8.1]: ../../releases/tag/v0.8.1
[v0.8.0]: ../../releases/tag/v0.8.0
[v0.7.0]: ../../releases/tag/v0.7.0
[v0.6.2]: ../../releases/tag/v0.6.2
[v0.6.1]: ../../releases/tag/v0.6.1
[v0.6.0]: ../../releases/tag/v0.6.0
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
[#8]: https://github.com/goodmami/wn/issues/8
[#15]: https://github.com/goodmami/wn/issues/15
[#17]: https://github.com/goodmami/wn/issues/17
[#19]: https://github.com/goodmami/wn/issues/19
[#23]: https://github.com/goodmami/wn/issues/23
[#40]: https://github.com/goodmami/wn/issues/40
[#46]: https://github.com/goodmami/wn/issues/46
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
[#80]: https://github.com/goodmami/wn/issues/80
[#81]: https://github.com/goodmami/wn/issues/81
[#82]: https://github.com/goodmami/wn/issues/82
[#83]: https://github.com/goodmami/wn/issues/83
[#86]: https://github.com/goodmami/wn/issues/86
[#87]: https://github.com/goodmami/wn/issues/87
[#89]: https://github.com/goodmami/wn/issues/89
[#90]: https://github.com/goodmami/wn/issues/90
[#91]: https://github.com/goodmami/wn/issues/91
[#92]: https://github.com/goodmami/wn/issues/92
[#93]: https://github.com/goodmami/wn/issues/93
[#95]: https://github.com/goodmami/wn/issues/95
[#97]: https://github.com/goodmami/wn/issues/97
[#99]: https://github.com/goodmami/wn/issues/99
[#104]: https://github.com/goodmami/wn/issues/104
[#105]: https://github.com/goodmami/wn/issues/105
[#106]: https://github.com/goodmami/wn/issues/106
[#108]: https://github.com/goodmami/wn/issues/108
[#113]: https://github.com/goodmami/wn/issues/113
[#115]: https://github.com/goodmami/wn/issues/115
[#116]: https://github.com/goodmami/wn/issues/116
[#117]: https://github.com/goodmami/wn/issues/117
[#119]: https://github.com/goodmami/wn/issues/119
[#122]: https://github.com/goodmami/wn/issues/122
[#123]: https://github.com/goodmami/wn/issues/123
[#124]: https://github.com/goodmami/wn/issues/124
[#125]: https://github.com/goodmami/wn/issues/125
[#140]: https://github.com/goodmami/wn/issues/140
[#142]: https://github.com/goodmami/wn/issues/142
[#143]: https://github.com/goodmami/wn/issues/143
[#144]: https://github.com/goodmami/wn/issues/144
[#146]: https://github.com/goodmami/wn/issues/146
[#147]: https://github.com/goodmami/wn/issues/147
[#148]: https://github.com/goodmami/wn/issues/148
[#152]: https://github.com/goodmami/wn/issues/152
[#154]: https://github.com/goodmami/wn/issues/154
[#155]: https://github.com/goodmami/wn/issues/155
[#156]: https://github.com/goodmami/wn/issues/156
[#157]: https://github.com/goodmami/wn/issues/157
[#168]: https://github.com/goodmami/wn/issues/168
[#169]: https://github.com/goodmami/wn/issues/169
[#177]: https://github.com/goodmami/wn/issues/177
[#181]: https://github.com/goodmami/wn/issues/181
[#191]: https://github.com/goodmami/wn/issues/191
[#194]: https://github.com/goodmami/wn/issues/194
