
import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_word_senses():
    assert len(wn.word('test-en-information-n').senses()) == 1
    assert len(wn.word('test-es-información-n').senses()) == 1


@pytest.mark.usefixtures('mini_db')
def test_word_synsets():
    assert len(wn.word('test-en-information-n').synsets()) == 1
    assert len(wn.word('test-es-información-n').synsets()) == 1


@pytest.mark.usefixtures('mini_db')
def test_word_translate():
    assert len(wn.word('test-en-example-n').translate(lang='es')) == 1
    assert len(wn.word('test-es-ejemplo-n').translate(lang='en')) == 1


@pytest.mark.usefixtures('mini_db')
def test_sense_word():
    assert (wn.sense('test-en-information-n-0001-01').word()
            == wn.word('test-en-information-n'))
    assert (wn.sense('test-es-información-n-0001-01').word()
            == wn.word('test-es-información-n'))


@pytest.mark.usefixtures('mini_db')
def test_sense_synset():
    assert (wn.sense('test-en-information-n-0001-01').synset()
            == wn.synset('test-en-0001-n'))
    assert (wn.sense('test-es-información-n-0001-01').synset()
            == wn.synset('test-es-0001-n'))


@pytest.mark.usefixtures('mini_db')
def test_sense_issue_157():
    # https://github.com/goodmami/wn/issues/157
    sense = wn.sense('test-en-information-n-0001-01')
    # This test uses non-public members, which is not ideal, but there
    # is currently no better alternative.
    assert sense._lexconf is sense.word()._lexconf
    assert sense._lexconf is sense.synset()._lexconf


@pytest.mark.usefixtures('mini_db')
def test_sense_examples():
    assert wn.sense('test-en-information-n-0001-01').examples() == []
    assert wn.sense('test-es-información-n-0001-01').examples() == []


@pytest.mark.usefixtures('mini_db')
def test_sense_lexicalized():
    assert wn.sense('test-en-information-n-0001-01').lexicalized()
    assert wn.sense('test-es-información-n-0001-01').lexicalized()


@pytest.mark.usefixtures('mini_db')
def test_sense_frames():
    assert wn.sense('test-en-illustrate-v-0003-01').frames() == [
        'Somebody ----s something',
        'Something ----s something',
    ]
    assert wn.sense('test-es-ilustrar-v-0003-01').frames() == []


@pytest.mark.usefixtures('mini_db_1_1')
def test_sense_frames_issue_156():
    # https://github.com/goodmami/wn/issues/156
    assert wn.sense('test-ja-示す-v-0003-01').frames() == [
        'ある人が何かを----',
    ]
    assert wn.sense('test-ja-事例-n-0002-01').frames() == []


@pytest.mark.usefixtures('mini_db')
def test_sense_translate():
    assert len(wn.sense('test-en-information-n-0001-01').translate(lang='es')) == 1
    assert len(wn.sense('test-es-información-n-0001-01').translate(lang='en')) == 1


@pytest.mark.usefixtures('mini_db')
def test_synset_senses():
    assert len(wn.synset('test-en-0003-v').senses()) == 2
    assert len(wn.synset('test-es-0003-v').senses()) == 2


@pytest.mark.usefixtures('mini_db')
def test_synset_words():
    assert len(wn.synset('test-en-0003-v').words()) == 2
    assert len(wn.synset('test-es-0003-v').words()) == 2


@pytest.mark.usefixtures('mini_db')
def test_synset_lemmas():
    assert wn.synset('test-en-0003-v').lemmas() == ['exemplify', 'illustrate']
    assert wn.synset('test-es-0003-v').lemmas() == ['ejemplificar', 'ilustrar']


@pytest.mark.usefixtures('mini_db')
def test_synset_ili():
    assert isinstance(wn.synset('test-en-0001-n').ili, wn.ILI)
    assert wn.synset('test-en-0001-n').ili.id == 'i67447'
    assert wn.synset('test-en-0001-n').ili.status == 'presupposed'
    assert wn.synset('test-en-0008-n').ili is None
    assert wn.synset('test-en-0007-v').ili.id is None
    assert wn.synset('test-en-0007-v').ili.status == 'proposed'


@pytest.mark.usefixtures('mini_db')
def test_synset_definition():
    assert wn.synset('test-en-0001-n').definition() == 'something that informs'
    defn = wn.synset('test-en-0001-n').definition(data=True)
    assert defn.source_sense_id == 'test-en-information-n-0001-01'
    assert wn.synset('test-es-0001-n').definition() == 'algo que informa'


@pytest.mark.usefixtures('mini_db')
def test_synset_definitions():
    assert wn.synset('test-en-0001-n').definitions() == ['something that informs']
    defns = wn.synset('test-en-0001-n').definitions(data=True)
    assert defns[0].source_sense_id == 'test-en-information-n-0001-01'
    assert wn.synset('test-es-0001-n').definitions() == ['algo que informa']


@pytest.mark.usefixtures('mini_db')
def test_synset_examples():
    assert wn.synset('test-en-0001-n').examples() == ['"this is information"']
    ex = wn.synset('test-en-0001-n').examples(data=True)[0]
    assert ex.text == '"this is information"'
    assert wn.synset('test-es-0001-n').examples() == ['"este es la información"']


@pytest.mark.usefixtures('mini_db')
def test_synset_lexicalized():
    assert wn.synset('test-en-0001-n').lexicalized()
    assert wn.synset('test-es-0001-n').lexicalized()


@pytest.mark.usefixtures('mini_db')
def test_synset_translate():
    assert len(wn.synset('test-en-0001-n').translate(lang='es')) == 1
    assert len(wn.synset('test-es-0001-n').translate(lang='en')) == 1
