"""
Database retrieval queries.
"""

from typing import (
    Optional, Any, Dict, Set, List, Tuple, Collection, Iterator, Sequence
)
import itertools
import sqlite3

import wn
from wn._types import Metadata
from wn._db import connect, NON_ROWID


# Local Types

_Form = Tuple[
    str,            # form
    Optional[str],  # script
    int             # rowid
]
_Word = Tuple[
    str,          # id
    str,          # pos
    List[_Form],  # forms
    int,          # lexid
    int,          # rowid
]
_Synset = Tuple[
    str,  # id
    str,  # pos
    str,  # ili
    int,  # lexid
    int,  # rowid
]
_Synset_Relation = Tuple[str, int, str, str, str, int, int]  # relname, relid, *_Synset
_Sense = Tuple[
    str,  # id
    str,  # entry_id
    str,  # synset_id
    int,  # lexid
    int,  # rowid
]
_Sense_Relation = Tuple[str, int, str, str, str, int, int]  # relname, relid,  *_Sense
_Lexicon = Tuple[
    int,       # rowid
    str,       # id
    str,       # label
    str,       # language
    str,       # email
    str,       # license
    str,       # version
    str,       # url
    str,       # citation
    Metadata,  # metadata
]


def find_lexicons(
    lexicon: str,
    lang: str = None,
) -> Iterator[_Lexicon]:
    conn = connect()
    rows = conn.execute('SELECT rowid, id, version, language FROM lexicons').fetchall()
    rowids = _get_lexicon_rowids_for_lang(rows, lang)
    # the next call is somewhat expensive, so try to skip it in a common case
    if lexicon != '*':
        rowids &= _get_lexicon_rowids_for_lexicon(rows, lexicon)
    if rows and not rowids:
        raise wn.Error(
            f'no lexicon found with lang={lang!r} and lexicon={lexicon!r}'
        )
    for rowid in sorted(rowids):
        yield _get_lexicon(conn, rowid)


def get_lexicon(rowid: int) -> _Lexicon:
    conn = connect()
    return _get_lexicon(conn, rowid)


def _get_lexicon(conn: sqlite3.Connection, rowid: int) -> _Lexicon:
    query = '''
        SELECT DISTINCT rowid, id, label, language, email, license,
                        version, url, citation
        FROM lexicons
        WHERE rowid = ?
    '''
    row: Optional[_Lexicon] = conn.execute(query, (rowid,)).fetchone()
    if row is None:
        raise LookupError(rowid)  # should we have a WnLookupError?
    return row


def _get_lexicon_rowids_for_lang(
        rows: List[Tuple[int, str, str, str]], lang: Optional[str]
) -> Set[int]:
    lg_match: Set[int] = set()
    if lang:
        lg_match.update(rowid for rowid, _, _, language in rows if language == lang)
        if not lg_match:
            raise wn.Error(f"no lexicon found with language code '{lang}'")
    else:
        lg_match.update(row[0] for row in rows)
    return lg_match


def _get_lexicon_rowids_for_lexicon(
    rows: List[Tuple[int, str, str, str]],
    lexicon: str,
) -> Set[int]:
    lexmap: Dict[str, Dict[str, int]] = {}
    for rowid, id, version, _ in rows:
        lexmap.setdefault(id, {})[version] = rowid

    lex_match: Set[int] = set()
    for id_ver in lexicon.split():
        id, _, ver = id_ver.partition(':')

        if id == '*':
            for vermap in lexmap.values():
                for version, rowid in vermap.items():
                    if ver in ('', '*', version):
                        lex_match.add(rowid)

        elif id in lexmap:
            if ver == '*':
                lex_match.update(rowid for rowid in lexmap[id].values())
            elif ver == '':
                lex_match.add(max(lexmap[id].values()))  # last installed version
            elif ver in lexmap[id]:
                lex_match.add(lexmap[id][ver])
            else:
                raise wn.Error(f"no lexicon with id '{id}' found with version '{ver}'")

        else:
            raise wn.Error(f"no lexicon found with id '{id}'")

    return lex_match


def find_entries(
        id: str = None,
        form: str = None,
        pos: str = None,
        lexicon_rowids: Sequence[int] = None,
) -> Iterator[_Word]:
    conn = connect()
    query_parts = [
        'SELECT DISTINCT e.lexicon_rowid, e.rowid, e.id, p.pos,'
        '                f.form, f.script, f.rowid',
        '  FROM entries AS e',
        '  JOIN parts_of_speech AS p ON p.rowid = e.pos_rowid',
        '  JOIN forms AS f ON f.entry_rowid = e.rowid',
    ]

    params: Dict[str, Any] = {'id': id, 'form': form, 'pos': pos}
    conditions = []
    if id:
        conditions.append('e.id = :id')
    if form:
        conditions.append('e.rowid IN'
                          ' (SELECT entry_rowid FROM forms WHERE form = :form)')
    if pos:
        conditions.append('p.pos = :pos')
    if lexicon_rowids:
        kws = {f'lex{i}': rowid for i, rowid in enumerate(lexicon_rowids, 1)}
        params.update(kws)
        conditions.append(f'e.lexicon_rowid IN ({_kws(kws)})')

    if conditions:
        query_parts.append(' WHERE ' + '\n   AND '.join(conditions))

    query_parts.append(' ORDER BY e.rowid, e.id, f.rank')

    query = '\n'.join(query_parts)
    rows: Iterator[
        Tuple[int, int, str, str, str, Optional[str], int]
    ] = conn.execute(query, params)
    groupby = itertools.groupby
    for key, group in groupby(rows, lambda row: row[0:4]):
        lexid, rowid, id, pos = key
        forms = [(row[4], row[5], row[6]) for row in group]
        yield (id, pos, forms, lexid, rowid)


def find_senses(
        id: str = None,
        form: str = None,
        pos: str = None,
        lexicon_rowids: Sequence[int] = None,
) -> Iterator[_Sense]:
    conn = connect()
    query_parts = [
        'SELECT DISTINCT s.id, e.id, ss.id, s.lexicon_rowid, s.rowid'
        '  FROM senses AS s'
        '  JOIN entries AS e ON e.rowid = s.entry_rowid'
        '  JOIN synsets AS ss ON ss.rowid = s.synset_rowid'
    ]

    params: Dict[str, Any] = {'id': id, 'form': form, 'pos': pos}
    conditions = []
    if id:
        conditions.append('s.id = :id')
    if form:
        conditions.append('s.entry_rowid IN'
                          ' (SELECT entry_rowid FROM forms WHERE form = :form)')
    if pos:
        conditions.append('e.pos_rowid IN'
                          ' (SELECT p.rowid'
                          '    FROM parts_of_speech AS p'
                          '   WHERE p.pos = :pos)')
    if lexicon_rowids:
        kws = {f'lex{i}': rowid for i, rowid in enumerate(lexicon_rowids, 1)}
        params.update(kws)
        conditions.append(f's.lexicon_rowid IN ({_kws(kws)})')

    if conditions:
        query_parts.append(' WHERE ' + '\n   AND '.join(conditions))

    query = '\n'.join(query_parts)
    rows: Iterator[_Sense] = conn.execute(query, params)
    yield from rows


def find_synsets(
        id: str = None,
        form: str = None,
        pos: str = None,
        ili: str = None,
        lexicon_rowids: Sequence[int] = None,
) -> Iterator[_Synset]:
    conn = connect()
    query_parts = [
        'SELECT DISTINCT ss.id, p.pos, ss.ili, ss.lexicon_rowid, ss.rowid',
        '  FROM synsets AS ss',
        '  JOIN parts_of_speech AS p ON p.rowid = ss.pos_rowid',
    ]

    params: Dict[str, Any] = {'id': id, 'form': form, 'pos': pos, 'ili': ili}
    conditions = []
    if id:
        conditions.append('ss.id = :id')
    if form:
        query_parts.append(
            '  JOIN (SELECT _s.synset_rowid, _s.entry_rowid, _s.entry_rank'
            '          FROM senses AS _s'
            '          JOIN forms AS f'
            '            ON f.entry_rowid = _s.entry_rowid'
            '         WHERE f.form = :form) AS s'
            '    ON s.synset_rowid = ss.rowid'
        )
    if pos:
        conditions.append('p.pos = :pos')
    if ili:
        conditions.append('ss.ili = :ili')
    if lexicon_rowids:
        kws = {f'lex{i}': rowid for i, rowid in enumerate(lexicon_rowids, 1)}
        params.update(kws)
        conditions.append(f'ss.lexicon_rowid IN ({_kws(kws)})')

    if conditions:
        query_parts.append(' WHERE ' + '\n   AND '.join(conditions))

    if form:
        query_parts.append(' ORDER BY s.entry_rowid, s.entry_rank')

    query = '\n'.join(query_parts)
    rows: Iterator[_Synset] = conn.execute(query, params)
    yield from rows


def get_synsets_for_ilis(
        ilis: Collection[str],
        lexicon_rowids: Sequence[int],
) -> Iterator[_Synset]:
    conn = connect()
    query = f'''
        SELECT DISTINCT ss.id, p.pos, ss.ili, ss.lexicon_rowid, ss.rowid
          FROM synsets as ss
          JOIN parts_of_speech AS p
            ON p.rowid = ss.pos_rowid
         WHERE ss.ili IN ({_qs(ilis)})
           AND ss.lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    params = *ilis, *lexicon_rowids
    result_rows: Iterator[_Synset] = conn.execute(query, params)
    yield from result_rows


def get_synset_relations(
        source_rowids: Collection[int],
        relation_types: Collection[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: List = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(source_rowids)
    query = f'''
          WITH relation_types(type_rowid, type) AS  -- relation type lookup
               (SELECT t.rowid, t.type
                  FROM synset_relation_types AS t
                {constraint})
        SELECT DISTINCT rel.type, rel.rowid,
                        tgt.id, p.pos, tgt.ili,
                        tgt.lexicon_rowid, tgt.rowid
          FROM (SELECT type, target_rowid, srel.rowid
                  FROM synset_relations AS srel
                  JOIN relation_types USING (type_rowid)
                 WHERE source_rowid IN ({_qs(source_rowids)})) AS rel
          JOIN synsets AS tgt
            ON tgt.rowid = rel.target_rowid
          JOIN parts_of_speech AS p
            ON p.rowid = tgt.pos_rowid
    '''
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows


def get_definitions(synset_rowid: int) -> List[Tuple[str, str, int]]:
    conn = connect()
    query = '''
        SELECT definition, language, rowid
          FROM definitions
         WHERE synset_rowid = ?
    '''
    return conn.execute(query, (synset_rowid,)).fetchall()


_SANITIZED_EXAMPLE_PREFIXES = {
    'senses': 'sense',
    'synsets': 'synset',
}


def get_examples(rowid: int, table: str) -> List[Tuple[str, str, int]]:
    conn = connect()
    prefix = _SANITIZED_EXAMPLE_PREFIXES.get(table)
    if prefix is None:
        raise wn.Error(f"'{table}' does not have examples")
    query = f'''
        SELECT example, language, rowid
          FROM {prefix}_examples
         WHERE {prefix}_rowid = ?
    '''
    return conn.execute(query, (rowid,)).fetchall()


def _get_senses(rowid: int, sourcetype: str) -> Iterator[_Sense]:
    conn = connect()
    query = f'''
        SELECT s.id, e.id, ss.id, s.lexicon_rowid, s.rowid
          FROM senses AS s
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
         WHERE s.{sourcetype}_rowid = ?
    '''
    return conn.execute(query, (rowid,))


def get_entry_senses(rowid: int) -> Iterator[_Sense]:
    yield from _get_senses(rowid, 'entry')


def get_synset_members(rowid: int) -> Iterator[_Sense]:
    yield from _get_senses(rowid, 'synset')


def get_sense_relations(
        source_rowid: int,
        relation_types: Collection[str],
) -> Iterator[_Sense_Relation]:
    conn = connect()
    params: List = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.append(source_rowid)
    query = f'''
          WITH relation_types(type_rowid, type) AS  -- relation type lookup
               (SELECT t.rowid, t.type
                  FROM sense_relation_types AS t
                {constraint})
        SELECT DISTINCT rel.type, rel.rowid,
                        s.id, e.id, ss.id,
                        s.lexicon_rowid, s.rowid
          FROM (SELECT type, target_rowid, srel.rowid
                  FROM sense_relations AS srel
                  JOIN relation_types USING (type_rowid)
                 WHERE source_rowid = ?) AS rel
          JOIN senses AS s
            ON s.rowid = rel.target_rowid
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
    '''
    rows: Iterator[_Sense_Relation] = conn.execute(query, params)
    yield from rows


def get_sense_synset_relations(
        source_rowid: int,
        relation_types: Collection[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: List = [source_rowid]
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    query = f'''
          WITH relation_types(type_rowid, type) AS  -- relation type lookup
               (SELECT t.rowid, t.type
                  FROM sense_relation_types AS t
                {constraint})
        SELECT DISTINCT rel.type, rel.rowid,
                        ss.id, p.pos, ss.ili,
                        ss.lexicon_rowid, ss.rowid
          FROM (SELECT type, target_rowid, srel.rowid
                  FROM sense_synset_relations AS srel
                  JOIN relation_types USING (type_rowid)
                 WHERE source_rowid = ?) AS rel
          JOIN synsets AS ss
            ON ss.rowid = rel.target_rowid
          JOIN parts_of_speech AS p
            ON p.rowid = ss.pos_rowid
    '''
    rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from rows


_SANITIZED_METADATA_TABLES = {
    'lexicons': 'lexicons',
    'entries': 'entries',
    'senses': 'senses',
    'synsets': 'synsets',
    'sense_relations': 'sense_relations',
    'sense_synset_relations': 'sense_synset_relations',
    'synset_relations': 'synset_relations',
    'sense_examples': 'sense_examples',
    'synset_examples': 'synset_examples',
    'definitions': 'definitions',
}


def get_metadata(
    rowid: int, table: str
) -> Metadata:
    conn = connect()
    tablename = _SANITIZED_METADATA_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not contain metadata")
    query = f'SELECT metadata FROM {tablename} WHERE rowid=?'
    return conn.execute(query, (rowid,)).fetchone()[0] or {}


_SANITIZED_LEXICALIZED_TABLES = {
    'senses': 'senses',
    'synsets': 'synsets',
}


def get_lexicalized(rowid: int, table: str) -> bool:
    conn = connect()
    tablename = _SANITIZED_LEXICALIZED_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not mark lexicalization")
    if rowid == NON_ROWID:
        return False
    query = f'SELECT lexicalized FROM {tablename} WHERE rowid=?'
    return conn.execute(query, (rowid,)).fetchone()[0]


def _qs(xs: Collection) -> str: return ','.join('?' * len(xs))
def _kws(xs: Collection) -> str: return ','.join(f':{x}' for x in xs)
