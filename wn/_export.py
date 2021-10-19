
from typing import List, Dict, Set, Tuple, Sequence, Optional, cast

import wn
from wn._types import AnyPath, VersionInfo
from wn._util import version_info
from wn import lmf
from wn._queries import (
    find_entries,
    find_senses,
    find_synsets,
    find_syntactic_behaviours,
    find_proposed_ilis,
    get_entry_senses,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_relations,
    get_synset_members,
    get_examples,
    get_definitions,
    get_metadata,
    get_lexicalized,
    get_adjposition,
    get_form_pronunciations,
    get_form_tags,
    get_sense_counts,
    get_lexfile,
    get_lexicon,
    get_lexicon_dependencies,
    get_lexicon_extension_bases,
)
from wn._core import Lexicon


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
    all_ids: Set[str] = set()
    for lex in lexicons:
        lexids = (lex._id,)
        idset = {lex.id}
        idset.update(row[0] for row in find_entries(lexicon_rowids=lexids))
        idset.update(row[0] for row in find_senses(lexicon_rowids=lexids))
        idset.update(row[0] for row in find_synsets(lexicon_rowids=lexids))
        # TODO: syntactic behaviours
        if all_ids.intersection(idset):
            raise wn.Error('cannot export: non-unique identifiers in lexicons')
        all_ids |= idset


_SBMap = Dict[str, List[Tuple[str, str]]]


def _export_lexicon(lexicon: Lexicon, version: VersionInfo) -> lmf.Lexicon:
    lexids = (lexicon._id,)

    # WN-LMF 1.0 lexicons put syntactic behaviours on lexical entries
    # WN-LMF 1.1 lexicons use a 'subcat' IDREFS attribute
    sbmap: _SBMap = {}
    if version < (1, 1):
        for sbid, frame, sids in find_syntactic_behaviours(lexicon_rowids=lexids):
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
        'entries': _export_lexical_entries(lexids, sbmap, version),
        'synsets': _export_synsets(lexids, version),
        'meta': _export_metadata(lexicon._id, 'lexicons'),
    }
    if version >= (1, 1):
        lex['logo'] = lexicon.logo or ''
        lex['requires'] = _export_requires(lexicon._id)
        lex['frames'] = _export_syntactic_behaviours_1_1(lexids)

    return lex


def _export_requires(lexid: int) -> List[lmf.Dependency]:
    return [
        {'id': id, 'version': version, 'url': url}
        for id, version, url, _ in get_lexicon_dependencies(lexid)
    ]


def _export_extends(lexid: int) -> lmf.Dependency:
    ext_lexid = get_lexicon_extension_bases(lexid, depth=1)[0]
    _, id, _, _, _, _, version, url, *_ = get_lexicon(ext_lexid)
    return {'id': id, 'version': version, 'url': url}


def _export_lexical_entries(
    lexids: Sequence[int],
    sbmap: _SBMap,
    version: VersionInfo
) -> List[lmf.LexicalEntry]:
    entries: List[lmf.LexicalEntry] = []
    for id, pos, forms, _, rowid in find_entries(lexicon_rowids=lexids):
        entry: lmf.LexicalEntry = {
            'id': id,
            'lemma': {
                'writtenForm': forms[0][0],
                'partOfSpeech': pos,
                'script': forms[0][2] or '',
                'tags': _export_tags(forms[0][3]),
            },
            'forms': [],
            'senses': _export_senses(rowid, lexids, sbmap, version),
            'meta': _export_metadata(rowid, 'entries'),
        }
        if version >= (1, 1):
            entry['lemma']['pronunciations'] = _export_pronunciations(forms[0][3])
        for form, fid, script, frowid in forms[1:]:
            _form: lmf.Form = {
                'id': fid or '',
                'writtenForm': form,
                'script': script or '',
                'tags': _export_tags(frowid),
            }
            if version >= (1, 1):
                _form['pronunciations'] = _export_pronunciations(frowid)
            entry['forms'].append(_form)
        if version < (1, 1):
            entry['frames'] = _export_syntactic_behaviours_1_0(entry, sbmap)
        entries.append(entry)
    return entries


def _export_pronunciations(rowid: int) -> List[lmf.Pronunciation]:
    return [
        {'text': text,
         'variety': variety,
         'notation': notation,
         'phonemic': phonemic,
         'audio': audio}
        for text, variety, notation, phonemic, audio
        in get_form_pronunciations(rowid)
    ]


def _export_tags(rowid: int) -> List[lmf.Tag]:
    return [
        {'text': text, 'category': category}
        for text, category in get_form_tags(rowid)
    ]


def _export_senses(
    entry_rowid: int,
    lexids: Sequence[int],
    sbmap: _SBMap,
    version: VersionInfo,
) -> List[lmf.Sense]:
    senses: List[lmf.Sense] = []
    for id, _, synset, _, rowid in get_entry_senses(entry_rowid, lexids):
        sense: lmf.Sense = {
            'id': id,
            'synset': synset,
            'relations': _export_sense_relations(rowid, lexids),
            'examples': _export_examples(rowid, 'senses', lexids),
            'counts': _export_counts(rowid, lexids),
            'lexicalized': get_lexicalized(rowid, 'senses'),
            'adjposition': get_adjposition(rowid) or '',
            'meta': _export_metadata(rowid, 'senses'),
        }
        if version >= (1, 1) and id in sbmap:
            sense['subcat'] = sorted(sbid for sbid, _ in sbmap[id])
        senses.append(sense)
    return senses


def _export_sense_relations(
    sense_rowid: int,
    lexids: Sequence[int]
) -> List[lmf.Relation]:
    relations: List[lmf.Relation] = [
        {'target': id,
         'relType': type,
         'meta': _export_metadata(rowid, 'sense_relations')}
        for type, rowid, id, *_
        in get_sense_relations(sense_rowid, '*', lexids)
    ]
    relations.extend(
        {'target': id,
         'relType': type,
         'meta': _export_metadata(rowid, 'sense_synset_relations')}
        for type, rowid, id, *_
        in get_sense_synset_relations(sense_rowid, '*', lexids)
    )
    return relations


def _export_examples(
    rowid: int,
    table: str,
    lexids: Sequence[int]
) -> List[lmf.Example]:
    return [
        {'text': text,
         'language': language,
         'meta': _export_metadata(rowid, f'{table[:-1]}_examples')}
        for text, language, rowid
        in get_examples(rowid, table, lexids)
    ]


def _export_counts(rowid: int, lexids: Sequence[int]) -> List[lmf.Count]:
    return [
        {'value': val,
         'meta': _export_metadata(id, 'counts')}
        for val, id in get_sense_counts(rowid, lexids)
    ]


def _export_synsets(lexids: Sequence[int], version: VersionInfo) -> List[lmf.Synset]:
    synsets: List[lmf.Synset] = []
    for id, pos, ili, _, rowid in find_synsets(lexicon_rowids=lexids):
        ilidef = _export_ili_definition(rowid)
        if ilidef and not ili:
            ili = 'in'  # special case for proposed ILIs
        ss: lmf.Synset = {
            'id': id,
            'ili': ili or '',
            'partOfSpeech': pos,
            'definitions': _export_definitions(rowid, lexids),
            'relations': _export_synset_relations(rowid, lexids),
            'examples': _export_examples(rowid, 'synsets', lexids),
            'lexicalized': get_lexicalized(rowid, 'synsets'),
            'lexfile': get_lexfile(rowid) or '',
            'meta': _export_metadata(rowid, 'synsets'),
        }
        if ilidef:
            ss['ili_definition'] = ilidef
        if version >= (1, 1):
            ss['members'] = [row[0] for row in get_synset_members(rowid, lexids)]
        synsets.append(ss)
    return synsets


def _export_definitions(rowid: int, lexids: Sequence[int]) -> List[lmf.Definition]:
    return [
        {'text': text,
         'language': language,
         'sourceSense': sense_id,
         'meta': _export_metadata(rowid, 'definitions')}
        for text, language, sense_id, rowid
        in get_definitions(rowid, lexids)
    ]


def _export_ili_definition(synset_rowid: int) -> Optional[lmf.ILIDefinition]:
    _, _, defn, rowid = next(find_proposed_ilis(synset_rowid=synset_rowid),
                             (None, None, None, None))
    ilidef: Optional[lmf.ILIDefinition] = None
    if defn:
        meta = None
        if rowid is not None:
            meta = _export_metadata(rowid, 'proposed_ilis')
        ilidef = {'text': defn, 'meta': meta}
    return ilidef


def _export_synset_relations(
    synset_rowid: int,
    lexids: Sequence[int]
) -> List[lmf.Relation]:
    return [
        {'target': id,
         'relType': type,
         'meta': _export_metadata(rowid, 'synset_relations')}
        for type, rowid, id, *_
        in get_synset_relations((synset_rowid,), '*', lexids)
    ]


def _export_syntactic_behaviours_1_0(
    entry: lmf.LexicalEntry,
    sbmap: _SBMap,
) -> List[lmf.SyntacticBehaviour]:
    frames: List[lmf.SyntacticBehaviour] = []
    sense_ids = {s['id'] for s in entry.get('senses', [])}
    sbs: Dict[str, Set[str]] = {}
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
    lexids: Sequence[int]
) -> List[lmf.SyntacticBehaviour]:
    return [
        {'id': id or '',
         'subcategorizationFrame': frame}
        for id, frame, _ in find_syntactic_behaviours(lexicon_rowids=lexids)
    ]


def _export_metadata(rowid: int, table: str) -> lmf.Metadata:
    return cast(lmf.Metadata, get_metadata(rowid, table))
