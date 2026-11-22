# -*- coding: utf-8 -*-
"""
tests.test_gate_10_11_12_fact_check - Unit tests covering Gate 10, 11, 12 in blog_core
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from blog_core.engine.gatekeeper import IroncladGatekeeper


class TestGate10_11_12(unittest.TestCase):

    def setUp(self):
        self.gatekeeper = IroncladGatekeeper()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="blog_core_g101112_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp(self, filename: str, content: str) -> Path:
        p = self.temp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_gate_10_missing_sources_rejected(self):
        md = """---
title: "리눅스 네트워크 분석"
category: "컴퓨터 과학 핵심 기초"
tags: ["linux"]
visibility: "public"
verification_date: "2026-11-22"
---
# 리눅스 네트워크
본문 내용입니다. 시스템 안정성을 분석합니다.
[출처: https://docs.kernel.org]
""" * 10
        p = self._write_temp("test_g10_no_sources.md", md)
        rep = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G10_MISSING_FM_SOURCES" for v in rep.violations))

    def test_gate_10_missing_verification_date_rejected(self):
        md = """---
title: "리눅스 네트워크 분석"
category: "컴퓨터 과학 핵심 기초"
tags: ["linux"]
visibility: "public"
fact_check_sources: ["https://docs.kernel.org"]
---
# 리눅스 네트워크
본문 내용입니다. 시스템 안정성을 분석합니다.
[출처: https://docs.kernel.org]
""" * 10
        p = self._write_temp("test_g10_no_date.md", md)
        rep = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G10_MISSING_FM_VERIFICATION_DATE" for v in rep.violations))

    def test_gate_11_theory_welfare_and_tech_integrity(self):
        # 1. 2026 중위소득 왜곡
        md_welfare = """---
title: "복지 지원금 분석"
category: "컴퓨터 과학 핵심 기초"
tags: ["welfare"]
visibility: "public"
fact_check_sources: ["https://www.bokjiro.go.kr"]
verification_date: "2026-11-22"
---
# 복지 분석
2026년 기준 중위소득은 540만 원으로 동결되었습니다.
[출처: 보건복지부]
""" * 10
        p1 = self._write_temp("test_g11_welfare.md", md_welfare)
        rep1 = self.gatekeeper.verify(str(p1), platform_override="tistory")
        self.assertFalse(rep1.is_passed)
        self.assertTrue(any(v.rule_id == "G11_WELFARE_OUTDATED_MEDIAN_INCOME" for v in rep1.violations))

        # 2. tcp_tw_recycle 제거 파라미터
        md_tech = """---
title: "커널 튜닝 가이드"
category: "컴퓨터 과학 핵심 기초"
tags: ["kernel"]
visibility: "public"
fact_check_sources: ["https://docs.kernel.org"]
verification_date: "2026-11-22"
---
# 커널 튜닝
net.ipv4.tcp_tw_recycle = 1 설정을 통해 TIME_WAIT 소켓을 빠르게 재활용합니다.
[출처: https://docs.kernel.org]
""" * 10
        p2 = self._write_temp("test_g11_tech.md", md_tech)
        rep2 = self.gatekeeper.verify(str(p2), platform_override="tistory")
        self.assertFalse(rep2.is_passed)
        self.assertTrue(any(v.rule_id == "G11_TECH_REMOVED_SYSCTL_TW_RECYCLE" for v in rep2.violations))

    def test_gate_12_stale_brands_and_temporal(self):
        # 1. ARIRANG 구형 브랜드
        md_arirang = """---
title: "ETF 분석"
category: "컴퓨터 과학 핵심 기초"
tags: ["etf"]
visibility: "public"
fact_check_sources: ["https://docs.kernel.org"]
verification_date: "2026-11-22"
---
# ETF 분석
ARIRANG 고배당주 ETF 상품을 매수합니다.
[출처: 한국거래소]
""" * 10
        p3 = self._write_temp("test_g12_arirang.md", md_arirang)
        rep3 = self.gatekeeper.verify(str(p3), platform_override="tistory")
        self.assertFalse(rep3.is_passed)
        self.assertTrue(any(v.rule_id == "G12_ANTI_STALE_AND_HALLUCINATION" for v in rep3.violations))

    def test_fully_compliant_article_passes(self):
        md_clean = """---
title: "[2026년 11월] 리눅스 커널 패킷 처리 아키텍처"
category: "컴퓨터 과학 핵심 기초"
tags: ["linux", "kernel"]
visibility: "public"
fact_check_sources: ["https://docs.kernel.org", "RFC 9110"]
verification_date: "2026-11-22"
---
# 리눅스 커널 패킷 처리 아키텍처

2026년 11월 기준 고성능 분산 인프라에서 대규모 네트워크 패킷이 인그레스될 때 리눅스 커널의 인터럽트 처리 메커니즘을 상세히 분석합니다.

## 1. Top-Half 및 Bottom-Half 구조
네트워크 인터페이스 카드로 패킷이 수신되면 하드웨어 인터럽트가 발생하여 커널 인터럽트 핸들러를 선점합니다.
리눅스 커널은 NAPI 인터페이스와 ksoftirqd를 통해 비동기 처리를 수행하여 CPU 오버헤드를 줄입니다.

## 2. NAPI와 RPS 부하 분산
단일 CPU 코어의 점유율이 급증하는 현상을 방지하기 위해 RPS를 활성화하여 패킷 해시 기반 분산을 구현합니다.

## 3. 프로덕션 점검 체크리스트
엔지니어는 mpstat과 proc softirqs 카운터를 실시간 모니터링하여 병목을 선제 차단해야 합니다.

---

> 📌 [출처: Linux Kernel Documentation (https://docs.kernel.org) 및 RFC 9110 표준 사양서]
""" * 5
        p4 = self._write_temp("test_clean_compliant.md", md_clean)
        rep4 = self.gatekeeper.verify(str(p4), platform_override="tistory")
        self.assertTrue(rep4.is_passed, f"Compliant article should pass, violations: {rep4.violations}")
