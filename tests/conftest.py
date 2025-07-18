
import lzma
import tempfile
from pathlib import Path

import pytest

import wn


@pytest.fixture(scope='session')
def datadir():
    return Path(__file__).parent / 'data'


@pytest.fixture
def uninitialized_datadir(monkeypatch, tmp_path: Path):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', tmp_path / 'uninitialized_datadir')
        yield


@pytest.fixture(scope='session')
def empty_db():
    with tempfile.TemporaryDirectory('wn_data_empty') as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            yield


# We want to build these DBs once per session, but connections
# are created once for every test.

@pytest.fixture(scope='session')
def mini_db_dir(datadir):
    with tempfile.TemporaryDirectory('wn_data_mini') as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            wn.add(datadir / 'mini-lmf-1.0.xml')
            wn._db.clear_connections()

        yield Path(dir)


@pytest.fixture
def mini_lmf_compressed(datadir):
    data = (datadir / 'mini-lmf-1.0.xml').read_bytes()
    with tempfile.NamedTemporaryFile(suffix='.xml.xz', delete=False) as file:
        path = Path(file.name)
    # Windows cannot reliably reopen file until it's closed
    with lzma.open(path, "w") as f:
        f.write(data)
    try:
        yield Path(file.name)
    finally:
        Path(file.name).unlink()


@pytest.fixture(scope='session')
def mini_db_1_1_dir(datadir):
    with tempfile.TemporaryDirectory('wn_data_mini_1_1') as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            wn.add(datadir / 'mini-lmf-1.0.xml')
            wn.add(datadir / 'mini-lmf-1.1.xml')
            wn._db.clear_connections()

        yield Path(dir)


@pytest.fixture(scope='session')
def mini_db_1_4_dir(datadir):
    with tempfile.TemporaryDirectory('wn_data_mini_1_4') as dir:
        with pytest.MonkeyPatch.context() as m:
            m.setattr(wn.config, 'data_directory', dir)
            wn.add(datadir / 'mini-lmf-1.4.xml')
            wn._db.clear_connections()

        yield Path(dir)


@pytest.fixture
def mini_db(monkeypatch, mini_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', mini_db_dir)
        yield
        wn._db.clear_connections()


@pytest.fixture
def mini_db_1_1(monkeypatch, mini_db_1_1_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', mini_db_1_1_dir)
        yield
        wn._db.clear_connections()


@pytest.fixture
def mini_db_1_4(monkeypatch, mini_db_1_4_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', mini_db_1_4_dir)
        yield
        wn._db.clear_connections()
