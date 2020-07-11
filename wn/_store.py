"""
Storage back-end interface.

The wordnets are stored in a cache directory as follows:

- index.json  : listing of added wordnets
- synsets/    : directory of project-specific synset stores
  - xyz       : synsets for the 'xyz' project
- senses/     : directory of project-specific sense stores
  - xyz       : senses for the 'xyz' project
"""

import sys
from typing import Union, Dict, List, Tuple
from pathlib import Path
import gzip
import tempfile
import shutil
import json
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
from wn import _models
from wn import lmf


CACHE_DIRECTORY = Path.home() / '.wn_data'
DOWNLOADS_DIRECTORY = CACHE_DIRECTORY / 'downloads'
DBFILENAME = 'wn.db'

CACHE_DIRECTORY.mkdir(exist_ok=True)
DOWNLOADS_DIRECTORY.mkdir(exist_ok=True)

BATCH_SIZE = 1000


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

def _connect(dbpath: Path = None) -> sqlite3.Connection:
    if dbpath is None:
        dbpath = CACHE_DIRECTORY / DBFILENAME
    conn = sqlite3.connect(dbpath)
    # foreign key support needs to be enabled for each connection
    conn.execute('PRAGMA foreign_keys = ON')
    # uncomment the following to help with debugging
    # conn.set_trace_callback(print)
    return conn


def _initialize(basepath: Path, exist_ok: bool = False) -> None:
    dbpath = basepath / DBFILENAME
    if not dbpath.exists():
        schema = resources.read_text('wn', 'schema.sql')
        with _connect(basepath / DBFILENAME) as conn:
            conn.executescript(schema)
            # prepare lookup tables
            conn.executemany(
                'INSERT INTO parts_of_speech (pos) VALUES (?)',
                ((pos,) for pos in constants.POS_LIST))
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
    elif not exist_ok:
        raise wn.Error('database already exists: {dbpath!s}')


# ensure the default database is initialized when loading the module
_initialize(CACHE_DIRECTORY, exist_ok=True)


def add(source: AnyPath) -> None:
    """Add the LMF file at *source* to the database.

    The file at *source* may be gzip-compressed or plain text XML.
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
            lex_rowid = cur.lastrowid

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
            _insert_synsets(synsets, lex_rowid, posmap, lexname_map, cur, indicator)
            _insert_entries(entries, lex_rowid, posmap, cur, indicator)
            _insert_forms(entries, cur, indicator)
            _insert_senses(entries, adjmap, cur, indicator)

            _insert_synset_relations(synsets, synset_relmap, cur, indicator)
            _insert_sense_relations(entries, sense_relmap, 'sense_sense_relations',
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
            'SELECT EXISTS(SELECT 1 FROM lexicons WHERE id=? AND version=?)',
            (id, version)
        ).fetchone()
        if row[0]:
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
        cur.executemany('INSERT INTO ilis VALUES (?,?,?)', data)
        indicator.send(len(batch))


def _insert_synsets(synsets, lex_rowid, posmap, lexname_map, cur, indicator):
    for batch in _split(synsets):
        data = (
            (synset.id,
             synset.ili if synset.ili and synset.ili != 'in' else None,
             lex_rowid,
             lexname_map[synset.meta.subject] if synset.meta else None,
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


def _insert_entries(entries, lex_rowid, posmap, cur, indicator):
    for batch in _split(entries):
        data = (
            (entry.id,
             lex_rowid,
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


def get_entry(id: str) -> _models.Word:
    with _connect() as conn:
        query = (
            'SELECT p.pos'
            '  FROM (SELECT pos_id FROM entries WHERE id = ? LIMIT 1)'
            '  JOIN parts_of_speech AS p'
            '    ON p.id = pos_id'
        )
        pos = conn.execute(query, (id,)).fetchone()[0]
        query = (
            'SELECT f.form'
            '  FROM forms AS f'
            ' WHERE f.entry_id = ?'
            ' ORDER BY f.rank ASC'
        )
        forms = [row[0] for row in conn.execute(query, (id,)).fetchall()]
        return _models.Word(id, pos, forms)


def find_entries(
        form: str = None,
        pos: str = None,
        lgcode: str = None,
        project: str = None
) -> List[_models.Word]:
    with _connect() as conn:
        # Unconstrained joins
        _form = 'forms AS f'
        _pos = 'parts_of_speech AS p'

        params = {}
        if form:
            _form = '(SELECT entry_id, form, rank FROM forms WHERE form = :form) AS f'
            params['form'] = form

        if pos:
            _pos = '(SELECT id, pos FROM parts_of_speech WHERE pos = :pos) AS p'
            params['pos'] = pos

        query = f'''
            SELECT e.id, p.pos, f.form, f.rank
              FROM entries AS e
              JOIN {_form} ON f.entry_id = e.id
              JOIN {_pos} ON p.id = e.pos_id
             GROUP BY e.id, p.pos
        '''
        data: Dict[Tuple[str, str], Tuple[int, str]] = {}
        for id, pos, form, rank in conn.execute(query, params):
            data.setdefault((id, pos), []).append((rank, form))
        entries = []
        for (id, pos), forms in data.items():
            entries.append(_models.Word(id, pos, [form for _, form in sorted(forms)]))

        return entries


def get_synset(id: str) -> _models.Synset:
    with _connect() as conn:
        query = (
            'SELECT ili, p.pos'
            '  FROM (SELECT ili, pos_id FROM synsets WHERE id = ? LIMIT 1)'
            '  JOIN parts_of_speech AS p'
            '    ON p.id = s.pos_id'
        )
        ili, pos = conn.execute(query, (id,)).fetchone()
        return _models.Synset(
            id,
            pos,
            ili,
        )


def find_synsets(
        form: str = None,
        pos: str = None,
        lgcode: str = None,
        project: str = None
) -> List[_models.Synset]:
    with _connect() as conn:
        # Unconstrained joins
        _pos = 'parts_of_speech AS p'
        _form = ''

        params = {}
        if form:
            _form = '''
                JOIN (SELECT n.synset_id FROM senses AS n
                        JOIN (SELECT entry_id FROM forms WHERE form = :form) AS f
                          ON f.entry_id = n.entry_id) AS n
                  ON s.id = n.synset_id
            '''
            params['form'] = form

        if pos:
            _pos = '(SELECT id, pos FROM parts_of_speech WHERE pos = :pos) AS p'
            params['pos'] = pos

        query = f'''
            SELECT s.id, p.pos, s.ili
              FROM synsets AS s
              {_form}
              JOIN {_pos} ON p.id = s.pos_id
        '''
        return [_models.Synset(id, pos, ili)
                for id, pos, ili
                in conn.execute(query, params)]


def get_synset_relations(source_id: str, relation_type: str) -> List[_models.Synset]:
    with _connect() as conn:
        query = '''
            SELECT r.target_id, p.pos, s.ili
              FROM (SELECT target_id
                      FROM synset_relations
                      JOIN synset_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type = ?) AS r
              JOIN synsets AS s
                ON s.id = r.target_id
              JOIN parts_of_speech AS p
                ON p.id = s.pos_id
        '''
        return [_models.Synset(id, pos, ili)
                for id, ili, pos
                in conn.execute(query, (source_id, relation_type))]


def get_definitions_for_synset(id: str) -> List[str]:
    with _connect() as conn:
        query = 'SELECT definition FROM definitions WHERE synset_id = ?'
        return [row[0] for row in conn.execute(query, (id,)).fetchall()]


def get_examples_for_synset(id: str) -> List[str]:
    with _connect() as conn:
        query = 'SELECT example from synset_examples WHERE synset_id = ?'
        return [row[0] for row in conn.execute(query, (id,)).fetchall()]


def get_sense(id: str) -> _models.Sense:
    with _connect() as conn:
        query = (
            'SELECT s.entry_id, s.synset_id, s.sense_key'
            '  FROM senses AS s'
            ' WHERE s.id = ?'
        )
        entry_id, synset_id, sense_key = conn.execute(query, (id,)).fetchone()
        return _models.Sense(id, entry_id, synset_id, sense_key)


def get_senses_for_entry(id: str) -> List[_models.Sense]:
    with _connect() as conn:
        query = (
            'SELECT s.id, s.entry_id, s.synset_id, s.sense_key'
            '  FROM senses AS s'
            ' WHERE s.entry_id = ?'
        )
        return [_models.Sense(id, entry_id, synset_id, sense_key)
                for id, entry_id, synset_id, sense_key
                in conn.execute(query, (id,)).fetchall()]


def get_senses_for_synset(id: str) -> List[_models.Sense]:
    with _connect() as conn:
        query = (
            'SELECT s.id, s.entry_id, s.synset_id, s.sense_key'
            '  FROM senses AS s'
            ' WHERE s.synset_id = ?'
        )
        return [_models.Sense(id, entry_id, synset_id, sense_key)
                for id, entry_id, synset_id, sense_key
                in conn.execute(query, (id,)).fetchall()]


def get_sense_relations(
        source_id: str,
        relation_type: str
) -> List[Union[_models.Synset, _models.Sense]]:
    with _connect() as conn:
        rels: List[Union[_models.Synset, _models.Sense]] = []
        query = '''
            SELECT r.target_id, s.entry_id, s.synset_id, s.sense_key
              FROM (SELECT target_id
                      FROM sense_sense_relations
                      JOIN sense_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type = ?) AS r
              JOIN senses AS s
                ON s.id = r.target_id
        '''
        rels.extend(_models.Sense(id, entry_id, synset_id, sense_key)
                    for id, entry_id, synset_id, sense_key
                    in conn.execute(query, (source_id, relation_type)))

        query = '''
            SELECT r.target_id, p.pos, s.ili
              FROM (SELECT target_id
                      FROM synset_relations
                      JOIN synset_relation_types AS t
                        ON type_id = t.id
                     WHERE source_id = ?
                       AND t.type = ?) AS r
              JOIN synsets AS s
                ON s.id = r.target_id
              JOIN parts_of_speech AS p
                ON p.id = s.pos_id
        '''
        rels.extend(_models.Synset(id, pos, ili)
                    for id, pos, ili
                    in conn.execute(query, (source_id, relation_type)))
        return rels
