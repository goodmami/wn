
from xml.etree import ElementTree as ET

from wn import lmf


def test_is_lmf(datadir):
    assert lmf.is_lmf(datadir / 'mini-lmf-1.0.xml')
    assert lmf.is_lmf(str(datadir / 'mini-lmf-1.0.xml'))
    assert not lmf.is_lmf(datadir / 'README.md')
    assert not lmf.is_lmf(datadir / 'missing.xml')
    assert lmf.is_lmf(datadir / 'mini-lmf-1.1.xml')


def test_load_1_0(mini_lmf_1_0):
    resource = lmf.load(mini_lmf_1_0)
    lexicons = resource['lexicons']
    assert len(lexicons) == 2
    lexicon = lexicons[0]

    assert lexicon['id'] == 'test-en'
    assert lexicon['label'] == 'Testing English WordNet'
    assert lexicon['language'] == 'en'
    assert lexicon['email'] == 'maintainer@example.com'
    assert lexicon['license'] == 'https://creativecommons.org/licenses/by/4.0/'
    assert lexicon['version'] == '1'
    assert lexicon['url'] == 'https://example.com/test-en'

    assert len(lexicon['entries']) == 9
    le = lexicon['entries'][0]
    assert le['id'] == 'test-en-information-n'

    assert le['lemma']['writtenForm'] == 'information'
    assert le['lemma']['partOfSpeech'] == 'n'
    assert le['lemma']['script'] == 'Latn'
    assert len(le['lemma']['tags']) == 1

    assert len(le.get('forms', [])) == 0

    assert len(le['senses']) == 1
    sense = le['senses'][0]
    assert sense['id'] == 'test-en-information-n-0001-01'
    assert sense['synset'] == 'test-en-0001-n'
    assert len(sense.get('relations', [])) == 0
    # assert sense['relations'][0]['target'] == 'test-en-exemplify-v-01023137-01'
    # assert sense['relations'][0]['type'] == 'derivation'

    assert len(lexicon.get('frames', [])) == 0  # frames are on lexical entry
    assert len(lexicon['entries'][6]['frames']) == 2
    frames = lexicon['entries'][6]['frames']
    assert frames[0]['subcategorizationFrame'] == 'Somebody ----s something'
    assert frames[0]['senses'] == ['test-en-illustrate-v-0003-01']

    assert len(lexicon['synsets']) == 8

    assert lexicons[1]['id'] == 'test-es'


def test_load_1_1(mini_lmf_1_1):
    resource = lmf.load(mini_lmf_1_1)
    lexicons = resource['lexicons']
    assert len(lexicons) == 2
    lexicon = lexicons[0]
    assert lexicon['id'] == 'test-ja'
    assert lexicon['version'] == '1'
    # assert lexicon.logo == 'logo.svg'
    assert lexicon.get('requires') == [{'id': 'test-en', 'version': '1'}]

    lexicon = lexicons[1]
    assert lexicon['id'] == 'test-en-ext'
    assert lexicon.get('extends') == {'id': 'test-en', 'version': '1'}


def test_dump(mini_lmf_1_0, mini_lmf_1_1, tmp_path):
    tmpdir = tmp_path / 'test_dump'
    tmpdir.mkdir()
    tmppath = tmpdir / 'mini_lmf_dump.xml'

    def assert_xml_equal(mini_lmf, dump_lmf):
        if hasattr(ET, 'canonicalize'):  # available from Python 3.8
            orig = ET.canonicalize(from_file=mini_lmf, strip_text=True)
            temp = ET.canonicalize(from_file=dump_lmf, strip_text=True)
            # additional transformation to help with debugging
            orig = orig.replace('<', '\n<')
            temp = temp.replace('<', '\n<')
            assert orig == temp

    lmf.dump(lmf.load(mini_lmf_1_0), tmppath)
    assert_xml_equal(mini_lmf_1_0, tmppath)

    lmf.dump(lmf.load(mini_lmf_1_1), tmppath)
    assert_xml_equal(mini_lmf_1_1, tmppath)
