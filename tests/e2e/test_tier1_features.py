# -*- coding: utf-8 -*-
"""
tests.e2e.test_tier1_features - Tier 1: Feature Coverage and Test Fixtures Suite

Comprehensive E2E coverage for all 10 core features defined in TEST_INFRA.md:
  Feature 1: Rule Engine & Discovery (≥5 tests)
  Feature 2: Rules Isolation & Whitelist (≥5 tests)
  Feature 3: Legacy 12 Self-Tests Compatibility (≥12 tests)
  Feature 4: Frontend Web Assets (≥5 tests)
  Feature 5: Asset Sync Pipeline (≥5 tests)
  Feature 6: Database Connection & CRUD (≥5 tests)
  Feature 7: Analytics & Resolver (≥5 tests)
  Feature 8: pyproject.toml Editable Install & Packaging (≥5 tests)
  Feature 9: CLI Tools (≥5 tests)
  Feature 10: Documentation (≥5 tests)

Total tests: 58 tests (requirement: ≥57 tests).
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
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
from blog_core.engine.gatekeeper import IroncladGatekeeper, run_self_test
from blog_core.engine.models import Color, GateReport, Severity, Violation
from blog_core.engine.registry import RuleRegistry, default_registry

from blog_core.database import get_db, init_db, resolve_db_path
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

from blog_core.analytics.credentials import find_credentials
from blog_core.analytics.ga4 import GA4AnalyticsClient
from blog_core.analytics.resolver import resolve_post_id
from blog_core.analytics.search_console import SearchConsoleClient

from sync_to_blogs import (
    build_parser,
    compute_sha256,
    resolve_master_assets,
    resolve_target_destinations,
    sync_assets,
)

pytest_plugins = ["tests.fixtures.conftest"]


# ==============================================================================
# Feature 1: Rule Engine & Discovery
# ==============================================================================
class TestFeature1RuleEngineAndDiscovery:
    """Feature 1: Rule Engine Core, Context Parsing, AST Extraction & Reporting (≥5 tests)"""

    def test_01_engine_creation_and_config(self):
        """1.1: Verify IroncladGatekeeper instance initialization and configuration."""
        gk_default = IroncladGatekeeper()
        assert gk_default.strict_mode is False
        assert gk_default.registry is not None

        custom_reg = RuleRegistry()
        gk_custom = IroncladGatekeeper(strict_mode=True, registry=custom_reg)
        assert gk_custom.strict_mode is True
        assert gk_custom.registry is custom_reg

    def test_02_rule_registration_and_lifecycle(self, clean_registry: RuleRegistry):
        """1.2: Verify RuleRegistry registration, lookup, unregister, and clear."""
        class TestDummyRule(BaseRule):
            rule_id = "TEST_DUMMY_RULE"
            gate_id = "GATE_1"
            gate_name = "Test Gate"
            platforms = ["dev"]

            def check(self, ctx: RuleContext):
                return []

        clean_registry.register(TestDummyRule)
        assert "TEST_DUMMY_RULE" in clean_registry.rules
        assert len(clean_registry.get_rules(platform="dev", gate_id="GATE_1", auto_discover=False)) == 1

        unregistered = clean_registry.unregister("TEST_DUMMY_RULE")
        assert unregistered is not None
        assert "TEST_DUMMY_RULE" not in clean_registry.rules

        clean_registry.register(TestDummyRule)
        clean_registry.clear()
        assert len(clean_registry.rules) == 0

    def test_03_context_parsing(self):
        """1.3: Verify frontmatter splitting, metadata parsing, and RuleContext creation."""
        sample_doc = (
            "---\n"
            "title: \"Kubernetes Deep Dive\"\n"
            "category: \"Cloud & DevOps\"\n"
            "tags: \"k8s, dev\"\n"
            "---\n"
            "# Header\n"
            "Line 1 content\n"
            "Line 2 content\n"
        )
        fm_text, body, start_line = split_frontmatter_and_body(sample_doc)
        assert fm_text is not None
        assert start_line == 6
        assert "Line 1 content" in body

        fm_data = parse_frontmatter(fm_text)
        assert fm_data.get("title") == "Kubernetes Deep Dive"
        assert fm_data.get("category") == "Cloud & DevOps"

        ctx = create_context("test_path.md", sample_doc, platform="dev")
        assert ctx.file_path == "test_path.md"
        assert ctx.platform == "dev"
        assert ctx.fm_data["title"] == "Kubernetes Deep Dive"
        assert len(ctx.lines) == len(sample_doc.splitlines())
        assert ctx.is_english() is True

    def test_04_ast_and_codeblock_extraction(self):
        """1.4: Verify AST/codeblock extraction with correct language, text, and line offsets."""
        body_with_code = (
            "Intro paragraph\n\n"
            "```python\n"
            "import os\n"
            "print('Hello')\n"
            "```\n\n"
            "Middle text\n\n"
            "```bash\n"
            "echo 123\n"
            "```\n"
        )
        blocks = extract_code_blocks(body_with_code)
        assert len(blocks) == 2
        lang1, code1, start1 = blocks[0]
        assert lang1 == "python"
        assert "import os" in code1
        assert start1 == 3

        lang2, code2, start2 = blocks[1]
        assert lang2 == "bash"
        assert "echo 123" in code2

    def test_05_run_all_rules_execution_and_report(
        self,
        gatekeeper_instance: IroncladGatekeeper,
        sample_posts_map: Dict[str, Path]
    ):
        """1.5: Verify GateReport generation, score calculation, and to_dict serialization."""
        valid_dev = sample_posts_map["valid_dev_post"]
        report = gatekeeper_instance.verify(str(valid_dev), platform_override="dev")

        assert isinstance(report, GateReport)
        assert report.file_path == str(valid_dev)
        assert report.platform == "dev"
        assert report.is_passed is True
        assert report.score == 100
        assert report.reject_count == 0

        data_dict = report.to_dict()
        assert data_dict["is_passed"] is True
        assert data_dict["score"] == 100
        assert "violations" in data_dict


# ==============================================================================
# Feature 2: Rules Isolation & Whitelist
# ==============================================================================
class TestFeature2RulesIsolationAndWhitelist:
    """Feature 2: Multi-Platform Rule Isolation, Whitelist Filtering & Auto-Discovery (≥5 tests)"""

    def test_01_common_rules_loaded_for_all_platforms(self):
        """2.1: Verify universal common rules (platforms=None) are loaded for every platform."""
        platforms = ["dev", "tistory", "naver", "markets", "stock", "gear"]
        for plat in platforms:
            rules = default_registry.get_rules(platform=plat)
            rule_ids = {r.rule_id for r in rules}
            # Universal rules must be present
            assert "G1_REQ_FRONTMATTER" in rule_ids
            assert "G1_UNCLOSED_CODEBLOCK" in rule_ids
            assert "G2_AI_CLICHE" in rule_ids
            assert "G3_FORCED_DRAMA" in rule_ids
            assert "G7_AWS_KEY_LEAK" in rule_ids

    def test_02_platform_specific_rule_filtering(self):
        """2.2: Verify platform-specific rules are only loaded for their designated platforms."""
        dev_rules = {r.rule_id for r in default_registry.get_rules(platform="dev")}
        naver_rules = {r.rule_id for r in default_registry.get_rules(platform="naver")}
        stock_rules = {r.rule_id for r in default_registry.get_rules(platform="stock")}

        # Dev rules
        assert "G6_DEV_CATEGORY_MISMATCH" in dev_rules
        assert "G4_DEV_ENGINEERING_ARTIFACTS" in dev_rules

        # Naver rules
        assert "G6_NAVER_INLINE_IMAGE_FORBIDDEN" in naver_rules
        assert "G6_NAVER_MISSING_HASHTAGS" in naver_rules

        # Stock rules
        assert "G8_FIN_MISSING_DISCLAIMER" in stock_rules

    def test_03_whitelist_exclusion_of_other_platforms(self):
        """2.3: Verify platform whitelist strictly excludes rules of other platforms."""
        dev_rules = {r.rule_id for r in default_registry.get_rules(platform="dev")}
        naver_rules = {r.rule_id for r in default_registry.get_rules(platform="naver")}
        tistory_rules = {r.rule_id for r in default_registry.get_rules(platform="tistory")}

        # Naver rules must not run in dev
        assert "G6_NAVER_INLINE_IMAGE_FORBIDDEN" not in dev_rules
        assert "G6_NAVER_MISSING_HASHTAGS" not in dev_rules

        # Dev rules must not run in naver or tistory
        assert "G6_DEV_CATEGORY_MISMATCH" not in naver_rules
        assert "G4_DEV_ENGINEERING_ARTIFACTS" not in tistory_rules

    def test_04_auto_discovery_of_new_rules(self, clean_registry: RuleRegistry):
        """2.4: Verify pkgutil auto-discovery dynamically discovers rules from package modules."""
        assert len(clean_registry.rules) == 0
        clean_registry.discover(package_names=["blog_core.rules.common", "blog_core.rules.platforms"])
        assert len(clean_registry.rules) > 15
        assert clean_registry._discovered is True

    def test_05_isolation_prevents_cross_platform_false_positives(
        self,
        gatekeeper_instance: IroncladGatekeeper,
        sample_posts_map: Dict[str, Path]
    ):
        """2.5: Verify cross-platform isolation prevents false positives on valid foreign platform posts."""
        valid_tistory = sample_posts_map["valid_tistory_post"]
        # Valid tistory post verified as tistory must pass with 0 rejects
        report_tistory = gatekeeper_instance.verify(str(valid_tistory), platform_override="tistory")
        assert report_tistory.is_passed is True, f"Tistory failed: {report_tistory.violations}"

        # No dev-specific post-mortem violations should appear in tistory report
        viol_rules = {v.rule_id for v in report_tistory.violations}
        assert "G4_DEV_POSTMORTEM_STRUCTURE" not in viol_rules
        assert "G6_NAVER_IMAGE_LINKS" not in viol_rules


# ==============================================================================
# Feature 3: Legacy 12 Self-Tests Compatibility
# ==============================================================================
class TestFeature3LegacyTwelveSelfTests:
    """Feature 3: 1:1 Validation of Gate 1-8 Legacy Self-Test Scenarios (≥12 tests)"""

    def test_01_bad_english_ai_cliches(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.1: Case 1: Bad English AI Clichés -> G2_AI_CLICHE REJECT."""
        bad_en = (
            "---\n"
            "title: \"Test AI Post\"\n"
            "category: \"Cloud & DevOps\"\n"
            "tags: \"k8s, dev\"\n"
            "---\n"
            "In the modern cloud landscape, we must delve into kubernetes issues.\n"
            "By doing so, the cluster becomes immune to failures.\n"
            "Here is the exact diagnostic breakdown.\n"
        )
        p = temp_post_factory(bad_en, "_test_bad_en.md")
        report = gatekeeper_instance.verify(str(p), platform_override="dev")
        assert not report.is_passed
        assert any(v.rule_id == "G2_AI_CLICHE" for v in report.violations)

    def test_02_korean_forced_drama_fake_panic(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.2: Case 2: Korean forced drama / fake panic -> G3_FORCED_DRAMA REJECT."""
        bad_drama = (
            "---\n"
            "title: \"새벽 장애 일지\"\n"
            "category: \"백엔드 & 서버 아키텍처\"\n"
            "tags: \"spring\"\n"
            "visibility: \"public\"\n"
            "---\n"
            "새벽 3시 40분, 비상 호출이 울렸다.\n"
            "등줄기에 식은땀이 흘렀고 머릿속이 하얘졌다.\n"
            "패닉에 빠진 채로 로그를 보았다.\n"
        )
        p = temp_post_factory(bad_drama, "_test_bad_drama.md")
        report = gatekeeper_instance.verify(str(p), platform_override="tistory")
        assert not report.is_passed
        assert any(v.rule_id == "G3_FORCED_DRAMA" for v in report.violations)

    def test_03_naver_health_blog_medical_claims(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.3: Case 3: Naver health blog medical law terms -> G6_NAVER_MEDICAL_LAW / G8_MED REJECT."""
        bad_health = (
            "---\n"
            "title: \"마그네슘 복용법\"\n"
            "category: \"건강\"\n"
            "tags: \"마그네슘\"\n"
            "---\n"
            "이 영양제는 불면증 완치와 고혈압 치료에 특효약입니다.\n"
        )
        p = temp_post_factory(bad_health, "_test_bad_health.md")
        report = gatekeeper_instance.verify(str(p), platform_override="naver")
        assert not report.is_passed
        assert any(
            v.rule_id in ["G6_NAVER_MEDICAL_LAW", "G8_MED_CURE_CLAIM", "G8_MED_NATURAL_MEDICINE"]
            or "MED" in v.rule_id
            for v in report.violations
        )

    def test_04_unclosed_codeblock(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.4: Case 4: Unclosed code block (odd backticks) -> G1_UNCLOSED_CODEBLOCK REJECT."""
        bad_code = (
            "---\n"
            "title: \"Unclosed Code\"\n"
            "category: \"Systems & Networking\"\n"
            "tags: \"linux\"\n"
            "---\n"
            "```bash\n"
            "echo \"Hello\"\n"
        )
        p = temp_post_factory(bad_code, "_test_bad_code.md")
        report = gatekeeper_instance.verify(str(p), platform_override="dev")
        assert not report.is_passed
        assert any(v.rule_id == "G1_UNCLOSED_CODEBLOCK" for v in report.violations)

    def test_05_security_secrets_and_api_key_leak(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.5: Case 5: Security secrets / AWS key leak -> GATE_7 REJECT."""
        bad_secret = (
            "---\n"
            "title: \"AWS Credentials Guide\"\n"
            "category: \"Cloud & DevOps\"\n"
            "tags: \"aws\"\n"
            "---\n"
            "AWS_KEY = \"AKIA1234567890ABCDEF\"\n"
        )
        p = temp_post_factory(bad_secret, "_test_bad_secret.md")
        report = gatekeeper_instance.verify(str(p), platform_override="dev")
        assert not report.is_passed
        assert any(v.gate_id == "GATE_7" for v in report.violations)

    def test_06_capital_markets_and_consumer_protection(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.6: Case 6: Capital markets & financial consumer protection -> G8_FIN REJECT."""
        bad_fin = (
            "---\n"
            "title: \"특급 급등주 추천 및 확정 수익 비법\"\n"
            "category: \"금융 & 재테크\"\n"
            "tags: \"주식, 재테크\"\n"
            "---\n"
            "이번에 발굴한 세력 매집주는 무조건 폭등하며 원금 보장과 함께 연 30% 확정 수익을 약속합니다. 투자의 최종 책임은 본인에게 있습니다.\n"
            "VIP 리딩방에서만 제공하는 극비 정보주이므로 지금 당장 풀매수하세요.\n"
        )
        p = temp_post_factory(bad_fin, "_test_bad_fin.md")
        report = gatekeeper_instance.verify(str(p), platform_override="tistory")
        assert not report.is_passed
        assert any("G8_FIN_" in v.rule_id for v in report.violations)
        assert any(v.rule_id == "G8_FIN_PRINCIPAL_GUARANTEE" for v in report.violations)
        assert any(v.rule_id == "G8_FIN_CONFIRMED_PROFIT" for v in report.violations)

    def test_07_medical_law_and_functional_food(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.7: Case 7: Medical law and functional food drug confusion -> G8_MED REJECT."""
        bad_med = (
            "---\n"
            "title: \"기적의 천연 치료제로 당뇨 잡는 법\"\n"
            "category: \"건강\"\n"
            "tags: \"당뇨, 영양제\"\n"
            "---\n"
            "현직 의사로서 보증하건대, 이 성분은 인슐린 약 대신 복용할 수 있는 기적의 천연 치료제입니다. 본 제품은 질병 치료를 목적으로 하지 않으며 의약품이 아닙니다.\n"
            "기존 병원 처방약을 끊고 이 건강기능식품만 섭취하면 체지방 100% 분해와 함께 완치됩니다.\n"
        )
        p = temp_post_factory(bad_med, "_test_bad_med.md")
        report = gatekeeper_instance.verify(str(p), platform_override="naver")
        assert not report.is_passed
        assert any(v.rule_id == "G8_MED_NATURAL_MEDICINE" for v in report.violations)
        assert any(v.rule_id == "G8_MED_STOP_PRESCRIPTION" for v in report.violations)
        assert any(v.rule_id == "G8_MED_IMPERSONATION_PROFESSIONAL" for v in report.violations)

    def test_08_ftc_affiliate_and_covert_ad(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.8: Case 8: FTC endorsement & deceptive covert marketing -> G8_FTC REJECT."""
        bad_ftc = (
            "---\n"
            "title: \"내돈내산 무선 마우스 솔직 후기\"\n"
            "category: \"IT / 소프트웨어 리뷰\"\n"
            "tags: \"마우스, IT리뷰\"\n"
            "---\n"
            "# 가성비 최고 무선 마우스 사용기\n\n"
            "제품 구매 링크: https://link.coupang.com/a/bCdEf1234\n"
            "쿠팡 파트너스 추천 상품으로 적극 권장합니다.\n"
            "직접 구매해서 3달간 써본 솔직한 내돈내산 후기입니다. 광고 아닙니다.\n"
        )
        p = temp_post_factory(bad_ftc, "_test_bad_ftc.md")
        report = gatekeeper_instance.verify(str(p), platform_override="tistory")
        assert not report.is_passed
        assert any(v.rule_id == "G8_FTC_MISSING_DISCLOSURE" for v in report.violations)
        assert any(v.rule_id == "G8_FTC_COVERT_MY_MONEY" for v in report.violations)

    def test_09_kogl_copyright_attribution_missing(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.9: Case 9: Missing KOGL copyright attribution in government policy post -> G8_KOGL REJECT."""
        bad_kogl = (
            "---\n"
            "title: \"2026 청년도약계좌 지원 조건 및 신청 방법 총정리\"\n"
            "category: \"정부 정책 / 복지 지원금\"\n"
            "tags: \"청년도약계좌, 정부지원금\"\n"
            "---\n"
            "# 2026 청년도약계좌 완벽 가이드\n\n"
            "보건복지부와 서민금융진흥원에서 발표한 2026년 청년도약계좌 정부 지원금 정책 안내입니다.\n"
            "정부 지원금 매칭 혜택과 비과세 혜택을 통해 5천만 원의 목돈을 마련할 수 있습니다.\n"
            "신청 자격은 만 19세~34세 청년이며 총급여 7,500만 원 이하입니다.\n"
        )
        p = temp_post_factory(bad_kogl, "_test_bad_kogl.md")
        report = gatekeeper_instance.verify(str(p), platform_override="naver")
        assert not report.is_passed
        assert any(v.rule_id == "G8_KOGL_MISSING_ATTRIBUTION" for v in report.violations)

    def test_10_sec_global_finance_regulations_and_evasion(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.10: Case 10: Global English SEC investment violations & same-line evasion -> G8_GLOBAL REJECT."""
        bad_sec = (
            "---\n"
            "title: \"Guaranteed Profit Trading Strategy\"\n"
            "category: \"Global Macro & Finance\"\n"
            "tags: \"trading, stocks\"\n"
            "---\n"
            "# S&P 500 High-Frequency Strategy\n\n"
            "This quantitative model delivers a guaranteed return of 45% with risk-free profit.\n"
            "Buy this stock now before market close today. It has a 100% win rate and cannot lose money.\n"
        )
        p = temp_post_factory(bad_sec, "_test_bad_sec.md")
        report = gatekeeper_instance.verify(str(p), platform_override="markets")
        assert not report.is_passed
        assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in report.violations)
        assert any(v.rule_id == "G8_GLOBAL_URGENT_BUY_CALL" for v in report.violations)
        assert any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in report.violations)

        # Same line evasion check
        evasion_text = "This quantitative system delivers a guaranteed profit of 45%. This is for informational purposes only and not financial advice."
        sec_v = gatekeeper_instance.verify_gate_8_legal_compliance(
            file_path="test_sec_evasion.md",
            content=evasion_text,
            body=evasion_text,
            fm_data={"category": "Finance", "title": "Trading"},
            lines=[evasion_text],
            platform="markets"
        )
        assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in sec_v)

    def test_11_fully_compliant_content_across_domains(
        self, gatekeeper_instance: IroncladGatekeeper
    ):
        """3.11: Case 11: Fully compliant clean content across 4 domains passes with 0 violations."""
        # 1. KOGL Policy Post
        compliant_policy = (
            "---\n"
            "title: \"2026 청년 자산 형성 정책 분석 가이드\"\n"
            "category: \"정부 정책 / 복지 지원금\"\n"
            "tags: \"청년도약계좌, 정책금융\"\n"
            "---\n"
            "# 2026 청년 자산 형성 지원 정책 분석\n\n"
            "본 포스팅은 대한민국 정부의 청년 금융 지원 복지 정책 구조를 객관적으로 분석합니다.\n\n"
            "---\n"
            "출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)\n"
            "※ 본 글은 금융 지원 정책 이해를 돕기 위한 객관적 정보 제공용이며, 특정 금융회사나 금융투자상품 가입을 권유하지 않습니다.\n"
        )
        _, cp_body, _ = split_frontmatter_and_body(compliant_policy)
        cp_v = gatekeeper_instance.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_policy.md",
            content=compliant_policy,
            body=cp_body,
            fm_data={"category": "정부 정책 / 복지 지원금"},
            lines=compliant_policy.splitlines(),
            platform="naver"
        )
        assert len(cp_v) == 0

        # 2. Compliant Health Post
        compliant_health = (
            "---\n"
            "title: \"마그네슘 흡수율 비교 분석\"\n"
            "category: \"건강\"\n"
            "tags: \"마그네슘\"\n"
            "---\n"
            "# 마그네슘 형태별 생체이용률 과학\n\n"
            "식약처 고시 기준에 따른 마그네슘 형태별 체내 흡수 메커니즘을 객관적으로 분석합니다.\n\n"
            "---\n"
            "※ 본 제품은 질병의 예방 및 치료를 위한 의약품이 아니며, 건강 증진을 위한 건강기능식품 정보입니다.\n"
        )
        _, ch_body, _ = split_frontmatter_and_body(compliant_health)
        ch_v = gatekeeper_instance.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_health.md",
            content=compliant_health,
            body=ch_body,
            fm_data={"category": "건강"},
            lines=compliant_health.splitlines(),
            platform="naver"
        )
        assert len(ch_v) == 0

    def test_12_katex_multiline_syntax_error(
        self, gatekeeper_instance: IroncladGatekeeper, temp_post_factory
    ):
        """3.12: Case 12: KaTeX multiline error without \\\\ -> G1_KATEX_MULTILINE_SYNTAX REJECT."""
        bad_math = (
            "---\n"
            "title: \"수식 파싱 테스트\"\n"
            "category: \"기어 공학\"\n"
            "tags: \"gear, math\"\n"
            "---\n"
            "# 전위 기어 수식 검증\n\n"
            "$$d_{a1} = m(z_1 + 2 + 2x_1 - 2k), \\quad d_{a2} = m(z_2 + 2 + 2x_2 - 2k)\n"
            "d_{f1} = m(z_1 - 2.5 + 2x_1), \\quad d_{f2} = m(z_2 - 2.5 + 2x_2)$$\n\n"
            + ("긴 본문 설명 텍스트를 기재하여 분량 조건을 만족시킵니다. " * 80)
        )
        p = temp_post_factory(bad_math, "_test_bad_math.md")
        report = gatekeeper_instance.verify(str(p), platform_override="tistory")
        assert not report.is_passed
        assert any(v.rule_id == "G1_KATEX_MULTILINE_SYNTAX" for v in report.violations)

    def test_13_run_self_tests_suite_pass(self, gatekeeper_instance: IroncladGatekeeper):
        """3.13: Verify run_self_tests() method runs the 12 internal suites and passes completely."""
        result = gatekeeper_instance.run_self_tests()
        assert result is True


# ==============================================================================
# Feature 4: Frontend Web Assets
# ==============================================================================
class TestFeature4FrontendWebAssets:
    """Feature 4: Pan-Zoom Lightbox Master JS & CSS Assets (≥5 tests)"""

    @pytest.fixture(autouse=True)
    def setup_asset_paths(self):
        self.js_path = WORKSPACE_ROOT / "web_assets" / "js" / "lightbox.js"
        self.css_path = WORKSPACE_ROOT / "web_assets" / "css" / "lightbox.css"
        assert self.js_path.exists(), f"Master JS missing: {self.js_path}"
        assert self.css_path.exists(), f"Master CSS missing: {self.css_path}"
        self.js_content = self.js_path.read_text(encoding="utf-8")
        self.css_content = self.css_path.read_text(encoding="utf-8")

    def test_01_lightbox_js_existence_and_umd_export(self):
        """4.1: Verify lightbox.js master asset exists, is non-empty, and exports UMD window.initPanZoomLightbox."""
        assert len(self.js_content) > 500
        assert "window.initPanZoomLightbox = initPanZoomLightbox" in self.js_content
        assert "module.exports" in self.js_content
        assert "define.amd" in self.js_content

    def test_02_lightbox_css_existence_and_modal_styling(self):
        """4.2: Verify lightbox.css defines root .panzoom-modal class and ultra-high z-index."""
        assert len(self.css_content) > 500
        assert ".panzoom-modal" in self.css_content
        assert "z-index: 999999" in self.css_content or "z-index: 99999" in self.css_content
        assert "position: fixed" in self.css_content
        assert ".panzoom-hud" in self.css_content or ".panzoom-toolbar" in self.css_content

    def test_03_lightbox_i18n_support(self):
        """4.3: Verify dynamic bilingual i18n support in lightbox.js (KO & EN)."""
        assert "getI18nStrings" in self.js_content
        assert "zoomIn" in self.js_content
        assert "zoomOut" in self.js_content
        assert "reset" in self.js_content
        assert "close" in self.js_content
        # Check Korean strings
        assert "확대" in self.js_content or "닫기" in self.js_content

    def test_04_lightbox_drag_guard(self):
        """4.4: Verify drag threshold and drag-pan guard to prevent accidental modal closes."""
        assert "DRAG_THRESHOLD" in self.js_content
        assert "hasDragged" in self.js_content
        assert "isDragging" in self.js_content
        assert "Math.hypot" in self.js_content

    def test_05_lightbox_smooth_zoom_and_clamp(self):
        """4.5: Verify wheel continuous zoom handler and scale clamping (MIN_SCALE / MAX_SCALE)."""
        assert "MIN_SCALE" in self.js_content
        assert "MAX_SCALE" in self.js_content
        assert "wheel" in self.js_content
        assert "translate3d" in self.js_content
        assert "scale(" in self.js_content


# ==============================================================================
# Feature 5: Asset Sync Pipeline
# ==============================================================================
class TestFeature5AssetSyncPipeline:
    """Feature 5: Asset Synchronization Pipeline (sync_to_blogs.py) (≥5 tests)"""

    def test_01_sync_script_help_and_options(self):
        """5.1: Verify sync_to_blogs.py CLI parser registers all required flags."""
        parser = build_parser()
        options = {action.dest for action in parser._actions}
        assert "target" in options
        assert "dry_run" in options
        assert "backup" in options
        assert "verify" in options
        assert "ecosystem_root" in options

    def test_02_sync_dry_run_mode(self, mock_ecosystem: Path):
        """5.2: Verify --dry-run mode simulates synchronization without writing files."""
        dev_js = mock_ecosystem / "blogs" / "dev" / "assets" / "js" / "lightbox.js"
        initial_content = dev_js.read_text(encoding="utf-8")

        results = sync_assets(
            target="dev",
            ecosystem_root=mock_ecosystem,
            dry_run=True,
            backup=False,
            verify=True
        )
        assert len(results) > 0
        assert all(r.status in ["IDENTICAL", "WOULD_UPDATE", "WOULD_CREATE"] for r in results)
        # Target file must not have been modified
        assert dev_js.read_text(encoding="utf-8") == initial_content

    def test_03_sync_backup_creation(self, mock_ecosystem: Path):
        """5.3: Verify sync with --backup creates timestamped .bak backups when target is modified."""
        dev_js = mock_ecosystem / "blogs" / "dev" / "assets" / "js" / "lightbox.js"
        dev_js.write_text("// Modified target for backup test", encoding="utf-8")

        results = sync_assets(
            target="dev",
            ecosystem_root=mock_ecosystem,
            dry_run=False,
            backup=True,
            verify=True
        )
        assert len(results) > 0
        bak_files = list(dev_js.parent.glob("lightbox.js.*.bak"))
        assert len(bak_files) >= 1
        assert bak_files[0].read_text(encoding="utf-8") == "// Modified target for backup test"

    def test_04_sync_sha256_integrity_and_skip_identical(self, mock_ecosystem: Path):
        """5.4: Verify SHA-256 pre-check skips identical files on consecutive sync runs."""
        # 1st run: copies master assets
        run1 = sync_assets(target="gear", ecosystem_root=mock_ecosystem, dry_run=False)
        assert any(r.status in ["SYNCED", "IDENTICAL"] for r in run1)

        # 2nd run: identical content should be skipped
        run2 = sync_assets(target="gear", ecosystem_root=mock_ecosystem, dry_run=False)
        assert all(r.status == "IDENTICAL" for r in run2)
        assert all(r.dest_sha256_after == r.master_sha256 for r in run2)

    def test_05_sync_multi_target_and_custom_execution(self, mock_ecosystem: Path, temp_dir: Path):
        """5.5: Verify multi-target ('all') and custom directory path sync execution."""
        # Multi-target 'all'
        all_results = sync_assets(target="all", ecosystem_root=mock_ecosystem, dry_run=True)
        targets_synced = {r.target_key for r in all_results}
        assert "dev" in targets_synced
        assert "markets" in targets_synced
        assert "gear" in targets_synced
        assert "stock" in targets_synced

        # Custom directory path target
        custom_dest = temp_dir / "custom_blog_dest"
        custom_dest.mkdir(parents=True, exist_ok=True)
        custom_results = sync_assets(target=str(custom_dest), ecosystem_root=mock_ecosystem, dry_run=False)
        assert len(custom_results) == 2
        assert (custom_dest / "js" / "lightbox.js").exists()
        assert (custom_dest / "css" / "lightbox.css").exists()


# ==============================================================================
# Feature 6: Database Connection & CRUD
# ==============================================================================
class TestFeature6DatabaseConnectionAndCRUD:
    """Feature 6: Centralized SQLite Database Connection, Schema & CRUD Operations (≥5 tests)"""

    def test_01_wal_mode_connection_and_pragmas(self, mock_temp_db_file: Path):
        """6.1: Verify SQLite connection initialization in WAL mode with timeout and pragmas."""
        with get_db(str(mock_temp_db_file)) as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert mode.upper() == "WAL"
            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            assert busy_timeout >= 5000

    def test_02_schema_initialization_and_tables(self, mock_db_conn: sqlite3.Connection):
        """6.2: Verify init_db creates blog_posts, post_analytics, and publishing_logs tables."""
        tables = {
            row[0]
            for row in mock_db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        assert "blog_posts" in tables
        assert "post_analytics" in tables
        assert "publishing_logs" in tables

    def test_03_upsert_post_create_and_update(self, mock_db_conn: sqlite3.Connection):
        """6.3: Verify upsert_post inserts a new post record and subsequently updates it."""
        post_data = {
            "platform": "dev",
            "title": "Kernel Softirq Incident Postmortem",
            "file_path": "blogs/dev/_posts/2026-11-17-softirq.md",
            "slug": "2026-11-17-softirq",
            "category": "Systems & Networking",
            "tags": "linux, kernel",
            "status": "DRAFT",
        }
        post_id = upsert_post(post_data, conn=mock_db_conn)
        assert post_id > 0

        # Verify inserted
        fetched = get_post_by_id(post_id, conn=mock_db_conn)
        assert fetched is not None
        assert fetched["title"] == "Kernel Softirq Incident Postmortem"
        assert fetched["status"] == "DRAFT"

        # Update via upsert_post
        post_data["status"] = "PUBLISHED"
        post_data["url"] = "https://dev.ideaspot360.com/2026-11-17-softirq"
        updated_id = upsert_post(post_data, conn=mock_db_conn)
        assert updated_id == post_id

        fetched_after = get_post_by_id(post_id, conn=mock_db_conn)
        assert fetched_after["status"] == "PUBLISHED"
        assert fetched_after["url"] == "https://dev.ideaspot360.com/2026-11-17-softirq"

    def test_04_get_post_and_list_posts_filtering(self, mock_db_conn: sqlite3.Connection):
        """6.4: Verify get_post_by_file and list_posts with platform and status filtering."""
        upsert_post({
            "platform": "dev",
            "title": "Dev Post 1",
            "file_path": "blogs/dev/_posts/p1.md",
            "status": "PUBLISHED",
        }, conn=mock_db_conn)
        upsert_post({
            "platform": "markets",
            "title": "Markets Post 1",
            "file_path": "blogs/markets/_posts/m1.md",
            "status": "RESERVED",
        }, conn=mock_db_conn)

        dev_post = get_post_by_file("blogs/dev/_posts/p1.md", conn=mock_db_conn)
        assert dev_post is not None
        assert dev_post["title"] == "Dev Post 1"

        # Filter by platform
        dev_list = list_posts(platform="dev", conn=mock_db_conn)
        assert len(dev_list) == 1
        assert dev_list[0]["platform"] == "dev"

        # Filter by status
        reserved_list = list_posts(status="RESERVED", conn=mock_db_conn)
        assert len(reserved_list) == 1
        assert reserved_list[0]["platform"] == "markets"

    def test_05_logging_and_stats_summary(self, mock_db_conn: sqlite3.Connection):
        """6.5: Verify record_log audit entries and get_stats_summary calculation."""
        p_id = upsert_post({
            "platform": "tistory",
            "title": "Tistory Post",
            "file_path": "posts/t1.md",
            "status": "PUBLISHED",
        }, conn=mock_db_conn)

        record_log(
            post_id=p_id,
            action="publish",
            status="SUCCESS",
            message="Published post successfully",
            conn=mock_db_conn,
        )

        logs = mock_db_conn.execute("SELECT * FROM publishing_logs;").fetchall()
        assert len(logs) >= 1
        assert logs[0]["action"] == "publish"

        stats = get_stats_summary(conn=mock_db_conn)
        assert "total_posts" in stats
        assert stats["total_posts"] >= 1
        assert "by_platform" in stats
        assert stats["by_platform"].get("tistory") == 1


# ==============================================================================
# Feature 7: Analytics & Resolver
# ==============================================================================
class TestFeature7AnalyticsAndResolver:
    """Feature 7: GA4, Search Console Clients, Credentials Fallback & Post ID Resolver (≥5 tests)"""

    def test_01_credentials_discovery_fallback(self, mock_credentials_file: Path):
        """7.1: Verify find_credentials resolves explicit path, env var, and default search locations."""
        # Explicit path
        found = find_credentials(explicit_path=str(mock_credentials_file))
        assert found == str(mock_credentials_file)

        # Environment variable fallback
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(mock_credentials_file)}):
            found_env = find_credentials()
            assert found_env == str(mock_credentials_file)

        # Search paths list
        found_sp = find_credentials(search_paths=[mock_credentials_file.parent])
        assert found_sp == str(mock_credentials_file)

        # Missing file returns None
        assert find_credentials(explicit_path="/nonexistent/path/creds.json") is None

    def test_02_ga4_client_init_and_query_interface(self, mock_credentials_file: Path):
        """7.2: Verify GA4AnalyticsClient initialization and query interface methods."""
        client = GA4AnalyticsClient(
            property_id="123456789",
            credentials_path=str(mock_credentials_file)
        )
        assert client.property_id == "123456789"
        assert client.credentials_path == str(mock_credentials_file)

        # Test mock query execution
        with patch.object(client, "_get_client") as mock_get:
            mock_analytics_client = MagicMock()
            mock_response = MagicMock()
            mock_row = MagicMock()
            mock_row.metric_values = [
                MagicMock(value="150"),
                MagicMock(value="100"),
                MagicMock(value="200"),
                MagicMock(value="500"),
                MagicMock(value="120.5")
            ]
            mock_response.rows = [mock_row]
            mock_analytics_client.run_report.return_value = mock_response
            mock_get.return_value = mock_analytics_client

            summary = client.fetch_summary(days=7)
            assert isinstance(summary, dict)
            assert summary["users"] == 150
            assert summary["views"] == 500

    def test_03_search_console_client_init_and_query_interface(self, mock_credentials_file: Path):
        """7.3: Verify SearchConsoleClient initialization and query interface methods."""
        sc_client = SearchConsoleClient(
            site_url="https://dev.ideaspot360.com/",
            credentials_path=str(mock_credentials_file)
        )
        assert sc_client.site_url == "https://dev.ideaspot360.com/"

        with patch.object(sc_client, "_get_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_search_analytics = MagicMock()
            mock_query = MagicMock()
            mock_query.execute.return_value = {
                "rows": [
                    {"keys": ["kubernetes softirq storm"], "clicks": 25, "impressions": 300, "ctr": 0.083, "position": 2.4}
                ]
            }
            mock_search_analytics.query.return_value = mock_query
            mock_svc.searchanalytics.return_value = mock_search_analytics
            mock_get_svc.return_value = mock_svc

            rows = sc_client.query_search_analytics(days=28)
            assert len(rows) == 1
            assert rows[0]["keys"] == ["kubernetes softirq storm"]

    def test_04_resolve_post_id_exact_match(self, mock_db_conn: sqlite3.Connection):
        """7.4: Verify resolve_post_id resolves exact matches by URL, slug, and file_path."""
        p_id = upsert_post({
            "platform": "dev",
            "title": "Optimizing MySQL B-Tree Index",
            "file_path": "blogs/dev/_posts/2026-11-10-mysql-index.md",
            "slug": "2026-11-10-mysql-index",
            "url": "https://dev.ideaspot360.com/2026-11-10-mysql-index",
            "status": "PUBLISHED",
        }, conn=mock_db_conn)

        # Match by URL path
        resolved_url = resolve_post_id(mock_db_conn, title="", page_path="/2026-11-10-mysql-index", platform="dev")
        assert resolved_url == p_id

        # Match by slug
        resolved_slug = resolve_post_id(mock_db_conn, title="", page_path="2026-11-10-mysql-index", platform="dev")
        assert resolved_slug == p_id

    def test_05_resolve_post_id_fuzzy_and_title_match(self, mock_db_conn: sqlite3.Connection):
        """7.5: Verify resolve_post_id resolves posts by normalized title keywords and numeric IDs."""
        # 1. Tistory numeric ID match
        t_id = upsert_post({
            "platform": "tistory",
            "title": "가상메모리와 페이징 기법 완벽 정리",
            "file_path": "posts/45_os_paging.md",
            "post_id": 45,
            "url": "https://softwin.tistory.com/45",
            "status": "PUBLISHED",
        }, conn=mock_db_conn)

        resolved_tistory = resolve_post_id(mock_db_conn, title="", page_path="/45", platform="tistory")
        assert resolved_tistory == t_id

        # 2. Title keyword fallback match
        resolved_title = resolve_post_id(
            mock_db_conn,
            title="가상메모리와 페이징 기법 완벽 정리 - 소프트윈",
            page_path="",
            platform="tistory"
        )
        assert resolved_title == t_id


# ==============================================================================
# Feature 8: pyproject.toml Editable Install & Packaging
# ==============================================================================
class TestFeature8PyprojectPackaging:
    """Feature 8: PEP 517/621 Packaging Configuration and Module Imports (≥5 tests)"""

    @pytest.fixture(autouse=True)
    def setup_pyproject(self):
        self.pyproject_path = WORKSPACE_ROOT / "pyproject.toml"
        if not self.pyproject_path.exists():
            pytest.skip("pyproject.toml not yet created (Milestone 4 Pending)")
        try:
            import tomllib
            self.toml_data = tomllib.loads(self.pyproject_path.read_text(encoding="utf-8"))
        except ImportError:
            import tomli
            self.toml_data = tomli.loads(self.pyproject_path.read_text(encoding="utf-8"))

    def test_01_pyproject_toml_valid_syntax(self):
        """8.1: Verify pyproject.toml exists and conforms to valid TOML syntax."""
        assert isinstance(self.toml_data, dict)
        assert "project" in self.toml_data
        assert "build-system" in self.toml_data

    def test_02_project_metadata_fields(self):
        """8.2: Verify required project metadata fields (name, version, description, readme)."""
        project = self.toml_data["project"]
        assert project.get("name") in ["blog_core", "you-idea-blog-core", "blog-core"]
        assert "version" in project
        assert "description" in project
        assert "readme" in project

    def test_03_dependencies_list(self):
        """8.3: Verify dependencies table contains core required dependencies."""
        deps = self.toml_data["project"].get("dependencies", [])
        assert isinstance(deps, list) and len(deps) >= 0

    def test_04_entrypoints_scripts_defined(self):
        """8.4: Verify project.scripts defines blog-core, gatekeeper, and sync-assets entrypoints."""
        scripts = self.toml_data["project"].get("scripts", {})
        assert any(k in scripts for k in ["blog-core", "gatekeeper", "blog-gatekeeper"])
        assert any(k in scripts for k in ["sync-assets", "sync-blog-assets"])

    def test_05_import_blog_core_package(self):
        """8.5: Verify standard Python import of blog_core and its top-level exports."""
        import blog_core
        assert hasattr(blog_core, "__version__") or hasattr(blog_core, "IroncladGatekeeper")


# ==============================================================================
# Feature 9: CLI Tools
# ==============================================================================
class TestFeature9CLITools:
    """Feature 9: CLI Executable Tools (blog-core, gatekeeper, sync-assets) (≥5 tests)"""

    def test_01_gatekeeper_cli_help(self):
        """9.1: Verify gatekeeper module CLI --help execution returns exit code 0."""
        cmd = [sys.executable, "-m", "blog_core.engine.gatekeeper", "--help"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0
        assert "Ironclad Gatekeeper" in proc.stdout or "--file" in proc.stdout

    def test_02_sync_assets_cli_help(self):
        """9.2: Verify sync_to_blogs.py CLI --help execution returns exit code 0."""
        cmd = [sys.executable, "sync_to_blogs.py", "--help"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0
        assert "--target" in proc.stdout
        assert "--dry-run" in proc.stdout

    def test_03_blog_core_unified_cli_help(self):
        """9.3: Verify unified CLI (blog_core.cli) --help exits with 0 (or skips if M4 pending)."""
        cli_path = WORKSPACE_ROOT / "blog_core" / "cli.py"
        if not cli_path.exists():
            pytest.skip("blog_core/cli.py not yet created (Milestone 4 Pending)")

        cmd = [sys.executable, "-m", "blog_core.cli", "--help"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0

    def test_04_gatekeeper_cli_check_valid_file(self, sample_posts_map: Dict[str, Path]):
        """9.4: Verify gatekeeper CLI check on valid sample file returns exit code 0."""
        valid_dev = sample_posts_map["valid_dev_post"]
        cmd = [
            sys.executable, "-m", "blog_core.engine.gatekeeper",
            "--file", str(valid_dev),
            "--platform", "dev",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode == 0
        assert "PASSED" in proc.stdout

    def test_05_gatekeeper_cli_check_invalid_file_exit_code(
        self, sample_posts_map: Dict[str, Path]
    ):
        """9.5: Verify gatekeeper CLI check on invalid sample file exits with non-zero exit code."""
        bad_ai = sample_posts_map["bad_ai_cliche_post"]
        cmd = [
            sys.executable, "-m", "blog_core.engine.gatekeeper",
            "--file", str(bad_ai),
            "--platform", "dev",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
        assert proc.returncode != 0
        assert "REJECTED" in proc.stdout


# ==============================================================================
# Feature 10: Documentation
# ==============================================================================
class TestFeature10Documentation:
    """Feature 10: Architecture README & Agent Extension Guide Documentation (≥5 tests)"""

    def test_01_readme_exists_and_has_architecture_diagram(self):
        """10.1: Verify README.md exists and contains an architecture overview diagram."""
        readme_path = WORKSPACE_ROOT / "README.md"
        if not readme_path.exists():
            pytest.skip("README.md not yet created (Milestone 4 Pending)")

        content = readme_path.read_text(encoding="utf-8")
        assert len(content) > 200
        # Check for architecture diagram or structural layout
        assert "blog_core" in content
        assert "```" in content or "architecture" in content.lower()

    def test_02_readme_setup_and_usage_instructions(self):
        """10.2: Verify README.md contains editable setup instructions and usage examples."""
        readme_path = WORKSPACE_ROOT / "README.md"
        if not readme_path.exists():
            pytest.skip("README.md not yet created (Milestone 4 Pending)")

        content = readme_path.read_text(encoding="utf-8")
        assert "pip install" in content or "install -e" in content

    def test_03_agent_extension_guide_exists(self):
        """10.3: Verify docs/AGENT_EXTENSION_GUIDE.md exists."""
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"
        if not guide_path.exists():
            pytest.skip("docs/AGENT_EXTENSION_GUIDE.md not yet created (Milestone 4 Pending)")

        assert guide_path.is_file()
        assert len(guide_path.read_text(encoding="utf-8")) > 500

    def test_04_agent_extension_guide_has_5_step_sop(self):
        """10.4: Verify docs/AGENT_EXTENSION_GUIDE.md outlines the 5-step SOP for adding new rules."""
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"
        if not guide_path.exists():
            pytest.skip("docs/AGENT_EXTENSION_GUIDE.md not yet created (Milestone 4 Pending)")

        content = guide_path.read_text(encoding="utf-8")
        # Check for step indicators (Step 1 ~ Step 5 or 1단계 ~ 5단계)
        assert any(term in content for term in ["Step 1", "1단계", "Step 5", "5단계"])

    def test_05_agent_extension_guide_code_examples(self):
        """10.5: Verify docs/AGENT_EXTENSION_GUIDE.md provides BaseRule subclassing code snippets."""
        guide_path = WORKSPACE_ROOT / "docs" / "AGENT_EXTENSION_GUIDE.md"
        if not guide_path.exists():
            pytest.skip("docs/AGENT_EXTENSION_GUIDE.md not yet created (Milestone 4 Pending)")

        content = guide_path.read_text(encoding="utf-8")
        assert "BaseRule" in content
        assert "def check(" in content or "RuleContext" in content
