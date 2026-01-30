import pytest

import wn


@pytest.mark.usefixtures("mini_db")
def test_word_senses():
    assert len(wn.word("test-en-information-n").senses()) == 1
    assert len(wn.word("test-es-información-n").senses()) == 1


@pytest.mark.usefixtures("mini_db")
def test_word_synsets():
    assert len(wn.word("test-en-information-n").synsets()) == 1
    assert len(wn.word("test-es-información-n").synsets()) == 1


@pytest.mark.usefixtures("mini_db")
def test_word_translate():
    assert len(wn.word("test-en-example-n").translate(lang="es")) == 1
    assert len(wn.word("test-es-ejemplo-n").translate(lang="en")) == 1


@pytest.mark.usefixtures("mini_db_1_1")
def test_word_lemma_tags():
    en = wn.Wordnet("test-en")
    assert en.word("test-en-exemplify-v").lemma(data=True).tags() == []
    ext = wn.Wordnet("test-en test-en-ext")
    assert ext.word("test-en-exemplify-v").lemma(data=True).tags() == [
        wn.Tag(tag="INF", category="tense")
    ]


@pytest.mark.usefixtures("mini_db_1_1")
def test_word_lemma_pronunciations():
    en = wn.Wordnet("test-en")
    assert en.word("test-en-information-n").lemma(data=True).pronunciations() == []
    ext = wn.Wordnet("test-en test-en-ext")
    assert ext.word("test-en-information-n").lemma(data=True).pronunciations() == [
        wn.Pronunciation(value="ˌɪnfəˈmeɪʃən", variety="GB"),  # noqa: RUF001
        wn.Pronunciation(value="ˌɪnfɚˈmeɪʃən", variety="US"),  # noqa: RUF001
    ]


@pytest.mark.usefixtures("mini_db")
def test_sense_word():
    assert wn.sense("test-en-information-n-0001-01").word() == wn.word(
        "test-en-information-n"
    )
    assert wn.sense("test-es-información-n-0001-01").word() == wn.word(
        "test-es-información-n"
    )


@pytest.mark.usefixtures("mini_db")
def test_sense_synset():
    assert wn.sense("test-en-information-n-0001-01").synset() == wn.synset(
        "test-en-0001-n"
    )
    assert wn.sense("test-es-información-n-0001-01").synset() == wn.synset(
        "test-es-0001-n"
    )


@pytest.mark.usefixtures("mini_db")
def test_sense_issue_157():
    # https://github.com/goodmami/wn/issues/157
    sense = wn.sense("test-en-information-n-0001-01")
    # This test uses non-public members, which is not ideal, but there
    # is currently no better alternative.
    assert sense._lexconf is sense.word()._lexconf
    assert sense._lexconf is sense.synset()._lexconf


@pytest.mark.usefixtures("mini_db")
def test_sense_examples():
    assert wn.sense("test-en-information-n-0001-01").examples() == []
    assert wn.sense("test-es-información-n-0001-01").examples() == []


@pytest.mark.usefixtures("mini_db")
def test_sense_counts():
    assert wn.sense("test-en-information-n-0001-01").counts() == [3]
    counts = wn.sense("test-en-information-n-0001-01").counts(data=True)
    assert counts[0].value == 3
    assert counts[0].lexicon().specifier() == "test-en:1"
    assert wn.sense("test-es-información-n-0001-01").counts() == []


@pytest.mark.usefixtures("mini_db")
def test_sense_lexicalized():
    assert wn.sense("test-en-information-n-0001-01").lexicalized()
    assert wn.sense("test-es-información-n-0001-01").lexicalized()


@pytest.mark.usefixtures("mini_db")
def test_sense_frames():
    assert wn.sense("test-en-illustrate-v-0003-01").frames() == [
        "Somebody ----s something",
        "Something ----s something",
    ]
    assert wn.sense("test-es-ilustrar-v-0003-01").frames() == []


@pytest.mark.usefixtures("mini_db_1_1")
def test_sense_frames_issue_156():
    # https://github.com/goodmami/wn/issues/156
    assert wn.sense("test-ja-示す-v-0003-01").frames() == [
        "ある人が何かを----",
    ]
    assert wn.sense("test-ja-事例-n-0002-01").frames() == []


@pytest.mark.usefixtures("mini_db")
def test_sense_translate():
    assert len(wn.sense("test-en-information-n-0001-01").translate(lang="es")) == 1
    assert len(wn.sense("test-es-información-n-0001-01").translate(lang="en")) == 1


@pytest.mark.usefixtures("mini_db")
def test_synset_senses():
    assert len(wn.synset("test-en-0003-v").senses()) == 2
    assert len(wn.synset("test-es-0003-v").senses()) == 2


@pytest.mark.usefixtures("mini_db")
def test_synset_words():
    assert len(wn.synset("test-en-0003-v").words()) == 2
    assert len(wn.synset("test-es-0003-v").words()) == 2


@pytest.mark.usefixtures("mini_db")
def test_synset_lemmas():
    assert wn.synset("test-en-0003-v").lemmas() == ["exemplify", "illustrate"]
    assert wn.synset("test-es-0003-v").lemmas() == ["ejemplificar", "ilustrar"]


@pytest.mark.usefixtures("mini_db")
def test_synset_ili():
    # Synset ILIs are now just strings; see ili_test.py for wn.ili tests
    assert isinstance(wn.synset("test-en-0001-n").ili, str)


@pytest.mark.usefixtures("mini_db")
def test_synset_definition():
    assert wn.synset("test-en-0001-n").definition() == "something that informs"
    defn = wn.synset("test-en-0001-n").definition(data=True)
    assert defn.source_sense_id == "test-en-information-n-0001-01"
    assert defn.lexicon().specifier() == "test-en:1"
    assert wn.synset("test-es-0001-n").definition() == "algo que informa"


@pytest.mark.usefixtures("mini_db")
def test_synset_definitions():
    assert wn.synset("test-en-0001-n").definitions() == ["something that informs"]
    defns = wn.synset("test-en-0001-n").definitions(data=True)
    assert defns[0].source_sense_id == "test-en-information-n-0001-01"
    assert wn.synset("test-es-0001-n").definitions() == ["algo que informa"]


@pytest.mark.usefixtures("mini_db")
def test_synset_examples():
    assert wn.synset("test-en-0001-n").examples() == ['"this is information"']
    ex = wn.synset("test-en-0001-n").examples(data=True)[0]
    assert ex.text == '"this is information"'
    assert ex.lexicon().specifier() == "test-en:1"
    assert wn.synset("test-es-0001-n").examples() == ['"este es la información"']


@pytest.mark.usefixtures("mini_db")
def test_synset_lexicalized():
    assert wn.synset("test-en-0001-n").lexicalized()
    assert wn.synset("test-es-0001-n").lexicalized()


@pytest.mark.usefixtures("mini_db")
def test_synset_translate():
    assert len(wn.synset("test-en-0001-n").translate(lang="es")) == 1
    assert len(wn.synset("test-es-0001-n").translate(lang="en")) == 1


@pytest.mark.usefixtures("uninitialized_datadir")
def test_word_sense_order(datadir):
    wn.add(datadir / "sense-member-order.xml")
    assert [s.id for s in wn.word("test-foo-n").senses()] == [
        "test-01-foo-n",
        "test-02-foo-n",
    ]
    assert [s.id for s in wn.word("test-bar-n").senses()] == [
        "test-02-bar-n",
        "test-01-bar-n",
    ]


@pytest.mark.usefixtures("uninitialized_datadir")
def test_synset_member_order(datadir):
    wn.add(datadir / "sense-member-order.xml")
    assert [s.id for s in wn.synset("test-01-n").senses()] == [
        "test-01-bar-n",
        "test-01-foo-n",
    ]
    assert [s.id for s in wn.synset("test-02-n").senses()] == [
        "test-02-bar-n",
        "test-02-foo-n",
    ]


@pytest.mark.usefixtures("mini_db")
def test_confidence():
    # default for unmarked lexicon is 1.0
    assert wn.lexicons(lexicon="test-es")[0].confidence() == 1.0
    # explicitly set lexicon confidence becomes the default for sub-elements
    assert wn.lexicons(lexicon="test-en")[0].confidence() == 0.9
    assert wn.word("test-en-information-n").confidence() == 0.9
    assert wn.sense("test-en-information-n-0001-01").confidence() == 0.9
    assert (
        wn.sense("test-en-information-n-0001-01").counts(data=True)[0].confidence()
    ) == 0.9
    assert (
        wn.sense("test-en-exemplify-v-0003-01")
        .relations(data=True)
        .popitem()[0]
        .confidence()
    ) == 0.9
    # explicit value overrides default
    assert wn.word("test-en-example-n").confidence() == 1.0
    assert (
        wn.sense("test-en-example-n-0002-01")
        .relations(data=True)
        .popitem()[0]
        .confidence()
    ) == 0.5
    # values on parents don't override default on children
    assert wn.sense("test-en-example-n-0002-01").confidence() == 0.9
    # check values on other elements
    assert wn.synset("test-en-0001-n").confidence() == 1.0
    assert wn.synset("test-en-0001-n").definition(data=True).confidence() == 0.95
    assert (
        wn.synset("test-en-0001-n").relations(data=True).popitem()[0].confidence()
    ) == 0.8
    assert wn.synset("test-en-0001-n").examples(data=True)[0].confidence() == 0.7
