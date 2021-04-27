
import pytest

import wn


@pytest.mark.usefixtures('mini_db_1_1')
def test_wordnet_lexicons():
    en = wn.Wordnet('test-en')
    assert len(en.lexicons()) == 1
    assert len(en.expanded_lexicons()) == 0

    en1 = wn.Wordnet('test-en:1')
    assert en.lexicons() == en1.lexicons()
    assert en.expanded_lexicons() == en1.expanded_lexicons()

    en2 = wn.Wordnet(lang='en')
    assert len(en2.lexicons()) == 2
    assert len(en2.expanded_lexicons()) == 0

    es = wn.Wordnet('test-es')
    assert len(es.lexicons()) == 1
    assert len(es.expanded_lexicons()) == 0

    es2 = wn.Wordnet('test-es', expand='test-en')
    assert len(es2.lexicons()) == 1
    assert len(es2.expanded_lexicons()) == 1

    ja = wn.Wordnet('test-ja')
    assert len(ja.lexicons()) == 1
    assert len(ja.expanded_lexicons()) == 1

    ja2 = wn.Wordnet('test-ja', expand='')
    assert len(ja2.lexicons()) == 1
    assert len(ja2.expanded_lexicons()) == 0


@pytest.mark.usefixtures('mini_db')
def test_wordnet_normalize():
    es = wn.Wordnet('test-es')
    assert es.words('Informacion') == es.words('información')
    assert es.words('ínfórmácíón') == es.words('información')
    es = wn.Wordnet('test-es', normalizer=None)
    assert es.words('informacion') == []
    assert es.words('Información') == []

    # The following doesn't necessarily work because any non-None
    # normalizer causes the normalized form column to be tested with
    # the original form
    # es = wn.Wordnet('test-es', normalizer=str.lower)
    # assert es.words('informacion') == []
    # assert es.words('Información') == es.words('información')


@pytest.mark.usefixtures('mini_db')
def test_wordnet_lemmatize():
    # default lemmatizer compares alternative forms
    en = wn.Wordnet('test-en')
    assert en.words('examples') == []
    assert en.words('exemplifying') == en.words('exemplify')
    assert en.words('data') == en.words('datum')

    en = wn.Wordnet('test-en', lemmatizer_class=None)
    assert en.words('examples') == []
    assert en.words('exemplifying') == []
    assert en.words('data') == []

    en = wn.Wordnet('test-en')
    en.lemmatizer = None
    assert en.words('examples') == []
    assert en.words('exemplifying') == []
    assert en.words('data') == []
