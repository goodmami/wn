
"""Wordnet lexicon validation.

This module is for checking whether the the contents of a lexicon are
valid according to a series of checks. Those checks are:

====  ==========================================================
Code  Message
====  ==========================================================
E101  ID is not unique within the lexicon.
W201  Lexical entry has no senses.
W202  Redundant sense between lexical entry and synset.
W203  Redundant lexical entry with the same lemma and synset.
E204  Synset of sense is missing.
W301  Synset is empty (not associated with any lexical entries).
W302  ILI is repeated across synsets.
W303  Proposed ILI is missing a definition.
W304  Existing ILI has a spurious definition.
E401  Relation target is missing or invalid.
W402  Relation type is invalid for the source and target.
W403  Redundant relation between source and target.
W404  Reverse relation is missing.
W501  Synset's part-of-speech is different from its hypernym's.
W502  Relation is a self-loop.
====  ==========================================================

"""

from typing import (Sequence, Iterator, Tuple, List, Dict,
                    Optional, Type, Union, Callable, cast)
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
_Result = Dict[str, Dict]
_CheckFunction = Callable[[lmf.Lexicon, _Ids], _Result]
_Report = Dict[str, Dict[str, Union[str, _Result]]]


def _non_unique_id(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """ID is not unique within the lexicon"""
    return _multiples(chain(
        [lex['id']],
        (f['id'] for e in _entries(lex) for f in _forms(e) if f.get('id')),
        (sb['id'] for sb in lex.get('frames', []) if sb.get('id')),
        ids['entry'],
        ids['sense'],
        ids['synset'],
    ))


def _has_no_senses(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """lexical entry has no senses"""
    return {e['id']: {} for e in _entries(lex) if not _senses(e)}


def _redundant_sense(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """redundant sense between lexical entry and synset"""
    result: _Result = {}
    for e in _entries(lex):
        redundant = _multiples(s['synset'] for s in _senses(e))
        result.update((s['id'], {'entry': e['id'], 'synset': s['synset']})
                      for s in _senses(e)
                      if s['synset'] in redundant)
    return result


def _redundant_entry(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """redundant lexical entry with the same lemma and synset"""
    redundant = _multiples((e['lemma']['writtenForm'], s['synset'])
                           for e in _entries(lex)
                           for s in _senses(e))
    return {form: {'synset': synset} for form, synset in redundant}


def _missing_synset(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """synset of sense is missing"""
    synset_ids = ids['synset']
    return {s['id']: {'synset': s['synset']}
            for e in _entries(lex)
            for s in _senses(e)
            if s['synset'] not in synset_ids}


def _empty_synset(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """synset is empty (not associated with any lexical entries)"""
    synsets = {s['synset'] for e in _entries(lex) for s in _senses(e)}
    return {ss['id']: {} for ss in _synsets(lex) if ss['id'] not in synsets}


def _repeated_ili(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """ILI is repeated across synsets"""
    repeated = _multiples(
        ss['ili'] for ss in _synsets(lex) if ss['ili'] and ss['ili'] != 'in'
    )
    return {ss['id']: {'ili': ss['ili']}
            for ss in _synsets(lex)
            if ss['ili'] in repeated}


def _missing_ili_definition(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """proposed ILI is missing a definition"""
    return {ss['id']: {} for ss in _synsets(lex)
            if ss['ili'] == 'in' and not ss.get('ili_definition')}


def _spurious_ili_definition(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """existing ILI has a spurious definition"""
    return {ss['id']: {'ili_definitin': ss['ili_definition']}
            for ss in _synsets(lex)
            if ss['ili'] and ss['ili'] != 'in' and ss.get('ili_definition')}


def _missing_relation_target(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """relation target is missing or invalid"""
    result = {s['id']: {'type': r['relType'], 'target': r['target']}
              for s, r in _sense_relations(lex)
              if r['target'] not in ids['sense'] and r['target'] not in ids['synset']}
    result.update((ss['id'], {'type': r['relType'], 'target': r['target']})
                  for ss, r in _synset_relations(lex)
                  if r['target'] not in ids['synset'])
    return result


def _invalid_relation_type(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """relation type is invalid for the source and target"""
    result = {s['id']: {'type': r['relType'], 'target': r['target']}
              for s, r in _sense_relations(lex)
              if (r['target'] in ids['sense']
                  and r['relType'] not in SENSE_RELATIONS)
              or (r['target'] in ids['synset']
                  and r['relType'] not in SENSE_SYNSET_RELATIONS)}
    result.update((ss['id'], {'type': r['relType'], 'target': r['target']})
                  for ss, r in _synset_relations(lex)
                  if r['relType'] not in SYNSET_RELATIONS)
    return result


def _redundant_relation(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """redundant relation between source and target"""
    redundant = _multiples(chain(
        ((s['id'], r['relType'], r['target']) for s, r in _sense_relations(lex)),
        ((ss['id'], r['relType'], r['target']) for ss, r in _synset_relations(lex)),
    ))
    return {src: {'type': typ, 'target': tgt} for src, typ, tgt in redundant}


def _missing_reverse_relation(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """reverse relation is missing"""
    regular = {(s['id'], r['relType'], r['target'])
               for s, r in _sense_relations(lex)
               if r['target'] in ids['sense']}
    regular.update((ss['id'], r['relType'], r['target'])
                   for ss, r in _synset_relations(lex))
    return {tgt: {'type': REVERSE_RELATIONS[typ], 'target': src}
            for src, typ, tgt in regular
            if typ in REVERSE_RELATIONS
            and (tgt, REVERSE_RELATIONS[typ], src) not in regular}


def _hypernym_wrong_pos(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """synset's part-of-speech is different from its hypernym's"""
    sspos = {ss['id']: ss.get('partOfSpeech') for ss in _synsets(lex)}
    return {ss['id']: {'type': r['relType'], 'target': r['target']}
            for ss, r in _synset_relations(lex)
            if r['relType'] == 'hypernym'
            and ss.get('partOfSpeech') != sspos[r['target']]}


def _self_loop(lex: lmf.Lexicon, ids: _Ids) -> _Result:
    """relation is a self-loop"""
    relations = chain(_sense_relations(lex), _synset_relations(lex))
    return {x['id']: {'type': r['relType'], 'target': r['target']}
            for x, r in relations
            if x['id'] == r['target']}


# Helpers

def _multiples(iterable):
    counts = Counter(iterable)
    return {x: {'count': cnt} for x, cnt in counts.items() if cnt > 1}


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


# Check codes and messages
#
# categories:
#   E - errors
#   W - warnings
# subcategories:
#   100 - general
#   200 - words and senses
#   300 - synsets and ilis
#   400 - relations
#   500 - graph and taxonomy

_codes: Dict[str, _CheckFunction] = {
    # 100 - general
    'E101': _non_unique_id,
    # 200 - words and senses
    'W201': _has_no_senses,
    'W202': _redundant_sense,
    'W203': _redundant_entry,
    'E204': _missing_synset,
    # 300 - synsets and ilis
    'W301': _empty_synset,
    'W302': _repeated_ili,
    'W303': _missing_ili_definition,
    'W304': _spurious_ili_definition,
    # 400 - relations
    'E401': _missing_relation_target,
    'W402': _invalid_relation_type,
    'W403': _redundant_relation,
    'W404': _missing_reverse_relation,
    # 500 - graph
    'W501': _hypernym_wrong_pos,
    'W502': _self_loop,
}


def _select_checks(select: Sequence[str]) -> List[Tuple[str, _CheckFunction, str]]:
    selectset = set(select)
    return [(code, func, func.__doc__ or '')
            for code, func in _codes.items()
            if code in selectset or code[0] in selectset]


# Main function

def validate(
    lex: Union[lmf.Lexicon, lmf.LexiconExtension],
    select: Sequence[str] = ('E', 'W'),
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar
) -> _Report:
    """Check *lex* for validity and return a report of the results.

    The *select* argument is a sequence of check codes (e.g.,
    ``E101``) or categories (``E`` or ``W``).

    The *progress_handler* parameter takes a subclass of
    :class:`wn.util.ProgressHandler`. An instance of the class will be
    created, used, and closed by this function.
    """
    if lex.get('extends'):
        print('validation of lexicon extensions is not supported')
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

    checks = _select_checks(select)

    progress = progress_handler(message='Validate', total=len(checks))

    report: _Report = {}
    for code, func, message in checks:
        progress.set(status=func.__name__.replace('_', ' '))
        report[code] = {'message': message,
                        'items': func(lex, ids)}
        progress.update()
    progress.set(status='')
    progress.close()
    return report
