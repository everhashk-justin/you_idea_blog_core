# -*- coding: utf-8 -*-
"""
tests.test_12_self_tests - Unit tests covering the complete 12 legacy self-test scenarios
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from blog_core.engine.gatekeeper import IroncladGatekeeper, split_frontmatter_and_body, parse_frontmatter
from blog_core.engine.models import Severity


class TestTwelveSelfTests(unittest.TestCase):
    """Legacy ironclad_gatekeeper.py의 12대 셀프 테스트 시나리오 단위 테스트 스위트"""

    def setUp(self):
        self.gatekeeper = IroncladGatekeeper()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="blog_core_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp(self, filename: str, content: str) -> Path:
        p = self.temp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_case_01_en_ai_cliche(self):
        """Case 1: 영문 AI 클리셰 포함 케이스 (delve, immune, diagnostic breakdown) -> G2_AI_CLICHE REJECT"""
        bad_en = """---
title: "Test AI Post"
category: "Cloud & DevOps"
tags: "k8s, dev"
---
In the modern cloud landscape, we must delve into kubernetes issues.
By doing so, the cluster becomes immune to failures.
Here is the exact diagnostic breakdown.
"""
        p = self._write_temp("_test_bad_en.md", bad_en)
        report = self.gatekeeper.verify(str(p), platform_override="dev")
        self.assertFalse(report.is_passed, "Case 1: Bad EN AI clichés should be REJECTED")
        self.assertTrue(
            any(v.rule_id == "G2_AI_CLICHE" for v in report.violations),
            "Case 1: Should detect AI cliché"
        )

    def test_case_02_ko_forced_drama(self):
        """Case 2: 국문 억지 스토리 포함 케이스 (새벽 3시 40분, 식은땀, 패닉) -> G3_FORCED_DRAMA REJECT"""
        bad_drama_ko = """---
title: "새벽 장애 일지"
category: "백엔드 & 서버 아키텍처"
tags: "spring"
visibility: "public"
---
새벽 3시 40분, 비상 호출이 울렸다.
등줄기에 식은땀이 흘렀고 머릿속이 하얘졌다.
패닉에 빠진 채로 로그를 보았다.
"""
        p = self._write_temp("_test_bad_drama.md", bad_drama_ko)
        report = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(report.is_passed, "Case 2: Forced drama should be REJECTED")
        self.assertTrue(
            any(v.rule_id == "G3_FORCED_DRAMA" for v in report.violations),
            "Case 2: Should detect forced drama"
        )

    def test_case_03_naver_medical_law(self):
        """Case 3: 네이버 건강 블로그 의료법 위반 단어 (완치, 치료, 특효약) -> G6_NAVER_MEDICAL_LAW REJECT"""
        bad_health_naver = """---
title: "마그네슘 복용법"
category: "건강"
tags: "마그네슘"
---
이 영양제는 불면증 완치와 고혈압 치료에 특효약입니다.
"""
        p = self._write_temp("_test_bad_health.md", bad_health_naver)
        report = self.gatekeeper.verify(str(p), platform_override="naver")
        self.assertFalse(report.is_passed, "Case 3: Medical claim in health blog should be REJECTED")
        self.assertTrue(
            any(v.rule_id == "G6_NAVER_MEDICAL_LAW" for v in report.violations),
            "Case 3: Medical law violation caught"
        )

    def test_case_04_unclosed_code_block(self):
        """Case 4: 코드 블록 백틱 홀수 (닫히지 않은 ```) -> G1_UNCLOSED_CODEBLOCK REJECT"""
        bad_codeblock = """---
title: "Unclosed Code"
category: "Systems & Networking"
tags: "linux"
---
```bash
echo "Hello"
"""
        p = self._write_temp("_test_bad_code.md", bad_codeblock)
        report = self.gatekeeper.verify(str(p), platform_override="dev")
        self.assertFalse(report.is_passed, "Case 4: Unclosed code block should be REJECTED")
        self.assertTrue(
            any(v.rule_id == "G1_UNCLOSED_CODEBLOCK" for v in report.violations),
            "Case 4: Unclosed code caught"
        )

    def test_case_05_security_key_leak(self):
        """Case 5: 보안 시크릿 누출 (AWS Key) -> GATE_7 REJECT"""
        bad_secret = """---
title: "AWS Credentials Guide"
category: "Cloud & DevOps"
tags: "aws"
---
AWS_KEY = "AKIA1234567890ABCDEF"
"""
        p = self._write_temp("_test_bad_secret.md", bad_secret)
        report = self.gatekeeper.verify(str(p), platform_override="dev")
        self.assertFalse(report.is_passed, "Case 5: Security secret leak should be REJECTED")
        self.assertTrue(
            any(v.gate_id == "GATE_7" for v in report.violations),
            "Case 5: Gate 7 secret leak caught"
        )

    def test_case_06_capital_markets_and_consumer_protection(self):
        """Case 6: 자본시장법 & 금소법 위반 (원금보장, 확정수익, VIP 리딩방) -> G8_FIN_... REJECT"""
        bad_finance = """---
title: "특급 급등주 추천 및 확정 수익 비법"
category: "금융 & 재테크"
tags: "주식, 재테크"
---
이번에 발굴한 세력 매집주는 무조건 폭등하며 원금 보장과 함께 연 30% 확정 수익을 약속합니다. 투자의 최종 책임은 본인에게 있습니다.
VIP 리딩방에서만 제공하는 극비 정보주이므로 지금 당장 풀매수하세요.
"""
        p = self._write_temp("_test_bad_fin.md", bad_finance)
        report = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(report.is_passed, "Case 6: Capital Markets & Consumer Protection violations should be REJECTED")
        self.assertTrue(any("G8_FIN_" in v.rule_id for v in report.violations), "Case 6: Should detect Capital Markets & Consumer Protection violations")
        self.assertTrue(any(v.rule_id == "G8_FIN_PRINCIPAL_GUARANTEE" for v in report.violations), "Case 6: Should detect principal guarantee even with disclaimer on same line")
        self.assertTrue(any(v.rule_id == "G8_FIN_CONFIRMED_PROFIT" for v in report.violations), "Case 6: Should detect confirmed profit")

    def test_case_07_medical_law_and_health_functional_food(self):
        """Case 7: 의료법 & 건강기능식품법 위반 (천연치료제, 처방약 중단, 의사 사칭) -> G8_MED_... REJECT"""
        bad_medical = """---
title: "기적의 천연 치료제로 당뇨 잡는 법"
category: "건강"
tags: "당뇨, 영양제"
---
현직 의사로서 보증하건대, 이 성분은 인슐린 약 대신 복용할 수 있는 기적의 천연 치료제입니다. 본 제품은 질병 치료를 목적으로 하지 않으며 의약품이 아닙니다.
기존 병원 처방약을 끊고 이 건강기능식품만 섭취하면 체지방 100% 분해와 함께 완치됩니다.
"""
        p = self._write_temp("_test_bad_med.md", bad_medical)
        report = self.gatekeeper.verify(str(p), platform_override="naver")
        self.assertFalse(report.is_passed, "Case 7: Medical law & drug confusion claims should be REJECTED")
        self.assertTrue(any("G8_MED_" in v.rule_id for v in report.violations), "Case 7: Should detect medical law violations")
        self.assertTrue(any(v.rule_id == "G8_MED_NATURAL_MEDICINE" for v in report.violations), "Case 7: Should detect natural medicine claim")
        self.assertTrue(any(v.rule_id == "G8_MED_STOP_PRESCRIPTION" for v in report.violations), "Case 7: Should detect stopping prescription")
        self.assertTrue(any(v.rule_id == "G8_MED_IMPERSONATION_PROFESSIONAL" for v in report.violations), "Case 7: Should detect medical impersonation")

    def test_case_08_ftc_affiliate_and_covert_ad(self):
        """Case 8: 공정거래위원회 추천·보증 심사지침 위반 (제휴링크 + 내돈내산/광고 아닙니다 기만) -> G8_FTC_... REJECT"""
        bad_ftc = """---
title: "내돈내산 무선 마우스 솔직 후기"
category: "IT / 소프트웨어 리뷰"
tags: "마우스, IT리뷰"
---
# 가성비 최고 무선 마우스 사용기

제품 구매 링크: https://link.coupang.com/a/bCdEf1234
쿠팡 파트너스 추천 상품으로 적극 권장합니다.
직접 구매해서 3달간 써본 솔직한 내돈내산 후기입니다. 광고 아닙니다.
"""
        p = self._write_temp("_test_bad_ftc.md", bad_ftc)
        report = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(report.is_passed, "Case 8: Missing FTC disclosure and covert ad should be REJECTED")
        self.assertTrue(any(v.rule_id == "G8_FTC_MISSING_DISCLOSURE" for v in report.violations), "Case 8: Should detect missing FTC disclosure")
        self.assertTrue(any(v.rule_id == "G8_FTC_COVERT_MY_MONEY" for v in report.violations), "Case 8: Should detect deceptive covert marketing")

    def test_case_09_kogl_copyright_attribution(self):
        """Case 9: 공공누리(KOGL) 저작권 출처 표기 누락 (정부 지원금 글) -> G8_KOGL_MISSING_ATTRIBUTION REJECT"""
        bad_kogl = """---
title: "2026 청년도약계좌 지원 조건 및 신청 방법 총정리"
category: "정부 정책 / 복지 지원금"
tags: "청년도약계좌, 정부지원금"
---
# 2026 청년도약계좌 완벽 가이드

보건복지부와 서민금융진흥원에서 발표한 2026년 청년도약계좌 정부 지원금 정책 안내입니다.
정부 지원금 매칭 혜택과 비과세 혜택을 통해 5천만 원의 목돈을 마련할 수 있습니다.
신청 자격은 만 19세~34세 청년이며 총급여 7,500만 원 이하입니다.
"""
        p = self._write_temp("_test_bad_kogl.md", bad_kogl)
        report = self.gatekeeper.verify(str(p), platform_override="naver")
        self.assertFalse(report.is_passed, "Case 9: Missing KOGL attribution should be REJECTED")
        self.assertTrue(any(v.rule_id == "G8_KOGL_MISSING_ATTRIBUTION" for v in report.violations), "Case 9: Should detect missing KOGL attribution")

    def test_case_10_sec_global_finance_and_evasion(self):
        """Case 10: 영문 글로벌 금융 규제 위반 및 동일 라인 우회 시도 차단 -> G8_GLOBAL_... REJECT"""
        bad_sec = """---
title: "Guaranteed Profit Trading Strategy"
category: "Global Macro & Finance"
tags: "trading, stocks"
---
# S&P 500 High-Frequency Strategy

This quantitative model delivers a guaranteed return of 45% with risk-free profit.
Buy this stock now before market close today. It has a 100% win rate and cannot lose money.
"""
        p = self._write_temp("_test_bad_sec.md", bad_sec)
        report = self.gatekeeper.verify(str(p), platform_override="markets")
        self.assertFalse(report.is_passed, "Case 10: Global financial/SEC violations should be REJECTED")
        self.assertTrue(any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in report.violations), "Case 10: Should detect guaranteed returns")
        self.assertTrue(any(v.rule_id == "G8_GLOBAL_URGENT_BUY_CALL" for v in report.violations), "Case 10: Should detect direct buy command")
        self.assertTrue(any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in report.violations), "Case 10: Should detect missing global financial disclaimer")

        # 10-2: 동일 라인 면책문구 우회 시도 검증
        sec_evasion_text = "This quantitative system delivers a guaranteed profit of 45%. This is for informational purposes only and not financial advice."
        sec_evasion_v = self.gatekeeper.verify_gate_8_legal_compliance(
            file_path="test_sec_evasion.md",
            content=sec_evasion_text,
            body=sec_evasion_text,
            fm_data={"category": "Finance", "title": "Trading"},
            lines=[sec_evasion_text],
            platform="markets"
        )
        self.assertTrue(any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in sec_evasion_v), "Case 10-2: Guaranteed profit must be caught even with disclaimer on same line")

    def test_case_11_fully_compliant_content_across_domains(self):
        """Case 11: 법적 규정을 100% 준수한 정상 콘텐츠 4종 무결성 검증 (0 violations)"""
        # 11-1: KOGL 정책 공공 저작물 정상 포스트 (naver)
        compliant_policy = """---
title: "2026 청년 자산 형성 정책 분석 가이드"
category: "정부 정책 / 복지 지원금"
tags: "청년도약계좌, 정책금융"
---
# 2026 청년 자산 형성 지원 정책 분석

본 포스팅은 대한민국 정부의 청년 금융 지원 복지 정책 구조를 객관적으로 분석합니다.
소득 구간별 정부기여금 매칭과 우대 금리 요건을 꼼꼼히 확인하여 자산 형성 계획을 수립해야 합니다.

신청 전 서민금융진흥원 및 취급 시중은행의 공식 공고를 확인하시기 바랍니다.

---
출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)

※ 본 글은 금융 지원 정책 이해를 돕기 위한 객관적 정보 제공용이며, 특정 금융회사나 금융투자상품 가입을 권유하지 않습니다.
"""
        cp_fm_text, cp_body, _ = split_frontmatter_and_body(compliant_policy)
        cp_fm = parse_frontmatter(cp_fm_text)
        cp_v = self.gatekeeper.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_policy.md",
            content=compliant_policy,
            body=cp_body,
            fm_data=cp_fm,
            lines=compliant_policy.splitlines(),
            platform="naver"
        )
        self.assertEqual(len(cp_v), 0, f"Case 11-1 should have 0 Gate 8 legal violations, found: {cp_v}")

        # 11-2: 식약처 고시 건기식 표준 면책문구 포스트 (naver)
        compliant_health = """---
title: "마그네슘 흡수율 비교 분석"
category: "건강"
tags: "마그네슘"
---
# 마그네슘 형태별 생체이용률 과학

식약처 고시 기준에 따른 마그네슘 형태별 체내 흡수 메커니즘을 객관적으로 분석합니다.
킬레이트 마그네슘과 산화 마그네슘의 용해도 차이를 인체적용시험 데이터로 비교합니다.

---
※ 본 제품은 질병의 예방 및 치료를 위한 의약품이 아니며, 건강 증진을 위한 건강기능식품 정보입니다. 전문 의료인의 진단 및 처방을 대신할 수 없습니다.
"""
        ch_fm_text, ch_body, _ = split_frontmatter_and_body(compliant_health)
        ch_fm = parse_frontmatter(ch_fm_text)
        ch_v = self.gatekeeper.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_health.md",
            content=compliant_health,
            body=ch_body,
            fm_data=ch_fm,
            lines=compliant_health.splitlines(),
            platform="naver"
        )
        self.assertEqual(len(ch_v), 0, f"Case 11-2 should have 0 Gate 8 legal violations, found: {ch_v}")

        # 11-3: 글로벌 영문 제휴 링크 & FTC 면책고지 포스트 (dev)
        compliant_ftc_en = """---
title: "Top Developer Keyboards"
category: "Cloud & DevOps"
tags: "hardware, dev"
---
# Essential Hardware for Engineers

A detailed review of ergonomic mechanical keyboards for infrastructure engineers.
Product link: https://amzn.to/3xyz123

Disclosure: This post contains affiliate links. As an Amazon Associate I earn from qualifying purchases at no additional cost to you.
"""
        ce_fm_text, ce_body, _ = split_frontmatter_and_body(compliant_ftc_en)
        ce_fm = parse_frontmatter(ce_fm_text)
        ce_v = self.gatekeeper.verify_gate_8_legal_compliance(
            file_path="blogs/dev/_posts/test_compliant_ftc.md",
            content=compliant_ftc_en,
            body=ce_body,
            fm_data=ce_fm,
            lines=compliant_ftc_en.splitlines(),
            platform="dev"
        )
        self.assertEqual(len(ce_v), 0, f"Case 11-3 should have 0 Gate 8 legal violations, found: {ce_v}")

        # 11-4: 개발 블로그 Portfolio Dashboard 튜토리얼 (dev)
        compliant_dev_portfolio = """---
title: "Building a Portfolio Dashboard with FastAPI"
category: "Cloud & DevOps"
tags: "fastapi, python"
---
# Building a Portfolio Dashboard

In this engineering tutorial, we implement an asynchronous worker pipeline to aggregate user metrics with FastAPI and Redis.
We deploy the containerized cluster across multiple availability zones.
"""
        cd_fm_text, cd_body, _ = split_frontmatter_and_body(compliant_dev_portfolio)
        cd_fm = parse_frontmatter(cd_fm_text)
        cd_v = self.gatekeeper.verify_gate_8_legal_compliance(
            file_path="blogs/dev/_posts/test_portfolio.md",
            content=compliant_dev_portfolio,
            body=cd_body,
            fm_data=cd_fm,
            lines=compliant_dev_portfolio.splitlines(),
            platform="dev"
        )
        self.assertEqual(len(cd_v), 0, f"Case 11-4 should have 0 Gate 8 legal violations, found: {cd_v}")

    def test_case_12_katex_multiline_syntax_error(self):
        """Case 12: KaTeX 파싱 에러 유발 멀티라인 수식 블록 ($$ 내 줄바꿈에 \\ 누락) -> G1_KATEX_MULTILINE_SYNTAX REJECT"""
        bad_math_katex = """---
title: "수식 파싱 테스트"
category: "기어 공학"
tags: "gear, math"
---
# 전위 기어 수식 검증

수식 블록 내에서 줄바꿈이 잘못되어 파서가 터지는 케이스:

$$d_{a1} = m(z_1 + 2 + 2x_1 - 2k), \\quad d_{a2} = m(z_2 + 2 + 2x_2 - 2k)
d_{f1} = m(z_1 - 2.5 + 2x_1), \\quad d_{f2} = m(z_2 - 2.5 + 2x_2)$$

본문 텍스트가 계속 이어집니다. 공백 제외 1200자 이상 충족을 위해 긴 텍스트를 기술합니다.
우리는 기계공학 현장에서 전위 기어의 물림률과 치형 밸런싱을 엄밀하게 해석해야 합니다.
인볼류트 치형 곡선의 기초원과 피치원의 관계를 명확히 정립하고,
운전 압력각과 이끝원 지름, 이뿌리원 지름을 정확하게 계산하여 조립 간섭을 방지해야 합니다.
""" * 10
        p = self._write_temp("_test_bad_math.md", bad_math_katex)
        report = self.gatekeeper.verify(str(p), platform_override="tistory")
        self.assertFalse(report.is_passed, "Case 12: KaTeX multiline error without \\\\ should be REJECTED")
        self.assertTrue(
            any(v.rule_id == "G1_KATEX_MULTILINE_SYNTAX" for v in report.violations),
            "Case 12: Should detect G1_KATEX_MULTILINE_SYNTAX"
        )

    def test_run_self_tests_suite_pass(self):
        """내장 자가 무결성 검증 함수 run_self_tests()의 100% 통과 확인"""
        result = self.gatekeeper.run_self_tests()
        self.assertTrue(result, "run_self_tests() must return True")


if __name__ == "__main__":
    unittest.main()
