
import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_word_derived_words():
    assert len(wn.word('test-en-example-n').derived_words()) == 1
    assert len(wn.word('test-es-ejemplo-n').derived_words()) == 1


@pytest.mark.usefixtures('mini_db')
def test_synset_hypernyms():
    assert wn.synset('test-en-0002-n').hypernyms() == [
        wn.synset('test-en-0001-n')
    ]
    assert wn.synset('test-en-0001-n').hypernyms() == []


@pytest.mark.usefixtures('mini_db')
def test_synset_hypernyms_expand_default():
    assert wn.synset('test-es-0002-n').hypernyms() == [
        wn.synset('test-es-0001-n')
    ]
    assert wn.synset('test-es-0001-n').hypernyms() == []


@pytest.mark.usefixtures('mini_db')
def test_synset_hypernyms_expand_empty():
    w = wn.Wordnet(lang='es', expand='')
    assert w.synset('test-es-0002-n').hypernyms() == []


@pytest.mark.usefixtures('mini_db')
def test_synset_hypernyms_expand_specified():
    w = wn.Wordnet(lang='es', expand='test-en')
    assert w.synset('test-es-0002-n').hypernyms() == [
        w.synset('test-es-0001-n')
    ]


@pytest.mark.usefixtures('mini_db')
def test_synset_relations():
    w = wn.Wordnet(lang='en')
    assert w.synset('test-en-0002-n').relations() == {
        'hypernym': [w.synset('test-en-0001-n')],
        'hyponym': [w.synset('test-en-0004-n')]
    }


@pytest.mark.usefixtures('mini_db')
def test_sense_get_related():
    w = wn.Wordnet('test-en')
    assert w.sense('test-en-example-n-0002-01').get_related() == [
        w.sense('test-en-exemplify-v-0003-01')
    ]


@pytest.mark.usefixtures('mini_db')
def test_sense_relations():
    w = wn.Wordnet('test-en')
    assert w.sense('test-en-example-n-0002-01').relations() == {
        'derivation': [w.sense('test-en-exemplify-v-0003-01')]
    }


@pytest.mark.usefixtures('mini_db_1_1')
def test_extension_relations():
    # default mode
    assert wn.synset('test-en-0007-v').hypernyms() == [
        wn.synset('test-en-ext-0009-v')
    ]
    assert wn.synset('test-en-ext-0009-v').hyponyms() == [
        wn.synset('test-en-0007-v')
    ]
    assert wn.sense('test-en-information-n-0001-01').get_related('pertainym') == [
        wn.sense('test-en-ext-info-n-0001-01')
    ]
    assert wn.sense('test-en-ext-info-n-0001-01').get_related('pertainym') == [
        wn.sense('test-en-information-n-0001-01')
    ]

    # restricted to base
    w = wn.Wordnet(lexicon='test-en')
    assert w.synset('test-en-0007-v').hypernyms() == []
    assert w.sense('test-en-information-n-0001-01').get_related('pertainym') == []

    # base and extension
    w = wn.Wordnet(lexicon='test-en test-en-ext')
    assert w.synset('test-en-0007-v').hypernyms() == [
        w.synset('test-en-ext-0009-v')
    ]
    assert w.synset('test-en-ext-0009-v').hyponyms() == [
        w.synset('test-en-0007-v')
    ]
    assert w.sense('test-en-information-n-0001-01').get_related('pertainym') == [
        w.sense('test-en-ext-info-n-0001-01')
    ]
    assert w.sense('test-en-ext-info-n-0001-01').get_related('pertainym') == [
        w.sense('test-en-information-n-0001-01')
    ]

    # restricted to extension
    w = wn.Wordnet(lexicon='test-en-ext')
    assert w.synset('test-en-ext-0009-v').hyponyms() == []
    assert w.sense('test-en-ext-info-n-0001-01').get_related('pertainym') == []


@pytest.mark.usefixtures('mini_db_1_1')
def test_sense_synset_issue_168():
    # https://github.com/goodmami/wn/issues/168
    ja = wn.Wordnet(lexicon='test-ja', expand='')
    assert ja.synset('test-ja-0001-n').get_related() == []
    assert ja.sense('test-ja-情報-n-0001-01').synset().get_related() == []


@pytest.mark.usefixtures('mini_db')
def test_synset_relations_issue_169():
    # https://github.com/goodmami/wn/issues/169
    en = wn.Wordnet('test-en')
    assert list(en.synset("test-en-0001-n").relations('hyponym')) == ['hyponym']
    es = wn.Wordnet('test-es', expand='test-en')
    assert list(es.synset("test-es-0001-n").relations('hyponym')) == ['hyponym']


@pytest.mark.usefixtures('mini_db')
def test_synset_relations_issue_177():
    # https://github.com/goodmami/wn/issues/177
    assert 'hyponym' in wn.synset('test-es-0001-n').relations()


@pytest.mark.usefixtures('mini_db')
def test_sense_relation_map():
    en = wn.Wordnet('test-en')
    assert en.sense('test-en-information-n-0001-01').relation_map() == {}
    relmap = en.sense('test-en-illustrate-v-0003-01').relation_map()
    # only sense-sense relations by default
    assert len(relmap) == 3
    assert all(isinstance(tgt, wn.Sense) for tgt in relmap.values())
    assert {rel.name for rel in relmap} == {'derivation', 'other'}
    assert {rel.target_id for rel in relmap} == {'test-en-illustration-n-0002-01'}
    # sense relations targets should always have same ids as resolved targets
    assert all(rel.target_id == tgt.id for rel, tgt in relmap.items())


@pytest.mark.usefixtures('mini_db')
def test_synset_relation_map():
    en = wn.Wordnet('test-en')
    assert en.synset('test-en-0003-v').relation_map() == {}
    relmap = en.synset('test-en-0002-n').relation_map()
    assert len(relmap) == 2
    assert {rel.name for rel in relmap} == {'hypernym', 'hyponym'}
    assert {rel.target_id for rel in relmap} == {'test-en-0001-n', 'test-en-0004-n'}
    # synset relation targets have same ids as resolved targets in same lexicon
    assert all(rel.target_id == tgt.id for rel, tgt in relmap.items())
    assert all(rel.lexicon().id == 'test-en' for rel in relmap)

    # interlingual synset relation targets show original target ids
    es = wn.Wordnet('test-es', expand='test-en')
    relmap = es.synset('test-es-0002-n').relation_map()
    assert len(relmap) == 2
    assert {rel.name for rel in relmap} == {'hypernym', 'hyponym'}
    assert {rel.target_id for rel in relmap} == {'test-en-0001-n', 'test-en-0004-n'}
    assert all(rel.target_id != tgt.id for rel, tgt in relmap.items())
    assert all(rel.lexicon().id == 'test-en' for rel in relmap)
