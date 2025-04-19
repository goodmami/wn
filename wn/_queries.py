"""
Database retrieval queries.
"""

from collections.abc import Collection, Iterator, Sequence
from typing import Optional, Union, cast
import itertools

import wn
from wn._types import Metadata
from wn._db import connect
from wn._util import split_lexicon_specifier


# Local Types

_Pronunciation = tuple[
    str,   # value
    Optional[str],   # variety
    Optional[str],   # notation
    bool,  # phonemic
    Optional[str],   # audio
]
_Tag = tuple[str, str]  # tag, category
_Form = tuple[
    str,            # form
    Optional[str],  # id
    Optional[str],  # script
    list[_Pronunciation],  # pronunciations
    list[_Tag],  # tags
]
_Word = tuple[
    str,          # id
    str,          # pos
    str,          # lexicon specifier
]
_Synset = tuple[
    str,  # id
    str,  # pos
    str,  # ili
    str,  # lexicon specifier
]
_Synset_Relation = tuple[
    str,  # rel_name
    str,  # lexicon
    Metadata,  # metadata
    str,  # srcid
    str,  # _Synset...
    str,
    str,
    str,
]
_Definition = tuple[
    str,  # text
    str,  # language
    str,  # sourceSense
    Optional[Metadata],  # metadata
]
_Example = tuple[
    str,  # text
    str,  # language
    Optional[Metadata],  # metadata
]
_Sense = tuple[
    str,  # id
    str,  # entry_id
    str,  # synset_id
    str,  # lexicon specifier
]
_Sense_Relation = tuple[
    str,  # rel_name
    str,  # lexicon
    Metadata,  # metadata
    str,  # _Sense...
    str,
    str,
    str,
]
_Count = tuple[int, Metadata]  # count, metadata
_SyntacticBehaviour = tuple[
    str,       # id
    str,       # frame
    list[str]  # sense ids
]
_ExistingILI = tuple[
    str,  # id
    str,  # status
    Optional[str],  # definition
]
_ProposedILI = tuple[
    None,  # id
    str,  # status
    str,  # definition
    str,  # synset id
    str,  # lexicon
]
_Lexicon = tuple[
    str,       # id
    str,       # label
    str,       # language
    str,       # email
    str,       # license
    str,       # version
    str,       # url
    str,       # citation
    str,       # logo
    Optional[Metadata],  # metadata
]


def resolve_lexicon_specifiers(
    lexicon: str,
    lang: Optional[str] = None,
) -> list[str]:
    cur = connect().cursor()
    specifiers: list[str] = []
    for specifier in lexicon.split():
        limit = '-1' if '*' in lexicon else '1'
        if ':' not in specifier:
            specifier += ':*'
        query = f'''
            SELECT DISTINCT id || ":" || version
              FROM lexicons
             WHERE id || ":" || version GLOB :specifier
               AND (:language ISNULL OR language = :language)
             LIMIT {limit}
        '''
        params = {'specifier': specifier, 'language': lang}
        specifiers.extend(row[0] for row in cur.execute(query, params))
    # only raise an error when the query specifies something
    if not specifiers and (lexicon != '*' or lang is not None):
        raise wn.Error(
            f'no lexicon found with lang={lang!r} and lexicon={lexicon!r}'
        )
    return specifiers


def get_lexicon(lexicon: str) -> _Lexicon:
    id, ver = split_lexicon_specifier(lexicon)
    query = '''
        SELECT DISTINCT id, label, language, email, license,
                        version, url, citation, logo, metadata
        FROM lexicons
        WHERE id = ? AND version = ?
    '''
    row: Optional[_Lexicon] = connect().execute(query, (id, ver)).fetchone()
    if row is None:
        raise LookupError(lexicon)  # should we have a WnLookupError?
    return row


def get_modified(lexicon: str) -> bool:
    query = 'SELECT modified FROM lexicons WHERE id || ":" || version = ?'
    return connect().execute(query, (lexicon,)).fetchone()[0]


def get_lexicon_dependencies(lexicon: str) -> list[tuple[str, str, bool]]:
    query = '''
        SELECT provider_id || ":" || provider_version, provider_url, provider_rowid
          FROM lexicon_dependencies
          JOIN lexicons AS lex ON lex.rowid = dependent_rowid
         WHERE lex.id || ":" || lex.version = ?
    '''
    return [
        (spec, url, rowid is not None)
        for spec, url, rowid in connect().execute(query, (lexicon,))
    ]


def get_lexicon_extension_bases(lexicon: str, depth: int = -1) -> list[str]:
    query = '''
          WITH RECURSIVE ext(x, d) AS
               (SELECT base_rowid, 1
                  FROM lexicon_extensions
                  JOIN lexicons AS lex ON lex.rowid = extension_rowid
                 WHERE lex.id || ":" || lex.version = :specifier
                 UNION SELECT base_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON extension_rowid = x)
        SELECT baselex.id || ":" || baselex.version
          FROM ext
          JOIN lexicons AS baselex ON baselex.rowid = ext.x
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    '''
    rows = connect().execute(query, {'specifier': lexicon, 'depth': depth})
    return [row[0] for row in rows]


def get_lexicon_extensions(lexicon: str, depth: int = -1) -> list[str]:
    query = '''
          WITH RECURSIVE ext(x, d) AS
               (SELECT extension_rowid, 1
                  FROM lexicon_extensions
                  JOIN lexicons AS lex ON lex.rowid = base_rowid
                 WHERE lex.id || ":" || lex.version = :specifier
                 UNION SELECT extension_rowid, d+1
                         FROM lexicon_extensions
                         JOIN ext ON base_rowid = x)
        SELECT extlex.id || ":" || extlex.version
          FROM ext
          JOIN lexicons AS extlex ON extlex.rowid = ext.x
         WHERE :depth < 0 OR d <= :depth
         ORDER BY d
    '''
    rows = connect().execute(query, {'specifier': lexicon, 'depth': depth})
    return [row[0] for row in rows]


def find_ilis(
    id: Optional[str] = None,
    status: Optional[str] = None,
    lexicons: Sequence[str] = (),
) -> Iterator[Union[_ExistingILI, _ProposedILI]]:
    if status == 'proposed' and not id:
        yield from find_proposed_ilis(lexicons=lexicons)
    else:
        yield from find_existing_ilis(id=id, status=status, lexicons=lexicons)


def find_existing_ilis(
    id: Optional[str] = None,
    status: Optional[str] = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_ExistingILI]:
    query = '''
        SELECT DISTINCT i.id, ist.status, i.definition
          FROM ilis AS i
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
    '''
    conditions: list[str] = []
    params: list = []
    if id:
        conditions.append('i.id = ?')
        params.append(id)
    if status:
        conditions.append('ist.status = ?')
        params.append(status)
    if lexicons:
        # this runs much faster than just adding a condition
        query = '''
        SELECT DISTINCT i.id, ist.status, i.definition
          FROM lexicons as lex
          JOIN synsets AS ss ON ss.lexicon_rowid = lex.rowid
          JOIN ilis AS i ON i.rowid = ss.ili_rowid
          JOIN ili_statuses AS ist ON i.status_rowid = ist.rowid
        '''
        conditions.append(f'lex.id || ":" || lex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)

    if conditions:
        query += ' WHERE ' + '\n           AND '.join(conditions)

    yield from connect().execute(query, params)


def find_proposed_ilis(
    synset_id: Optional[str] = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_ProposedILI]:
    query = '''
    SELECT null, "proposed", definition, ss.id, lex.id || ":" || lex.version
      FROM proposed_ilis
      JOIN synsets AS ss ON ss.rowid = synset_rowid
      JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
    '''
    conditions: list[str] = []
    params: list = []
    if synset_id is not None:
        conditions.append('ss.id = ?')
        params.append(synset_id)
    if lexicons:
        conditions.append(f'lex.id || ":" || lex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)
    if conditions:
        query += ' WHERE ' + '\n           AND '.join(conditions)
    yield from connect().execute(query, params)


def find_entries(
    id: Optional[str] = None,
    forms: Sequence[str] = (),
    pos: Optional[str] = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Word]:
    conn = connect()
    cte = ''
    params: list = []
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
    if lexicons:
        conditions.append(f'lex.id || ":" || lex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    query = f'''
          {cte}
        SELECT DISTINCT e.id, e.pos, lex.id || ":" || lex.version
          FROM entries AS e
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
         {condition}
         ORDER BY e.rowid ASC
    '''

    rows: Iterator[_Word] = conn.execute(query, params)
    yield from rows


def find_senses(
    id: Optional[str] = None,
    forms: Sequence[str] = (),
    pos: Optional[str] = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Sense]:
    conn = connect()
    cte = ''
    params: list = []
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
    if lexicons:
        conditions.append(f'slex.id || ":" || slex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    query = f'''
          {cte}
        SELECT DISTINCT s.id, e.id, ss.id, slex.id || ":" || slex.version
          FROM senses AS s
          JOIN entries AS e ON e.rowid = s.entry_rowid
          JOIN synsets AS ss ON ss.rowid = s.synset_rowid
          JOIN lexicons AS slex ON slex.rowid = s.lexicon_rowid
         {condition}
         ORDER BY s.rowid ASC
    '''

    rows: Iterator[_Sense] = conn.execute(query, params)
    yield from rows


def find_synsets(
    id: Optional[str] = None,
    forms: Sequence[str] = (),
    pos: Optional[str] = None,
    ili: Optional[str] = None,
    lexicons: Sequence[str] = (),
    normalized: bool = False,
    search_all_forms: bool = False,
) -> Iterator[_Synset]:
    conn = connect()
    cte = ''
    join = ''
    conditions = []
    order = ''
    params: list = []
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
    if lexicons:
        conditions.append(f'sslex.id || ":" || sslex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)

    condition = ''
    if conditions:
        condition = 'WHERE ' + '\n           AND '.join(conditions)

    if not order:
        order = 'ORDER BY ss.rowid ASC'

    query = f'''
          {cte}
        SELECT DISTINCT ss.id, ss.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid=ss.ili_rowid),
                        sslex.id || ":" || sslex.version
          FROM synsets AS ss
          JOIN lexicons AS sslex ON sslex.rowid = ss.lexicon_rowid
          {join}
         {condition}
         {order}
    '''

    rows: Iterator[_Synset] = conn.execute(query, params)
    yield from rows


def get_entry_forms(id: str, lexicons: Sequence[str]) -> Iterator[_Form]:
    form_query = f'''
        SELECT f.rowid, f.form, f.id, f.script
          FROM forms AS f
          JOIN entries AS e ON e.rowid = entry_rowid
          JOIN lexicons AS lex ON lex.rowid = e.lexicon_rowid
         WHERE e.id = ?
           AND lex.id || ":" || lex.version IN ({_qs(lexicons)})
         ORDER BY f.rank
    '''
    pron_query = '''
        SELECT value, variety, notation, phonemic, audio
          FROM pronunciations
         WHERE form_rowid = ?
    '''
    tag_query = 'SELECT tag, category FROM tags WHERE form_rowid = ?'

    cur = connect().cursor()
    for row in cur.execute(form_query, (id, *lexicons)).fetchall():
        params = (row[0],)
        prons: list[_Pronunciation] = cur.execute(pron_query, params).fetchall()
        tags: list[_Tag] = cur.execute(tag_query, params).fetchall()
        yield (*row[1:], prons, tags)


def get_synsets_for_ilis(
    ilis: Collection[str],
    lexicons: Sequence[str],
) -> Iterator[_Synset]:
    conn = connect()
    query = f'''
        SELECT DISTINCT ss.id, ss.pos, ili.id,
                        sslex.id || ":" || sslex.version
          FROM synsets as ss
          JOIN ilis as ili ON ss.ili_rowid = ili.rowid
          JOIN lexicons AS sslex ON sslex.rowid = ss.lexicon_rowid
         WHERE ili.id IN ({_qs(ilis)})
           AND sslex.id || ":" || sslex.version IN ({_qs(lexicons)})
    '''
    params = *ilis, *lexicons
    result_rows: Iterator[_Synset] = conn.execute(query, params)
    yield from result_rows


def get_synset_relations(
    synset_id: str,
    synset_lexicon: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: list = []
    constraint = ''
    if relation_types and '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(lexicons)
    params.append(synset_id)
    params.append(synset_lexicon)
    query = f'''
        WITH
          reltypes(rowid) AS
            (SELECT rowid FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons
              WHERE id || ":" || version IN ({_vs(lexicons)})),
          srcsynset(rowid) AS
            (SELECT ss.rowid
               FROM synsets AS ss
               JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
              WHERE ss.id = ?
                AND lex.id || ":" || lex.version = ?),
          matchingrels(rowid) AS
            (SELECT srel.rowid
               FROM synset_relations AS srel
              WHERE srel.source_rowid IN srcsynset
                AND srel.lexicon_rowid IN lexrowids
                AND srel.type_rowid IN reltypes)
        SELECT DISTINCT rt.type, lex.id || ":" || lex.version, srel.metadata,
                        src.id, tgt.id, tgt.pos, tgtili.id,
                        tgtlex.id || ":" || tgtlex.version
          FROM matchingrels AS mr
          JOIN synset_relations AS srel ON srel.rowid=mr.rowid
          JOIN relation_types AS rt ON rt.rowid=srel.type_rowid
          JOIN synsets AS src ON src.rowid = srel.source_rowid
          JOIN synsets AS tgt ON tgt.rowid = srel.target_rowid
          JOIN lexicons AS lex ON lex.rowid = srel.lexicon_rowid
          JOIN lexicons AS tgtlex ON tgtlex.rowid = tgt.lexicon_rowid
          LEFT JOIN ilis AS tgtili ON tgtili.rowid = tgt.ili_rowid  -- might be null
         WHERE tgt.lexicon_rowid IN lexrowids  -- ensure target is included
    '''
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows


def get_expanded_synset_relations(
    ili_id: str,
    relation_types: Collection[str],
    expands: Sequence[str],
) -> Iterator[_Synset_Relation]:
    conn = connect()
    params: list = []
    constraint = ''
    if relation_types and '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(expands)
    params.append(ili_id)
    query = f'''
        WITH
          reltypes(rowid) AS
            (SELECT rowid FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE id || ":" || version IN ({_vs(expands)})),
          srcsynset(rowid) AS
            (SELECT ss.rowid
               FROM synsets AS ss
               JOIN ilis ON ilis.rowid = ss.ili_rowid
              WHERE ilis.id = ?
                AND ss.lexicon_rowid IN lexrowids),
          matchingrels(rowid) AS
            (SELECT srel.rowid
               FROM synset_relations AS srel
              WHERE srel.source_rowid IN srcsynset
                AND srel.lexicon_rowid IN lexrowids
                AND srel.type_rowid IN reltypes)
        SELECT DISTINCT rt.type, lex.id || ":" || lex.version, srel.metadata,
                        src.id, tgt.id, tgt.pos, tgtili.id,
                        tgtlex.id || ":" || tgtlex.version
          FROM matchingrels AS mr
          JOIN synset_relations AS srel ON srel.rowid=mr.rowid
          JOIN relation_types AS rt ON rt.rowid=srel.type_rowid
          JOIN synsets AS src ON src.rowid = srel.source_rowid
          JOIN synsets AS tgt ON tgt.rowid = srel.target_rowid
          JOIN ilis AS tgtili ON tgtili.rowid = tgt.ili_rowid
          JOIN lexicons AS lex ON lex.rowid = srel.lexicon_rowid
          JOIN lexicons AS tgtlex ON tgtlex.rowid = tgt.lexicon_rowid
    '''
    result_rows: Iterator[_Synset_Relation] = conn.execute(query, params)
    yield from result_rows

def get_definitions(
    synset_id: str,
    lexicons: Sequence[str],
) -> list[_Definition]:
    conn = connect()
    query = f'''
        SELECT d.definition,
               d.language,
               (SELECT s.id FROM senses AS s WHERE s.rowid=d.sense_rowid),
               d.metadata
          FROM definitions AS d
          JOIN synsets AS ss ON ss.rowid = d.synset_rowid
          JOIN lexicons AS lex ON lex.rowid = d.lexicon_rowid
         WHERE ss.id = ?
           AND lex.id || ":" || lex.version IN ({_qs(lexicons)})
    '''
    return conn.execute(query, (synset_id, *lexicons)).fetchall()


_SANITIZED_EXAMPLE_PREFIXES = {
    'senses': 'sense',
    'synsets': 'synset',
}


def get_examples(
    id: str,
    table: str,
    lexicons: Sequence[str],
) -> list[_Example]:
    conn = connect()
    prefix = _SANITIZED_EXAMPLE_PREFIXES.get(table)
    if prefix is None:
        raise wn.Error(f"'{table}' does not have examples")
    query = f'''
        SELECT ex.example, ex.language, ex.metadata
          FROM {prefix}_examples AS ex
          JOIN {table} AS tbl ON tbl.rowid = ex.{prefix}_rowid
          JOIN lexicons AS lex ON lex.rowid = ex.lexicon_rowid
         WHERE tbl.id = ?
           AND lex.id || ":" || lex.version IN ({_qs(lexicons)})
    '''
    return conn.execute(query, (id, *lexicons)).fetchall()


def find_syntactic_behaviours(
    id: Optional[str] = None,
    lexicons: Sequence[str] = (),
) -> Iterator[_SyntacticBehaviour]:
    conn = connect()
    query = '''
        SELECT sb.id, sb.frame, s.id
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
          JOIN senses AS s
            ON s.rowid = sbs.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = sb.lexicon_rowid
    '''
    conditions: list[str] = []
    params: list = []
    if id:
        conditions.append('sb.id = ?')
        params.append(id)
    if lexicons:
        conditions.append(f'lex.id || ":" || lex.version IN ({_qs(lexicons)})')
        params.extend(lexicons)
    if conditions:
        query += '\n WHERE ' + '\n   AND '.join(conditions)
    rows: Iterator[tuple[str, str, str]] = conn.execute(query, params)
    for key, group in itertools.groupby(rows, lambda row: row[0:2]):
        id, frame = cast(tuple[str, str], key)
        sense_ids = [row[2] for row in group]
        yield id, frame, sense_ids


def get_syntactic_behaviours(
    sense_id: str,
    lexicons: Sequence[str],
) -> list[str]:
    conn = connect()
    query = f'''
        SELECT sb.frame
          FROM syntactic_behaviours AS sb
          JOIN syntactic_behaviour_senses AS sbs
            ON sbs.syntactic_behaviour_rowid = sb.rowid
          JOIN senses AS s ON s.rowid = sbs.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = sb.lexicon_rowid
         WHERE s.id = ?
           AND lex.id || ":" || lex.version IN ({_qs(lexicons)})
    '''
    return [row[0] for row in conn.execute(query, (sense_id, *lexicons))]


def _get_senses(
    id: str,
    sourcetype: str,
    lexicons: Sequence[str],
) -> Iterator[_Sense]:
    conn = connect()
    if sourcetype == 'entry':
        sourcealias = 'e'
    elif sourcetype == 'synset':
        sourcealias = 'ss'
    else:
        raise wn.Error(f'invalid sense source type: {sourcetype}')
    query = f'''
        SELECT s.id, e.id, ss.id, slex.id || ":" || slex.version
          FROM senses AS s
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
          JOIN lexicons AS slex
            ON slex.rowid = s.lexicon_rowid
         WHERE {sourcealias}.id = ?
           AND slex.id || ":" || slex.version IN ({_qs(lexicons)})
         ORDER BY s.{sourcetype}_rank
    '''
    return conn.execute(query, (id, *lexicons))


def get_entry_senses(
    sense_id: str,
    lexicons: Sequence[str],
) -> Iterator[_Sense]:
    yield from _get_senses(sense_id, 'entry', lexicons)


def get_synset_members(
    synset_id: str,
    lexicons: Sequence[str],
) -> Iterator[_Sense]:
    yield from _get_senses(synset_id, 'synset', lexicons)


def get_sense_relations(
    sense_id: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
) -> Iterator[_Sense_Relation]:
    params: list = []
    constraint = ''
    if relation_types and '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(lexicons)
    params.append(sense_id)
    query = f'''
        WITH
          rt(rowid, type) AS
            (SELECT rowid, type FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE id || ":" || version IN ({_vs(lexicons)}))
        SELECT DISTINCT rel.type, rel.lexicon, rel.metadata,
                        s.id, e.id, ss.id,
                        slex.id || ":" || slex.version
          FROM (SELECT rt.type,
                       lex.id || ":" || lex.version AS lexicon,
                       srel.metadata AS metadata,
                       target_rowid
                  FROM sense_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                  JOIN lexicons AS lex ON srel.lexicon_rowid = lex.rowid
                  JOIN senses AS s ON s.rowid = srel.source_rowid
                 WHERE s.id = ?
                   AND srel.lexicon_rowid IN lexrowids
               ) AS rel
          JOIN senses AS s
            ON s.rowid = rel.target_rowid
           AND s.lexicon_rowid IN lexrowids
          JOIN lexicons AS slex
            ON slex.rowid = s.lexicon_rowid
          JOIN entries AS e
            ON e.rowid = s.entry_rowid
          JOIN synsets AS ss
            ON ss.rowid = s.synset_rowid
    '''
    rows: Iterator[_Sense_Relation] = connect().execute(query, params)
    yield from rows


def get_sense_synset_relations(
    sense_id: str,
    relation_types: Collection[str],
    lexicons: Sequence[str],
) -> Iterator[_Synset_Relation]:
    params: list = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(lexicons)
    params.append(sense_id)
    query = f'''
        WITH
          rt(rowid, type) AS
            (SELECT rowid, type FROM relation_types {constraint}),
          lexrowids(rowid) AS
            (SELECT rowid FROM lexicons WHERE id || ":" || version IN ({_vs(lexicons)}))
        SELECT DISTINCT rel.type, rel.lexicon, rel.metadata,
                        rel.source_rowid, tgt.id, tgt.pos,
                        (SELECT ilis.id FROM ilis WHERE ilis.rowid = tgt.ili_rowid),
                        tgtlex.id || ":" || tgtlex.version
          FROM (SELECT rt.type,
                       lex.id || ":" || lex.version AS lexicon,
                       srel.metadata AS metadata,
                       source_rowid,
                       target_rowid
                  FROM sense_synset_relations AS srel
                  JOIN rt ON srel.type_rowid = rt.rowid
                  JOIN lexicons AS lex ON srel.lexicon_rowid = lex.rowid
                  JOIN senses AS s ON s.rowid = srel.source_rowid
                 WHERE s.id = ?
                   AND srel.lexicon_rowid IN lexrowids
               ) AS rel
          JOIN synsets AS tgt
            ON tgt.rowid = rel.target_rowid
           AND tgt.lexicon_rowid IN lexrowids
          JOIN lexicons AS tgtlex
            ON tgtlex.rowid = tgt.lexicon_rowid
    '''
    rows: Iterator[_Synset_Relation] = connect().execute(query, params)
    yield from rows


_SANITIZED_METADATA_TABLES = {
    # 'ilis': 'ilis',
    # 'proposed_ilis': 'proposed_ilis',
    # 'lexicons': 'lexicons',
    'entries': 'entries',
    'senses': 'senses',
    'synsets': 'synsets',
    # 'sense_relations': 'sense_relations',
    # 'sense_synset_relations': 'sense_synset_relations',
    # 'synset_relations': 'synset_relations',
    # 'sense_examples': 'sense_examples',
    # 'counts': 'counts',
    # 'synset_examples': 'synset_examples',
    # 'definitions': 'definitions',
}


def get_metadata(
    id: str, lexicon: str, table: str
) -> Metadata:
    tablename = _SANITIZED_METADATA_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not contain metadata")
    query = f'''
        SELECT tbl.metadata
          FROM {tablename} AS tbl
          JOIN lexicons AS lex ON lex.rowid = lexicon_rowid
         WHERE tbl.id=?
           AND lex.id || ":" || lex.version = ?
    '''
    return connect().execute(query, (id, lexicon)).fetchone()[0] or {}


def get_ili_metadata(id: str) -> Metadata:
    query = 'SELECT metadata FROM ilis WHERE id = ?'
    return connect().execute(query, (id,)).fetchone()[0] or {}


def get_proposed_ili_metadata(synset: str, lexicon: str) -> Metadata:
    query = '''
        SELECT pili.metadata
          FROM proposed_ilis AS pili
          JOIN synsets AS ss ON ss.rowid = synset_rowid
          JOIN lexicons AS lex ON lex.rowid = ss.lexicon_rowid
         WHERE ss.id = ?
           AND lex.id || ":" || lex.version = ?
    '''
    return connect().execute(query, (synset, lexicon)).fetchone()[0] or {}


_SANITIZED_LEXICALIZED_TABLES = {
    'senses': 'senses',
    'synsets': 'synsets',
}


def get_lexicalized(id: str, lexicon: str, table: str) -> bool:
    conn = connect()
    tablename = _SANITIZED_LEXICALIZED_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not mark lexicalization")
    if not id or not lexicon:
        return False
    query = f'''
        SELECT tbl.lexicalized
          FROM {tablename} AS tbl
          JOIN lexicons AS lex ON lex.rowid = tbl.lexicon_rowid
         WHERE tbl.id = ?
           AND lex.id || ":" || lex.version = ?
    '''
    return conn.execute(query, (id, lexicon)).fetchone()[0]


def get_adjposition(sense_id: str, lexicon: str) -> Optional[str]:
    conn = connect()
    query = '''
        SELECT adjposition
          FROM adjpositions
          JOIN senses AS s ON s.rowid = sense_rowid
          JOIN lexicons AS lex ON lex.rowid = s.lexicon_rowid
         WHERE s.id = ?
           AND lex.id || ":" || lex.version = ?
    '''
    row = conn.execute(query, (sense_id, lexicon)).fetchone()
    if row:
        return row[0]
    return None


def get_sense_counts(sense_id: str, lexicons: Sequence[str]) -> list[_Count]:
    conn = connect()
    query = f'''
        SELECT c.count, c.metadata
          FROM counts AS c
          JOIN senses AS s ON s.rowid = c.sense_rowid
          JOIN lexicons AS lex ON lex.rowid = c.lexicon_rowid
         WHERE s.id = ?
           AND lex.id || ":" || lex.version IN ({_qs(lexicons)})
    '''
    rows: list[_Count] = conn.execute(
        query, (sense_id, *lexicons)
    ).fetchall()
    return rows


def get_lexfile(synset_id: str, lexicon: str) -> Optional[str]:
    conn = connect()
    query = '''
        SELECT lf.name
          FROM lexfiles AS lf
          JOIN synsets AS ss ON ss.lexfile_rowid = lf.rowid
          JOIN lexicons AS lex on lex.rowid = ss.lexicon_rowid
         WHERE ss.id = ?
           AND lex.id || ":" || lex.version = ?
    '''
    row = conn.execute(query, (synset_id, lexicon)).fetchone()
    if row is not None and row[0] is not None:
        return row[0]
    return None


def _qs(xs: Collection) -> str: return ','.join('?' * len(xs))
def _vs(xs: Collection) -> str: return ','.join(['(?)'] * len(xs))
def _kws(xs: Collection) -> str: return ','.join(f':{x}' for x in xs)
