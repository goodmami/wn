"""
Adding and removing lexicons to/from the database.
"""

from typing import (
    Union, Optional, TypeVar, Type, Tuple, List, Dict, Set,
    Iterator, Iterable, Sequence, cast
)
from pathlib import Path
from itertools import islice
import sqlite3
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

_AnyLexicon = Union[lmf.Lexicon, lmf.LexiconExtension]
_AnyEntry = Union[lmf.LexicalEntry, lmf.ExternalLexicalEntry]
_AnyLemma = Union[lmf.Lemma, lmf.ExternalLemma]
_AnyForm = Union[lmf.Form, lmf.ExternalForm]
_AnySense = Union[lmf.Sense, lmf.ExternalSense]
_AnySynset = Union[lmf.Synset, lmf.ExternalSynset]


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
    source: Path,
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
        all_infos = _precheck(source, cur)

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
        resource = lmf.load(source, progress_handler)

        for lexicon, info in zip(resource['lexicons'], all_infos):
            if 'skip' in info:
                continue

            progress.flash('Updating lookup tables')
            _update_lookup_tables(lexicon, cur)

            progress.set(count=0, total=_sum_counts(lexicon))
            synsets: Sequence[_AnySynset] = _synsets(lexicon)
            entries: Sequence[_AnyEntry] = _entries(lexicon)
            synbhrs: Sequence[lmf.SyntacticBehaviour] = _collect_frames(lexicon)

            lexid, extid = _insert_lexicon(lexicon, info, cur, progress)

            lexidmap = _build_lexid_map(lexicon, lexid, extid)

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
            _insert_examples([sense for e in entries for sense in _senses(e)],
                             lexid, lexidmap, 'sense_examples', cur, progress)
            _insert_examples(synsets, lexid, lexidmap, 'synset_examples', cur, progress)

            progress.set(status='')  # clear type string
            progress.flash(
                f"Added {lexicon['id']}:{lexicon['version']} ({lexicon['label']})\n"
            )


def _precheck(source: Path, cur: sqlite3.Cursor) -> List[Dict]:
    lexqry = 'SELECT * FROM lexicons WHERE id = :id AND version = :version'
    infos = lmf.scan_lexicons(source)
    for info in infos:
        base = info.get('extends')
        if cur.execute(lexqry, info).fetchone():
            info['skip'] = 'already added'
        if base and cur.execute(lexqry, base).fetchone() is None:
            id_, ver = base['id'], base['version']
            info['skip'] = f'base lexicon ({id_}:{ver}) not available'
    return infos


def _sum_counts(lex: _AnyLexicon) -> int:
    ents = _entries(lex)
    locs = _local_entries(ents)
    lems = [e['lemma'] for e in locs if e.get('lemma')]
    frms = [f for e in ents for f in _forms(e)]
    sens = [s for e in ents for s in _senses(e)]
    syns = _synsets(lex)
    return sum([
        # lexical entries
        len(ents),
        len(lems),
        sum(len(lem.get('pronunciations', [])) for lem in lems),
        sum(len(lem.get('tags', [])) for lem in lems),
        len(frms),
        sum(len(frm.get('pronunciations', [])) for frm in frms),
        sum(len(frm.get('tags', [])) for frm in frms),
        # senses
        len(sens),
        sum(len(sen.get('relations', [])) for sen in sens),
        sum(len(sen.get('examples', [])) for sen in sens),
        sum(len(sen.get('counts', [])) for sen in sens),
        # synsets
        len(syns),
        sum(len(syn.get('definitions', [])) for syn in syns),
        sum(len(syn.get('relations', [])) for syn in syns),
        sum(len(syn.get('examples', [])) for syn in syns),
        # syntactic behaviours
        sum(len(ent.get('frames', [])) for ent in locs),
        len(lex.get('frames', [])),
    ])


def _update_lookup_tables(
    lexicon: _AnyLexicon,
    cur: sqlite3.Cursor
) -> None:
    reltypes = set(rel['relType']
                   for ss in _synsets(lexicon)
                   for rel in ss.get('relations', []))
    reltypes.update(rel['relType']
                    for e in _entries(lexicon)
                    for s in _senses(e)
                    for rel in s.get('relations', []))
    cur.executemany('INSERT OR IGNORE INTO relation_types VALUES (null,?)',
                    [(rt,) for rt in sorted(reltypes)])
    lexfiles: Set[str] = {ss.get('lexfile', '')
                          for ss in _local_synsets(_synsets(lexicon))
                          if ss.get('lexfile')}
    cur.executemany('INSERT OR IGNORE INTO lexfiles VALUES (null,?)',
                    [(lf,) for lf in sorted(lexfiles)])


def _insert_lexicon(
    lexicon: _AnyLexicon,
    info: dict,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> Tuple[int, int]:
    progress.set(status='Lexicon Info')
    cur.execute(
        'INSERT INTO lexicons VALUES (null,?,?,?,?,?,?,?,?,?,?,?)',
        (lexicon['id'],
         lexicon['label'],
         lexicon['language'],
         lexicon['email'],
         lexicon['license'],
         lexicon['version'],
         lexicon.get('url'),
         lexicon.get('citation'),
         lexicon.get('logo'),
         lexicon.get('meta'),
         False))
    lexid = cur.lastrowid

    query = '''
        UPDATE lexicon_dependencies
           SET provider_rowid = ?
         WHERE provider_id = ? AND provider_version = ?
    '''
    cur.execute(query, (lexid, lexicon['id'], lexicon['version']))

    query = '''
        INSERT INTO {table}
        VALUES (:lid,
                :id,
                :version,
                :url,
                (SELECT rowid FROM lexicons WHERE id=:id AND version=:version))
    '''
    params = []
    for dep in lexicon.get('requires', []):
        param_dict = dict(dep)
        param_dict.setdefault('url', None)
        param_dict['lid'] = lexid
        params.append(param_dict)
    if params:
        cur.executemany(query.format(table='lexicon_dependencies'), params)

    if lexicon.get('extends'):
        lexicon = cast(lmf.LexiconExtension, lexicon)
        param_dict = dict(lexicon['extends'])
        param_dict.setdefault('url', None)
        param_dict['lid'] = lexid
        cur.execute(query.format(table='lexicon_extensions'), param_dict)
        extid = cur.execute(
            'SELECT rowid FROM lexicons WHERE id=? AND version=?',
            (param_dict['id'], param_dict['version'])
        ).fetchone()[0]
    else:
        extid = lexid

    return lexid, extid


_LexIdMap = Dict[str, int]


def _build_lexid_map(lexicon: _AnyLexicon, lexid: int, extid: int) -> _LexIdMap:
    """Build a mapping of entity IDs to extended lexicon rowid."""
    lexidmap: _LexIdMap = {}
    if lexid != extid:
        lexidmap.update((e['id'], extid)
                        for e in _entries(lexicon)
                        if _is_external(e))
        lexidmap.update((s['id'], extid)
                        for e in _entries(lexicon)
                        for s in _senses(e)
                        if _is_external(s))
        lexidmap.update((ss['id'], extid)
                        for ss in _synsets(lexicon)
                        if _is_external(ss))
    return lexidmap


T = TypeVar('T')


def _batch(sequence: Iterable[T]) -> Iterator[List[T]]:
    it = iter(sequence)
    batch = list(islice(it, 0, BATCH_SIZE))
    while len(batch):
        yield batch
        batch = list(islice(it, 0, BATCH_SIZE))


def _insert_synsets(
    synsets: Sequence[_AnySynset],
    lexid: int,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
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

    for batch in _batch(_local_synsets(synsets)):

        # first add presupposed ILIs
        pre_ili_data = []
        for ss in batch:
            ili = ss['ili']
            if ili and ili != 'in':
                defn = ss.get('ili_definition')  # normally null
                text = defn['text'] if defn else None
                meta = defn['meta'] if defn else None
                pre_ili_data.append((ili, 'presupposed', text, meta))
        cur.executemany(pre_ili_query, pre_ili_data)

        # then add synsets
        ss_data = (
            (ss['id'],
             lexid,
             ss['ili'] if ss['ili'] and ss['ili'] != 'in' else None,
             ss['partOfSpeech'],
             ss.get('lexicalized', True),
             ss.get('lexfile'),
             ss['meta'])
            for ss in batch
        )
        cur.executemany(ss_query, ss_data)

        # finally add proposed ILIs
        pro_ili_data = []
        for ss in batch:
            ili = ss['ili']
            if ili == 'in':
                defn = ss.get('ili_definition')
                text = defn['text'] if defn else None
                meta = defn['meta'] if defn else None
                pro_ili_data.append((ss['id'], lexid, text, meta))
        cur.executemany(pro_ili_query, pro_ili_data)

        progress.update(len(batch))


def _insert_synset_definitions(
    synsets: Sequence[_AnySynset],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Definitions')
    query = f'''
        INSERT INTO definitions
        VALUES (null,?,({SYNSET_QUERY}),?,?,({SENSE_QUERY}),?)
    '''
    for batch in _batch(synsets):
        data = [
            (lexid,
             synset['id'],
             lexidmap.get(synset['id'], lexid),
             definition['text'],
             definition.get('language'),
             definition.get('sourceSense'),
             lexidmap.get(definition.get('sourceSense', ''), lexid),
             definition['meta'])
            for synset in batch
            for definition in synset.get('definitions', [])
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_synset_relations(
    synsets: Sequence[_AnySynset],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Synset Relations')
    query = f'''
        INSERT INTO synset_relations
        VALUES (null,?,({SYNSET_QUERY}),({SYNSET_QUERY}),({RELTYPE_QUERY}),?)
    '''
    for batch in _batch(synsets):
        data = [
            (lexid,
             synset['id'], lexidmap.get(synset['id'], lexid),
             relation['target'], lexidmap.get(relation['target'], lexid),
             relation['relType'],
             relation['meta'])
            for synset in batch
            for relation in synset.get('relations', [])
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_entries(
    entries: Sequence[_AnyEntry],
    lexid: int,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Words')
    query = 'INSERT INTO entries VALUES (null,?,?,?,?)'
    for batch in _batch(_local_entries(entries)):
        data = (
            (entry['id'],
             lexid,
             entry['lemma']['partOfSpeech'],
             entry['meta'])
            for entry in batch
        )
        cur.executemany(query, data)
        progress.update(len(batch))


def _insert_forms(
    entries: Sequence[_AnyEntry],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Word Forms')
    query = f'INSERT INTO forms VALUES (null,?,?,({ENTRY_QUERY}),?,?,?,?)'
    for batch in _batch(entries):
        forms: List[Tuple[Optional[str], int, str, int,
                          str, Optional[str], Optional[str], int]] = []
        for entry in batch:
            eid = entry['id']
            lid = lexidmap.get(eid, lexid)
            if not _is_external(entry):
                entry = cast(lmf.LexicalEntry, entry)
                written_form = entry['lemma']['writtenForm']
                norm = normalize_form(written_form)
                forms.append(
                    (None, lexid, eid, lid,
                     written_form, norm if norm != written_form else None,
                     entry['lemma'].get('script'), 0)
                )
            for i, form in enumerate(_forms(entry), 1):
                if _is_external(form):
                    continue
                form = cast(lmf.Form, form)
                written_form = form['writtenForm']
                norm = normalize_form(written_form)
                forms.append(
                    (form.get('id'), lexid, eid, lid,
                     written_form, norm if norm != written_form else None,
                     form.get('script'), i)
                )
        cur.executemany(query, forms)
        progress.update(len(forms))


def _insert_pronunciations(
    entries: Sequence[_AnyEntry],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Pronunciations')
    query = f'INSERT INTO pronunciations VALUES (({FORM_QUERY}),?,?,?,?,?)'
    for batch in _batch(entries):
        prons: List[Tuple[str, int, Optional[str], int,
                          str, Optional[str], Optional[str],
                          bool, Optional[str]]] = []
        for entry in batch:
            eid = entry['id']
            lid = lexidmap.get(eid, lexid)
            if entry.get('lemma'):
                for p in entry['lemma'].get('pronunciations', []):
                    prons.append(
                        (eid, lid, None, 0,
                         p['text'], p.get('variety'), p.get('notation'),
                         p.get('phonemic', True), p.get('audio'))
                    )
            for i, form in enumerate(_forms(entry), 1):
                # rank is not valid in FORM_QUERY for external forms
                rank = -1 if _is_external(form) else i
                for p in form.get('pronunciations', []):
                    prons.append(
                        (eid, lid, form.get('id'), rank,
                         p['text'], p.get('variety'), p.get('notation'),
                         p.get('phonemic', True), p.get('audio'))
                    )
        cur.executemany(query, prons)
        progress.update(len(prons))


def _insert_tags(
    entries: Sequence[_AnyEntry],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Word Form Tags')
    query = f'INSERT INTO tags VALUES (({FORM_QUERY}),?,?)'
    for batch in _batch(entries):
        tags: List[Tuple[str, int, Optional[str], int, str, str]] = []
        for entry in batch:
            eid = entry['id']
            lid = lexidmap.get(eid, lexid)
            if entry.get('lemma'):
                for tag in entry['lemma'].get('tags', []):
                    tags.append((eid, lid, None, 0, tag['text'], tag['category']))
            for i, form in enumerate(_forms(entry), 1):
                # rank is not valid in FORM_QUERY for external forms
                rank = -1 if _is_external(form) else i
                for tag in form.get('tags', []):
                    tags.append(
                        (eid, lid, form.get('id'), rank, tag['text'], tag['category'])
                    )
        cur.executemany(query, tags)
        progress.update(len(tags))


def _insert_senses(
    entries: Sequence[_AnyEntry],
    synsets: Sequence[_AnySynset],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Senses')
    ssrank = {s: i
              for ss in _local_synsets(synsets)
              for i, s in enumerate(ss.get('members', []))}
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
    for batch in _batch(entries):
        data = [
            (sense['id'],
             lexid,
             entry['id'], lexidmap.get(entry['id'], lexid),
             i,
             sense['synset'], lexidmap.get(sense['synset'], lexid),
             ssrank.get(sense['id'], DEFAULT_MEMBER_RANK),
             sense.get('lexicalized', True),
             sense['meta'])
            for entry in batch
            for i, sense in enumerate(_local_senses(_senses(entry)))
        ]
        cur.executemany(query, data)
        progress.update(len(data))


def _insert_adjpositions(
    entries: Sequence[_AnyEntry],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
):
    progress.set(status='Sense Adjpositions')
    data = [(s['id'], lexidmap.get(s['id'], lexid), s['adjposition'])
            for e in entries
            for s in _local_senses(_senses(e))
            if s.get('adjposition')]
    query = f'INSERT INTO adjpositions VALUES (({SENSE_QUERY}),?)'
    cur.executemany(query, data)


def _insert_counts(
    entries: Sequence[_AnyEntry],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Counts')
    data = [(lexid,
             sense['id'], lexidmap.get(sense['id'], lexid),
             count['value'],
             count['meta'])
            for entry in entries
            for sense in _senses(entry)
            for count in sense.get('counts', [])]
    query = f'INSERT INTO counts VALUES (null,?,({SENSE_QUERY}),?,?)'
    cur.executemany(query, data)
    progress.update(len(data))


def _collect_frames(lexicon: _AnyLexicon) -> List[lmf.SyntacticBehaviour]:
    # WN-LMF 1.0 syntactic behaviours are on lexical entries, and in
    # WN-LMF 1.1 they are at the lexticon level with IDs. This
    # function normalizes the two variants.

    # IDs are not required and frame strings must be unique in a
    # lexicon, so lookup syntactic behaviours by the frame string
    synbhrs: Dict[str, lmf.SyntacticBehaviour] = {
        frame['subcategorizationFrame']: {
            'id': frame['id'],
            'subcategorizationFrame': frame['subcategorizationFrame'],
            'senses': frame.get('senses', []),
        }
        for frame in lexicon.get('frames', [])
    }
    # all relevant senses are collected into the 'senses' key
    id_senses_map = {sb['id']: sb['senses']
                     for sb in synbhrs.values() if sb.get('id')}
    for entry in _entries(lexicon):
        # for WN-LMF 1.1
        for sense in _local_senses(_senses(entry)):
            for sbid in sense.get('subcat', []):
                id_senses_map[sbid].append(sense['id'])
        # for WN-LMF 1.0
        if _is_external(entry) or not entry.get('frames'):
            continue
        entry = cast(lmf.LexicalEntry, entry)
        all_senses = [s['id'] for s in _senses(entry)]
        for frame in entry.get('frames', []):
            subcat_frame = frame['subcategorizationFrame']
            if subcat_frame not in synbhrs:
                synbhrs[subcat_frame] = {'subcategorizationFrame': subcat_frame,
                                         'senses': []}
            senses = frame.get('senses', []) or all_senses
            synbhrs[subcat_frame]['senses'].extend(senses)
    return list(synbhrs.values())


def _insert_syntactic_behaviours(
    synbhrs: Sequence[lmf.SyntacticBehaviour],
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Syntactic Behaviours')

    query = 'INSERT INTO syntactic_behaviours VALUES (null,?,?,?)'
    sbdata = [(sb.get('id') or None, lexid, sb['subcategorizationFrame'])
              for sb in synbhrs]
    cur.executemany(query, sbdata)

    # syntactic behaviours don't have a required ID; index on frame
    framemap: Dict[str, List[str]] = {
        sb['subcategorizationFrame']: sb.get('senses', []) for sb in synbhrs
    }
    query = f'''
        INSERT INTO syntactic_behaviour_senses
        VALUES ((SELECT rowid
                   FROM syntactic_behaviours
                  WHERE lexicon_rowid=? AND frame=?),
                ({SENSE_QUERY}))
    '''
    sbsdata = [(lexid, frame, sid, lexidmap.get(sid, lexid))
               for frame in framemap
               for sid in framemap[frame]]
    cur.executemany(query, sbsdata)

    progress.update(len(synbhrs))


def _insert_sense_relations(
    lexicon: _AnyLexicon,
    lexid: int,
    lexidmap: _LexIdMap,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Sense Relations')
    # need to separate relations into those targeting senses vs synsets
    synset_ids = {ss['id'] for ss in _synsets(lexicon)}
    sense_ids = {s['id']
                 for e in _entries(lexicon)
                 for s in _senses(e)}
    s_s_rels = []
    s_ss_rels = []
    for entry in _entries(lexicon):
        for sense in _senses(entry):
            slid = lexidmap.get(sense['id'], lexid)
            for relation in sense.get('relations', []):
                target_id = relation['target']
                tlid = lexidmap.get(target_id, lexid)
                if target_id in sense_ids:
                    s_s_rels.append((sense['id'], slid, tlid, relation))
                elif target_id in synset_ids:
                    s_ss_rels.append((sense['id'], slid, tlid, relation))
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
        for batch in _batch(rels):
            data = [
                (lexid,
                 sense_id, slid,
                 relation['target'], tlid,
                 relation['relType'],
                 relation['meta'])
                for sense_id, slid, tlid, relation in batch
            ]
            cur.executemany(query, data)
            progress.update(len(data))


def _insert_examples(
    objs: Sequence[Union[lmf.Sense, lmf.ExternalSense, lmf.Synset, lmf.ExternalSynset]],
    lexid: int,
    lexidmap: _LexIdMap,
    table: str,
    cur: sqlite3.Cursor,
    progress: ProgressHandler
) -> None:
    progress.set(status='Examples')
    if table == 'sense_examples':
        query = f'INSERT INTO {table} VALUES (null,?,({SENSE_QUERY}),?,?,?)'
    else:
        query = f'INSERT INTO {table} VALUES (null,?,({SYNSET_QUERY}),?,?,?)'
    for batch in _batch(objs):
        data = [
            (lexid,
             obj['id'], lexidmap.get(obj['id'], lexid),
             example['text'],
             example.get('language'),
             example['meta'])
            for obj in batch
            for example in obj.get('examples', [])
        ]
        # be careful of SQL injection here
        cur.executemany(query, data)
        progress.update(len(data))


def _add_ili(
    source: Path,
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
        for batch in _batch(ili):
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


def _entries(lex: _AnyLexicon) -> Sequence[_AnyEntry]: return lex.get('entries', [])
def _forms(e: _AnyEntry) -> Sequence[_AnyForm]: return e.get('forms', [])
def _senses(e: _AnyEntry) -> Sequence[_AnySense]: return e.get('senses', [])
def _synsets(lex: _AnyLexicon) -> Sequence[_AnySynset]: return lex.get('synsets', [])


def _is_external(
    x: Union[_AnyForm, _AnyLemma, _AnyEntry, _AnySense, _AnySynset]
) -> bool:
    return x.get('external', False) is True


def _local_synsets(synsets: Sequence[_AnySynset]) -> Iterator[lmf.Synset]:
    for ss in synsets:
        if _is_external(ss):
            continue
        yield cast(lmf.Synset, ss)


def _local_entries(entries: Sequence[_AnyEntry]) -> Iterator[lmf.LexicalEntry]:
    for e in entries:
        if _is_external(e):
            continue
        yield cast(lmf.LexicalEntry, e)


def _local_senses(senses: Sequence[_AnySense]) -> Iterator[lmf.Sense]:
    for s in senses:
        if _is_external(s):
            continue
        yield cast(lmf.Sense, s)
