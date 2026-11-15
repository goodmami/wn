from pathlib import Path

from wn._config import WNConfig


def test_envvar_data_dir(monkeypatch, tmp_path):
    # database_path, unlike data_directory, does not create the directory
    with monkeypatch.context() as mp:
        mp.delenv("WN_DATA_DIR", raising=False)
        assert WNConfig().database_path.parent == Path.home() / ".wn_data"
    with monkeypatch.context() as mp:
        mp.setenv("WN_DATA_DIR", str(tmp_path))
        assert WNConfig().data_directory == tmp_path
