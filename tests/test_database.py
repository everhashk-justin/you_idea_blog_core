"""
Unit and integration tests for blog_core.database module.
Verifies connection lifecycle, WAL mode, migrations, and CRUD operations.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pytest

from blog_core.database.connection import get_db, init_db, resolve_db_path, DEFAULT_SHARED_DB_PATH
from blog_core.database.schema import init_db_schema, migrate_schema_if_needed
from blog_core.database.operations import (
    upsert_post,
    get_post_by_file,
    get_post_by_id,
    get_post_by_uid,
    get_post_by_slug,
    list_posts,
    search_posts,
    update_post_status,
    update_post_live_sync,
    record_log,
    record_analytics,
    get_stats_summary,
    infer_blog_id,
)


@pytest.fixture
def temp_db_path():
    """Provides a temporary file path for a SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def memory_db():
    """Provides an initialized in-memory database connection with schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db_schema(conn)
    yield conn
    conn.close()


class TestConnectionAndPath:
    def test_resolve_explicit_path(self):
        explicit = "custom/test_path.db"
        assert resolve_db_path(explicit) == explicit

    def test_resolve_env_var(self, monkeypatch):
        test_env_path = r"D:\custom\env_posts.db"
        monkeypatch.setenv("BLOG_CORE_DB_PATH", test_env_path)
        assert resolve_db_path() == test_env_path

    def test_get_db_memory_wal_and_pragmas(self):
        with get_db(":memory:") as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            fk = cursor.fetchone()[0]
            assert fk == 1

            cursor.execute("PRAGMA busy_timeout;")
            timeout = cursor.fetchone()[0]
            assert timeout == 30000

    def test_init_db_with_connection_object(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert {"blog_posts", "post_analytics", "publishing_logs"}.issubset(tables)
        conn.close()

    def test_init_db_import_from_schema(self):
        from blog_core.database.schema import init_db as schema_init_db
        conn = sqlite3.connect(":memory:")
        schema_init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert {"blog_posts", "post_analytics", "publishing_logs"}.issubset(tables)
        conn.close()

    def test_get_db_file_transaction_commit_and_rollback(self, temp_db_path):
        init_db(temp_db_path)

        # Commit test
        with get_db(temp_db_path) as conn:
            upsert_post({
                "post_uid": "test_uid_1",
                "platform": "dev",
                "file_path": "blogs/dev/test1.md",
                "title": "Test 1"
            }, conn=conn)

        with get_db(temp_db_path) as conn:
            post = get_post_by_uid("test_uid_1", conn=conn)
            assert post is not None
            assert post["title"] == "Test 1"

        # Rollback test on exception
        with pytest.raises(ValueError):
            with get_db(temp_db_path) as conn:
                upsert_post({
                    "post_uid": "test_uid_2",
                    "platform": "dev",
                    "file_path": "blogs/dev/test2.md",
                    "title": "Test 2"
                }, conn=conn)
                raise ValueError("Simulated failure")

        with get_db(temp_db_path) as conn:
            post = get_post_by_uid("test_uid_2", conn=conn)
            assert post is None


class TestSchemaAndMigration:
    def test_init_db_schema_idempotent(self, memory_db):
        # Call it second time on already initialized DB
        init_db_schema(memory_db)
        cursor = memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert {"blog_posts", "post_analytics", "publishing_logs"}.issubset(tables)

    def test_migration_from_legacy_schema(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create legacy table without blog_id and only dev/tistory check constraint
        cursor.execute("""
        CREATE TABLE blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_uid TEXT UNIQUE NOT NULL,
            platform TEXT NOT NULL CHECK(platform IN ('dev', 'tistory')),
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

        # Insert legacy posts
        cursor.execute("""
        INSERT INTO blog_posts (post_uid, platform, title, file_path, status)
        VALUES ('legacy_dev_1', 'dev', 'Dev Post', 'dev/p1.md', 'PUBLISHED'),
               ('legacy_tis_1', 'tistory', 'Tistory Post', 'posts/p1.md', 'PUBLISHED')
        """)
        conn.commit()

        # Run migration
        migrate_schema_if_needed(conn)

        # Verify columns and data
        cursor.execute("SELECT * FROM blog_posts ORDER BY id ASC")
        rows = cursor.fetchall()
        assert len(rows) == 2

        dev_row = rows[0]
        assert dev_row["post_uid"] == "legacy_dev_1"
        assert dev_row["blog_id"] == "dev"

        tis_row = rows[1]
        assert tis_row["post_uid"] == "legacy_tis_1"
        assert tis_row["blog_id"] == "softwin"

        # Verify new platforms can now be inserted without constraint violation
        cursor.execute("""
        INSERT INTO blog_posts (post_uid, platform, blog_id, title, file_path, status)
        VALUES ('stock_1', 'stock', 'stock', 'Stock Market Analysis', 'stock/p1.md', 'DRAFT')
        """)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM blog_posts WHERE platform = 'stock'")
        assert cursor.fetchone()[0] == 1
        conn.close()


class TestBlogIdInference:
    def test_infer_blog_id_rules(self):
        assert infer_blog_id({"platform": "dev"}) == "dev"
        assert infer_blog_id({"platform": "tistory"}) == "softwin"
        assert infer_blog_id({"platform": "gear"}) == "gear"
        assert infer_blog_id({"platform": "stock"}) == "stock"
        assert infer_blog_id({"platform": "markets"}) == "markets"

        # Naver sub-blogs
        assert infer_blog_id({"platform": "naver", "file_path": "posts/tidynote_excel.md"}) == "tidynote"
        assert infer_blog_id({"platform": "naver", "url": "https://blog.naver.com/hasvica/123"}) == "tidynote"
        assert infer_blog_id({"platform": "naver", "file_path": "posts/naver/hasvica_01.md"}) == "tidynote"
        assert infer_blog_id({"platform": "naver", "slug": "infopiece-vitamin-d"}) == "infopiece"
        assert infer_blog_id({"platform": "naver", "file_path": "author_mhsjkk/doc.md"}) == "infopiece"
        assert infer_blog_id({"platform": "naver", "url": "https://blog.naver.com/mhsjkk/12345"}) == "infopiece"
        assert infer_blog_id({"platform": "naver", "file_path": "posts/solidlog_welfare.md"}) == "solidlog"

        # Explicit override
        assert infer_blog_id({"platform": "tistory", "blog_id": "custom_blog"}) == "custom_blog"


class TestOperationsCRUD:
    def test_upsert_and_get_operations(self, memory_db):
        data = {
            "post_uid": "uid_dev_100",
            "platform": "dev",
            "track": "Track 1",
            "title": "Kernel Memory Tuning",
            "slug": "kernel-memory-tuning",
            "category": "Kernel & OS",
            "tags": ["Linux", "Kernel", "Performance"],
            "file_path": "blogs/dev/_posts/2026-11-17-kernel.md",
            "status": "DRAFT",
            "content_length": 3500
        }

        # 1. Insert new post
        post_id = upsert_post(data, conn=memory_db)
        assert post_id > 0

        # 2. Get by ID
        post_by_id = get_post_by_id(post_id, conn=memory_db)
        assert post_by_id is not None
        assert post_by_id["title"] == "Kernel Memory Tuning"
        assert post_by_id["tags"] == "Linux, Kernel, Performance"
        assert post_by_id["blog_id"] == "dev"

        # 3. Get by File
        post_by_file = get_post_by_file(data["file_path"], conn=memory_db)
        assert post_by_file is not None
        assert post_by_file["id"] == post_id

        # 4. Get by UID
        post_by_uid = get_post_by_uid(data["post_uid"], conn=memory_db)
        assert post_by_uid is not None
        assert post_by_uid["id"] == post_id

        # 5. Get by Slug
        post_by_slug = get_post_by_slug("dev", "kernel-memory-tuning", conn=memory_db)
        assert post_by_slug is not None
        assert post_by_slug["id"] == post_id

        # 6. Update existing post via upsert (matching file_path)
        update_data = {
            "file_path": data["file_path"],
            "title": "Kernel Memory Tuning (Revised)",
            "status": "PUBLISHED",
            "url": "https://dev.ideaspot360.com/kernel-memory-tuning.html"
        }
        updated_id = upsert_post(update_data, conn=memory_db)
        assert updated_id == post_id

        refreshed = get_post_by_id(post_id, conn=memory_db)
        assert refreshed["title"] == "Kernel Memory Tuning (Revised)"
        assert refreshed["status"] == "PUBLISHED"
        assert refreshed["url"] == "https://dev.ideaspot360.com/kernel-memory-tuning.html"

    def test_list_and_search_posts(self, memory_db):
        posts = [
            {
                "post_uid": "p1", "platform": "dev", "blog_id": "dev", "track": "Track 1",
                "title": "FastAPI Async Guide", "category": "Backend", "tags": "Python, API",
                "file_path": "dev/p1.md", "status": "PUBLISHED"
            },
            {
                "post_uid": "p2", "platform": "tistory", "blog_id": "softwin", "track": "Track 2",
                "title": "Python 비동기 프로그래밍 기초", "category": "프로그래밍 언어", "tags": "Python, Async",
                "file_path": "tistory/p2.md", "status": "PUBLISHED"
            },
            {
                "post_uid": "p3", "platform": "stock", "blog_id": "stock", "track": "Track 1",
                "title": "미국 배당주 ETF 심층 분석", "category": "ETF", "tags": "Dividend, Stock",
                "file_path": "stock/p3.md", "status": "DRAFT"
            }
        ]
        for p in posts:
            upsert_post(p, conn=memory_db)

        # Filter by platform
        devs = list_posts(platform="dev", conn=memory_db)
        assert len(devs) == 1
        assert devs[0]["post_uid"] == "p1"

        # Filter by status
        published = list_posts(status="PUBLISHED", conn=memory_db)
        assert len(published) == 2

        # Pagination and order
        ordered = list_posts(limit=2, offset=1, order_by="id ASC", conn=memory_db)
        assert len(ordered) == 2
        assert ordered[0]["post_uid"] == "p2"

        # Search by keyword
        res_python = search_posts("Python", conn=memory_db)
        assert len(res_python) == 2

    def test_list_posts_order_by_sanitization(self, memory_db):
        upsert_post({"post_uid": "ob_1", "platform": "dev", "file_path": "dev/ob1.md", "title": "Beta Post", "status": "DRAFT"}, conn=memory_db)
        upsert_post({"post_uid": "ob_2", "platform": "dev", "file_path": "dev/ob2.md", "title": "Alpha Post", "status": "DRAFT"}, conn=memory_db)

        # Valid order_by
        posts_desc = list_posts(conn=memory_db, order_by="title desc")
        assert len(posts_desc) == 2
        assert posts_desc[0]["title"] == "Beta Post"

        posts_asc = list_posts(conn=memory_db, order_by="title asc")
        assert len(posts_asc) == 2
        assert posts_asc[0]["title"] == "Alpha Post"

        # Malicious or invalid order_by should safely fallback to id ASC without error or SQL injection
        posts_invalid = list_posts(conn=memory_db, order_by="; DROP TABLE blog_posts; --")
        assert len(posts_invalid) == 2
        assert posts_invalid[0]["post_uid"] == "ob_1"

        # Pure whitespace order_by strings should safely fallback to id ASC
        for ws in ("   ", "\t", "\n", "\r\n", "   \t  "):
            posts_ws = list_posts(conn=memory_db, order_by=ws)
            assert len(posts_ws) == 2
            assert posts_ws[0]["post_uid"] == "ob_1"

        # Verify table still exists and is intact
        cursor = memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM blog_posts")
        assert cursor.fetchone()[0] == 2

    def test_update_post_status_and_live_sync(self, memory_db):
        post_id = upsert_post({
            "post_uid": "sync_test",
            "platform": "tistory",
            "file_path": "posts/sync_test.md",
            "title": "Sync Test",
            "status": "RESERVED",
            "reserved_at": "2026-11-17 18:25:00"
        }, conn=memory_db)

        # Update status
        success = update_post_status(
            file_path="posts/sync_test.md",
            status="PUBLISHED",
            published_at="2026-11-17 18:25:05",
            url="https://softwin.tistory.com/99",
            conn=memory_db
        )
        assert success is True

        post = get_post_by_id(post_id, conn=memory_db)
        assert post["status"] == "PUBLISHED"
        assert post["url"] == "https://softwin.tistory.com/99"

        # Live sync update (clearing reserved_at)
        sync_success = update_post_live_sync(
            post_id=post_id,
            status="PUBLISHED",
            url="https://softwin.tistory.com/99",
            published_at="2026-11-17 18:25:05",
            reserved_at=None,
            conn=memory_db
        )
        assert sync_success is True

        refreshed = get_post_by_id(post_id, conn=memory_db)
        assert refreshed["reserved_at"] is None

    def test_logging_and_analytics_cascade(self, memory_db):
        post_id = upsert_post({
            "post_uid": "analytics_test",
            "platform": "dev",
            "file_path": "dev/analytics_test.md",
            "title": "Analytics Post",
            "status": "PUBLISHED"
        }, conn=memory_db)

        # Record log
        log_id = record_log(
            post_id=post_id,
            action="PUBLISH",
            status="SUCCESS",
            message="Post successfully published",
            conn=memory_db
        )
        assert log_id > 0

        # Record analytics (UPSERT)
        a1 = record_analytics(
            post_id=post_id,
            record_date="2026-11-17",
            pageviews=150,
            users=95,
            sessions=110,
            avg_duration_sec=85.5,
            bounce_rate=0.42,
            source="GA4",
            conn=memory_db
        )
        assert a1 > 0

        # Upsert update on same date/source
        a2 = record_analytics(
            post_id=post_id,
            record_date="2026-11-17",
            pageviews=200,
            users=120,
            sessions=140,
            conn=memory_db
        )

        cursor = memory_db.cursor()
        cursor.execute("SELECT pageviews, users FROM post_analytics WHERE post_id = ? AND record_date = ?", (post_id, "2026-11-17"))
        row = cursor.fetchone()
        assert row["pageviews"] == 200
        assert row["users"] == 120

        # Foreign key cascade on delete
        cursor.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
        memory_db.commit()

        cursor.execute("SELECT COUNT(*) FROM post_analytics WHERE post_id = ?", (post_id,))
        assert cursor.fetchone()[0] == 0

        # Log should retain record with post_id set to NULL
        cursor.execute("SELECT post_id, action FROM publishing_logs WHERE id = ?", (log_id,))
        log_row = cursor.fetchone()
        assert log_row["post_id"] is None
        assert log_row["action"] == "PUBLISH"

    def test_get_stats_summary(self, memory_db):
        posts = [
            {"post_uid": "s1", "platform": "dev", "blog_id": "dev", "track": "Track 1", "category": "OS", "pair_id": "pair_01", "file_path": "p1.md", "status": "PUBLISHED"},
            {"post_uid": "s2", "platform": "tistory", "blog_id": "softwin", "track": "Track 2", "category": "OS", "pair_id": "pair_01", "file_path": "p2.md", "status": "PUBLISHED"},
            {"post_uid": "s3", "platform": "stock", "blog_id": "stock", "track": "Track 1", "category": "Finance", "pair_id": "", "file_path": "p3.md", "status": "DRAFT"},
        ]
        for p in posts:
            upsert_post(p, conn=memory_db)

        stats = get_stats_summary(conn=memory_db)
        assert stats["total_posts"] == 3
        assert stats["by_platform"]["dev"] == 1
        assert stats["by_platform"]["tistory"] == 1
        assert stats["by_platform"]["stock"] == 1
        assert stats["by_status"]["PUBLISHED"] == 2
        assert stats["by_status"]["DRAFT"] == 1
        assert stats["by_category"]["OS"] == 2
        assert stats["distinct_pairs"] == 1
