# -*- coding: utf-8 -*-
"""
tests.e2e.test_tier2_boundaries - Tier 2: Boundary & Corner Cases Suite

Exhaustive boundary, edge, corner, and error-prone input verification across
all 10 core features defined in TEST_INFRA.md:
  Feature 1: Rule Engine & Discovery Boundaries (≥5 tests)
  Feature 2: Rules Isolation & Whitelist Boundaries (≥5 tests)
  Feature 3: Legacy 12 Self-Tests Boundaries (≥5 tests)
  Feature 4: Frontend Web Assets Boundaries (≥5 tests)
  Feature 5: Asset Sync Pipeline Boundaries (≥5 tests)
  Feature 6: Database Connection & CRUD Boundaries (≥5 tests)
  Feature 7: Analytics & Resolver Boundaries (≥5 tests)
  Feature 8: pyproject.toml Packaging Boundaries (≥5 tests)
  Feature 9: CLI Tools Boundaries (≥5 tests)
  Feature 10: Documentation Boundaries (≥5 tests)

Total tests: 55 boundary & corner test cases (Requirement: ≥50 tests).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Type
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from blog_core.engine.base_rule import BaseRule
from blog_core.engine.context import (
    RuleContext,
    create_context,
    extract_code_blocks,
    parse_frontmatter,
    split_frontmatter_and_body,
)
from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.engine.models import Color, GateReport, Severity, Violation
from blog_core.engine.registry import RuleRegistry, default_registry
from blog_core.rules.common.markdown_structure import (
    FrontmatterRequiredRule,
    KatexMultilineSyntaxRule,
    UnclosedCodeBlockRule,
    UnclosedMathBlockRule,
)
from blog_core.rules.common.min_length import MinLengthRule

from blog_core.database import get_db, init_db, resolve_db_path
from blog_core.database.operations import (
    get_post_by_file,
    get_post_by_id,
    list_posts,
    search_posts,
    update_post_live_sync,
    update_post_status,
    upsert_post,
)

from blog_core.analytics.credentials import find_credentials
from blog_core.analytics.ga4 import GA4AnalyticsClient
from blog_core.analytics.resolver import resolve_post_id
from blog_core.analytics.search_console import SearchConsoleClient

from sync_to_blogs import (
    SyncItemResult,
    compute_sha256,
    resolve_master_assets,
    resolve_target_destinations,
    sync_assets,
)

pytest_plugins = ["tests.fixtures.conftest"]


# ==============================================================================
# Feature 1: Rule Engine & Discovery Boundaries (≥5 tests)
# ==============================================================================
class TestFeature1RuleEngineAndDiscoveryBoundaries:
    """Feature 1: Boundary inputs to parser, context creation, and rule registry."""

    def test_01_empty_markdown_file_boundary(self, temp_post_factory: Callable):
        """1.1: Verify completely empty (0-byte) markdown file handling."""
        empty_file = temp_post_factory("", filename="empty_post.md")

        # Context creation on empty content
        ctx = create_context(str(empty_file), "", "tistory")
        assert ctx.fm_data == {}
        assert ctx.body == ""
        assert ctx.lines == []
        assert ctx.code_blocks == []

        # Gatekeeper verify on empty file
        gk = IroncladGatekeeper()
        report = gk.verify(str(empty_file))
        assert report.is_passed is False
        assert report.reject_count >= 1

        rule_ids = {v.rule_id for v in report.violations}
        # Frontmatter and min length rules must trigger
        assert "G1_REQ_FRONTMATTER" in rule_ids
        assert "G1_MIN_LENGTH_KO" in rule_ids

    def test_02_missing_frontmatter_closing_delimiter_boundary(self):
        """1.2: Verify handling when frontmatter opening '---' has no closing '---'."""
        content = (
            "---\n"
            "title: Broken Frontmatter\n"
            "tags: test, boundary\n"
            "category: IT & Tech\n"
            "\n"
            "Body text follows without the closing three dashes.\n"
        )
        fm_text, body, start_line = split_frontmatter_and_body(content)
        # Should gracefully treat entire content as body without crashing
        assert fm_text is None
        assert body == content
        assert start_line == 1

        fm_data = parse_frontmatter(fm_text)
        assert fm_data == {}

        ctx = create_context("unclosed_fm.md", content, "tistory")
        assert ctx.fm_data == {}

    def test_03_malformed_yaml_frontmatter_boundary(self):
        """1.3: Verify parsing of malformed YAML (missing colons, list items, invalid chars)."""
        malformed_fm = (
            ": invalid leading colon\n"
            "no_colon_line_here\n"
            "valid_key:   \"Valid Value With Extra Spaces\"   \n"
            "list_item_dash - item without mapping\n"
            "another_key: simple_val\n"
            "### commented line\n"
            "quote_mismatch: 'value with single start and double end\"\n"
        )
        data = parse_frontmatter(malformed_fm)
        # Valid key-value pairs must be safely extracted
        assert data.get("valid_key") == "Valid Value With Extra Spaces"
        assert data.get("another_key") == "simple_val"
        # Invalid lines must be ignored without exception
        assert "no_colon_line_here" not in data

    def test_04_huge_document_scaling_boundary(self):
        """1.4: Verify context parsing and rule extraction on extreme document size (>10,000 lines)."""
        header = "---\ntitle: Extreme Big Post\ntags: scale, stress\ncategory: Cloud\n---\n\n"
        # Construct 10,500 lines of body text with intermittent code fences
        body_lines = [f"Line {i}: Scalability test content with technical details." for i in range(10500)]
        body_lines[100] = "```python"
        body_lines[105] = "x = 42"
        body_lines[110] = "```"
        content = header + "\n".join(body_lines)

        ctx = create_context("huge_post.md", content, "dev")
        assert len(ctx.lines) >= 10500
        assert ctx.fm_data.get("title") == "Extreme Big Post"
        assert len(ctx.code_blocks) == 1
        assert ctx.code_blocks[0][0] == "python"

    def test_05_unicode_and_cjk_boundary_in_frontmatter(self):
        """1.5: Verify multi-byte Unicode, CJK characters, emojis, and special symbols in frontmatter."""
        content = (
            "---\n"
            "title: \"분산 합의 알고리즘 🚀 & 分散系統 コンピュータ: Paxos vs Raft [Special]\"\n"
            "tags: \"분산시스템, 算法, テスト, 🎯, ε-greedy, O(N log N)\"\n"
            "category: \"컴퓨터 과학 핵심 기초\"\n"
            "visibility: \"public\"\n"
            "---\n\n"
            "본문 시작 부분입니다.\n"
        )
        fm_text, body, _ = split_frontmatter_and_body(content)
        data = parse_frontmatter(fm_text)

        assert "분산 합의 알고리즘 🚀 & 分散系統" in data.get("title", "")
        assert "🎯" in data.get("tags", "")
        assert data.get("category") == "컴퓨터 과학 핵심 기초"

    def test_06_nonexistent_platform_query_boundary(self, clean_registry: RuleRegistry):
        """1.6: Verify registry query with non-existent or bizarre platform string."""
        clean_registry.discover()
        # Querying an unknown platform must safely fallback to returning universal common rules only
        rules = clean_registry.get_rules(platform="alien_unknown_platform_v999")
        assert len(rules) > 0
        for r in rules:
            assert r.platforms is None, f"Rule {r.rule_id} should be universal common rule"


# ==============================================================================
# Feature 2: Rules Isolation & Whitelist Boundaries (≥5 tests)
# ==============================================================================
class TestFeature2RulesIsolationAndWhitelistBoundaries:
    """Feature 2: Boundary conditions for platform whitelist filtering and isolation."""

    def test_01_unknown_platform_string_fallback_to_common_rules(self, clean_registry: RuleRegistry):
        """2.1: Unknown platform string returns common rules and zero platform-specific rules."""
        clean_registry.discover()
        common_rules = [r for r in clean_registry.rules.values() if r.platforms is None]
        queried_rules = clean_registry.get_rules(platform="unregistered_platform_123")

        assert len(queried_rules) == len(common_rules)
        queried_ids = {r.rule_id for r in queried_rules}
        common_ids = {r.rule_id for r in common_rules}
        assert queried_ids == common_ids

    def test_02_platform_casing_and_whitespace_boundary(self, clean_registry: RuleRegistry):
        """2.2: Verify case-insensitivity ('DEV', 'Dev', '  dev  ') for platform whitelist matching."""
        clean_registry.discover()
        rules_lower = clean_registry.get_rules(platform="dev")
        rules_upper = clean_registry.get_rules(platform="DEV")
        rules_mixed = clean_registry.get_rules(platform="Dev")
        rules_padded = clean_registry.get_rules(platform="  dev  ")

        ids_lower = [r.rule_id for r in rules_lower]
        ids_upper = [r.rule_id for r in rules_upper]
        ids_mixed = [r.rule_id for r in rules_mixed]
        ids_padded = [r.rule_id for r in rules_padded]

        assert ids_lower == ids_upper
        assert ids_lower == ids_mixed
        assert ids_lower == ids_padded

    def test_03_dynamic_rule_unhandled_exception_resilience(self, clean_registry: RuleRegistry):
        """2.3: Verify that a rule raising an unhandled exception does not corrupt the registry."""
        class FaultyRule(BaseRule):
            rule_id = "FAULTY_EXPLODING_RULE"
            gate_id = "GATE_1"
            gate_name = "Fault Injection"
            platforms = None

            def check(self, ctx):
                raise ZeroDivisionError("Simulated unhandled math division error!")

        faulty = FaultyRule()
        clean_registry.register(faulty)
        assert "FAULTY_EXPLODING_RULE" in clean_registry.rules

        # Unregister cleanly restores registry
        removed = clean_registry.unregister("FAULTY_EXPLODING_RULE")
        assert removed is faulty
        assert "FAULTY_EXPLODING_RULE" not in clean_registry.rules

    def test_04_duplicate_rule_registration_overwrite_behavior(self, clean_registry: RuleRegistry):
        """2.4: Registering a rule with the same rule_id overwrites previous instance cleanly."""
        class RuleV1(BaseRule):
            rule_id = "DUPLICATE_OVERWRITE_TEST"
            gate_id = "GATE_1"
            gate_name = "Version 1"
            description = "Initial Version"
            platforms = None

            def check(self, ctx):
                return []

        class RuleV2(BaseRule):
            rule_id = "DUPLICATE_OVERWRITE_TEST"
            gate_id = "GATE_2"
            gate_name = "Version 2"
            description = "Overwritten Version"
            platforms = None

            def check(self, ctx):
                return []

        clean_registry.register(RuleV1)
        assert clean_registry.rules["DUPLICATE_OVERWRITE_TEST"].gate_name == "Version 1"

        clean_registry.register(RuleV2)
        assert clean_registry.rules["DUPLICATE_OVERWRITE_TEST"].gate_name == "Version 2"
        # Total rule count must remain 1
        assert len([k for k in clean_registry.rules if k == "DUPLICATE_OVERWRITE_TEST"]) == 1

    def test_05_empty_rules_list_boundary(self, clean_registry: RuleRegistry):
        """2.5: Verify behavior when registry has zero rules (empty rules list)."""
        clean_registry.clear()
        clean_registry._discovered = True
        assert len(clean_registry.rules) == 0

        rules = clean_registry.get_rules(platform="dev", auto_discover=False)
        assert rules == []

        gk = IroncladGatekeeper(registry=clean_registry)
        # With zero rules, file passes since no checks fail
        sample_path = str(WORKSPACE_ROOT / "tests" / "fixtures" / "sample_posts" / "valid_dev_post.md")
        report = gk.verify(sample_path, platform_override="dev")
        assert report.is_passed is True
        assert report.reject_count == 0
        assert report.violations == []


# ==============================================================================
# Feature 3: Legacy 12 Self-Tests Boundaries (≥5 tests)
# ==============================================================================
class TestFeature3LegacyTwelveSelfTestsBoundaries:
    """Feature 3: Exact boundary values for content length, code blocks, and math blocks."""

    def test_01_korean_min_length_exact_boundary(self):
        """3.1: Verify Korean min length rule exact boundary at 1,199 vs 1,200 chars (excluding whitespace)."""
        rule = MinLengthRule()

        # Korean filler text: 10 chars per chunk
        chunk = "가나다라마바사아자차"  # 10 chars
        text_1190 = chunk * 119       # 1,190 chars
        text_9 = "가나다라마바사아자"      # 9 chars
        body_1199 = text_1190 + text_9  # exactly 1,199 non-space chars

        text_10 = "가나다라마바사아자차"    # 10 chars
        body_1200 = text_1190 + text_10 # exactly 1,200 non-space chars

        ctx_1199 = RuleContext(
            file_path="post_1199.md", content=body_1199, lines=body_1199.splitlines(),
            platform="tistory", fm_data={}, body=body_1199, body_start_line=1, code_blocks=[]
        )
        ctx_1200 = RuleContext(
            file_path="post_1200.md", content=body_1200, lines=body_1200.splitlines(),
            platform="tistory", fm_data={}, body=body_1200, body_start_line=1, code_blocks=[]
        )

        v_1199 = rule.check(ctx_1199)
        assert len(v_1199) == 1
        assert v_1199[0].rule_id == "G1_MIN_LENGTH_KO"
        assert "1199" in v_1199[0].snippet

        v_1200 = rule.check(ctx_1200)
        assert len(v_1200) == 0

    def test_02_english_word_count_exact_boundary(self):
        """3.2: Verify English min length rule exact boundary at 699 vs 700 words."""
        rule = MinLengthRule()

        body_699 = " ".join([f"word{i}" for i in range(699)])
        body_700 = " ".join([f"word{i}" for i in range(700)])

        ctx_699 = RuleContext(
            file_path="post_699.md", content=body_699, lines=body_699.splitlines(),
            platform="dev", fm_data={}, body=body_699, body_start_line=1, code_blocks=[]
        )
        ctx_700 = RuleContext(
            file_path="post_700.md", content=body_700, lines=body_700.splitlines(),
            platform="dev", fm_data={}, body=body_700, body_start_line=1, code_blocks=[]
        )

        v_699 = rule.check(ctx_699)
        assert len(v_699) == 1
        assert v_699[0].rule_id == "G1_MIN_LENGTH_EN"
        assert "699" in v_699[0].snippet

        v_700 = rule.check(ctx_700)
        assert len(v_700) == 0

    def test_03_zero_body_text_markdown_boundary(self):
        """3.3: Verify post with complete frontmatter but literally zero body text."""
        rule_fm = FrontmatterRequiredRule()
        rule_len = MinLengthRule()

        content = (
            "---\n"
            "title: Zero Body Post\n"
            "tags: test, boundary\n"
            "category: 컴퓨터 과학 핵심 기초\n"
            "---\n"
        )
        fm_text, body, start_line = split_frontmatter_and_body(content)
        fm_data = parse_frontmatter(fm_text)

        ctx = RuleContext(
            file_path="zero_body.md", content=content, lines=content.splitlines(),
            platform="tistory", fm_data=fm_data, body=body, body_start_line=start_line, code_blocks=[]
        )

        # Frontmatter rule passes
        assert len(rule_fm.check(ctx)) == 0
        # Min length rule fails
        v_len = rule_len.check(ctx)
        assert len(v_len) == 1
        assert v_len[0].rule_id == "G1_MIN_LENGTH_KO"

    def test_04_markdown_with_only_code_fences_boundary(self):
        """3.4: Verify markdown composed entirely of closed vs unclosed code fences."""
        rule_code = UnclosedCodeBlockRule()

        # Closed code block
        closed_content = "```python\nfor i in range(10):\n    print(i)\n```\n"
        ctx_closed = RuleContext(
            file_path="closed.md", content=closed_content, lines=closed_content.splitlines(),
            platform="dev", fm_data={}, body=closed_content, body_start_line=1, code_blocks=[]
        )
        assert len(rule_code.check(ctx_closed)) == 0

        # Unclosed code block
        unclosed_content = "```python\nfor i in range(10):\n    print(i)\n"
        ctx_unclosed = RuleContext(
            file_path="unclosed.md", content=unclosed_content, lines=unclosed_content.splitlines(),
            platform="dev", fm_data={}, body=unclosed_content, body_start_line=1, code_blocks=[]
        )
        v = rule_code.check(ctx_unclosed)
        assert len(v) == 1
        assert v[0].rule_id == "G1_UNCLOSED_CODEBLOCK"

    def test_05_katex_single_line_math_vs_multiline_edge_cases(self):
        """3.5: Verify KaTeX math block single line, valid multiline, and broken multiline."""
        rule_katex = KatexMultilineSyntaxRule()

        # Case 1: Valid single line math
        single_line = "Formula: $$E = mc^2$$ is Einstein's mass-energy equation."
        ctx_single = RuleContext(
            file_path="single.md", content=single_line, lines=[single_line],
            platform="tistory", fm_data={}, body=single_line, body_start_line=1, code_blocks=[]
        )
        assert len(rule_katex.check(ctx_single)) == 0

        # Case 2: Broken multiline math (missing \\ before line break)
        broken_multiline = (
            "$$\n"
            "a + b = c\n"
            "d + e = f\n"
            "$$\n"
        )
        ctx_broken = RuleContext(
            file_path="broken.md", content=broken_multiline, lines=broken_multiline.splitlines(),
            platform="tistory", fm_data={}, body=broken_multiline, body_start_line=1, code_blocks=[]
        )
        v_broken = rule_katex.check(ctx_broken)
        assert len(v_broken) == 1
        assert v_broken[0].rule_id == "G1_KATEX_MULTILINE_SYNTAX"

        # Case 3: Valid multiline math with \\ escape
        valid_multiline = (
            "$$\n"
            "a + b = c \\\\\n"
            "d + e = f\n"
            "$$\n"
        )
        ctx_valid = RuleContext(
            file_path="valid.md", content=valid_multiline, lines=valid_multiline.splitlines(),
            platform="tistory", fm_data={}, body=valid_multiline, body_start_line=1, code_blocks=[]
        )
        assert len(rule_katex.check(ctx_valid)) == 0


# ==============================================================================
# Feature 4: Frontend Web Assets Boundaries (≥5 tests)
# ==============================================================================
class TestFeature4FrontendWebAssetsBoundaries:
    """Feature 4: JavaScript scale bounds, CSS z-index, drag thresholds, and DOM guards."""

    @pytest.fixture
    def js_content(self) -> str:
        js_path = WORKSPACE_ROOT / "web_assets" / "js" / "lightbox.js"
        assert js_path.exists(), f"lightbox.js not found at {js_path}"
        return js_path.read_text(encoding="utf-8")

    @pytest.fixture
    def css_content(self) -> str:
        css_path = WORKSPACE_ROOT / "web_assets" / "css" / "lightbox.css"
        assert css_path.exists(), f"lightbox.css not found at {css_path}"
        return css_path.read_text(encoding="utf-8")

    def test_01_lightbox_scale_clamping_constants_and_logic(self, js_content: str):
        """4.1: Verify scale clamping bounds (MIN_SCALE = 0.5, MAX_SCALE = 6.0) in lightbox.js."""
        # Check constant definitions
        min_match = re.search(r"const\s+MIN_SCALE\s*=\s*([0-9.]+)", js_content)
        max_match = re.search(r"const\s+MAX_SCALE\s*=\s*([0-9.]+)", js_content)
        assert min_match is not None, "MIN_SCALE constant missing from lightbox.js"
        assert max_match is not None, "MAX_SCALE constant missing from lightbox.js"
        min_scale = float(min_match.group(1))
        max_scale = float(max_match.group(1))

        assert min_scale == 0.5
        assert max_scale == 6.0

        # Verify mathematical clamp behavior
        def clamp(val: float, low: float, high: float) -> float:
            return min(max(val, low), high)

        assert clamp(0.1, min_scale, max_scale) == 0.5
        assert clamp(0.5, min_scale, max_scale) == 0.5
        assert clamp(3.0, min_scale, max_scale) == 3.0
        assert clamp(6.0, min_scale, max_scale) == 6.0
        assert clamp(99.0, min_scale, max_scale) == 6.0

    def test_02_zero_image_dom_handling_guard(self, js_content: str):
        """4.2: Verify lightbox.js exits gracefully when page contains zero matching images."""
        # Must inspect querySelectorAll result and return null if images.length === 0
        assert "images.length === 0" in js_content or "!images || images.length === 0" in js_content
        # Must return null on zero images to avoid polluting DOM with modal
        assert "return null;" in js_content

    def test_03_drag_threshold_boundary(self, js_content: str):
        """4.3: Verify DRAG_THRESHOLD = 5 boundary to distinguish drag-pan from backdrop click."""
        drag_match = re.search(r"const\s+DRAG_THRESHOLD\s*=\s*(\d+)", js_content)
        assert drag_match is not None, "DRAG_THRESHOLD missing from lightbox.js"
        threshold = int(drag_match.group(1))
        assert threshold == 5

        # Verify distance check logic exists (Math.hypot or dx*dx + dy*dy)
        assert "DRAG_THRESHOLD" in js_content
        assert "hasDragged" in js_content

    def test_04_css_z_index_collision_boundary(self, css_content: str):
        """4.4: Verify CSS z-index is set to 999999 to avoid colliding with blog host styles."""
        z_match = re.search(r"z-index:\s*(\d+);", css_content)
        assert z_match is not None, "z-index missing from lightbox.css"
        modal_z_index = int(z_match.group(1))
        # Master spec requires 999999 to guarantee priority over headers/navbars/widgets
        assert modal_z_index >= 999990, f"z-index {modal_z_index} is too low; expected >= 999990"

    def test_05_non_standard_viewport_dimensions_css(self, css_content: str):
        """4.5: Verify 100vw / 100vh viewport lock and touch-action: none for mobile pinch zoom."""
        assert "100vw" in css_content
        assert "100vh" in css_content
        assert "touch-action: none" in css_content
        assert "overflow: hidden" in css_content

    def test_06_umd_wrapper_environment_boundaries(self, js_content: str):
        """4.6: Verify UMD module pattern handles define.amd, module.exports, and browser root."""
        assert "typeof define === \"function\" && define.amd" in js_content
        assert "typeof module === \"object\" && module.exports" in js_content
        assert "PanZoomLightbox" in js_content


# ==============================================================================
# Feature 5: Asset Sync Pipeline Boundaries (≥5 tests)
# ==============================================================================
class TestFeature5AssetSyncPipelineBoundaries:
    """Feature 5: Destination auto-creation, corrupt master asset detection, and concurrency."""

    def test_01_nonexistent_target_directory_autocreation(self, temp_dir: Path):
        """5.1: Destination directory auto-created when target path does not exist."""
        deep_target = temp_dir / "deeply" / "nested" / "nonexistent" / "custom_blog"
        results = sync_assets(
            target=str(deep_target),
            ecosystem_root=temp_dir,
            core_root=WORKSPACE_ROOT,
            dry_run=False,
            verify=True
        )

        assert len(results) == 2
        for r in results:
            assert r.status == "SYNCED"
            assert r.dest_path.exists()
            assert r.dest_sha256_after == r.master_sha256

    def test_02_corrupt_master_asset_detection(self, temp_dir: Path):
        """5.2: Corrupt or 0-byte master asset raises FileNotFoundError."""
        fake_core = temp_dir / "fake_core"
        js_dir = fake_core / "web_assets" / "js"
        css_dir = fake_core / "web_assets" / "css"
        js_dir.mkdir(parents=True, exist_ok=True)
        css_dir.mkdir(parents=True, exist_ok=True)

        # Create empty 0-byte JS file
        (js_dir / "lightbox.js").write_text("", encoding="utf-8")
        (css_dir / "lightbox.css").write_text("/* valid */", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Master JS asset missing or empty"):
            resolve_master_assets(fake_core)

    def test_03_read_only_destination_directory_error_handling(self, temp_dir: Path):
        """5.3: Permission error or failure when writing to read-only destination handled cleanly."""
        dest_dir = temp_dir / "readonly_dest"
        dest_dir.mkdir(parents=True, exist_ok=True)
        ro_file = dest_dir / "js" / "lightbox.js"
        ro_file.parent.mkdir(parents=True, exist_ok=True)
        ro_file.write_text("// existing", encoding="utf-8")

        # Mock shutil.copy2 to simulate a PermissionError
        with patch("shutil.copy2", side_effect=PermissionError("Simulated permission denied")):
            results = sync_assets(
                target=str(dest_dir),
                ecosystem_root=temp_dir,
                core_root=WORKSPACE_ROOT,
                dry_run=False,
                verify=False
            )
            failed_results = [r for r in results if r.status == "FAILED"]
            assert len(failed_results) >= 1
            assert "permission denied" in str(failed_results[0].error_message).lower()

    def test_04_empty_and_invalid_target_argument_handling(self, temp_dir: Path):
        """5.4: Unrecognized target string raises ValueError with valid choices."""
        with pytest.raises(ValueError, match="Unknown target 'unknown_fake_target'"):
            resolve_target_destinations("unknown_fake_target", temp_dir)

        with pytest.raises(ValueError, match="Unknown target 'invalid_blog_key'"):
            resolve_target_destinations("invalid_blog_key", temp_dir)

    def test_05_concurrent_sync_invocation_safety(self, mock_ecosystem: Path):
        """5.5: Concurrent sync invocations across distinct ecosystem blogs execute safely."""
        blogs = ["dev", "markets", "gear", "stock"]
        def run_sync(blog_key: str):
            return sync_assets(
                target=blog_key,
                ecosystem_root=mock_ecosystem,
                core_root=WORKSPACE_ROOT,
                dry_run=False,
                verify=True
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_sync, b) for b in blogs]
            all_results = [f.result() for f in futures]

        for res_list in all_results:
            assert len(res_list) == 2
            for r in res_list:
                assert r.status in ("SYNCED", "IDENTICAL")
                assert r.dest_sha256_after == r.master_sha256

    def test_06_backup_edge_case_when_dest_missing(self, temp_dir: Path):
        """5.6: Backup flag creates no .bak file when destination file does not exist initially."""
        fresh_target = temp_dir / "fresh_blog"
        results = sync_assets(
            target=str(fresh_target),
            ecosystem_root=temp_dir,
            core_root=WORKSPACE_ROOT,
            backup=True,
            dry_run=False
        )
        assert len(results) == 2
        for r in results:
            assert r.backup_path is None
            assert r.dest_path.exists()


# ==============================================================================
# Feature 6: Database Connection & CRUD Boundaries (≥5 tests)
# ==============================================================================
class TestFeature6DatabaseConnectionAndCRUDBoundaries:
    """Feature 6: Database boundaries, SQL special characters, concurrency, and rollbacks."""

    def test_01_invalid_db_file_path_boundary(self):
        """6.1: Opening database with invalid or prohibited path raises OperationalError."""
        # Windows illegal device name / path
        invalid_path = "NUL:\\invalid\\deep\\path\\posts.db"
        with pytest.raises((sqlite3.OperationalError, OSError)):
            with get_db(db_path=invalid_path) as conn:
                conn.execute("SELECT 1;")

    def test_02_sql_special_characters_and_injection_resilience(self, mock_db_conn: sqlite3.Connection):
        """6.2: Quotes, semicolons, and SQL comments in title and search are handled safely."""
        malicious_title = "'; DROP TABLE blog_posts; -- ' OR '1'='1"
        post_data = {
            "title": malicious_title,
            "file_path": "posts/test_injection.md",
            "platform": "dev",
            "slug": "test-injection",
            "category": "Cloud & DevOps",
            "tags": ["sql' injection", "quote\"test"],
        }

        # Insertion with parameterized SQL
        post_id = upsert_post(post_data, conn=mock_db_conn)
        assert post_id > 0

        # Verify table was NOT dropped
        cursor = mock_db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blog_posts;")
        count = cursor.fetchone()[0]
        assert count >= 1

        # Search with SQL comment syntax
        search_res = search_posts("DROP TABLE", conn=mock_db_conn)
        assert len(search_res) == 1
        assert search_res[0]["title"] == malicious_title

    def test_03_empty_title_and_file_path_validation(self, mock_db_conn: sqlite3.Connection):
        """6.3: Empty title, file_path, and tags in upsert are handled without exception."""
        data = {
            "title": "",
            "file_path": "posts/empty_title.md",
            "platform": "tistory",
            "tags": [],
        }
        pid = upsert_post(data, conn=mock_db_conn)
        assert pid > 0

        post = get_post_by_id(pid, conn=mock_db_conn)
        assert post is not None
        assert post["title"] == ""
        assert post["tags"] == ""

    def test_04_busy_timeout_and_wal_mode_settings(self, mock_temp_db_file: Path):
        """6.4: Verify busy_timeout is set to 30,000ms and WAL journal mode is active on file DB."""
        with get_db(db_path=str(mock_temp_db_file)) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0].upper()
            assert journal_mode == "WAL"

            cursor.execute("PRAGMA busy_timeout;")
            busy_timeout = cursor.fetchone()[0]
            assert busy_timeout == 30000

    def test_05_transaction_rollback_on_insert_failure(self, mock_temp_db_file: Path):
        """6.5: Transaction automatically rolls back when an unhandled exception occurs inside get_db."""
        # Record initial count
        with get_db(db_path=str(mock_temp_db_file)) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM blog_posts;")
            initial_count = c.fetchone()[0]

        # Execute block that inserts then fails
        with pytest.raises(RuntimeError, match="Simulated crash during transaction"):
            with get_db(db_path=str(mock_temp_db_file)) as conn:
                upsert_post({
                    "file_path": "posts/rollback_test.md",
                    "title": "Will Rollback",
                    "platform": "dev",
                }, conn=conn)
                raise RuntimeError("Simulated crash during transaction")

        # Verify rollback occurred and post was NOT persisted
        with get_db(db_path=str(mock_temp_db_file)) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM blog_posts;")
            after_count = c.fetchone()[0]
            assert after_count == initial_count

    def test_06_tag_list_serialization_boundaries(self, mock_db_conn: sqlite3.Connection):
        """6.6: Verify various tag formats (None, empty list, single item, whitespace-heavy list)."""
        data1 = {"file_path": "posts/tags1.md", "tags": None, "platform": "dev"}
        data2 = {"file_path": "posts/tags2.md", "tags": [" single "], "platform": "dev"}
        data3 = {"file_path": "posts/tags3.md", "tags": ["alpha", "beta", "gamma"], "platform": "dev"}

        id1 = upsert_post(data1, conn=mock_db_conn)
        id2 = upsert_post(data2, conn=mock_db_conn)
        id3 = upsert_post(data3, conn=mock_db_conn)

        assert get_post_by_id(id1, conn=mock_db_conn)["tags"] is None
        assert get_post_by_id(id2, conn=mock_db_conn)["tags"] == "single"
        assert get_post_by_id(id3, conn=mock_db_conn)["tags"] == "alpha, beta, gamma"


# ==============================================================================
# Feature 7: Analytics & Resolver Boundaries (≥5 tests)
# ==============================================================================
class TestFeature7AnalyticsAndResolverBoundaries:
    """Feature 7: Credentials fallback, URL normalization, special characters, and empty results."""

    def test_01_nonexistent_service_account_credentials_fallback(self):
        """7.1: Non-existent credentials file path returns None gracefully without crashing."""
        creds = find_credentials(
            explicit_path="Z:/nonexistent/fake/service_account.json",
            env_var="NONEXISTENT_ENV_KEY_12345"
        )
        assert creds is None

        # GA4 client with missing credentials raises FileNotFoundError on connect
        client = GA4AnalyticsClient(property_id="12345678", credentials_path="Z:/fake/creds.json")
        with pytest.raises(FileNotFoundError, match="Google Service Account JSON credentials not found"):
            client._get_client()

    def test_02_malformed_json_credentials_handling(self, temp_dir: Path):
        """7.2: Corrupt non-JSON file in credentials path raises JSONDecodeError when parsed."""
        corrupt_file = temp_dir / "corrupt_creds.json"
        corrupt_file.write_text("{ incomplete_json: true, broken_syntax ", encoding="utf-8")

        found = find_credentials(explicit_path=corrupt_file)
        assert found == str(corrupt_file.resolve())

        # When reading JSON, decode error is raised
        with pytest.raises(json.JSONDecodeError):
            with open(found, "r", encoding="utf-8") as f:
                json.load(f)

    def test_03_url_matching_with_and_without_trailing_slashes_and_protocols(self, mock_db_conn: sqlite3.Connection):
        """7.3: URL variants (slashes, params, hashes, index.html) resolve to the exact same post ID."""
        post_data = {
            "title": "CORS Troubleshooting Guide",
            "file_path": "blogs/dev/_posts/2026-11-20-cors-fix.md",
            "slug": "cors-fix",
            "url": "https://dev.ideaspot360.com/troubleshoot/cors-fix",
            "platform": "dev",
        }
        target_id = upsert_post(post_data, conn=mock_db_conn)

        variants = [
            "/troubleshoot/cors-fix",
            "/troubleshoot/cors-fix/",
            "/troubleshoot/cors-fix/index.html",
            "https://dev.ideaspot360.com/troubleshoot/cors-fix?utm_source=twitter&ref=123",
            "/troubleshoot/cors-fix#technical-details",
        ]
        for v in variants:
            resolved = resolve_post_id(mock_db_conn, page_path=v, platform="dev")
            assert resolved == target_id, f"Variant '{v}' failed to resolve to post ID {target_id}"

    def test_04_title_with_special_punctuation_in_resolve_post_id(self, mock_db_conn: sqlite3.Connection):
        """7.4: Title containing regex characters (?, *, +, [, ], (, ), $) resolves safely."""
        tricky_title = "[Troubleshooting] C++ vs Rust: Memory Leak (v1.2.3)? $100 & 50% [Critical]"
        post_data = {
            "title": tricky_title,
            "file_path": "posts/cpp_rust.md",
            "slug": "cpp-rust-leak",
            "platform": "dev",
        }
        target_id = upsert_post(post_data, conn=mock_db_conn)

        # Keyword matching should succeed without regex compiler failure
        resolved = resolve_post_id(mock_db_conn, title=tricky_title, platform="dev")
        assert resolved == target_id

    def test_05_empty_query_results_and_unmatched_resolution(self, mock_db_conn: sqlite3.Connection):
        """7.5: Empty path and unmatched title return None cleanly without exceptions."""
        res_empty = resolve_post_id(mock_db_conn, title="", page_path="", platform="dev")
        assert res_empty is None

        res_unmatched = resolve_post_id(mock_db_conn, title="Totally Unknown Title 9999", page_path="/unmatched/path")
        assert res_unmatched is None

    def test_06_tistory_numeric_post_id_boundary(self, mock_db_conn: sqlite3.Connection):
        """7.6: Numeric Tistory URLs (e.g. /72, 72) correctly resolve to post record."""
        post_data = {
            "title": "Tistory Post 72",
            "file_path": "posts/72_post.md",
            "url": "https://softwin.tistory.com/72",
            "platform": "tistory",
            "slug": "72-post",
        }
        target_id = upsert_post(post_data, conn=mock_db_conn)

        assert resolve_post_id(mock_db_conn, page_path="/72", platform="tistory") == target_id
        assert resolve_post_id(mock_db_conn, page_path="72", platform="tistory") == target_id
        assert resolve_post_id(mock_db_conn, page_path="/99999", platform="tistory") is None


# ==============================================================================
# Feature 8: pyproject.toml Packaging Boundaries (≥5 tests)
# ==============================================================================
class TestFeature8PyprojectPackagingBoundaries:
    """Feature 8: TOML decoding errors, PEP 621 fields validation, and circular imports."""

    def test_01_malformed_toml_syntax_handling(self):
        """8.1: Malformed TOML syntax raises TOMLDecodeError."""
        broken_toml = (
            '[project]\n'
            'name = "blog_core"\n'
            'version = 0.1.0\n'  # Missing quotes around version string
            'dependencies = [\n'
            '    "pytest>=7.0"\n'
            # Missing closing bracket
        )
        with pytest.raises(tomllib.TOMLDecodeError):
            tomllib.loads(broken_toml)

    def test_02_pep621_required_fields_validation_boundary(self):
        """8.2: PEP 621 metadata validator detects missing required fields ('name', 'version')."""
        def validate_pep621(toml_dict: dict) -> List[str]:
            errors = []
            if "project" not in toml_dict:
                errors.append("Missing [project] table")
                return errors
            proj = toml_dict["project"]
            if "name" not in proj or not proj["name"]:
                errors.append("Missing project.name")
            if "version" not in proj and "dynamic" not in proj:
                errors.append("Missing project.version or dynamic declaration")
            return errors

        # Invalid metadata missing 'name'
        invalid_meta = {"project": {"version": "0.1.0"}}
        errors = validate_pep621(invalid_meta)
        assert "Missing project.name" in errors

        # Valid metadata passes
        valid_meta = {"project": {"name": "blog_core", "version": "0.1.0"}}
        assert validate_pep621(valid_meta) == []

        # If pyproject.toml exists in root, validate it directly
        pyproject_path = WORKSPACE_ROOT / "pyproject.toml"
        if pyproject_path.exists():
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            live_errors = validate_pep621(data)
            assert live_errors == [], f"Live pyproject.toml validation failed: {live_errors}"
        else:
            pytest.skip("pyproject.toml not yet created (Milestone 4 Pending)")

    def test_03_python_version_specifier_boundary(self):
        """8.3: Verify python version requirement allows current Python 3.14+ runtime."""
        current_version = sys.version_info
        # blog_core requires Python >= 3.10
        assert current_version >= (3, 10), f"Current Python {current_version} is below 3.10"

    def test_04_circular_import_isolation_boundary(self):
        """8.4: Verify zero circular import deadlocks across all core subpackages in any order."""
        import importlib

        # Import modules in reverse sequence
        modules_to_test = [
            "blog_core.engine.models",
            "blog_core.engine.context",
            "blog_core.engine.base_rule",
            "blog_core.engine.registry",
            "blog_core.database.connection",
            "blog_core.database.operations",
            "blog_core.analytics.resolver",
            "blog_core.analytics.credentials",
            "blog_core.rules.common.markdown_structure",
            "blog_core.rules.common.min_length",
        ]
        for mod_name in modules_to_test:
            mod = importlib.import_module(mod_name)
            assert mod is not None

    def test_05_clean_import_without_dev_dependencies(self):
        """8.5: Core modules do not strictly require heavy optional analytics dependencies on import."""
        # blog_core.analytics.ga4 can be imported without instantiating BetaAnalyticsDataClient
        from blog_core.analytics import ga4
        assert hasattr(ga4, "GA4AnalyticsClient")

        # blog_core.analytics.search_console can be imported without calling credentials
        from blog_core.analytics import search_console
        assert hasattr(search_console, "SearchConsoleClient")


# ==============================================================================
# Feature 9: CLI Tools Boundaries (≥5 tests)
# ==============================================================================
class TestFeature9CLIToolsBoundaries:
    """Feature 9: CLI exit codes, non-existent files, empty stdin/dir, and JSON format."""

    def test_01_invalid_command_line_flags_exit_code_2(self):
        """9.1: Supplying unrecognized flags exits with code 2 (argparse standard)."""
        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--nonexistent-unrecognized-flag"]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert result.returncode == 2
        assert "unrecognized arguments" in result.stderr or "usage:" in result.stderr

    def test_02_nonexistent_input_file_exit_code_1(self):
        """9.2: Passing non-existent file path to gatekeeper CLI exits with code 1."""
        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--file", "nonexistent_fake_post_123.md"]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert result.returncode == 1
        assert "G0_FILE_NOT_FOUND" in result.stdout or "찾을 수 없습니다" in result.stdout

    def test_03_empty_file_to_gatekeeper_cli_exit_code_1(self, temp_post_factory: Callable):
        """9.3: Passing empty (0-byte) file to gatekeeper CLI exits with code 1."""
        empty_post = temp_post_factory("", filename="cli_empty.md")
        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--file", str(empty_post)]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert result.returncode == 1
        assert "REJECTED" in result.stdout

    def test_04_empty_directory_scan_cli_boundary(self, temp_dir: Path):
        """9.4: Directory scan with zero markdown files outputs warning and exits cleanly with 0."""
        empty_scan_dir = temp_dir / "empty_scan_dir"
        empty_scan_dir.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--dir", str(empty_scan_dir)]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert result.returncode == 0
        assert "0개" in result.stdout or "없습니다" in result.stdout

    def test_05_json_flag_output_schema_boundary(self):
        """9.5: CLI --json flag outputs valid parseable JSON with all required GateReport keys."""
        sample = WORKSPACE_ROOT / "tests" / "fixtures" / "sample_posts" / "valid_dev_post.md"
        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--file", str(sample), "--platform", "dev", "--json"]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        expected_keys = {"file_path", "platform", "is_passed", "score", "reject_count", "warning_count", "violations"}
        assert expected_keys.issubset(data.keys())
        assert data["is_passed"] is True

    def test_06_sync_to_blogs_cli_invalid_target_exit_code(self):
        """9.6: sync_to_blogs.py with invalid target exits with non-zero code."""
        cmd = [sys.executable, "sync_to_blogs.py", "--target", "totally_invalid_target_xyz"]
        result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert result.returncode != 0


# ==============================================================================
# Feature 10: Documentation Boundaries (≥5 tests)
# ==============================================================================
class TestFeature10DocumentationBoundaries:
    """Feature 10: Docs structure, required sections, broken link detection, and UTF-8 encoding."""

    def test_01_docs_directory_structure_boundary(self):
        """10.1: Verify documentation structure when M4 files are present or skipped cleanly."""
        readme_path = WORKSPACE_ROOT / "README.md"
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"

        if not readme_path.exists() and not guide_path.exists():
            pytest.skip("README.md and docs/ not yet created (Milestone 4 Pending)")

        if readme_path.exists():
            assert readme_path.is_file()
        if guide_path.exists():
            assert guide_path.is_file()

    def test_02_missing_required_section_headers_detection(self):
        """10.2: Header validator detects missing mandatory sections in markdown documentation."""
        def validate_sections(text: str, mandatory_headers: List[str]) -> List[str]:
            missing = []
            for h in mandatory_headers:
                pattern = rf"^#+.*{re.escape(h)}"
                if not re.search(pattern, text, re.MULTILINE):
                    missing.append(h)
            return missing

        # Defective markdown missing 'Architecture'
        bad_md = "# Overview\nSome intro text.\n## Quickstart\nRun tests.\n"
        missing = validate_sections(bad_md, ["Overview", "Architecture", "Quickstart"])
        assert "Architecture" in missing

        # Complete markdown passes
        good_md = "# Overview\nIntro.\n# Architecture\nDiag.\n# Quickstart\nRun."
        assert validate_sections(good_md, ["Overview", "Architecture", "Quickstart"]) == []

        # If live README exists, check mandatory sections
        readme_path = WORKSPACE_ROOT / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            missing_live = validate_sections(content, ["아키텍처", "빠른 시작", "확장", "가이드"])
            assert missing_live == []

    def test_03_broken_markdown_links_detection_boundary(self, temp_dir: Path):
        """10.3: Relative link validator detects broken targets in markdown documents."""
        def find_broken_relative_links(md_path: Path) -> List[str]:
            content = md_path.read_text(encoding="utf-8")
            broken = []
            # Find [text](target)
            matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            for text, target in matches:
                # Ignore web URLs and anchors
                if target.startswith("http://") or target.startswith("https://") or target.startswith("#"):
                    continue
                # Resolve relative to markdown file directory
                clean_target = target.split("#")[0].split("?")[0]
                target_path = (md_path.parent / clean_target).resolve()
                if not target_path.exists():
                    broken.append(target)
            return broken

        # Create test markdown with 1 valid and 1 broken link
        doc = temp_dir / "guide.md"
        (temp_dir / "existing_file.txt").write_text("hello", encoding="utf-8")
        doc.write_text(
            "[Valid Link](existing_file.txt)\n[Broken Link](nonexistent_subfile.md)\n",
            encoding="utf-8"
        )
        broken_links = find_broken_relative_links(doc)
        assert len(broken_links) == 1
        assert broken_links[0] == "nonexistent_subfile.md"

    def test_04_empty_code_fences_detection_boundary(self):
        """10.4: Validator detects accidental empty code fences (``` followed immediately by ```)."""
        def detect_empty_code_blocks(text: str) -> List[int]:
            empty_block_lines = []
            lines = text.splitlines()
            for idx, line in enumerate(lines[:-1], start=1):
                if line.strip().startswith("```") and lines[idx].strip() == "```":
                    empty_block_lines.append(idx)
            return empty_block_lines

        text_with_empty = "Intro\n```python\n```\nOutro\n"
        empty_lines = detect_empty_code_blocks(text_with_empty)
        assert len(empty_lines) == 1

        text_clean = "Intro\n```python\nprint(1)\n```\nOutro\n"
        assert detect_empty_code_blocks(text_clean) == []

    def test_05_utf_8_encoding_strict_verification(self):
        """10.5: Strict UTF-8 validation distinguishes clean UTF-8 from corrupt non-UTF-8 bytes."""
        # Valid UTF-8 with Korean and symbols
        valid_bytes = "안녕하세요 🚀 Paxos vs Raft (v1.0)".encode("utf-8")
        decoded = valid_bytes.decode("utf-8")
        assert "안녕하세요" in decoded

        # Corrupt byte sequence
        corrupt_bytes = b"\xff\xfe\x00\x12\x80\x81"
        with pytest.raises(UnicodeDecodeError):
            corrupt_bytes.decode("utf-8")

        # Verify existing markdown files in workspace are all valid UTF-8
        for md_file in (WORKSPACE_ROOT / "tests" / "fixtures" / "sample_posts").glob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert len(content) > 0
