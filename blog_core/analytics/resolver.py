"""
blog_core.analytics.resolver - Post ID Resolution Utility
Normalizes and resolves GA4/GSC page paths and titles to internal blog_posts.id.
"""

import re
import sqlite3
from urllib.parse import unquote
from typing import Optional, Any


def resolve_post_id(
    conn: Any,
    title: Optional[str] = None,
    page_path: Optional[str] = None,
    platform: Optional[str] = None
) -> Optional[int]:
    """
    Identifies the unique blog_posts.id matching a GA4/GSC page title and path.
    Applies 9-stage robust normalization:
    1. URL decode & query/hash parameter stripping.
    2. /index.html and /index.htm suffix normalization.
    3. Root homepage path resolution via platform and title keyword heuristic.
    4. Multi-language knowledge base home routes (/en, /ko, /ja).
    5. Fixed informational routes (about.html, privacy.html).
    6. Direct URL substring matching.
    7. Filename and slug pattern matching.
    8. Tistory numeric post id matching (/57 -> url ending with /57).
    9. Core title keyword matching.
    """
    cursor = conn.cursor() if hasattr(conn, "cursor") else conn

    def _get_id(row) -> Optional[int]:
        if not row:
            return None
        if isinstance(row, (tuple, list)):
            return int(row[0])
        elif isinstance(row, (dict, sqlite3.Row)):
            return int(row["id"])
        return None

    # 1. URL decoding and stripping query parameters & hash fragments
    safe_title = str(title or "").strip()
    decoded_path = unquote(page_path or "").strip()
    clean_path = decoded_path.split("?")[0].split("#")[0].strip().strip("/")

    # 2. Normalize /index.html and /index.htm
    if clean_path.endswith("/index.html"):
        clean_path = clean_path[:-11].rstrip("/")
    elif clean_path.endswith("/index.htm"):
        clean_path = clean_path[:-10].rstrip("/")
    elif clean_path in ("index.html", "index.htm"):
        clean_path = ""

    # 3. Root main page (empty clean_path)
    if not clean_path:
        target_platform = platform.lower() if platform else None
        if not target_platform:
            if any(k in safe_title for k in ["증시", "맥락트레이딩", "stock"]):
                target_platform = "stock"
            elif any(k in safe_title for k in ["H-GEAR", "기어", "gear"]):
                target_platform = "gear"
            elif any(k in safe_title for k in ["Market Context", "markets", "마켓"]):
                target_platform = "markets"
            elif any(k in safe_title for k in ["IdeaSpot360 Dev", "개발", "Dev"]):
                target_platform = "dev"
            else:
                target_platform = "dev"

        cursor.execute(
            "SELECT id FROM blog_posts WHERE platform = ? AND slug = ?",
            (target_platform, f"{target_platform}-home")
        )
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

        # Fallback to dev-home
        cursor.execute("SELECT id FROM blog_posts WHERE platform = 'dev' AND slug = 'dev-home'")
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    # 4. Gear language-specific knowledge base homes (/en, /ko, /ja)
    if clean_path in ("en", "ko", "ja"):
        cursor.execute(
            "SELECT id FROM blog_posts WHERE platform = 'gear' AND slug = ?",
            (f"gear-{clean_path}-home",)
        )
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    # 5. Dev blog fixed informational pages
    if clean_path == "about.html":
        cursor.execute("SELECT id FROM blog_posts WHERE platform = 'dev' AND slug = 'dev-about'")
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid
    if clean_path == "privacy.html":
        cursor.execute("SELECT id FROM blog_posts WHERE platform = 'dev' AND slug = 'dev-privacy'")
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    # 6. Direct URL matching (clean_path length >= 3)
    if len(clean_path) >= 3:
        if platform:
            cursor.execute(
                "SELECT id FROM blog_posts WHERE platform = ? AND url LIKE ?",
                (platform, f"%{clean_path}%")
            )
        else:
            cursor.execute("SELECT id FROM blog_posts WHERE url LIKE ?", (f"%{clean_path}%",))
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    # 7. Filename / slug pattern matching
    slug_match = re.search(r"([^/]+?)(?:\.html|\.md)?$", clean_path)
    if slug_match:
        file_slug = slug_match.group(1)
        if len(file_slug) >= 3:
            if platform:
                cursor.execute(
                    "SELECT id FROM blog_posts WHERE platform = ? AND (slug = ? OR slug LIKE ?)",
                    (platform, file_slug, f"%{file_slug}")
                )
            else:
                cursor.execute(
                    "SELECT id FROM blog_posts WHERE slug = ? OR slug LIKE ?",
                    (file_slug, f"%{file_slug}")
                )
            pid = _get_id(cursor.fetchone())
            if pid:
                return pid

    # 8. Tistory numeric post number matching (e.g. /57 -> https://softwin.tistory.com/57)
    if clean_path.isdigit():
        cursor.execute(
            "SELECT id FROM blog_posts WHERE platform = 'tistory' AND url LIKE ?",
            (f"%/{clean_path}",)
        )
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    # 9. Core title keyword matching
    core_title = safe_title.split("|")[0].split("-")[0].strip()
    if len(core_title) >= 6:
        pattern = f"%{core_title[:25]}%"
        if platform:
            cursor.execute(
                "SELECT id FROM blog_posts WHERE platform = ? AND title LIKE ?",
                (platform, pattern)
            )
        else:
            cursor.execute("SELECT id FROM blog_posts WHERE title LIKE ?", (pattern,))
        pid = _get_id(cursor.fetchone())
        if pid:
            return pid

    return None
