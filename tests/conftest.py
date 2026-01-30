import lzma
from pathlib import Path

import pytest

import wn


@pytest.fixture(scope="session")
def datadir():
    return Path(__file__).parent / "data"


@pytest.fixture
def uninitialized_datadir(monkeypatch, tmp_path: Path):
    with monkeypatch.context() as m:
        m.setattr(wn.config, "data_directory", tmp_path / "uninitialized_datadir")
        yield


@pytest.fixture(scope="session")
def empty_db(tmp_path_factory):
    dir = tmp_path_factory.mktemp("wn_data_empty")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(wn.config, "data_directory", dir)
        yield


# We want to build these DBs once per session, but connections
# are created once for every test.


@pytest.fixture(scope="session")
def mini_db_dir(datadir, tmp_path_factory):
    dir = tmp_path_factory.mktemp("wn_data_mini")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(wn.config, "data_directory", dir)
        wn.add(datadir / "mini-lmf-1.0.xml")
        wn.add(datadir / "mini-ili.tsv")
        wn._db.clear_connections()

    return Path(dir)


@pytest.fixture
def mini_lmf_compressed(datadir, tmp_path):
    data = (datadir / "mini-lmf-1.0.xml").read_bytes()
    path = tmp_path / "temp.xml.xz"
    with lzma.open(path, "w") as f:
        f.write(data)
    return Path(path)


@pytest.fixture(scope="session")
def mini_db_1_1_dir(datadir, tmp_path_factory):
    dir = tmp_path_factory.mktemp("wn_data_mini_1_1")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(wn.config, "data_directory", dir)
        wn.add(datadir / "mini-lmf-1.0.xml")
        wn.add(datadir / "mini-lmf-1.1.xml")
        wn._db.clear_connections()

    return Path(dir)


@pytest.fixture(scope="session")
def mini_db_1_4_dir(datadir, tmp_path_factory):
    dir = tmp_path_factory.mktemp("wn_data_mini_1_4")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(wn.config, "data_directory", dir)
        wn.add(datadir / "mini-lmf-1.0.xml")
        wn.add(datadir / "mini-lmf-1.4.xml")
        wn._db.clear_connections()

    return Path(dir)


@pytest.fixture
def mini_db(monkeypatch, mini_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, "data_directory", mini_db_dir)
        yield
        wn._db.clear_connections()


@pytest.fixture
def mini_db_1_1(monkeypatch, mini_db_1_1_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, "data_directory", mini_db_1_1_dir)
        yield
        wn._db.clear_connections()


@pytest.fixture
def mini_db_1_4(monkeypatch, mini_db_1_4_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, "data_directory", mini_db_1_4_dir)
        yield
        wn._db.clear_connections()
