
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
        wn.synset('test-es-0001-n')
    ]
