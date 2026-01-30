from collections.abc import Iterator, Sequence
from typing import Literal, NamedTuple, overload

from wn import lmf
from wn._exceptions import Error
from wn._lexicon import Lexicon
from wn._queries import (
    Form,
    Pronunciation,
    Sense,
    Tag,
    find_entries,
    find_proposed_ilis,
    find_senses,
    find_synsets,
    find_syntactic_behaviours,
    get_adjposition,
    get_definitions,
    get_entry_forms,
    get_entry_index,
    get_entry_senses,
    get_examples,
    get_lexfile,
    get_lexicalized,
    get_lexicon_dependencies,
    get_metadata,
    get_proposed_ili_metadata,
    get_relation_targets,
    get_sense_counts,
    get_sense_n,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_members,
    get_synset_relations,
)
from wn._types import AnyPath, VersionInfo
from wn._util import split_lexicon_specifier, version_info

PROPOSED_ILI_ID = "in"  # special case for proposed ILIs


def export(
    lexicons: Sequence[Lexicon], destination: AnyPath, version: str = "1.4"
) -> None:
    """Export lexicons from the database to a WN-LMF file.

    More than one lexicon may be exported in the same file, subject to
    these conditions:

    - identifiers on wordnet entities must be unique in all lexicons
    - lexicons extensions may not be exported with their dependents

    >>> w = wn.Wordnet(lexicon="omw-cmn:1.4 omw-zsm:1.4")
    >>> wn.export(w.lexicons(), "cmn-zsm.xml")

    Args:
        lexicons: sequence of :class:`wn.Lexicon` objects
        destination: path to the destination file
        version: LMF version string

    """
    _precheck(lexicons)
    exporter = _LMFExporter(version)
    resource: lmf.LexicalResource = {
        "lmf_version": version,
        "lexicons": [exporter.export(lexicon) for lexicon in lexicons],
    }
    lmf.dump(resource, destination)


def _precheck(lexicons: Sequence[Lexicon]) -> None:
    all_ids: set[str] = set()
    for lex in lexicons:
        lexspecs = (lex.specifier(),)
        idset = {lex.id}
        idset.update(row[0] for row in find_entries(lexicons=lexspecs))
        idset.update(row[0] for row in find_senses(lexicons=lexspecs))
        idset.update(row[0] for row in find_synsets(lexicons=lexspecs))
        # TODO: syntactic behaviours
        if all_ids.intersection(idset):
            raise Error("cannot export: non-unique identifiers in lexicons")
        all_ids |= idset


_SBMap = dict[str, list[tuple[str, str]]]


class _LexSpecs(NamedTuple):
    primary: str  # lexicon or lexicon extension being exported
    base: str  # base lexicon (when primary is an extension)


class _LMFExporter:
    version: VersionInfo
    # ids: set[str]
    # The following are reset for each lexicon that is exported
    lexspecs: _LexSpecs
    sbmap: _SBMap
    external_sense_ids: set[str]  # necessary external senses
    external_synset_ids: set[str]  # necessary external synsets

    def __init__(self, version: str) -> None:
        if version not in lmf.SUPPORTED_VERSIONS:
            raise Error(f"WN-LMF version not supported: {version}")
        self.version = version_info(version)
        self.lexspecs = _LexSpecs("", "")
        self.sbmap = {}
        self.external_sense_ids = set()
        self.external_synset_ids = set()

    def export(self, lexicon: Lexicon) -> lmf.Lexicon | lmf.LexiconExtension:
        base = lexicon.extends()

        self.lexspecs = _LexSpecs(lexicon.specifier(), base.specifier() if base else "")
        self.sbmap = _build_sbmap(self.lexspecs)

        if base is None:
            return self._lexicon(lexicon)
        else:
            self.external_sense_ids = _get_external_sense_ids(self.lexspecs)
            self.external_synset_ids = _get_external_synset_ids(self.lexspecs)
            return self._lexicon_extension(lexicon, base)

    def _lexicon(self, lexicon: Lexicon) -> lmf.Lexicon:
        lex = lmf.Lexicon(
            id=lexicon.id,
            label=lexicon.label,
            language=lexicon.language,
            email=lexicon.email,
            license=lexicon.license,
            version=lexicon.version,
            url=lexicon.url or "",
            citation=lexicon.citation or "",
            entries=list(self._entries(False)),
            synsets=list(self._synsets(False)),
            meta=lexicon.metadata(),
        )
        if self.version >= (1, 1):
            lex["logo"] = lexicon.logo or ""
            lex["requires"] = self._requires()
            lex["frames"] = self._syntactic_behaviours_1_1()

        return lex

    def _requires(self) -> list[lmf.Dependency]:
        dependencies: list[lmf.Dependency] = []
        for specifier, url, _ in get_lexicon_dependencies(self.lexspecs.primary):
            id, version = split_lexicon_specifier(specifier)
            dependencies.append(self._dependency(id, version, url))
        return dependencies

    def _dependency(self, id: str, version: str, url: str | None) -> lmf.Dependency:
        return lmf.Dependency(id=id, version=version, url=url)

    @overload
    def _entries(
        self, extension: Literal[True]
    ) -> Iterator[lmf.LexicalEntry | lmf.ExternalLexicalEntry]: ...

    @overload
    def _entries(self, extension: Literal[False]) -> Iterator[lmf.LexicalEntry]: ...

    def _entries(
        self, extension: Literal[True, False]
    ) -> Iterator[lmf.LexicalEntry | lmf.ExternalLexicalEntry]:
        lexspec = self.lexspecs.primary
        lexicons = self.lexspecs if extension else (lexspec,)
        for id, pos, lex in find_entries(lexicons=lexicons):
            if lex == lexspec:
                yield self._entry(id, pos)
            elif extension and (entry := self._ext_entry(id)):
                yield entry

    def _entry(self, id: str, pos: str) -> lmf.LexicalEntry:
        lexspec = self.lexspecs.primary
        lemma, forms = _get_entry_forms(id, self.lexspecs)
        index = get_entry_index(id, lexspec)
        entry = lmf.LexicalEntry(
            id=id,
            lemma=self._lemma(lemma, pos),
            forms=[self._form(form) for form in forms],
            index=index or "",
            senses=list(self._senses(id, index, False)),
            meta=self._metadata(id, "entries"),
        )
        if self.version < (1, 1):
            # cleanup 1.1+ features
            entry["lemma"].pop("pronunciations", None)
            for form in entry["forms"]:
                form.pop("pronunciations", None)
            # 1.0 has syntactic behaviours on each entry
            entry["frames"] = self._syntactic_behaviours_1_0(entry)
        if self.version < (1, 4) and index:
            entry.pop("index", None)
        return entry

    def _lemma(self, form: Form, pos: str) -> lmf.Lemma:
        return lmf.Lemma(
            writtenForm=form[0],
            partOfSpeech=pos,
            script=(form[2] or ""),
            pronunciations=self._pronunciations(form[4]),
            tags=self._tags(form[5]),
        )

    def _form(self, form: Form) -> lmf.Form:
        return lmf.Form(
            writtenForm=form[0],
            id=form[1] or "",
            script=form[2] or "",
            pronunciations=self._pronunciations(form[4]),
            tags=self._tags(form[5]),
        )

    def _pronunciations(self, prons: list[Pronunciation]) -> list[lmf.Pronunciation]:
        lexspec = self.lexspecs.primary
        return [
            lmf.Pronunciation(
                text=text,
                variety=variety or "",
                notation=notation or "",
                phonemic=phonemic,
                audio=audio or "",
            )
            for text, variety, notation, phonemic, audio, lex in prons
            if lex == lexspec
        ]

    def _tags(self, tags: list[Tag]) -> list[lmf.Tag]:
        lexspec = self.lexspecs.primary
        return [
            lmf.Tag(text=text, category=category)
            for text, category, lex in tags
            if lex == lexspec
        ]

    @overload
    def _senses(
        self, id: str, index: str | None, extension: Literal[True]
    ) -> Iterator[lmf.Sense | lmf.ExternalSense]: ...

    @overload
    def _senses(
        self, id: str, index: str | None, extension: Literal[False]
    ) -> Iterator[lmf.Sense]: ...

    def _senses(
        self, id: str, index: str | None, extension: Literal[True, False]
    ) -> Iterator[lmf.Sense | lmf.ExternalSense]:
        lexspec = self.lexspecs.primary
        lexicons = self.lexspecs if extension else (lexspec,)
        for i, sense in enumerate(get_entry_senses(id, lexicons, False), 1):
            sid, _, _, lex = sense
            if lex == lexspec:
                yield self._sense(sense, index, i)
            elif extension and (ext_sense := self._ext_sense(sid)):
                yield ext_sense

    def _sense(self, sense: Sense, index: str | None, i: int) -> lmf.Sense:
        id, _, synset_id, lexspec = sense
        lmf_sense = lmf.Sense(
            id=id,
            synset=synset_id,
            n=_get_sense_n(id, lexspec, index, i),
            relations=self._sense_relations(id),
            examples=self._examples(id, "senses"),
            counts=self._counts(id),
            meta=self._metadata(id, "senses"),
            lexicalized=get_lexicalized(id, lexspec, "senses"),
            adjposition=get_adjposition(id, lexspec) or "",
        )
        if self.version >= (1, 1) and id in self.sbmap:
            lmf_sense["subcat"] = sorted(sbid for sbid, _ in self.sbmap[id])
        return lmf_sense

    def _sense_relations(self, sense_id: str) -> list[lmf.Relation]:
        # only get relations defined for the primary lexicon, but the
        # relation target can be from a base lexicon
        lexicons = (self.lexspecs.primary,)
        relations: list[lmf.Relation] = [
            lmf.Relation(target=id, relType=type, meta=metadata)
            for type, _, metadata, id, *_ in get_sense_relations(
                sense_id, "*", lexicons, self.lexspecs
            )
        ]
        relations.extend(
            lmf.Relation(target=id, relType=type, meta=metadata)
            for type, _, metadata, _, id, *_ in get_sense_synset_relations(
                sense_id, "*", lexicons, self.lexspecs
            )
        )
        return relations

    def _examples(self, id: str, table: str) -> list[lmf.Example]:
        lexicons = (self.lexspecs.primary,)  # only for the lexicon being exported
        return [
            lmf.Example(text=text, language=language, meta=metadata)
            for text, language, _, metadata in get_examples(id, table, lexicons)
        ]

    def _counts(self, sense_id: str) -> list[lmf.Count]:
        lexicons = (self.lexspecs.primary,)  # only for the lexicon being exported
        return [
            lmf.Count(value=val, meta=metadata)
            for val, _, metadata in get_sense_counts(sense_id, lexicons)
        ]

    @overload
    def _synsets(
        self, extension: Literal[True]
    ) -> Iterator[lmf.Synset | lmf.ExternalSynset]: ...

    @overload
    def _synsets(self, extension: Literal[False]) -> Iterator[lmf.Synset]: ...

    def _synsets(
        self, extension: Literal[True, False]
    ) -> Iterator[lmf.Synset | lmf.ExternalSynset]:
        lexspec = self.lexspecs.primary
        lexicons = self.lexspecs if extension else (lexspec,)
        for id, pos, ili, lex in find_synsets(lexicons=lexicons):
            if lex == lexspec:
                yield self._synset(id, pos, ili)
            elif extension and (ext_synset := self._ext_synset(id)):
                yield ext_synset

    def _synset(self, id: str, pos: str, ili: str) -> lmf.Synset:
        lexspec = self.lexspecs.primary
        lexicons = (lexspec,)
        ilidef = self._ili_definition(id)
        if ilidef and not ili:
            ili = PROPOSED_ILI_ID
        ss = lmf.Synset(
            id=id,
            ili=ili or "",
            partOfSpeech=pos,
            definitions=self._definitions(id),
            relations=self._synset_relations(id, lexspec),
            examples=self._examples(id, "synsets"),
            lexicalized=get_lexicalized(id, lexspec, "synsets"),
            lexfile=get_lexfile(id, lexspec) or "",
            meta=self._metadata(id, "synsets"),
        )
        if ilidef:
            ss["ili_definition"] = ilidef
        if self.version >= (1, 1):
            ss["members"] = [row[0] for row in get_synset_members(id, lexicons)]
        return ss

    def _definitions(self, synset_id: str) -> list[lmf.Definition]:
        lexicons = (self.lexspecs.primary,)  # only for the lexicon being exported
        return [
            lmf.Definition(
                text=text,
                language=language,
                sourceSense=sense_id,
                meta=metadata,
            )
            for text, language, sense_id, _, metadata in get_definitions(
                synset_id, lexicons
            )
        ]

    def _ili_definition(self, synset: str) -> lmf.ILIDefinition | None:
        lexicons = (self.lexspecs.primary,)  # only for the lexicon being exported
        _, lexspec, defn, _ = next(
            find_proposed_ilis(synset_id=synset, lexicons=lexicons),
            (None, None, None, None),
        )
        ilidef: lmf.ILIDefinition | None = None
        if defn:
            meta = None
            if lexspec is not None:
                meta = get_proposed_ili_metadata(synset, lexspec)
            ilidef = lmf.ILIDefinition(text=defn, meta=meta)
        return ilidef

    def _synset_relations(
        self, synset_id: str, synset_lexicon: str
    ) -> list[lmf.Relation]:
        # only get relations defined for the primary lexicon, but the
        # relation target can be from a base lexicon
        lexicons = (self.lexspecs.primary,)
        return [
            lmf.Relation(target=id, relType=type, meta=metadata)
            for type, _, metadata, _, id, *_ in get_synset_relations(
                synset_id, synset_lexicon, "*", lexicons, self.lexspecs
            )
        ]

    def _syntactic_behaviours_1_0(
        self,
        entry: lmf.LexicalEntry,
    ) -> list[lmf.SyntacticBehaviour]:
        frames: list[lmf.SyntacticBehaviour] = []
        sense_ids = {s["id"] for s in entry.get("senses", [])}
        sbs: dict[str, set[str]] = {}
        for sid in sense_ids:
            for _, subcat_frame in self.sbmap.get(sid, []):
                sbs.setdefault(subcat_frame, set()).add(sid)
        for subcat_frame, sids in sbs.items():
            frame: lmf.SyntacticBehaviour = {
                "subcategorizationFrame": subcat_frame,
                "senses": sorted(sids),
            }
            frames.append(frame)
        return frames

    def _syntactic_behaviours_1_1(self) -> list[lmf.SyntacticBehaviour]:
        lexicons = (self.lexspecs.primary,)  # only for the lexicon being exported
        return [
            lmf.SyntacticBehaviour(id=id or "", subcategorizationFrame=frame)
            for id, frame, _ in find_syntactic_behaviours(lexicons=lexicons)
        ]

    def _metadata(self, id: str, table: str) -> lmf.Metadata:
        return get_metadata(id, self.lexspecs.primary, table)

    ### Lexicon Extensions ###################################################

    def _lexicon_extension(
        self, lexicon: Lexicon, base: Lexicon
    ) -> lmf.LexiconExtension:
        lexspec = self.lexspecs.primary
        if self.version < (1, 1):
            raise Error(
                f"cannot export lexicon extension {lexspec} with WN-LMF version < 1.1"
            )
        lex = lmf.LexiconExtension(
            id=lexicon.id,
            label=lexicon.label,
            language=lexicon.language,
            email=lexicon.email,
            license=lexicon.license,
            version=lexicon.version,
            url=lexicon.url or "",
            citation=lexicon.citation or "",
            logo=lexicon.logo or "",
            extends=self._dependency(base.id, base.version, base.url),
            requires=self._requires(),
            entries=list(self._entries(True)),
            synsets=list(self._synsets(True)),
            frames=self._syntactic_behaviours_1_1(),
            meta=lexicon.metadata(),
        )
        return lex

    def _ext_entry(self, id: str) -> lmf.ExternalLexicalEntry | None:
        lexspec = self.lexspecs.primary
        lemma, forms = _get_entry_forms(id, self.lexspecs)
        index = get_entry_index(id, lexspec)
        ext_lemma = self._ext_lemma(lemma)
        ext_forms = self._ext_forms(forms)
        ext_senses = list(self._senses(id, index, True))
        if ext_lemma or ext_forms or ext_senses:
            return lmf.ExternalLexicalEntry(
                external=True,
                id=id,
                lemma=ext_lemma,
                forms=ext_forms,
                senses=ext_senses,
            )
        return None

    def _ext_lemma(self, lemma: Form) -> lmf.ExternalLemma | None:
        _, _, _, _, pronunciations, tags = lemma
        ext_prons = self._pronunciations(pronunciations)
        ext_tags = self._tags(tags)
        if ext_prons or ext_tags:
            return lmf.ExternalLemma(
                external=True,
                pronunciations=ext_prons,
                tags=ext_tags,
            )
        return None

    def _ext_forms(self, forms: list[Form]) -> list[lmf.Form | lmf.ExternalForm]:
        lexspec = self.lexspecs.primary
        ext_forms: list[lmf.Form | lmf.ExternalForm] = []
        for form in forms:
            if form[3] == lexspec:
                ext_forms.append(self._form(form))
            elif ext_form := self._ext_form(form):
                ext_forms.append(ext_form)
        return ext_forms

    def _ext_form(self, form: Form) -> lmf.ExternalForm | None:
        value, id, _, _, prons, tags = form
        ext_prons = self._pronunciations(prons)
        ext_tags = self._tags(tags)
        if ext_prons or ext_tags:
            if not id:
                raise Error(f"cannot export external form {value!r} without an id")
            return lmf.ExternalForm(
                external=True,
                id=id,
                pronunciations=ext_prons,
                tags=ext_tags,
            )
        return None

    def _ext_sense(self, id: str) -> lmf.ExternalSense | None:
        ext_relations = self._sense_relations(id)
        ext_examples = self._examples(id, "senses")
        ext_counts = self._counts(id)
        if ext_relations or ext_examples or ext_counts or id in self.external_sense_ids:
            return lmf.ExternalSense(
                external=True,
                id=id,
                relations=ext_relations,
                examples=ext_examples,
                counts=ext_counts,
            )
        return None

    def _ext_synset(self, id: str) -> lmf.ExternalSynset | None:
        ext_definitions = self._definitions(id)
        ext_relations = self._synset_relations(id, self.lexspecs.base)
        ext_examples = self._examples(id, "synsets")
        if (
            ext_definitions
            or ext_relations
            or ext_examples
            or id in self.external_synset_ids
        ):
            return lmf.ExternalSynset(
                external=True,
                id=id,
                definitions=ext_definitions,
                relations=ext_relations,
                examples=ext_examples,
            )
        return None


### Helper Functions #########################################################


def _build_sbmap(lexicons: Sequence[str]) -> _SBMap:
    # WN-LMF 1.0 lexicons put syntactic behaviours on lexical entries
    # WN-LMF 1.1 lexicons use a 'subcat' IDREFS attribute
    sbmap: _SBMap = {}
    for sbid, frame, sids in find_syntactic_behaviours(lexicons=lexicons):
        for sid in sids:
            sbmap.setdefault(sid, []).append((sbid, frame))
    return sbmap


def _get_entry_forms(id: str, lexicons: Sequence[str]) -> tuple[Form, list[Form]]:
    all_forms: list[Form] = list(get_entry_forms(id, lexicons))
    # the first result is always the lemma
    return all_forms[0], all_forms[1:]


def _get_sense_n(id: str, lexspec: str, index: str | None, i: int) -> int:
    """Get the n rank value for a sense.

    The n value is only informative if it is non-None and different
    from the expected rank i. If an index is used, always return a
    non-None value of n, even if it is the expected rank.
    """
    n = get_sense_n(id, lexspec)
    if n is not None and (index is not None or n != i):
        return n
    return 0


def _get_external_sense_ids(lexspecs: _LexSpecs) -> set[str]:
    """Get ids of external senses needed for an extension."""
    return get_relation_targets(
        "sense_relations", "senses", (lexspecs.primary,), lexspecs
    )


def _get_external_synset_ids(lexspecs: _LexSpecs) -> set[str]:
    """Get ids of external synsets needed for an extension."""
    return (
        get_relation_targets(
            "synset_relations", "synsets", (lexspecs.primary,), lexspecs
        )
        | get_relation_targets(
            "sense_synset_relations", "synsets", (lexspecs.primary,), lexspecs
        )
        | {
            sense[2]
            for sense in find_senses(lexicons=lexspecs)
            if sense[3] != lexspecs.base
        }
    )
