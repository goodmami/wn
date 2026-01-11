from pathlib import Path

import pytest

import wn
from wn import ili

I67447_DEFN = "knowledge acquired through study or experience or instruction"


def test_is_ili_tsv(datadir: Path) -> None:
    assert ili.is_ili_tsv(datadir / "mini-ili.tsv")
    assert ili.is_ili_tsv(datadir / "mini-ili-with-status.tsv")
    assert not ili.is_ili_tsv(datadir / "mini-lmf-1.0.xml")
    assert not ili.is_ili_tsv(datadir / "does-not-exist")


def test_load_tsv(datadir: Path) -> None:
    assert list(ili.load_tsv(datadir / "mini-ili.tsv")) == [
        {"ili": "i1", "definition": "i1 definition"},
        {"ili": "i2", "definition": ""},
        {"ili": "i67447", "definition": I67447_DEFN},
    ]
    assert list(ili.load_tsv(datadir / "mini-ili-with-status.tsv")) == [
        {"ili": "i1", "definition": "i1 definition", "status": "active"},
        {"ili": "i2", "definition": "", "status": "deprecated"},
        {"ili": "i67447", "definition": I67447_DEFN, "status": "active"},
    ]


@pytest.mark.usefixtures("mini_db")
def test_get() -> None:
    # present in ili file, not in lexicon
    i = ili.get("i1")
    assert i.id == "i1"
    assert i.status == ili.ILIStatus.ACTIVE
    assert i.definition() == "i1 definition"
    defn = i.definition(data=True)
    assert defn.text == "i1 definition"
    assert defn.metadata() == {}
    assert defn.confidence() == 1.0
    # present in lexicon, not in ili file
    i = ili.get("i67469")
    assert i.id == "i67469"
    assert i.status == ili.ILIStatus.PRESUPPOSED
    assert i.definition() is None
    assert i.definition(data=True) is None
    # present in ili file and lexicon
    i = ili.get("i67447")
    assert i.id == "i67447"
    assert i.status == ili.ILIStatus.ACTIVE
    assert i.definition() == I67447_DEFN
    defn = i.definition(data=True)
    assert defn.text == I67447_DEFN
    assert defn.metadata() == {}
    assert defn.confidence() == 1.0


@pytest.mark.usefixtures("mini_db")
def test_get_proposed() -> None:
    proposed_defn = "to fire someone while making it look like it was their idea"
    # synset with proposed ili
    ss = wn.synset("test-en-0007-v", lexicon="test-en")
    i = ili.get_proposed(ss)
    assert i is not None
    assert i.id is None
    assert i.synset() == ss
    assert i.status == ili.ILIStatus.PROPOSED
    assert i.lexicon() == ss.lexicon()
    assert i.definition() == proposed_defn
    defn = i.definition(data=True)
    assert defn.text == proposed_defn
    assert defn.metadata() == {"creator": "MM"}
    assert defn.confidence() == 0.9  # inherited from lexicon

    # synset without proposed ili
    ss = wn.synset("test-en-0006-n", lexicon="test-en")
    assert ili.get_proposed(ss) is None
