
from pathlib import Path

import pytest

import wn


@pytest.fixture
def datadir():
    return Path(__file__).parent / 'data'


@pytest.fixture
def mini_lmf_1_0(datadir):
    return datadir / 'mini-lmf-1.0.xml'


@pytest.fixture
def empty_db(monkeypatch, tmp_path):
    dir = tmp_path / 'wn_data_tmp'
    dir.mkdir()
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', dir)
        yield


@pytest.fixture
def mini_db(monkeypatch, tmp_path, mini_lmf_1_0):
    dir = tmp_path / 'wn_data_tmp'
    dir.mkdir()
    with monkeypatch.context() as m:
        m.setattr(wn.config, 'data_directory', dir)
        wn.add(mini_lmf_1_0)
        yield
