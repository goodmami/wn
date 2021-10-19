
"""Wordnet lexicon validation.

This module is for checking whether the the contents of a lexicon are
valid according to a range of criteria.

"""

from typing import Tuple, List, Dict, Any, Optional, Type, Iterator, Union, cast
from collections import Counter
from itertools import chain

from wn import lmf
from wn.constants import (
    SENSE_RELATIONS,
    SENSE_SYNSET_RELATIONS,
    SYNSET_RELATIONS,
    REVERSE_RELATIONS,
)
from wn.util import ProgressHandler, ProgressBar


_Ids = Dict[str, Counter]
_Result = Dict[str, Any]


def validate(
    lex: Union[lmf.Lexicon, lmf.LexiconExtension],
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar
) -> Dict[str, _Result]:
    if lex.get('extends'):
        print('lexicon extensions not currently validated')
        return {}
    lex = cast(lmf.Lexicon, lex)

    if progress_handler is None:
        progress_handler = ProgressHandler

    ids: _Ids = {
        'entry': Counter(entry['id'] for entry in _entries(lex)),
        'sense': Counter(sense['id']
                         for entry in _entries(lex)
                         for sense in _senses(entry)),
        'synset': Counter(synset['id'] for synset in _synsets(lex)),
    }

    checks = [
        # general identifier checks
        (_non_unique_id, 'non-unique ID'),
        # lexical entries and senses
        (_has_no_senses, 'lexical entry has no senses'),
        (_missing_synset, 'synset of sense is missing'),
        (_redundant_sense, 'redundant sense between lexical entry and synset'),
        (_redundant_entry, 'redundant lexical entry with the same lemma and synset'),
        # ili
        (_repeated_ili, 'ILI is repeated across synsets'),
        (_missing_ili_definition, 'proposed ILI is missing a definition'),
        (_spurious_ili_definition, 'existing ILI has a spurious definition'),
        # synset
        (_unused_synset, 'not a synset for any lexical entry'),
        # relations
        (_missing_relation_target, 'relation target is missing or invalid'),
        (_invalid_relation_type, 'relation type is invalid for the source and target'),
        (_redundant_relation, 'redundant relation between source and target'),
        (_hypernym_wrong_pos, "hypernym's part-of-speech is different than hyponym"),
        (_missing_reverse_relation, 'reverse relation is missing'),
        (_self_loop, 'relation is a self-loop'),
    ]

    progress = progress_handler(message='Validate', total=len(checks))

    report: Dict[str, _Result] = {}
    for check, message in checks:
        progress.set(status=check.__name__.replace('_', ' '))
        report[message] = check(lex, ids)
        progress.update()
    progress.set(status='')
    progress.close()
    return {message: check(lex, ids) for check, message in checks}


def _non_unique_id(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    return _multiples(chain(
        [lex['id']],
        (f['id'] for e in _entries(lex) for f in _forms(e) if f.get('id')),
        (sb['id'] for sb in lex.get('frames', []) if sb.get('id')),
        ids['entry'],
        ids['sense'],
        ids['synset'],
    ))


def _redundant_entry(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    redundant = _multiples((e['lemma']['writtenForm'], s['synset'])
                           for e in _entries(lex)
                           for s in _senses(e))
    return {form: synset for form, synset in redundant}


def _has_no_senses(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    return {e['id']: None for e in _entries(lex) if not _senses(e)}


def _missing_synset(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    synset_ids = ids['synset']
    return {s['id']: s['synset']
            for e in _entries(lex)
            for s in _senses(e)
            if s['synset'] not in synset_ids}


def _redundant_sense(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    report: Dict[str, str] = {}
    for e in _entries(lex):
        redundant = _multiples(s['synset'] for s in _senses(e))
        report.update((s['id'], s['synset'])
                      for s in _senses(e)
                      if s['synset'] in redundant)
    return report


def _repeated_ili(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    repeated = _multiples(
        ss['ili'] for ss in _synsets(lex) if ss['ili'] and ss['ili'] != 'in'
    )
    return {ss['id']: ss['ili'] for ss in _synsets(lex) if ss['ili'] in repeated}


def _missing_ili_definition(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    return {ss['id']: None for ss in _synsets(lex)
            if ss['ili'] == 'in' and not ss.get('ili_definition')}


def _spurious_ili_definition(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    return {ss['id']: None for ss in _synsets(lex)
            if ss['ili'] and ss['ili'] != 'in' and ss.get('ili_definition')}


def _unused_synset(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    synsets = {s['synset'] for e in _entries(lex) for s in _senses(e)}
    return {ss['id']: None for ss in _synsets(lex) if ss['id'] not in synsets}


def _missing_relation_target(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    result = {s['id']: (r['relType'], r['target'])
              for s, r in _sense_relations(lex)
              if r['target'] not in ids['sense'] and r['target'] not in ids['synset']}
    result.update((ss['id'], (r['relType'], r['target']))
                  for ss, r in _synset_relations(lex)
                  if r['target'] not in ids['synset'])
    return result


def _invalid_relation_type(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    result = {s['id']: (r['relType'], r['target'])
              for s, r in _sense_relations(lex)
              if (r['target'] in ids['sense']
                  and r['relType'] not in SENSE_RELATIONS)
              or (r['target'] in ids['synset']
                  and r['relType'] not in SENSE_SYNSET_RELATIONS)}
    result.update((ss['id'], (r['relType'], r['target']))
                  for ss, r in _synset_relations(lex)
                  if r['relType'] not in SYNSET_RELATIONS)
    return result


def _redundant_relation(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    redundant = _multiples(chain(
        ((s['id'], r['relType'], r['target']) for s, r in _sense_relations(lex)),
        ((ss['id'], r['relType'], r['target']) for ss, r in _synset_relations(lex)),
    ))
    return {src: (typ, tgt) for src, typ, tgt in redundant}


def _hypernym_wrong_pos(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    sspos = {ss['id']: ss.get('partOfSpeech') for ss in _synsets(lex)}
    return {ss['id']: (r['relType'], r['target'])
            for ss, r in _synset_relations(lex)
            if r['relType'] == 'hypernym'
            and ss.get('partOfSpeech') != sspos[r['target']]}


def _missing_reverse_relation(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    regular = {(s['id'], r['relType'], r['target'])
               for s, r in _sense_relations(lex)
               if r['target'] in ids['sense']}
    regular.update((ss['id'], r['relType'], r['target'])
                   for ss, r in _synset_relations(lex))
    return {f'{tgt} :{REVERSE_RELATIONS[typ]} {src}': None
            for src, typ, tgt in regular
            if typ in REVERSE_RELATIONS
            and (tgt, REVERSE_RELATIONS[typ], src) not in regular}


def _self_loop(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    relations = chain(_sense_relations(lex), _synset_relations(lex))
    return {x['id']: (r['relType'], r['target'])
            for x, r in relations
            if x['id'] == r['target']}


# Helpers

def _multiples(iterable):
    counts = Counter(iterable)
    return {x: cnt+1 for x, cnt in (counts - Counter(set(counts))).items()}


def _entries(lex: lmf.Lexicon) -> List[lmf.LexicalEntry]: return lex.get('entries', [])
def _forms(e: lmf.LexicalEntry) -> List[lmf.Form]: return e.get('forms', [])
def _senses(e: lmf.LexicalEntry) -> List[lmf.Sense]: return e.get('senses', [])
def _synsets(lex: lmf.Lexicon) -> List[lmf.Synset]: return lex.get('synsets', [])


def _sense_relations(lex: lmf.Lexicon) -> Iterator[Tuple[lmf.Sense, lmf.Relation]]:
    for e in _entries(lex):
        for s in _senses(e):
            for r in s.get('relations', []):
                yield (s, r)


def _synset_relations(lex: lmf.Lexicon) -> Iterator[Tuple[lmf.Synset, lmf.Relation]]:
    for ss in _synsets(lex):
        for r in ss.get('relations', []):
            yield (ss, r)
