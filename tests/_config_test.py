from pathlib import Path

from wn._config import WNConfig


def test_envvar_data_dir(monkeypatch, tmp_path):
    assert WNConfig().data_directory == Path.home() / ".wn_data"
    with monkeypatch.context() as mp:
        mp.setenv("WN_DATA_DIR", str(tmp_path))
        assert WNConfig().data_directory == tmp_path
