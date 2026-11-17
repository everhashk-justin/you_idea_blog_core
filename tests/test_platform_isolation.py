# -*- coding: utf-8 -*-
"""
tests.test_platform_isolation - Unit tests verifying strict platform isolation and whitelist filtering
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from blog_core.engine.registry import RuleRegistry, default_registry
from blog_core.engine.gatekeeper import IroncladGatekeeper


class TestPlatformIsolation(unittest.TestCase):
    """플랫폼별 규칙 격리(Platform Isolation) 및 화이트리스트 필터링 엄격 검증"""

    def setUp(self):
        self.registry = default_registry
        self.registry.discover()
        self.gatekeeper = IroncladGatekeeper(registry=self.registry)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="blog_core_isolation_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp(self, filename: str, content: str) -> Path:
        p = self.temp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_dev_platform_rules_whitelist(self):
        """dev 플랫폼 전용 룰이 타 플랫폼 룰 목록에 포함되지 않음을 검증"""
        dev_rules = self.registry.get_rules(platform="dev")
        dev_rule_ids = {r.rule_id for r in dev_rules}

        # dev 플랫폼 전용 룰 포함 확인
        self.assertIn("G6_DEV_CATEGORY_MISMATCH", dev_rule_ids)
        self.assertIn("G4_DEV_ENGINEERING_ARTIFACTS", dev_rule_ids)

        # 타 플랫폼 전용 룰 배제 확인
        self.assertNotIn("G6_NAVER_MEDICAL_LAW", dev_rule_ids)
        self.assertNotIn("G6_NAVER_MISSING_DISCLAIMER", dev_rule_ids)
        self.assertNotIn("G6_NAVER_INLINE_IMAGE_FORBIDDEN", dev_rule_ids)
        self.assertNotIn("G6_NAVER_MISSING_HASHTAGS", dev_rule_ids)
        self.assertNotIn("G6_TISTORY_CATEGORY_MISMATCH", dev_rule_ids)
        self.assertNotIn("G1_TISTORY_REQ_FRONTMATTER", dev_rule_ids)
        self.assertNotIn("G8_GLOBAL_MISSING_DISCLAIMER", dev_rule_ids)
        self.assertNotIn("G8_FIN_MISSING_DISCLAIMER", dev_rule_ids)
        self.assertNotIn("G1_GEAR_REQ_FRONTMATTER", dev_rule_ids)

    def test_naver_platform_rules_whitelist(self):
        """naver 플랫폼 전용 룰이 타 플랫폼 룰 목록에 포함되지 않음을 검증"""
        naver_rules = self.registry.get_rules(platform="naver")
        naver_rule_ids = {r.rule_id for r in naver_rules}

        # naver 플랫폼 전용 룰 포함 확인
        self.assertIn("G6_NAVER_MEDICAL_LAW", naver_rule_ids)
        self.assertIn("G6_NAVER_MISSING_DISCLAIMER", naver_rule_ids)
        self.assertIn("G6_NAVER_INLINE_IMAGE_FORBIDDEN", naver_rule_ids)
        self.assertIn("G6_NAVER_MISSING_HASHTAGS", naver_rule_ids)

        # dev 및 타 플랫폼 전용 룰 배제 확인
        self.assertNotIn("G6_DEV_CATEGORY_MISMATCH", naver_rule_ids)
        self.assertNotIn("G4_DEV_ENGINEERING_ARTIFACTS", naver_rule_ids)
        self.assertNotIn("G6_TISTORY_CATEGORY_MISMATCH", naver_rule_ids)
        self.assertNotIn("G1_TISTORY_REQ_FRONTMATTER", naver_rule_ids)
        self.assertNotIn("G8_GLOBAL_MISSING_DISCLAIMER", naver_rule_ids)
        self.assertNotIn("G8_FIN_MISSING_DISCLAIMER", naver_rule_ids)

    def test_tistory_platform_rules_whitelist(self):
        """tistory 플랫폼 전용 룰이 타 플랫폼 룰 목록에 포함되지 않음을 검증"""
        tistory_rules = self.registry.get_rules(platform="tistory")
        tistory_rule_ids = {r.rule_id for r in tistory_rules}

        # tistory 전용 룰 포함 확인
        self.assertIn("G6_TISTORY_CATEGORY_MISMATCH", tistory_rule_ids)
        self.assertIn("G1_TISTORY_REQ_FRONTMATTER", tistory_rule_ids)

        # dev 및 naver 전용 룰 배제 확인
        self.assertNotIn("G6_DEV_CATEGORY_MISMATCH", tistory_rule_ids)
        self.assertNotIn("G4_DEV_ENGINEERING_ARTIFACTS", tistory_rule_ids)
        self.assertNotIn("G6_NAVER_INLINE_IMAGE_FORBIDDEN", tistory_rule_ids)
        self.assertNotIn("G6_NAVER_MISSING_HASHTAGS", tistory_rule_ids)
        self.assertNotIn("G8_GLOBAL_MISSING_DISCLAIMER", tistory_rule_ids)
        self.assertNotIn("G8_FIN_MISSING_DISCLAIMER", tistory_rule_ids)

    def test_universal_rules_applied_to_all_platforms(self):
        """공통 규칙(platforms=None)은 모든 플랫폼에 예외 없이 공통 적용됨을 검증"""
        for plat in ["dev", "naver", "tistory", "stock", "markets", "gear"]:
            rules = self.registry.get_rules(platform=plat)
            rule_ids = {r.rule_id for r in rules}
            # 공통 규칙 11개 영역 확인
            self.assertIn("G1_REQ_FRONTMATTER", rule_ids, f"G1_REQ_FRONTMATTER must be in {plat}")
            self.assertIn("G1_UNCLOSED_CODEBLOCK", rule_ids, f"G1_UNCLOSED_CODEBLOCK must be in {plat}")
            self.assertIn("G2_AI_CLICHE", rule_ids, f"G2_AI_CLICHE must be in {plat}")
            self.assertIn("G3_FORCED_DRAMA", rule_ids, f"G3_FORCED_DRAMA must be in {plat}")
            self.assertIn("G7_AWS_KEY_LEAK", rule_ids, f"G7_AWS_KEY_LEAK must be in {plat}")
            self.assertIn("G8_FIN_CAPITAL_MARKETS", rule_ids, f"G8_FIN_CAPITAL_MARKETS must be in {plat}")
            self.assertIn("G8_MED_MEDICAL_LAW", rule_ids, f"G8_MED_MEDICAL_LAW must be in {plat}")
            self.assertIn("G8_FTC_AFFILIATE", rule_ids, f"G8_FTC_AFFILIATE must be in {plat}")
            self.assertIn("G8_KOGL_MISSING_ATTRIBUTION", rule_ids, f"G8_KOGL_MISSING_ATTRIBUTION must be in {plat}")
            self.assertIn("G8_GLOBAL_SEC_FINANCE", rule_ids, f"G8_GLOBAL_SEC_FINANCE must be in {plat}")

    def test_runtime_cross_platform_false_positive_prevention(self):
        """실제 파일 검증 시 타 플랫폼 룰의 오탐이 100% 방지되는지 런타임 검증"""
        # 1. 네이버에서 금지되는 인라인 이미지 (![...])가 dev 글에 있을 때 dev 검증에서는 위반이 발생하지 않아야 함
        dev_post_with_image = """---
title: "Kubernetes Network Troubleshooting"
category: "Cloud & DevOps"
tags: "k8s, networking"
---
# Kubernetes Debugging Guide

Here is an architectural diagram:
![Architecture Diagram](https://example.com/arch.png)

Now we analyze the actual production issue without any fake emergency drama.
The ingress gateway experienced intermittent connection resets during high load.
"""
        p1 = self._write_temp("dev_post.md", dev_post_with_image)
        rep1 = self.gatekeeper.verify(str(p1), platform_override="dev")
        # G6_NAVER_INLINE_IMAGE_FORBIDDEN 이 절대 검출되지 않아야 함
        self.assertFalse(
            any(v.rule_id == "G6_NAVER_INLINE_IMAGE_FORBIDDEN" for v in rep1.violations),
            "Dev verification must not execute Naver's inline image rule"
        )

        # 2. dev 카테고리가 아닌 일반 카테고리가 네이버 글에 있을 때 G6_DEV_CATEGORY_MISMATCH 가 발생하지 않아야 함
        naver_post = """---
title: "정부 지원금 신청 안내"
category: "정부 정책 / 복지 지원금"
tags: "지원금, 정책"
---
# 정부 지원금 신청 안내

[사진 1: 안내문](file:///D:/images/guide.png)

본 포스팅은 공공누리 제1유형 출처표시에 따라 작성되었습니다.
출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)

#정책 #지원금 #복지 #청년도약계좌
"""
        p2 = self._write_temp("naver_post.md", naver_post)
        rep2 = self.gatekeeper.verify(str(p2), platform_override="naver")
        self.assertFalse(
            any(v.rule_id == "G6_DEV_CATEGORY_MISMATCH" for v in rep2.violations),
            "Naver verification must not execute Dev's category mismatch rule"
        )


if __name__ == "__main__":
    unittest.main()
