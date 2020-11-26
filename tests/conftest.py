
from pathlib import Path
import tempfile

import pytest

import wn


@pytest.fixture(scope='session')
def datadir():
    return Path(__file__).parent / 'data'


@pytest.fixture(scope='session')
def mini_lmf_1_0(datadir):
    return datadir / 'mini-lmf-1.0.xml'


@pytest.fixture(scope='session')
def empty_db_dir():
    with tempfile.TemporaryDirectory('wn_data_empty') as dir:
        yield Path(dir)


@pytest.fixture(scope='session')
def mini_db_dir(mini_lmf_1_0):
    with tempfile.TemporaryDirectory('wn_data_empty') as dir:
        old_data_dir = wn.config.data_directory
        wn.config.data_directory = dir
        wn.add(mini_lmf_1_0)
        wn.config.data_directory = old_data_dir
        yield Path(dir)


@pytest.fixture
def empty_db(monkeypatch, empty_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', empty_db_dir)
        yield


@pytest.fixture
def mini_db(monkeypatch, mini_db_dir):
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', mini_db_dir)
        yield
