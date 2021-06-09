
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
