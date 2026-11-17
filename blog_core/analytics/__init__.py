"""
blog_core.analytics - Analytics & Resolver Utilities for IdeaSpot360 Ecosystem
Provides GA4 & Search Console API clients, lazy credentials discovery, and URL resolver.
"""

from .credentials import find_credentials, KNOWN_CREDENTIAL_FILENAMES, DEFAULT_SEARCH_DIRS
from .resolver import resolve_post_id
from .ga4 import GA4AnalyticsClient
from .search_console import SearchConsoleClient

__all__ = [
    "find_credentials",
    "KNOWN_CREDENTIAL_FILENAMES",
    "DEFAULT_SEARCH_DIRS",
    "resolve_post_id",
    "GA4AnalyticsClient",
    "SearchConsoleClient",
]
