"""
blog_core.analytics.ga4 - Google Analytics 4 (GA4) Data API Client
Provides reporting methods for active users, top pages, traffic sources, countries, and real-time.
"""

import os
from typing import Optional, List, Tuple, Dict, Any
from .credentials import find_credentials


class GA4AnalyticsClient:
    """
    GA4 Data API Client with lazy authentication and query helpers.
    """

    def __init__(self, property_id: str, credentials_path: Optional[str] = None):
        self.property_id = str(property_id)
        self.credentials_path = credentials_path
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        key_path = find_credentials(explicit_path=self.credentials_path)
        if not key_path:
            raise FileNotFoundError(
                "Google Service Account JSON credentials not found. "
                "Provide credentials_path, set GOOGLE_APPLICATION_CREDENTIALS, "
                "or place credentials.json in search paths."
            )

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
        except ImportError as e:
            raise RuntimeError(
                "google-analytics-data package is required for GA4 queries. "
                "Install it via `pip install google-analytics-data`."
            ) from e

        self._client = BetaAnalyticsDataClient()
        return self._client

    def fetch_summary(self, days: int = 7) -> Dict[str, int]:
        """
        Fetches summary metrics for the given lookback period:
        active users, new users, sessions, pageviews, and user engagement duration.
        """
        from google.analytics.data_v1beta.types import RunReportRequest, Metric, DateRange

        client = self._get_client()
        req = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="newUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="userEngagementDuration"),
            ]
        )
        res = client.run_report(req)
        if not res.rows:
            return {"users": 0, "new_users": 0, "sessions": 0, "views": 0, "duration": 0}

        vals = res.rows[0].metric_values

        def _get_val(idx: int, default: int = 0) -> int:
            return int(float(vals[idx].value)) if idx < len(vals) else default

        return {
            "users": _get_val(0),
            "new_users": _get_val(1),
            "sessions": _get_val(2),
            "views": _get_val(3),
            "duration": _get_val(4),
        }

    def fetch_top_pages(self, limit: int = 5, days: int = 7) -> List[Tuple[str, str, str, str]]:
        """
        Fetches top pages by screenPageViews.
        Returns list of tuples: (pageTitle, pagePath, views, users)
        """
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Metric, Dimension, DateRange, OrderBy
        )

        client = self._get_client()
        req = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="pageTitle"), Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
            limit=limit
        )
        res = client.run_report(req)
        pages = []
        for row in res.rows:
            title = row.dimension_values[0].value
            path = row.dimension_values[1].value
            views = row.metric_values[0].value
            users = row.metric_values[1].value
            pages.append((title, path, views, users))
        return pages

    def fetch_sources(self, limit: int = 5, days: int = 7) -> List[Tuple[str, str, str]]:
        """
        Fetches top traffic acquisition sources (sessionSource / sessionMedium).
        Returns list of tuples: (source_medium, sessions, users)
        """
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Metric, Dimension, DateRange, OrderBy
        )

        client = self._get_client()
        req = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="sessionSource"), Dimension(name="sessionMedium")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=limit
        )
        res = client.run_report(req)
        sources = []
        for row in res.rows:
            source = row.dimension_values[0].value
            medium = row.dimension_values[1].value
            sessions = row.metric_values[0].value
            users = row.metric_values[1].value
            sources.append((f"{source} / {medium}", sessions, users))
        return sources

    def fetch_realtime(self) -> int:
        """
        Fetches real-time active users over the past 30 minutes.
        """
        from google.analytics.data_v1beta.types import RunRealtimeReportRequest, Metric

        client = self._get_client()
        try:
            req = RunRealtimeReportRequest(
                property=f"properties/{self.property_id}",
                metrics=[Metric(name="activeUsers")]
            )
            res = client.run_realtime_report(req)
            return int(res.rows[0].metric_values[0].value) if res.rows else 0
        except Exception:
            return 0

    def fetch_countries(self, limit: int = 7, days: int = 7) -> List[Tuple[str, str, str]]:
        """
        Fetches top visiting countries.
        Returns list of tuples: (country, users, views)
        """
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Metric, Dimension, DateRange, OrderBy
        )

        client = self._get_client()
        req = RunReportRequest(
            property=f"properties/{self.property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="activeUsers"), Metric(name="screenPageViews")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="activeUsers"), desc=True)],
            limit=limit
        )
        res = client.run_report(req)
        countries = []
        for row in res.rows:
            country = row.dimension_values[0].value
            users = row.metric_values[0].value
            views = row.metric_values[1].value
            countries.append((country, users, views))
        return countries
