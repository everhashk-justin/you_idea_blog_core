"""
blog_core.database.schema - Centralized Database Schema, DDL & Migrations
Provides schema definitions, indexing, and migration logic for IdeaSpot360 blog ecosystem.
"""

import sqlite3

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_uid TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL CHECK(platform IN ('dev', 'tistory', 'naver', 'gear', 'stock', 'markets')),
    blog_id TEXT,
    track TEXT,
    title TEXT NOT NULL,
    slug TEXT,
    category TEXT,
    tags TEXT,
    file_path TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PUBLISHED', 'RESERVED', 'DRAFT')),
    reserved_at TEXT,
    published_at TEXT,
    url TEXT,
    pair_id TEXT,
    content_length INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS post_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    record_date TEXT NOT NULL,
    pageviews INTEGER DEFAULT 0,
    users INTEGER DEFAULT 0,
    sessions INTEGER DEFAULT 0,
    avg_duration_sec REAL DEFAULT 0.0,
    bounce_rate REAL DEFAULT 0.0,
    source TEXT DEFAULT 'GA4',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (post_id) REFERENCES blog_posts(id) ON DELETE CASCADE,
    UNIQUE (post_id, record_date, source)
);

CREATE TABLE IF NOT EXISTS publishing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    action TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED')),
    message TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (post_id) REFERENCES blog_posts(id) ON DELETE SET NULL
);
"""

INDEXES_DDL = """
CREATE INDEX IF NOT EXISTS idx_posts_platform ON blog_posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON blog_posts(blog_id);
CREATE INDEX IF NOT EXISTS idx_posts_track ON blog_posts(track);
CREATE INDEX IF NOT EXISTS idx_posts_status ON blog_posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_pair_id ON blog_posts(pair_id);
CREATE INDEX IF NOT EXISTS idx_posts_file_path ON blog_posts(file_path);
CREATE INDEX IF NOT EXISTS idx_analytics_post_date ON post_analytics(post_id, record_date);
CREATE INDEX IF NOT EXISTS idx_logs_post_id ON publishing_logs(post_id);
"""


def migrate_schema_if_needed(conn: sqlite3.Connection) -> None:
    """
    Checks the current database schema and performs idempotent migration
    if legacy columns or platform constraints are detected.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='blog_posts'")
    row = cursor.fetchone()
    if not row:
        return

    sql = row[0] if isinstance(row, (tuple, list)) else row["sql"]

    # If blog_id and newer platforms are already present in CHECK constraint, no table rebuild is needed
    needs_migration = False
    if "blog_id" not in sql:
        needs_migration = True
    elif not all(f"'{p}'" in sql for p in ('naver', 'gear', 'stock', 'markets')):
        needs_migration = True

    if not needs_migration:
        return

    cursor.execute("PRAGMA foreign_keys = OFF;")

    cursor.execute("""
    CREATE TABLE blog_posts_migration_backup (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_uid TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL CHECK(platform IN ('dev', 'tistory', 'naver', 'gear', 'stock', 'markets')),
        blog_id TEXT,
        track TEXT,
        title TEXT NOT NULL,
        slug TEXT,
        category TEXT,
        tags TEXT,
        file_path TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('PUBLISHED', 'RESERVED', 'DRAFT')),
        reserved_at TEXT,
        published_at TEXT,
        url TEXT,
        pair_id TEXT,
        content_length INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # Check if old table has blog_id
    cursor.execute("PRAGMA table_info(blog_posts)")
    columns = [col[1] if isinstance(col, (tuple, list)) else col["name"] for col in cursor.fetchall()]

    if "blog_id" in columns:
        cursor.execute("""
        INSERT INTO blog_posts_migration_backup (
            id, post_uid, platform, blog_id, track, title, slug, category, tags,
            file_path, status, reserved_at, published_at, url, pair_id,
            content_length, created_at, updated_at
        )
        SELECT
            id, post_uid, platform, blog_id,
            track, title, slug, category, tags,
            file_path, status, reserved_at, published_at, url, pair_id,
            content_length, created_at, updated_at
        FROM blog_posts;
        """)
    else:
        cursor.execute("""
        INSERT INTO blog_posts_migration_backup (
            id, post_uid, platform, blog_id, track, title, slug, category, tags,
            file_path, status, reserved_at, published_at, url, pair_id,
            content_length, created_at, updated_at
        )
        SELECT
            id, post_uid, platform,
            CASE
                WHEN platform = 'dev' THEN 'dev'
                WHEN platform = 'tistory' THEN 'softwin'
                ELSE platform
            END as blog_id,
            track, title, slug, category, tags,
            file_path, status, reserved_at, published_at, url, pair_id,
            content_length, created_at, updated_at
        FROM blog_posts;
        """)

    cursor.execute("DROP TABLE blog_posts;")
    cursor.execute("ALTER TABLE blog_posts_migration_backup RENAME TO blog_posts;")

    blog_posts_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_posts_platform ON blog_posts(platform);",
        "CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON blog_posts(blog_id);",
        "CREATE INDEX IF NOT EXISTS idx_posts_track ON blog_posts(track);",
        "CREATE INDEX IF NOT EXISTS idx_posts_status ON blog_posts(status);",
        "CREATE INDEX IF NOT EXISTS idx_posts_pair_id ON blog_posts(pair_id);",
        "CREATE INDEX IF NOT EXISTS idx_posts_file_path ON blog_posts(file_path);",
    ]
    for stmt in blog_posts_indexes:
        cursor.execute(stmt)

    cursor.execute("PRAGMA foreign_keys = ON;")


def init_db_schema(conn: sqlite3.Connection) -> None:
    """
    Executes table creation, runs migration if existing schema is outdated,
    and ensures all required indexes exist.
    """
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_DDL)
    migrate_schema_if_needed(conn)
    cursor.executescript(INDEXES_DDL)


# Backward-compatible alias for fixtures/modules importing init_db from schema
init_db = init_db_schema

__all__ = [
    "SCHEMA_DDL",
    "INDEXES_DDL",
    "init_db_schema",
    "migrate_schema_if_needed",
    "init_db",
]
