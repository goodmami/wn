"""
Storage back-end interface.
"""

from typing import List, Tuple, Collection, Iterator
import sys
from pathlib import Path
import gzip
import tempfile
import shutil
import json
import itertools
import sqlite3
try:
    import importlib.resources as resources
except ImportError:
    # 3.6 backport
    # for the mypy error, see: https://github.com/python/mypy/issues/1153
    import importlib_resources as resources  # type: ignore

import wn
from wn._types import AnyPath
from wn._util import is_gzip, progress_bar
from wn import constants
from wn import lmf

DBFILENAME = 'wn.db'
BATCH_SIZE = 1000

_Word = Tuple[str, str, List[str]]  # id, pos, forms
_Synset = Tuple[str, str, str]      # id, pos, ili
_Sense = Tuple[str, str, str]       # id, entry_id, synset_id


# Optional metadata is stored as a JSON string

def _adapt_metadata(meta: lmf.Metadata) -> bytes:
    d = {key: val for key, val in zip(meta._fields, meta) if val is not None}
    return json.dumps(d).encode('utf-8')


def _convert_metadata(s: bytes) -> lmf.Metadata:
    d = json.loads(s)
    return lmf.Metadata(*(d.get(key) for key in lmf.Metadata._fields))


def _convert_boolean(s: bytes) -> bool:
    return bool(int(s))


sqlite3.register_adapter(lmf.Metadata, _adapt_metadata)
sqlite3.register_converter('meta', _convert_metadata)
sqlite3.register_converter('boolean', _convert_boolean)


# The _connect() function should be used for all connections

def _connect() -> sqlite3.Connection:
    dbpath = wn.config.data_directory / DBFILENAME
    initialized = dbpath.is_file()
    conn = sqlite3.connect(dbpath)
    # foreign key support needs to be enabled for each connection
    conn.execute('PRAGMA foreign_keys = ON')
    # uncomment the following to help with debugging
    # conn.set_trace_callback(print)
    if not initialized:
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


def add(source: AnyPath) -> None:
    """Add the LMF file at *source* to the database.

    The file at *source* may be gzip-compressed or plain text XML.

    >>> wn.add('english-wordnet-2020.xml')
    Checking english-wordnet-2020.xml
    Reading english-wordnet-2020.xml
    Building [###############################] (1337590/1337590)

    """
    source = Path(source)

    if is_gzip(source):
        try:
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                with gzip.open(source, 'rb') as src:
                    shutil.copyfileobj(src, tmp)
            _add_lmf(tmp_path)
        finally:
            tmp_path.unlink()
    else:
        _add_lmf(source)


def _add_lmf(source):
    with _connect() as conn:
        cur = conn.cursor()
        # abort if any lexicon in *source* is already added
        print(f'Checking {source!s}', file=sys.stderr)
        all_counts = list(_precheck(source, cur))
        posmap, adjmap, sense_relmap, synset_relmap, lexname_map = _build_maps(cur)
        # all clear, try to add them

        print(f'Reading {source!s}', file=sys.stderr)
        for lexicon, counts in zip(lmf.load(source), all_counts):
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

            count = sum(counts.get(name, 0) for name in
                        ('LexicalEntry', 'Lemma', 'Form',  # 'Tag',
                         'Sense', 'SenseRelation', 'Example',  # 'Count',
                         # 'SyntacticBehaviour',
                         'Synset', 'Definition',  # 'ILIDefinition',
                         'SynsetRelation'))
            count += counts.get('Synset', 0)  # again for ILIs
            indicator = progress_bar('Building ', max=count)

            synsets = lexicon.synsets
            entries = lexicon.lexical_entries

            _insert_ilis(synsets, cur, indicator)
            _insert_synsets(synsets, lexid, posmap, lexname_map, cur, indicator)
            _insert_entries(entries, lexid, posmap, cur, indicator)
            _insert_forms(entries, cur, indicator)
            _insert_senses(entries, adjmap, cur, indicator)

            _insert_synset_relations(synsets, synset_relmap, cur, indicator)
            _insert_sense_relations(entries, sense_relmap, 'sense_relations',
                                    sense_ids, cur, indicator)
            _insert_sense_relations(entries, sense_relmap, 'sense_synset_relations',
                                    synset_ids, cur, indicator)

            _insert_synset_definitions(synsets, cur, indicator)
            _insert_examples([sense for entry in entries for sense in entry.senses],
                             'sense_examples', cur, indicator)
            _insert_examples(synsets, 'synset_examples', cur, indicator)

            indicator.close()
            print(file=sys.stderr)


def _precheck(source, cur):
    for info in lmf.scan_lexicons(source):
        id = info['id']
        version = info['version']
        row = cur.execute(
            'SELECT * FROM lexicons WHERE id=? AND version=?',
            (id, version)
        ).fetchone()
        if row:
            raise wn.Error(f'wordnet already added: {id} {version}')
        yield info['counts']


def _build_maps(cur):
    posmap = dict(
        cur.execute('SELECT p.pos, p.id FROM parts_of_speech AS p').fetchall()
    )
    adjmap = dict(
        cur.execute('SELECT a.position, a.id FROM adjpositions AS a').fetchall()
    )
    sense_relmap = dict(
        cur.execute('SELECT r.type, r.id FROM sense_relation_types AS r').fetchall()
    )
    synset_relmap = dict(
        cur.execute('SELECT r.type, r.id FROM synset_relation_types AS r').fetchall()
    )
    lexname_map = dict(
        cur.execute('SELECT l.name, l.id FROM lexicographer_files AS l').fetchall()
    )
    return posmap, adjmap, sense_relmap, synset_relmap, lexname_map


def _split(sequence):
    i = 0
    for j in range(0, len(sequence), BATCH_SIZE):
        yield sequence[i:j]
        i = j
    yield sequence[i:]


def _insert_ilis(synsets, cur, indicator):
    for batch in _split(synsets):
        data = (
            (synset.ili,
             synset.ili_definition.text if synset.ili_definition else None,
             synset.ili_definition.meta if synset.ili_definition else None)
            for synset in batch if synset.ili and synset.ili != 'in'
        )
        cur.executemany('INSERT OR IGNORE INTO ilis VALUES (?,?,?)', data)
        indicator.send(len(batch))


def _insert_synsets(synsets, lex_id, posmap, lexname_map, cur, indicator):
    for batch in _split(synsets):
        data = (
            (synset.id,
             synset.ili if synset.ili and synset.ili != 'in' else None,
             lex_id,
             lexname_map.get(synset.meta.subject) if synset.meta else None,
             posmap[synset.pos],
             synset.lexicalized,
             synset.meta)
            for synset in batch
        )
        cur.executemany('INSERT INTO synsets VALUES (?,?,?,?,?,?,?)', data)
        indicator.send(len(batch))


def _insert_synset_definitions(synsets, cur, indicator):
    for batch in _split(synsets):
        data = [
            (synset.id,
             definition.text,
             definition.language,
             definition.source_sense,
             definition.meta)
            for synset in batch
            for definition in synset.definitions
        ]
        cur.executemany('INSERT INTO definitions VALUES (?,?,?,?,?)', data)
        indicator.send(len(data))


def _insert_synset_relations(synsets, synset_relmap, cur, indicator):
    for batch in _split(synsets):
        data = [
            (synset.id,
             relation.target,
             synset_relmap[relation.type],
             relation.meta)
            for synset in batch
            for relation in synset.relations
        ]
        cur.executemany('INSERT INTO synset_relations VALUES (?,?,?,?)', data)
        indicator.send(len(data))


def _insert_entries(entries, lex_id, posmap, cur, indicator):
    for batch in _split(entries):
        data = (
            (entry.id,
             lex_id,
             posmap[entry.lemma.pos],
             entry.meta)
            for entry in batch
        )
        cur.executemany('INSERT INTO entries VALUES (?,?,?,?)', data)
        indicator.send(len(batch))


def _insert_forms(entries, cur, indicator):
    for batch in _split(entries):
        forms = []
        for entry in batch:
            forms.append((entry.id, entry.lemma.form, entry.lemma.script, 0))
            forms.extend((entry.id, form.form, form.script, i)
                         for i, form in enumerate(entry.forms, 1))
        cur.executemany('INSERT INTO forms VALUES (null,?,?,?,?)', forms)
        indicator.send(len(forms))


# This is slower but it can link up tags with forms.
#
# def _insert_forms_with_tags(entries, cur, indicator):
#     for entry in entries:
#         forms = [entry.lemma] + list(entry.forms)
#         for i, form in enumerate(forms):
#             cur.execute('INSERT INTO forms VALUES (null,?,?,?,?)',
#                         (entry.id, form.form, form.script, i))
#             form_rowid = cur.lastrowid
#             for tag in form.tags:
#                 cur.execute('INSERT INTO tags VALUES (?,?,?)',
#                             (form_rowid, tag.text, tag.category))
#         indicator.send(len(forms))

def _insert_senses(entries, adjmap, cur, indicator):
    for batch in _split(entries):
        data = [
            (sense.id,
             entry.id,
             i,
             sense.synset,
             sense.meta.identifier if sense.meta else None,
             adjmap.get(sense.adjposition),
             sense.lexicalized,
             sense.meta)
            for entry in batch
            for i, sense in enumerate(entry.senses)
        ]
        cur.executemany('INSERT INTO senses VALUES (?,?,?,?,?,?,?,?)', data)
        indicator.send(len(data))


def _insert_sense_relations(entries, sense_relmap, table, ids, cur, indicator):
    for batch in _split(entries):
        data = [
            (sense.id,
             relation.target,
             sense_relmap[relation.type],
             relation.meta)
            for entry in batch
            for sense in entry.senses
            for relation in sense.relations if relation.target in ids
        ]
        # be careful of SQL injection here
        cur.executemany(f'INSERT INTO {table} VALUES (?,?,?,?)', data)
        indicator.send(len(data))


def _insert_examples(objs, table, cur, indicator):
    for batch in _split(objs):
        data = [
            (obj.id,
             example.text,
             example.language,
             example.meta)
            for obj in batch
            for example in obj.examples
        ]
        # be careful of SQL injection here
        cur.executemany(f'INSERT INTO {table} VALUES (?,?,?,?)', data)
        indicator.send(len(data))


def find_entries(
        id: str = None,
        form: str = None,
        pos: str = None,
        lgcode: str = None,
        lexicon: str = None
) -> Iterator[_Word]:
    with _connect() as conn:
        query_parts = [
            'SELECT e.id, p.pos, f.form',
            '  FROM entries AS e',
            '  JOIN parts_of_speech AS p ON p.id == e.pos_id',
            '  JOIN forms AS f ON f.entry_id = e.id',
        ]

        params = {'id': id, 'form': form, 'pos': pos,
                  'lgcode': lgcode, 'lexicon': lexicon}
        conditions = []
        if id:
            conditions.append('e.id=:id')
        if form:
            conditions.append('e.id IN'
                              ' (SELECT entry_id FROM forms WHERE form=:form)')
        if pos:
            conditions.append('p.pos=:pos')
        if lexicon:
            conditions.append('e.lexicon_id=:lexid')
        elif lgcode:
            conditions.append('e.lexicon_id IN'
                              ' (SELECT id FROM lexicons WHERE language=:lgcode)')

        if conditions:
            query_parts.append(' WHERE ' + '\n   AND '.join(conditions))

        query_parts.append(' ORDER BY e.id, f.rank')

        query = '\n'.join(query_parts)
        rows: Iterator[Tuple[str, str, str]] = conn.execute(query, params)
        for key, group in itertools.groupby(rows, lambda row: row[0:2]):
            id, pos = key
            forms = [row[2] for row in group]
            yield (id, pos, forms)


def find_synsets(
        id: str = None,
        form: str = None,
        pos: str = None,
        lgcode: str = None,
        lexicon: str = None
) -> Iterator[_Synset]:
    with _connect() as conn:
        query_parts = [
            'SELECT s.id, p.pos, s.ili',
            '  FROM synsets AS s',
            '  JOIN parts_of_speech AS p ON p.id == s.pos_id',
        ]

        params = {'id': id, 'form': form, 'pos': pos,
                  'lgcode': lgcode, 'lexicon': lexicon}
        conditions = []
        if id:
            conditions.append('s.id=:id')
        if form:
            conditions.append(
                's.id IN (SELECT n.synset_id FROM senses AS n'
                '           JOIN forms AS f ON f.entry_id=n.entry_id'
                '          WHERE f.form=:form)')
        if pos:
            conditions.append('p.pos=:pos')
        if lexicon:
            conditions.append('s.lexicon_id=:lexid')
        elif lgcode:
            conditions.append('s.lexicon_id IN'
                              ' (SELECT id FROM lexicons WHERE language=:lgcode)')

        if conditions:
            query_parts.append(' WHERE ' + '\n   AND '.join(conditions))

        query = '\n'.join(query_parts)
        rows: Iterator[_Synset] = conn.execute(query, params)
        yield from rows


def get_synset_relations(
        source_id: str,
        relation_types: Collection[str],
) -> Iterator[_Synset]:
    if isinstance(relation_types, str):
        relation_types = (relation_types,)
    with _connect() as conn:
        query = f'''
            SELECT r.target_id, p.pos, s.ili
              FROM (SELECT target_id
                      FROM synset_relations
                      JOIN synset_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type in ({_qs(relation_types)})) AS r
              JOIN synsets AS s
                ON s.id = r.target_id
              JOIN parts_of_speech AS p
                ON p.id = s.pos_id
        '''
        params = source_id, *relation_types
        rows: Iterator[_Synset] = conn.execute(query, params)
        yield from rows


def get_definitions_for_synset(id: str) -> List[str]:
    with _connect() as conn:
        query = 'SELECT definition FROM definitions WHERE synset_id = ?'
        return [row[0] for row in conn.execute(query, (id,)).fetchall()]


def get_examples_for_synset(id: str) -> List[str]:
    with _connect() as conn:
        query = 'SELECT example from synset_examples WHERE synset_id = ?'
        return [row[0] for row in conn.execute(query, (id,)).fetchall()]


def get_sense(id: str) -> _Sense:
    with _connect() as conn:
        query = (
            'SELECT s.entry_id, s.synset_id'
            '  FROM senses AS s'
            ' WHERE s.id = ?'
        )
        row: Tuple[str, str] = conn.execute(query, (id,)).fetchone()
        if not row:
            raise wn.Error(f'no such sense: {id}')
        return (id, *row)


def get_senses_for_entry(id: str) -> Iterator[_Sense]:
    with _connect() as conn:
        query = (
            'SELECT s.id, s.entry_id, s.synset_id'
            '  FROM senses AS s'
            ' WHERE s.entry_id = ?'
        )
        rows: Iterator[_Sense] = conn.execute(query, (id,))
        yield from rows


def get_senses_for_synset(id: str) -> Iterator[_Sense]:
    with _connect() as conn:
        query = (
            'SELECT s.id, s.entry_id, s.synset_id'
            '  FROM senses AS s'
            ' WHERE s.synset_id = ?'
        )
        rows: Iterator[_Sense] = conn.execute(query, (id,))
        yield from rows


def get_sense_relations(
        source_id: str,
        relation_types: Collection[str],
) -> Iterator[_Sense]:
    if isinstance(relation_types, str):
        relation_types = (relation_types,)
    with _connect() as conn:
        query = f'''
            SELECT r.target_id, s.entry_id, s.synset_id
              FROM (SELECT target_id
                      FROM sense_relations
                      JOIN sense_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type in ({_qs(relation_types)})) AS r
              JOIN senses AS s
                ON s.id = r.target_id
        '''
        params = source_id, *relation_types
        rows: Iterator[_Sense] = conn.execute(query, params)
        yield from rows


def get_sense_synset_relations(
        source_id: str,
        relation_types: Collection[str],
) -> Iterator[_Synset]:
    if isinstance(relation_types, str):
        relation_types = (relation_types,)
    with _connect() as conn:
        query = f'''
            SELECT r.target_id, p.pos, s.ili
              FROM (SELECT target_id
                      FROM sense_synset_relations
                      JOIN synset_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type in ({_qs(relation_types)})) AS r
              JOIN synsets AS s
                ON s.id = r.target_id
              JOIN parts_of_speech AS p
                ON p.id = s.pos_id
        '''
        params = source_id, *relation_types
        rows: Iterator[_Synset] = conn.execute(query, params)
        yield from rows


def _qs(x: Collection) -> str:
    return ','.join('?' * len(x))
