"""
blog_core.analytics.search_console - Google Search Console (GSC) API Client
Provides methods to query search analytics, indexed pages, sitemaps, and accessible properties.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .credentials import find_credentials


class SearchConsoleClient:
    """
    Search Console API Client with lazy authentication and search analytics queries.
    """

    def __init__(self, site_url: str, credentials_path: Optional[str] = None):
        self.site_url = str(site_url)
        self.credentials_path = credentials_path
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        key_path = find_credentials(explicit_path=self.credentials_path)
        if not key_path:
            raise FileNotFoundError(
                "Google Service Account JSON credentials not found. "
                "Provide credentials_path, set GOOGLE_APPLICATION_CREDENTIALS, "
                "or place credentials.json in search paths."
            )

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as e:
            raise RuntimeError(
                "google-api-python-client and google-auth packages are required. "
                "Install them via `pip install google-api-python-client google-auth`."
            ) from e

        creds = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        self._service = build("searchconsole", "v1", credentials=creds)
        return self._service

    def list_accessible_sites(self) -> List[str]:
        """
        Lists all site URLs accessible to the authenticated service account.
        """
        service = self._get_service()
        try:
            response = service.sites().list().execute()
            return [entry["siteUrl"] for entry in response.get("siteEntry", [])]
        except Exception:
            return []

    def query_search_analytics(self, days: int = 28, row_limit: int = 10) -> List[Dict[str, Any]]:
        """
        Queries top search queries and impressions/clicks (with 2-day reporting lag adjustment).
        """
        service = self._get_service()
        end_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 2)).strftime("%Y-%m-%d")

        request_body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": row_limit
        }

        try:
            response = service.searchanalytics().query(siteUrl=self.site_url, body=request_body).execute()
            return response.get("rows", [])
        except Exception:
            return []

    def query_top_pages(self, days: int = 28, row_limit: int = 10) -> List[Dict[str, Any]]:
        """
        Queries top receiving landing pages.
        """
        service = self._get_service()
        end_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 2)).strftime("%Y-%m-%d")

        request_body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["page"],
            "rowLimit": row_limit
        }

        try:
            response = service.searchanalytics().query(siteUrl=self.site_url, body=request_body).execute()
            return response.get("rows", [])
        except Exception:
            return []

    def check_sitemaps(self) -> List[Dict[str, Any]]:
        """
        Checks submission and processing status of sitemaps.
        """
        service = self._get_service()
        try:
            response = service.sitemaps().list(siteUrl=self.site_url).execute()
            return response.get("sitemap", [])
        except Exception:
            return []
