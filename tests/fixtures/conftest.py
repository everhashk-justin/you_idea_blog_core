# -*- coding: utf-8 -*-
"""
tests.fixtures.conftest - Reusable Pytest Fixtures for 01_you_idea_blog_core

Provides test fixtures for:
- Sample markdown posts (valid and invalid across all platforms)
- Temporary post file creation
- Gatekeeper instances (standard and strict)
- Clean and isolated RuleRegistry instances
- Mock SQLite database connections and files (in-memory and WAL-mode tempfile)
- Mock multi-blog ecosystem directories for asset synchronization
- Mock Google service account credentials
- Dynamic BaseRule subclasses for discovery testing
"""

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Callable, Dict, Generator, List, Optional, Type

import pytest

from blog_core.engine.base_rule import BaseRule
from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.engine.models import Severity, Violation
from blog_core.engine.registry import RuleRegistry
from blog_core.database import get_db, init_db
from blog_core.database.schema import init_db_schema


@pytest.fixture(scope="session")
def fixtures_root() -> Path:
    """Return the absolute path to tests/fixtures."""
    return Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def sample_posts_dir(fixtures_root: Path) -> Path:
    """Return the absolute path to tests/fixtures/sample_posts."""
    path = fixtures_root / "sample_posts"
    assert path.exists(), f"Sample posts directory not found: {path}"
    return path


@pytest.fixture
def sample_posts_map(sample_posts_dir: Path) -> Dict[str, Path]:
    """Return a mapping of post stem name to its Path."""
    return {p.stem: p for p in sample_posts_dir.glob("*.md")}


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory that is automatically cleaned up."""
    d = Path(tempfile.mkdtemp(prefix="blog_core_fixture_"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_post_factory(temp_dir: Path) -> Callable[[str, Optional[str]], Path]:
    """Factory fixture to create a temporary markdown post file."""
    counter = [0]

    def _create(content: str, filename: Optional[str] = None) -> Path:
        counter[0] += 1
        name = filename or f"test_post_{counter[0]}.md"
        p = temp_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    return _create


@pytest.fixture
def gatekeeper_instance() -> IroncladGatekeeper:
    """Return a standard IroncladGatekeeper instance."""
    return IroncladGatekeeper(strict_mode=False)


@pytest.fixture
def strict_gatekeeper() -> IroncladGatekeeper:
    """Return a strict-mode IroncladGatekeeper instance."""
    return IroncladGatekeeper(strict_mode=True)


@pytest.fixture
def clean_registry() -> RuleRegistry:
    """Return an isolated, undiscovered RuleRegistry instance."""
    return RuleRegistry()


@pytest.fixture
def mock_db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Provide an in-memory SQLite database connection with initialized schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def mock_temp_db_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Provide a temporary SQLite database file on disk with WAL mode enabled."""
    db_path = temp_dir / "test_posts.db"
    init_db(str(db_path))
    yield db_path


@pytest.fixture
def mock_ecosystem(temp_dir: Path) -> Path:
    """
    Construct a mock multi-blog ecosystem directory structure:
    - blogs/dev/assets/js & css
    - blogs/markets/assets/js & css
    - blogs/gear/assets/js & css
    - blogs/stock/assets/js & css
    """
    eco = temp_dir / "mock_ecosystem"
    blogs = ["dev", "markets", "gear", "stock"]
    for blog in blogs:
        js_dir = eco / "blogs" / blog / "assets" / "js"
        css_dir = eco / "blogs" / blog / "assets" / "css"
        js_dir.mkdir(parents=True, exist_ok=True)
        css_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy initial files
        (js_dir / "lightbox.js").write_text("// initial js", encoding="utf-8")
        (css_dir / "lightbox.css").write_text("/* initial css */", encoding="utf-8")

    return eco


@pytest.fixture
def mock_credentials_file(temp_dir: Path) -> Path:
    """Create a temporary valid mock Google Service Account credentials JSON."""
    creds_data = {
        "type": "service_account",
        "project_id": "mock-idea-blog-project",
        "private_key_id": "mock_key_id_123456",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_KEY\n-----END PRIVATE KEY-----\n",
        "client_email": "mock-service@mock-idea-blog-project.iam.gserviceaccount.com",
        "client_id": "123456789012345678901",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mock.iam.gserviceaccount.com"
    }
    creds_path = temp_dir / "service_account.json"
    creds_path.write_text(json.dumps(creds_data, indent=2), encoding="utf-8")
    return creds_path


@pytest.fixture
def dynamic_rule_factory() -> Callable[[str, str, Optional[List[str]]], Type[BaseRule]]:
    """Factory to create a dynamic BaseRule class for registry and discovery testing."""
    def _create(rule_id: str, gate_id: str = "GATE_1", platforms: Optional[List[str]] = None) -> Type[BaseRule]:
        class DynamicTestRule(BaseRule):
            pass

        DynamicTestRule.rule_id = rule_id
        DynamicTestRule.gate_id = gate_id
        DynamicTestRule.gate_name = f"Test Gate for {rule_id}"
        DynamicTestRule.platforms = platforms
        DynamicTestRule.default_severity = Severity.REJECT

        def check(self, ctx):
            violations = []
            if "FAIL_TEST_TRIGGER" in ctx.content:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet="FAIL_TEST_TRIGGER",
                    message=f"Triggered test rule {self.rule_id}",
                    fix_hint="Remove trigger"
                ))
            return violations

        DynamicTestRule.check = check
        return DynamicTestRule

    return _create
