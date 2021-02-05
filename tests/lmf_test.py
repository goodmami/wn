
from xml.etree import ElementTree as ET

from wn import lmf


class TestLexicon:

    def test_entry_ids(self):
        lex = lmf.Lexicon(
            'id', 'Test', 'tst', 'test@example.com', 'CC-BY 4.0', '1',
            lexical_entries=[],
            synsets=[])
        assert lex.entry_ids() == set()


def test_is_lmf(datadir):
    assert lmf.is_lmf(datadir / 'mini-lmf-1.0.xml')
    assert lmf.is_lmf(str(datadir / 'mini-lmf-1.0.xml'))
    assert not lmf.is_lmf(datadir / 'README.md')
    assert not lmf.is_lmf(datadir / 'missing.xml')


def test_load(mini_lmf_1_0):
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

    assert len(lexicon.lexical_entries) == 8
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

    assert len(lexicon.synsets) == 6

    assert lexicons[1].id == 'test-es'


def test_dump(mini_lmf_1_0, tmp_path):
    lexicons = lmf.load(mini_lmf_1_0)
    tmpdir = tmp_path / 'test_dump'
    tmpdir.mkdir()
    tmppath = tmpdir / 'mini_lmf_dump.xml'
    lmf.dump(lexicons, tmppath)
    if hasattr(ET, 'canonicalize'):  # available from Python 3.8
        orig = ET.canonicalize(from_file=mini_lmf_1_0, strip_text=True)
        temp = ET.canonicalize(from_file=tmppath, strip_text=True)
        assert orig == temp
