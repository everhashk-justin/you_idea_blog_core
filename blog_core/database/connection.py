"""
blog_core.database.connection - SQLite Database Connection Manager
Provides connection lifecycle management, WAL mode, foreign keys, and path resolution.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Generator, Union
from contextlib import contextmanager

from .schema import init_db_schema

DEFAULT_SHARED_DB_PATH = Path(r"D:\00_antigravity\01_you_idea_blog\data\posts.db")


def resolve_db_path(db_path: Optional[str] = None) -> str:
    """
    Resolves database path using priority:
    1. Explicit `db_path` argument
    2. `BLOG_CORE_DB_PATH` environment variable
    3. Shared reference DB (D:\\00_antigravity\\01_you_idea_blog\\data\\posts.db) if exists
    4. Default local fallback: <cwd>/data/posts.db
    """
    if db_path is not None:
        return str(db_path)

    env_path = os.environ.get("BLOG_CORE_DB_PATH")
    if env_path:
        return env_path

    if DEFAULT_SHARED_DB_PATH.exists():
        return str(DEFAULT_SHARED_DB_PATH)

    fallback_path = Path.cwd() / "data" / "posts.db"
    return str(fallback_path)


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    SQLite connection context manager.
    Applies WAL journal mode, 30s busy timeout, and foreign keys ON.
    Commits on normal exit, rolls back on exception, and closes connection.
    """
    target = resolve_db_path(db_path)

    if target != ":memory:":
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target_path), timeout=30.0)
    else:
        conn = sqlite3.connect(":memory:", timeout=30.0)

    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Union[str, sqlite3.Connection]] = None) -> None:
    """
    Initializes the database schema and performs migrations if needed.
    Supports either an explicit database path string, None, or an
    already-open sqlite3.Connection object directly.
    """
    if isinstance(db_path, sqlite3.Connection):
        init_db_schema(db_path)
        return
    with get_db(db_path=db_path) as conn:
        init_db_schema(conn)
