"""
Storage back-end interface.
"""

import json
import logging
import sqlite3
from importlib import resources
from pathlib import Path

from wn._config import config
from wn._exceptions import DatabaseError
from wn._types import AnyPath
from wn._util import format_lexicon_specifier, short_hash

logger = logging.getLogger("wn")


# Module Constants

DEBUG = False

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
    "8348fc1a6254f514294a1dc70458e0733742935d",
}


# Optional metadata is stored as a JSON string


def _adapt_dict(d: dict) -> bytes:
    return json.dumps(d).encode("utf-8")


def _convert_dict(s: bytes) -> dict:
    return json.loads(s)


def _convert_boolean(s: bytes) -> bool:
    return bool(int(s))


sqlite3.register_adapter(dict, _adapt_dict)
sqlite3.register_converter("meta", _convert_dict)
sqlite3.register_converter("boolean", _convert_boolean)


# The pool is a cache of open connections. Unless the database path is
# changed, there should only be zero or one.
pool: dict[AnyPath, sqlite3.Connection] = {}


# The connect() function should be used for all connections


def connect(check_schema: bool = True) -> sqlite3.Connection:
    dbpath = config.database_path
    if dbpath not in pool:
        if not config.data_directory.exists():
            config.data_directory.mkdir(parents=True, exist_ok=True)
        initialized = dbpath.is_file()
        conn = sqlite3.connect(
            str(dbpath),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=not config.allow_multithreading,
        )
        # foreign key support needs to be enabled for each connection
        conn.execute("PRAGMA foreign_keys = ON")
        if DEBUG:
            conn.set_trace_callback(print)
        if not initialized:
            logger.info("initializing database: %s", dbpath)
            _init_db(conn)
        if check_schema:
            _check_schema_compatibility(conn, dbpath)

        pool[dbpath] = conn
    return pool[dbpath]


def _init_db(conn: sqlite3.Connection) -> None:
    schema = (resources.files("wn") / "schema.sql").read_text()
    conn.executescript(schema)
    with conn:
        conn.executemany(
            "INSERT INTO ili_statuses VALUES (null,?)",
            [("presupposed",), ("proposed",)],
        )


def _check_schema_compatibility(conn: sqlite3.Connection, dbpath: Path) -> None:
    hash = schema_hash(conn)

    # if the hash is known, then we're all good here
    if hash in COMPATIBLE_SCHEMA_HASHES:
        return

    logger.debug("current schema hash:\n  %s", hash)
    logger.debug(
        "compatible schema hashes:\n  %s", "\n  ".join(COMPATIBLE_SCHEMA_HASHES)
    )
    # otherwise, try to raise a helpful error message
    msg = "Wn's schema has changed and is no longer compatible with the database."
    try:
        specs = list_lexicons_safe(conn)
    except DatabaseError as exc:
        raise DatabaseError(msg) from exc
    if specs:
        installed = "\n  ".join(specs)
        msg += (
            f"\nLexicons currently installed:\n  {installed}"
            "\nRun wn.reset_database(rebuild=True) to rebuild the database."
        )
    else:
        msg += (
            "\nNo lexicons are currently installed."
            "\nRun wn.reset_database() to re-initialize the database."
        )
    raise DatabaseError(msg)


def list_lexicons_safe(conn: sqlite3.Connection | None = None) -> list[str]:
    """Return the list of lexicon specifiers for added lexicons."""
    if conn is None:
        conn = connect(check_schema=False)
    try:
        specs = conn.execute("SELECT id, version FROM lexicons").fetchall()
    except sqlite3.OperationalError as exc:
        raise DatabaseError("could not list lexicons") from exc
    return [format_lexicon_specifier(id, ver) for id, ver in specs]


def schema_hash(conn: sqlite3.Connection) -> str:
    query = "SELECT sql FROM sqlite_master WHERE NOT sql ISNULL"
    schema = "\n\n".join(row[0] for row in conn.execute(query))
    return short_hash(schema)


def clear_connections() -> None:
    """Close and delete any open database connections."""
    for path in list(pool):
        pool[path].close()
        del pool[path]
