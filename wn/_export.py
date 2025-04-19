
from collections.abc import Sequence
from typing import Optional, cast

import wn
from wn._types import AnyPath, Metadata, VersionInfo
from wn._util import version_info, split_lexicon_specifier
from wn import lmf
from wn._queries import (
    find_entries,
    find_senses,
    find_synsets,
    find_syntactic_behaviours,
    find_proposed_ilis,
    get_entry_forms,
    get_entry_senses,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_relations,
    get_synset_members,
    get_examples,
    get_definitions,
    get_metadata,
    get_proposed_ili_metadata,
    get_lexicalized,
    get_adjposition,
    get_sense_counts,
    get_lexfile,
    get_lexicon,
    get_lexicon_dependencies,
    get_lexicon_extension_bases,
)
from wn._core import Lexicon

PROPOSED_ILI_ID = "in"  # special case for proposed ILIs


def export(
    lexicons: Sequence[Lexicon], destination: AnyPath, version: str = '1.0'
) -> None:
    """Export lexicons from the database to a WN-LMF file.

    More than one lexicon may be exported in the same file, subject to
    these conditions:

    - identifiers on wordnet entities must be unique in all lexicons
    - lexicons extensions may not be exported with their dependents

    >>> w = wn.Wordnet(lexicon='cmnwn zsmwn')
    >>> wn.export(w.lexicons(), 'cmn-zsm.xml')

    Args:
        lexicons: sequence of :class:`wn.Lexicon` objects
        destination: path to the destination file
        version: LMF version string

    """
    _precheck(lexicons)
    assert version in lmf.SUPPORTED_VERSIONS
    _version = version_info(version)
    resource: lmf.LexicalResource = {
        'lmf_version': version,
        'lexicons': [_export_lexicon(lex, _version) for lex in lexicons]
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
            raise wn.Error('cannot export: non-unique identifiers in lexicons')
        all_ids |= idset


_SBMap = dict[str, list[tuple[str, str]]]


def _export_lexicon(lexicon: Lexicon, version: VersionInfo) -> lmf.Lexicon:
    lexicons = (lexicon.specifier(),)
    spec = lexicon.specifier()

    # WN-LMF 1.0 lexicons put syntactic behaviours on lexical entries
    # WN-LMF 1.1 lexicons use a 'subcat' IDREFS attribute
    sbmap: _SBMap = {}
    if version < (1, 1):
        for sbid, frame, sids in find_syntactic_behaviours(lexicons=lexicons):
            for sid in sids:
                sbmap.setdefault(sid, []).append((sbid, frame))

    lex: lmf.Lexicon = {
        'id': lexicon.id,
        'label': lexicon.label,
        'language': lexicon.language,
        'email': lexicon.email,
        'license': lexicon.license,
        'version': lexicon.version,
        'url': lexicon.url or '',
        'citation': lexicon.citation or '',
        'entries': _export_lexical_entries(spec, sbmap, version),
        'synsets': _export_synsets(spec, version),
        'meta': _cast_metadata(lexicon.metadata()),
    }
    if version >= (1, 1):
        lex['logo'] = lexicon.logo or ''
        lex['requires'] = _export_requires(spec)
        lex['frames'] = _export_syntactic_behaviours_1_1(lexicons)

    return lex


def _export_requires(spec: str) -> list[lmf.Dependency]:
    dependencies: list[lmf.Dependency] = []
    for specifier, url, _ in get_lexicon_dependencies(spec):
        id, version = split_lexicon_specifier(specifier)
        dependencies.append(
            {'id': id, 'version': version, 'url': url}
        )
    return dependencies


def _export_extends(spec: str) -> lmf.Dependency:
    ext_spec = get_lexicon_extension_bases(spec, depth=1)[0]
    _, id, _, _, _, _, version, url, *_ = get_lexicon(ext_spec)
    return {'id': id, 'version': version, 'url': url}


def _export_lexical_entries(
    lexspec: str,
    sbmap: _SBMap,
    version: VersionInfo
) -> list[lmf.LexicalEntry]:
    lexicons = (lexspec,)
    entries: list[lmf.LexicalEntry] = []
    for id, pos, *_ in find_entries(lexicons=lexicons):
        forms = list(get_entry_forms(id, lexicons))
        entry: lmf.LexicalEntry = {
            'id': id,
            'lemma': {
                'writtenForm': forms[0][0],
                'partOfSpeech': pos,
                'script': forms[0][2] or '',
                'tags': _export_tags(forms[0][4]),
            },
            'forms': [],
            'senses': _export_senses(id, lexspec, sbmap, version),
            'meta': _export_metadata(id, lexspec, 'entries'),
        }
        if version >= (1, 1):
            entry['lemma']['pronunciations'] = _export_pronunciations(forms[0][3])
        for form, fid, script, prons, tags in forms[1:]:
            _form: lmf.Form = {
                'id': fid or '',
                'writtenForm': form,
                'script': script or '',
                'tags': _export_tags(tags),
            }
            if version >= (1, 1):
                _form['pronunciations'] = _export_pronunciations(prons)
            entry['forms'].append(_form)
        if version < (1, 1):
            entry['frames'] = _export_syntactic_behaviours_1_0(entry, sbmap)
        entries.append(entry)
    return entries


def _export_pronunciations(
    rows: list[tuple[str, Optional[str], Optional[str], bool, Optional[str]]]
) -> list[lmf.Pronunciation]:
    prons: list[lmf.Pronunciation] = []
    for text, variety, notation, phonemic, audio in rows:
        pron = lmf.Pronunciation(text=text)
        if variety is not None:
            pron['variety'] = variety
        if notation is not None:
            pron['notation'] = notation
        if not phonemic:
            pron['phonemic'] = phonemic
        if audio is not None:
            pron['audio'] = audio
    return prons


def _export_tags(rows: list[tuple[str, str]]) -> list[lmf.Tag]:
    return [
        {'text': text, 'category': category}
        for text, category in rows
    ]


def _export_senses(
    entry_id,
    lexspec: str,
    sbmap: _SBMap,
    version: VersionInfo,
) -> list[lmf.Sense]:
    senses: list[lmf.Sense] = []
    lexicons = (lexspec,)
    for id, _, synset, *_ in get_entry_senses(entry_id, lexicons):
        sense: lmf.Sense = {
            'id': id,
            'synset': synset,
            'relations': _export_sense_relations(id, lexicons),
            'examples': _export_examples(id, 'senses', lexicons),
            'counts': _export_counts(id, lexicons),
            'lexicalized': get_lexicalized(id, lexspec, 'senses'),
            'adjposition': get_adjposition(id, lexspec) or '',
            'meta': _export_metadata(id, lexspec, 'senses'),
        }
        if version >= (1, 1) and id in sbmap:
            sense['subcat'] = sorted(sbid for sbid, _ in sbmap[id])
        senses.append(sense)
    return senses


def _export_sense_relations(
    sense_id: str,
    lexicons: Sequence[str]
) -> list[lmf.Relation]:
    relations: list[lmf.Relation] = [
        {'target': id,
         'relType': type,
         'meta': _cast_metadata(metadata)}
        for type, _, metadata, id, *_
        in get_sense_relations(sense_id, '*', lexicons)
    ]
    relations.extend(
        {'target': id,
         'relType': type,
         'meta': _cast_metadata(metadata)}
        for type, _, metadata, _, id, *_
        in get_sense_synset_relations(sense_id, '*', lexicons)
    )
    return relations


def _export_examples(
    id: str,
    table: str,
    lexicons: Sequence[str]
) -> list[lmf.Example]:
    return [
        {'text': text,
         'language': language,
         'meta': cast(lmf.Metadata, metadata)}
        for text, language, metadata
        in get_examples(id, table, lexicons)
    ]


def _export_counts(sense_id: str, lexicons: Sequence[str]) -> list[lmf.Count]:
    return [
        {'value': val, 'meta': _cast_metadata(metadata)}
        for val, metadata in get_sense_counts(sense_id, lexicons)
    ]


def _export_synsets(
    lexspec: str,
    version: VersionInfo,
) -> list[lmf.Synset]:
    lexicons = (lexspec,)
    synsets: list[lmf.Synset] = []
    for id, pos, ili, *_ in find_synsets(lexicons=lexicons):
        ilidef = _export_ili_definition(id)
        if ilidef and not ili:
            ili = PROPOSED_ILI_ID
        ss: lmf.Synset = {
            'id': id,
            'ili': ili or '',
            'partOfSpeech': pos,
            'definitions': _export_definitions(id, lexicons),
            'relations': _export_synset_relations(id, lexspec),
            'examples': _export_examples(id, 'synsets', lexicons),
            'lexicalized': get_lexicalized(id, lexspec, 'synsets'),
            'lexfile': get_lexfile(id, lexspec) or '',
            'meta': _export_metadata(id, lexspec, 'synsets'),
        }
        if ilidef:
            ss['ili_definition'] = ilidef
        if version >= (1, 1):
            ss['members'] = [row[0] for row in get_synset_members(id, lexicons)]
        synsets.append(ss)
    return synsets


def _export_definitions(
    synset_id: str,
    lexicons: Sequence[str],
) -> list[lmf.Definition]:
    return [
        {'text': text,
         'language': language,
         'sourceSense': sense_id,
         'meta': _cast_metadata(metadata)}
        for text, language, sense_id, metadata
        in get_definitions(synset_id, lexicons)
    ]


def _export_ili_definition(synset: str) -> Optional[lmf.ILIDefinition]:
    _, _, defn, _, lexspec = next(
        find_proposed_ilis(synset_id=synset),
        (None, None, None, None, None)
    )
    ilidef: Optional[lmf.ILIDefinition] = None
    if defn:
        meta = None
        if lexspec is not None:
            meta = get_proposed_ili_metadata(synset, lexspec)
        ilidef = {'text': defn, 'meta': _cast_metadata(meta)}
    return ilidef


def _export_synset_relations(
    synset_id: str,
    synset_lexicon: str,
) -> list[lmf.Relation]:
    return [
        {'target': id,
         'relType': type,
         'meta': _cast_metadata(metadata)}
        for type, _, metadata, _, id, *_
        in get_synset_relations(synset_id, synset_lexicon, '*', (synset_lexicon,))
    ]


def _export_syntactic_behaviours_1_0(
    entry: lmf.LexicalEntry,
    sbmap: _SBMap,
) -> list[lmf.SyntacticBehaviour]:
    frames: list[lmf.SyntacticBehaviour] = []
    sense_ids = {s['id'] for s in entry.get('senses', [])}
    sbs: dict[str, set[str]] = {}
    for sid in sense_ids:
        for _, subcat_frame in sbmap.get(sid, []):
            sbs.setdefault(subcat_frame, set()).add(sid)
    for subcat_frame, sids in sbs.items():
        frame: lmf.SyntacticBehaviour = {
            'subcategorizationFrame': subcat_frame,
            'senses': sorted(sids),
        }
        frames.append(frame)
    return frames


def _export_syntactic_behaviours_1_1(
    lexicons: Sequence[str]
) -> list[lmf.SyntacticBehaviour]:
    return [
        {'id': id or '',
         'subcategorizationFrame': frame}
        for id, frame, _ in find_syntactic_behaviours(lexicons=lexicons)
    ]


def _export_metadata(id: str, lexicon: str, table: str) -> lmf.Metadata:
    return cast(lmf.Metadata, get_metadata(id, lexicon, table))


def _cast_metadata(metadata: Optional[Metadata]) -> lmf.Metadata:
    return cast(lmf.Metadata, metadata or {})
