
import sqlite3
import threading
import tempfile

import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_schema_compatibility():
    conn = sqlite3.connect(str(wn.config.database_path))
    schema_hash = wn._db.schema_hash(conn)
    assert schema_hash in wn._db.COMPATIBLE_SCHEMA_HASHES


@pytest.mark.usefixtures('mini_db')
def test_db_multithreading():
    """
    See https://github.com/goodmami/wn/issues/86
    Thanks: @fushinari
    """

    class WNThread:
        w = None

        def __init__(self):
            w_thread = threading.Thread(target=self.set_w)
            w_thread.start()
            w_thread.join()
            self.w.synsets()

        def set_w(self):
            if self.w is None:
                self.w = wn.Wordnet()

    # close the connections by resetting the pool
    wn._db.pool = {}
    with pytest.raises(sqlite3.ProgrammingError):
        WNThread()
    wn._db.pool = {}
    wn.config.allow_multithreading = True
    WNThread()  # no error
    wn.config.allow_multithreading = False
    wn._db.pool = {}


def test_remove_extension(mini_lmf_1_0, mini_lmf_1_1):
    with tempfile.TemporaryDirectory('wn_data_1_1_trigger') as dir:
        old_data_dir = wn.config.data_directory
        wn.config.data_directory = dir
        wn.add(mini_lmf_1_0)
        wn.add(mini_lmf_1_1)
        assert len(wn.lexicons()) == 4
        wn.remove('test-en-ext')
        assert len(wn.lexicons()) == 3
        wn.remove('test-ja')
        assert len(wn.lexicons()) == 2
        wn.add(mini_lmf_1_1)
        assert len(wn.lexicons()) == 4
        wn.remove('test-en')
        assert {lex.id for lex in wn.lexicons()} == {'test-es', 'test-ja'}
        wn.config.data_directory = old_data_dir
        # close any open DB connections before teardown
        for conn in wn._db.pool.values():
            conn.close()
