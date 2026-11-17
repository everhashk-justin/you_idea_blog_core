"""
blog_core.database.operations - Comprehensive CRUD Operations for Blog Ecosystem
Provides operations for blog posts, live sync, analytics recording, audit logs, and statistics.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .connection import get_db


@contextmanager
def _connection_context(conn: Optional[sqlite3.Connection] = None):
    """Yields provided connection or manages a new connection context."""
    if conn is not None:
        yield conn
    else:
        with get_db() as new_conn:
            yield new_conn


def infer_blog_id(data: Dict[str, Any]) -> str:
    """
    Infers blog_id based on platform, file path, slug, or url.
    """
    explicit = data.get("blog_id")
    if explicit:
        return str(explicit)

    platform = str(data.get("platform", "dev")).lower()
    if platform == "dev":
        return "dev"
    elif platform == "tistory":
        return "softwin"
    elif platform == "gear":
        return "gear"
    elif platform == "stock":
        return "stock"
    elif platform == "markets":
        return "markets"
    elif platform == "naver":
        f_path = str(data.get("file_path", "")).lower()
        f_slug = str(data.get("slug", "")).lower()
        f_url = str(data.get("url", "")).lower()
        if (
            "tidynote" in f_path
            or "tidynote" in f_slug
            or "tidynote" in f_url
            or "hasvica" in f_path
            or "hasvica" in f_slug
            or "hasvica" in f_url
        ):
            return "tidynote"
        elif (
            "infopiece" in f_path
            or "infopiece" in f_slug
            or "infopiece" in f_url
            or "mhsjkk" in f_path
            or "mhsjkk" in f_url
        ):
            return "infopiece"
        else:
            return "solidlog"
    return platform


def upsert_post(data: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Inserts a new post or updates an existing post matching file_path or post_uid.
    Handles tag list serialization and automatic blog_id inference.
    Returns the post's integer primary key ID.
    """
    with _connection_context(conn) as c:
        cursor = c.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tags = data.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(str(t).strip() for t in tags)

        blog_id = infer_blog_id(data)
        file_path = data.get("file_path")
        post_uid = data.get("post_uid")

        # Find existing record
        row = None
        if file_path and post_uid:
            cursor.execute(
                "SELECT id FROM blog_posts WHERE file_path = ? OR post_uid = ?",
                (file_path, post_uid)
            )
            row = cursor.fetchone()
        elif file_path:
            cursor.execute("SELECT id FROM blog_posts WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
        elif post_uid:
            cursor.execute("SELECT id FROM blog_posts WHERE post_uid = ?", (post_uid,))
            row = cursor.fetchone()

        if row:
            post_id = row[0] if isinstance(row, (tuple, list)) else row["id"]
            cursor.execute("""
            UPDATE blog_posts SET
                post_uid = COALESCE(?, post_uid),
                platform = COALESCE(?, platform),
                blog_id = COALESCE(?, blog_id),
                track = COALESCE(?, track),
                title = COALESCE(?, title),
                slug = COALESCE(?, slug),
                category = COALESCE(?, category),
                tags = COALESCE(?, tags),
                file_path = COALESCE(?, file_path),
                status = COALESCE(?, status),
                reserved_at = COALESCE(?, reserved_at),
                published_at = COALESCE(?, published_at),
                url = COALESCE(?, url),
                pair_id = COALESCE(?, pair_id),
                content_length = COALESCE(?, content_length),
                updated_at = ?
            WHERE id = ?
            """, (
                post_uid,
                data.get("platform"),
                blog_id,
                data.get("track"),
                data.get("title"),
                data.get("slug"),
                data.get("category"),
                tags,
                file_path,
                data.get("status"),
                data.get("reserved_at"),
                data.get("published_at"),
                data.get("url"),
                data.get("pair_id"),
                data.get("content_length"),
                now_str,
                post_id
            ))
            return int(post_id)
        else:
            effective_uid = post_uid or f"{data.get('platform', 'post')}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            cursor.execute("""
            INSERT INTO blog_posts (
                post_uid, platform, blog_id, track, title, slug, category, tags,
                file_path, status, reserved_at, published_at, url, pair_id,
                content_length, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                effective_uid,
                data.get("platform", "dev"),
                blog_id,
                data.get("track"),
                data.get("title", ""),
                data.get("slug"),
                data.get("category"),
                tags,
                file_path,
                data.get("status", "DRAFT"),
                data.get("reserved_at"),
                data.get("published_at"),
                data.get("url"),
                data.get("pair_id"),
                data.get("content_length", 0),
                now_str,
                now_str
            ))
            return int(cursor.lastrowid)


def get_post_by_file(file_path: str, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    """Finds a single post by file_path."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("SELECT * FROM blog_posts WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_post_by_id(post_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    """Finds a single post by primary key id."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_post_by_uid(post_uid: str, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    """Finds a single post by unique post_uid."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("SELECT * FROM blog_posts WHERE post_uid = ?", (post_uid,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_post_by_slug(platform: str, slug: str, conn: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    """Finds a single post by platform and slug."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("SELECT * FROM blog_posts WHERE platform = ? AND slug = ?", (platform, slug))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_posts(
    platform: Optional[str] = None,
    blog_id: Optional[str] = None,
    track: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[dict]:
    """Lists posts matching optional filters, pagination, and sorting."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        query = "SELECT * FROM blog_posts WHERE 1=1"
        params: list = []

        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if blog_id:
            query += " AND blog_id = ?"
            params.append(blog_id)
        if track:
            query += " AND track = ?"
            params.append(track)
        if status:
            query += " AND status = ?"
            params.append(status)

        # Whitelist sorting columns and directions to prevent invalid SQL injection
        sort_col = "id ASC"
        if order_by and order_by.strip():
            parts = order_by.strip().split()
            if parts:
                col = parts[0].lower()
                direction = parts[1].upper() if len(parts) > 1 else "ASC"
                valid_cols = {
                    "id", "created_at", "updated_at", "published_at", "reserved_at",
                    "title", "content_length", "status", "platform", "blog_id", "slug"
                }
                if col in valid_cols and direction in ("ASC", "DESC"):
                    sort_col = f"{col} {direction}"
                else:
                    sort_col = "id ASC"

        query += f" ORDER BY {sort_col}"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset or 0)])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def search_posts(keyword: str, conn: Optional[sqlite3.Connection] = None) -> List[dict]:
    """Searches posts across title, category, tags, slug, and blog_id."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        pattern = f"%{keyword}%"
        cursor.execute("""
        SELECT * FROM blog_posts
        WHERE title LIKE ? OR category LIKE ? OR tags LIKE ? OR slug LIKE ? OR blog_id LIKE ?
        ORDER BY id DESC
        """, (pattern, pattern, pattern, pattern, pattern))
        return [dict(row) for row in cursor.fetchall()]


def update_post_status(
    file_path: str,
    status: str,
    reserved_at: Optional[str] = None,
    published_at: Optional[str] = None,
    url: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> bool:
    """Updates post status, timestamps, and URL by file path."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        UPDATE blog_posts SET
            status = ?,
            reserved_at = COALESCE(?, reserved_at),
            published_at = COALESCE(?, published_at),
            url = COALESCE(?, url),
            updated_at = ?
        WHERE file_path = ?
        """, (status, reserved_at, published_at, url, now_str, file_path))
        return cursor.rowcount > 0


def update_post_live_sync(
    post_id: int,
    status: str,
    url: Optional[str] = None,
    published_at: Optional[str] = None,
    reserved_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> bool:
    """Updates live synchronization status, published URL/date, and explicitly sets reserved_at."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        UPDATE blog_posts SET
            status = ?,
            url = COALESCE(?, url),
            published_at = COALESCE(?, published_at),
            reserved_at = ?,
            updated_at = ?
        WHERE id = ?
        """, (status, url, published_at, reserved_at, now_str, post_id))
        return cursor.rowcount > 0


def record_log(
    post_id: Optional[int],
    action: str,
    status: str,
    message: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """Records an audit log entry in publishing_logs."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("""
        INSERT INTO publishing_logs (post_id, action, status, message)
        VALUES (?, ?, ?, ?)
        """, (post_id, action, status, message or ""))
        return int(cursor.lastrowid)


def record_analytics(
    post_id: int,
    record_date: str,
    pageviews: int = 0,
    users: int = 0,
    sessions: int = 0,
    avg_duration_sec: float = 0.0,
    bounce_rate: float = 0.0,
    source: str = "GA4",
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """Records or updates daily performance snapshot in post_analytics (UPSERT)."""
    with _connection_context(conn) as c:
        cursor = c.cursor()
        cursor.execute("""
        INSERT INTO post_analytics (
            post_id, record_date, pageviews, users, sessions, avg_duration_sec, bounce_rate, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id, record_date, source) DO UPDATE SET
            pageviews = excluded.pageviews,
            users = excluded.users,
            sessions = excluded.sessions,
            avg_duration_sec = excluded.avg_duration_sec,
            bounce_rate = excluded.bounce_rate,
            created_at = datetime('now', 'localtime')
        """, (post_id, record_date, pageviews, users, sessions, avg_duration_sec, bounce_rate, source))
        return int(cursor.lastrowid)


def get_stats_summary(conn: Optional[sqlite3.Connection] = None) -> dict:
    """Aggregates overall blog ecosystem statistics."""
    with _connection_context(conn) as c:
        cursor = c.cursor()

        cursor.execute("SELECT COUNT(*) FROM blog_posts")
        total_posts = cursor.fetchone()[0]

        cursor.execute("SELECT platform, COUNT(*) FROM blog_posts GROUP BY platform")
        by_platform = dict(cursor.fetchall())

        cursor.execute("SELECT COALESCE(blog_id, platform) as b_id, COUNT(*) FROM blog_posts GROUP BY b_id")
        by_blog = dict(cursor.fetchall())

        cursor.execute("SELECT track, COUNT(*) FROM blog_posts GROUP BY track")
        by_track = dict(cursor.fetchall())

        cursor.execute("SELECT status, COUNT(*) FROM blog_posts GROUP BY status")
        by_status = dict(cursor.fetchall())

        cursor.execute("""
        SELECT category, COUNT(*) as cnt FROM blog_posts
        WHERE category IS NOT NULL AND category != ''
        GROUP BY category ORDER BY cnt DESC
        """)
        by_category = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(DISTINCT pair_id) FROM blog_posts WHERE pair_id IS NOT NULL AND pair_id != ''")
        distinct_pairs = cursor.fetchone()[0]

        return {
            "total_posts": total_posts,
            "by_platform": by_platform,
            "by_blog": by_blog,
            "by_track": by_track,
            "by_status": by_status,
            "by_category": by_category,
            "distinct_pairs": distinct_pairs
        }
