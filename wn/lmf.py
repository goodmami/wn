
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import (
    Type,
    Container,
    List,
    Tuple,
    Dict,
    NamedTuple,
    Optional,
    TextIO,
    BinaryIO,
    Iterator,
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
    SENSE_SYNSET_RELATIONS,
    SYNSET_RELATIONS,
    ADJPOSITIONS,
    PARTS_OF_SPEECH,
    LEXICOGRAPHER_FILES,
)
from wn.util import ProgressHandler, ProgressBar


LEXICON_INFO_ATTRIBUTES = {
    'LexicalEntry', 'ExternalLexicalEntry',
    'Lemma', 'Form', 'Pronunciation', 'Tag',
    'Sense', 'ExternalSense',
    'SenseRelation', 'Example', 'Count',
    'SyntacticBehaviour',
    'Synset', 'ExternalSynset',
    'Definition',  # 'ILIDefinition',
    'SynsetRelation'
}


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


class XMLEventIterator:
    """etree.iterparse() event iterator with lookahead"""
    def __init__(
        self,
        iterator: Iterator[Tuple[str, ET.Element]],
        progress: ProgressHandler
    ):
        self.iterator = iterator
        self.progress = progress
        self._next = next(iterator, (None, None))

    def __iter__(self):
        return self

    def __next__(self):
        _next = self._next
        event, elem = _next
        if _next == (None, None):
            self.progress.set(status="Complete")
            raise StopIteration
        self._next = next(self.iterator, (None, None))
        return _next

    def starts(self, *tags: str) -> bool:
        event, elem = self._next
        if elem is None:
            return False
        return event == 'start' and elem.tag in tags

    def start(self, *tags: str) -> ET.Element:
        event, elem = next(self)
        if event != 'start':
            raise LMFError(f'expected <{"|".join(tags)}>, got </{elem.tag}>')
        if elem.tag not in tags:
            raise LMFError(f'expected <{"|".join(tags)}>, got <{elem.tag}>')
        return elem

    def end(self, *tags: str) -> ET.Element:
        event, elem = next(self)
        if event != 'end':
            raise LMFError(f'expected </{"|".join(tags)}>, got <{elem.tag}>')
        if elem.tag not in tags:
            raise LMFError(f'expected </{"|".join(tags)}>, got </{elem.tag}>')
        self.progress.update()
        return elem


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
    __slots__ = 'id', 'frame', 'senses'

    def __init__(self, id: str, frame: str, senses: List[str] = None):
        self.id = id
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
                 'relations', 'examples', 'lexicalized', 'members',
                 'lexfile', 'external')

    def __init__(
        self,
        id: str,
        ili: str = None,
        pos: str = None,
        definitions: List[Definition] = None,
        ili_definition: ILIDefinition = None,
        relations: List[SynsetRelation] = None,
        examples: List[Example] = None,
        lexicalized: bool = True,
        members: List[str] = None,
        lexfile: str = None,
        meta: Metadata = None
    ):
        super().__init__(meta)
        self.id = id
        self.ili = ili
        self.pos = pos
        self.definitions = definitions or []
        self.ili_definition = ili_definition
        self.relations = relations or []
        self.examples = examples or []
        self.lexicalized = lexicalized
        self.members = members or []
        self.lexfile = lexfile
        self.external = False

    @classmethod
    def as_external(
        cls,
        id: str,
        definitions: List[Definition] = None,
        relations: List[SynsetRelation] = None,
        examples: List[Example] = None
    ):
        obj = cls(
            id,
            '',
            '',
            definitions=definitions,
            relations=relations,
            examples=examples
        )
        obj.external = True
        return obj


class Sense(_HasMeta):
    __slots__ = ('id', 'synset', 'relations', 'examples', 'counts',
                 'lexicalized', 'adjposition', 'external')

    def __init__(
        self,
        id: str,
        synset: str,
        relations: List[SenseRelation] = None,
        examples: List[Example] = None,
        counts: List[Count] = None,
        lexicalized: bool = True,
        adjposition: str = '',
        meta: Metadata = None
    ):
        super().__init__(meta)
        self.id = id
        self.synset = synset
        self.relations = relations or []
        self.examples = examples or []
        self.counts = counts or []
        self.lexicalized = lexicalized
        self.adjposition = adjposition
        self.external = False

    @classmethod
    def as_external(
        cls,
        id: str,
        relations: List[SenseRelation] = None,
        examples: List[Example] = None,
        counts: List[Count] = None
    ):
        obj = cls(
            id,
            '',
            relations=relations,
            examples=examples,
            counts=counts
        )
        obj.external = True
        return obj


class Pronunciation:
    __slots__ = 'value', 'variety', 'notation', 'phonemic', 'audio'

    def __init__(
        self,
        value: str,
        variety: str = None,
        notation: str = None,
        phonemic: bool = True,
        audio: str = None,
    ):
        self.value = value
        self.variety = variety
        self.notation = notation
        self.phonemic = phonemic
        self.audio = audio


class Tag:
    __slots__ = 'text', 'category'

    def __init__(self, text: str, category: str):
        self.text = text
        self.category = category


class Form:
    __slots__ = 'id', 'form', 'script', 'pronunciations', 'tags', 'external'

    def __init__(
        self,
        id: Optional[str],
        form: str,
        script: str,
        pronunciations: List[Pronunciation] = None,
        tags: List[Tag] = None,
    ):
        self.id = id
        self.form = form
        self.script = script
        self.pronunciations = pronunciations or []
        self.tags = tags or []
        self.external = False

    @classmethod
    def as_external(
        cls,
        id: str,
        pronunciations: List[Pronunciation] = None,
        tags: List[Tag] = None,
    ):
        obj = cls(
            id,
            '',
            '',
            pronunciations=pronunciations,
            tags=tags,
        )
        obj.external = True
        return obj


class Lemma:
    __slots__ = 'form', 'pos', 'script', 'pronunciations', 'tags', 'external'

    def __init__(
        self,
        form: str,
        pos: str,
        script: str = '',
        pronunciations: List[Pronunciation] = None,
        tags: List[Tag] = None,
    ):
        self.form = form
        self.pos = pos
        self.script = script
        self.pronunciations = pronunciations or []
        self.tags = tags or []
        self.external = False

    @classmethod
    def as_external(
        cls,
        pronunciations: List[Pronunciation] = None,
        tags: List[Tag] = None,
    ):
        obj = cls(
            '',
            '',
            pronunciations=pronunciations,
            tags=tags,
        )
        obj.external = True
        return obj


class LexicalEntry(_HasMeta):
    __slots__ = 'id', 'lemma', 'forms', 'senses', 'external'

    def __init__(
        self,
        id: str,
        lemma: Optional[Lemma],
        forms: List[Form] = None,
        senses: List[Sense] = None,
        meta: Metadata = None
    ):
        super().__init__(meta)
        self.id = id
        self.lemma = lemma
        self.forms = forms or []
        self.senses = senses or []
        self.external = False

    @classmethod
    def as_external(
        cls,
        id: str,
        lemma: Lemma = None,
        forms: List[Form] = None,
        senses: List[Sense] = None,
    ):
        obj = cls(
            id,
            lemma,
            forms=forms,
            senses=senses
        )
        obj.external = True
        return obj


class Lexicon(_HasMeta):
    __slots__ = ('id', 'label', 'language',
                 'email', 'license', 'version', 'url', 'citation', 'logo',
                 'lexical_entries', 'synsets', 'syntactic_behaviours',
                 'extends', 'requires')

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
            logo: str = '',
            lexical_entries: List[LexicalEntry] = None,
            synsets: List[Synset] = None,
            syntactic_behaviours: List[SyntacticBehaviour] = None,
            extends: Dict[str, str] = None,
            requires: List[Dict[str, str]] = None,
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
        self.logo = logo
        self.lexical_entries = lexical_entries or []
        self.synsets = synsets or []
        self.syntactic_behaviours = syntactic_behaviours or []
        self.extends = extends
        self.requires = requires or []


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

    # this is implemented with expat as it's much faster than etree for
    # this task
    infos = []

    def start(name, attrs):
        if name in ('Lexicon', 'LexiconExtension'):
            attrs['counts'] = {}
            infos.append(attrs)
        elif name == 'Extends':
            infos[-1]['extends'] = attrs['id'], attrs['version']
        elif infos:
            counts = infos[-1]['counts']
            if name in counts:
                counts[name] += 1
            else:
                counts[name] = 1

    p = xml.parsers.expat.ParserCreate()
    p.StartElementHandler = start
    with open(source, 'rb') as fh:
        try:
            p.ParseFile(fh)
        except xml.parsers.expat.ExpatError as exc:
            raise LMFError('invalid or ill-formed WN-LMF file') from exc

    return infos


def load(
    source: AnyPath,
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar
) -> LexicalResource:
    """Load wordnets encoded in the WN-LMF format.

    Args:
        source: path to a WN-LMF file
    """
    if progress_handler is None:
        progress_handler = ProgressHandler

    source = Path(source).expanduser()

    with source.open('rb') as fh:
        version = _read_header(fh)
        # _read_header() only reads the first 2 lines
        remainder = fh.read()
        total_elements = remainder.count(b'</') + remainder.count(b'/>')

    progress = progress_handler(
        message='Read', total=total_elements, refresh_interval=10000
    )
    events = XMLEventIterator(
        ET.iterparse(source, events=('start', 'end')),
        progress
    )
    root = events.start('LexicalResource')

    lexicons: List[Lexicon] = []
    while events.starts('Lexicon', 'LexiconExtension'):
        lexicons.append(_load_lexicon(events, version))
        root.clear()

    events.end(root.tag)
    list(events)  # consume remaining events, if any

    return lexicons


def _load_lexicon(events, version) -> Lexicon:
    extends: Optional[Dict[str, str]] = None
    requires: List[Dict[str, str]] = []

    if version == '1.0':
        lex_root = events.start('Lexicon')
        extension = False
    else:
        lex_root = events.start('Lexicon', 'LexiconExtension')
        extension = lex_root.tag == 'LexiconExtension'
        extends = _load_dependency(events, 'Extends') if extension else None
        while events.starts('Requires'):
            requires.append(_load_dependency(events, 'Requires'))

    attrs = lex_root.attrib
    events.progress.set(message=f'Read {attrs["id"]}:{attrs["version"]}')

    events.progress.set(status='Lexical Entries')
    entries, frames, sbmap = _load_lexical_entries(
        events, extension, version, lex_root
    )
    events.progress.set(status='Synsets')
    synsets = _load_synsets(
        events, extension, version, lex_root
    )
    if version != '1.0':
        frames.extend(_load_syntactic_behaviours(events, version))
        for sb in frames:
            sb.senses.extend(sbmap.get(sb.id, []))

    lex = Lexicon(
        attrs['id'],
        attrs['label'],
        attrs['language'],
        attrs['email'],
        attrs['license'],
        attrs['version'],
        url=attrs.get('url'),
        citation=attrs.get('citation'),
        logo=attrs.get('logo'),
        lexical_entries=entries,
        synsets=synsets,
        syntactic_behaviours=frames,
        extends=extends,
        requires=requires,
        meta=_get_metadata(attrs, version),
    )
    events.end(lex_root.tag)

    return lex


def _load_dependency(events, tag) -> Dict[str, str]:
    events.start(tag)
    elem = events.end(tag)
    return {'id': elem.attrib['id'],
            'version': elem.attrib['version'],
            'url': elem.attrib.get('url')}


def _load_lexical_entries(
    events: XMLEventIterator,
    extension: bool,
    version: str,
    lex_root: ET.Element,
) -> Tuple[List[LexicalEntry], List[SyntacticBehaviour], Dict[str, List[str]]]:
    entries: List[LexicalEntry] = []
    syntactic_behaviours: List[SyntacticBehaviour] = []
    sbmap: Dict[str, List[str]] = {}
    while True:
        if events.starts('LexicalEntry'):
            attrs = events.start('LexicalEntry').attrib
            entry = LexicalEntry(
                attrs['id'],
                _load_lemma(events, False),
                forms=_load_forms(events, False),
                senses=_load_senses(events, sbmap, False, version),
                meta=_get_metadata(attrs, version),
            )
            syntactic_behaviours.extend(_load_syntactic_behaviours(events, version))
            events.end('LexicalEntry')
        elif extension and events.starts('ExternalLexicalEntry'):
            attrs = events.start('ExternalLexicalEntry').attrib
            entry = LexicalEntry.as_external(
                attrs['id'],
                lemma=_load_lemma(events, True),
                forms=_load_forms(events, True),
                senses=_load_senses(events, sbmap, True, version)
            )
            syntactic_behaviours.extend(_load_syntactic_behaviours(events, version))
            events.end('ExternalLexicalEntry')
        else:
            break
        entries.append(entry)
        lex_root.clear()

    return entries, syntactic_behaviours, sbmap


def _load_lemma(events, external) -> Optional[Lemma]:
    lemma: Optional[Lemma] = None
    if external and events.starts('ExternalLemma'):
        next(events)
        lemma = Lemma.as_external(
            pronunciations=_load_pronunciations(events),
            tags=_load_tags(events)
        )
        events.end('ExternalLemma')
    elif not external or events.starts('Lemma'):
        attrs = events.start('Lemma').attrib
        lemma = Lemma(
            attrs['writtenForm'],
            _get_literal(attrs['partOfSpeech'], PARTS_OF_SPEECH),
            script=attrs.get('script'),
            pronunciations=_load_pronunciations(events),
            tags=_load_tags(events)
        )
        events.end('Lemma')
    return lemma


def _load_forms(events, external) -> List[Form]:
    forms: List[Form] = []
    while True:
        if events.starts('Form'):
            attrs = next(events)[1].attrib
            forms.append(
                Form(attrs.get('id'),
                     attrs['writtenForm'],
                     script=attrs.get('script'),
                     pronunciations=_load_pronunciations(events),
                     tags=_load_tags(events))
            )
            events.end('Form')
        elif external and events.starts('ExternalForm'):
            attrs = next(events)[1].attrib
            forms.append(
                Form.as_external(
                    attrs['id'],
                    pronunciations=_load_pronunciations(events),
                    tags=_load_tags(events)
                )
            )
            events.end('ExternalForm')
        else:
            break
    return forms


def _load_pronunciations(events) -> List[Pronunciation]:
    pronunciations: List[Pronunciation] = []
    while events.starts('Pronunciation'):
        next(events)
        elem = events.end('Pronunciation')
        attrs = elem.attrib
        pronunciations.append(
            Pronunciation(
                elem.text,
                variety=attrs.get('variety'),
                notation=attrs.get('notation'),
                phonemic=_get_bool(attrs.get('phonemic', 'true')),
                audio=attrs.get('audio'),
            )
        )
    return pronunciations


def _load_tags(events) -> List[Tag]:
    tags: List[Tag] = []
    while events.starts('Tag'):
        next(events)
        elem = events.end('Tag')
        tags.append(Tag(elem.text, elem.attrib['category']))
    return tags


def _load_senses(events, sbmap, external, version) -> List[Sense]:
    senses: List[Sense] = []
    while True:
        if events.starts('Sense'):
            attrs = events.start('Sense').attrib
            sense = Sense(
                attrs['id'],
                attrs['synset'],
                relations=_load_sense_relations(events, version),
                examples=_load_examples(events, version),
                counts=_load_counts(events, version),
                lexicalized=_get_bool(attrs.get('lexicalized', 'true')),
                adjposition=_get_literal(attrs.get('adjposition'), ADJPOSITIONS),
                meta=_get_metadata(attrs, version),
            )
            for sbid in attrs.get('subcat', '').split():
                sbmap.setdefault(sbid, []).append(attrs['id'])
            events.end('Sense')
        elif external and events.starts('ExternalSense'):
            attrs = events.start('ExternalSense').attrib
            sense = Sense.as_external(
                attrs['id'],
                relations=_load_sense_relations(events, version),
                examples=_load_examples(events, version),
                counts=_load_counts(events, version),
            )
            events.end('ExternalSense')
        else:
            break
        senses.append(sense)
    return senses


def _load_sense_relations(events, version) -> List[SenseRelation]:
    relations: List[SenseRelation] = []
    while events.starts('SenseRelation'):
        next(events)
        elem = events.end('SenseRelation')
        attrs = elem.attrib
        reltype = attrs['relType']
        if not (reltype in SENSE_RELATIONS or reltype in SENSE_SYNSET_RELATIONS):
            raise LMFError(f'invalid sense relation: {reltype}')
        relations.append(
            SenseRelation(
                attrs['target'],
                reltype,
                meta=_get_metadata(attrs, version)
            )
        )
    return relations


def _load_examples(events, version) -> List[Example]:
    examples: List[Example] = []
    while events.starts('Example'):
        next(events)
        elem = events.end('Example')
        attrs = elem.attrib
        examples.append(
            Example(
                elem.text,
                language=attrs.get('language'),
                meta=_get_metadata(attrs, version),
            )
        )
    return examples


def _load_counts(events, version) -> List[Count]:
    counts: List[Count] = []
    while events.starts('Count'):
        next(events)
        elem = events.end('Count')
        attrs = elem.attrib
        value: int = -1
        try:
            value = int(elem.text)
        except ValueError:
            warnings.warn(f'count must be an integer: {elem.text}', LMFWarning)

        counts.append(Count(value, meta=_get_metadata(attrs, version)))

    return counts


def _load_syntactic_behaviours(events, version) -> List[SyntacticBehaviour]:
    syntactic_behaviours: List[SyntacticBehaviour] = []
    while events.starts('SyntacticBehaviour'):
        next(events)
        attrs = events.end('SyntacticBehaviour').attrib
        syntactic_behaviours.append(
            SyntacticBehaviour(
                attrs.get('id'),
                attrs['subcategorizationFrame'],
                senses=attrs.get('senses', '').split(),
            )
        )
    return syntactic_behaviours


def _load_synsets(
    events: XMLEventIterator,
    extension: bool,
    version: str,
    lex_root: ET.Element,
) -> List[Synset]:
    synsets: List[Synset] = []
    while True:
        if events.starts('Synset'):
            attrs = events.start('Synset').attrib
            synset = Synset(
                attrs['id'],
                attrs['ili'],
                pos=_get_literal(attrs.get('partOfSpeech'), PARTS_OF_SPEECH),
                definitions=_load_definitions(events, version),
                ili_definition=_load_ilidefinition(events, version),
                relations=_load_synset_relations(events, version),
                examples=_load_examples(events, version),
                lexicalized=_get_bool(attrs.get('lexicalized', 'true')),
                members=attrs.get('members', '').split(),
                lexfile=_get_literal(attrs.get('lexfile'), LEXICOGRAPHER_FILES),
                meta=_get_metadata(attrs, version),
            )
            events.end('Synset')
        elif extension and events.starts('ExternalSynset'):
            attrs = events.start('ExternalSynset').attrib
            synset = Synset.as_external(
                attrs['id'],
                definitions=_load_definitions(events, version),
                relations=_load_synset_relations(events, version),
                examples=_load_examples(events, version),
            )
            events.end('ExternalSynset')
        else:
            break
        synsets.append(synset)
        lex_root.clear()

    return synsets


def _load_definitions(events, version) -> List[Definition]:
    definitions: List[Definition] = []
    while events.starts('Definition'):
        next(events)
        elem = events.end('Definition')
        attrs = elem.attrib
        definitions.append(
            Definition(
                elem.text,
                language=attrs.get('language'),
                source_sense=attrs.get('sourceSense'),
                meta=_get_metadata(attrs, version),
            )
        )
    return definitions


def _load_ilidefinition(events, version) -> Optional[ILIDefinition]:
    ili_definition: Optional[ILIDefinition] = None
    if events.starts('ILIDefinition'):
        next(events)
        elem = events.end('ILIDefinition')
        ili_definition = ILIDefinition(
            elem.text,
            meta=_get_metadata(elem.attrib, version),
        )
    return ili_definition


def _load_synset_relations(events, version: str) -> List[SynsetRelation]:
    relations: List[SynsetRelation] = []
    while events.starts('SynsetRelation'):
        next(events)
        elem = events.end('SynsetRelation')
        attrs = elem.attrib
        reltype = attrs['relType']
        if reltype not in SYNSET_RELATIONS:
            raise LMFError(f'invalid synset relation: {reltype}')
        relations.append(
            SynsetRelation(
                attrs['target'],
                reltype,
                meta=_get_metadata(attrs, version),
            )
        )
    return relations


def _get_bool(value: str) -> bool:
    return _get_literal(value.lower(), ('true', 'false')) == 'true'


def _get_literal(value: Optional[str], choices: Container[str]) -> str:
    if value is not None and value not in choices:
        warnings.warn(f'{value!r} is not one of {choices!r}', LMFWarning)
    return value or ''


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


def dump(
        lexicons: LexicalResource, destination: AnyPath, version: str = '1.0'
) -> None:
    """Write wordnets in the WN-LMF format.

    Args:
        lexicons: a list of :class:`Lexicon` objects
    """
    if version not in _SCHEMAS:
        raise LMFError(f'invalid version: {version}')
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


def _dump_lexicon(lexicon: Lexicon, out: TextIO, version: str) -> None:
    lexicontype = 'LexiconExtension' if lexicon.extends else 'Lexicon'
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
    if version != '1.0' and lexicon.logo:
        attrib['logo'] = lexicon.logo
    attrib.update(_meta_dict(lexicon.meta))
    attrdelim = '\n' + (' ' * len(f'  <{lexicontype} '))
    attrs = attrdelim.join(
        f'{attr}={quoteattr(str(val))}' for attr, val in attrib.items()
    )
    print(f'  <{lexicontype} {attrs}>', file=out)

    if version != '1.0':
        if lexicontype == 'LexiconExtension':
            assert lexicon.extends is not None
            _dump_dependency(lexicon.extends, 'Extends', out)
        for req in lexicon.requires:
            _dump_dependency(req, 'Requires', out)
    sbmap: Dict[str, List[SyntacticBehaviour]] = {}
    for sb in lexicon.syntactic_behaviours:
        for sense_id in sb.senses:
            sbmap.setdefault(sense_id, []).append(sb)

    for entry in lexicon.lexical_entries:
        _dump_lexical_entry(entry, out, sbmap, version)

    for synset in lexicon.synsets:
        _dump_synset(synset, out, version)

    if version != '1.0':
        for sb in lexicon.syntactic_behaviours:
            _dump_syntactic_behaviour(sb, out, version)

    print(f'  </{lexicontype}>', file=out)


def _dump_dependency(
    dep: Dict[str, str], deptype: str, out: TextIO
) -> None:
    attrib = {'id': dep['id'], 'version': dep['version']}
    if dep.get('url'):
        attrib['url'] = dep['url']
    elem = ET.Element(deptype, attrib=attrib)
    print(_tostring(elem, 2), file=out)


def _dump_lexical_entry(
    entry: LexicalEntry,
    out: TextIO,
    sbmap: Dict[str, List[SyntacticBehaviour]],
    version: str,
) -> None:
    attrib = {'id': entry.id}
    if entry.external:
        elem = ET.Element('ExternalLexicalEntry', attrib=attrib)
    else:
        attrib.update(_meta_dict(entry.meta))
        elem = ET.Element('LexicalEntry', attrib=attrib)
        assert entry.lemma is not None
    if entry.lemma:
        elem.append(_build_lemma(entry.lemma, version))
    elem.extend(_build_form(form, version) for form in entry.forms)
    elem.extend(_build_sense(sense, sbmap, version) for sense in entry.senses)
    if version == '1.0':
        senses = set(sense.id for sense in entry.senses)
        for sense_id in senses:
            for sb in sbmap.get(sense_id, []):
                elem.append(
                    _build_syntactic_behaviour_1_0(
                        sb.frame, sorted(senses.intersection(sb.senses))
                    )
                )
    print(_tostring(elem, 2), file=out)


def _build_syntactic_behaviour_1_0(frame: str, senses: List[str]) -> ET.Element:
    return ET.Element(
        'SyntacticBehaviour',
        attrib={'subcategorizationFrame': frame, 'senses': ' '.join(senses)}
    )


def _build_lemma(lemma: Lemma, version: str) -> ET.Element:
    if lemma.external:
        elem = ET.Element('ExternalLemma')
    else:
        attrib = {'writtenForm': lemma.form}
        if lemma.script:
            attrib['script'] = lemma.script
        attrib['partOfSpeech'] = lemma.pos
        elem = ET.Element('Lemma', attrib=attrib)
    if version != '1.0':
        for pron in lemma.pronunciations:
            elem.append(_build_pronunciation(pron))
    for tag in lemma.tags:
        elem.append(_build_tag(tag))
    return elem


def _build_form(form: Form, version: str) -> ET.Element:
    attrib = {}
    if version != '1.0' and form.id:
        attrib['id'] = form.id
    if form.external:
        elem = ET.Element('ExternalForm', attrib=attrib)
    else:
        attrib['writtenForm'] = form.form
        if form.script:
            attrib['script'] = form.script
        elem = ET.Element('Form', attrib=attrib)
    if version != '1.0':
        for pron in form.pronunciations:
            elem.append(_build_pronunciation(pron))
    for tag in form.tags:
        elem.append(_build_tag(tag))
    return elem


def _build_pronunciation(pron) -> ET.Element:
    attrib = {}
    if pron.variety:
        attrib['variety'] = pron.variety
    if pron.notation:
        attrib['notation'] = pron.notation
    if not pron.phonemic:
        attrib['phonemic'] = 'false'
    if pron.audio:
        attrib['audio'] = pron.audio
    elem = ET.Element('Pronunciation', attrib=attrib)
    elem.text = pron.value
    return elem


def _build_tag(tag: Tag) -> ET.Element:
    elem = ET.Element('Tag', category=tag.category)
    elem.text = tag.text
    return elem


def _build_sense(
    sense: Sense,
    sbmap: Dict[str, List[SyntacticBehaviour]],
    version: str,
) -> ET.Element:
    attrib = {'id': sense.id}
    if sense.external:
        elem = ET.Element('ExternalSense', attrib=attrib)
    else:
        attrib['synset'] = sense.synset
        attrib.update(_meta_dict(sense.meta))
        if not sense.lexicalized:
            attrib['lexicalized'] = 'false'
        if sense.adjposition:
            attrib['adjposition'] = sense.adjposition
        if version != '1.0' and sense.id in sbmap:
            attrib['subcat'] = ' '.join(sb.id for sb in sbmap[sense.id] if sb.id)
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
    attrib: Dict[str, str] = {'id': synset.id}
    if synset.external:
        elem = ET.Element('ExternalSynset', attrib=attrib)
    else:
        attrib['ili'] = synset.ili or ''
        if synset.pos:
            attrib['partOfSpeech'] = synset.pos
        if not synset.lexicalized:
            attrib['lexicalized'] = 'false'
        if version != '1.0':
            if synset.members:
                attrib['members'] = ' '.join(synset.members)
            if synset.lexfile:
                attrib['lexfile'] = synset.lexfile
        attrib.update(_meta_dict(synset.meta))
        elem = ET.Element('Synset', attrib=attrib)
    elem.extend(_build_definition(defn) for defn in synset.definitions)
    if synset.ili_definition and not synset.external:
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
    elem = _build_syntactic_behaviour(syntactic_behaviour, version=version)
    print('    ' + _tostring(elem, 2), file=out)


def _build_syntactic_behaviour(
    syntactic_behaviour: SyntacticBehaviour, version: str
) -> ET.Element:
    elem = ET.Element('SyntacticBehaviour')
    if version != '1.0' and syntactic_behaviour.id:
        elem.set('id', syntactic_behaviour.id)
    elem.set('subcategorizationFrame', syntactic_behaviour.frame)
    if version == '1.0' and syntactic_behaviour.senses:
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


def _meta_dict(m: Optional[Metadata]) -> Dict[str, str]:
    if m:
        d = {f'dc:{key}': str(val)
             for key, val in zip(m._fields, m)
             if val is not None}
    else:
        d = {}
    return d
