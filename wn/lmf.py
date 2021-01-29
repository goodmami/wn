
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
    TextIO,
    BinaryIO
)
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET  # for general XML parsing
import xml.parsers.expat  # for fast scanning of Lexicon versions
from xml.sax.saxutils import quoteattr

import wn
from wn._types import AnyPath
from wn._util import is_xml
from wn.constants import (
    SENSE_RELATIONS,
    SYNSET_RELATIONS,
    ADJPOSITIONS,
    PARTS_OF_SPEECH,
)


class LMFError(wn.Error):
    """Raised on invalid LMF-XML documents."""


class LMFWarning(Warning):
    """Issued on non-conforming LFM values."""


_XMLDECL = b'<?xml version="1.0" encoding="UTF-8"?>'
_DOCTYPE = '<!DOCTYPE LexicalResource SYSTEM "{schema}">'
_SCHEMAS = {
    '1.0': 'http://globalwordnet.github.io/schemas/WN-LMF-1.0.dtd',
    '1.1': 'http://globalwordnet.github.io/schemas/WN-LMF-1.1.dtd',
}
_DOCTYPES = {
    _DOCTYPE.format(schema=schema): version for version, schema in _SCHEMAS.items()
}

_DC_URIS = {
    '1.0': 'http://purl.org/dc/elements/1.1/',
    '1.1': 'http://globalwordnet.github.io/schemas/dc/',
}
_DC_ATTRS = [
    'contributor',
    'coverage',
    'creator',
    'date',
    'description',
    'format',
    'identifier',
    'publisher',
    'relation',
    'rights',
    'source',
    'subject',
    'title',
    'type',
]
# dublin-core metadata needs the namespace uri prefixed
_DC_QNAME_PAIRS = {
    version: [(f'{{{uri}}}{attr}', attr) for attr in _DC_ATTRS]
    for version, uri in _DC_URIS.items()
}


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
    """Return True if *source* is a WN-LMF file."""
    source = Path(source).expanduser()
    if not is_xml(source):
        return False
    with source.open(mode='rb') as fh:
        try:
            _read_header(fh)
        except LMFError:
            return False
    return True


def _read_header(fh: BinaryIO) -> str:
    xmldecl = fh.readline().rstrip().replace(b"'", b'"')
    doctype = fh.readline().rstrip().replace(b"'", b'"')

    if xmldecl != _XMLDECL:
        raise LMFError('invalid or missing XML declaration')

    # the XML declaration states that the file is UTF-8 (other
    # encodings are not allowed)
    doctype_decoded = doctype.decode('utf-8')
    if doctype_decoded not in _DOCTYPES:
        raise LMFError('invalid or missing DOCTYPE declaration')

    return _DOCTYPES[doctype_decoded]


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
        try:
            p.ParseFile(fh)
        except xml.parsers.expat.ExpatError as exc:
            raise LMFError('invalid or ill-formed WN-LMF file') from exc

    return infos


def load(source: AnyPath) -> LexicalResource:
    """Load wordnets encoded in the WN-LMF format.

    Args:
        source: path to a WN-LMF file
    """
    source = Path(source).expanduser()

    with source.open('rb') as fh:
        version = _read_header(fh)

    events = ET.iterparse(source, events=('start', 'end'))
    root = next(events)[1]
    event, elem = next(events)

    lexicons: List[Lexicon] = []
    while event == 'start' and elem.tag == 'Lexicon':
        lexicons.append(_load_lexicon(elem, events, version))
        root.clear()
        event, elem = next(events)

    _assert_closed(event, elem, 'LexicalResource')
    list(events)  # consume remaining events, if any

    return lexicons


def dump(
        lexicons: LexicalResource, destination: AnyPath, version: str = '1.0'
) -> None:
    """Write wordnets in the WN-LMF format.

    Args:
        lexicons: a list of :class:`Lexicon` objects
    """
    destination = Path(destination).expanduser()
    doctype = _DOCTYPE.format(schema=_SCHEMAS[version])
    dc_uri = _DC_URIS[version]
    with destination.open('wt', encoding='utf-8') as out:
        print(_XMLDECL.decode('utf-8'), file=out)
        print(doctype, file=out)
        print(f'<LexicalResource xmlns:dc="{dc_uri}">', file=out)
        for lexicon in lexicons:
            _dump_lexicon(lexicon, out, version)
        print('</LexicalResource>', file=out)


def _load_lexicon(local_root, events, version) -> Lexicon:
    attrs = local_root.attrib
    event, elem = next(events)

    syntactic_behaviours: List[SyntacticBehaviour] = []
    lexical_entries: List[LexicalEntry] = []
    while event == 'start' and elem.tag == 'LexicalEntry':
        entry, sbs = _load_lexical_entry(elem, events, version)
        lexical_entries.append(entry)
        syntactic_behaviours.extend(sbs)
        local_root.clear()
        event, elem = next(events)

    synsets: List[Synset] = []
    while event == 'start' and elem.tag == 'Synset':
        synsets.append(_load_synset(elem, events, version))
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
        meta=_get_metadata(attrs, version),
    )


def _load_lexical_entry(
        local_root,
        events,
        version,
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
        senses.append(_load_sense(elem, events, version))
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
        meta=_get_metadata(attrs, version),
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


def _load_sense(local_root, events, version) -> Sense:
    attrs = local_root.attrib
    event, elem = next(events)

    relations: List[SenseRelation] = []
    while event == 'start' and elem.tag == 'SenseRelation':
        event, elem = next(events)
        _assert_closed(event, elem, 'SenseRelation')
        relations.append(
            _load_relation(elem, SenseRelation, SENSE_RELATIONS, version)
        )
        event, elem = next(events)

    examples: List[Example] = []
    while event == 'start' and elem.tag == 'Example':
        event, elem = next(events)
        _assert_closed(event, elem, 'Example')
        examples.append(_load_example(elem, version))
        event, elem = next(events)

    counts: List[Count] = []
    while event == 'start' and elem.tag == 'Count':
        event, elem = next(events)
        _assert_closed(event, elem, 'Count')
        counts.append(_load_count(elem, version))
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
        meta=_get_metadata(attrs, version),
    )


_R = TypeVar('_R', SynsetRelation, SenseRelation)


def _load_relation(elem, cls: Type[_R], choices: Container[str], version: str) -> _R:
    attrs = elem.attrib
    return cls(
        attrs['target'],
        _get_literal
        (attrs['relType'], choices),
        meta=_get_metadata(attrs, version),
    )


def _load_example(elem, version) -> Example:
    attrs = elem.attrib
    return Example(
        elem.text,
        language=attrs.get('language'),
        meta=_get_metadata(attrs, version),
    )


def _load_count(elem, version) -> Count:
    attrs = elem.attrib
    value: int = -1
    try:
        value = int(elem.text)
    except ValueError:
        warnings.warn(f'count must be an integer: {elem.text}', LMFWarning)
    return Count(
        value,
        meta=_get_metadata(attrs, version),
    )


def _load_syntactic_behaviour(elem) -> SyntacticBehaviour:
    attrs = elem.attrib
    return SyntacticBehaviour(
        attrs['subcategorizationFrame'],
        senses=attrs.get('senses', '').split(),
    )


def _load_synset(local_root, events, version) -> Synset:
    attrs = local_root.attrib
    event, elem = next(events)

    definitions: List[Definition] = []
    while event == 'start' and elem.tag == 'Definition':
        event, elem = next(events)
        _assert_closed(event, elem, 'Definition')
        definitions.append(_load_definition(elem, version))
        event, elem = next(events)

    ili_definition = None
    if event == 'start' and elem.tag == 'ILIDefinition':
        event, elem = next(events)
        _assert_closed(event, elem, 'ILIDefinition')
        ili_definition = _load_ilidefinition(elem, version)
        event, elem = next(events)

    relations: List[SynsetRelation] = []
    while event == 'start' and elem.tag == 'SynsetRelation':
        event, elem = next(events)
        _assert_closed(event, elem, 'SynsetRelation')
        relations.append(
            _load_relation(elem, SynsetRelation, SYNSET_RELATIONS, version)
        )
        event, elem = next(events)

    examples: List[Example] = []
    while event == 'start' and elem.tag == 'Example':
        event, elem = next(events)
        _assert_closed(event, elem, 'Example')
        examples.append(_load_example(elem, version))
        event, elem = next(events)

    _assert_closed(event, elem, 'Synset')

    return Synset(
        attrs['id'],
        attrs['ili'],
        pos=_get_optional_literal(attrs.get('partOfSpeech'), PARTS_OF_SPEECH),
        definitions=definitions,
        ili_definition=ili_definition,
        relations=relations,
        examples=examples,
        lexicalized=_get_bool(attrs.get('lexicalized', 'true')),
        meta=_get_metadata(attrs, version),
    )


def _load_definition(elem, version) -> Definition:
    attrs = elem.attrib
    return Definition(
        elem.text,
        language=attrs.get('language'),
        source_sense=attrs.get('sourceSense'),
        meta=_get_metadata(attrs, version),
    )


def _load_ilidefinition(elem, version) -> ILIDefinition:
    attrs = elem.attrib
    return ILIDefinition(
        elem.text,
        meta=_get_metadata(attrs, version),
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


def _get_metadata(attrs: Dict, version: str) -> Optional[Metadata]:
    metas = [attrs.get(qname) for qname, _ in _DC_QNAME_PAIRS[version]]
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


def _dump_lexicon(lexicon: Lexicon, out: TextIO, version: str) -> None:
    attrib = {
        'id': lexicon.id,
        'label': lexicon.label,
        'language': lexicon.language,
        'email': lexicon.email,
        'license': lexicon.license,
        'version': lexicon.version,
    }
    if lexicon.url:
        attrib['url'] = lexicon.url
    if lexicon.citation:
        attrib['citation'] = lexicon.citation
    attrib.update(_meta_dict(lexicon.meta))
    attrdelim = '\n' + (' ' * 11)
    attrs = attrdelim.join(
        f'{attr}={quoteattr(str(val))}' for attr, val in attrib.items()
    )
    print(f'  <Lexicon {attrs}>', file=out)

    for entry in lexicon.lexical_entries:
        # TODO: 1.0 SyntacticBehaviour
        _dump_lexical_entry(entry, out, version)

    for synset in lexicon.synsets:
        _dump_synset(synset, out, version)

    # TODO: 1.1 SyntacticBehaviour

    print('  </Lexicon>', file=out)


def _dump_lexical_entry(
        entry: LexicalEntry, out: TextIO, version: str
) -> None:
    attrib = {'id': entry.id}
    attrib.update(_meta_dict(entry.meta))
    elem = ET.Element('LexicalEntry', attrib=attrib)
    elem.append(_build_lemma(entry.lemma))
    elem.extend(_build_form(form) for form in entry.forms)
    elem.extend(_build_sense(sense) for sense in entry.senses)
    # TODO: 1.0 SyntacticBehaviour
    print(_tostring(elem, 2), file=out)


def _build_lemma(lemma: Lemma) -> ET.Element:
    attrib = {'writtenForm': lemma.form}
    if lemma.script:
        attrib['script'] = lemma.script
    attrib['partOfSpeech'] = lemma.pos
    elem = ET.Element('Lemma', attrib=attrib)
    # TODO: Pronunciation
    for tag in lemma.tags:
        elem.append(_build_tag(tag))
    return elem


def _build_form(form: Form) -> ET.Element:
    attrib = {'writtenForm': form.form}
    if form.script:
        attrib['script'] = form.script
    elem = ET.Element('Form', attrib=attrib)
    # TODO: Pronunciation
    for tag in form.tags:
        elem.append(_build_tag(tag))
    return elem


def _build_tag(tag: Tag) -> ET.Element:
    elem = ET.Element('Tag', category=tag.category)
    elem.text = tag.text
    return elem


def _build_sense(sense: Sense) -> ET.Element:
    attrib = {'id': sense.id, 'synset': sense.synset}
    attrib.update(_meta_dict(sense.meta))
    if not sense.lexicalized:
        attrib['lexicalized'] = 'false'
    if sense.adjposition:
        attrib['adjposition'] = sense.adjposition
    # TODO: subcat
    elem = ET.Element('Sense', attrib=attrib)
    elem.extend(_build_sense_relation(rel) for rel in sense.relations)
    elem.extend(_build_example(ex) for ex in sense.examples)
    elem.extend(_build_count(cnt) for cnt in sense.counts)
    return elem


def _build_sense_relation(relation: SenseRelation) -> ET.Element:
    attrib = {'target': relation.target, 'relType': relation.type}
    attrib.update(_meta_dict(relation.meta))
    return ET.Element('SenseRelation', attrib=attrib)


def _build_example(example: Example) -> ET.Element:
    elem = ET.Element('Example')
    elem.text = example.text
    if example.language:
        elem.set('language', example.language)
    return elem


def _build_count(count: Count) -> ET.Element:
    elem = ET.Element('Count', attrib=_meta_dict(count.meta))
    elem.text = str(count.value)
    return elem


def _dump_synset(synset: Synset, out: TextIO, version: str) -> None:
    attrib = {'id': synset.id, 'ili': synset.ili}
    if synset.pos:
        attrib['partOfSpeech'] = synset.pos
    attrib.update(_meta_dict(synset.meta))
    if not synset.lexicalized:
        attrib['lexicalized'] = 'false'
    elem = ET.Element('Synset', attrib=attrib)
    elem.extend(_build_definition(defn) for defn in synset.definitions)
    if synset.ili_definition:
        elem.append(_build_ili_definition(synset.ili_definition))
    elem.extend(_build_synset_relation(rel) for rel in synset.relations)
    elem.extend(_build_example(ex) for ex in synset.examples)
    print(_tostring(elem, 2), file=out)


def _build_definition(definition: Definition) -> ET.Element:
    attrib = {}
    if definition.language:
        attrib['language'] = definition.language
    if definition.source_sense:
        attrib['sourceSense'] = definition.source_sense
    attrib.update(_meta_dict(definition.meta))
    elem = ET.Element('Definition', attrib=attrib)
    elem.text = definition.text
    return elem


def _build_ili_definition(ili_definition: ILIDefinition) -> ET.Element:
    elem = ET.Element('ILIDefinition', attrib=_meta_dict(ili_definition.meta))
    elem.text = ili_definition.text
    return elem


def _build_synset_relation(relation: SynsetRelation) -> ET.Element:
    attrib = {'target': relation.target, 'relType': relation.type}
    attrib.update(_meta_dict(relation.meta))
    return ET.Element('SynsetRelation', attrib=attrib)


def _dump_syntactic_behaviour(
        syntactic_behaviour: SyntacticBehaviour, out: TextIO, version: str
) -> None:
    elem = _build_syntactic_behaviour(syntactic_behaviour)
    print('    ' + _tostring(elem, 2), file=out)


def _build_syntactic_behaviour(syntactic_behaviour: SyntacticBehaviour) -> ET.Element:
    elem = ET.Element('SyntacticBehaviour')
    # if getattr(syntactic_behaviour, 'id', None):
    #     elem.set('id', syntactic_behaviour.id)
    elem.set('subcategorizationFrame', syntactic_behaviour.frame)
    if syntactic_behaviour.senses:
        elem.set('senses', ' '.join(syntactic_behaviour.senses))
    return elem


def _tostring(
        elem: ET.Element, level: int, short_empty_elements: bool = True
) -> str:
    _indent(elem, level)
    return ('  ' * level) + ET.tostring(
        elem,
        encoding='unicode',
        short_empty_elements=short_empty_elements
    )


def _indent(elem: ET.Element, level: int) -> None:
    self_indent = '\n' + '  ' * level
    child_indent = self_indent + '  '
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for child in elem[:-1]:
            _indent(child, level + 1)
            child.tail = child_indent
        _indent(elem[-1], level + 1)
        elem[-1].tail = self_indent


def _meta_dict(m: Optional[Metadata]) -> Dict:
    if m:
        d = {f'dc:{key}': str(val)
             for key, val in zip(m._fields, m)
             if val is not None}
    else:
        d = {}
    return d
