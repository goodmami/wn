import pytest
from starlette.testclient import TestClient

import wn
import wn._db
from wn import web


# clearing connections on teardown (see conftest.py) isn't enough. For
# this we apparently need to monkeypatch the wn._db.pool as well.

@pytest.fixture
def mini_db_web(monkeypatch, mini_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn._db, 'pool', {})
        m.setattr(wn.config, 'data_directory', mini_db_dir)
        m.setattr(wn.config, 'allow_multithreading', True)
        yield
        wn._db.clear_connections()


client = TestClient(web.app)


@pytest.mark.usefixtures('mini_db_web')
def test_root():
    response = client.get('/')
    assert response.status_code == 404


@pytest.mark.usefixtures('mini_db_web')
def test_lexicons():
    response = client.get("/lexicons")
    assert response.status_code == 200
    data = response.json()["data"]
    assert [lex["id"] for lex in data] == ["test-en:1", "test-es:1"]


@pytest.mark.usefixtures('mini_db_web')
def test_words():
    response = client.get("/words")
    assert response.status_code == 200
    data = response.json()["data"]
    word_ids = {word["id"] for word in data}
    assert "test-en-information-n" in word_ids
    assert "test-es-información-n" in word_ids

    response = client.get("/words", params={"lexicon": "test-en:1"})
    assert response.status_code == 200
    data = response.json()["data"]
    word_ids = {word["id"] for word in data}
    assert "test-en-information-n" in word_ids
    assert "test-es-información-n" not in word_ids


@pytest.mark.usefixtures('mini_db_web')
def test_senses():
    response = client.get("/senses")
    assert response.status_code == 200
    data = response.json()["data"]
    sense_ids = {sense["id"] for sense in data}
    assert "test-en-information-n-0001-01" in sense_ids
    assert "test-es-información-n-0001-01" in sense_ids

    response = client.get("/senses", params={"lexicon": "test-en:1"})
    assert response.status_code == 200
    data = response.json()["data"]
    sense_ids = {sense["id"] for sense in data}
    assert "test-en-information-n-0001-01" in sense_ids
    assert "test-es-información-n-0001-01" not in sense_ids


@pytest.mark.usefixtures('mini_db_web')
def test_synsets():
    response = client.get("/synsets")
    assert response.status_code == 200
    data = response.json()["data"]
    synset_ids = {synset["id"] for synset in data}
    assert "test-en-0001-n" in synset_ids
    assert "test-es-0001-n" in synset_ids

    response = client.get("/synsets", params={"lexicon": "test-en:1"})
    assert response.status_code == 200
    data = response.json()["data"]
    synset_ids = {synset["id"] for synset in data}
    assert "test-en-0001-n" in synset_ids
    assert "test-es-0001-n" not in synset_ids


@pytest.mark.usefixtures('mini_db_web')
def test_lexicon_words():
    response1 = client.get("/lexicons/test-en:1/words")
    response2 = client.get("/words", params={"lexicon": "test-en:1"})
    assert response1.status_code == 200
    assert response2.status_code == 200
    data1 = response1.json()["data"]
    data2 = response2.json()["data"]
    assert {word["id"] for word in data1} == {word["id"] for word in data2}


@pytest.mark.usefixtures('mini_db_web')
def test_lexicon_senses():
    response1 = client.get("/lexicons/test-en:1/senses")
    response2 = client.get("/senses", params={"lexicon": "test-en:1"})
    assert response1.status_code == 200
    assert response2.status_code == 200
    data1 = response1.json()["data"]
    data2 = response2.json()["data"]
    assert {sense["id"] for sense in data1} == {sense["id"] for sense in data2}


@pytest.mark.usefixtures('mini_db_web')
def test_lexicon_synsets():
    response1 = client.get("/lexicons/test-en:1/synsets")
    response2 = client.get("/synsets", params={"lexicon": "test-en:1"})
    assert response1.status_code == 200
    assert response2.status_code == 200
    data1 = response1.json()["data"]
    data2 = response2.json()["data"]
    assert {synset["id"] for synset in data1} == {synset["id"] for synset in data2}
