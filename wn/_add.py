"""
Adding and removing lexicons to/from the database.
"""

from typing import Optional, Type, Tuple, List
from itertools import islice
import logging

import wn
from wn._types import AnyPath
from wn.constants import _WORDNET, _ILI
from wn._db import connect
from wn._queries import find_lexicons, get_lexicon_extensions, get_lexicon
from wn._util import normalize_form
from wn.util import ProgressHandler, ProgressBar
from wn.project import iterpackages
from wn import lmf
from wn import _ili


logger = logging.getLogger('wn')


BATCH_SIZE = 1000
DEFAULT_MEMBER_RANK = 127  # synset member rank when not specified by 'members'

ENTRY_QUERY = '''
    SELECT e.rowid
      FROM entries AS e
     WHERE e.id = ?
       AND e.lexicon_rowid = ?
'''
# forms don't have reliable ids, so also consider rank; this depends
# on each form having a unique rank, and this doesn't work for lexicon
# extensions
FORM_QUERY = '''
    SELECT f.rowid
      FROM forms AS f
      JOIN entries AS e ON f.entry_rowid = e.rowid
     WHERE e.id = ?
       AND e.lexicon_rowid = ?
       AND (f.id = ? OR f.rank = ?)
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
RELTYPE_QUERY = '''
    SELECT rt.rowid
      FROM relation_types AS rt
     WHERE rt.type = ?
'''
ILISTAT_QUERY = '''
    SELECT ist.rowid
      FROM ili_statuses AS ist
     WHERE ist.status = ?
'''
LEXFILE_QUERY = '''
    SELECT lf.rowid
      FROM lexfiles AS lf
     WHERE lf.name = ?
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
                _add_lmf(package.resource_file(), progress, progress_handler)
            elif package.type == _ILI:
                _add_ili(package.resource_file(), progress)
            else:
                raise wn.Error(f'unknown package type: {package.type}')
    finally:
        progress.close()


def _add_lmf(
    source,
    progress: ProgressHandler,
    progress_handler: Type[ProgressHandler],
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
        for info in all_infos:
            skip = info.get('skip', '')
            if skip:
                id, ver, lbl = info['id'], info['version'], info['label']
                progress.flash(f'Skipping {id}:{ver} ({lbl}); {skip}\n')
        if all('skip' in info for info in all_infos):
            return

        # all clear, try to add them
        progress.flash(f'Reading {source!s}')

        for lexicon, info in zip(lmf.load(source, progress_handler), all_infos):
            if 'skip' in info:
                continue

            progress.flash('Updating lookup tables')
            _update_lookup_tables(lexicon, cur)

            progress.set(count=0, total=_sum_counts(info))
            synsets = lexicon.synsets
            entries = lexicon.lexical_entries
            synbhrs = lexicon.syntactic_behaviours

            lexid, qryid = _insert_lexicon(lexicon, info, cur, progress)

            lexidmap = _build_lexid_map(lexicon, lexid, qryid)

            _insert_synsets(synsets, lexid, cur, progress)
            _insert_entries(entries, lexid, cur, progress)
            _insert_forms(entries, lexid, lexidmap, cur, progress)
            _insert_pronunciations(entries, lexid, lexidmap, cur, progress)
            _insert_tags(entries, lexid, lexidmap, cur, progress)
            _insert_senses(entries, synsets, lexid, lexidmap, cur, progress)
            _insert_adjpositions(entries, lexid, lexidmap, cur, progress)
            _insert_counts(entries, lexid, lexidmap, cur, progress)
            _insert_syntactic_behaviours(synbhrs, lexid, lexidmap, cur, progress)

            _insert_synset_relations(synsets, lexid, lexidmap, cur, progress)
            _insert_sense_relations(lexicon, lexid, lexidmap, cur, progress)

            _insert_synset_definitions(synsets, lexid, lexidmap, cur, progress)
            _insert_examples([sense for entry in entries for sense in entry.senses],
                             lexid, lexidmap, 'sense_examples', cur, progress)
            _insert_examples(synsets, lexid, lexidmap, 'synset_examples', cur, progress)

            progress.set(status='')  # clear type string
            progress.flash(f'Added {lexicon.id}:{lexicon.version} ({lexicon.label})\n')


def _precheck(source, cur):
    lexqry = 'SELECT * FROM lexicons WHERE id = ? AND version = ?'
    for info in lmf.scan_lexicons(source):
        id = info['id']
        version = info['version']
        base = info.get('extends')
        if cur.execute(lexqry, (id, version)).fetchone():
            info['skip'] = 'already added'
        if base and cur.execute(lexqry, base).fetchone() is None:
            info['skip'] = f'base lexicon ({base[0]}:{base[1]}) not available'
        yield info


def _sum_counts(info) -> int:
    counts = info['counts']
    return sum(counts.get(name, 0) for name in lmf.LEXICON_INFO_ATTRIBUTES)


def _update_lookup_tables(lexicon, cur):
    reltypes = set(rel.type
                   for ss in lexicon.synsets
                   for rel in ss.relations)
    reltypes.update(rel.type
                    for e in lexicon.lexical_entries
                    for s in e.senses
                    for rel in s.relations)
    cur.executemany('INSERT OR IGNORE INTO relation_types VALUES (null,?)',
                    [(rt,) for rt in sorted(reltypes)])
    lexfiles = set(ss.lexfile for ss in lexicon.synsets) - {None}
    cur.executemany('INSERT OR IGNORE INTO lexfiles VALUES (null,?)',
                    [(lf,) for lf in sorted(lexfiles)])


def _insert_lexicon(lexicon, info, cur, progress) -> Tuple[int, int]:
    progress.set(status='Lexicon Info')
    cur.execute(
        'INSERT INTO lexicons VALUES (null,?,?,?,?,?,?,?,?,?,?,?)',
        (lexicon.id,
         lexicon.label,
         lexicon.language,
         lexicon.email,
         lexicon.license,
         lexicon.version,
         lexicon.url,
         lexicon.citation,
         lexicon.logo,
         lexicon.meta,
         False))
    lexid = cur.lastrowid

    query = '''
        UPDATE lexicon_dependencies
           SET provider_rowid = ?
         WHERE provider_id = ? AND provider_version = ?
    '''
    cur.execute(query, (lexid, lexicon.id, lexicon.version))

    query = '''
        INSERT INTO {table}
        VALUES (:lid,
                :id,
                :version,
                :url,
                (SELECT rowid FROM lexicons WHERE id=:id AND version=:version))
    '''
    params = []
    for dep in lexicon.requires:
        param_dict = dict(dep)
        param_dict.setdefault('url', None)
        param_dict['lid'] = lexid
        params.append(param_dict)
    if params:
        cur.executemany(query.format(table='lexicon_dependencies'), params)

    if lexicon.extends:
        param_dict = dict(lexicon.extends)
        param_dict.setdefault('url', None)
        param_dict['lid'] = lexid
        cur.execute(query.format(table='lexicon_extensions'), param_dict)
        qryid = cur.execute(
            'SELECT rowid FROM lexicons WHERE id=? AND version=?',
            (param_dict['id'], param_dict['version'])
        ).fetchone()[0]
    else:
        qryid = lexid

    return lexid, qryid


def _build_lexid_map(lexicon, lexid, qryid):
    lexidmap = {}
    if lexid != qryid:
        lexidmap.update((e.id, qryid) for e in lexicon.lexical_entries if e.external)
        lexidmap.update((s.id, qryid)
                        for e in lexicon.lexical_entries
                        for s in e.senses
                        if s.external)
        lexidmap.update((ss.id, qryid) for ss in lexicon.synsets if ss.external)
    return lexidmap


def _split(sequence):
    it = iter(sequence)
    batch = list(islice(it, 0, BATCH_SIZE))
    while len(batch):
        yield batch
        batch = list(islice(it, 0, BATCH_SIZE))


def _insert_synsets(synsets, lexid, cur, progress):
    progress.set(status='Synsets')
    # synsets
    ss_query = f'''
        INSERT INTO synsets
        VALUES (null,?,?,(SELECT rowid FROM ilis WHERE id=?),?,?,({LEXFILE_QUERY}),?)
    '''
    # presupposed ILIs
    pre_ili_query = f'''
        INSERT OR IGNORE INTO ilis
        VALUES (null,?,({ILISTAT_QUERY}),?,?)
    '''
    # proposed ILIs
    pro_ili_query = '''
        INSERT INTO proposed_ilis
        VALUES (null,
               (SELECT ss.rowid
                  FROM synsets AS ss
                 WHERE ss.id=? AND lexicon_rowid=?),
               ?,
               ?)
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
                data.append((ili, 'presupposed', text, meta))
        cur.executemany(pre_ili_query, data)

        # then add synsets
        data = (
            (ss.id,
             lexid,
             ss.ili if ss.ili and ss.ili != 'in' else None,
             ss.pos,
             ss.lexicalized,
             ss.lexfile,
             ss.meta)
            for ss in batch if not ss.external
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
                data.append((ss.id, lexid, text, meta))
        cur.executemany(pro_ili_query, data)

        progress.update(len(batch))


def _insert_synset_definitions(synsets, lexid, lexidmap, cur, progress):
    progress.set(status='Definitions')
    query = f'''
        INSERT INTO definitions
        VALUES (null,?,({SYNSET_QUERY}),?,?,({SENSE_QUERY}),?)
    '''
    for batch in _split(synsets):
        data = [
            (lexid,
             synset.id, lexidmap.get(synset.id, lexid),
             definition.text,
             definition.language,
             definition.source_sense, lexidmap.get(definition.source_sense, lexid),
             definition.meta)
            for synset in batch
            for definition in synset.definitions
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_synset_relations(synsets, lexid, lexidmap, cur, progress):
    progress.set(status='Synset Relations')
    query = f'''
        INSERT INTO synset_relations
        VALUES (null,?,({SYNSET_QUERY}),({SYNSET_QUERY}),({RELTYPE_QUERY}),?)
    '''
    for batch in _split(synsets):
        data = [
            (lexid,
             synset.id, lexidmap.get(synset.id, lexid),
             relation.target, lexidmap.get(relation.target, lexid),
             relation.type,
             relation.meta)
            for synset in batch
            for relation in synset.relations
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_entries(entries, lexid, cur, progress):
    progress.set(status='Words')
    query = 'INSERT INTO entries VALUES (null,?,?,?,?)'
    for batch in _split(entries):
        data = (
            (entry.id,
             lexid,
             entry.lemma.pos,
             entry.meta)
            for entry in batch if not entry.external
        )
        cur.executemany(query, data)
        progress.update(len(batch))


def _insert_forms(entries, lexid, lexidmap, cur, progress):
    progress.set(status='Word Forms')
    query = f'INSERT INTO forms VALUES (null,?,?,({ENTRY_QUERY}),?,?,?,?)'
    for batch in _split(entries):
        forms = []
        for entry in batch:
            eid = entry.id
            lemma = entry.lemma
            lid = lexidmap.get(eid, lexid)
            if not entry.external:
                form = lemma.form
                norm = normalize_form(form)
                forms.append(
                    (None, lexid, eid, lid,
                     form, norm if norm != form else None,
                     lemma.script, 0)
                )
            for i, form in enumerate(entry.forms, 1):
                _form = form.form
                norm = normalize_form(_form)
                forms.append(
                    (form.id, lexid, eid, lid,
                     form.form, norm if norm != form else None,
                     form.script, i)
                )
        cur.executemany(query, forms)
        progress.update(len(forms))


def _insert_pronunciations(entries, lexid, lexidmap, cur, progress):
    progress.set(status='Pronunciations')
    query = f'INSERT INTO pronunciations VALUES (({FORM_QUERY}),?,?,?,?,?)'
    for batch in _split(entries):
        prons = []
        for entry in batch:
            eid = entry.id
            lid = lexidmap.get(eid, lexid)
            if entry.lemma:
                for p in entry.lemma.pronunciations:
                    prons.append(
                        (eid, lid, None, 0,
                         p.value, p.variety, p.notation, p.phonemic, p.audio)
                    )
            for i, form in enumerate(entry.forms, 1):
                # rank is not valid in FORM_QUERY for external forms
                rank = -1 if form.external else i
                for p in form.pronunciations:
                    prons.append(
                        (eid, lid, form.id, rank,
                         p.text, p.variety, p.notation, p.phonemic, p.audio)
                    )
        cur.executemany(query, prons)
        progress.update(len(prons))


def _insert_tags(entries, lexid, lexidmap, cur, progress):
    progress.set(status='Word Form Tags')
    query = f'INSERT INTO tags VALUES (({FORM_QUERY}),?,?)'
    for batch in _split(entries):
        tags = []
        for entry in batch:
            eid = entry.id
            lid = lexidmap.get(eid, lexid)
            if entry.lemma:
                for tag in entry.lemma.tags:
                    tags.append((eid, lid, None, 0, tag.text, tag.category))
            for i, form in enumerate(entry.forms, 1):
                # rank is not valid in FORM_QUERY for external forms
                rank = -1 if form.external else i
                for tag in form.tags:
                    tags.append((eid, lid, form.id, rank, tag.text, tag.category))
        cur.executemany(query, tags)
        progress.update(len(tags))


def _insert_senses(entries, synsets, lexid, lexidmap, cur, progress):
    progress.set(status='Senses')
    ssrank = {s: i for ss in synsets for i, s in enumerate(ss.members)}
    query = f'''
        INSERT INTO senses
        VALUES (null,
                ?,
                ?,
                ({ENTRY_QUERY}),
                ?,
                ({SYNSET_QUERY}),
                ?,
                ?,
                ?)
    '''
    for batch in _split(entries):
        data = [
            (sense.id,
             lexid,
             entry.id, lexidmap.get(entry.id, lexid),
             i,
             sense.synset, lexidmap.get(sense.synset, lexid),
             ssrank.get(sense.id, DEFAULT_MEMBER_RANK),
             sense.lexicalized,
             sense.meta)
            for entry in batch
            for i, sense in enumerate(entry.senses)
            if not sense.external
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_adjpositions(entries, lexid, lexidmap, cur, progress):
    progress.set(status='Sense Adjpositions')
    data = [(s.id, lexidmap.get(s.id, lexid), s.adjposition)
            for e in entries
            for s in e.senses
            if s.adjposition and not s.external]
    query = f'INSERT INTO adjpositions VALUES (({SENSE_QUERY}),?)'
    cur.executemany(query, data)


def _insert_counts(entries, lexid, lexidmap, cur, progress):
    progress.set(status='Counts')
    data = [(lexid,
             sense.id, lexidmap.get(sense.id, lexid),
             count.value,
             count.meta)
            for entry in entries
            for sense in entry.senses
            for count in sense.counts]
    query = f'INSERT INTO counts VALUES (null,?,({SENSE_QUERY}),?,?)'
    cur.executemany(query, data)
    progress.update(len(data))


def _insert_syntactic_behaviours(synbhrs, lexid, lexidmap, cur, progress):
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
    data = [(lexid, frame, sid, lexidmap.get(sid, lexid))
            for frame in framemap
            for sid in framemap[frame]]
    cur.executemany(query, data)

    progress.update(len(synbhrs))


def _insert_sense_relations(lexicon, lexid, lexidmap, cur, progress):
    progress.set(status='Sense Relations')
    # need to separate relations into those targeting senses vs synsets
    synset_ids = {ss.id for ss in lexicon.synsets}
    sense_ids = {s.id for e in lexicon.lexical_entries for s in e.senses}
    s_s_rels = []
    s_ss_rels = []
    for entry in lexicon.lexical_entries:
        for sense in entry.senses:
            slid = lexidmap.get(sense.id, lexid)
            for relation in sense.relations:
                target_id = relation.target
                tlid = lexidmap.get(target_id, lexid)
                if target_id in sense_ids:
                    s_s_rels.append((sense.id, slid, tlid, relation))
                elif target_id in synset_ids:
                    s_ss_rels.append((sense.id, slid, tlid, relation))
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
            VALUES (null,?,({SENSE_QUERY}),({target_query}),({RELTYPE_QUERY}),?)
        '''
        for batch in _split(rels):
            data = [
                (lexid,
                 sense_id, slid,
                 relation.target, tlid,
                 relation.type,
                 relation.meta)
                for sense_id, slid, tlid, relation in batch
            ]
            cur.executemany(query, data)
            progress.update(len(data))


def _insert_examples(objs, lexid, lexidmap, table, cur, progress):
    progress.set(status='Examples')
    if table == 'sense_examples':
        query = f'INSERT INTO {table} VALUES (null,?,({SENSE_QUERY}),?,?,?)'
    else:
        query = f'INSERT INTO {table} VALUES (null,?,({SYNSET_QUERY}),?,?,?)'
    for batch in _split(objs):
        data = [
            (lexid,
             obj.id, lexidmap.get(obj.id, lexid),
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
    query = f'''
        INSERT INTO ilis
        VALUES (null,?,({ILISTAT_QUERY}),?,null)
            ON CONFLICT(id) DO
               UPDATE SET status_rowid=excluded.status_rowid,
                          definition=excluded.definition
    '''
    with connect() as conn:
        cur = conn.cursor()

        progress.flash(f'Reading ILI file: {source!s}')
        ili = list(_ili.load(source))

        progress.flash('Updating ILI Status Names')
        statuses = set(info.get('status', 'active') for info in ili)
        cur.executemany('INSERT OR IGNORE INTO ili_statuses VALUES (null,?)',
                        [(stat,) for stat in sorted(statuses)])

        progress.set(count=0, total=len(ili), status='ILI')
        for batch in _split(ili):
            data = [
                (info['ili'],
                 info.get('status', 'active'),
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
    will need to be removed individually or, if applicable, a star
    specifier.

    The *progress_handler* parameter takes a subclass of
    :class:`wn.util.ProgressHandler`. An instance of the class will be
    created, used, and closed by this function.

    >>> wn.remove('ewn:2019')  # removes a single lexicon
    >>> wn.remove('*:1.3+omw')  # removes all lexicons with version 1.3+omw

    """
    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Removing', unit='\be5 operations')

    conn = connect()
    conn.set_progress_handler(progress.update, 100000)
    try:
        for rowid, id, _, _, _, _, version, *_ in find_lexicons(lexicon=lexicon):
            extensions = _find_all_extensions(rowid)

            with conn:

                for ext_id, ext_spec in reversed(extensions):
                    progress.set(status=f'{ext_spec} (extension)')
                    conn.execute('DELETE from lexicons WHERE rowid = ?', (ext_id,))
                    progress.flash(f'Removed {ext_spec}\n')

                spec = f'{id}:{version}'
                extra = f' (and {len(extensions)} extension(s))' if extensions else ''
                progress.set(status=f'{spec}', count=0)
                conn.execute('DELETE from lexicons WHERE rowid = ?', (rowid,))
                progress.flash(f'Removed {spec}{extra}\n')

    finally:
        progress.close()
        conn.set_progress_handler(None, 0)


def _find_all_extensions(rowid: int) -> List[Tuple[int, str]]:
    exts: List[Tuple[int, str]] = []
    for ext_id in get_lexicon_extensions(rowid):
        lexinfo = get_lexicon(ext_id)
        exts.append((ext_id, f'{lexinfo[1]}:{lexinfo[6]}'))
    return exts
