
from xml.etree import ElementTree as ET

from wn import lmf


def test_is_lmf(datadir):
    assert lmf.is_lmf(datadir / 'mini-lmf-1.0.xml')
    assert lmf.is_lmf(str(datadir / 'mini-lmf-1.0.xml'))
    assert not lmf.is_lmf(datadir / 'README.md')
    assert not lmf.is_lmf(datadir / 'missing.xml')
    assert lmf.is_lmf(datadir / 'mini-lmf-1.1.xml')


def test_load_1_0(mini_lmf_1_0):
    lexicons = lmf.load(mini_lmf_1_0)
    assert len(lexicons) == 2
    lexicon = lexicons[0]

    assert lexicon.id == 'test-en'
    assert lexicon.label == 'Testing English WordNet'
    assert lexicon.language == 'en'
    assert lexicon.email == 'maintainer@example.com'
    assert lexicon.license == 'https://creativecommons.org/licenses/by/4.0/'
    assert lexicon.version == '1'
    assert lexicon.url == 'https://example.com/test-en'

    assert len(lexicon.lexical_entries) == 9
    le = lexicon.lexical_entries[0]
    assert le.id == 'test-en-information-n'

    assert le.lemma.form == 'information'
    assert le.lemma.pos == 'n'
    assert le.lemma.script == 'Latn'
    assert len(le.lemma.tags) == 1

    assert len(le.forms) == 0

    assert len(le.senses) == 1
    assert le.senses[0].id == 'test-en-information-n-0001-01'
    assert le.senses[0].synset == 'test-en-0001-n'
    assert len(le.senses[0].relations) == 0
    # assert le.senses[0].relations[0].target == 'test-en-exemplify-v-01023137-01'
    # assert le.senses[0].relations[0].type == 'derivation'

    assert len(lexicon.syntactic_behaviours) == 2
    assert lexicon.syntactic_behaviours[0].frame == 'Somebody ----s something'
    assert lexicon.syntactic_behaviours[0].senses == ['test-en-illustrate-v-0004-01']

    assert len(lexicon.synsets) == 8

    assert lexicons[1].id == 'test-es'


def test_load_1_1(mini_lmf_1_1):
    lexicons = lmf.load(mini_lmf_1_1)
    assert len(lexicons) == 2
    lexicon = lexicons[0]
    assert lexicon.id == 'test-ja'
    assert lexicon.version == '1'
    # assert lexicon.logo == 'logo.svg'
    assert lexicon.requires == [{'id': 'test-en', 'version': '1', 'url': None}]

    lexicon = lexicons[1]
    assert lexicon.id == 'test-en-ext'
    assert lexicon.extends == {'id': 'test-en', 'version': '1', 'url': None}


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

    lmf.dump(lmf.load(mini_lmf_1_0), tmppath, version='1.0')
    assert_xml_equal(mini_lmf_1_0, tmppath)

    lmf.dump(lmf.load(mini_lmf_1_1), tmppath, version='1.1')
    assert_xml_equal(mini_lmf_1_1, tmppath)
