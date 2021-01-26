
import sqlite3
import threading

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
