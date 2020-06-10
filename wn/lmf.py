
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import NamedTuple, Tuple, List, Dict, Optional, Type, TypeVar
import warnings
import xml.etree.ElementTree as ET

from wn._types import AnyPath


class LMFError(Exception):
    """Raised on invalid LMF-XML documents."""


class LMFWarning(Warning):
    """Issued on non-conforming LFM values."""


_sense_rels = (
    'antonym',
    'also',
    'participle',
    'pertainym',
    'derivation',
    'domain_topic',
    'has_domain_topic',
    'domain_region',
    'has_domain_region',
    'exemplifies',
    'is_exemplified_by',
    'similar',
    'other',
)

_synset_rels = (
    'agent',
    'also',
    'attribute',
    'be_in_state',
    'causes',
    'classified_by',
    'classifies',
    'co_agent_instrument',
    'co_agent_patient',
    'co_agent_result',
    'co_instrument_agent',
    'co_instrument_patient',
    'co_instrument_result',
    'co_patient_agent',
    'co_patient_instrument',
    'co_result_agent',
    'co_result_instrument',
    'co_role',
    'direction',
    'domain_region',
    'domain_topic',
    'exemplifies',
    'entails',
    'eq_synonym',
    'has_domain_region',
    'has_domain_topic',
    'is_exemplified_by',
    'holo_location',
    'holo_member',
    'holo_part',
    'holo_portion',
    'holo_substance',
    'holonym',
    'hypernym',
    'hyponym',
    'in_manner',
    'instance_hypernym',
    'instance_hyponym',
    'instrument',
    'involved',
    'involved_agent',
    'involved_direction',
    'involved_instrument',
    'involved_location',
    'involved_patient',
    'involved_result',
    'involved_source_direction',
    'involved_target_direction',
    'is_caused_by',
    'is_entailed_by',
    'location',
    'manner_of',
    'mero_location',
    'mero_member',
    'mero_part',
    'mero_portion',
    'mero_substance',
    'meronym',
    'similar',
    'other',
    'patient',
    'restricted_by',
    'restricts',
    'result',
    'role',
    'source_direction',
    'state_of',
    'target_direction',
    'subevent',
    'is_subevent_of',
    'antonym',
)

_adjpositions = (
    'a',
    'ip',
    'p',
)

_pos = tuple('nvarstcpxu')

_dc_uri = 'http://purl.org/dc/elements/1.1/'

_dc_qname_pairs = (
    (f'{{{_dc_uri}}}contributor', 'contributor'),
    (f'{{{_dc_uri}}}coverage', 'coverage'),
    (f'{{{_dc_uri}}}creator', 'creator'),
    (f'{{{_dc_uri}}}date', 'date'),
    (f'{{{_dc_uri}}}description', 'description'),
    (f'{{{_dc_uri}}}format', 'format'),
    (f'{{{_dc_uri}}}identifier', 'identifier'),
    (f'{{{_dc_uri}}}publisher', 'publisher'),
    (f'{{{_dc_uri}}}relation', 'relation'),
    (f'{{{_dc_uri}}}rights', 'rights'),
    (f'{{{_dc_uri}}}source', 'source'),
    (f'{{{_dc_uri}}}subject', 'subject'),
    (f'{{{_dc_uri}}}title', 'title'),
    (f'{{{_dc_uri}}}type', 'type'),
)

DublinCoreMetadata = Dict  # While we support Python < 3.8

# use the following if Python 3.8+
# class DublinCoreMetadata(TypedDict, total=False):
#     contributor: str
#     coverage: str
#     creator: str
#     date: str
#     description: str
#     format: str
#     identifier: str
#     publisher: str
#     relation: str
#     rights: str
#     source: str
#     subject: str
#     title: str
#     -type: str  # NOTE: -type is to avoid mypy type comments


# These types model the WN-LMF DTD
# http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd

class Count(NamedTuple):
    value: int
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class SyntacticBehaviour(NamedTuple):
    subcategorization_frame: str
    senses: Tuple[str, ...]


class SenseRelation(NamedTuple):
    target: str
    type: str  # Literal[*_sense_rels] if python 3.8+
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class SynsetRelation(NamedTuple):
    target: str
    type: str  # Literal[*_synset_rels] if python 3.8+
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Example(NamedTuple):
    text: str
    language: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class ILIDefinition(NamedTuple):
    text: str
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Definition(NamedTuple):
    text: str
    language: Optional[str] = None
    source_sense: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Synset(NamedTuple):
    id: str
    ili: str
    pos: Optional[str] = None  # Literal[*_pos] if Python 3.8+
    definitions: Tuple[Definition, ...] = ()
    ili_definition: Optional[ILIDefinition] = None
    relations: Tuple[SynsetRelation, ...] = ()
    examples: Tuple[Example, ...] = ()
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Sense(NamedTuple):
    id: str
    synset: str
    relations: Tuple[SenseRelation, ...] = ()
    examples: Tuple[Example, ...] = ()
    counts: Tuple[Count, ...] = ()
    lexicalized: bool = True
    adjposition: Optional[str] = None  # Literal[*_adjpositions] if Python 3.8+
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Tag(NamedTuple):
    text: str
    category: str


class Form(NamedTuple):
    form: str
    script: Optional[str] = None
    tags: Tuple[Tag, ...] = ()


class Lemma(NamedTuple):
    form: str
    pos: str  # Literal[*_pos] if Python 3.8+
    script: Optional[str] = None
    tags: Tuple[Tag, ...] = ()


class LexicalEntry(NamedTuple):
    id: str
    lemma: Lemma
    forms: Tuple[Form, ...] = ()
    senses: Tuple[Sense, ...] = ()
    syntactic_behaviors: Tuple[SyntacticBehaviour, ...] = ()
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


class Lexicon(NamedTuple):
    id: str
    label: str
    language: str
    email: str
    license: str
    version: str
    lemmas: Tuple[LexicalEntry, ...]
    synsets: Tuple[Synset, ...]
    url: Optional[str] = None
    citation: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None
    dcmeta: Optional[DublinCoreMetadata] = None


LexicalResource = Tuple[Lexicon, ...]


def load(source: AnyPath) -> LexicalResource:
    """Load wordnets encoded in the LMF-XML format.

    Args:
        source: path to an LMF-XML file
    """

    events = ET.iterparse(source, events=('start', 'end'))
    root = next(events)[1]
    event, elem = next(events)

    lexicons: List[Lexicon] = []
    while event == 'start' and elem.tag == 'Lexicon':
        lexicons.append(_load_lexicon(elem, events))
        root.clear()
        event, elem = next(events)

    _assert_closed(event, elem, 'LexicalResource')

    return tuple(lexicons)


def _load_lexicon(local_root, events) -> Lexicon:
    attrs = local_root.attrib
    event, elem = next(events)

    lemmas: List[LexicalEntry] = []
    while event == 'start' and elem.tag == 'LexicalEntry':
        lemmas.append(_load_lexical_entry(elem, events))
        local_root.clear()
        event, elem = next(events)

    synsets: List[Synset] = []
    while event == 'start' and elem.tag == 'Synset':
        synsets.append(_load_synset(elem, events))
        local_root.clear()
        event, elem = next(events)

    _assert_closed(event, elem, 'Lexicon')

    return Lexicon(
        attrs['id'],
        attrs['label'],
        attrs['language'],
        attrs['email'],
        attrs['license'],
        attrs['version'],
        tuple(lemmas),
        tuple(synsets),
        url=attrs.get('url'),
        citation=attrs.get('citation'),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_lexical_entry(local_root, events) -> LexicalEntry:
    attrs = local_root.attrib
    lemma: Lemma = _load_lemma(events)
    event, elem = next(events)

    forms: List[Form] = []
    while event == 'start' and elem.tag == 'Form':
        forms.append(_load_form(elem, events))
        event, elem = next(events)

    senses: List[Sense] = []
    while event == 'start' and elem.tag == 'Sense':
        senses.append(_load_sense(elem, events))
        event, elem = next(events)

    syntactic_behaviors: List[SyntacticBehaviour] = []
    while event == 'start' and elem.tag == 'SyntacticBehaviour':
        event, elem = next(events)
        _assert_closed(event, elem, 'SyntacticBehaviour')
        syntactic_behaviors.append(_load_syntactic_behavior(elem))
        event, elem = next(events)

    _assert_closed(event, elem, 'LexicalEntry')

    return LexicalEntry(
        attrs['id'],
        lemma,
        forms=tuple(forms),
        senses=tuple(senses),
        syntactic_behaviors=tuple(syntactic_behaviors),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_lemma(events) -> Lemma:
    event, elem = next(events)
    if event != 'start' or elem.tag != 'Lemma':
        raise LMFError('expected a Lemma element')
    attrs = elem.attrib
    return Lemma(
        attrs['writtenForm'],
        _get_literal(attrs['partOfSpeech'], _pos),
        script=attrs.get('script'),
        tags=_load_tags_until(events, 'Lemma'))


def _load_form(local_root, events) -> Form:
    attrs = local_root.attrib
    return Form(
        attrs['writtenForm'],
        script=attrs.get('script'),
        tags=_load_tags_until(events, 'Form'))


def _load_tags_until(events, terminus) -> Tuple[Tag, ...]:
    event, elem = next(events)

    tags: List[Tag] = []
    while event == 'start' and elem.tag == 'Tag':
        event, elem = next(events)
        _assert_closed(event, elem, 'Tag')
        tags.append(Tag(elem.text, elem.attrib['category']))
        event, elem = next(events)

    _assert_closed(event, elem, terminus)

    return tuple(tags)


def _load_sense(local_root, events) -> Sense:
    attrs = local_root.attrib
    event, elem = next(events)

    relations: List[SenseRelation] = []
    while event == 'start' and elem.tag == 'SenseRelation':
        event, elem = next(events)
        _assert_closed(event, elem, 'SenseRelation')
        relations.append(_load_relation(elem, SenseRelation, _sense_rels))
        event, elem = next(events)

    examples: List[Example] = []
    while event == 'start' and elem.tag == 'Example':
        event, elem = next(events)
        _assert_closed(event, elem, 'Example')
        examples.append(_load_example(elem))
        event, elem = next(events)

    counts: List[Count] = []
    while event == 'start' and elem.tag == 'Count':
        event, elem = next(events)
        _assert_closed(event, elem, 'Count')
        counts.append(_load_count(elem))
        event, elem = next(events)

    _assert_closed(event, elem, 'Sense')

    return Sense(
        attrs['id'],
        attrs['synset'],
        relations=tuple(relations),
        examples=tuple(examples),
        counts=tuple(counts),
        lexicalized=_get_bool(attrs.get('lexicalized', 'true')),
        adjposition=_get_optional_literal(attrs.get('adjposition'), _adjpositions),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


_R = TypeVar('_R', SynsetRelation, SenseRelation)


def _load_relation(elem, cls: Type[_R], choices: Tuple[str, ...]) -> _R:
    attrs = elem.attrib
    return cls(
        attrs['target'],
        _get_literal(attrs['relType'], choices),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_example(elem) -> Example:
    attrs = elem.attrib
    return Example(
        elem.text,
        language=attrs.get('language'),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_count(elem) -> Count:
    attrs = elem.attrib
    value: int = -1
    try:
        value = int(elem.text)
    except ValueError:
        warnings.warn(f'count must be an integer: {elem.text}', LMFWarning)
    return Count(
        value,
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_syntactic_behavior(elem) -> SyntacticBehaviour:
    attrs = elem.attrib
    return SyntacticBehaviour(
        attrs['subcategorizationFrame'],
        senses=tuple(attrs.get('senses', '').split()),
    )


def _load_synset(local_root, events) -> Synset:
    attrs = local_root.attrib
    event, elem = next(events)

    definitions: List[Definition] = []
    while event == 'start' and elem.tag == 'Definition':
        event, elem = next(events)
        _assert_closed(event, elem, 'Definition')
        definitions.append(_load_definition(elem))
        event, elem = next(events)

    ili_definition = None
    if event == 'start' and elem.tag == 'ILIDefinition':
        event, elem = next(events)
        _assert_closed(event, elem, 'ILIDefinition')
        ili_definition = _load_ilidefinition(elem)
        event, elem = next(events)

    relations: List[SynsetRelation] = []
    while event == 'start' and elem.tag == 'SynsetRelation':
        event, elem = next(events)
        _assert_closed(event, elem, 'SynsetRelation')
        relations.append(_load_relation(elem, SynsetRelation, _synset_rels))
        event, elem = next(events)

    examples: List[Example] = []
    while event == 'start' and elem.tag == 'Example':
        event, elem = next(events)
        _assert_closed(event, elem, 'Example')
        examples.append(_load_example(elem))
        event, elem = next(events)

    _assert_closed(event, elem, 'Synset')

    return Synset(
        attrs['id'],
        attrs['ili'],
        pos=_get_optional_literal(attrs['partOfSpeech'], _pos),
        definitions=tuple(definitions),
        ili_definition=ili_definition,
        relations=tuple(relations),
        examples=tuple(examples),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_definition(elem) -> Definition:
    attrs = elem.attrib
    return Definition(
        elem.text,
        language=attrs.get('language'),
        source_sense=attrs.get('sourceSense'),
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _load_ilidefinition(elem) -> ILIDefinition:
    attrs = elem.attrib
    return ILIDefinition(
        elem.text,
        status=attrs.get('status'),
        note=attrs.get('note'),
        confidence=_get_confidence(attrs),
        dcmeta=_get_dublin_core_metadata(attrs),
    )


def _get_confidence(attrs: Dict) -> Optional[float]:
    conf = attrs.get('confidenceScore')
    if conf:
        try:
            conf = float(conf)
            assert 0 <= conf <= 1
        except (ValueError, AssertionError):
            warnings.warn(f'confidenceScore not between 0 and 1: {conf}', LMFWarning)
            conf = None
    return conf


def _get_bool(value: str) -> bool:
    value = value.lower()
    if value not in ('true', 'false'):
        warnings.warn(f'value must be "true" or "false", not {value!r}', LMFWarning)
    return value == 'true'


def _get_optional_literal(value: Optional[str], choices: Tuple[str, ...]) -> Optional[str]:
    if value is None:
        return value
    else:
        return _get_literal(value, choices)


def _get_literal(value: str, choices: Tuple[str, ...]) -> str:
    if value is not None and value not in choices:
        warnings.warn(f'{value!r} is not one of {choices!r}', LMFWarning)
    return value


def _get_dublin_core_metadata(attrs: Dict) -> DublinCoreMetadata:
    dc: DublinCoreMetadata = {}
    for qname, name in _dc_qname_pairs:
        if qname in attrs:
            dc[name] = attrs[qname]
    return dc


def _assert_closed(event, elem, tag) -> None:
    if event != 'end' or elem.tag != tag:
        raise _unexpected(elem)


def _unexpected(elem) -> LMFError:
    return LMFError(f'unexpected element: {elem.tag}')
