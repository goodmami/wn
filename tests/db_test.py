
import sqlite3

import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_schema_compatibility():
    conn = sqlite3.connect(str(wn.config.database_path))
    schema_hash = wn._db.schema_hash(conn)
    assert schema_hash in wn._db.COMPATIBLE_SCHEMA_HASHES
