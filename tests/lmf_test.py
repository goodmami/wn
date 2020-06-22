
from wn import lmf


def test_load(test_en_lmf):
    lexicons = lmf.load(test_en_lmf)
    assert len(lexicons) == 1
    lexicon = lexicons[0]

    assert lexicon.id == 'test-en'
    assert lexicon.label == 'Testing English WordNet'
    assert lexicon.language == 'en'
    assert lexicon.email == 'maintainer@example.com'
    assert lexicon.license == 'https://creativecommons.org/licenses/by/4.0/'
    assert lexicon.version == '1'
    assert lexicon.url == 'https://example.com/test-en'

    assert len(lexicon.lexical_entries) == 1
    le = lexicon.lexical_entries[0]
    assert le.id == 'test-en-example-n'

    assert le.lemma.form == 'example'
    assert le.lemma.pos == 'n'
    assert le.lemma.script is None
    assert len(le.lemma.tags) == 0

    assert len(le.forms) == 0

    assert len(le.senses) == 1
    assert le.senses[0].id == 'test-en-example-n-05828980-01'
    assert le.senses[0].synset == 'test-en-05828980-n'
    assert len(le.senses[0].relations) == 1
    assert le.senses[0].relations[0].target == 'test-en-exemplify-v-01023137-01'
    assert le.senses[0].relations[0].type == 'derivation'

    assert len(lexicon.synsets) == 2
