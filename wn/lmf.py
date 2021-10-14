
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import (
    Type,
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
import xml.etree.ElementTree as ET  # for general XML parsing
import xml.parsers.expat  # for fast scanning of Lexicon versions
from xml.sax.saxutils import quoteattr

import wn
from wn._types import AnyPath
from wn._util import is_xml
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
    '1.1': 'https://globalwordnet.github.io/schemas/dc/',
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
_NS_ATTRS = {
    version: {f'{uri} {attr}': attr for attr in _DC_ATTRS}
    for version, uri in _DC_URIS.items()
}

_LMF_1_0_ELEMS: Dict[str, str] = {
    'Lexicon': 'lexicons',
    'LexicalEntry': 'lexical_entries',
    'Lemma': 'lemma',
    'Form': 'forms',
    'Tag': 'tags',
    'Sense': 'senses',
    'SenseRelation': 'relations',
    'Example': 'examples',
    'Count': 'counts',
    'SyntacticBehaviour': 'syntactic_behaviours',
    'Synset': 'synsets',
    'Definition': 'definitions',
    'ILIDefinition': 'ili_definition',
    'SynsetRelation': 'relations',
}
_LMF_1_1_ELEMS = dict(_LMF_1_0_ELEMS)
_LMF_1_1_ELEMS.update({
    'Requires': 'requires',
    'Extends': 'extends',
    'Pronunciation': 'pronunciations',
    'LexiconExtension': 'lexicons',
    'ExternalLexicalEntry': 'lexical_entries',
    'ExternalLemma': 'lemma',
    'ExternalForm': 'forms',
    'ExternalSense': 'senses',
    'ExternalSynset': 'synsets',
})
_VALID_ELEMS = {
    '1.0': _LMF_1_0_ELEMS,
    '1.1': _LMF_1_1_ELEMS,
}
_LIST_ELEMS = {
    'Lexicon',
    'LexicalEntry',
    'Form',
    'Pronunciation',
    'Tag',
    'Sense',
    'SenseRelation',
    'Example',
    'Count',
    'Synset',
    'Definition',
    'SynsetRelation',
    # 'SyntacticBehaviour',  # handled specially
    'LexiconExtension',
    'Requires',
    'ExternalLexicalEntry',
    'ExternalForm',
    'ExternalSense',
    'ExternalSynset',
}
_CDATA_ELEMS = {
    'Pronunciation',
    'Tag',
    'Definition',
    'ILIDefinition',
    'Example',
    'Count',
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

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(int(attrs.get('text', '0')), meta=meta)

    @property
    def text(self): return self.value

    @text.setter
    def text(self, text):
        self.value = int(text)


class SyntacticBehaviour:
    __slots__ = 'id', 'frame', 'senses'

    def __init__(self, id: str, frame: str, senses: List[str] = None):
        self.id = id
        self.frame = frame
        self.senses = senses or []

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('id', ''),
                   attrs['subcategorizationFrame'],
                   senses=attrs.get('senses', '').split())


class SenseRelation(_HasMeta):
    __slots__ = 'target', 'type'

    def __init__(self, target: str, type: str, meta: Metadata = None):
        super().__init__(meta)
        self.target = target
        self.type = type

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs['target'], attrs['relType'], meta=meta)


class SynsetRelation(_HasMeta):
    __slots__ = 'target', 'type'

    def __init__(self, target: str, type: str, meta: Metadata = None):
        super().__init__(meta)
        self.target = target
        self.type = type

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs['target'], attrs['relType'], meta=meta)


class Example(_HasMeta):
    __slots__ = 'text', 'language'

    def __init__(self, text: str, language: str = '', meta: Metadata = None):
        super().__init__(meta)
        self.text = text
        self.language = language

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('text', ''), language=attrs.get('language', ''), meta=meta)


class ILIDefinition(_HasMeta):
    __slots__ = 'text',

    def __init__(self, text: str, meta: Metadata = None):
        super().__init__(meta)
        self.text = text

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('text', ''), meta=meta)


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

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('text', ''),
                   language=attrs.get('language', ''),
                   source_sense=attrs.get('sourceSense', ''),
                   meta=meta)


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
    def from_expat(cls, attrs, meta):
        obj = cls(attrs['id'],
                  attrs.get('ili', ''),
                  attrs.get('partOfSpeech', ''),
                  definitions=attrs.get('definitions'),
                  ili_definition=attrs.get('ili_definition'),
                  relations=attrs.get('relations'),
                  examples=attrs.get('examples'),
                  lexicalized=attrs.get('lexicalized', 'true') == 'true',
                  members=attrs.get('members', '').split() or None,
                  lexfile=attrs.get('lexfile'),
                  meta=meta)
        obj.external = attrs.get('external', False)
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
    def from_expat(cls, attrs, meta):
        obj = cls(attrs['id'],
                  attrs.get('synset', ''),
                  relations=attrs.get('relations'),
                  examples=attrs.get('examples'),
                  counts=attrs.get('counts'),
                  lexicalized=attrs.get('lexicalized', 'true') == 'true',
                  adjposition=attrs.get('adjposition'),
                  meta=meta)
        obj.external = attrs.get('external', False)
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

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('text', ''),
                   variety=attrs.get('variety'),
                   notation=attrs.get('notation'),
                   phonemic=attrs.get('phonemic', True),
                   audio=attrs.get('audio'))

    @property
    def text(self): return self.value

    @text.setter
    def text(self, text):
        self.value = text


class Tag:
    __slots__ = 'text', 'category'

    def __init__(self, text: str, category: str):
        self.text = text
        self.category = category

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('text', ''), attrs['category'])


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
    def from_expat(cls, attrs, meta):
        obj = cls(attrs.get('id'),
                  attrs['writtenForm'],
                  attrs.get('script', ''),
                  pronunciations=attrs.get('pronunciations'),
                  tags=attrs.get('tags'))
        obj.external = attrs.get('external', False)
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
    def from_expat(cls, attrs, meta):
        obj = cls(attrs.get('writtenForm', ''),
                  attrs.get('partOfSpeech', ''),
                  script=attrs.get('script', ''),
                  pronunciations=attrs.get('pronunciations'),
                  tags=attrs.get('tags'))
        obj.external = attrs.get('external', False)
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
    def from_expat(cls, attrs, meta):
        obj = cls(attrs['id'],
                  lemma=attrs.get('lemma'),
                  forms=attrs.get('forms'),
                  senses=attrs.get('senses'),
                  meta=meta)
        obj.external = attrs.get('external', False)
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

    @classmethod
    def from_expat(cls, attrs, meta):
        for dep in [attrs.get('extends', {}), *attrs.get('requires', [])]:
            dep.setdefault('url', None)
        return cls(attrs['id'],
                   attrs['label'],
                   attrs['language'],
                   attrs['email'],
                   attrs['license'],
                   attrs['version'],
                   url=attrs.get('url', ''),
                   citation=attrs.get('citation', ''),
                   logo=attrs.get('logo', ''),
                   lexical_entries=attrs.get('entries'),
                   synsets=attrs.get('synsets'),
                   syntactic_behaviours=attrs.get('frames'),
                   extends=attrs.get('extends'),
                   requires=attrs.get('requires'),
                   meta=meta)


class Dependency:
    @staticmethod
    def from_expat(attrs, meta):
        attrs.setdefault('url', None)
        return attrs


class LexicalResource:
    def __init__(self, lexicons: List[Lexicon], lmf_version: str):
        self.lexicons = lexicons or []
        self.lmf_version = lmf_version

    @classmethod
    def from_expat(cls, attrs, meta):
        return cls(attrs.get('lexicons', []),
                   attrs.get('lmf-version'))


_ELEM_CLASS = {
    'LexicalResource': LexicalResource,
    'Lexicon': Lexicon,
    'LexicalEntry': LexicalEntry,
    'Lemma': Lemma,
    'Form': Form,
    'Tag': Tag,
    'Sense': Sense,
    'SenseRelation': SenseRelation,
    'Example': Example,
    'Count': Count,
    'SyntacticBehaviour': SyntacticBehaviour,
    'Synset': Synset,
    'Definition': Definition,
    'ILIDefinition': ILIDefinition,
    'SynsetRelation': SynsetRelation,
    'Requires': Dependency,
    'Extends': Dependency,
    'Pronunciation': Pronunciation,
    'LexiconExtension': Lexicon,
    'ExternalLexicalEntry': LexicalEntry,
    'ExternalLemma': Lemma,
    'ExternalForm': Form,
    'ExternalSense': Sense,
    'ExternalSynset': Synset,
}


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
) -> List[Lexicon]:
    """Load wordnets encoded in the WN-LMF format.

    Args:
        source: path to a WN-LMF file
    """
    source = Path(source).expanduser()
    if progress_handler is None:
        progress_handler = ProgressHandler

    version, num_elements = _quick_scan(source)
    progress = progress_handler(
        message='Read', total=num_elements, refresh_interval=10000
    )

    root = LexicalResource([], version)
    parser = _make_parser(root, version, progress)

    with open(source, 'rb') as fh:
        try:
            parser.ParseFile(fh)
        except xml.parsers.expat.ExpatError as exc:
            raise LMFError('invalid or ill-formed XML') from exc

    progress.close()

    return root.lexicons


def _quick_scan(source: Path) -> Tuple[str, int]:
    with source.open('rb') as fh:
        version = _read_header(fh)
        # _read_header() only reads the first 2 lines
        remainder = fh.read()
        num_elements = remainder.count(b'</') + remainder.count(b'/>')
    return version, num_elements


def _make_parser(root, version, progress):  # noqa: C901
    stack = [root]
    ELEMS = _VALID_ELEMS[version]
    NS_ATTRS = _NS_ATTRS[version]
    CDATA_ELEMS = _CDATA_ELEMS & set(ELEMS)
    LIST_ELEMS = _LIST_ELEMS & set(ELEMS)
    frames: Dict[str, SyntacticBehaviour] = {}
    sbmap: Dict[str, List[str]] = {}

    p = xml.parsers.expat.ParserCreate(namespace_separator=' ')
    has_text = False

    def start(name, attrs):
        nonlocal has_text
        if name in CDATA_ELEMS:
            has_text = True
        elif name in ('Lexicon', 'LexiconExtension'):
            frames.clear()
            sbmap.clear()
        elif name == 'Sense' and 'subcat' in attrs:
            for sbid in attrs['subcat'].split():
                sbmap.setdefault(sbid, []).append(attrs['id'])
        parent = stack[-1]
        if name in ELEMS:
            meta = Metadata(**{attr: attrs[uri]
                               for uri, attr in NS_ATTRS.items()
                               if uri in attrs})
            if name.startswith('External'):
                attrs['external'] = True
            obj = _ELEM_CLASS[name].from_expat(attrs, meta)
            if name in LIST_ELEMS:
                getattr(parent, ELEMS[name]).append(obj)
            elif name == 'SyntacticBehaviour':
                if obj.id and obj.id in sbmap:  # assume at end of LMF 1.1 lexicon
                    obj.senses.extend(sbmap[obj.id])
                    frames[obj.frame] = obj
                else:
                    # assume at end of LMF 1.0 lexical entry
                    if not obj.senses and isinstance(parent, LexicalEntry):
                        obj.senses = [s.id for s in parent.senses]
                    if obj.frame in frames:
                        frames[obj.frame].senses.extend(obj.senses)
                    else:
                        frames[obj.frame] = obj
            else:
                setattr(parent, ELEMS[name], obj)
            stack.append(obj)
        elif name != 'LexicalResource':
            raise _unexpected(name, p)

    def char_data(data):
        if has_text:
            stack[-1].text = data

    def end(name):
        nonlocal has_text
        has_text = False
        obj = stack.pop()
        if name in ('Lexicon', 'LexiconExtension'):
            obj.syntactic_behaviours = list(frames.values())
        progress.update(force=(name == 'LexicalResource'))

    p.StartElementHandler = start
    p.EndElementHandler = end
    p.CharacterDataHandler = char_data

    return p


def _unexpected(name: str, p: xml.parsers.expat.XMLParserType) -> LMFError:
    return LMFError(f'unexpected element at line {p.CurrentLineNumber}: {name}')


def dump(
        lexicons: List[Lexicon], destination: AnyPath, version: str = '1.0'
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
        d = {f'dc:{key}': str(getattr(m, key))
             for key in _DC_ATTRS
             if getattr(m, key, None) is not None}
        if m.status is not None:
            d['status'] = m.status
        if m.note is not None:
            d['note'] = m.note
        if m.confidence is not None:
            d['confidenceScore'] = str(m.confidence)
    else:
        d = {}
    return d
