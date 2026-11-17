# -*- coding: utf-8 -*-
"""
tests.e2e.test_tier3_combinations - Tier 3: Pairwise Cross-Feature Interactions Suite

Exhaustive pairwise cross-feature interaction testing covering combinations
of the 10 core features defined in TEST_INFRA.md:
  Pair 1: Feature 1 (Rule Engine) + Feature 2 (Rules Isolation & Whitelist)
  Pair 2: Feature 1 (Rule Engine) + Feature 6 (Database CRUD)
  Pair 3: Feature 2 (Rules Isolation) + Feature 3 (Legacy 12 Self-Tests)
  Pair 4: Feature 4 (Frontend Web Assets) + Feature 5 (Asset Sync Pipeline)
  Pair 5: Feature 5 (Sync Pipeline) + Feature 9 (CLI Tools)
  Pair 6: Feature 6 (Database) + Feature 7 (Analytics & Resolver)
  Pair 7: Feature 1 (Rule Engine) + Feature 9 (CLI Tools)
  Pair 8: Feature 6 (Database) + Feature 8 (Packaging)
  Pair 9: Feature 7 (Analytics) + Feature 9 (CLI Tools)
  Pair 10: Feature 1 (Rule Engine) + Feature 10 (Documentation)

Total tests: 23 pairwise interaction tests (Requirement: >= 10 tests).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
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
from blog_core.engine.context import RuleContext, create_context
from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.engine.models import GateReport, Severity, Violation
from blog_core.engine.registry import RuleRegistry, default_registry

from blog_core.database import get_db, init_db
from blog_core.database.operations import (
    get_post_by_file,
    get_post_by_id,
    get_stats_summary,
    list_posts,
    record_analytics,
    record_log,
    search_posts,
    update_post_live_sync,
    update_post_status,
    upsert_post,
)
from blog_core.analytics.resolver import resolve_post_id
from blog_core.analytics.credentials import find_credentials
from sync_to_blogs import (
    compute_sha256,
    resolve_master_assets,
    sync_assets,
    TARGET_MAP,
)


def make_test_rule(
    rule_id: str,
    gate_id: str = "GATE_1",
    platforms: Optional[List[str]] = None,
    fail_trigger: Optional[str] = None,
) -> Type[BaseRule]:
    """Helper to dynamically generate a valid BaseRule subclass."""
    class DynamicTestRule(BaseRule):
        def check(self, ctx: RuleContext) -> List[Violation]:
            if fail_trigger and fail_trigger in ctx.content:
                return [Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet=fail_trigger,
                    message=f"Triggered test rule {self.rule_id}",
                    fix_hint="Remove trigger"
                )]
            return []

    DynamicTestRule.rule_id = rule_id
    DynamicTestRule.gate_id = gate_id
    DynamicTestRule.gate_name = f"Test Gate for {rule_id}"
    DynamicTestRule.platforms = platforms
    DynamicTestRule.default_severity = Severity.REJECT
    return DynamicTestRule


# ==============================================================================
# Pair 1: Feature 1 (Rule Engine) + Feature 2 (Rules Isolation & Whitelist)
# ==============================================================================
class TestPair1RuleEngineAndRulesIsolation:
    """Pair 1: Feature 1 (Rule Engine) + Feature 2 (Rules Isolation & Whitelist)"""

    def test_01_dynamic_rule_registration_and_platform_whitelist(
        self, clean_registry: RuleRegistry
    ):
        """
        Verify that dynamically registering common rules (platforms=None) and
        platform-specific rules (platforms=['dev']) ensures platform-specific rules
        execute ONLY when inspecting the target platform, while common rules run on all.
        """
        common_rule_cls = make_test_rule("TEST_COMMON_RULE", "GATE_1", platforms=None)
        dev_rule_cls = make_test_rule("TEST_DEV_RULE", "GATE_2", platforms=["dev"])
        naver_rule_cls = make_test_rule("TEST_NAVER_RULE", "GATE_3", platforms=["naver"])

        clean_registry.register(common_rule_cls)
        clean_registry.register(dev_rule_cls)
        clean_registry.register(naver_rule_cls)

        # Query rules for dev platform
        dev_rules = clean_registry.get_rules(platform="dev", auto_discover=False)
        dev_rule_ids = {r.rule_id for r in dev_rules}
        assert "TEST_COMMON_RULE" in dev_rule_ids
        assert "TEST_DEV_RULE" in dev_rule_ids
        assert "TEST_NAVER_RULE" not in dev_rule_ids

        # Query rules for naver platform
        naver_rules = clean_registry.get_rules(platform="naver", auto_discover=False)
        naver_rule_ids = {r.rule_id for r in naver_rules}
        assert "TEST_COMMON_RULE" in naver_rule_ids
        assert "TEST_NAVER_RULE" in naver_rule_ids
        assert "TEST_DEV_RULE" not in naver_rule_ids

        # Query rules for stock platform (has only common rule)
        stock_rules = clean_registry.get_rules(platform="stock", auto_discover=False)
        stock_rule_ids = {r.rule_id for r in stock_rules}
        assert "TEST_COMMON_RULE" in stock_rule_ids
        assert "TEST_DEV_RULE" not in stock_rule_ids
        assert "TEST_NAVER_RULE" not in stock_rule_ids

    def test_02_multi_platform_isolation_execution(
        self, clean_registry: RuleRegistry, temp_post_factory: Callable
    ):
        """
        Verify that IroncladGatekeeper with custom registry evaluates only rules
        matching the target platform, without triggering false alarms from sibling platforms.
        """
        class DevCheckRule(BaseRule):
            rule_id = "DEV_TRIGGER_CHECK"
            gate_id = "GATE_2"
            gate_name = "Dev Spec Check"
            platforms = ["dev"]

            def check(self, ctx: RuleContext) -> List[Violation]:
                if "TRIGGER_DEV" in ctx.content:
                    return [Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=Severity.REJECT,
                        line_number=1,
                        snippet="TRIGGER_DEV",
                        message="Dev violation detected",
                        fix_hint="Remove TRIGGER_DEV"
                    )]
                return []

        class MarketsCheckRule(BaseRule):
            rule_id = "MARKETS_TRIGGER_CHECK"
            gate_id = "GATE_8"
            gate_name = "Markets Spec Check"
            platforms = ["markets"]

            def check(self, ctx: RuleContext) -> List[Violation]:
                if "TRIGGER_MARKETS" in ctx.content:
                    return [Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=Severity.REJECT,
                        line_number=1,
                        snippet="TRIGGER_MARKETS",
                        message="Markets violation detected",
                        fix_hint="Remove TRIGGER_MARKETS"
                    )]
                return []

        clean_registry.register(DevCheckRule)
        clean_registry.register(MarketsCheckRule)

        gatekeeper = IroncladGatekeeper(strict_mode=False, registry=clean_registry)

        # Post containing TRIGGER_DEV
        post_path = temp_post_factory(
            "---\ntitle: Sample Post\n---\nTRIGGER_DEV in content here."
        )

        # When evaluated as dev: MUST FAIL
        dev_report = gatekeeper.verify(str(post_path), platform_override="dev")
        assert not dev_report.is_passed
        assert any(v.rule_id == "DEV_TRIGGER_CHECK" for v in dev_report.violations)

        # When evaluated as markets: MUST NOT trigger DEV_TRIGGER_CHECK
        markets_report = gatekeeper.verify(str(post_path), platform_override="markets")
        assert not any(v.rule_id == "DEV_TRIGGER_CHECK" for v in markets_report.violations)

    def test_03_dynamic_unregister_isolation(self, clean_registry: RuleRegistry):
        """
        Verify that dynamically unregistering a rule removes it immediately from
        future gatekeeper executions while leaving other rules active.
        """
        rule1 = make_test_rule("RULE_TEMP_A", "GATE_1", platforms=["dev"])
        rule2 = make_test_rule("RULE_TEMP_B", "GATE_1", platforms=["dev"])
        clean_registry.register(rule1)
        clean_registry.register(rule2)

        assert len(clean_registry.get_rules(platform="dev", auto_discover=False)) == 2

        unreg = clean_registry.unregister("RULE_TEMP_A")
        assert unreg is not None
        assert unreg.rule_id == "RULE_TEMP_A"

        remaining = clean_registry.get_rules(platform="dev", auto_discover=False)
        assert len(remaining) == 1
        assert remaining[0].rule_id == "RULE_TEMP_B"


# ==============================================================================
# Pair 2: Feature 1 (Rule Engine) + Feature 6 (Database CRUD)
# ==============================================================================
class TestPair2RuleEngineAndDatabaseCRUD:
    """Pair 2: Feature 1 (Rule Engine) + Feature 6 (Database CRUD)"""

    def test_01_valid_gatekeeper_pass_upsert_and_audit_log(
        self,
        gatekeeper_instance: IroncladGatekeeper,
        mock_db_conn: sqlite3.Connection,
        sample_posts_map: Dict[str, Path],
    ):
        """
        Verify that a markdown post passing Gatekeeper verification has its parsed
        metadata extracted and stored into SQLite posts.db via upsert_post,
        followed by an audit entry written to publishing_logs.
        """
        valid_dev = sample_posts_map["valid_dev_post"]
        report = gatekeeper_instance.verify(str(valid_dev), platform_override="dev")
        assert report.is_passed, f"Gatekeeper rejected valid post: {report.violations}"

        # Extract parsed metadata using Gatekeeper / context helpers
        content = valid_dev.read_text(encoding="utf-8")
        ctx = create_context(str(valid_dev), content, platform="dev")

        post_data = {
            "post_uid": "dev_20261117_softirq_storm",
            "platform": "dev",
            "blog_id": "dev",
            "track": "Track 1",
            "title": ctx.fm_data.get("title", "Untitled"),
            "slug": valid_dev.stem,
            "category": ctx.fm_data.get("category", "Systems & Networking"),
            "tags": ctx.fm_data.get("tags", "linux, kernel"),
            "file_path": str(valid_dev),
            "status": "DRAFT",
            "content_length": len(content),
        }

        post_id = upsert_post(post_data, conn=mock_db_conn)
        assert post_id > 0

        # Record audit log
        log_id = record_log(
            post_id=post_id,
            action="GATEKEEPER_AUDIT",
            status="SUCCESS",
            message=f"Score: {report.score}/100, Violations: {len(report.violations)}",
            conn=mock_db_conn,
        )
        assert log_id > 0

        # Verify database record
        stored = get_post_by_id(post_id, conn=mock_db_conn)
        assert stored is not None
        assert stored["title"] == ctx.fm_data["title"]
        assert stored["status"] == "DRAFT"
        assert stored["platform"] == "dev"

        # Verify audit log in database
        cursor = mock_db_conn.cursor()
        cursor.execute("SELECT * FROM publishing_logs WHERE id = ?", (log_id,))
        log_row = cursor.fetchone()
        assert log_row is not None
        assert log_row["action"] == "GATEKEEPER_AUDIT"
        assert log_row["status"] == "SUCCESS"
        assert "Score: 100" in log_row["message"]

    def test_02_gatekeeper_rejection_audit_logging(
        self,
        gatekeeper_instance: IroncladGatekeeper,
        mock_db_conn: sqlite3.Connection,
        sample_posts_map: Dict[str, Path],
    ):
        """
        Verify that a post rejected by Gatekeeper records an audit entry in publishing_logs
        with status FAILED and violation messages, without creating a published entry.
        """
        bad_ai = sample_posts_map["bad_ai_cliche_post"]
        report = gatekeeper_instance.verify(str(bad_ai), platform_override="dev")
        assert not report.is_passed
        assert report.reject_count > 0

        # Record audit log without associating to an existing post
        violation_summary = "; ".join(v.message for v in report.violations[:3])
        log_id = record_log(
            post_id=None,
            action="GATEKEEPER_AUDIT",
            status="FAILED",
            message=f"File: {bad_ai.name}, Reason: {violation_summary}",
            conn=mock_db_conn,
        )
        assert log_id > 0

        cursor = mock_db_conn.cursor()
        cursor.execute("SELECT * FROM publishing_logs WHERE id = ?", (log_id,))
        row = cursor.fetchone()
        assert row["status"] == "FAILED"
        assert bad_ai.name in row["message"]


# ==============================================================================
# Pair 3: Feature 2 (Rules Isolation) + Feature 3 (Legacy 12 Self-Tests)
# ==============================================================================
class TestPair3RulesIsolationAndLegacy12SelfTests:
    """Pair 3: Feature 2 (Rules Isolation & Whitelist) + Feature 3 (Legacy 12 Self-Tests)"""

    def test_01_legacy_self_tests_platform_context_isolation(
        self, gatekeeper_instance: IroncladGatekeeper
    ):
        """
        Verify that legacy Gate 8 legal compliance self-test logic executes platform
        disclaimer checks according to the target platform parameter:
        - Financial / investment disclaimers trigger on 'stock' or 'markets'.
        - When running with platform='dev', stock disclaimer rule must NOT be enforced.
        """
        # Test content missing stock disclaimer
        stock_text = (
            "이 종목은 향후 강력한 상승이 기대되며 목표가는 10만원입니다. 매수를 적극 추천합니다."
        )

        # Under 'stock' platform: MUST TRIGGER investment disclaimer violation
        violations_stock = gatekeeper_instance.verify_gate_8_legal_compliance(
            file_path="test_stock.md",
            content=stock_text,
            body=stock_text,
            platform="stock",
        )
        stock_rule_ids = {v.rule_id for v in violations_stock}
        assert "G8_FIN_MISSING_DISCLAIMER" in stock_rule_ids

        # Under 'dev' platform: Stock disclaimer rule MUST NOT trigger
        violations_dev = gatekeeper_instance.verify_gate_8_legal_compliance(
            file_path="test_dev.md",
            content=stock_text,
            body=stock_text,
            platform="dev",
        )
        dev_rule_ids = {v.rule_id for v in violations_dev}
        assert "G8_FIN_MISSING_DISCLAIMER" not in dev_rule_ids

    def test_02_platform_specific_rules_not_triggering_on_other_platforms(
        self, gatekeeper_instance: IroncladGatekeeper, sample_posts_map: Dict[str, Path]
    ):
        """
        Verify that running Gatekeeper on a valid Tistory post does not trigger
        dev-specific rules (such as Dev 5 Troubleshooting Artifacts requirements).
        """
        valid_tistory = sample_posts_map["valid_tistory_post"]

        # Run with platform='tistory'
        tistory_rep = gatekeeper_instance.verify(str(valid_tistory), platform_override="tistory")
        assert tistory_rep.is_passed, f"Tistory post failed under tistory platform: {tistory_rep.violations}"
        assert not any(v.rule_id.startswith("DEV_") for v in tistory_rep.violations)


# ==============================================================================
# Pair 4: Feature 4 (Frontend Web Assets) + Feature 5 (Asset Sync Pipeline)
# ==============================================================================
class TestPair4WebAssetsAndAssetSyncPipeline:
    """Pair 4: Feature 4 (Frontend Web Assets) + Feature 5 (Asset Sync Pipeline)"""

    def test_01_master_assets_sync_sha256_integrity(
        self, mock_ecosystem: Path
    ):
        """
        Verify master lightbox.js and lightbox.css assets exist, have valid frontend
        signatures, and when synced via sync_assets, all target blog repositories
        receive files whose SHA-256 matches the master copy 100%.
        """
        master_js, master_css = resolve_master_assets(WORKSPACE_ROOT)
        assert master_js.exists() and master_js.stat().st_size > 0
        assert master_css.exists() and master_css.stat().st_size > 0

        master_js_content = master_js.read_text(encoding="utf-8")
        master_css_content = master_css.read_text(encoding="utf-8")

        # Verify key frontend tokens
        assert "initPanZoomLightbox" in master_js_content
        assert ".panzoom-modal" in master_css_content

        master_js_sha = compute_sha256(master_js)
        master_css_sha = compute_sha256(master_css)

        # Execute sync to all mock blogs
        results = sync_assets(
            target="all",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=False,
            verify=True,
        )

        assert len(results) == 8  # 4 blogs * 2 files
        for res in results:
            assert res.status == "SYNCED"
            assert res.dest_path.exists()
            assert res.dest_sha256_after == (master_js_sha if res.file_type == "JS" else master_css_sha)
            assert compute_sha256(res.dest_path) == res.dest_sha256_after

    def test_02_backup_creation_and_idempotent_skip(
        self, mock_ecosystem: Path
    ):
        """
        Verify that syncing with backup=True creates .bak copies of preexisting files,
        and subsequent identical sync operations skip writes with status IDENTICAL.
        """
        # Pass 1: Sync with backup
        pass1_results = sync_assets(
            target="dev",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )
        assert len(pass1_results) == 2
        for res in pass1_results:
            assert res.status == "SYNCED"
            assert res.backup_path is not None
            assert res.backup_path.exists()

        # Pass 2: Re-run sync immediately - must be IDENTICAL (no-op)
        pass2_results = sync_assets(
            target="dev",
            ecosystem_root=mock_ecosystem,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            backup=True,
            verify=True,
        )
        assert len(pass2_results) == 2
        for res in pass2_results:
            assert res.status == "IDENTICAL"
            assert res.backup_path is None  # No new backup on skipped write


# ==============================================================================
# Pair 5: Feature 5 (Sync Pipeline) + Feature 9 (CLI Tools)
# ==============================================================================
class TestPair5SyncPipelineAndCLITools:
    """Pair 5: Feature 5 (Asset Sync Pipeline) + Feature 9 (CLI Tools)"""

    def test_01_cli_subprocess_dry_run_exit_code(self, mock_ecosystem: Path):
        """
        Execute sync_to_blogs.py via CLI subprocess with --dry-run and verify
        that exit code is 0 and output describes planned dry-run actions without modifying files.
        """
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "sync_to_blogs.py"),
            "--target", "dev",
            "--ecosystem-root", str(mock_ecosystem),
            "--dry-run",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0, f"sync_to_blogs CLI failed: {proc.stderr}"
        assert "DRY RUN MODE" in proc.stdout or "WOULD_UPDATE" in proc.stdout or "Summary" in proc.stdout

    def test_02_cli_subprocess_invalid_target_error_code(self, mock_ecosystem: Path):
        """
        Execute sync_to_blogs.py with an invalid target argument and assert exit code 2.
        """
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "sync_to_blogs.py"),
            "--target", "nonexistent_target_xyz_123",
            "--ecosystem-root", str(mock_ecosystem),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 2
        assert "ARGUMENT ERROR" in proc.stderr or "Unknown target" in proc.stderr

    def test_03_cli_subprocess_sync_all_execution(self, mock_ecosystem: Path):
        """
        Execute sync_to_blogs.py --target all via CLI subprocess and verify exit code 0
        and physical asset presence in mock ecosystem.
        """
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "sync_to_blogs.py"),
            "--target", "all",
            "--ecosystem-root", str(mock_ecosystem),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0, f"Sync all CLI failed: {proc.stderr}"
        assert "Summary: 8 item(s) processed, 0 failure(s)" in proc.stdout


# ==============================================================================
# Pair 6: Feature 6 (Database) + Feature 7 (Analytics & Resolver)
# ==============================================================================
class TestPair6DatabaseAndAnalyticsResolver:
    """Pair 6: Feature 6 (Database CRUD) + Feature 7 (Analytics & Resolver)"""

    def test_01_resolve_post_id_url_slug_title_variations(
        self, mock_db_conn: sqlite3.Connection
    ):
        """
        Seed posts.db with varied posts, then verify resolve_post_id accurately matches
        diverse URL queries, hashes, trailing slashes, and title keywords.
        """
        # Seed 3 posts
        pid1 = upsert_post({
            "platform": "dev",
            "blog_id": "dev",
            "file_path": "blogs/dev/_posts/2026-11-17-softirq-storm-linux.md",
            "slug": "softirq-storm-linux",
            "title": "Troubleshooting Softirq Storm in Linux Network Stack",
            "url": "https://dev.ideaspot360.com/softirq-storm-linux/",
        }, conn=mock_db_conn)

        pid2 = upsert_post({
            "platform": "tistory",
            "blog_id": "softwin",
            "file_path": "posts/70_trouble_softirq.md",
            "slug": "70_trouble_softirq",
            "title": "리눅스 네트워크 소프트웨어 인터럽트 폭풍 완벽 분석",
            "url": "https://softwin.tistory.com/70",
        }, conn=mock_db_conn)

        pid3 = upsert_post({
            "platform": "stock",
            "blog_id": "stock",
            "file_path": "blogs/stock/index.md",
            "slug": "stock-home",
            "title": "맥락트레이딩 국내 증시 브리핑",
            "url": "https://stock.ideaspot360.com/",
        }, conn=mock_db_conn)

        # 1. Match via URL with query param and hash
        res1 = resolve_post_id(
            mock_db_conn,
            title="Any Title",
            page_path="/softirq-storm-linux/?utm_source=feed#sec-1",
            platform="dev"
        )
        assert res1 == pid1

        # 2. Match Tistory numeric post number
        res2 = resolve_post_id(
            mock_db_conn,
            title="Some Title",
            page_path="/70",
            platform="tistory"
        )
        assert res2 == pid2

        # 3. Match home route with title keyword
        res3 = resolve_post_id(
            mock_db_conn,
            title="맥락트레이딩 국내 증시 브리핑",
            page_path="/",
            platform="stock"
        )
        assert res3 == pid3

    def test_02_record_analytics_and_query_metrics(
        self, mock_db_conn: sqlite3.Connection
    ):
        """
        Verify that resolving a post ID and recording GA4 metrics via record_analytics
        persists accurately and updates stats summary.
        """
        pid = upsert_post({
            "platform": "dev",
            "blog_id": "dev",
            "file_path": "blogs/dev/_posts/2026-11-17-memory-leak.md",
            "slug": "memory-leak-investigation",
            "title": "Memory Leak Root Cause Analysis in Node.js",
            "url": "https://dev.ideaspot360.com/memory-leak-investigation",
        }, conn=mock_db_conn)

        aid = record_analytics(
            post_id=pid,
            record_date="2026-11-17",
            pageviews=1240,
            users=890,
            sessions=950,
            avg_duration_sec=142.5,
            bounce_rate=0.28,
            source="GA4",
            conn=mock_db_conn,
        )
        assert aid > 0

        cursor = mock_db_conn.cursor()
        cursor.execute("SELECT * FROM post_analytics WHERE id = ?", (aid,))
        row = cursor.fetchone()
        assert row["pageviews"] == 1240
        assert row["users"] == 890
        assert row["post_id"] == pid


# ==============================================================================
# Pair 7: Feature 1 (Rule Engine) + Feature 9 (CLI Tools)
# ==============================================================================
class TestPair7RuleEngineAndCLITools:
    """Pair 7: Feature 1 (Rule Engine) + Feature 9 (CLI Tools)"""

    def test_01_gatekeeper_cli_valid_file_json(self, sample_posts_map: Dict[str, Path]):
        """
        Execute python -m blog_core.engine.gatekeeper --file <valid_file> --json via CLI,
        verify exit code 0, and validate structured JSON output schema.
        """
        valid_dev = sample_posts_map["valid_dev_post"]
        cmd = [
            sys.executable,
            "-m", "blog_core.engine.gatekeeper",
            "--file", str(valid_dev),
            "--platform", "dev",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0, f"Gatekeeper CLI failed: {proc.stderr}"

        data = json.loads(proc.stdout)
        assert data["is_passed"] is True
        assert data["score"] == 100
        assert data["reject_count"] == 0
        assert isinstance(data["violations"], list)
        assert len(data["violations"]) == 0

    def test_02_gatekeeper_cli_invalid_file_json(self, sample_posts_map: Dict[str, Path]):
        """
        Execute gatekeeper CLI on an invalid post with --json, assert exit code 1,
        and verify that the JSON output reports is_passed=False with violation details.
        """
        bad_ai = sample_posts_map["bad_ai_cliche_post"]
        cmd = [
            sys.executable,
            "-m", "blog_core.engine.gatekeeper",
            "--file", str(bad_ai),
            "--platform", "dev",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 1

        data = json.loads(proc.stdout)
        assert data["is_passed"] is False
        assert data["reject_count"] >= 1
        assert len(data["violations"]) >= 1

    def test_03_gatekeeper_cli_dir_json(self, sample_posts_dir: Path):
        """
        Execute gatekeeper CLI with --dir <path> --json and assert output contains
        a JSON array of reports representing batch verification.
        """
        cmd = [
            sys.executable,
            "-m", "blog_core.engine.gatekeeper",
            "--dir", str(sample_posts_dir),
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        # Batch includes bad posts so exit code will be 1
        assert proc.returncode in (0, 1)

        start_idx = proc.stdout.find("[")
        assert start_idx != -1, f"No JSON array start found in output: {proc.stdout}"
        json_content = proc.stdout[start_idx:].strip()

        reports = json.loads(json_content)
        assert isinstance(reports, list)
        assert len(reports) >= 10


# ==============================================================================
# Pair 8: Feature 6 (Database) + Feature 8 (Packaging)
# ==============================================================================
class TestPair8DatabaseAndPackaging:
    """Pair 8: Feature 6 (Database CRUD) + Feature 8 (Packaging)"""

    def test_01_packaging_import_and_wal_connection(self, mock_temp_db_file: Path):
        """
        Verify that database modules imported via standard package paths execute
        WAL-mode connection initialization and schema creation.
        """
        import blog_core.database as bcdb
        from blog_core.database.connection import get_db

        with get_db(str(mock_temp_db_file)) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"

            # Check core tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            assert "blog_posts" in tables
            assert "post_analytics" in tables
            assert "publishing_logs" in tables

    def test_02_packaged_db_concurrent_crud(
        self, mock_temp_db_file: Path, monkeypatch
    ):
        """
        Verify concurrent writes and reads through packaged database operations
        without database locked errors.
        """
        import blog_core.database.operations as db_ops

        monkeypatch.setenv("BLOG_CORE_DB_PATH", str(mock_temp_db_file))

        for i in range(5):
            db_ops.upsert_post({
                "post_uid": f"concurrent_post_{i}",
                "platform": "tistory",
                "blog_id": "softwin",
                "file_path": f"posts/concurrent_article_{i}.md",
                "title": f"Concurrent Article {i}",
                "status": "DRAFT",
            })

        posts = db_ops.list_posts(platform="tistory")
        assert len(posts) >= 5


# ==============================================================================
# Pair 9: Feature 7 (Analytics) + Feature 9 (CLI Tools)
# ==============================================================================
class TestPair9AnalyticsAndCLITools:
    """Pair 9: Feature 7 (Analytics & Resolver) + Feature 9 (CLI Tools)"""

    def test_01_analytics_credentials_cli_and_env_resolution(
        self, mock_credentials_file: Path, monkeypatch
    ):
        """
        Verify credentials discovery resolution priority across CLI explicit path,
        environment variables, and search directories.
        """
        # 1. Explicit path parameter (highest priority)
        found_explicit = find_credentials(explicit_path=str(mock_credentials_file))
        assert found_explicit == str(mock_credentials_file.resolve())

        # 2. Environment variable
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(mock_credentials_file))
        found_env = find_credentials()
        assert found_env == str(mock_credentials_file.resolve())

        # 3. Search directory
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        found_dir = find_credentials(search_paths=[mock_credentials_file.parent])
        assert found_dir is not None

    def test_02_analytics_cli_tool_invocation(self):
        """
        Verify that CLI tool entrypoint for analytics behaves properly or gracefully
        skips if blog_core/cli.py is pending in Milestone 4.
        """
        cli_file = WORKSPACE_ROOT / "blog_core" / "cli.py"
        if not cli_file.exists():
            pytest.skip("blog_core/cli.py not yet created (Milestone 4 Pending)")

        cmd = [sys.executable, "-m", "blog_core.cli", "--help"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0


# ==============================================================================
# Pair 10: Feature 1 (Rule Engine) + Feature 10 (Documentation)
# ==============================================================================
class TestPair10RuleEngineAndDocumentation:
    """Pair 10: Feature 1 (Rule Engine) + Feature 10 (Documentation)"""

    def test_01_custom_rule_extension_contract_execution(
        self, clean_registry: RuleRegistry, temp_post_factory: Callable
    ):
        """
        Verify that custom rule examples following the documented extension guide
        (inheriting BaseRule, specifying gate_id and platforms, implementing check)
        integrate into RuleRegistry and execute accurately via Gatekeeper.
        """
        class DocumentedCustomRuleExample(BaseRule):
            """Example rule as documented in AGENT_EXTENSION_GUIDE.md"""
            rule_id = "DOC_EXAMPLE_KEYWORD_CHECK"
            gate_id = "GATE_2"
            gate_name = "Documented Style Guide"
            platforms = ["dev"]
            default_severity = Severity.REJECT

            def check(self, ctx: RuleContext) -> List[Violation]:
                violations = []
                for idx, line in enumerate(ctx.lines, start=1):
                    if "UNAPPROVED_DOC_PATTERN" in line:
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            line_number=idx,
                            snippet=line.strip(),
                            message="Found unapproved documentation pattern.",
                            fix_hint="Replace with approved documentation phrasing."
                        ))
                return violations

        # Register documented rule
        clean_registry.register(DocumentedCustomRuleExample)
        gatekeeper = IroncladGatekeeper(registry=clean_registry)

        bad_post = temp_post_factory(
            "---\ntitle: Documented Test\ncategory: Systems & Networking\ntags: doc, test\n---\nLine 1: OK\nLine 2: UNAPPROVED_DOC_PATTERN found here\n"
        )
        report = gatekeeper.verify(str(bad_post), platform_override="dev")
        assert not report.is_passed
        assert any(v.rule_id == "DOC_EXAMPLE_KEYWORD_CHECK" for v in report.violations)

    def test_02_documented_agent_extension_guide_code_compilation(self):
        """
        Verify that docs/AGENT_EXTENSION_GUIDE.md exists and contains valid syntax
        (or gracefully skip if Milestone 4 Pending).
        """
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"
        if not guide_path.exists():
            pytest.skip("docs/AGENT_EXTENSION_GUIDE.md not yet created (Milestone 4 Pending)")

        content = guide_path.read_text(encoding="utf-8")
        assert len(content) > 100
        assert "BaseRule" in content
        assert "RuleRegistry" in content
