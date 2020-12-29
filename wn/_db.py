"""
Storage back-end interface.
"""

from typing import (
    Optional, Any, Dict, Set, List, Tuple, Collection, Iterator, Sequence
)
import sys
import json
import itertools
import sqlite3
import logging

import wn
from wn._types import AnyPath, Metadata
from wn._util import get_progress_handler, resources, short_hash
from wn.project import iterpackages
from wn import constants
from wn import lmf


logger = logging.getLogger('wn')


# Module Constants

DEBUG = False
BATCH_SIZE = 1000
NON_ROWID = 0  # imaginary rowid of non-existent row

# This stores hashes of the schema to check for version differences.
# When the schema changes, the hash will change. If the new hash is
# not added here, the 'test_schema_compatibility' test will fail. It
# is the developer's responsibility to only add compatible schema
# hashes here. If the schema change is not backwards-compatible, they
# clear all old hashes and only put the latest hash here. A hash can
# be generated like this:
#
# >>> import wn
# >>> wn._db.schema_hash()
#
COMPATIBLE_SCHEMA_HASHES = {
    '0cbec124b988d08e428b80d2b749563c2dccfa65',
}

# Common Subqueries

POS_QUERY = '''
    SELECT p.rowid
      FROM parts_of_speech AS p
     WHERE p.pos = ?
'''

ENTRY_QUERY = '''
    SELECT e.rowid
      FROM entries AS e
     WHERE e.id = ?
       AND e.lexicon_rowid = ?
'''

SENSE_QUERY = '''
    SELECT s.rowid
      FROM senses AS s
     WHERE s.id = ?
       AND s.lexicon_rowid = ?
'''

SYNSET_QUERY = '''
    SELECT ss.rowid
      FROM synsets AS ss
     WHERE ss.id = ?
       AND ss.lexicon_rowid = ?
'''


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
_Synset_Relation = Tuple[str, str, str, str, int, int]  # relname, *_Synset
_Sense = Tuple[
    str,  # id
    str,  # entry_id
    str,  # synset_id
    int,  # lexid
    int,  # rowid
]
_Sense_Relation = Tuple[str, str, str, str, int, int]  # relname, *_Sense
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


# Optional metadata is stored as a JSON string

def _adapt_metadata(meta: lmf.Metadata) -> bytes:
    d = {key: val for key, val in zip(meta._fields, meta) if val is not None}
    return json.dumps(d).encode('utf-8')


def _convert_metadata(s: bytes) -> Metadata:  # note: wn._types.Metadata
    return json.loads(s)


def _convert_boolean(s: bytes) -> bool:
    return bool(int(s))


sqlite3.register_adapter(lmf.Metadata, _adapt_metadata)
sqlite3.register_converter('meta', _convert_metadata)
sqlite3.register_converter('boolean', _convert_boolean)


# The _connect() function should be used for all connections

def _connect() -> sqlite3.Connection:
    dbpath = wn.config.database_path
    initialized = dbpath.is_file()
    conn = sqlite3.connect(str(dbpath), detect_types=sqlite3.PARSE_DECLTYPES)
    # foreign key support needs to be enabled for each connection
    conn.execute('PRAGMA foreign_keys = ON')
    # uncomment the following to help with debugging
    if DEBUG:
        conn.set_trace_callback(print)
    if not initialized:
        logger.info('initializing database: %s', dbpath)
        _initialize(conn)
    return conn


def _initialize(conn: sqlite3.Connection) -> None:
    schema = resources.read_text('wn', 'schema.sql')
    with conn:
        conn.executescript(schema)
        # prepare lookup tables
        conn.executemany(
            'INSERT INTO parts_of_speech (pos) VALUES (?)',
            ((pos,) for pos in constants.PARTS_OF_SPEECH))
        conn.executemany(
            'INSERT INTO adjpositions (position) VALUES (?)',
            ((adj,) for adj in constants.ADJPOSITIONS))
        conn.executemany(
            'INSERT INTO synset_relation_types (type) VALUES (?)',
            ((typ,) for typ in constants.SYNSET_RELATIONS))
        conn.executemany(
            'INSERT INTO sense_relation_types (type) VALUES (?)',
            ((typ,) for typ in constants.SENSE_RELATIONS))
        conn.executemany(
            'INSERT INTO lexicographer_files (id, name) VALUES (?,?)',
            ((id, name) for name, id in constants.LEXICOGRAPHER_FILES.items()))


def schema_hash() -> str:
    query = 'SELECT sql FROM sqlite_master WHERE NOT sql ISNULL'
    with _connect() as conn:
        schema = '\n\n'.join(row[0] for row in conn.execute(query))
        return short_hash(schema)


def is_schema_compatible(create: bool = False) -> bool:
    if create or wn.config.database_path.exists():
        return schema_hash() in COMPATIBLE_SCHEMA_HASHES
    else:
        return True


def add(source: AnyPath, progress_handler=get_progress_handler) -> None:
    """Add the LMF file at *source* to the database.

    The file at *source* may be gzip-compressed or plain text XML.

    >>> wn.add('english-wordnet-2020.xml')
    Added ewn:2020 (English WordNet)

    The *progress_handler* parameter takes a callable that is called
    after every block of rows is inserted. The handler function
    should have the following signature:

    .. code-block:: python

       def progress_handler(n: int, **kwargs) -> str:
           ...

    The *n* parameter is the number of rows last inserted into the
    database.  A ``status`` key on the *kwargs* indicates the current
    status of adding the lexicon (``Inspecting``, ``ILI``, ``Synset``,
    etc.). After inspecting the file, a ``max`` keyword on *kwargs*
    indicates the total number of rows to insert.

    """
    logger.info('adding project to database')
    logger.info('  database: %s', wn.config.database_path)
    logger.info('  project file: %s', source)
    for package in iterpackages(source):
        _add_lmf(package.resource_file(), progress_handler)


def _add_lmf(source, progress_handler):
    callback = get_progress_handler(progress_handler, 'Database', '\b', '')

    with _connect() as conn:
        cur = conn.cursor()
        # these two settings increase the risk of database corruption
        # if the system crashes during a write, but they should also
        # make inserts much faster
        cur.execute('PRAGMA synchronous = OFF')
        cur.execute('PRAGMA journal_mode = MEMORY')

        # abort if any lexicon in *source* is already added
        print(f'Checking {source!s}', end='', file=sys.stderr)
        all_infos = list(_precheck(source, cur))

        if not all_infos:
            print(f'\r\033[K{source}: No lexicons found', file=sys.stderr)
            return
        elif all(info.get('skip', False) for info in all_infos):
            print(f'\r\033[K{source}: Some or all lexicons already added',
                  file=sys.stderr)
            return

        # all clear, try to add them
        print(f'\r\033[KReading {source!s}', end='', file=sys.stderr)
        for lexicon, info in zip(lmf.load(source), all_infos):

            if info.get('skip', False):
                print(f'Skipping {info["id"]:info["version"]} ({info["label"]})',
                      file=sys.stderr)
                continue

            sense_ids = lexicon.sense_ids()
            synset_ids = lexicon.synset_ids()

            cur.execute(
                'INSERT INTO lexicons VALUES (null,?,?,?,?,?,?,?,?,?)',
                (lexicon.id,
                 lexicon.label,
                 lexicon.language,
                 lexicon.email,
                 lexicon.license,
                 lexicon.version,
                 lexicon.url,
                 lexicon.citation,
                 lexicon.meta))
            lexid = cur.lastrowid

            counts = info['counts']
            count = sum(counts.get(name, 0) for name in
                        ('LexicalEntry', 'Lemma', 'Form',  # 'Tag',
                         'Sense', 'SenseRelation', 'Example',  # 'Count',
                         # 'SyntacticBehaviour',
                         'Synset', 'Definition',  # 'ILIDefinition',
                         'SynsetRelation'))
            count += counts.get('Synset', 0)  # again for ILIs
            callback(0, count=0, max=count)

            synsets = lexicon.synsets
            entries = lexicon.lexical_entries

            _insert_ilis(synsets, cur, callback)
            _insert_synsets(synsets, lexid, cur, callback)
            _insert_entries(entries, lexid, cur, callback)
            _insert_forms(entries, lexid, cur, callback)
            _insert_senses(entries, lexid, cur, callback)

            _insert_synset_relations(synsets, lexid, cur, callback)
            _insert_sense_relations(entries, lexid, 'sense_relations',
                                    sense_ids, cur, callback)
            _insert_sense_relations(entries, lexid, 'sense_synset_relations',
                                    synset_ids, cur, callback)

            _insert_synset_definitions(synsets, lexid, cur, callback)
            _insert_examples([sense for entry in entries for sense in entry.senses],
                             lexid, 'sense_examples', cur, callback)
            _insert_examples(synsets, lexid, 'synset_examples', cur, callback)
            callback(0, status='')  # clear type string

            print(f'\r\033[KAdded {lexicon.id}:{lexicon.version} ({lexicon.label})',
                  file=sys.stderr)


def _precheck(source, cur):
    for info in lmf.scan_lexicons(source):
        id = info['id']
        version = info['version']
        if cur.execute(
            'SELECT * FROM lexicons WHERE id = ? AND version = ?',
            (id, version)
        ).fetchone():
            info['skip'] = True
        yield info


def _split(sequence):
    i = 0
    for j in range(0, len(sequence), BATCH_SIZE):
        yield sequence[i:j]
        i = j
    yield sequence[i:]


def _insert_ilis(synsets, cur, callback):
    callback(0, status='ILI')
    for batch in _split(synsets):
        data = (
            (synset.ili,
             synset.ili_definition.text if synset.ili_definition else None,
             synset.ili_definition.meta if synset.ili_definition else None)
            for synset in batch if synset.ili and synset.ili != 'in'
        )
        cur.executemany('INSERT OR IGNORE INTO ilis VALUES (?,?,?)', data)
        callback(len(batch))


def _insert_synsets(synsets, lex_id, cur, callback):
    callback(0, status='Synsets')
    query = f'INSERT INTO synsets VALUES (null,?,?,?,({POS_QUERY}),?,?)'
    for batch in _split(synsets):
        data = (
            (synset.id,
             lex_id,
             synset.ili if synset.ili and synset.ili != 'in' else None,
             synset.pos,
             # lexfile_map.get(synset.meta.subject) if synset.meta else None,
             synset.lexicalized,
             synset.meta)
            for synset in batch
        )
        cur.executemany(query, data)
        callback(len(batch))


def _insert_synset_definitions(synsets, lexid, cur, callback):
    callback(0, status='Definitions')
    query = f'INSERT INTO definitions VALUES (({SYNSET_QUERY}),?,?,?)'
    for batch in _split(synsets):
        data = [
            (synset.id, lexid,
             definition.text,
             definition.language,
             # definition.source_sense,
             # lexid,
             definition.meta)
            for synset in batch
            for definition in synset.definitions
        ]
        cur.executemany(query, data)
        callback(len(data))


def _insert_synset_relations(synsets, lexid, cur, callback):
    callback(0, status='Synset Relations')
    type_query = 'SELECT r.rowid FROM synset_relation_types AS r WHERE r.type = ?'
    query = f'''
        INSERT INTO synset_relations
        VALUES (({SYNSET_QUERY}),
                ({SYNSET_QUERY}),
                ({type_query}),
                ?)
    '''
    for batch in _split(synsets):
        data = [
            (synset.id, lexid,
             relation.target, lexid,
             relation.type,
             relation.meta)
            for synset in batch
            for relation in synset.relations
        ]
        cur.executemany(query, data)
        callback(len(data))


def _insert_entries(entries, lex_id, cur, callback):
    callback(0, status='Words')
    query = f'INSERT INTO entries VALUES (null,?,?,({POS_QUERY}),?)'
    for batch in _split(entries):
        data = (
            (entry.id,
             lex_id,
             entry.lemma.pos,
             entry.meta)
            for entry in batch
        )
        cur.executemany(query, data)
        callback(len(batch))


def _insert_forms(entries, lexid, cur, callback):
    callback(0, status='Word Forms')
    query = f'INSERT INTO forms VALUES (null,({ENTRY_QUERY}),?,?,?)'
    for batch in _split(entries):
        forms = []
        for entry in batch:
            forms.append((entry.id, lexid, entry.lemma.form, entry.lemma.script, 0))
            forms.extend((entry.id, lexid, form.form, form.script, i)
                         for i, form in enumerate(entry.forms, 1))
        cur.executemany(query, forms)
        callback(len(forms))


def _insert_senses(entries, lexid, cur, callback):
    callback(0, status='Senses')
    query = f'''
        INSERT INTO senses
        VALUES (null,
                ?,
                ?,
                ({ENTRY_QUERY}),
                ?,
                ({SYNSET_QUERY}),
                ?,
                ?)
    '''
    for batch in _split(entries):
        data = [
            (sense.id,
             lexid,
             entry.id, lexid,
             i,
             sense.synset, lexid,
             # sense.meta.identifier if sense.meta else None,
             # adjmap.get(sense.adjposition),
             sense.lexicalized,
             sense.meta)
            for entry in batch
            for i, sense in enumerate(entry.senses)
        ]
        cur.executemany(query, data)
        callback(len(data))


def _insert_sense_relations(entries, lexid, table, ids, cur, callback):
    callback(0, status='Sense Relations')
    target_query = SENSE_QUERY if table == 'sense_relations' else SYNSET_QUERY
    type_query = 'SELECT r.rowid FROM sense_relation_types AS r WHERE r.type = ?'
    query = f'''
        INSERT INTO {table}
        VALUES (({SENSE_QUERY}),
                ({target_query}),
                ({type_query}),
                ?)
    '''
    for batch in _split(entries):
        data = [
            (sense.id, lexid,
             relation.target, lexid,
             relation.type,
             relation.meta)
            for entry in batch
            for sense in entry.senses
            for relation in sense.relations if relation.target in ids
        ]
        # be careful of SQL injection here
        cur.executemany(query, data)
        callback(len(data))


def _insert_examples(objs, lexid, table, cur, callback):
    callback(0, status='Examples')
    query = f'INSERT INTO {table} VALUES (({SYNSET_QUERY}),?,?,?)'
    for batch in _split(objs):
        data = [
            (obj.id, lexid,
             example.text,
             example.language,
             example.meta)
            for obj in batch
            for example in obj.examples
        ]
        # be careful of SQL injection here
        cur.executemany(query, data)
        callback(len(data))


def remove(lexicon: str) -> None:
    with _connect() as conn:
        for rowid, id, _, _, _, _, version, *_ in find_lexicons(lexicon=lexicon):
            conn.execute('DELETE FROM entries WHERE lexicon_rowid = ?', (rowid,))
            conn.execute('DELETE FROM synsets WHERE lexicon_rowid = ?', (rowid,))
            conn.execute('DELETE FROM syntactic_behaviours WHERE lexicon_rowid = ?',
                         (rowid,))
            conn.execute('DELETE FROM lexicons WHERE rowid = ?', (rowid,))


def find_lexicons(lang: str = None, lexicon: str = None) -> Iterator[_Lexicon]:
    with _connect() as conn:
        for rowid in _get_lexicon_rowids(conn, lang=lang, lexicon=lexicon):
            yield _get_lexicon(conn, rowid)


def get_lexicon(rowid: int) -> _Lexicon:
    with _connect() as conn:
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


def _get_lexicon_rowids(
        conn: sqlite3.Connection,
        lang: str = None,
        lexicon: str = None,
) -> List[int]:
    rows = conn.execute('SELECT rowid, id, version, language FROM lexicons').fetchall()
    lg_match = _get_lexicon_rowids_for_lang(rows, lang)
    lex_match = _get_lexicon_rowids_for_lexicon(rows, lexicon)
    result = lg_match & lex_match
    if rows and not result:
        raise wn.Error(
            f'no lexicon found with lang={lang!r} and lexicon={lexicon!r}'
        )

    return sorted(result)


def _get_lexicon_rowids_for_lang(
        rows: List[Tuple[int, str, str, str]], lang: str = None
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
        rows: List[Tuple[int, str, str, str]], lexicon: str = None
) -> Set[int]:
    lex_match: Set[int] = set()
    lex_specs = lexicon.split() if lexicon else []
    if not lex_specs or '*' in lex_specs or '*:' in lex_specs:
        lex_match.update(row[0] for row in rows)
    else:
        lexmap: Dict[str, Dict[str, int]] = {}
        for rowid, id, version, _ in rows:
            lexmap.setdefault(id, {})[version] = rowid
        for id_ver in lex_specs:
            id, _, ver = id_ver.partition(':')
            if id == '*':
                raise wn.Error("version not allowed when lexicon id is '*'")
            elif id not in lexmap:
                raise wn.Error(f"no lexicon found with id '{id}'")
            if not ver:
                lex_match.add(next(iter(lexmap[id].values())))
            elif ver == '*':
                lex_match.update(lexmap[id].values())
            elif ver not in lexmap[id]:
                raise wn.Error(f"no lexicon with id '{id}' found with version '{ver}'")
            else:
                lex_match.add(lexmap[id][ver])
    return lex_match


def find_entries(
        id: str = None,
        form: str = None,
        pos: str = None,
        lexicon_rowids: Sequence[int] = None,
) -> Iterator[_Word]:
    with _connect() as conn:
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
    with _connect() as conn:
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
    with _connect() as conn:
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
        lexicon_rowids: Sequence[int] = None,
) -> Iterator[_Synset]:
    with _connect() as conn:
        if lexicon_rowids is None:
            lexicon_rowids = _get_lexicon_rowids(conn)
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
    params: List = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.extend(source_rowids)
    with _connect() as conn:
        query = f'''
              WITH relation_types(type_rowid, type) AS  -- relation type lookup
                   (SELECT t.rowid, t.type
                      FROM synset_relation_types AS t
                    {constraint})
            SELECT DISTINCT rel.type, tgt.id, p.pos, tgt.ili,
                            tgt.lexicon_rowid, tgt.rowid
              FROM (SELECT type, target_rowid
                      FROM synset_relations
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
    with _connect() as conn:
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
    prefix = _SANITIZED_EXAMPLE_PREFIXES.get(table)
    if prefix is None:
        raise wn.Error(f"'{table}' does not have examples")
    with _connect() as conn:
        query = f'''
            SELECT example, language, rowid
              FROM {prefix}_examples
             WHERE {prefix}_rowid = ?
        '''
        return conn.execute(query, (rowid,)).fetchall()


def _get_senses(rowid: int, sourcetype: str) -> Iterator[_Sense]:
    with _connect() as conn:
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
    params: List = []
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    params.append(source_rowid)
    with _connect() as conn:
        query = f'''
              WITH relation_types(type_rowid, type) AS  -- relation type lookup
                   (SELECT t.rowid, t.type
                      FROM sense_relation_types AS t
                    {constraint})
            SELECT DISTINCT rel.type, s.id, e.id, ss.id, s.lexicon_rowid, s.rowid
              FROM (SELECT type, target_rowid
                      FROM sense_relations
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
    params: List = [source_rowid]
    constraint = ''
    if '*' not in relation_types:
        constraint = f'WHERE t.type IN ({_qs(relation_types)})'
        params.extend(relation_types)
    with _connect() as conn:
        query = f'''
              WITH relation_types(type_rowid, type) AS  -- relation type lookup
                   (SELECT t.rowid, t.type
                      FROM sense_relation_types AS t
                    {constraint})
            SELECT DISTINCT rel.type, ss.id, p.pos, ss.ili, ss.lexicon_rowid, ss.rowid
              FROM (SELECT type, target_rowid
                      FROM sense_synset_relations
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
}


def get_metadata(rowid: int, table: str) -> Metadata:
    tablename = _SANITIZED_METADATA_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not contain metadata")
    with _connect() as conn:
        query = f'SELECT metadata FROM {tablename} WHERE rowid=?'
        return conn.execute(query, (rowid,)).fetchone()[0] or {}


_SANITIZED_LEXICALIZED_TABLES = {
    'senses': 'senses',
    'synsets': 'synsets',
}


def get_lexicalized(rowid: int, table: str) -> bool:
    tablename = _SANITIZED_LEXICALIZED_TABLES.get(table)
    if tablename is None:
        raise wn.Error(f"'{table}' does not mark lexicalization")
    if rowid == NON_ROWID:
        return False
    with _connect() as conn:
        query = f'SELECT lexicalized FROM {tablename} WHERE rowid=?'
        return conn.execute(query, (rowid,)).fetchone()[0]


def _qs(xs: Collection) -> str: return ','.join('?' * len(xs))
def _kws(xs: Collection) -> str: return ','.join(f':{x}' for x in xs)
