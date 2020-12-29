"""
Storage back-end interface.
"""

from typing import Callable, TypeVar, Any, cast
import json
import sqlite3
import logging
from functools import wraps

import wn
from wn._types import Metadata
from wn._util import resources, short_hash
from wn import constants
from wn import lmf


logger = logging.getLogger('wn')


# Module Constants

DEBUG = False
NON_ROWID = 0  # imaginary rowid of non-existent row

# This stores hashes of the schema to check for version differences.
# When the schema changes, the hash will change. If the new hash is
# not added here, the 'test_schema_compatibility' test will fail. It
# is the developer's responsibility to only add compatible schema
# hashes here. If the schema change is not backwards-compatible, they
# clear all old hashes and only put the latest hash here. A hash can
# be generated like this:
#
# >>> import wn
# >>> wn._db.schema_hash()
#
COMPATIBLE_SCHEMA_HASHES = {
    '0cbec124b988d08e428b80d2b749563c2dccfa65',
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


# The connect() function should be used for all connections

def connect() -> sqlite3.Connection:
    dbpath = wn.config.database_path
    initialized = dbpath.is_file()
    conn = sqlite3.connect(str(dbpath), detect_types=sqlite3.PARSE_DECLTYPES)
    # foreign key support needs to be enabled for each connection
    conn.execute('PRAGMA foreign_keys = ON')
    # uncomment the following to help with debugging
    if DEBUG:
        conn.set_trace_callback(print)
    if not initialized:
        logger.info('initializing database: %s', dbpath)
        _initialize(conn)
    return conn


F = TypeVar('F', bound=Callable[..., Any])


def connects(f: F) -> F:
    """Wrapper for a function that establishes a database connection."""

    @wraps(f)
    def connect_wrapper(*args, conn: sqlite3.Connection = None, **kwargs):
        if conn is None:
            try:
                _conn = connect()
                value = f(*args, conn=_conn, **kwargs)
            finally:
                _conn.close()
        else:
            value = f(*args, conn=conn, **kwargs)
        return value

    return cast(F, connect_wrapper)


def connects_generator(f: F) -> F:
    """Wrapper for a generator that establishes a database connection."""

    @wraps(f)
    def connect_wrapper(*args, conn: sqlite3.Connection = None, **kwargs):
        if conn is None:
            try:
                _conn = connect()
                yield from f(*args, conn=_conn, **kwargs)
            finally:
                _conn.close()
        else:
            yield from f(*args, conn=conn, **kwargs)

    return cast(F, connect_wrapper)


def _initialize(conn: sqlite3.Connection) -> None:
    schema = resources.read_text('wn', 'schema.sql')
    with conn:
        conn.executescript(schema)
        # prepare lookup tables
        conn.executemany(
            'INSERT INTO parts_of_speech (pos) VALUES (?)',
            ((pos,) for pos in constants.PARTS_OF_SPEECH))
        conn.executemany(
            'INSERT INTO adjpositions (position) VALUES (?)',
            ((adj,) for adj in constants.ADJPOSITIONS))
        conn.executemany(
            'INSERT INTO synset_relation_types (type) VALUES (?)',
            ((typ,) for typ in constants.SYNSET_RELATIONS))
        conn.executemany(
            'INSERT INTO sense_relation_types (type) VALUES (?)',
            ((typ,) for typ in constants.SENSE_RELATIONS))
        conn.executemany(
            'INSERT INTO lexicographer_files (id, name) VALUES (?,?)',
            ((id, name) for name, id in constants.LEXICOGRAPHER_FILES.items()))


def schema_hash() -> str:
    query = 'SELECT sql FROM sqlite_master WHERE NOT sql ISNULL'
    try:
        conn = connect()
        schema = '\n\n'.join(row[0] for row in conn.execute(query))
    finally:
        conn.close()
    return short_hash(schema)


def is_schema_compatible(create: bool = False) -> bool:
    if create or wn.config.database_path.exists():
        return schema_hash() in COMPATIBLE_SCHEMA_HASHES
    else:
        return True
