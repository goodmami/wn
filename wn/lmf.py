
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import (
    TypeVar,
    Type,
    Container,
    List,
    Dict,
    Set,
    NamedTuple,
    Optional,
    Tuple,
)
import warnings
import xml.etree.ElementTree as ET  # for general XML parsing
import xml.parsers.expat  # for fast scanning of Lexicon versions

from wn._types import AnyPath
from wn.constants import (
    SENSE_RELATIONS,
    SYNSET_RELATIONS,
    ADJPOSITIONS,
    POS_LIST,
)


class LMFError(Exception):
    """Raised on invalid LMF-XML documents."""


class LMFWarning(Warning):
    """Issued on non-conforming LFM values."""


_dc_uri = 'http://purl.org/dc/elements/1.1/'

_dc_qname_pairs = (
    # dublin-core metadata needs the namespace uri prefixed
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


class Metadata(NamedTuple):
    contributor: Optional[str]
    coverage: Optional[str]
    creator: Optional[str]
    date: Optional[str]
    description: Optional[str]
    format: Optional[str]
    identifier: Optional[str]
    publisher: Optional[str]
    relation: Optional[str]
    rights: Optional[str]
    source: Optional[str]
    subject: Optional[str]
    title: Optional[str]
    type: Optional[str]
    status: Optional[str]
    note: Optional[str]
    confidence: Optional[float]


# These types model the WN-LMF DTD
# http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd

class Count(NamedTuple):
    value: int
    meta: Optional[Metadata]


class SyntacticBehaviour(NamedTuple):
    subcategorization_frame: str
    senses: Tuple[str, ...]


class SenseRelation(NamedTuple):
    target: str
    type: str  # Literal[*SENSE_RELATIONS] if python 3.8+
    meta: Optional[Metadata]


class SynsetRelation(NamedTuple):
    target: str
    type: str  # Literal[*SYNSET_RELATIONS] if python 3.8+
    meta: Optional[Metadata]


class Example(NamedTuple):
    text: str
    language: str
    meta: Optional[Metadata]


class ILIDefinition(NamedTuple):
    text: str
    meta: Optional[Metadata]


class Definition(NamedTuple):
    text: str
    language: str
    source_sense: str
    meta: Optional[Metadata]


class Synset(NamedTuple):
    id: str
    ili: str
    pos: str  # Literal[*POS_LIST] if Python 3.8+
    definitions: Tuple[Definition, ...]
    ili_definition: Optional[ILIDefinition]
    relations: Tuple[SynsetRelation, ...]
    examples: Tuple[Example, ...]
    lexicalized: bool
    meta: Optional[Metadata]


class Sense(NamedTuple):
    id: str
    synset: str
    relations: Tuple[SenseRelation, ...]
    examples: Tuple[Example, ...]
    counts: Tuple[Count, ...]
    lexicalized: bool
    adjposition: str  # Literal[*ADJPOSITIONS] if Python 3.8+
    meta: Optional[Metadata]


class Tag(NamedTuple):
    text: str
    category: str


class Form(NamedTuple):
    form: str
    script: str
    tags: Tuple[Tag, ...]


class Lemma(NamedTuple):
    form: str
    pos: str  # Literal[*POS_LIST] if Python 3.8+
    script: str
    tags: Tuple[Tag, ...]


class LexicalEntry(NamedTuple):
    id: str
    lemma: Lemma
    forms: Tuple[Form, ...]
    senses: Tuple[Sense, ...]
    syntactic_behaviours: Tuple[SyntacticBehaviour, ...]
    meta: Optional[Metadata]


class Lexicon(NamedTuple):
    id: str
    label: str
    language: str
    email: str
    license: str
    version: str
    lexical_entries: Tuple[LexicalEntry, ...]
    synsets: Tuple[Synset, ...]
    url: str
    citation: str
    meta: Optional[Metadata]

    def entry_ids(self) -> Set[str]:
        return {entry.id for entry in self.lexical_entries}

    def sense_ids(self) -> Set[str]:
        return {sense.id for entry in self.lexical_entries for sense in entry.senses}

    def synset_ids(self) -> Set[str]:
        return {synset.id for synset in self.synsets}


LexicalResource = Tuple[Lexicon, ...]


def scan_lexicons(source: AnyPath) -> List[Dict]:
    """Scan *source* and return only the top-level lexicon info."""

    # this is implemeted with expat as it's much faster than etree for
    # this task
    infos = []

    def start(name, attrs):
        if name == 'Lexicon':
            attrs['counts'] = {}
            infos.append(attrs)
        elif infos:
            counts = infos[-1]['counts']
            counts[name] = counts.get(name, 0) + 1

    p = xml.parsers.expat.ParserCreate()
    p.StartElementHandler = start
    with open(source, 'rb') as fh:
        p.ParseFile(fh)

    return infos


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
    list(events)  # consume remaining events, if any

    return tuple(lexicons)


def _load_lexicon(local_root, events) -> Lexicon:
    attrs = local_root.attrib
    event, elem = next(events)

    lexical_entries: List[LexicalEntry] = []
    while event == 'start' and elem.tag == 'LexicalEntry':
        lexical_entries.append(_load_lexical_entry(elem, events))
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
        tuple(lexical_entries),
        tuple(synsets),
        url=attrs.get('url'),
        citation=attrs.get('citation'),
        meta=_get_metadata(attrs),
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

    syntactic_behaviours: List[SyntacticBehaviour] = []
    while event == 'start' and elem.tag == 'SyntacticBehaviour':
        event, elem = next(events)
        _assert_closed(event, elem, 'SyntacticBehaviour')
        syntactic_behaviours.append(_load_syntactic_behaviour(elem))
        event, elem = next(events)

    _assert_closed(event, elem, 'LexicalEntry')

    return LexicalEntry(
        attrs['id'],
        lemma,
        forms=tuple(forms),
        senses=tuple(senses),
        syntactic_behaviours=tuple(syntactic_behaviours),
        meta=_get_metadata(attrs),
    )


def _load_lemma(events) -> Lemma:
    event, elem = next(events)
    if event != 'start' or elem.tag != 'Lemma':
        raise LMFError('expected a Lemma element')
    attrs = elem.attrib
    return Lemma(
        attrs['writtenForm'],
        _get_literal(attrs['partOfSpeech'], POS_LIST),
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
        relations.append(_load_relation(elem, SenseRelation, SENSE_RELATIONS))
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
        adjposition=_get_optional_literal(attrs.get('adjposition'), ADJPOSITIONS),
        meta=_get_metadata(attrs),
    )


_R = TypeVar('_R', SynsetRelation, SenseRelation)


def _load_relation(elem, cls: Type[_R], choices: Container[str]) -> _R:
    attrs = elem.attrib
    return cls(
        attrs['target'],
        _get_literal
        (attrs['relType'], choices),
        meta=_get_metadata(attrs),
    )


def _load_example(elem) -> Example:
    attrs = elem.attrib
    return Example(
        elem.text,
        language=attrs.get('language'),
        meta=_get_metadata(attrs),
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
        meta=_get_metadata(attrs),
    )


def _load_syntactic_behaviour(elem) -> SyntacticBehaviour:
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
        relations.append(_load_relation(elem, SynsetRelation, SYNSET_RELATIONS))
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
        pos=_get_optional_literal(attrs['partOfSpeech'], POS_LIST),
        definitions=tuple(definitions),
        ili_definition=ili_definition,
        relations=tuple(relations),
        examples=tuple(examples),
        lexicalized=_get_bool(attrs.get('lexicalized', 'true')),
        meta=_get_metadata(attrs),
    )


def _load_definition(elem) -> Definition:
    attrs = elem.attrib
    return Definition(
        elem.text,
        language=attrs.get('language'),
        source_sense=attrs.get('sourceSense'),
        meta=_get_metadata(attrs),
    )


def _load_ilidefinition(elem) -> ILIDefinition:
    attrs = elem.attrib
    return ILIDefinition(
        elem.text,
        meta=_get_metadata(attrs),
    )


def _get_bool(value: str) -> bool:
    value = value.lower()
    if value not in ('true', 'false'):
        warnings.warn(f'value must be "true" or "false", not {value!r}', LMFWarning)
    return value == 'true'


def _get_optional_literal(value: Optional[str], choices: Container[str]) -> str:
    if value is None:
        return ''
    else:
        return _get_literal(value, choices)


def _get_literal(value: str, choices: Container[str]) -> str:
    if value is not None and value not in choices:
        warnings.warn(f'{value!r} is not one of {choices!r}', LMFWarning)
    return value


def _get_metadata(attrs: Dict) -> Optional[Metadata]:
    metas = [attrs.get(qname) for qname, _ in _dc_qname_pairs]
    metas.append(attrs.get('status'))
    metas.append(attrs.get('note'))
    if 'confidenceScore' in attrs:
        value = attrs['confidenceScore']
        try:
            value = float(value)
            assert 0 <= value <= 1
        except (ValueError, AssertionError):
            warnings.warn(f'confidenceScore not between 0 and 1: {value}', LMFWarning)
        metas.append(value)
    else:
        metas.append(None)
    if any(meta is not None for meta in metas):
        return Metadata(*metas)
    else:
        return None


def _assert_closed(event, elem, tag) -> None:
    if event != 'end' or elem.tag != tag:
        raise _unexpected(elem)


def _unexpected(elem) -> LMFError:
    return LMFError(f'unexpected element: {elem.tag}')
