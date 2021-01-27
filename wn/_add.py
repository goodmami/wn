"""
Adding and removing lexicons to/from the database.
"""

from typing import Optional, Type
import logging

import wn
from wn._types import AnyPath
from wn._db import connect
from wn._queries import find_lexicons
from wn.util import ProgressHandler, ProgressBar
from wn.project import iterpackages
from wn import lmf


logger = logging.getLogger('wn')


BATCH_SIZE = 1000

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


def add(
    source: AnyPath,
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar,
) -> None:
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
    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Database', unit='\b')

    logger.info('adding project to database')
    logger.info('  database: %s', wn.config.database_path)
    logger.info('  project file: %s', source)

    try:
        for package in iterpackages(source):
            _add_lmf(package.resource_file(), progress)
    finally:
        progress.close()


def _add_lmf(
    source,
    progress: ProgressHandler,
) -> None:
    with connect() as conn:
        cur = conn.cursor()
        # these two settings increase the risk of database corruption
        # if the system crashes during a write, but they should also
        # make inserts much faster
        cur.execute('PRAGMA synchronous = OFF')
        cur.execute('PRAGMA journal_mode = MEMORY')

        # abort if any lexicon in *source* is already added
        progress.flash(f'Checking {source!s}')
        all_infos = list(_precheck(source, cur))

        if not all_infos:
            progress.flash(f'{source}: No lexicons found')
            return
        elif all(info.get('skip', False) for info in all_infos):
            progress.flash(f'{source}: Some or all lexicons already added')
            return

        # all clear, try to add them
        progress.flash(f'Reading {source!s}')
        for lexicon, info in zip(lmf.load(source), all_infos):

            if info.get('skip', False):
                progress.flash(
                    f'Skipping {info["id"]:info["version"]} ({info["label"]})\n',
                )
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
            progress.set(count=0, total=count)

            synsets = lexicon.synsets
            entries = lexicon.lexical_entries

            _insert_ilis(synsets, cur, progress)
            _insert_synsets(synsets, lexid, cur, progress)
            _insert_entries(entries, lexid, cur, progress)
            _insert_forms(entries, lexid, cur, progress)
            _insert_senses(entries, lexid, cur, progress)

            _insert_synset_relations(synsets, lexid, cur, progress)
            _insert_sense_relations(entries, lexid, 'sense_relations',
                                    sense_ids, cur, progress)
            _insert_sense_relations(entries, lexid, 'sense_synset_relations',
                                    synset_ids, cur, progress)

            _insert_synset_definitions(synsets, lexid, cur, progress)
            _insert_examples([sense for entry in entries for sense in entry.senses],
                             lexid, 'sense_examples', cur, progress)
            _insert_examples(synsets, lexid, 'synset_examples', cur, progress)
            progress.set(status='')  # clear type string
            progress.flash(f'Added {lexicon.id}:{lexicon.version} ({lexicon.label})')


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


def _insert_ilis(synsets, cur, progress):
    progress.set(status='ILI')
    for batch in _split(synsets):
        data = (
            (synset.ili,
             synset.ili_definition.text if synset.ili_definition else None,
             synset.ili_definition.meta if synset.ili_definition else None)
            for synset in batch if synset.ili and synset.ili != 'in'
        )
        cur.executemany('INSERT OR IGNORE INTO ilis VALUES (?,?,?)', data)
        progress.update(len(batch))


def _insert_synsets(synsets, lex_id, cur, progress):
    progress.set(status='Synsets')
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
        progress.update(len(batch))


def _insert_synset_definitions(synsets, lexid, cur, progress):
    progress.set(status='Definitions')
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
        progress.update(len(data))


def _insert_synset_relations(synsets, lexid, cur, progress):
    progress.set(status='Synset Relations')
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
        progress.update(len(data))


def _insert_entries(entries, lex_id, cur, progress):
    progress.set(status='Words')
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
        progress.update(len(batch))


def _insert_forms(entries, lexid, cur, progress):
    progress.set(status='Word Forms')
    query = f'INSERT INTO forms VALUES (null,({ENTRY_QUERY}),?,?,?)'
    for batch in _split(entries):
        forms = []
        for entry in batch:
            forms.append((entry.id, lexid, entry.lemma.form, entry.lemma.script, 0))
            forms.extend((entry.id, lexid, form.form, form.script, i)
                         for i, form in enumerate(entry.forms, 1))
        cur.executemany(query, forms)
        progress.update(len(forms))


def _insert_senses(entries, lexid, cur, progress):
    progress.set(status='Senses')
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
        progress.update(len(data))


def _insert_sense_relations(entries, lexid, table, ids, cur, progress):
    progress.set(status='Sense Relations')
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
        progress.update(len(data))


def _insert_examples(objs, lexid, table, cur, progress):
    progress.set(status='Examples')
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
        progress.update(len(data))


def remove(lexicon: str) -> None:
    """Remove lexicon(s) from the database.

    The *lexicon* argument is a :ref:`lexicon specifier
    <lexicon-specifiers>`. Note that this removes a lexicon and not a
    project, so the lexicons of projects containing multiple lexicons
    will need to be removed individually.

    >>> wn.remove('ewn:2019')

    """
    with connect() as conn:
        for rowid, id, _, _, _, _, version, *_ in find_lexicons(lexicon=lexicon):
            conn.execute('DELETE FROM entries WHERE lexicon_rowid = ?', (rowid,))
            conn.execute('DELETE FROM synsets WHERE lexicon_rowid = ?', (rowid,))
            conn.execute('DELETE FROM syntactic_behaviours WHERE lexicon_rowid = ?',
                         (rowid,))
            conn.execute('DELETE FROM lexicons WHERE rowid = ?', (rowid,))
