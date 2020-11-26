
import pytest

import wn


@pytest.mark.usefixtures('empty_db')
def test_lexicons_empty():
    assert len(wn.lexicons()) == 0


@pytest.mark.usefixtures('mini_db')
def test_lexicons_mini():
    assert len(wn.lexicons()) == 2
    assert all(isinstance(lex, wn.Lexicon) for lex in wn.lexicons())

    results = wn.lexicons(lgcode='en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lgcode='es')
    assert len(results) == 1 and results[0].language == 'es'
    # results = wn.lexicons(lgcode='pt')
    # assert len(results) == 0

    results = wn.lexicons(lexicon='*')
    assert len(results) == 2
    results = wn.lexicons(lexicon='test-en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:1')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:*')
    assert len(results) == 1 and results[0].language == 'en'
    # results = wn.lexicons(lexicon='test-pt')
    # assert len(results) == 0


@pytest.mark.usefixtures('empty_db')
def test_words_empty():
    assert len(wn.words()) == 0


@pytest.mark.usefixtures('mini_db')
def test_words_mini():
    assert len(wn.words()) == 10
    assert all(isinstance(w, wn.Word) for w in wn.words())

    words = wn.words('information')  # search lemma
    assert len(words) == 1
    assert words[0].lemma() == 'information'

    words = wn.words('exemplifies')  # search secondary form
    assert len(words) == 1
    assert words[0].lemma() == 'exemplify'

    assert len(wn.words(pos='n')) == 6
    assert all(w.pos == 'n' for w in wn.words(pos='n'))
    assert len(wn.words(pos='v')) == 4
    assert len(wn.words(pos='q')) == 0  # fake pos

    assert len(wn.words(lgcode='en')) == 5
    assert len(wn.words(lgcode='es')) == 5
    # assert len(wn.words(lgcode='pt')) == 0

    assert len(wn.words(lexicon='test-en')) == 5
    assert len(wn.words(lexicon='test-es')) == 5
    # assert len(wn.words(lexicon='test-pt')) == 0

    assert len(wn.words(lgcode='en', lexicon='test-en')) == 5
    # assert len(wn.words(lgcode='en', lexicon='test-es')) == 0
    assert len(wn.words(pos='v', lgcode='en')) == 2
    assert len(wn.words('information', lgcode='en')) == 1
    assert len(wn.words('information', lgcode='es')) == 0


@pytest.mark.usefixtures('empty_db')
def test_word_empty():
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n')


@pytest.mark.usefixtures('mini_db')
def test_word_mini():
    assert wn.word('test-es-información-n')
    assert wn.word('test-es-información-n', lgcode='es')
    assert wn.word('test-es-información-n', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lgcode='en')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lexicon='test-en')


@pytest.mark.usefixtures('empty_db')
def test_senses_empty():
    assert len(wn.senses()) == 0


@pytest.mark.usefixtures('mini_db')
def test_senses_mini():
    assert len(wn.senses()) == 10
    assert all(isinstance(s, wn.Sense) for s in wn.senses())

    senses = wn.senses('information')  # search lemma
    assert len(senses) == 1
    assert senses[0].word().lemma() == 'information'

    senses = wn.senses('exemplifies')  # search secondary form
    assert len(senses) == 1
    assert senses[0].word().lemma() == 'exemplify'

    assert len(wn.senses(pos='n')) == 6
    assert len(wn.senses(pos='v')) == 4
    assert len(wn.senses(pos='q')) == 0  # fake pos

    assert len(wn.senses(lgcode='en')) == 5
    assert len(wn.senses(lgcode='es')) == 5
    # assert len(wn.senses(lgcode='pt')) == 0

    assert len(wn.senses(lexicon='test-en')) == 5
    assert len(wn.senses(lexicon='test-es')) == 5
    # assert len(wn.senses(lexicon='test-pt')) == 0

    assert len(wn.senses(lgcode='en', lexicon='test-en')) == 5
    # assert len(wn.senses(lgcode='en', lexicon='test-es')) == 0
    assert len(wn.senses(pos='v', lgcode='en')) == 2
    assert len(wn.senses('information', lgcode='en')) == 1
    assert len(wn.senses('information', lgcode='es')) == 0


@pytest.mark.usefixtures('empty_db')
def test_sense_empty():
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01')


@pytest.mark.usefixtures('mini_db')
def test_sense_mini():
    assert wn.sense('test-es-información-n-0001-01')
    assert wn.sense('test-es-información-n-0001-01', lgcode='es')
    assert wn.sense('test-es-información-n-0001-01', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lgcode='en')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lexicon='test-en')


@pytest.mark.usefixtures('empty_db')
def test_synsets_empty():
    assert len(wn.synsets()) == 0


@pytest.mark.usefixtures('mini_db')
def test_synsets_mini():
    assert len(wn.synsets()) == 6
    assert all(isinstance(ss, wn.Synset) for ss in wn.synsets())

    synsets = wn.synsets('information')  # search lemma
    assert len(synsets) == 1
    assert 'information' in synsets[0].lemmas()

    synsets = wn.synsets('exemplifies')  # search secondary form
    assert len(synsets) == 1
    assert 'exemplify' in synsets[0].lemmas()

    assert len(wn.synsets(pos='n')) == 4
    assert len(wn.synsets(pos='v')) == 2
    assert len(wn.synsets(pos='q')) == 0  # fake pos

    assert len(wn.synsets(ili='i67469')) == 2
    assert len(wn.synsets(ili='i67468')) == 0

    assert len(wn.synsets(lgcode='en')) == 3
    assert len(wn.synsets(lgcode='es')) == 3
    # assert len(wn.synsets(lgcode='pt')) == 0

    assert len(wn.synsets(lexicon='test-en')) == 3
    assert len(wn.synsets(lexicon='test-es')) == 3
    # assert len(wn.synsets(lexicon='test-pt')) == 0

    assert len(wn.synsets(lgcode='en', lexicon='test-en')) == 3
    # assert len(wn.synsets(lgcode='en', lexicon='test-es')) == 0
    assert len(wn.synsets(pos='v', lgcode='en')) == 1
    assert len(wn.synsets('information', lgcode='en')) == 1
    assert len(wn.synsets('information', lgcode='es')) == 0
    assert len(wn.synsets(ili='i67469', lgcode='es')) == 1


@pytest.mark.usefixtures('empty_db')
def test_synset_empty():
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n')


@pytest.mark.usefixtures('mini_db')
def test_synset_mini():
    assert wn.synset('test-es-0001-n')
    assert wn.synset('test-es-0001-n', lgcode='es')
    assert wn.synset('test-es-0001-n', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lgcode='en')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lexicon='test-en')
