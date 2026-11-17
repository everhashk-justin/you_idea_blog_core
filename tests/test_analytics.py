"""
Unit and integration tests for blog_core.analytics module.
Verifies post_id resolver, lazy credential discovery, GA4 client, and Search Console client.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from blog_core.analytics.credentials import find_credentials
from blog_core.analytics.resolver import resolve_post_id
from blog_core.analytics.ga4 import GA4AnalyticsClient
from blog_core.analytics.search_console import SearchConsoleClient
from blog_core.database.schema import init_db_schema
from blog_core.database.operations import upsert_post


@pytest.fixture
def memory_db():
    """Provides an initialized in-memory database with realistic posts for resolver testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db_schema(conn)

    posts = [
        # Root homes
        {"post_uid": "dev_home", "platform": "dev", "slug": "dev-home", "title": "IdeaSpot360 Dev Hub", "file_path": "dev_home.md", "url": "https://dev.ideaspot360.com/"},
        {"post_uid": "stock_home", "platform": "stock", "slug": "stock-home", "title": "맥락트레이딩 증시 홈", "file_path": "stock_home.md", "url": "https://stock.ideaspot360.com/"},
        {"post_uid": "gear_home", "platform": "gear", "slug": "gear-home", "title": "H-GEAR 기어 아카이브", "file_path": "gear_home.md", "url": "https://gear.ideaspot360.com/"},
        {"post_uid": "markets_home", "platform": "markets", "slug": "markets-home", "title": "Market Context 360", "file_path": "markets_home.md", "url": "https://markets.ideaspot360.com/"},

        # Gear multilingual homes
        {"post_uid": "gear_ko_home", "platform": "gear", "slug": "gear-ko-home", "title": "기어 지식베이스 한국어", "file_path": "gear_ko.md", "url": "https://gear.ideaspot360.com/ko/"},
        {"post_uid": "gear_en_home", "platform": "gear", "slug": "gear-en-home", "title": "Gear Knowledge Base EN", "file_path": "gear_en.md", "url": "https://gear.ideaspot360.com/en/"},

        # Dev fixed pages
        {"post_uid": "dev_about", "platform": "dev", "slug": "dev-about", "title": "About IdeaSpot360 Dev", "file_path": "about.md", "url": "https://dev.ideaspot360.com/about.html"},
        {"post_uid": "dev_privacy", "platform": "dev", "slug": "dev-privacy", "title": "Privacy Policy", "file_path": "privacy.md", "url": "https://dev.ideaspot360.com/privacy.html"},

        # Tistory posts with numeric IDs
        {"post_uid": "tistory_57", "platform": "tistory", "slug": "kafka-cluster-setup", "title": "Kafka 클러스터 장애 극복기", "file_path": "kafka.md", "url": "https://softwin.tistory.com/57"},
        {"post_uid": "tistory_65", "platform": "tistory", "slug": "redis-distributed-lock", "title": "Redis 분산 락 구현 원리", "file_path": "redis.md", "url": "https://softwin.tistory.com/65"},

        # Gear deep URL
        {"post_uid": "gear_conjugate", "platform": "gear", "slug": "01-conjugate-action", "title": "기어 치형 맞물림 원리", "file_path": "conjugate.md", "url": "https://gear.ideaspot360.com/ko/part1-kinematics/01-conjugate-action/"},

        # Dev article by slug
        {"post_uid": "dev_kernel", "platform": "dev", "slug": "2026-11-17-kernel-page-cache-tuning", "title": "Kernel Page Cache Tuning Guide | Dev Deep Dive", "file_path": "kernel.md", "url": "https://dev.ideaspot360.com/2026-11-17-kernel-page-cache-tuning.html"},
    ]

    for p in posts:
        upsert_post(p, conn=conn)

    yield conn
    conn.close()


class TestCredentialsLocator:
    def test_find_credentials_explicit_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            found = find_credentials(explicit_path=temp_path)
            assert found is not None
            assert Path(found).resolve() == Path(temp_path).resolve()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_find_credentials_explicit_nonexistent(self):
        found = find_credentials(explicit_path="non_existent_credentials_12345.json")
        assert found is None

    def test_find_credentials_env_var(self, monkeypatch):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", temp_path)
            found = find_credentials()
            assert found is not None
            assert Path(found).resolve() == Path(temp_path).resolve()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_find_credentials_custom_env_var(self, monkeypatch):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            monkeypatch.setenv("CUSTOM_GOOGLE_CREDS", temp_path)
            found = find_credentials(env_var="CUSTOM_GOOGLE_CREDS")
            assert found is not None
            assert Path(found).resolve() == Path(temp_path).resolve()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_find_credentials_in_search_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_cred = Path(temp_dir) / "service_account.json"
            temp_cred.write_text("{}", encoding="utf-8")

            found = find_credentials(search_paths=[temp_dir])
            assert found is not None
            assert Path(found).resolve() == temp_cred.resolve()

    def test_find_credentials_glob_pattern(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_cred = Path(temp_dir) / "blog-analytics-custom-test.json"
            temp_cred.write_text("{}", encoding="utf-8")

            found = find_credentials(search_paths=[temp_dir])
            assert found is not None
            assert Path(found).resolve() == temp_cred.resolve()


class TestResolver:
    def test_resolve_root_pages_by_title(self, memory_db):
        # Stock home
        p_stock = resolve_post_id(memory_db, title="맥락트레이딩 | 홈", page_path="/")
        assert p_stock is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_stock,)).fetchone()
        assert row["slug"] == "stock-home"

        # Gear home
        p_gear = resolve_post_id(memory_db, title="H-GEAR 포털", page_path="/index.html")
        assert p_gear is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_gear,)).fetchone()
        assert row["slug"] == "gear-home"

        # Dev home
        p_dev = resolve_post_id(memory_db, title="IdeaSpot360 Dev Main", page_path="")
        assert p_dev is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_dev,)).fetchone()
        assert row["slug"] == "dev-home"

    def test_resolve_gear_multilingual_homes(self, memory_db):
        p_ko = resolve_post_id(memory_db, title="기어", page_path="/ko/")
        assert p_ko is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_ko,)).fetchone()
        assert row["slug"] == "gear-ko-home"

        p_en = resolve_post_id(memory_db, title="Gear", page_path="/en/index.html?ref=google")
        assert p_en is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_en,)).fetchone()
        assert row["slug"] == "gear-en-home"

    def test_resolve_dev_fixed_pages(self, memory_db):
        p_about = resolve_post_id(memory_db, title="About", page_path="/about.html")
        assert p_about is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_about,)).fetchone()
        assert row["slug"] == "dev-about"

        p_privacy = resolve_post_id(memory_db, title="Privacy", page_path="/privacy.html#section2")
        assert p_privacy is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_privacy,)).fetchone()
        assert row["slug"] == "dev-privacy"

    def test_resolve_tistory_numeric_id(self, memory_db):
        p57 = resolve_post_id(memory_db, title="소프트윈", page_path="/57")
        assert p57 is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p57,)).fetchone()
        assert row["slug"] == "kafka-cluster-setup"

        p65 = resolve_post_id(memory_db, title="소프트윈", page_path="/65?category=123")
        assert p65 is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p65,)).fetchone()
        assert row["slug"] == "redis-distributed-lock"

    def test_resolve_direct_url_and_slug(self, memory_db):
        # Gear deep URL
        p_gear = resolve_post_id(memory_db, title="치형", page_path="/ko/part1-kinematics/01-conjugate-action/")
        assert p_gear is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_gear,)).fetchone()
        assert row["slug"] == "01-conjugate-action"

        # Slug match with query params
        p_slug = resolve_post_id(
            memory_db,
            title="Kernel Page Cache Tuning",
            page_path="/2026-11-17-kernel-page-cache-tuning.html?utm_source=twitter"
        )
        assert p_slug is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_slug,)).fetchone()
        assert row["slug"] == "2026-11-17-kernel-page-cache-tuning"

    def test_resolve_core_title_keyword(self, memory_db):
        p_title = resolve_post_id(
            memory_db,
            title="Kernel Page Cache Tuning Guide | Dev Deep Dive",
            page_path="/unknown/unmapped/path.html"
        )
        assert p_title is not None
        row = memory_db.execute("SELECT slug FROM blog_posts WHERE id = ?", (p_title,)).fetchone()
        assert row["slug"] == "2026-11-17-kernel-page-cache-tuning"

    def test_resolve_nonexistent_returns_none(self, memory_db):
        result = resolve_post_id(memory_db, title="Unknown Random Article", page_path="/random-404-page")
        assert result is None

    def test_resolve_with_none_or_empty_title_safe(self, memory_db):
        # Must not raise TypeError or AttributeError when title is None or empty
        res_root = resolve_post_id(memory_db, title=None, page_path="/")
        assert res_root is not None

        res_empty = resolve_post_id(memory_db, title="", page_path="")
        assert res_empty is not None

        res_none_path = resolve_post_id(memory_db, title=None, page_path=None)
        assert res_none_path is not None

        res_unmatched = resolve_post_id(memory_db, title=None, page_path="/unmatched/path/random")
        assert res_unmatched is None


class TestGA4AnalyticsClient:
    def test_missing_credentials_raises_file_not_found(self):
        client = GA4AnalyticsClient(property_id="123456", credentials_path="non_existent_key.json")
        with pytest.raises(FileNotFoundError):
            client._get_client()

    @patch("blog_core.analytics.ga4.find_credentials")
    def test_fetch_summary_mock(self, mock_find_cred):
        mock_find_cred.return_value = "dummy_cred.json"

        client = GA4AnalyticsClient(property_id="562280019")

        # Mock BetaAnalyticsDataClient
        mock_beta_client = MagicMock()
        mock_row = MagicMock()
        # activeUsers, newUsers, sessions, screenPageViews, userEngagementDuration
        mock_row.metric_values = [
            MagicMock(value="150"),
            MagicMock(value="110"),
            MagicMock(value="180"),
            MagicMock(value="420"),
            MagicMock(value="85.4"),
        ]
        mock_res = MagicMock()
        mock_res.rows = [mock_row]
        mock_beta_client.run_report.return_value = mock_res

        client._client = mock_beta_client

        summary = client.fetch_summary(days=7)
        assert summary["users"] == 150
        assert summary["new_users"] == 110
        assert summary["sessions"] == 180
        assert summary["views"] == 420
        assert summary["duration"] == 85

    @patch("blog_core.analytics.ga4.find_credentials")
    def test_fetch_summary_short_metrics_safe(self, mock_find_cred):
        mock_find_cred.return_value = "dummy_cred.json"
        client = GA4AnalyticsClient(property_id="562280019")

        mock_beta_client = MagicMock()
        mock_row = MagicMock()
        # Only 2 metric values returned instead of 5
        mock_row.metric_values = [
            MagicMock(value="42"),
            MagicMock(value="10"),
        ]
        mock_res = MagicMock()
        mock_res.rows = [mock_row]
        mock_beta_client.run_report.return_value = mock_res
        client._client = mock_beta_client

        summary = client.fetch_summary(days=7)
        assert summary["users"] == 42
        assert summary["new_users"] == 10
        assert summary["sessions"] == 0
        assert summary["views"] == 0
        assert summary["duration"] == 0

    @patch("blog_core.analytics.ga4.find_credentials")
    def test_fetch_top_pages_mock(self, mock_find_cred):
        mock_find_cred.return_value = "dummy_cred.json"
        client = GA4AnalyticsClient(property_id="562280019")

        mock_beta_client = MagicMock()
        row1 = MagicMock()
        row1.dimension_values = [MagicMock(value="FastAPI Async Guide"), MagicMock(value="/fastapi-guide.html")]
        row1.metric_values = [MagicMock(value="250"), MagicMock(value="120")]

        mock_res = MagicMock()
        mock_res.rows = [row1]
        mock_beta_client.run_report.return_value = mock_res
        client._client = mock_beta_client

        pages = client.fetch_top_pages(limit=1, days=7)
        assert len(pages) == 1
        assert pages[0] == ("FastAPI Async Guide", "/fastapi-guide.html", "250", "120")

    @patch("blog_core.analytics.ga4.find_credentials")
    def test_fetch_realtime_mock(self, mock_find_cred):
        mock_find_cred.return_value = "dummy_cred.json"
        client = GA4AnalyticsClient(property_id="562280019")

        mock_beta_client = MagicMock()
        row1 = MagicMock()
        row1.metric_values = [MagicMock(value="14")]
        mock_res = MagicMock()
        mock_res.rows = [row1]
        mock_beta_client.run_realtime_report.return_value = mock_res
        client._client = mock_beta_client

        rt = client.fetch_realtime()
        assert rt == 14


class TestSearchConsoleClient:
    def test_missing_credentials_raises_file_not_found(self):
        client = SearchConsoleClient(site_url="https://dev.ideaspot360.com/", credentials_path="non_existent.json")
        with pytest.raises(FileNotFoundError):
            client._get_service()

    @patch("blog_core.analytics.search_console.find_credentials")
    def test_search_console_methods_mock(self, mock_find_cred):
        mock_find_cred.return_value = "dummy_cred.json"
        client = SearchConsoleClient(site_url="https://dev.ideaspot360.com/")

        mock_service = MagicMock()

        # Mock sites().list()
        mock_sites_call = MagicMock()
        mock_sites_call.execute.return_value = {
            "siteEntry": [
                {"siteUrl": "https://dev.ideaspot360.com/"},
                {"siteUrl": "https://softwin.tistory.com/"}
            ]
        }
        mock_service.sites.return_value.list.return_value = mock_sites_call

        # Mock searchanalytics().query()
        mock_query_call = MagicMock()
        mock_query_call.execute.return_value = {
            "rows": [
                {"keys": ["linux memory tuning"], "clicks": 25, "impressions": 300, "ctr": 0.083, "position": 3.2}
            ]
        }
        mock_service.searchanalytics.return_value.query.return_value = mock_query_call

        # Mock sitemaps().list()
        mock_sitemap_call = MagicMock()
        mock_sitemap_call.execute.return_value = {
            "sitemap": [
                {"path": "https://dev.ideaspot360.com/sitemap.xml", "lastSubmitted": "2026-11-17"}
            ]
        }
        mock_service.sitemaps.return_value.list.return_value = mock_sitemap_call

        client._service = mock_service

        sites = client.list_accessible_sites()
        assert sites == ["https://dev.ideaspot360.com/", "https://softwin.tistory.com/"]

        analytics = client.query_search_analytics(days=28, row_limit=5)
        assert len(analytics) == 1
        assert analytics[0]["clicks"] == 25

        sitemaps = client.check_sitemaps()
        assert len(sitemaps) == 1
        assert sitemaps[0]["path"] == "https://dev.ideaspot360.com/sitemap.xml"
