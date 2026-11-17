# -*- coding: utf-8 -*-
"""
tests.e2e.test_tier4_workloads - Tier 4: Real-World Workloads Suite

Comprehensive end-to-end real-world workload scenarios for 01_you_idea_blog_core:
  Scenario 1: Greenfield Blog Agent Onboarding & Custom Rule Plugin (OCP Extensibility)
  Scenario 2: Multi-Blog Production Asset Deployment (Pan-Zoom Web Assets Sync Pipeline)
  Scenario 3: End-to-End Analytics Ingestion & Post Matching Workflow (GA4 / GSC to posts.db)
  Scenario 4: Full Multi-Domain Content Compliance Audit (16 Real Markdown Posts Across 6 Platforms)
  Scenario 5: Cross-Platform Regression & Mutation Stress Test (Multi-Tenant Isolation & Zero False Alarms)

Authoritative sources:
- ORIGINAL_REQUEST.md (§R1, §R2, §R3, §R4, §R5, §Acceptance Criteria)
- PROJECT.md (§Architecture, §Feature Inventory, §Interface Contracts)
- TEST_INFRA.md (§Real-World Application Scenarios Tier 4)
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Type

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

pytest_plugins = ["tests.fixtures.conftest"]

from blog_core.engine.base_rule import BaseRule
from blog_core.engine.context import (
    RuleContext,
    create_context,
    parse_frontmatter,
    split_frontmatter_and_body,
)
from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.engine.models import GateReport, Severity, Violation
from blog_core.engine.registry import RuleRegistry, default_registry

from blog_core.database import get_db, init_db
from blog_core.database.schema import init_db_schema
from blog_core.database.operations import (
    get_post_by_file,
    get_post_by_id,
    get_stats_summary,
    list_posts,
    record_analytics,
    record_log,
    update_post_live_sync,
    update_post_status,
    upsert_post,
)
from blog_core.analytics.resolver import resolve_post_id
from sync_to_blogs import (
    compute_sha256,
    resolve_master_assets,
    sync_assets,
    TARGET_MAP,
)


# ==============================================================================
# Helpers
# ==============================================================================

def _generate_synthetic_clean_body(lang: str = "en", target_chars: int = 1500) -> str:
    """Generates synthetic compliant filler text exceeding length requirements without cliches."""
    if lang == "en":
        # ~1000 words clean English technical text
        paragraph = (
            "The distributed scheduler optimizes workload placement across heterogeneous nodes "
            "by monitoring kernel metrics, network interface throughput, and memory bandwidth. "
            "Proper queue sizing prevents unexpected buffer saturation during traffic surges. "
            "Each worker daemon maintains an isolated worker pool with deterministic memory limits. "
            "Telemetry signals are aggregated in real time to trigger adaptive rate throttling.\n\n"
        )
        body = "## System Overview and Architectural Analysis\n\n"
        while len(body.split()) < 800:
            body += paragraph
        return body
    else:
        # ~1500 chars clean Korean technical text
        paragraph = (
            "분산 아키텍처 환경에서 스케줄러는 시스템의 처리량과 지연 시간을 균형 있게 제어하기 위해 "
            "노드별 가용 자원과 커널 인터럽트 발생 빈도를 지속적으로 모니터링합니다. "
            "네트워크 링 버퍼의 크기를 적절히 조절함으로써 대규모 패킷 유입 시 발생할 수 있는 "
            "버퍼 오버플로우와 프로세스 기아 현상을 미연에 방지할 수 있습니다. "
            "각 작업 단위는 독립된 스레드 풀에서 실행되며 메모리 할당 상한을 엄격히 준수합니다. "
            "주기적인 성능 프로파일링을 통해 병목 구간을 신속하게 식별하고 최적화 패치를 적용합니다.\n\n"
        )
        body = "## 시스템 구조 및 동작 원리\n\n"
        while len(body.replace(" ", "").replace("\n", "")) < target_chars:
            body += paragraph
        return body


# ==============================================================================
# Scenario 1: Greenfield Blog Agent Onboarding & Custom Rule Plugin
# ==============================================================================

class TestScenario1GreenfieldBlogAgentOnboarding:
    """
    Scenario 1: Greenfield Blog Agent Onboarding & Custom Rule Plugin
    An external blog agent (e.g. for a new platform 'quantum_pulse') onboards onto
    01_you_idea_blog_core. The agent:
    1. Consults AGENT_EXTENSION_GUIDE.md and pyproject.toml.
    2. Develops a custom platform rule class inheriting from BaseRule.
    3. Dynamically registers the rule in RuleRegistry.
    4. Verifies platform whitelist isolation (active for quantum_pulse, inactive for dev/tistory).
    5. Runs IroncladGatekeeper across compliant and non-compliant articles.
    """

    def test_01_greenfield_agent_consults_extension_guide_and_pyproject(self):
        """1.1: Verify agent extension documentation and package editable install specification."""
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"
        assert guide_path.exists(), f"Guide missing: {guide_path}"
        guide_text = guide_path.read_text(encoding="utf-8")

        # Verify guide contains OCP principles and 5-step SOP
        assert "BaseRule" in guide_text
        assert "RuleRegistry" in guide_text
        assert "platforms" in guide_text
        assert "GATE_" in guide_text

        # Verify packaging metadata in pyproject.toml
        pyproj_path = WORKSPACE_ROOT / "pyproject.toml"
        assert pyproj_path.exists()
        pyproj_text = pyproj_path.read_text(encoding="utf-8")
        assert 'name = "you-idea-blog-core"' in pyproj_text or 'name = "blog_core"' in pyproj_text
        assert "blog-gatekeeper" in pyproj_text or "blog_core" in pyproj_text

    def test_02_greenfield_agent_creates_and_registers_dynamic_platform_rule(
        self, clean_registry: RuleRegistry
    ):
        """1.2: External agent defines custom BaseRule plugin and registers it in RuleRegistry."""

        class QuantumSafetyProtocolRule(BaseRule):
            """Custom platform rule for quantum_pulse blog."""
            rule_id = "G4_QUANTUM_SAFETY_PROTOCOL"
            gate_id = "GATE_4"
            gate_name = "Quantum Simulation Safety Protocol"
            description = "Mandates quantum backend declaration and synthetic simulation notice"
            platforms = ["quantum_pulse"]
            default_severity = Severity.REJECT

            def check(self, ctx: RuleContext) -> List[Violation]:
                violations: List[Violation] = []
                backend = ctx.fm_data.get("quantum_backend", "").strip()
                if not backend:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=1,
                        snippet="Missing frontmatter: quantum_backend",
                        message="Frontmatter must specify 'quantum_backend: <simulator|hardware>'",
                        fix_hint="Add 'quantum_backend: aer_simulator' to frontmatter."
                    ))

                if "[QUANTUM SIMULATION PROTOCOL VERIFIED]" not in ctx.content:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=0,
                        snippet="Notice missing",
                        message="Article body lacks mandatory '[QUANTUM SIMULATION PROTOCOL VERIFIED]' notice.",
                        fix_hint="Insert synthetic simulation notice before technical conclusion."
                    ))

                return violations

        # Register custom rule
        reg_rule = clean_registry.register(QuantumSafetyProtocolRule)
        assert reg_rule.rule_id == "G4_QUANTUM_SAFETY_PROTOCOL"
        assert reg_rule.platforms == ["quantum_pulse"]

        # Platform Whitelist Isolation Verification:
        # Rule must be included when target platform is quantum_pulse
        qp_rules = clean_registry.get_rules(platform="quantum_pulse", auto_discover=False)
        assert any(r.rule_id == "G4_QUANTUM_SAFETY_PROTOCOL" for r in qp_rules)

        # Rule must NOT be included for dev, tistory, naver, or markets
        for other_platform in ["dev", "tistory", "naver", "markets", "stock", "gear"]:
            other_rules = clean_registry.get_rules(platform=other_platform, auto_discover=False)
            assert not any(r.rule_id == "G4_QUANTUM_SAFETY_PROTOCOL" for r in other_rules), (
                f"Rule leaked into foreign platform '{other_platform}'!"
            )

    def test_03_greenfield_agent_gatekeeper_verification_workflow(
        self, temp_post_factory: Callable[[str, Optional[str]], Path]
    ):
        """1.3: Run full IroncladGatekeeper verification on compliant and non-compliant articles."""
        # Use a fresh registry with the custom rule registered alongside standard rules
        custom_registry = RuleRegistry()
        custom_registry.discover()

        class QuantumSafetyProtocolRule(BaseRule):
            rule_id = "G4_QUANTUM_SAFETY_PROTOCOL"
            gate_id = "GATE_4"
            gate_name = "Quantum Simulation Safety Protocol"
            platforms = ["quantum_pulse"]
            default_severity = Severity.REJECT

            def check(self, ctx: RuleContext) -> List[Violation]:
                v = []
                if not ctx.fm_data.get("quantum_backend", "").strip():
                    v.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=1,
                        snippet="quantum_backend missing",
                        message="Missing quantum_backend frontmatter",
                        fix_hint="Add quantum_backend: qiskit"
                    ))
                if "[QUANTUM SIMULATION PROTOCOL VERIFIED]" not in ctx.content:
                    v.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=0,
                        snippet="Notice missing",
                        message="Missing mandatory simulation notice",
                        fix_hint="Add notice"
                    ))
                return v

        custom_registry.register(QuantumSafetyProtocolRule)
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=custom_registry)

        # 1. Compliant article for quantum_pulse
        compliant_body = _generate_synthetic_clean_body("en", target_chars=1200)
        compliant_post_text = (
            "---\n"
            "title: \"Quantum Gate Fidelity Optimization in Superconducting Circuits\"\n"
            "category: \"Quantum Computing\"\n"
            "tags: \"quantum, physics, computing\"\n"
            "quantum_backend: \"aer_simulator_v2\"\n"
            "---\n\n"
            "# Quantum Gate Fidelity Optimization\n\n"
            f"{compliant_body}\n\n"
            "```python\n"
            "from qiskit import QuantumCircuit\n"
            "qc = QuantumCircuit(2)\n"
            "qc.h(0)\n"
            "qc.cx(0, 1)\n"
            "```\n\n"
            "[QUANTUM SIMULATION PROTOCOL VERIFIED]\n"
        )
        compliant_file = temp_post_factory(compliant_post_text, "compliant_quantum.md")
        rep_compliant = gatekeeper.verify(str(compliant_file), platform_override="quantum_pulse")

        assert rep_compliant.is_passed is True, f"Compliant post failed: {rep_compliant.violations}"
        assert rep_compliant.score == 100
        assert rep_compliant.reject_count == 0

        # 2. Non-compliant article (missing quantum_backend and simulation notice)
        non_compliant_post_text = (
            "---\n"
            "title: \"Unverified Quantum State Teleportation Algorithm\"\n"
            "category: \"Quantum Computing\"\n"
            "tags: \"quantum, physics\"\n"
            "---\n\n"
            "# Unverified Quantum Teleportation\n\n"
            f"{compliant_body}\n"
        )
        non_compliant_file = temp_post_factory(non_compliant_post_text, "non_compliant_quantum.md")
        rep_non_compliant = gatekeeper.verify(str(non_compliant_file), platform_override="quantum_pulse")

        assert rep_non_compliant.is_passed is False
        assert rep_non_compliant.reject_count >= 2
        qp_violations = [v for v in rep_non_compliant.violations if v.rule_id == "G4_QUANTUM_SAFETY_PROTOCOL"]
        assert len(qp_violations) == 2, f"Expected 2 custom violations, got: {qp_violations}"

        # 3. Cross-Platform Isolation:
        # Same non-compliant file verified under 'dev' must NEVER trigger G4_QUANTUM_SAFETY_PROTOCOL
        rep_as_dev = gatekeeper.verify(str(non_compliant_file), platform_override="dev")
        dev_rule_ids = [v.rule_id for v in rep_as_dev.violations]
        assert "G4_QUANTUM_SAFETY_PROTOCOL" not in dev_rule_ids, (
            "Custom rule leaked into dev evaluation!"
        )


# ==============================================================================
# Scenario 2: Multi-Blog Production Asset Deployment
# ==============================================================================

class TestScenario2MultiBlogProductionAssetDeployment:
    """
    Scenario 2: Multi-Blog Production Asset Deployment
    Complete web asset synchronization pipeline deployment across 4 distinct blog
    repositories (dev, markets, gear, stock).
    Tests:
    1. Pre-sync dry-run preview (verifies zero accidental writes).
    2. Full multi-blog deployment with SHA-256 verification and automatic .bak backup.
    3. Second-pass identical skip (deterministic idempotency and zero redundant writes).
    4. Targeted single blog sync and custom destination sync.
    """

    def test_01_multi_blog_mock_setup_and_dry_run_inspection(self, mock_ecosystem: Path):
        """2.1: Pre-sync dry-run mode detects out-of-date assets without modifying disk."""
        # Initial assets in mock_ecosystem have dummy content "// initial js"
        results = sync_assets(
            target="all",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=True,
            backup=True,
            verify=True,
        )

        assert len(results) == 8  # 4 targets * 2 assets (JS, CSS)
        targets_seen = {r.target_key for r in results}
        assert targets_seen == {"dev", "markets", "gear", "stock"}

        for res in results:
            assert res.status == "WOULD_UPDATE", f"Expected WOULD_UPDATE, got {res.status}"
            assert res.backup_path is None, "Dry run must not create backup files"
            # Verify file on disk was NOT changed
            assert res.dest_path.exists()
            content = res.dest_path.read_text(encoding="utf-8")
            assert "initial" in content, "Dry run must not overwrite existing file"

    def test_02_full_deployment_with_backup_and_sha256_verification(self, mock_ecosystem: Path):
        """2.2: Full sync copies master assets, creates timestamped backups, and verifies SHA-256."""
        master_js, master_css = resolve_master_assets(WORKSPACE_ROOT)
        master_js_sha = compute_sha256(master_js)
        master_css_sha = compute_sha256(master_css)

        results = sync_assets(
            target="all",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )

        assert len(results) == 8
        for res in results:
            assert res.status == "SYNCED", f"Target {res.target_key} {res.file_type} failed: {res.error_message}"
            assert res.dest_sha256_after is not None

            # Verify deployed file SHA-256 matches master exactly
            expected_sha = master_js_sha if res.file_type == "JS" else master_css_sha
            assert res.dest_sha256_after == expected_sha
            assert compute_sha256(res.dest_path) == expected_sha

            # Verify backup file was created and retains original dummy content
            assert res.backup_path is not None
            assert res.backup_path.exists()
            backup_content = res.backup_path.read_text(encoding="utf-8")
            assert "initial" in backup_content

    def test_03_second_pass_identical_skip_and_idempotency(self, mock_ecosystem: Path):
        """2.3: Second sync pass detects identical hashes and skips writes without redundant backups."""
        # First sync pass: updates files
        sync_assets(
            target="all",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=False,
            verify=True,
        )

        # Count backup files before second pass
        baks_before = list(mock_ecosystem.rglob("*.bak"))

        # Second sync pass: must detect all identical
        results_second = sync_assets(
            target="all",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )

        assert len(results_second) == 8
        for res in results_second:
            assert res.status == "IDENTICAL", f"Expected IDENTICAL, got {res.status}"
            assert res.backup_path is None, "Identical skip must not generate backup files"

        # Verify no new backup files were created on the second pass
        baks_after = list(mock_ecosystem.rglob("*.bak"))
        assert len(baks_after) == len(baks_before)

    def test_04_targeted_single_blog_deployment_and_custom_destination(
        self, mock_ecosystem: Path, temp_dir: Path
    ):
        """2.4: Targeted deployment to single blog and custom directory destinations."""
        master_js, master_css = resolve_master_assets(WORKSPACE_ROOT)
        master_js_sha = compute_sha256(master_js)

        # 1. Targeted single blog: markets only
        results_markets = sync_assets(
            target="markets",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )
        assert len(results_markets) == 2
        assert all(r.target_key == "markets" for r in results_markets)
        assert all(r.status == "SYNCED" for r in results_markets)

        # 2. Custom external directory deployment
        custom_out = temp_dir / "external_partner_blog" / "assets"
        custom_out.mkdir(parents=True, exist_ok=True)

        results_custom = sync_assets(
            target=str(custom_out),
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )
        assert len(results_custom) == 2
        assert results_custom[0].target_key == "custom"
        assert results_custom[0].status == "SYNCED"
        assert (custom_out / "js" / "lightbox.js").exists()
        assert compute_sha256(custom_out / "js" / "lightbox.js") == master_js_sha


# ==============================================================================
# Scenario 3: End-to-End Analytics Ingestion & Post Matching Workflow
# ==============================================================================

class TestScenario3AnalyticsIngestionAndPostMatching:
    """
    Scenario 3: End-to-End Analytics Ingestion & Post Matching Workflow
    Simulates production analytics pipelines fetching GA4 and Search Console reports,
    resolving varied URL/path patterns to posts.db IDs via resolve_post_id,
    and updating daily metrics and publishing logs.
    """

    @pytest.fixture
    def seeded_db(self, mock_temp_db_file: Path) -> Path:
        """Seed a clean SQLite database with multi-platform posts."""
        with get_db(str(mock_temp_db_file)) as conn:
            # 1. Dev blog troubleshooting post
            upsert_post({
                "post_uid": "dev-20261117-kernel-softirq",
                "platform": "dev",
                "blog_id": "dev",
                "track": "Track 1",
                "title": "Troubleshooting High CPU Kernel Softirq Storm in Linux Network Stack",
                "slug": "2026-11-17-kernel-softirq",
                "category": "Systems & Networking",
                "tags": "linux, kernel, softirq",
                "file_path": "blogs/dev/_posts/2026-11-17-kernel-softirq.md",
                "status": "PUBLISHED",
                "published_at": "2026-11-17 10:30:00",
                "url": "https://dev.ideaspot360.com/posts/2026-11-17-kernel-softirq.html",
                "content_length": 5346
            }, conn)

            # 2. Dev blog homepage
            upsert_post({
                "post_uid": "dev-home-root",
                "platform": "dev",
                "blog_id": "dev",
                "title": "IdeaSpot360 Dev Home | High-Throughput Engineering",
                "slug": "dev-home",
                "file_path": "blogs/dev/index.html",
                "status": "PUBLISHED",
                "url": "https://dev.ideaspot360.com/",
                "content_length": 1500
            }, conn)

            # 3. Dev blog about page
            upsert_post({
                "post_uid": "dev-about-fixed",
                "platform": "dev",
                "blog_id": "dev",
                "title": "About IdeaSpot360 Dev",
                "slug": "dev-about",
                "file_path": "blogs/dev/about.html",
                "status": "PUBLISHED",
                "url": "https://dev.ideaspot360.com/about.html",
                "content_length": 1200
            }, conn)

            # 4. Markets macro analysis post
            upsert_post({
                "post_uid": "markets-20261117-fed-liquidity",
                "platform": "markets",
                "blog_id": "markets",
                "track": "Track 1",
                "title": "Global Macro Net Liquidity and Quantitative Tightening Dynamics",
                "slug": "fed-liquidity-dynamics",
                "category": "Global Macro & Finance",
                "file_path": "blogs/markets/_posts/2026-11-17-fed-liquidity.md",
                "status": "PUBLISHED",
                "published_at": "2026-11-17 11:00:00",
                "url": "https://markets.ideaspot360.com/fed-liquidity-dynamics",
                "content_length": 4648
            }, conn)

            # 5. Stock dividend ETF post
            upsert_post({
                "post_uid": "stock-20261117-dividend-etf",
                "platform": "stock",
                "blog_id": "stock",
                "title": "미국 배당성장 ETF 및 커버드콜 월배당 분배금 포트폴리오 전략",
                "slug": "us-dividend-etf-strategy",
                "category": "주식 & ETF",
                "file_path": "blogs/stock/_posts/2026-11-17-dividend-etf.md",
                "status": "PUBLISHED",
                "published_at": "2026-11-17 12:15:00",
                "url": "https://stock.ideaspot360.com/us-dividend-etf-strategy",
                "content_length": 3200
            }, conn)

            # 6. Gear Korean knowledge base home
            upsert_post({
                "post_uid": "gear-ko-home-kb",
                "platform": "gear",
                "blog_id": "gear",
                "title": "H-GEAR Studio Korea Knowledge Base",
                "slug": "gear-ko-home",
                "file_path": "blogs/gear/ko/index.html",
                "status": "PUBLISHED",
                "url": "https://gear.ideaspot360.com/ko/",
                "content_length": 2100
            }, conn)

            # 7. Tistory post #57
            upsert_post({
                "post_uid": "tistory-post-57",
                "platform": "tistory",
                "blog_id": "softwin",
                "track": "Track 2",
                "title": "Spring Boot OOM 장애 원인 분석 및 힙 덤프 트러블슈팅 가이드",
                "slug": "57",
                "category": "실무 장애 트러블슈팅",
                "file_path": "posts/57_trouble_oom.md",
                "status": "PUBLISHED",
                "published_at": "2026-11-17 13:40:00",
                "url": "https://softwin.tistory.com/57",
                "content_length": 3800
            }, conn)

        return mock_temp_db_file

    def test_01_seed_multi_platform_posts_in_database(self, seeded_db: Path):
        """3.1: Verify seeded multi-blog posts and ecosystem summary metrics."""
        with get_db(str(seeded_db)) as conn:
            stats = get_stats_summary(conn)
            assert stats["total_posts"] == 7
            assert stats["by_status"]["PUBLISHED"] == 7
            assert stats["by_platform"]["dev"] == 3
            assert stats["by_platform"]["markets"] == 1
            assert stats["by_platform"]["stock"] == 1
            assert stats["by_platform"]["gear"] == 1
            assert stats["by_platform"]["tistory"] == 1

            all_posts = list_posts(conn=conn)
            assert len(all_posts) == 7

    def test_02_resolve_diverse_ga4_and_gsc_paths_to_posts(self, seeded_db: Path):
        """3.2: Resolve diverse real-world URL/path patterns to posts.db IDs via resolve_post_id."""
        with get_db(str(seeded_db)) as conn:
            # 1. Root homepage with query params and title
            pid_home = resolve_post_id(
                conn,
                title="IdeaSpot360 Dev Home | High-Throughput Engineering",
                page_path="/?utm_source=twitter&utm_medium=social#overview",
                platform="dev"
            )
            assert pid_home is not None
            home_post = get_post_by_id(pid_home, conn)
            assert home_post["slug"] == "dev-home"

            # 2. Fixed about route
            pid_about = resolve_post_id(conn, page_path="/about.html", platform="dev")
            assert pid_about is not None
            about_post = get_post_by_id(pid_about, conn)
            assert about_post["slug"] == "dev-about"

            # 3. Gear language-specific home (/ko)
            pid_gear_ko = resolve_post_id(conn, page_path="/ko", platform="gear")
            assert pid_gear_ko is not None
            gear_post = get_post_by_id(pid_gear_ko, conn)
            assert gear_post["slug"] == "gear-ko-home"

            # 4. Direct article path with query params (dev blog post)
            pid_dev_art = resolve_post_id(
                conn,
                title="Troubleshooting High CPU Kernel Softirq Storm",
                page_path="/posts/2026-11-17-kernel-softirq.html?fbclid=IwAR123",
                platform="dev"
            )
            assert pid_dev_art is not None
            dev_art = get_post_by_id(pid_dev_art, conn)
            assert "kernel-softirq" in dev_art["slug"]

            # 5. Slug match without extension (markets post)
            pid_markets = resolve_post_id(
                conn,
                page_path="/fed-liquidity-dynamics",
                platform="markets"
            )
            assert pid_markets is not None
            markets_post = get_post_by_id(pid_markets, conn)
            assert markets_post["slug"] == "fed-liquidity-dynamics"

            # 6. Tistory numeric path (/57)
            pid_tistory = resolve_post_id(
                conn,
                page_path="/57",
                platform="tistory"
            )
            assert pid_tistory is not None
            tistory_post = get_post_by_id(pid_tistory, conn)
            assert tistory_post["url"] == "https://softwin.tistory.com/57"

            # 7. Fuzzy title match fallback
            pid_fuzzy = resolve_post_id(
                conn,
                title="Spring Boot OOM 장애 원인 분석 및 힙 덤프 트러블슈팅 - Softwin",
                page_path="/unknown/unmapped/path.html",
                platform="tistory"
            )
            assert pid_fuzzy == pid_tistory

    def test_03_ingest_ga4_gsc_snapshots_and_publishing_logs(self, seeded_db: Path):
        """3.3: Ingest daily performance analytics snapshots and verify audit logging & UPSERT."""
        with get_db(str(seeded_db)) as conn:
            dev_post_id = resolve_post_id(
                conn,
                page_path="/posts/2026-11-17-kernel-softirq.html",
                platform="dev"
            )
            assert dev_post_id is not None

            # 1. Ingest GA4 metrics snapshot
            aid_ga4 = record_analytics(
                post_id=dev_post_id,
                record_date="2026-11-17",
                pageviews=3420,
                users=1250,
                sessions=1890,
                avg_duration_sec=142.8,
                bounce_rate=0.34,
                source="GA4",
                conn=conn
            )
            assert aid_ga4 > 0

            # 2. Ingest Search Console metrics snapshot
            aid_gsc = record_analytics(
                post_id=dev_post_id,
                record_date="2026-11-17",
                pageviews=890,  # clicks
                users=850,
                sessions=860,
                source="GSC",
                conn=conn
            )
            assert aid_gsc > 0
            assert aid_gsc != aid_ga4

            # 3. Idempotent UPSERT test: re-recording updated GA4 numbers on same date
            aid_ga4_updated = record_analytics(
                post_id=dev_post_id,
                record_date="2026-11-17",
                pageviews=4100,  # increased
                users=1500,
                sessions=2200,
                avg_duration_sec=155.0,
                bounce_rate=0.31,
                source="GA4",
                conn=conn
            )
            assert aid_ga4_updated > 0

            # Verify the record was updated in place (no duplicate rows)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*), pageviews, users FROM post_analytics WHERE post_id = ? AND record_date = ? AND source = 'GA4'",
                (dev_post_id, "2026-11-17")
            )
            row = cur.fetchone()
            assert row[0] == 1, "UPSERT must not duplicate rows for same (post_id, record_date, source)"
            assert row[1] == 4100
            assert row[2] == 1500

            # 4. Audit logging
            lid = record_log(
                post_id=dev_post_id,
                action="ANALYTICS_INGEST",
                status="SUCCESS",
                message="Successfully ingested 4,100 GA4 pageviews and 890 GSC clicks",
                conn=conn
            )
            assert lid > 0

            # 5. Live synchronization status update
            synced = update_post_live_sync(
                post_id=dev_post_id,
                status="PUBLISHED",
                url="https://dev.ideaspot360.com/posts/2026-11-17-kernel-softirq.html",
                published_at="2026-11-17 10:30:00",
                conn=conn
            )
            assert synced is True

            # Verify audit log entry
            cur.execute("SELECT * FROM publishing_logs WHERE id = ?", (lid,))
            log_row = cur.fetchone()
            assert log_row["action"] == "ANALYTICS_INGEST"
            assert log_row["status"] == "SUCCESS"


# ==============================================================================
# Scenario 4: Full Multi-Domain Content Compliance Audit
# ==============================================================================

class TestScenario4FullMultiDomainContentComplianceAudit:
    """
    Scenario 4: Full Multi-Domain Content Compliance Audit
    Comprehensive enterprise quality audit scanning all 16 real sample markdown
    posts across 6 blog platforms:
    - 6 valid compliant posts: valid_dev, valid_gear, valid_markets, valid_naver, valid_stock, valid_tistory
    - 10 bad defective posts: bad_ai_cliche, bad_finance, bad_forced_drama, bad_ftc,
      bad_health_medical, bad_kogl, bad_math_katex, bad_sec, bad_secret, bad_unclosed_code
    Validates 100% precision and defect code attribution.
    """

    PLATFORM_SAMPLE_MAP = {
        "valid_dev_post.md": "dev",
        "valid_gear_post.md": "gear",
        "valid_markets_post.md": "markets",
        "valid_naver_post.md": "naver",
        "valid_stock_post.md": "stock",
        "valid_tistory_post.md": "tistory",
    }

    EXPECTED_DEFECT_MAP = {
        "bad_ai_cliche_post.md": ("GATE_2", "G2_AI_CLICHE"),
        "bad_finance_post.md": ("GATE_8", "G8_FIN_"),
        "bad_forced_drama_post.md": ("GATE_3", "G3_FORCED_DRAMA"),
        "bad_ftc_post.md": ("GATE_8", "G8_FTC_"),
        "bad_health_medical_post.md": ("GATE_8", "G8_MED_"),
        "bad_kogl_post.md": ("GATE_8", "G8_KOGL_MISSING_ATTRIBUTION"),
        "bad_math_katex_post.md": ("GATE_1", "G1_KATEX_MULTILINE_SYNTAX"),
        "bad_sec_post.md": ("GATE_8", "G8_GLOBAL_"),
        "bad_secret_post.md": ("GATE_7", "G7_"),
        "bad_unclosed_code_post.md": ("GATE_1", "G1_UNCLOSED_CODEBLOCK"),
    }

    def test_01_audit_all_16_real_sample_posts_precision_and_recall(
        self, sample_posts_dir: Path
    ):
        """4.1: Audit all 16 sample posts; verify 100% precision in clean vs defective classification."""
        # Use an isolated registry configured for domain compliance auditing
        domain_registry = RuleRegistry()
        domain_registry.discover()
        # For domain rule auditing, unregister minimum length to evaluate content compliance
        domain_registry.unregister("G1_MIN_LENGTH")
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=domain_registry)

        valid_results: Dict[str, GateReport] = {}
        bad_results: Dict[str, GateReport] = {}

        # 1. Audit the 6 valid posts
        for fname, platform in self.PLATFORM_SAMPLE_MAP.items():
            fpath = sample_posts_dir / fname
            assert fpath.exists(), f"Sample post missing: {fpath}"
            report = gatekeeper.verify(str(fpath), platform_override=platform)
            valid_results[fname] = report

            assert report.is_passed is True, (
                f"Valid post '{fname}' on platform '{platform}' unexpectedly failed: "
                f"{[(v.gate_id, v.rule_id, v.message) for v in report.violations]}"
            )
            assert report.score == 100, f"Score for {fname} was {report.score}, expected 100"
            assert report.reject_count == 0

        # 2. Audit the 10 defective posts
        for fname in self.EXPECTED_DEFECT_MAP:
            fpath = sample_posts_dir / fname
            assert fpath.exists(), f"Sample post missing: {fpath}"
            report = gatekeeper.verify(str(fpath))
            bad_results[fname] = report

            assert report.is_passed is False, f"Defective post '{fname}' unexpectedly passed!"
            assert report.reject_count >= 1
            assert report.score < 100

        # Aggregate Statistics
        total_scanned = len(valid_results) + len(bad_results)
        total_passed = sum(1 for r in valid_results.values() if r.is_passed)
        total_rejected = sum(1 for r in bad_results.values() if not r.is_passed)

        assert total_scanned == 16
        assert total_passed == 6
        assert total_rejected == 10
        # Precision: 100%, False Positives: 0, False Negatives: 0

    def test_02_audit_defect_categorization_and_attribution(
        self, sample_posts_dir: Path
    ):
        """4.2: Verify precise defect attribution and gate mapping across all 10 defective posts."""
        gatekeeper = IroncladGatekeeper(strict_mode=False)

        for fname, (expected_gate, expected_prefix) in self.EXPECTED_DEFECT_MAP.items():
            fpath = sample_posts_dir / fname
            report = gatekeeper.verify(str(fpath))

            # Must contain at least one REJECT violation matching the expected gate and rule prefix
            matched_violations = [
                v for v in report.violations
                if v.gate_id == expected_gate and v.rule_id.startswith(expected_prefix)
            ]
            assert len(matched_violations) >= 1, (
                f"Post '{fname}' failed to trigger expected defect ({expected_gate}, {expected_prefix}). "
                f"Actual violations: {[(v.gate_id, v.rule_id) for v in report.violations]}"
            )

            # Check that violation metadata contains helpful fix advice and snippets
            lead_v = matched_violations[0]
            assert lead_v.severity == Severity.REJECT
            assert len(lead_v.message) > 0
            assert len(lead_v.fix_hint) > 0

    def test_03_min_length_boundary_audit_on_raw_fixtures(
        self, sample_posts_dir: Path
    ):
        """4.3: Verify standard IroncladGatekeeper enforces length boundaries on raw short fixtures."""
        std_gatekeeper = IroncladGatekeeper(strict_mode=False)

        # valid_dev_post (5,346 chars, >700 words), valid_markets_post (4,648 chars), and valid_tistory_post (2,108 chars)
        # fully satisfy the length requirement
        rep_dev = std_gatekeeper.verify(str(sample_posts_dir / "valid_dev_post.md"), platform_override="dev")
        assert rep_dev.is_passed is True

        rep_markets = std_gatekeeper.verify(str(sample_posts_dir / "valid_markets_post.md"), platform_override="markets")
        assert rep_markets.is_passed is True

        rep_tistory = std_gatekeeper.verify(str(sample_posts_dir / "valid_tistory_post.md"), platform_override="tistory")
        assert rep_tistory.is_passed is True

        # Raw short fixtures (< 1200 chars) are flagged specifically for length by standard gatekeeper
        rep_gear = std_gatekeeper.verify(str(sample_posts_dir / "valid_gear_post.md"), platform_override="gear")
        assert not rep_gear.is_passed
        assert any(v.rule_id == "G1_MIN_LENGTH_KO" for v in rep_gear.violations)
        # Verify no OTHER violations exist
        non_length_violations = [v for v in rep_gear.violations if v.rule_id != "G1_MIN_LENGTH_KO"]
        assert len(non_length_violations) == 0, f"Unexpected violation on valid_gear_post: {non_length_violations}"


# ==============================================================================
# Scenario 5: Cross-Platform Regression & Mutation Stress Test
# ==============================================================================

class TestScenario5CrossPlatformRegressionAndMutationStress:
    """
    Scenario 5: Cross-Platform Regression & Mutation Stress Test
    Mutates frontmatter and body across platforms to prove strict multi-tenant
    isolation without false alarms:
    1. Dev post-mortem requirements do NOT trigger on Tistory or Naver.
    2. Naver hashtags & image links do NOT trigger on Dev or Markets.
    3. Markets vs Stock financial disclaimers isolation.
    4. Category taxonomy cross-tenant isolation.
    5. Universal common invariants (code blocks, secrets, AI cliches) universally enforced.
    """

    def test_01_dev_postmortem_requirements_isolated_from_tistory_and_naver(
        self, sample_posts_map: Dict[str, Path]
    ):
        """5.1: Dev 5 artifacts rule (G4_DEV_ENGINEERING_ARTIFACTS) never triggers on Tistory or Naver."""
        domain_registry = RuleRegistry()
        domain_registry.discover()
        domain_registry.unregister("G1_MIN_LENGTH")
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=domain_registry)

        valid_tistory = sample_posts_map["valid_tistory_post"]
        valid_naver = sample_posts_map["valid_naver_post"]

        # Tistory evaluation: passes without requiring dev post-mortem sections
        rep_tistory = gatekeeper.verify(str(valid_tistory), platform_override="tistory")
        assert rep_tistory.is_passed is True
        assert not any("DEV" in v.rule_id for v in rep_tistory.violations)

        # Naver evaluation: passes without requiring dev post-mortem sections
        rep_naver = gatekeeper.verify(str(valid_naver), platform_override="naver")
        assert rep_naver.is_passed is True
        assert not any("DEV" in v.rule_id for v in rep_naver.violations)

        # Conversely, evaluating the same Tistory post under 'dev' platform MUST fail for missing dev artifacts
        rep_tistory_as_dev = gatekeeper.verify(str(valid_tistory), platform_override="dev")
        assert rep_tistory_as_dev.is_passed is False
        dev_artifact_rule_ids = {v.rule_id for v in rep_tistory_as_dev.violations if v.gate_id == "GATE_4"}
        assert len(dev_artifact_rule_ids) >= 1
        assert any(r.startswith("G4_MISSING_") for r in dev_artifact_rule_ids)

    def test_02_naver_hashtags_and_image_links_isolated_from_dev_and_markets(
        self, sample_posts_map: Dict[str, Path], temp_post_factory: Callable[[str, Optional[str]], Path]
    ):
        """5.2: Naver image links & hashtag rules never trigger on Dev or Markets."""
        domain_registry = RuleRegistry()
        domain_registry.discover()
        domain_registry.unregister("G1_MIN_LENGTH")
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=domain_registry)

        valid_dev = sample_posts_map["valid_dev_post"]
        valid_markets = sample_posts_map["valid_markets_post"]

        # Dev post evaluated on dev: passes cleanly
        rep_dev = gatekeeper.verify(str(valid_dev), platform_override="dev")
        assert rep_dev.is_passed is True
        assert not any("NAVER" in v.rule_id for v in rep_dev.violations)

        # Markets post evaluated on markets: passes cleanly
        rep_markets = gatekeeper.verify(str(valid_markets), platform_override="markets")
        assert rep_markets.is_passed is True
        assert not any("NAVER" in v.rule_id for v in rep_markets.violations)

        # Evaluating valid_dev under 'naver' flags Naver hashtag requirement
        rep_dev_as_naver = gatekeeper.verify(str(valid_dev), platform_override="naver")
        assert any(v.rule_id == "G6_NAVER_MISSING_HASHTAGS" for v in rep_dev_as_naver.violations)

        # Test inline image rule isolation: Markdown image tags (![...]) are allowed on Dev,
        # but strictly REJECTED on Naver (G6_NAVER_INLINE_IMAGE_FORBIDDEN)
        post_with_inline_img = temp_post_factory(
            "---\n"
            "title: \"Architecture Diagram Walkthrough\"\n"
            "category: \"Systems & Networking\"\n"
            "tags: \"arch, systems\"\n"
            "---\n\n"
            "# Architecture Walkthrough\n\n"
            f"{_generate_synthetic_clean_body('en', 1200)}\n\n"
            "![System Architecture Diagram](https://example.com/assets/arch.png)\n",
            "img_post.md"
        )
        rep_img_on_dev = gatekeeper.verify(str(post_with_inline_img), platform_override="dev")
        assert not any(v.rule_id == "G6_NAVER_INLINE_IMAGE_FORBIDDEN" for v in rep_img_on_dev.violations)

        rep_img_on_naver = gatekeeper.verify(str(post_with_inline_img), platform_override="naver")
        assert rep_img_on_naver.is_passed is False
        assert any(v.rule_id == "G6_NAVER_INLINE_IMAGE_FORBIDDEN" for v in rep_img_on_naver.violations)

    def test_03_markets_and_stock_financial_disclaimers_cross_isolation(
        self, sample_posts_map: Dict[str, Path]
    ):
        """5.3: Domestic stock disclaimer (Korean) and global markets disclaimer (English) isolation."""
        domain_registry = RuleRegistry()
        domain_registry.discover()
        domain_registry.unregister("G1_MIN_LENGTH")
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=domain_registry)

        valid_stock = sample_posts_map["valid_stock_post"]
        valid_markets = sample_posts_map["valid_markets_post"]

        # Stock post on stock platform passes
        rep_stock = gatekeeper.verify(str(valid_stock), platform_override="stock")
        assert rep_stock.is_passed is True
        assert not any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in rep_stock.violations)

        # Markets post on markets platform passes
        rep_markets = gatekeeper.verify(str(valid_markets), platform_override="markets")
        assert rep_markets.is_passed is True
        assert not any(v.rule_id == "G8_FIN_MISSING_DISCLAIMER" for v in rep_markets.violations)

        # Cross-mutation: evaluating stock post on markets platform MUST fail for missing English SEC disclaimer
        rep_stock_as_markets = gatekeeper.verify(str(valid_stock), platform_override="markets")
        assert rep_stock_as_markets.is_passed is False
        assert any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in rep_stock_as_markets.violations)

        # Cross-mutation: evaluating markets post on stock platform MUST fail for missing Korean disclaimer
        rep_markets_as_stock = gatekeeper.verify(str(valid_markets), platform_override="stock")
        assert rep_markets_as_stock.is_passed is False
        assert any(v.rule_id == "G8_FIN_MISSING_DISCLAIMER" for v in rep_markets_as_stock.violations)

    def test_04_category_taxonomies_cross_tenant_isolation(
        self, sample_posts_map: Dict[str, Path]
    ):
        """5.4: Tistory 11-category rule and Dev 3-category rule do not cross-interfere."""
        domain_registry = RuleRegistry()
        domain_registry.discover()
        domain_registry.unregister("G1_MIN_LENGTH")
        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=domain_registry)

        valid_tistory = sample_posts_map["valid_tistory_post"]
        valid_dev = sample_posts_map["valid_dev_post"]

        # Tistory has category '컴퓨터 과학 핵심 기초' -> valid on tistory
        rep_t = gatekeeper.verify(str(valid_tistory), platform_override="tistory")
        assert rep_t.is_passed is True

        # Dev has category 'Systems & Networking' -> valid on dev
        rep_d = gatekeeper.verify(str(valid_dev), platform_override="dev")
        assert rep_d.is_passed is True

        # If Tistory post is evaluated on dev, dev category rule flags mismatch
        rep_t_on_dev = gatekeeper.verify(str(valid_tistory), platform_override="dev")
        assert any(v.rule_id == "G6_DEV_CATEGORY_MISMATCH" for v in rep_t_on_dev.violations)

        # If Dev post is evaluated on tistory, tistory category rule flags mismatch
        rep_d_on_tistory = gatekeeper.verify(str(valid_dev), platform_override="tistory")
        assert any(v.rule_id == "G6_TISTORY_CATEGORY_MISMATCH" for v in rep_d_on_tistory.violations)

    def test_05_universal_common_invariants_enforced_across_all_platforms(
        self, temp_post_factory: Callable[[str, Optional[str]], Path]
    ):
        """5.5: Universal common invariants (e.g. unclosed code blocks) are enforced on ALL platforms."""
        gatekeeper = IroncladGatekeeper(strict_mode=False)
        platforms = ["dev", "markets", "gear", "stock", "naver", "tistory"]

        for plat in platforms:
            clean_body = _generate_synthetic_clean_body("en" if plat in ("dev", "markets") else "ko", target_chars=1300)
            mutated_content = (
                "---\n"
                "title: \"Universal Code Block Mutation Test\"\n"
                "category: \"Systems & Networking\"\n"
                "tags: \"test\"\n"
                "visibility: \"public\"\n"
                "quantum_backend: \"aer\"\n"
                "---\n\n"
                "# Invariant Test\n\n"
                f"{clean_body}\n\n"
                "```python\n"
                "def trigger_unclosed():\n"
                "    pass\n"
                # Intentionally missing closing backticks!
            )
            p = temp_post_factory(mutated_content, f"unclosed_{plat}.md")
            report = gatekeeper.verify(str(p), platform_override=plat)

            assert report.is_passed is False, f"Platform '{plat}' bypassed unclosed code block invariant!"
            assert any(v.rule_id == "G1_UNCLOSED_CODEBLOCK" for v in report.violations), (
                f"Platform '{plat}' failed to flag G1_UNCLOSED_CODEBLOCK"
            )
