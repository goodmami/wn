
import pytest

import wn


@pytest.mark.usefixtures('empty_db')
def test_lexicons_empty():
    assert len(wn.lexicons()) == 0


@pytest.mark.usefixtures('mini_db')
def test_lexicons_mini():
    assert len(wn.lexicons()) == 2
    assert all(isinstance(lex, wn.Lexicon) for lex in wn.lexicons())

    results = wn.lexicons(lang='en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lang='es')
    assert len(results) == 1 and results[0].language == 'es'

    results = wn.lexicons(lexicon='*')
    assert len(results) == 2
    results = wn.lexicons(lexicon='*:1')
    assert len(results) == 2
    results = wn.lexicons(lexicon='test-en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:1')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:*')
    assert len(results) == 1 and results[0].language == 'en'

    assert wn.lexicons(lexicon='test-en')[0].specifier() == 'test-en:1'
    assert wn.lexicons(lexicon='test-es')[0].specifier() == 'test-es:1'

    assert wn.lexicons(lexicon='test-en')[0].requires() == {}
    assert wn.lexicons(lexicon='test-es')[0].requires() == {}


@pytest.mark.usefixtures('mini_db')
def test_lexicons_unknown():
    results = wn.lexicons(lang='unk')
    assert len(results) == 0
    results = wn.lexicons(lexicon='test-unk')
    assert len(results) == 0


@pytest.mark.usefixtures('empty_db')
def test_words_empty():
    assert len(wn.words()) == 0


@pytest.mark.usefixtures('mini_db')
def test_words_mini():
    assert len(wn.words()) == 15
    assert all(isinstance(w, wn.Word) for w in wn.words())

    words = wn.words('information')  # search lemma
    assert len(words) == 1
    assert words[0].lemma() == 'information'

    assert words[0].lemma().script == 'Latn'
    assert words[0].lemma().tags() == [wn.Tag('tag-text', 'tag-category')]

    words = wn.words('exemplifies')  # search secondary form
    assert len(words) == 1
    assert words[0].lemma() == 'exemplify'

    assert len(wn.words(pos='n')) == 10
    assert all(w.pos == 'n' for w in wn.words(pos='n'))
    assert len(wn.words(pos='v')) == 5
    assert len(wn.words(pos='q')) == 0  # fake pos

    assert len(wn.words(lang='en')) == 9
    assert len(wn.words(lang='es')) == 6

    assert len(wn.words(lexicon='test-en')) == 9
    assert len(wn.words(lexicon='test-es')) == 6

    assert len(wn.words(lang='en', lexicon='test-en')) == 9
    assert len(wn.words(pos='v', lang='en')) == 3
    assert len(wn.words('information', lang='en')) == 1
    assert len(wn.words('information', lang='es')) == 0

    with pytest.raises(wn.Error):
        wn.words(lang='unk')
    with pytest.raises(wn.Error):
        wn.words(lexicon='test-unk')


@pytest.mark.usefixtures('empty_db')
def test_word_empty():
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n')


@pytest.mark.usefixtures('mini_db')
def test_word_mini():
    assert wn.word('test-es-información-n')
    assert wn.word('test-es-información-n', lang='es')
    assert wn.word('test-es-información-n', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lang='en')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lexicon='test-en')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lang='unk')
    with pytest.raises(wn.Error):
        assert wn.word('test-es-información-n', lexicon='test-unk')


@pytest.mark.usefixtures('empty_db')
def test_senses_empty():
    assert len(wn.senses()) == 0


@pytest.mark.usefixtures('mini_db')
def test_senses_mini():
    assert len(wn.senses()) == 16
    assert all(isinstance(s, wn.Sense) for s in wn.senses())

    senses = wn.senses('information')  # search lemma
    assert len(senses) == 1
    assert senses[0].word().lemma() == 'information'
    assert senses[0].counts() == [3]

    senses = wn.senses('exemplifies')  # search secondary form
    assert len(senses) == 1
    assert senses[0].word().lemma() == 'exemplify'

    assert len(wn.senses(pos='n')) == 11
    assert len(wn.senses(pos='v')) == 5
    assert len(wn.senses(pos='q')) == 0  # fake pos

    assert len(wn.senses(lang='en')) == 10
    assert len(wn.senses(lang='es')) == 6

    assert len(wn.senses(lexicon='test-en')) == 10
    assert len(wn.senses(lexicon='test-es')) == 6

    assert len(wn.senses(lang='en', lexicon='test-en')) == 10
    assert len(wn.senses(pos='v', lang='en')) == 3
    assert len(wn.senses('information', lang='en')) == 1
    assert len(wn.senses('information', lang='es')) == 0

    with pytest.raises(wn.Error):
        wn.senses(lang='unk')
    with pytest.raises(wn.Error):
        wn.senses(lexicon='test-unk')


@pytest.mark.usefixtures('empty_db')
def test_sense_empty():
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01')


@pytest.mark.usefixtures('mini_db')
def test_sense_mini():
    assert wn.sense('test-es-información-n-0001-01')
    assert wn.sense('test-es-información-n-0001-01', lang='es')
    assert wn.sense('test-es-información-n-0001-01', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lang='en')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lexicon='test-en')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lang='unk')
    with pytest.raises(wn.Error):
        assert wn.sense('test-es-información-n-0001-01', lexicon='test-unk')


@pytest.mark.usefixtures('empty_db')
def test_synsets_empty():
    assert len(wn.synsets()) == 0


@pytest.mark.usefixtures('mini_db')
def test_synsets_mini():
    assert len(wn.synsets()) == 12
    assert all(isinstance(ss, wn.Synset) for ss in wn.synsets())

    synsets = wn.synsets('information')  # search lemma
    assert len(synsets) == 1
    assert 'information' in synsets[0].lemmas()

    synsets = wn.synsets('exemplifies')  # search secondary form
    assert len(synsets) == 1
    assert 'exemplify' in synsets[0].lemmas()

    assert len(wn.synsets(pos='n')) == 9
    assert len(wn.synsets(pos='v')) == 3
    assert len(wn.synsets(pos='q')) == 0  # fake pos

    assert len(wn.synsets(ili='i67469')) == 2
    assert len(wn.synsets(ili='i67468')) == 0

    assert len(wn.synsets(lang='en')) == 8
    assert len(wn.synsets(lang='es')) == 4

    assert len(wn.synsets(lexicon='test-en')) == 8
    assert len(wn.synsets(lexicon='test-es')) == 4

    assert len(wn.synsets(lang='en', lexicon='test-en')) == 8
    assert len(wn.synsets(pos='v', lang='en')) == 2
    assert len(wn.synsets('information', lang='en')) == 1
    assert len(wn.synsets('information', lang='es')) == 0
    assert len(wn.synsets(ili='i67469', lang='es')) == 1

    with pytest.raises(wn.Error):
        wn.synsets(lang='unk')
    with pytest.raises(wn.Error):
        wn.synsets(lexicon='test-unk')


@pytest.mark.usefixtures('empty_db')
def test_synset_empty():
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n')


@pytest.mark.usefixtures('mini_db')
def test_synset_mini():
    assert wn.synset('test-es-0001-n')
    assert wn.synset('test-es-0001-n', lang='es')
    assert wn.synset('test-es-0001-n', lexicon='test-es')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lang='en')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lexicon='test-en')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lang='unk')
    with pytest.raises(wn.Error):
        assert wn.synset('test-es-0001-n', lexicon='test-unk')


@pytest.mark.usefixtures('mini_db_1_1')
def test_mini_1_1():
    assert len(wn.lexicons()) == 4
    assert len(wn.lexicons(lang='en')) == 2
    assert len(wn.lexicons(lang='ja')) == 1
    assert wn.lexicons(lang='ja')[0].logo == 'logo.svg'

    w = wn.Wordnet(lang='en')
    assert len(w.lexicons()) == 2
    assert len(w.expanded_lexicons()) == 0
    assert len(w.word('test-en-exemplify-v').lemma().tags()) == 1

    w = wn.Wordnet(lang='ja')
    assert len(w.lexicons()) == 1
    assert len(w.expanded_lexicons()) == 1
    assert len(w.synsets('例え')[0].hypernyms()) == 1
    assert w.synsets('例え')[0].lexfile() == 'noun.cognition'
    assert len(w.word('test-ja-例え-n').lemma().pronunciations()) == 1
    assert w.word('test-ja-例え-n').forms()[1].id == 'test-ja-例え-n-たとえ'
    p = w.word('test-ja-例え-n').lemma().pronunciations()[0]
    assert p.value == 'tatoe'
    assert p.variety == 'standard'
    assert p.notation == 'ipa'
    assert p.phonemic
    assert p.audio == 'tatoe.wav'

    w = wn.Wordnet(lang='ja', expand='')
    assert len(w.lexicons()) == 1
    assert len(w.expanded_lexicons()) == 0
    assert len(w.synsets('例え')[0].hypernyms()) == 0

    w = wn.Wordnet(lexicon='test-en test-en-ext')
    assert len(w.lexicons()) == 2
    assert len(w.expanded_lexicons()) == 0
    assert len(w.synsets('fire')[0].hyponyms()) == 1
