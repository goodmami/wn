import tempfile
from collections.abc import Iterator
from itertools import product, cycle
from pathlib import Path

import pytest

import wn
from wn import lmf


@pytest.fixture
def clean_db():

    def clean_db():
        wn.remove("*")
        dummy_lex = lmf.Lexicon(
            id="dummy",
            version="1",
            label="placeholder to initialize the db",
            language="zxx",
            email="",
            license="",
        )
        wn.add_lexical_resource(
            lmf.LexicalResource(lmf_version="1.3", lexicons=[dummy_lex])
        )

    return clean_db


@pytest.fixture(scope="session")
def datadir():
    return Path(__file__).parent.parent / "tests" / "data"


@pytest.fixture
def empty_db(clean_db):
    with tempfile.TemporaryDirectory('wn_data_empty') as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            clean_db()
            yield


@pytest.fixture(scope="session")
def mock_lmf():
    synsets: list[lmf.Synset] = [
       * _make_synsets("n", 20000),
       * _make_synsets("v", 10000),
       * _make_synsets("a", 2000),
       * _make_synsets("r", 1000),
    ]
    entries = _make_entries(synsets)
    lexicon = lmf.Lexicon(
        id="mock",
        version="1",
        label="",
        language="zxx",
        email="",
        license="",
        entries=entries,
        synsets=synsets,
    )
    return lmf.LexicalResource(lmf_version="1.3", lexicons=[lexicon])


@pytest.fixture(scope="session")
def mock_db_dir(mock_lmf):
    with tempfile.TemporaryDirectory("wn_data_empty") as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            wn.add_lexical_resource(mock_lmf, progress_handler=None)
            wn._db.clear_connections()

        yield Path(dir)


@pytest.fixture
def mock_db(monkeypatch, mock_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, "data_directory", mock_db_dir)
        yield
        wn._db.clear_connections()


def _make_synsets(pos: str, n: int) -> list[lmf.Synset]:
    synsets: list[lmf.Synset] = [
        lmf.Synset(
            id=f"{i}-{pos}",
            ili="",
            partOfSpeech=pos,
            relations=[],
            meta={},
        )
        for i in range(1, n+1)
    ]
    # add relations for nouns and verbs
    if pos in "nv":
        total = len(synsets)
        tgt_i = 1  # index of next target synset
        n = cycle([2])  # how many targets to relate
        for cur_i in range(total):
            if tgt_i <= cur_i:
                tgt_i = cur_i + 1
            source = synsets[cur_i]
            for cur_k in range(tgt_i, tgt_i + next(n)):
                if cur_k >= total:
                    break
                target = synsets[cur_k]
                source["relations"].append(
                    lmf.Relation(target=target["id"], relType="hyponym", meta={})
                )
                target["relations"].append(
                    lmf.Relation(target=source["id"], relType="hypernym", meta={})
                )
            tgt_i = cur_k + 1

    return synsets


def _words() -> Iterator[str]:
    consonants = "kgtdpbfvszrlmnhw"
    vowels = "aeiou"
    while True:
        yield from map("".join, product(consonants, vowels, consonants, vowels))


def _make_entries(synsets: list[lmf.Synset]) -> list[lmf.LexicalEntry]:
    words = _words()
    member_count = cycle(range(1, 4))  # 1, 2, or 3 synset members
    entries: dict[str, lmf.LexicalEntry] = {}
    prev_synsets: list[lmf.Synset] = []
    for synset in synsets:
        ssid = synset["id"]
        pos = synset["partOfSpeech"]

        for _ in range(next(member_count)):
            word = next(words)
            senses = [lmf.Sense(id=f"{word}-{ssid}", synset=ssid, meta={})]
            # add some polysemy
            if prev_synsets:
                ssid2 = prev_synsets.pop()["id"]
                senses.append(lmf.Sense(id=f"{word}-{ssid2}", synset=ssid2, meta={}))
            eid = f"{word}-{pos}"
            if eid not in entries:
                entries[eid] = lmf.LexicalEntry(
                    id=eid,
                    lemma=lmf.Lemma(
                        writtenForm=word,
                        partOfSpeech=pos,
                    ),
                    senses=[],
                    meta={},
                )
            entries[eid]["senses"].extend(senses)

        prev_synsets.append(synset)

    return list(entries.values())
