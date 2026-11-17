"""
blog_core.database - Centralized Database Package for IdeaSpot360 Ecosystem
Re-exports connection managers, schema definitions, and CRUD operations.
"""

from .connection import get_db, init_db, resolve_db_path, DEFAULT_SHARED_DB_PATH
from .schema import (
    SCHEMA_DDL,
    INDEXES_DDL,
    init_db_schema,
    migrate_schema_if_needed,
)
from .operations import (
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

__all__ = [
    "get_db",
    "init_db",
    "resolve_db_path",
    "DEFAULT_SHARED_DB_PATH",
    "SCHEMA_DDL",
    "INDEXES_DDL",
    "init_db_schema",
    "migrate_schema_if_needed",
    "upsert_post",
    "get_post_by_file",
    "get_post_by_id",
    "get_post_by_uid",
    "get_post_by_slug",
    "list_posts",
    "search_posts",
    "update_post_status",
    "update_post_live_sync",
    "record_log",
    "record_analytics",
    "get_stats_summary",
    "infer_blog_id",
]
