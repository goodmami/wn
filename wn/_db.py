"""
Storage back-end interface.
"""

from typing import Dict
from pathlib import Path
import json
import sqlite3
import logging

import wn
from wn._types import Metadata, AnyPath
from wn._util import resources, short_hash
from wn import lmf


logger = logging.getLogger('wn')


# Module Constants

DEBUG = False
NON_ROWID = 0  # imaginary rowid of non-existent row

# This stores hashes of the schema to check for version differences.
# When the schema changes, the hash will change. If the new hash is
# not added here, the 'test_schema_compatibility' test will fail. It
# is the developer's responsibility to only add compatible schema
# hashes here. If the schema change is not backwards-compatible, then
# clear all old hashes and only put the latest hash here. A hash can
# be generated like this:
#
# >>> import sqlite3
# >>> import wn
# >>> conn = sqlite3.connect(wn.config.database_path)
# >>> wn._db.schema_hash(conn)
#
COMPATIBLE_SCHEMA_HASHES = {
    '4c8ad03af5422d6979039ee2b80838d07c12d2c8',
}


# Optional metadata is stored as a JSON string

def _adapt_metadata(meta: lmf.Metadata) -> bytes:
    d = {key: val for key, val in zip(meta._fields, meta) if val is not None}
    return json.dumps(d).encode('utf-8')


def _convert_metadata(s: bytes) -> Metadata:  # note: wn._types.Metadata
    return json.loads(s)


def _convert_boolean(s: bytes) -> bool:
    return bool(int(s))


sqlite3.register_adapter(lmf.Metadata, _adapt_metadata)
sqlite3.register_converter('meta', _convert_metadata)
sqlite3.register_converter('boolean', _convert_boolean)


# The pool is a cache of open connections. Unless the database path is
# changed, there should only be zero or one.
pool: Dict[AnyPath, sqlite3.Connection] = {}


# The connect() function should be used for all connections

def connect() -> sqlite3.Connection:
    dbpath = wn.config.database_path
    if dbpath not in pool:
        initialized = dbpath.is_file()
        conn = sqlite3.connect(
            str(dbpath),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=not wn.config.allow_multithreading,
        )
        # foreign key support needs to be enabled for each connection
        conn.execute('PRAGMA foreign_keys = ON')
        if DEBUG:
            conn.set_trace_callback(print)
        if not initialized:
            logger.info('initializing database: %s', dbpath)
            _init_db(conn)
        _check_schema_compatibility(conn, dbpath)

        pool[dbpath] = conn
    return pool[dbpath]


def _init_db(conn: sqlite3.Connection) -> None:
    schema = resources.read_text('wn', 'schema.sql')
    conn.executescript(schema)
    with conn:
        conn.executemany('INSERT INTO ili_statuses VALUES (null,?)',
                         [('presupposed',), ('proposed',)])


def _check_schema_compatibility(conn: sqlite3.Connection, dbpath: Path) -> None:
    hash = schema_hash(conn)

    # if the hash is known, then we're all good here
    if hash in COMPATIBLE_SCHEMA_HASHES:
        return

    logger.debug('current schema hash:\n  %s', hash)
    logger.debug('compatible schema hashes:\n  %s',
                 '\n  '.join(COMPATIBLE_SCHEMA_HASHES))
    # otherwise, try to raise a helpful error message
    msg = ("Wn's schema has changed and is no longer compatible with the "
           f"database. Please move or delete {dbpath} and rebuild it.")
    try:
        specs = conn.execute('SELECT id, version FROM lexicons').fetchall()
    except sqlite3.OperationalError as exc:
        raise wn.DatabaseError(msg) from exc
    else:
        if specs:
            installed = '\n  '.join(f'{id}:{ver}' for id, ver in specs)
            msg += f" Lexicons currently installed:\n  {installed}"
        else:
            msg += ' No lexicons are currently installed.'
        raise wn.DatabaseError(msg)


def schema_hash(conn: sqlite3.Connection) -> str:
    query = 'SELECT sql FROM sqlite_master WHERE NOT sql ISNULL'
    schema = '\n\n'.join(row[0] for row in conn.execute(query))
    return short_hash(schema)
