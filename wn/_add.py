"""
Adding and removing lexicons to/from the database.
"""

from typing import Optional, Type
from itertools import islice
import logging

import wn
from wn._types import AnyPath
from wn.constants import _WORDNET, _ILI
from wn._db import connect, relmap, ilistatmap
from wn._queries import find_lexicons
from wn.util import ProgressHandler, ProgressBar
from wn.project import iterpackages
from wn import lmf
from wn import _ili


logger = logging.getLogger('wn')


BATCH_SIZE = 1000

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

    The *progress_handler* parameter takes a subclass of
    :class:`wn.util.ProgressHandler`. An instance of the class will be
    created, used, and closed by this function.

    """
    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Database')

    logger.info('adding project to database')
    logger.info('  database: %s', wn.config.database_path)
    logger.info('  project file: %s', source)

    try:
        for package in iterpackages(source):
            if package.type == _WORDNET:
                _add_lmf(package.resource_file(), progress)
            elif package.type == _ILI:
                _add_ili(package.resource_file(), progress)
            else:
                raise wn.Error(f'unknown package type: {package.type}')
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
                        ('LexicalEntry', 'Lemma', 'Form', 'Tag',
                         'Sense', 'SenseRelation', 'Example', 'Count',
                         'SyntacticBehaviour',
                         'Synset', 'Definition',  # 'ILIDefinition',
                         'SynsetRelation'))
            progress.set(count=0, total=count)

            synsets = lexicon.synsets
            entries = lexicon.lexical_entries
            synbhrs = lexicon.syntactic_behaviours

            _insert_synsets(synsets, lexid, cur, progress)
            _insert_entries(entries, lexid, cur, progress)
            _insert_forms(entries, lexid, cur, progress)
            _insert_tags(entries, lexid, cur, progress)
            _insert_senses(entries, lexid, cur, progress)
            _insert_adjpositions(entries, lexid, cur, progress)
            _insert_counts(entries, lexid, cur, progress)
            _insert_syntactic_behaviours(synbhrs, lexid, cur, progress)

            _insert_synset_relations(synsets, lexid, cur, progress)
            _insert_sense_relations(lexicon, lexid, cur, progress)

            _insert_synset_definitions(synsets, lexid, cur, progress)
            _insert_examples([sense for entry in entries for sense in entry.senses],
                             lexid, 'sense_examples', cur, progress)
            _insert_examples(synsets, lexid, 'synset_examples', cur, progress)
            progress.set(status='')  # clear type string
            progress.flash(f'Added {lexicon.id}:{lexicon.version} ({lexicon.label})\n')


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
    it = iter(sequence)
    batch = list(islice(it, 0, BATCH_SIZE))
    while len(batch):
        yield batch
        batch = list(islice(it, 0, BATCH_SIZE))


def _insert_synsets(synsets, lex_id, cur, progress):
    progress.set(status='Synsets')
    # synsets
    ss_query = '''
        INSERT INTO synsets
        VALUES (null,?,?,(SELECT rowid FROM ilis WHERE id=?),?,?,?)
    '''
    # presupposed ILIs
    presupposed = ilistatmap['presupposed']
    pre_ili_query = 'INSERT OR IGNORE INTO ilis VALUES (null,?,?,?,?)'
    # proposed ILIs
    pro_ili_query = '''
        INSERT INTO proposed_ilis
        VALUES (null,(SELECT ss.rowid FROM synsets AS ss WHERE ss.id=?),?,?)
    '''

    for batch in _split(synsets):

        # first add presupposed ILIs
        data = []
        for ss in batch:
            ili = ss.ili
            if ili and ili != 'in':
                defn = ss.ili_definition
                text = defn.text if defn else None
                meta = defn.meta if defn else None
                data.append((ili, presupposed, text, meta))
        cur.executemany(pre_ili_query, data)

        # then add synsets
        data = (
            (ss.id,
             lex_id,
             ss.ili if ss.ili and ss.ili != 'in' else None,
             ss.pos,
             # lexfile_map.get(ss.meta.subject) if ss.meta else None,
             ss.lexicalized,
             ss.meta)
            for ss in batch
        )
        cur.executemany(ss_query, data)

        # finally add proposed ILIs
        data = []
        for ss in batch:
            ili = ss.ili
            if ili == 'in':
                defn = ss.ili_definition
                text = defn.text if defn else None
                meta = defn.meta if defn else None
                data.append((ss.id, text, meta))
        cur.executemany(pro_ili_query, data)

        progress.update(len(batch))


def _insert_synset_definitions(synsets, lexid, cur, progress):
    progress.set(status='Definitions')
    query = f'''
        INSERT INTO definitions
        VALUES (null,?,({SYNSET_QUERY}),?,?,({SENSE_QUERY}),?)
    '''
    for batch in _split(synsets):
        data = [
            (lexid,
             synset.id, lexid,
             definition.text,
             definition.language,
             definition.source_sense, lexid,
             definition.meta)
            for synset in batch
            for definition in synset.definitions
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_synset_relations(synsets, lexid, cur, progress):
    progress.set(status='Synset Relations')
    query = f'''
        INSERT INTO synset_relations
        VALUES (null,?,({SYNSET_QUERY}),({SYNSET_QUERY}),?,?)
    '''
    for batch in _split(synsets):
        data = [
            (lexid,
             synset.id, lexid,
             relation.target, lexid,
             relmap[relation.type],
             relation.meta)
            for synset in batch
            for relation in synset.relations
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_entries(entries, lex_id, cur, progress):
    progress.set(status='Words')
    query = 'INSERT INTO entries VALUES (null,?,?,?,?)'
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
    query = f'INSERT INTO forms VALUES (null,?,({ENTRY_QUERY}),?,?,?)'
    for batch in _split(entries):
        forms = []
        for entry in batch:
            eid = entry.id
            lemma = entry.lemma
            forms.append((lexid, eid, lexid, lemma.form, lemma.script, 0))
            forms.extend((lexid, eid, lexid, form.form, form.script, i)
                         for i, form in enumerate(entry.forms, 1))
        cur.executemany(query, forms)
        progress.update(len(forms))


def _insert_tags(entries, lexid, cur, progress):
    progress.set(status='Word Form Tags')
    query = '''
        INSERT INTO tags VALUES (
            (SELECT f.rowid
               FROM forms AS f
               JOIN entries AS e ON f.entry_rowid = e.rowid
              WHERE e.lexicon_rowid = ?
                AND e.id = ?
                AND f.form = ?
                AND f.script IS ?),
            ?,?)
    '''
    for batch in _split(entries):
        tags = []
        for entry in batch:
            eid = entry.id
            lemma = entry.lemma
            for tag in entry.lemma.tags:
                tags.append(
                    (lexid, eid, lemma.form, lemma.script, tag.text, tag.category)
                )
            for form in entry.forms:
                for tag in form.tags:
                    tags.append(
                        (lexid, eid, form.form, form.script, tag.text, tag.category)
                    )
        cur.executemany(query, tags)
        progress.update(len(tags))


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
             sense.lexicalized,
             sense.meta)
            for entry in batch
            for i, sense in enumerate(entry.senses)
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_adjpositions(entries, lexid, cur, progress):
    progress.set(status='Sense Adjpositions')
    data = [(s.id, lexid, s.adjposition)
            for e in entries
            for s in e.senses
            if s.adjposition]
    query = f'INSERT INTO adjpositions VALUES (({SENSE_QUERY}),?)'
    cur.executemany(query, data)


def _insert_counts(entries, lexid, cur, progress):
    progress.set(status='Counts')
    data = [(lexid, sense.id, lexid, count.value, count.meta)
            for entry in entries
            for sense in entry.senses
            for count in sense.counts]
    query = f'INSERT INTO counts VALUES (null,?,({SENSE_QUERY}),?,?)'
    cur.executemany(query, data)
    progress.update(len(data))


def _insert_syntactic_behaviours(synbhrs, lexid, cur, progress):
    progress.set(status='Syntactic Behaviours')
    # syntactic behaviours don't have a required ID; index on frame
    framemap = {}
    for sb in synbhrs:
        framemap.setdefault(sb.frame, []).extend(sb.senses)

    query = 'INSERT INTO syntactic_behaviours VALUES (null,?,?,?)'
    cur.executemany(query, [(None, lexid, frame) for frame in framemap])

    query = f'''
        INSERT INTO syntactic_behaviour_senses
        VALUES ((SELECT rowid
                   FROM syntactic_behaviours
                  WHERE lexicon_rowid=? AND frame=?),
                ({SENSE_QUERY}))
    '''
    data = [(lexid, frame, sid, lexid)
            for frame in framemap
            for sid in framemap[frame]]
    cur.executemany(query, data)

    progress.update(len(synbhrs))


def _insert_sense_relations(lexicon, lexid, cur, progress):
    progress.set(status='Sense Relations')
    # need to separate relations into those targeting senses vs synsets
    synset_ids = {ss.id for ss in lexicon.synsets}
    sense_ids = {s.id for e in lexicon.lexical_entries for s in e.senses}
    s_s_rels = []
    s_ss_rels = []
    for entry in lexicon.lexical_entries:
        for sense in entry.senses:
            for relation in sense.relations:
                target_id = relation.target
                if target_id in sense_ids:
                    s_s_rels.append((sense.id, relation))
                elif target_id in synset_ids:
                    s_ss_rels.append((sense.id, relation))
                else:
                    raise wn.Error(
                        f'relation target is not a known sense or synset: {target_id}'
                    )
    hyperparams = [
        ('sense_relations', SENSE_QUERY, s_s_rels),
        ('sense_synset_relations', SYNSET_QUERY, s_ss_rels),
    ]
    for table, target_query, rels in hyperparams:
        query = f'''
            INSERT INTO {table}
            VALUES (null,?,({SENSE_QUERY}),({target_query}),?,?)
        '''
        for batch in _split(rels):
            data = [
                (lexid,
                 sense_id, lexid,
                 relation.target, lexid,
                 relmap[relation.type],
                 relation.meta)
                for sense_id, relation in batch
            ]
            cur.executemany(query, data)
            progress.update(len(data))


def _insert_examples(objs, lexid, table, cur, progress):
    progress.set(status='Examples')
    query = f'INSERT INTO {table} VALUES (null,?,({SYNSET_QUERY}),?,?,?)'
    for batch in _split(objs):
        data = [
            (lexid,
             obj.id, lexid,
             example.text,
             example.language,
             example.meta)
            for obj in batch
            for example in obj.examples
        ]
        # be careful of SQL injection here
        cur.executemany(query, data)
        progress.update(len(data))


def _add_ili(
    source,
    progress: ProgressHandler,
) -> None:
    query = '''
        INSERT INTO ilis
        VALUES (null,?,?,?,null)
            ON CONFLICT(id) DO
               UPDATE SET status=excluded.status,
                          definition=excluded.definition
    '''
    with connect() as conn:
        cur = conn.cursor()

        progress.flash(f'Reading ILI file: {source!s}')
        ili = list(_ili.load(source))
        progress.set(count=0, total=len(ili), status='ILI')
        for batch in _split(ili):
            data = [
                (info['ili'],
                 ilistatmap[info.get('status', 'active')],
                 info.get('definition'))
                for info in batch
            ]
            cur.executemany(query, data)
            progress.update(len(data))


def remove(
    lexicon: str,
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar
) -> None:
    """Remove lexicon(s) from the database.

    The *lexicon* argument is a :ref:`lexicon specifier
    <lexicon-specifiers>`. Note that this removes a lexicon and not a
    project, so the lexicons of projects containing multiple lexicons
    will need to be removed individually.

    The *progress_handler* parameter takes a subclass of
    :class:`wn.util.ProgressHandler`. An instance of the class will be
    created, used, and closed by this function.

    >>> wn.remove('ewn:2019')

    """
    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Removing', unit='\be5 operations')

    conn = connect()
    conn.set_progress_handler(progress.update, 100000)
    try:
        for rowid, id, _, _, _, _, version, *_ in find_lexicons(lexicon=lexicon):
            progress.set(status=f'{id}:{version}', count=0)
            with conn:
                conn.execute('DELETE from lexicons WHERE rowid = ?', (rowid,))
            progress.flash(f'Removed {id}:{version}')

    finally:
        progress.close()
