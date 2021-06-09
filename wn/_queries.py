"""
Database retrieval queries.
"""

from typing import (
    Optional, Dict, Set, List, Tuple, Collection, Iterator, Sequence
)
import itertools
import sqlite3

import wn
from wn._types import Metadata
from wn._db import connect, NON_ROWID


# Local Types

_Pronunciation = Tuple[
    str,   # value
    str,   # variety
    str,   # notation
    bool,  # phonemic
    str,   # audio
]
_Tag = Tuple[str, str]  # tag, category
_Form = Tuple[
    str,            # form
    Optional[str],  # id
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
_Count = Tuple[int, int]  # count, count_id
_SyntacticBehaviour = Tuple[
    str,       # id
    str,       # frame
    List[str]  # sense ids
]
_ILI = Tuple[
    Optional[str],  # id
    str,            # status
    Optional[str],  # definition
    int,            # rowid
]
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
    str,       # logo
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
                        version, url, citation, logo
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


def get_modified(rowid: int) -> bool:
    query = 'SELECT modified FROM lexicons WHERE rowid = ?'
    return connect().execute(query, (rowid,)).fetchone()[0]


def get_lexicon_dependencies(rowid: int) -> List[Tuple[str, str, str, Optional[int]]]:
    query = '''
        SELECT provider_id, provider_version, provider_url, provider_rowid
          FROM lexicon_dependencies
         WHERE dependent_rowid = ?
    '''
    return connect().execute(query, (rowid,)).fetchall()


def get_lexicon_extension_bases(rowid: int, depth: int = -1) -> List[int]:
    query = '''
          WITH RECURSIVE ext(x, d) AS
               (SELECT base_rowid, 1
                  FROM lexicon_extensions
                 WHERE extension_rowid = :rowid
                 UNION SELECT base_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON extension_rowid = x)
        SELECT x FROM ext
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    '''
    rows = connect().execute(query, {'rowid': rowid, 'depth': depth})
    return [row[0] for row in rows]


def get_lexicon_extensions(rowid: int, depth: int = -1) -> List[int]:
    query = '''
          WITH RECURSIVE ext(x, d) AS
               (SELECT extension_rowid, 1
                  FROM lexicon_extensions
                 WHERE base_rowid = :rowid
                 UNION SELECT extension_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON base_rowid = x)
        SELECT x FROM ext
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    '''
    rows = connect().execute(query, {'rowid': rowid, 'depth': depth})
    return [row[0] for row in rows]


def find_ilis(
    id: str = None,
    status: str = None,
    lexicon_rowids: Sequence[int] = None,
) -> Iterator[_ILI]:
    if status != 'proposed':
        yield from _find_existing_ilis(
            id=id, status=status, lexicon_rowids=lexicon_rowids
        )
    if not id and (not status or status == 'proposed'):
        yield from find_proposed_ilis(lexicon_rowids=lexicon_rowids)


def _find_existing_ilis(
    id: str = None,
    status: str = None,
    lexicon_rowids: Sequence[int] = None,
) -> Iterator[_ILI]:
    query = '''
        SELECT DISTINCT i.id, ist.status, i.definition, i.rowid
          FROM ilis AS i
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
    '''
    conditions: List[str] = []
    params: List = []
    if id:
        conditions.append('i.id = ?')
        params.append(id)
    if status:
        conditions.append('ist.status = ?')
        params.append(status)
    if lexicon_rowids:
        conditions.append(f'''
            i.rowid IN
            (SELECT ss.ili_rowid
               FROM synsets AS ss
              WHERE ss.lexicon_rowid IN ({_qs(lexicon_rowids)}))
        ''')
        params.extend(lexicon_rowids)
    if conditions:
        query += '\n WHERE ' + '\n   AND '.join(conditions)
    yield from connect().execute(query, params)


def find_proposed_ilis(
    synset_rowid: int = None,
    lexicon_rowids: Sequence[int] = None,
) -> Iterator[_ILI]:
    query = '''
        SELECT null, "proposed", definition, rowid
          FROM proposed_ilis
    '''
    conditions = []
    params = []
    if synset_rowid is not None:
        conditions.append('synset_rowid = ?')
        params.append(synset_rowid)
    if lexicon_rowids:
        conditions.append(f'''
            synset_rowid IN
            (SELECT ss.rowid FROM synsets AS ss
              WHERE ss.lexicon_rowid IN ({_qs(lexicon_rowids)}))
        ''')
        params.extend(lexicon_rowids)
    if conditions:
        query += '\n WHERE ' + '\n   AND '.join(conditions)
    yield from connect().execute(query, params)


def find_entries(
    id: str = None,
    forms: Sequence[str] = None,
    pos: str = None,
    lexicon_rowids: Sequence[int] = None,
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Word]:
    conn = connect()
    cte = ''
    params: List = []
    conditions = []
    if id:
        conditions.append('e.id = ?')
        params.append(id)
    if forms:
        cte = f'WITH wordforms(s) AS (VALUES {_vs(forms)})'
        or_norm = 'OR normalized_form IN wordforms' if normalized else ''
        and_rank = '' if search_all_forms else 'AND rank = 0'
        conditions.append(f'''
            e.rowid IN
               (SELECT entry_rowid
                  FROM forms
                 WHERE (form IN wordforms {or_norm}) {and_rank})
        '''.strip())
        params.extend(forms)
    if pos:
        conditions.append('e.pos = ?')
        params.append(pos)
    if lexicon_rowids:
        conditions.append(f'e.lexicon_rowid IN ({_qs(lexicon_rowids)})')
        params.extend(lexicon_rowids)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    query = f'''
          {cte}
        SELECT DISTINCT e.lexicon_rowid, e.rowid, e.id, e.pos,
                        f.form, f.id, f.script, f.rowid
          FROM entries AS e
          JOIN forms AS f ON f.entry_rowid = e.rowid
         {condition}
         ORDER BY e.rowid, e.id, f.rank
    '''

    rows: Iterator[
        Tuple[int, int, str, str, str, Optional[str], Optional[str], int]
    ] = conn.execute(query, params)
    groupby = itertools.groupby
    for key, group in groupby(rows, lambda row: row[0:4]):
        lexid, rowid, id, pos = key
        wordforms = [(row[4], row[5], row[6], row[7]) for row in group]
        yield (id, pos, wordforms, lexid, rowid)


def find_senses(
    id: str = None,
    forms: Sequence[str] = None,
    pos: str = None,
    lexicon_rowids: Sequence[int] = None,
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Sense]:
    conn = connect()
    cte = ''
    params: List = []
    conditions = []
    if id:
        conditions.append('s.id = ?')
        params.append(id)
    if forms:
        cte = f'WITH wordforms(s) AS (VALUES {_vs(forms)})'
        or_norm = 'OR normalized_form IN wordforms' if normalized else ''
        and_rank = '' if search_all_forms else 'AND rank = 0'
        conditions.append(f'''
            s.entry_rowid IN
               (SELECT entry_rowid
                  FROM forms
                 WHERE (form IN wordforms {or_norm}) {and_rank})
        '''.strip())
        params.extend(forms)
    if pos:
        conditions.append('e.pos = ?')
        params.append(pos)
    if lexicon_rowids:
        conditions.append(f's.lexicon_rowid IN ({_qs(lexicon_rowids)})')
        params.extend(lexicon_rowids)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    query = f'''
          {cte}
        SELECT DISTINCT s.id, e.id, ss.id, s.lexicon_rowid, s.rowid
          FROM senses AS s
          JOIN entries AS e ON e.rowid = s.entry_rowid
          JOIN synsets AS ss ON ss.rowid = s.synset_rowid
         {condition}
    '''

    rows: Iterator[_Sense] = conn.execute(query, params)
    yield from rows


def find_synsets(
    id: str = None,
    forms: Sequence[str] = None,
    pos: str = None,
    ili: str = None,
    lexicon_rowids: Sequence[int] = None,
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Synset]:
    conn = connect()
    cte = ''
    join = ''
    conditions = []
    order = ''
    params: List = []
    if id:
        conditions.append('ss.id = ?')
        params.append(id)
    if forms:
        cte = f'WITH wordforms(s) AS (VALUES {_vs(forms)})'
        or_norm = 'OR normalized_form IN wordforms' if normalized else ''
        and_rank = '' if search_all_forms else 'AND rank = 0'
        join = f'''\
          JOIN (SELECT _s.entry_rowid, _s.synset_rowid, _s.entry_rank
                  FROM forms AS f
                  JOIN senses AS _s ON _s.entry_rowid = f.entry_rowid
                 WHERE (f.form IN wordforms {or_norm}) {and_rank}) AS s
            ON s.synset_rowid = ss.rowid
        '''.strip()
        params.extend(forms)
        order = 'ORDER BY s.entry_rowid, s.entry_rank'
    if pos:
        conditions.append('ss.pos = ?')
        params.append(pos)
    if ili:
        conditions.append(
            'ss.ili_rowid IN (SELECT ilis.rowid FROM ilis WHERE ilis.id = ?)'
        )
        params.append(ili)
    if lexicon_rowids:
        conditions.append(f'ss.lexicon_rowid IN ({_qs(lexicon_rowids)})')
        params.extend(lexicon_rowids)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    query = f'''
          {cte}
        SELECT DISTINCT ss.id, ss.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid=ss.ili_rowid),
                        ss.lexicon_rowid, ss.rowid
          FROM synsets AS ss
          {join}
         {condition}
         {order}
    '''

    rows: Iterator[_Synset] = conn.execute(query, params)
    yield from rows


def get_synsets_for_ilis(
        ilis: Collection[str],
        lexicon_rowids: Sequence[int],
) -> Iterator[_Synset]:
    conn = connect()
    query = f'''
        SELECT DISTINCT ss.id, ss.pos, ili.id, ss.lexicon_rowid, ss.rowid
          FROM synsets as ss
          JOIN ilis as ili ON ss.ili_rowid = ili.rowid
         WHERE ili.id IN ({_qs(ilis)})
           AND ss.lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    params = *ilis, *lexicon_rowids
    result_rows: Iterator[_Synset] = conn.execute(query, params)
    yield from result_rows


def get_synset_relations(
    source_rowids: Collection[int],
    relation_types: Collection[str],
    lexicon_rowids: Sequence[int],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: List = []
    constraint = ''
    if relation_types and '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(source_rowids)
    params.extend(lexicon_rowids)
    query = f'''
          WITH rt(rowid, type) AS
               (SELECT rowid, type FROM relation_types {constraint})
        SELECT DISTINCT rel.type, rel.rowid, tgt.id, tgt.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid = tgt.ili_rowid),
                        tgt.lexicon_rowid, tgt.rowid
          FROM (SELECT rt.type, target_rowid, srel.rowid
                  FROM synset_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                 WHERE source_rowid IN ({_qs(source_rowids)})
                   AND lexicon_rowid IN ({_qs(lexicon_rowids)})
               ) AS rel
          JOIN synsets AS tgt
            ON tgt.rowid = rel.target_rowid
    '''
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows


def get_definitions(
    synset_rowid: int,
    lexicon_rowids: Sequence[int],
) -> List[Tuple[str, str, str, int]]:
    conn = connect()
    query = f'''
        SELECT d.definition,
               d.language,
               (SELECT s.id FROM senses AS s WHERE s.rowid=d.sense_rowid),
               d.rowid
          FROM definitions AS d
         WHERE d.synset_rowid = ?
           AND d.lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    return conn.execute(query, (synset_rowid, *lexicon_rowids)).fetchall()


_SANITIZED_EXAMPLE_PREFIXES = {
    'senses': 'sense',
    'synsets': 'synset',
}


def get_examples(
    rowid: int,
    table: str,
    lexicon_rowids: Sequence[int],
) -> List[Tuple[str, str, int]]:
    conn = connect()
    prefix = _SANITIZED_EXAMPLE_PREFIXES.get(table)
    if prefix is None:
        raise wn.Error(f"'{table}' does not have examples")
    query = f'''
        SELECT example, language, rowid
          FROM {prefix}_examples
         WHERE {prefix}_rowid = ?
           AND lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    return conn.execute(query, (rowid, *lexicon_rowids)).fetchall()


def find_syntactic_behaviours(
    id: str = None,
    lexicon_rowids: Sequence[int] = None,
) -> Iterator[_SyntacticBehaviour]:
    conn = connect()
    query = '''
        SELECT sb.id, sb.frame, s.id
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
          JOIN senses AS s
            ON s.rowid = sbs.sense_rowid
    '''
    conditions: List[str] = []
    params: List = []
    if id:
        conditions.append('sb.id = ?')
        params.append(id)
    if lexicon_rowids:
        conditions.append(f'sb.lexicon_rowid IN ({_qs(lexicon_rowids)})')
        params.extend(lexicon_rowids)
    if conditions:
        query += '\n WHERE ' + '\n   AND '.join(conditions)
    rows: Iterator[Tuple[str, str, str]] = conn.execute(query, params)
    for key, group in itertools.groupby(rows, lambda row: row[0:2]):
        id, frame = key
        sense_ids = [row[2] for row in group]
        yield id, frame, sense_ids


def get_syntactic_behaviours(
    rowid: int,
    lexicon_rowids: Sequence[int],
) -> List[str]:
    conn = connect()
    query = f'''
        SELECT sb.frame
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
         WHERE sbs.sense_rowid = ?
           AND sb.lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    return [row[0] for row in conn.execute(query, (rowid, *lexicon_rowids))]


def _get_senses(
    rowid: int,
    sourcetype: str,
    lexicon_rowids: Sequence[int],
) -> Iterator[_Sense]:
    conn = connect()
    query = f'''
        SELECT s.id, e.id, ss.id, s.lexicon_rowid, s.rowid
          FROM senses AS s
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
         WHERE s.{sourcetype}_rowid = ?
           AND s.lexicon_rowid IN ({_qs(lexicon_rowids)})
         ORDER BY s.{sourcetype}_rank
    '''
    return conn.execute(query, (rowid, *lexicon_rowids))


def get_entry_senses(rowid: int, lexicon_rowids: Sequence[int]) -> Iterator[_Sense]:
    yield from _get_senses(rowid, 'entry', lexicon_rowids)


def get_synset_members(rowid: int, lexicon_rowids: Sequence[int]) -> Iterator[_Sense]:
    yield from _get_senses(rowid, 'synset', lexicon_rowids)


def get_sense_relations(
    source_rowid: int,
    relation_types: Collection[str],
    lexicon_rowids: Sequence[int],
) -> Iterator[_Sense_Relation]:
    params: List = []
    constraint = ''
    if relation_types and '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.append(source_rowid)
    params.extend(lexicon_rowids)
    query = f'''
          WITH rt(rowid, type) AS
               (SELECT rowid, type FROM relation_types {constraint})
        SELECT DISTINCT rel.type, rel.rowid,
                        s.id, e.id, ss.id,
                        s.lexicon_rowid, s.rowid
          FROM (SELECT rt.type, target_rowid, srel.rowid
                  FROM sense_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                 WHERE source_rowid = ?
                   AND lexicon_rowid IN ({_qs(lexicon_rowids)})
               ) AS rel
          JOIN senses AS s
            ON s.rowid = rel.target_rowid
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
    '''
    rows: Iterator[_Sense_Relation] = connect().execute(query, params)
    yield from rows


def get_sense_synset_relations(
        source_rowid: int,
        relation_types: Collection[str],
        lexicon_rowids: Sequence[int],
) -> Iterator[_Synset_Relation]:
    params: List = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.append(source_rowid)
    params.extend(lexicon_rowids)
    query = f'''
          WITH rt(rowid, type) AS
               (SELECT rowid, type FROM relation_types {constraint})
        SELECT DISTINCT rel.type, rel.rowid, ss.id, ss.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid = ss.ili_rowid),
                        ss.lexicon_rowid, ss.rowid
          FROM (SELECT rt.type, target_rowid, srel.rowid
                  FROM sense_synset_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                 WHERE source_rowid = ?
                   AND lexicon_rowid IN ({_qs(lexicon_rowids)})
               ) AS rel
          JOIN synsets AS ss
            ON ss.rowid = rel.target_rowid
    '''
    rows: Iterator[_Synset_Relation] = connect().execute(query, params)
    yield from rows


_SANITIZED_METADATA_TABLES = {
    'ilis': 'ilis',
    'proposed_ilis': 'proposed_ilis',
    'lexicons': 'lexicons',
    'entries': 'entries',
    'senses': 'senses',
    'synsets': 'synsets',
    'sense_relations': 'sense_relations',
    'sense_synset_relations': 'sense_synset_relations',
    'synset_relations': 'synset_relations',
    'sense_examples': 'sense_examples',
    'counts': 'counts',
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


def get_adjposition(rowid: int) -> Optional[str]:
    conn = connect()
    query = 'SELECT adjposition FROM adjpositions WHERE sense_rowid = ?'
    row = conn.execute(query, (rowid,)).fetchone()
    if row:
        return row[0]
    return None


def get_form_pronunciations(form_rowid: int) -> List[_Pronunciation]:
    # TODO: restrict by lexicon ids
    conn = connect()
    query = '''
        SELECT value, variety, notation, phonemic, audio
          FROM pronunciations
         WHERE form_rowid = ?
    '''
    rows: List[_Pronunciation] = conn.execute(query, (form_rowid,)).fetchall()
    return rows


def get_form_tags(form_rowid: int) -> List[_Tag]:
    # TODO: restrict by lexicon ids
    conn = connect()
    query = 'SELECT tag, category FROM tags WHERE form_rowid = ?'
    rows: List[_Tag] = conn.execute(query, (form_rowid,)).fetchall()
    return rows


def get_sense_counts(sense_rowid: int, lexicon_rowids: Sequence[int]) -> List[_Count]:
    conn = connect()
    query = f'''
        SELECT count, rowid
          FROM counts
         WHERE sense_rowid = ?
           AND lexicon_rowid IN ({_qs(lexicon_rowids)})
    '''
    rows: List[_Count] = conn.execute(
        query, (sense_rowid, *lexicon_rowids)
    ).fetchall()
    return rows


def get_lexfile(synset_rowid: int) -> Optional[str]:
    conn = connect()
    query = '''
        SELECT lf.name
          FROM lexfiles AS lf
          JOIN synsets AS ss ON ss.lexfile_rowid = lf.rowid
         WHERE ss.rowid = ?
    '''
    row = conn.execute(query, (synset_rowid,)).fetchone()
    if row is not None and row[0] is not None:
        return row[0]
    return None


def _qs(xs: Collection) -> str: return ','.join('?' * len(xs))
def _vs(xs: Collection) -> str: return ','.join(['(?)'] * len(xs))
def _kws(xs: Collection) -> str: return ','.join(f':{x}' for x in xs)
