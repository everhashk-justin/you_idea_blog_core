# -*- coding: utf-8 -*-
"""
tests.test_auto_discovery - Unit tests verifying dynamic plugin auto-discovery without touching engine code
"""

import sys
import unittest
import tempfile
import shutil
from pathlib import Path

from blog_core.engine.base_rule import BaseRule
from blog_core.engine.context import RuleContext, create_context
from blog_core.engine.models import Violation
from blog_core.engine.registry import RuleRegistry
from blog_core.engine.gatekeeper import IroncladGatekeeper


class TestAutoDiscovery(unittest.TestCase):
    """엔진 수정 없는 동적 플러그인 규칙 자동 탐색(Auto-discovery) 검증"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="blog_core_autodiscover_"))
        self.registry = RuleRegistry()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_rules_discovered(self):
        """기본 common 및 platforms 하위 규칙들이 정상적으로 자동 탐색되는지 검증"""
        self.registry.discover()
        rules = self.registry.rules
        self.assertGreater(len(rules), 10, "Should discover more than 10 default rules")
        
        # 주요 규칙 식별자 존재 검증
        self.assertIn("G1_REQ_FRONTMATTER", rules)
        self.assertIn("G2_AI_CLICHE", rules)
        self.assertIn("G3_FORCED_DRAMA", rules)
        self.assertIn("G7_AWS_KEY_LEAK", rules)
        self.assertIn("G8_FIN_CAPITAL_MARKETS", rules)
        self.assertIn("G6_DEV_CATEGORY_MISMATCH", rules)
        self.assertIn("G6_NAVER_MEDICAL_LAW", rules)

    def test_dynamic_package_auto_discovery(self):
        """새로운 디렉터리에 플러그인 규칙 모듈 파일 생성 시 discover()로 자동 감지되는지 검증"""
        # 임시 패키지 생성
        pkg_dir = self.temp_dir / "custom_plugins"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

        # 플러그인 룰 모듈 작성
        plugin_code = """# -*- coding: utf-8 -*-
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext
from typing import List

class DynamicForbiddenWordRule(BaseRule):
    rule_id = "G9_DYNAMIC_TEST_RULE"
    gate_id = "GATE_9"
    gate_name = "동적 테스트 게이트"
    description = "동적으로 생성된 플러그인 규칙"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations = []
        if "forbidden_dynamic_keyword" in ctx.content:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=1,
                snippet="forbidden_dynamic_keyword",
                message="동적 플러그인 금지 키워드 탐지",
                fix_hint="키워드를 삭제하십시오."
            ))
        return violations
"""
        (pkg_dir / "custom_rule.py").write_text(plugin_code, encoding="utf-8")

        # sys.path에 임시 패키지 경로 추가 후 discover 수행
        sys.path.insert(0, str(self.temp_dir))
        try:
            custom_registry = RuleRegistry()
            custom_registry.discover(package_names=["custom_plugins"])

            # 엔진 수정 없이 동적으로 발견되었는지 검증
            self.assertIn("G9_DYNAMIC_TEST_RULE", custom_registry.rules)
            discovered_rule = custom_registry.rules["G9_DYNAMIC_TEST_RULE"]
            self.assertEqual(discovered_rule.gate_id, "GATE_9")

            # Gatekeeper와 연동하여 실제 검사 실행 및 위반 탐지 확인
            gatekeeper = IroncladGatekeeper(registry=custom_registry)

            # 1) 금지 키워드가 없는 글 검증 -> PASS
            clean_file = self.temp_dir / "clean.md"
            clean_file.write_text("Hello clean dynamic content", encoding="utf-8")
            rep1 = gatekeeper.verify(str(clean_file), platform_override="dev")
            self.assertTrue(rep1.is_passed)

            # 2) 금지 키워드가 포함된 글 검증 -> REJECT with G9_DYNAMIC_TEST_RULE
            bad_file = self.temp_dir / "bad.md"
            bad_file.write_text("This contains forbidden_dynamic_keyword here", encoding="utf-8")
            rep2 = gatekeeper.verify(str(bad_file), platform_override="dev")
            self.assertFalse(rep2.is_passed)
            self.assertTrue(any(v.rule_id == "G9_DYNAMIC_TEST_RULE" for v in rep2.violations))
        finally:
            if str(self.temp_dir) in sys.path:
                sys.path.remove(str(self.temp_dir))

    def test_direct_class_registration(self):
        """register() 메서드를 통한 개별 룰 클래스 또는 인스턴스 직접 등록 검증"""
        registry = RuleRegistry()

        class DirectRule(BaseRule):
            rule_id = "CUSTOM_DIRECT_RULE"
            gate_id = "GATE_1"
            gate_name = "직접 등록 테스트"
            platforms = ["dev"]

            def check(self, ctx: RuleContext):
                return []

        registry.register(DirectRule)
        self.assertIn("CUSTOM_DIRECT_RULE", registry.rules)
        # auto_discover=False로 격리 상태에서 직접 등록된 규칙만 필터링되는지 검증
        self.assertEqual(len(registry.get_rules(platform="dev", auto_discover=False)), 1)
        self.assertEqual(len(registry.get_rules(platform="naver", auto_discover=False)), 0)

    def test_invalid_rule_registration_raises_error(self):
        """rule_id가 비어있는 규칙 등록 시 ValueError 발생 검증"""
        registry = RuleRegistry()

        class InvalidRule(BaseRule):
            rule_id = ""
            gate_id = "GATE_1"
            gate_name = "무효 규칙"

            def check(self, ctx):
                return []

        with self.assertRaises(ValueError):
            registry.register(InvalidRule)


if __name__ == "__main__":
    unittest.main()
