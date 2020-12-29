
from typing import List, Set, Sequence
import sqlite3

import wn
from wn._types import AnyPath
from wn import lmf
from wn._db import connects
from wn._queries import (
    find_entries,
    find_senses,
    find_synsets,
    get_entry_senses,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_relations,
    get_examples,
    get_definitions,
    get_metadata,
    get_lexicalized,
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
    _lexicons = [_export_lexicon(lex) for lex in lexicons]
    lmf.dump(_lexicons, destination, version=version)


@connects
def _precheck(lexicons: Sequence[Lexicon], conn: sqlite3.Connection = None) -> None:
    assert conn is not None  # provided by decorator
    all_ids: Set[str] = set()
    for lex in lexicons:
        lexids = (lex._id,)
        idset = {lex.id}
        idset.update(row[0] for row in find_entries(lexicon_rowids=lexids, conn=conn))
        idset.update(row[0] for row in find_senses(lexicon_rowids=lexids, conn=conn))
        idset.update(row[0] for row in find_synsets(lexicon_rowids=lexids, conn=conn))
        # TODO: syntactic behaviours
        if all_ids.intersection(idset):
            raise wn.Error('cannot export: non-unique identifiers in lexicons')
        all_ids |= idset


@connects
def _export_lexicon(lexicon: Lexicon, conn: sqlite3.Connection = None) -> lmf.Lexicon:
    assert conn is not None  # provided by decorator
    lexids = (lexicon._id,)
    return lmf.Lexicon(
        id=lexicon.id,
        label=lexicon.label,
        language=lexicon.language,
        email=lexicon.email,
        license=lexicon.license,
        version=lexicon.version,
        url=lexicon.url or '',
        citation=lexicon.citation or '',
        lexical_entries=_export_lexical_entries(conn, lexids),
        synsets=_export_synsets(conn, lexids),
        syntactic_behaviours=_export_syntactic_behaviours(conn, lexids),
        meta=lmf.Metadata(**lexicon.metadata())
    )


def _export_lexical_entries(
    conn: sqlite3.Connection, lexids: Sequence[int]
) -> List[lmf.LexicalEntry]:
    LexicalEntry = lmf.LexicalEntry
    Lemma = lmf.Lemma
    Form = lmf.Form
    return [
        LexicalEntry(
            id,
            Lemma(forms[0][0], pos, script=forms[0][1] or ''),  # TODO: tags
            forms=[Form(form, script or '')
                   for form, script, _ in forms[1:]],  # TODO: tags
            senses=_export_senses(conn, rowid),
            meta=_export_metadata(conn, rowid, 'entries'),
        )
        for id, pos, forms, _, rowid
        in find_entries(lexicon_rowids=lexids, conn=conn)
    ]


def _export_senses(
    conn: sqlite3.Connection, entry_rowid: int
) -> List[lmf.Sense]:
    Sense = lmf.Sense
    return [
        Sense(
            id,
            synset,
            relations=_export_sense_relations(conn, rowid),
            examples=_export_examples(conn, rowid, 'senses'),
            # TODO: counts
            lexicalized=get_lexicalized(rowid, 'senses', conn=conn),
            # TODO: adjposition
            meta=_export_metadata(conn, rowid, 'senses'),
        )
        for id, _, synset, _, rowid
        in get_entry_senses(entry_rowid, conn=conn)
    ]


def _export_sense_relations(
    conn: sqlite3.Connection, sense_rowid: int
) -> List[lmf.SenseRelation]:
    SenseRelation = lmf.SenseRelation
    relations = [
        SenseRelation(
            id,
            type,
            meta=_export_metadata(conn, rowid, 'sense_relations')
        )
        for type, rowid, id, *_
        in get_sense_relations(sense_rowid, '*', conn=conn)
    ]
    relations.extend(
        SenseRelation(
            id,
            type,
            meta=_export_metadata(conn, rowid, 'sense_synset_relations')
        )
        for type, rowid, id, *_
        in get_sense_synset_relations(sense_rowid, '*', conn=conn)
    )
    return relations


def _export_examples(
    conn: sqlite3.Connection, rowid: int, table: str
) -> List[lmf.Example]:
    Example = lmf.Example
    return [
        Example(
            text,
            language,
            meta=_export_metadata(conn, rowid, f'{table[:-1]}_examples')
        )
        for text, language, rowid
        in get_examples(rowid, table, conn=conn)
    ]


def _export_synsets(
    conn: sqlite3.Connection, lexids: Sequence[int]
) -> List[lmf.Synset]:
    Synset = lmf.Synset
    return [
        Synset(
            id,
            ili or '',
            pos,
            definitions=_export_definitions(conn, rowid),
            # TODO: ili_definition,
            relations=_export_synset_relations(conn, rowid),
            examples=_export_examples(conn, rowid, 'synsets'),
            lexicalized=get_lexicalized(rowid, 'synsets', conn=conn),
            meta=_export_metadata(conn, rowid, 'synsets'),
        )
        for id, pos, ili, _, rowid
        in find_synsets(lexicon_rowids=lexids, conn=conn)
    ]


def _export_definitions(
    conn: sqlite3.Connection, rowid: int
) -> List[lmf.Definition]:
    Definition = lmf.Definition
    return [
        Definition(
            text,
            language,
            meta=_export_metadata(conn, rowid, 'definitions')
        )
        for text, language, rowid
        in get_definitions(rowid, conn=conn)
    ]


def _export_synset_relations(
    conn: sqlite3.Connection, synset_rowid: int
) -> List[lmf.SynsetRelation]:
    SynsetRelation = lmf.SynsetRelation
    relations = [
        SynsetRelation(
            id,
            type,
            meta=_export_metadata(conn, rowid, 'synset_relations')
        )
        for type, rowid, id, *_
        in get_synset_relations((synset_rowid,), '*', conn=conn)
    ]
    return relations


def _export_syntactic_behaviours(
    conn: sqlite3.Connection, lexids: Sequence[int]
) -> List[lmf.SyntacticBehaviour]:
    return []  # TODO


def _export_metadata(
    conn: sqlite3.Connection, rowid: int, table: str
) -> lmf.Metadata:
    return lmf.Metadata(**get_metadata(rowid, table, conn=conn))
