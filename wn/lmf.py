
"""
Reader for the Lexical Markup Framework (LMF) format.
"""

from typing import (
    Type,
    List,
    Tuple,
    Dict,
    Optional,
    TextIO,
    BinaryIO,
    Any,
    Union,
    cast
)
import sys
if sys.version_info >= (3, 8):
    from typing import TypedDict, Literal
else:
    from typing_extensions import TypedDict, Literal
import re
from pathlib import Path
import xml.etree.ElementTree as ET  # for general XML parsing
import xml.parsers.expat  # for fast scanning of Lexicon versions
from xml.sax.saxutils import quoteattr

import wn
from wn._types import AnyPath, VersionInfo
from wn._util import is_xml, version_info
from wn.util import ProgressHandler, ProgressBar


class LMFError(wn.Error):
    """Raised on invalid LMF-XML documents."""


class LMFWarning(Warning):
    """Issued on non-conforming LFM values."""


SUPPORTED_VERSIONS = {'1.0', '1.1'}
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
    version: dict(
        [(f'{uri} {attr}', attr) for attr in _DC_ATTRS]
        + [('status', 'status'),
           ('note', 'note'),
           ('confidenceScore', 'confidenceScore')]
    )
    for version, uri in _DC_URIS.items()
}

_LMF_1_0_ELEMS: Dict[str, str] = {
    'LexicalResource': 'lexical-resource',
    'Lexicon': 'lexicons',
    'LexicalEntry': 'entries',
    'Lemma': 'lemma',
    'Form': 'forms',
    'Tag': 'tags',
    'Sense': 'senses',
    'SenseRelation': 'relations',
    'Example': 'examples',
    'Count': 'counts',
    'SyntacticBehaviour': 'frames',
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
    'ExternalLexicalEntry': 'entries',
    'ExternalLemma': 'lemma',
    'ExternalForm': 'forms',
    'ExternalSense': 'senses',
    'ExternalSynset': 'synsets',
})
_VALID_ELEMS = {
    '1.0': _LMF_1_0_ELEMS,
    '1.1': _LMF_1_1_ELEMS,
}
_LIST_ELEMS = {  # elements that collect into lists
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
    'SyntacticBehaviour',
    'LexiconExtension',
    'Requires',
    'ExternalLexicalEntry',
    'ExternalForm',
    'ExternalSense',
    'ExternalSynset',
}
_CDATA_ELEMS = {  # elements with inner text
    'Pronunciation',
    'Tag',
    'Definition',
    'ILIDefinition',
    'Example',
    'Count',
}
_META_ELEMS = {  # elements with metadata
    'Lexicon',
    'LexicalEntry',
    'Sense',
    'SenseRelation',
    'Example',
    'Count',
    'Synset',
    'Definition',
    'ILIDefinition',
    'SynsetRelation',
    'LexiconExtension',
}


# WN-LMF Modeling ######################################################

# WN-LMF type-checking is handled via TypedDicts.  Inheritance and
# `total=False` are used to model optionality. For more information
# about this tactic, see https://www.python.org/dev/peps/pep-0589/.

class Metadata(TypedDict, total=False):
    contributor: str
    coverage: str
    creator: str
    date: str
    description: str
    format: str
    identifier: str
    publisher: str
    relation: str
    rights: str
    source: str
    subject: str
    title: str
    type: str
    status: str
    note: str
    confidenceScore: float


_HasId = TypedDict('_HasId', {'id': str})
_HasVersion = TypedDict('_HasVersion', {'version': str})
_HasILI = TypedDict('_HasILI', {'ili': str})
_HasSynset = TypedDict('_HasSynset', {'synset': str})
_MaybeId = TypedDict('_MaybeId', {'id': str}, total=False)
_HasText = TypedDict('_HasText', {'text': str})
_MaybeScript = TypedDict('_MaybeScript', {'script': str}, total=False)
_HasMeta = TypedDict('_HasMeta', {'meta': Optional[Metadata]})
_External = TypedDict('_External', {'external': Literal['true']})


class ILIDefinition(_HasText, _HasMeta):
    ...


class Definition(_HasText, _HasMeta, total=False):
    language: str
    sourceSense: str


class Relation(_HasMeta):
    target: str
    relType: str


class Example(_HasText, _HasMeta, total=False):
    language: str


class Synset(_HasId, _HasILI, _HasMeta, total=False):
    ili_definition: ILIDefinition
    partOfSpeech: str
    definitions: List[Definition]
    relations: List[Relation]
    examples: List[Example]
    lexicalized: bool
    members: List[str]
    lexfile: str


class ExternalSynset(_HasId, _External, total=False):
    definitions: List[Definition]
    relations: List[Relation]
    examples: List[Example]


class Count(_HasMeta):
    value: int


class Sense(_HasId, _HasSynset, _HasMeta, total=False):
    relations: List[Relation]
    examples: List[Example]
    counts: List[Count]
    lexicalized: bool
    adjposition: str
    subcat: List[str]


class ExternalSense(_HasId, _External, total=False):
    relations: List[Relation]
    examples: List[Example]
    counts: List[Count]


class Pronunciation(_HasText, total=False):
    variety: str
    notation: str
    phonemic: bool
    audio: str


class Tag(_HasText):
    category: str


class _FormChildren(TypedDict, total=False):
    pronunciations: List[Pronunciation]
    tags: List[Tag]


class Lemma(_MaybeScript, _FormChildren):
    writtenForm: str
    partOfSpeech: str


class ExternalLemma(_FormChildren, _External):
    ...


class Form(_MaybeId, _MaybeScript, _FormChildren):
    writtenForm: str


class ExternalForm(_HasId, _FormChildren, _External):
    ...


class _SyntacticBehaviourBase(_MaybeId):
    subcategorizationFrame: str


class SyntacticBehaviour(_SyntacticBehaviourBase, total=False):
    senses: List[str]


class _LexicalEntryBase(_HasId, _HasMeta, total=False):
    forms: List[Form]
    senses: List[Sense]
    frames: List[SyntacticBehaviour]


class LexicalEntry(_LexicalEntryBase):
    lemma: Lemma


class ExternalLexicalEntry(_HasId, _External, total=False):
    lemma: ExternalLemma
    forms: List[Union[Form, ExternalForm]]
    senses: List[Union[Sense, ExternalSense]]


class Dependency(_HasId, _HasVersion, total=False):
    url: str


class _LexiconBase(_HasMeta):
    id: str
    version: str
    label: str
    language: str
    email: str
    license: str


class Lexicon(_LexiconBase, total=False):
    url: str
    citation: str
    logo: str
    requires: List[Dependency]
    entries: List[LexicalEntry]
    synsets: List[Synset]
    frames: List[SyntacticBehaviour]


class LexiconExtension(_LexiconBase, total=False):
    url: str
    citation: str
    logo: str
    extends: Dependency
    requires: List[Dependency]
    entries: List[Union[LexicalEntry, ExternalLexicalEntry]]
    synsets: List[Union[Synset, ExternalSynset]]
    frames: List[SyntacticBehaviour]


class LexicalResource(TypedDict):
    lmf_version: str
    lexicons: List[Union[Lexicon, LexiconExtension]]


# Reading ##############################################################

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
    infos: List[Dict] = []

    lex_re = re.compile(b'<(Lexicon|LexiconExtension|Extends)\\b([^>]*)>', flags=re.M)
    attr_re = re.compile(b'''\\b(id|version|label)=["']([^"']+)["']''', flags=re.M)

    with open(source, 'rb') as fh:
        for m in lex_re.finditer(fh.read()):
            lextype, remainder = m.groups()
            info = {_m.group(1).decode('utf-8'): _m.group(2).decode('utf-8')
                    for _m in attr_re.finditer(remainder)}
            if 'id' not in info or 'version' not in info:
                raise LMFError(f'<{lextype.decode("utf-8")}> missing id or version')
            if lextype != b'Extends':
                infos.append(info)
            elif len(infos) > 0:
                infos[-1]['extends'] = info
            else:
                raise LMFError('invalid use of <Extends> in WN-LMF file')

    return infos


_Elem = Dict[str, Any]  # basic type for the loaded XML data


def load(
    source: AnyPath,
    progress_handler: Optional[Type[ProgressHandler]] = ProgressBar
) -> LexicalResource:
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

    root: Dict[str, _Elem] = {}
    parser = _make_parser(root, version, progress)

    with open(source, 'rb') as fh:
        try:
            parser.ParseFile(fh)
        except xml.parsers.expat.ExpatError as exc:
            raise LMFError('invalid or ill-formed XML') from exc

    progress.close()

    resource: LexicalResource = {
        'lmf_version': version,
        'lexicons': [_validate(lex)
                     for lex in root['lexical-resource'].get('lexicons', [])],
    }

    return resource


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

    p = xml.parsers.expat.ParserCreate(namespace_separator=' ')
    has_text = False

    def start(name, attrs):
        nonlocal has_text
        if name in CDATA_ELEMS:
            has_text = True

        if name in _META_ELEMS:
            meta = {}
            for attr in list(attrs):
                if attr in NS_ATTRS:
                    meta[NS_ATTRS[attr]] = attrs.pop(attr)
            attrs['meta'] = meta or None

        if name.startswith('External'):
            attrs['external'] = True

        parent = stack[-1]
        key = ELEMS.get(name)
        if name in LIST_ELEMS:
            parent.setdefault(key, []).append(attrs)
        elif key is None or key in parent:
            raise _unexpected(name, p)
        else:
            parent[key] = attrs

        stack.append(attrs)

    def char_data(data):
        if has_text:
            parent = stack[-1]
            # sometimes the buffering occurs in the middle of text; if
            # so, append the current data
            if 'text' in parent:
                parent['text'] += data
            else:
                parent['text'] = data

    def end(name):
        nonlocal has_text
        has_text = False
        stack.pop()
        progress.update(force=(name == 'LexicalResource'))

    p.StartElementHandler = start
    p.EndElementHandler = end
    p.CharacterDataHandler = char_data

    return p


def _unexpected(name: str, p: xml.parsers.expat.XMLParserType) -> LMFError:
    return LMFError(f'unexpected element at line {p.CurrentLineNumber}: {name}')


# Validation ###########################################################

def _validate(elem: _Elem) -> Union[Lexicon, LexiconExtension]:
    ext = elem.get('extends')
    if ext:
        assert 'id' in ext
        assert 'version' in ext
        _validate_lexicon(elem, True)
        return cast(LexiconExtension, elem)
    else:
        _validate_lexicon(elem, False)
        return cast(Lexicon, elem)


def _validate_lexicon(elem: _Elem, extension: bool) -> None:
    for attr in 'id', 'version', 'label', 'language', 'email', 'license':
        assert attr in elem, f'<Lexicon> missing required attribute: {attr}'
    for dep in elem.get('requires', []):
        assert 'id' in dep
        assert 'version' in dep
    _validate_entries(elem.get('entries', []), extension)
    _validate_synsets(elem.get('synsets', []), extension)
    _validate_frames(elem.get('frames', []))


def _validate_entries(elems: List[_Elem], extension: bool) -> None:
    for elem in elems:
        assert 'id' in elem
        if not extension:
            assert not elem.get('external')
        lemma = elem.get('lemma')
        if not elem.get('external'):
            assert lemma is not None
            elem.setdefault('meta')
        # lemma and forms are the same except for partOfSpeech and id
        if lemma is not None and not lemma.get('external'):
            assert 'partOfSpeech' in lemma
        for form in elem.get('forms', []):
            assert not form.get('external') or form.get('id')
        _validate_forms(([lemma] if lemma else []) + elem.get('forms', []), extension)
        _validate_senses(elem.get('senses', []), extension)
        _validate_frames(elem.get('frames', []))


def _validate_forms(elems: List[_Elem], extension: bool) -> None:
    for elem in elems:
        if not extension:
            assert not elem.get('external')
        if not elem.get('external'):
            assert 'writtenForm' in elem
        for pron in elem.get('pronunciations', []):
            pron.setdefault('text', '')
            if pron.get('phonemic'):
                pron['phonemic'] = False if pron['phonemic'] == 'false' else True
        for tag in elem.get('tags', []):
            tag.setdefault('text', '')
            assert 'category' in tag


def _validate_senses(elems: List[_Elem], extension: bool) -> None:
    for elem in elems:
        assert 'id' in elem
        if not extension:
            assert not elem.get('external')
        if not elem.get('external'):
            assert 'synset' in elem
            elem.setdefault('meta')
        for rel in elem.get('relations', []):
            assert 'target' in rel
            assert 'relType' in rel
            rel.setdefault('meta')
        for ex in elem.get('examples', []):
            ex.setdefault('text', '')
            ex.setdefault('meta')
        for cnt in elem.get('counts', []):
            assert 'text' in cnt
            cnt['value'] = int(cnt.pop('text'))
            cnt.setdefault('meta')
        if elem.get('lexicalized'):
            elem['lexicalized'] = False if elem['lexicalized'] == 'false' else True
        if elem.get('subcat'):
            elem['subcat'] = elem['subcat'].split()


def _validate_frames(elems: List[_Elem]) -> None:
    for elem in elems:
        assert 'subcategorizationFrame' in elem
        if elem.get('senses'):
            elem['senses'] = elem['senses'].split()


def _validate_synsets(elems: List[_Elem], extension: bool) -> None:
    for elem in elems:
        assert 'id' in elem
        if not extension:
            assert not elem.get('external')
        if not elem.get('external'):
            assert 'ili' in elem
            elem.setdefault('meta')
        for defn in elem.get('definitions', []):
            defn.setdefault('text', '')
            defn.setdefault('meta')
        for rel in elem.get('relations', []):
            assert 'target' in rel
            assert 'relType' in rel
            rel.setdefault('meta')
        for ex in elem.get('examples', []):
            ex.setdefault('text', '')
            ex.setdefault('meta')
        if elem.get('lexicalized'):
            elem['lexicalized'] = False if elem['lexicalized'] == 'false' else True
        if elem.get('members'):
            elem['members'] = elem['members'].split()


def _validate_metadata(elem: _Elem) -> None:
    if elem.get('confidenceScore'):
        elem['confidenceScore'] = float(elem['confidenceScore'])


# Serialization ########################################################

def dump(resource: LexicalResource, destination: AnyPath) -> None:
    """Write wordnets in the WN-LMF format.

    Args:
        lexicons: a list of :class:`Lexicon` objects
    """
    version = resource['lmf_version']
    if version not in SUPPORTED_VERSIONS:
        raise LMFError(f'invalid version: {version}')
    destination = Path(destination).expanduser()
    doctype = _DOCTYPE.format(schema=_SCHEMAS[version])
    dc_uri = _DC_URIS[version]
    _version = version_info(version)
    with destination.open('wt', encoding='utf-8') as out:
        print(_XMLDECL.decode('utf-8'), file=out)
        print(doctype, file=out)
        print(f'<LexicalResource xmlns:dc="{dc_uri}">', file=out)
        for lexicon in resource['lexicons']:
            _dump_lexicon(lexicon, out, _version)
        print('</LexicalResource>', file=out)


def _dump_lexicon(
    lexicon: Union[Lexicon, LexiconExtension],
    out: TextIO,
    version: VersionInfo
) -> None:
    lexicontype = 'LexiconExtension' if lexicon.get('extends') else 'Lexicon'
    attrib = _build_lexicon_attrib(lexicon, version)
    attrdelim = '\n' + (' ' * len(f'  <{lexicontype} '))
    attrs = attrdelim.join(
        f'{attr}={quoteattr(str(val))}' for attr, val in attrib.items()
    )
    print(f'  <{lexicontype} {attrs}>', file=out)

    if version >= (1, 1):
        if lexicontype == 'LexiconExtension':
            assert lexicon.get('extends')
            lexicon = cast(LexiconExtension, lexicon)
            _dump_dependency(lexicon['extends'], 'Extends', out)
        for req in lexicon.get('requires', []):
            _dump_dependency(req, 'Requires', out)

    for entry in lexicon.get('entries', []):
        _dump_lexical_entry(entry, out, version)

    for synset in lexicon.get('synsets', []):
        _dump_synset(synset, out, version)

    if version >= (1, 1):
        for sb in lexicon.get('frames', []):
            _dump_syntactic_behaviour(sb, out, version)

    print(f'  </{lexicontype}>', file=out)


def _build_lexicon_attrib(
    lexicon: Union[Lexicon, LexiconExtension],
    version: VersionInfo
) -> Dict[str, str]:
    attrib = {
        'id': lexicon['id'],
        'label': lexicon['label'],
        'language': lexicon['language'],
        'email': lexicon['email'],
        'license': lexicon['license'],
        'version': lexicon['version'],
    }
    if lexicon.get('url'):
        attrib['url'] = lexicon['url']
    if lexicon.get('citation'):
        attrib['citation'] = lexicon['citation']
    if version >= (1, 1) and lexicon.get('logo'):
        attrib['logo'] = lexicon['logo']
    attrib.update(_meta_dict(lexicon.get('meta')))
    return attrib


def _dump_dependency(
    dep: Dependency, deptype: str, out: TextIO
) -> None:
    attrib = {'id': dep['id'], 'version': dep['version']}
    if dep.get('url'):
        attrib['url'] = dep['url']
    elem = ET.Element(deptype, attrib=attrib)
    print(_tostring(elem, 2), file=out)


def _dump_lexical_entry(
    entry: Union[LexicalEntry, ExternalLexicalEntry],
    out: TextIO,
    version: VersionInfo,
) -> None:
    frames = []
    attrib = {'id': entry['id']}
    if entry.get('external', False):
        elem = ET.Element('ExternalLexicalEntry', attrib=attrib)
        if entry.get('lemma'):
            assert entry['lemma'].get('external', False)
            elem.append(_build_lemma(entry['lemma'], version))
    else:
        entry = cast(LexicalEntry, entry)
        attrib.update(_meta_dict(entry.get('meta')))
        elem = ET.Element('LexicalEntry', attrib=attrib)
        elem.append(_build_lemma(entry['lemma'], version))
        if version < (1, 1):
            frames = [_build_syntactic_behaviour(sb, version)
                      for sb in entry.get('frames', [])]
    elem.extend([_build_form(form, version) for form in entry.get('forms', [])])
    elem.extend([_build_sense(sense, version)
                 for sense in entry.get('senses', [])])
    elem.extend(frames)
    print(_tostring(elem, 2), file=out)


def _build_lemma(
    lemma: Union[Lemma, ExternalLemma],
    version: VersionInfo
) -> ET.Element:
    if lemma.get('external', False):
        elem = ET.Element('ExternalLemma')
    else:
        lemma = cast(Lemma, lemma)
        attrib = {'writtenForm': lemma['writtenForm']}
        if lemma.get('script'):
            attrib['script'] = lemma['script']
        attrib['partOfSpeech'] = lemma['partOfSpeech']
        elem = ET.Element('Lemma', attrib=attrib)
    if version >= (1, 1):
        for pron in lemma.get('pronunciations', []):
            elem.append(_build_pronunciation(pron))
    for tag in lemma.get('tags', []):
        elem.append(_build_tag(tag))
    return elem


def _build_form(form: Union[Form, ExternalForm], version: VersionInfo) -> ET.Element:
    attrib = {}
    if version >= (1, 1) and form['id']:
        attrib['id'] = form['id']
    if form.get('external', False):
        elem = ET.Element('ExternalForm', attrib=attrib)
    else:
        form = cast(Form, form)
        attrib['writtenForm'] = form['writtenForm']
        if form.get('script'):
            attrib['script'] = form['script']
        elem = ET.Element('Form', attrib=attrib)
    if version >= (1, 1):
        for pron in form.get('pronunciations', []):
            elem.append(_build_pronunciation(pron))
    for tag in form.get('tags', []):
        elem.append(_build_tag(tag))
    return elem


def _build_pronunciation(pron: Pronunciation) -> ET.Element:
    attrib = {}
    if pron.get('variety'):
        attrib['variety'] = pron['variety']
    if pron.get('notation'):
        attrib['notation'] = pron['notation']
    if not pron.get('phonemic', True):
        attrib['phonemic'] = 'false'
    if pron.get('audio'):
        attrib['audio'] = pron['audio']
    elem = ET.Element('Pronunciation', attrib=attrib)
    elem.text = pron['text']
    return elem


def _build_tag(tag: Tag) -> ET.Element:
    elem = ET.Element('Tag', category=tag['category'])
    elem.text = tag['text']
    return elem


def _build_sense(
    sense: Union[Sense, ExternalSense],
    version: VersionInfo,
) -> ET.Element:
    attrib = {'id': sense['id']}
    if sense.get('external'):
        elem = ET.Element('ExternalSense', attrib=attrib)
    else:
        sense = cast(Sense, sense)
        attrib['synset'] = sense['synset']
        attrib.update(_meta_dict(sense.get('meta')))
        if not sense.get('lexicalized', True):
            attrib['lexicalized'] = 'false'
        if sense.get('adjposition'):
            attrib['adjposition'] = sense['adjposition']
        if version >= (1, 1) and sense.get('subcat'):
            attrib['subcat'] = ' '.join(sense['subcat'])
        elem = ET.Element('Sense', attrib=attrib)
    elem.extend([_build_relation(rel, 'SenseRelation')
                 for rel in sense.get('relations', [])])
    elem.extend([_build_example(ex) for ex in sense.get('examples', [])])
    elem.extend([_build_count(cnt) for cnt in sense.get('counts', [])])
    return elem


def _build_example(example: Example) -> ET.Element:
    elem = ET.Element('Example')
    elem.text = example['text']
    if example.get('language'):
        elem.set('language', example['language'])
    return elem


def _build_count(count: Count) -> ET.Element:
    elem = ET.Element('Count', attrib=_meta_dict(count.get('meta')))
    elem.text = str(count['value'])
    return elem


def _dump_synset(
    synset: Union[Synset, ExternalSynset],
    out: TextIO,
    version: VersionInfo
) -> None:
    attrib: Dict[str, str] = {'id': synset['id']}
    if synset.get('external', False):
        elem = ET.Element('ExternalSynset', attrib=attrib)
        elem.extend([_build_definition(defn) for defn in synset.get('definitions', [])])
    else:
        synset = cast(Synset, synset)
        attrib['ili'] = synset['ili']
        if synset.get('partOfSpeech'):
            attrib['partOfSpeech'] = synset['partOfSpeech']
        if not synset.get('lexicalized', True):
            attrib['lexicalized'] = 'false'
        if version >= (1, 1):
            if synset.get('members'):
                attrib['members'] = ' '.join(synset['members'])
            if synset.get('lexfile'):
                attrib['lexfile'] = synset['lexfile']
        attrib.update(_meta_dict(synset.get('meta')))
        elem = ET.Element('Synset', attrib=attrib)
        elem.extend([_build_definition(defn) for defn in synset.get('definitions', [])])
        if synset.get('ili_definition'):
            elem.append(_build_ili_definition(synset['ili_definition']))
    elem.extend([_build_relation(rel, 'SynsetRelation')
                 for rel in synset.get('relations', [])])
    elem.extend([_build_example(ex) for ex in synset.get('examples', [])])
    print(_tostring(elem, 2), file=out)


def _build_definition(definition: Definition) -> ET.Element:
    attrib = {}
    if definition.get('language'):
        attrib['language'] = definition['language']
    if definition.get('sourceSense'):
        attrib['sourceSense'] = definition['sourceSense']
    attrib.update(_meta_dict(definition.get('meta')))
    elem = ET.Element('Definition', attrib=attrib)
    elem.text = definition['text']
    return elem


def _build_ili_definition(ili_definition: ILIDefinition) -> ET.Element:
    elem = ET.Element('ILIDefinition', attrib=_meta_dict(ili_definition.get('meta')))
    elem.text = ili_definition['text']
    return elem


def _build_relation(relation: Relation, elemtype: str) -> ET.Element:
    attrib = {'target': relation['target'], 'relType': relation['relType']}
    attrib.update(_meta_dict(relation.get('meta')))
    return ET.Element(elemtype, attrib=attrib)


def _dump_syntactic_behaviour(
    syntactic_behaviour: SyntacticBehaviour,
    out: TextIO,
    version: VersionInfo
) -> None:
    elem = _build_syntactic_behaviour(syntactic_behaviour, version)
    print('    ' + _tostring(elem, 2), file=out)


def _build_syntactic_behaviour(
    syntactic_behaviour: SyntacticBehaviour,
    version: VersionInfo
) -> ET.Element:
    attrib = {'subcategorizationFrame': syntactic_behaviour['subcategorizationFrame']}
    if version >= (1, 1) and syntactic_behaviour.get('id'):
        attrib['id'] = syntactic_behaviour['id']
    elif version < (1, 1) and syntactic_behaviour.get('senses'):
        attrib['senses'] = ' '.join(syntactic_behaviour['senses'])
    return ET.Element('SyntacticBehaviour', attrib=attrib)


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


def _meta_dict(meta: Optional[Metadata]) -> Dict[str, str]:
    if meta is not None:
        # Literal keys are required for typing purposes, so first
        # construct the dict and then remove those that weren't specified.
        d = {
            'dc:contributor': meta.get('contributor', ''),
            'dc:coverage': meta.get('coverage', ''),
            'dc:creator': meta.get('creator', ''),
            'dc:date': meta.get('date', ''),
            'dc:description': meta.get('description', ''),
            'dc:format': meta.get('format', ''),
            'dc:identifier': meta.get('identifier', ''),
            'dc:publisher': meta.get('publisher', ''),
            'dc:relation': meta.get('relation', ''),
            'dc:rights': meta.get('rights', ''),
            'dc:source': meta.get('source', ''),
            'dc:subject': meta.get('subject', ''),
            'dc:title': meta.get('title', ''),
            'dc:type': meta.get('type', ''),
            'status': meta.get('status', ''),
            'note': meta.get('note', ''),
        }
        d = {key: val for key, val in d.items() if val}
        # this one requires a conversion, so do it separately
        if 'confidenceScore' in meta:
            d['confidenceScore'] = str(meta['confidenceScore'])
    else:
        d = {}
    return d
