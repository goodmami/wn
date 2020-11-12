
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import (
    TypeVar,
    Type,
    Container,
    List,
    Tuple,
    Dict,
    Set,
    NamedTuple,
    Optional,
)
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET  # for general XML parsing
import xml.parsers.expat  # for fast scanning of Lexicon versions

from wn._types import AnyPath
from wn._util import is_xml
from wn.constants import (
    SENSE_RELATIONS,
    SYNSET_RELATIONS,
    ADJPOSITIONS,
    PARTS_OF_SPEECH,
)


class LMFError(Exception):
    """Raised on invalid LMF-XML documents."""


class LMFWarning(Warning):
    """Issued on non-conforming LFM values."""


_XMLDECL = '<?xml version="1.0" encoding="UTF-8"?>'
_SCHEMAS = (
    'http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd',
)
_DOCTYPES = {
    f'<!DOCTYPE LexicalResource SYSTEM "{schema}">' for schema in _SCHEMAS
}

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
    contributor: Optional[str] = None
    coverage: Optional[str] = None
    creator: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    identifier: Optional[str] = None
    publisher: Optional[str] = None
    relation: Optional[str] = None
    rights: Optional[str] = None
    source: Optional[str] = None
    subject: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    confidence: Optional[float] = None


class _HasMeta:
    __slots__ = 'meta',

    def __init__(self, meta: Metadata = None):
        self.meta = meta


# These types model the WN-LMF DTD
# http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd

class Count(_HasMeta):
    __slots__ = 'value',

    def __init__(self, value: int, meta: Metadata = None):
        super().__init__(meta)
        self.value = value


class SyntacticBehaviour:
    __slots__ = 'frame', 'senses'

    def __init__(self, frame: str, senses: List[str] = None):
        self.frame = frame
        self.senses = senses or []


class SenseRelation(_HasMeta):
    __slots__ = 'target', 'type'

    def __init__(self, target: str, type: str, meta: Metadata = None):
        super().__init__(meta)
        self.target = target
        self.type = type


class SynsetRelation(_HasMeta):
    __slots__ = 'target', 'type'

    def __init__(self, target: str, type: str, meta: Metadata = None):
        super().__init__(meta)
        self.target = target
        self.type = type


class Example(_HasMeta):
    __slots__ = 'text', 'language'

    def __init__(self, text: str, language: str = '', meta: Metadata = None):
        super().__init__(meta)
        self.text = text
        self.language = language


class ILIDefinition(_HasMeta):
    __slots__ = 'text',

    def __init__(self, text: str, meta: Metadata = None):
        super().__init__(meta)
        self.text = text


class Definition(_HasMeta):
    __slots__ = 'text', 'language', 'source_sense'

    def __init__(
            self,
            text: str,
            language: str = '',
            source_sense: str = '',
            meta: Metadata = None):
        super().__init__(meta)
        self.text = text
        self.language = language
        self.source_sense = source_sense


class Synset(_HasMeta):
    __slots__ = ('id', 'ili', 'pos', 'definitions', 'ili_definition',
                 'relations', 'examples', 'lexicalized')

    def __init__(
            self,
            id: str,
            ili: str,
            pos: str,
            definitions: List[Definition] = None,
            ili_definition: ILIDefinition = None,
            relations: List[SynsetRelation] = None,
            examples: List[Example] = None,
            lexicalized: bool = True,
            meta: Metadata = None):
        super().__init__(meta)
        self.id = id
        self.ili = ili
        self.pos = pos
        self.definitions = definitions or []
        self.ili_definition = ili_definition
        self.relations = relations or []
        self.examples = examples or []
        self.lexicalized = lexicalized


class Sense(_HasMeta):
    __slots__ = ('id', 'synset', 'relations', 'examples', 'counts',
                 'lexicalized', 'adjposition')

    def __init__(
            self,
            id: str,
            synset: str,
            relations: List[SenseRelation] = None,
            examples: List[Example] = None,
            counts: List[Count] = None,
            lexicalized: bool = True,
            adjposition: str = '',
            meta: Metadata = None):
        super().__init__(meta)
        self.id = id
        self.synset = synset
        self.relations = relations or []
        self.examples = examples or []
        self.counts = counts or []
        self.lexicalized = lexicalized
        self.adjposition = adjposition


class Tag:
    __slots__ = 'text', 'category'

    def __init__(self, text: str, category: str):
        self.text = text
        self.category = category


class Form:
    __slots__ = 'form', 'script', 'tags'

    def __init__(self, form: str, script: str, tags: List[Tag] = None):
        self.form = form
        self.script = script
        self.tags = tags or []


class Lemma:
    __slots__ = 'form', 'pos', 'script', 'tags'

    def __init__(self, form: str, pos: str, script: str = '', tags: List[Tag] = None):
        self.form = form
        self.pos = pos
        self.script = script
        self.tags = tags or []


class LexicalEntry(_HasMeta):
    __slots__ = 'id', 'lemma', 'forms', 'senses'

    def __init__(
            self,
            id: str,
            lemma: Lemma,
            forms: List[Form] = None,
            senses: List[Sense] = None,
            meta: Metadata = None):
        super().__init__(meta)
        self.id = id
        self.lemma = lemma
        self.forms = forms or []
        self.senses = senses or []


class Lexicon(_HasMeta):
    __slots__ = ('id', 'label', 'language',
                 'email', 'license', 'version', 'url', 'citation',
                 'lexical_entries', 'synsets', 'syntactic_behaviours')

    def __init__(
            self,
            id: str,
            label: str,
            language: str,
            email: str,
            license: str,
            version: str,
            url: str = '',
            citation: str = '',
            lexical_entries: List[LexicalEntry] = None,
            synsets: List[Synset] = None,
            syntactic_behaviours: List[SyntacticBehaviour] = None,
            meta: Metadata = None):
        super().__init__(meta)
        self.id = id
        self.label = label
        self.language = language
        self.email = email
        self.license = license
        self.version = version
        self.url = url
        self.citation = citation
        self.lexical_entries = lexical_entries or []
        self.synsets = synsets or []
        self.syntactic_behaviours = syntactic_behaviours or []

    def entry_ids(self) -> Set[str]:
        return {entry.id for entry in self.lexical_entries}

    def sense_ids(self) -> Set[str]:
        return {sense.id for entry in self.lexical_entries for sense in entry.senses}

    def synset_ids(self) -> Set[str]:
        return {synset.id for synset in self.synsets}


LexicalResource = List[Lexicon]


def is_lmf(source: AnyPath) -> bool:
    """Return True if *source* is a WN-LMF XML file."""
    source = Path(source).expanduser()
    if not is_xml(source):
        return False
    with source.open() as fh:
        xmldecl = fh.readline().rstrip()
        doctype = fh.readline().rstrip()
        if not (xmldecl == _XMLDECL and doctype in _DOCTYPES):
            return False
    return True


def scan_lexicons(source: AnyPath) -> List[Dict]:
    """Scan *source* and return only the top-level lexicon info."""

    source = Path(source).expanduser()

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
    source = Path(source).expanduser()
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

    return lexicons


def _load_lexicon(local_root, events) -> Lexicon:
    attrs = local_root.attrib
    event, elem = next(events)

    syntactic_behaviours: List[SyntacticBehaviour] = []
    lexical_entries: List[LexicalEntry] = []
    while event == 'start' and elem.tag == 'LexicalEntry':
        entry, sbs = _load_lexical_entry(elem, events)
        lexical_entries.append(entry)
        syntactic_behaviours.extend(sbs)
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
        url=attrs.get('url'),
        citation=attrs.get('citation'),
        lexical_entries=lexical_entries,
        synsets=synsets,
        syntactic_behaviours=syntactic_behaviours,
        meta=_get_metadata(attrs),
    )


def _load_lexical_entry(
        local_root,
        events
) -> Tuple[LexicalEntry, List[SyntacticBehaviour]]:
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

    entry = LexicalEntry(
        attrs['id'],
        lemma,
        forms=forms,
        senses=senses,
        meta=_get_metadata(attrs),
    )

    return entry, syntactic_behaviours


def _load_lemma(events) -> Lemma:
    event, elem = next(events)
    if event != 'start' or elem.tag != 'Lemma':
        raise LMFError('expected a Lemma element')
    attrs = elem.attrib
    return Lemma(
        attrs['writtenForm'],
        _get_literal(attrs['partOfSpeech'], PARTS_OF_SPEECH),
        script=attrs.get('script'),
        tags=_load_tags_until(events, 'Lemma'))


def _load_form(local_root, events) -> Form:
    attrs = local_root.attrib
    return Form(
        attrs['writtenForm'],
        script=attrs.get('script'),
        tags=_load_tags_until(events, 'Form'))


def _load_tags_until(events, terminus) -> List[Tag]:
    event, elem = next(events)

    tags: List[Tag] = []
    while event == 'start' and elem.tag == 'Tag':
        event, elem = next(events)
        _assert_closed(event, elem, 'Tag')
        tags.append(Tag(elem.text, elem.attrib['category']))
        event, elem = next(events)

    _assert_closed(event, elem, terminus)

    return tags


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
        relations=relations,
        examples=examples,
        counts=counts,
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
        senses=attrs.get('senses', '').split(),
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
        pos=_get_optional_literal(attrs['partOfSpeech'], PARTS_OF_SPEECH),
        definitions=definitions,
        ili_definition=ili_definition,
        relations=relations,
        examples=examples,
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
