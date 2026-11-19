# -*- coding: utf-8 -*-
"""
blog_core.engine.gatekeeper - Ironclad Gatekeeper Facade and CLI Engine
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Fix Windows console UTF-8 encoding
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from blog_core.engine.models import Violation, GateReport, Severity, Color
from blog_core.engine.context import (
    RuleContext,
    split_frontmatter_and_body,
    parse_frontmatter,
    extract_code_blocks,
    create_context,
)
from blog_core.engine.registry import RuleRegistry, default_registry


class IroncladGatekeeper:
    """
    모든 블로그 콘텐츠의 무결성을 기계적으로 판정하는 마스터 검증 엔진 파사드(Facade).
    모듈러 플러그인 규칙 레지스트리(RuleRegistry)와 100% 하위 호환성을 제공합니다.
    """

    def __init__(
        self,
        platform: Optional[str] = None,
        strict_mode: bool = False,
        registry: Optional[RuleRegistry] = None
    ):
        self.platform = platform
        self.strict_mode = strict_mode
        self.registry = registry or default_registry

    def detect_platform(self, file_path: str, content: str = "") -> str:
        """파일 경로 및 본문 패턴으로 플랫폼 자동 감지."""
        norm_path = file_path.replace("\\", "/").lower()
        if "blogs/dev" in norm_path or "dev.ideaspot360" in norm_path:
            return "dev"
        if "stock_blog_global" in norm_path or "markets" in norm_path or "markets.ideaspot360" in norm_path:
            return "markets"
        if "stock" in norm_path or "stock.ideaspot360" in norm_path:
            return "stock"
        if "gear" in norm_path or "gear.ideaspot360" in norm_path:
            return "gear"
        if "naver" in norm_path or "solidlog" in norm_path or "tidynote" in norm_path or "infopiece" in norm_path:
            return "naver"
        # Frontmatter 언어 및 메타데이터 검사
        if "category:" in content:
            import re
            if re.search(r"^category:\s*(Cloud & DevOps|Database & Storage|Systems & Networking)", content, re.MULTILINE):
                return "dev"
        return "tistory"

    # 하위 호환성 헬퍼 메서드
    def split_frontmatter_and_body(self, content: str) -> Tuple[Optional[str], str, int]:
        return split_frontmatter_and_body(content)

    def parse_frontmatter(self, fm_text: Optional[str]) -> Dict[str, str]:
        return parse_frontmatter(fm_text)

    def extract_code_blocks(self, body: str) -> List[Tuple[str, str, int]]:
        return extract_code_blocks(body)

    def verify_gate_8_legal_compliance(
        self,
        file_path: str = "",
        content: str = "",
        body: str = "",
        fm_data: Optional[Dict[str, str]] = None,
        lines: Optional[List[str]] = None,
        platform: str = "tistory",
    ) -> List[Violation]:
        """
        레거시 셀프 테스트 및 외부 연동용 Gate 8 전용 검증 래퍼.
        등록된 GATE_8 규칙들을 화이트리스트에 맞춰 실행합니다.
        """
        if fm_data is None:
            fm_data = {}
        if lines is None:
            lines = content.splitlines()

        code_blocks = extract_code_blocks(body)
        ctx = RuleContext(
            file_path=file_path,
            content=content,
            lines=lines,
            platform=platform,
            fm_data=fm_data,
            body=body,
            body_start_line=1,
            code_blocks=code_blocks,
            strict_mode=self.strict_mode,
        )

        rules = self.registry.get_rules(platform=platform, gate_id="GATE_8")
        violations: List[Violation] = []
        for rule in rules:
            violations.extend(rule.check(ctx))
        return violations

    def verify(
        self,
        file_path: str,
        platform_override: Optional[str] = None,
        strict: Optional[bool] = None
    ) -> GateReport:
        """
        단일 마크다운 파일 검증 실행기.
        RuleRegistry에 등록된 공통 및 플랫폼 규칙들을 자동 탐색하여 실행.
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            return GateReport(
                file_path=file_path,
                platform="unknown",
                is_passed=False,
                score=0,
                reject_count=1,
                warning_count=0,
                violations=[Violation(
                    gate_id="GATE_0",
                    gate_name="파일 접근성",
                    rule_id="G0_FILE_NOT_FOUND",
                    severity=Severity.REJECT,
                    line_number=0,
                    snippet=file_path,
                    message="지정된 파일을 찾을 수 없습니다.",
                    fix_hint="파일 경로가 정확한지 확인하십시오."
                )]
            )

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        platform = platform_override or self.platform or self.detect_platform(file_path, content)
        effective_strict = self.strict_mode if strict is None else strict

        ctx = create_context(
            file_path=file_path,
            content=content,
            platform=platform,
            strict_mode=effective_strict
        )

        # 레지스트리에서 해당 플랫폼 화이트리스트에 일치하는 규칙 수집
        rules = self.registry.get_rules(platform=platform)

        violations: List[Violation] = []
        for rule in rules:
            rule_violations = rule.check(ctx)
            if rule_violations:
                violations.extend(rule_violations)

        reject_count = sum(1 for v in violations if v.severity == Severity.REJECT)
        warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)

        score = GateReport.calculate_score(reject_count, warning_count)
        is_passed = (reject_count == 0)

        return GateReport(
            file_path=file_path,
            platform=platform,
            is_passed=is_passed,
            score=score,
            reject_count=reject_count,
            warning_count=warning_count,
            violations=violations
        )

    def evaluate_file(
        self,
        file_path: str,
        platform_override: Optional[str] = None,
        strict: Optional[bool] = None
    ) -> GateReport:
        """단일 파일 검증 수행 (verify의 별칭, 01_you_idea_blog_core 표준 인터페이스)."""
        return self.verify(file_path, platform_override=platform_override, strict=strict)

    def run_self_tests(self) -> bool:
        """12개 내장 셀프 테스트 실행 (하위 호환성 별칭)."""
        return run_self_test(self)


# ==============================================================================
# 📢 리포트 출력 및 하드 블록(Hard Block) 실행 함수
# ==============================================================================
def print_gate_report(report: GateReport, show_hints: bool = True):
    """검증 결과를 터미널에 미려한 ANSI 박스로 출력."""
    status_color = Color.GREEN if report.is_passed else Color.RED
    status_text = "PASSED (발행 승인)" if report.is_passed else "REJECTED (발행 원천 차단)"

    print("\n" + "=" * 80)
    print(f"🛡️  {Color.BOLD}철벽 게이트 검증 보고서 (Ironclad Gatekeeper Report){Color.RESET}")
    print("=" * 80)
    print(f"📄 대상 파일: {Color.CYAN}{report.file_path}{Color.RESET}")
    print(f"🌐 타깃 플랫폼: {Color.YELLOW}{report.platform.upper()}{Color.RESET}")
    print(f"⚖️  최종 판정: {status_color}{Color.BOLD}[{status_text}]{Color.RESET}")
    print(f"📈 품질 점수: {Color.BOLD}{report.score}/100{Color.RESET} (치명적 결함: {Color.RED}{report.reject_count}건{Color.RESET}, 경고: {Color.YELLOW}{report.warning_count}건{Color.RESET})")
    print("-" * 80)

    if not report.violations:
        print(f"{Color.GREEN}✨ 축하합니다! 단 하나의 결함도 발견되지 않은 완전무결한 콘텐츠입니다.{Color.RESET}")
        print("=" * 80 + "\n")
        return

    for idx, v in enumerate(report.violations, start=1):
        sev_color = Color.RED if v.severity == Severity.REJECT else Color.YELLOW
        line_info = f"Line {v.line_number}" if v.line_number > 0 else "전체/글로벌"
        print(f"\n{sev_color}{Color.BOLD}[{v.severity}] #{idx} {v.gate_id} ({v.gate_name}) - {line_info}{Color.RESET}")
        print(f"  🔍 사유: {v.message}")
        if v.snippet:
            print(f"  📝 원문: {Color.WHITE}\"{v.snippet}\"{Color.RESET}")
        if show_hints and v.fix_hint:
            print(f"  💡 교정 팁: {Color.GREEN}{v.fix_hint}{Color.RESET}")

    print("\n" + "=" * 80)
    if not report.is_passed:
        print(f"{Color.BG_RED}{Color.WHITE}{Color.BOLD} ❌ HARD BLOCK: 품질 기준 미달로 인해 글 발행 파이프라인이 물리적으로 중단됩니다. {Color.RESET}")
        print(f"{Color.RED}위 REJECT 항목을 100% 해소한 후 다시 발행 명령을 실행하십시오.{Color.RESET}")
    else:
        print(f"{Color.GREEN}✅ 검증 통과: 발행 시스템으로 작업을 안전하게 인계합니다.{Color.RESET}")
    print("=" * 80 + "\n")


def verify_or_abort(
    file_path: str,
    platform: Optional[str] = None,
    strict: bool = False,
    show_hints: bool = True
) -> GateReport:
    """
    글 발행 시스템(create_post.py, publish_to_dev.py 등) 연동용 함수.
    검증 실패 시 즉각 sys.exit(1)을 호출하여 후속 발행 트랜잭션을 물리적으로 차단함.
    """
    gatekeeper = IroncladGatekeeper(strict_mode=strict)
    report = gatekeeper.verify(file_path, platform_override=platform)
    print_gate_report(report, show_hints=show_hints)

    if not report.is_passed:
        sys.exit(1)

    return report


# ==============================================================================
# 🧪 내장 자체 단위 테스트 스위트 (12 Self-Tests Suite)
# ==============================================================================
def run_self_test(gatekeeper: Optional[IroncladGatekeeper] = None) -> bool:
    """
    기존 12개 셀프 테스트 시나리오를 모듈러 엔진 상에서 100% 동일하게 검증.
    """
    print("\n🧪 [철벽 게이트 검증 시스템 내장 Self-Test 시작]")
    if gatekeeper is None:
        gatekeeper = IroncladGatekeeper()

    temp_dir = Path("scratch")
    temp_dir.mkdir(exist_ok=True)

    try:
        # Case 1: AI 클리셰 포함 케이스 (영문) -> REJECT 기대
        bad_en = """---
title: "Test AI Post"
category: "Cloud & DevOps"
tags: "k8s, dev"
---
In the modern cloud landscape, we must delve into kubernetes issues.
By doing so, the cluster becomes immune to failures.
Here is the exact diagnostic breakdown.
"""
        temp_bad_en = temp_dir / "_test_bad_en.md"
        temp_bad_en.write_text(bad_en, encoding="utf-8")

        report1 = gatekeeper.verify(str(temp_bad_en), platform_override="dev")
        assert not report1.is_passed, "Case 1: Bad EN AI clichés should be REJECTED"
        assert any(v.rule_id == "G2_AI_CLICHE" for v in report1.violations), "Case 1: Should detect AI cliché"
        print("  ✅ Test 1 Passed: Bad English AI Clichés caught successfully.")

        # Case 2: 억지 스토리 포함 케이스 (국문) -> REJECT 기대
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
        temp_bad_drama = temp_dir / "_test_bad_drama.md"
        temp_bad_drama.write_text(bad_drama_ko, encoding="utf-8")

        report2 = gatekeeper.verify(str(temp_bad_drama), platform_override="tistory")
        assert not report2.is_passed, "Case 2: Forced drama should be REJECTED"
        assert any(v.rule_id == "G3_FORCED_DRAMA" for v in report2.violations), "Case 2: Should detect forced drama"
        print("  ✅ Test 2 Passed: Forced Drama Story caught successfully.")

        # Case 3: 네이버 건강 블로그 의료법 위반 단어 -> REJECT 기대
        bad_health_naver = """---
title: "마그네슘 복용법"
category: "건강"
tags: "마그네슘"
---
이 영양제는 불면증 완치와 고혈압 치료에 특효약입니다.
"""
        temp_bad_health = temp_dir / "_test_bad_health.md"
        temp_bad_health.write_text(bad_health_naver, encoding="utf-8")

        report3 = gatekeeper.verify(str(temp_bad_health), platform_override="naver")
        assert not report3.is_passed, "Case 3: Medical claim in health blog should be REJECTED"
        assert any(v.rule_id == "G6_NAVER_MEDICAL_LAW" for v in report3.violations), "Case 3: Medical law violation caught"
        print("  ✅ Test 3 Passed: Naver Medical Law violation caught successfully.")

        # Case 4: 코드 블록 백틱 홀수 (닫히지 않은 코드) -> REJECT 기대
        bad_codeblock = """---
title: "Unclosed Code"
category: "Systems & Networking"
tags: "linux"
---
```bash
echo "Hello"
"""
        temp_bad_code = temp_dir / "_test_bad_code.md"
        temp_bad_code.write_text(bad_codeblock, encoding="utf-8")

        report4 = gatekeeper.verify(str(temp_bad_code), platform_override="dev")
        assert not report4.is_passed, "Case 4: Unclosed code block should be REJECTED"
        assert any(v.rule_id == "G1_UNCLOSED_CODEBLOCK" for v in report4.violations), "Case 4: Unclosed code caught"
        print("  ✅ Test 4 Passed: Unclosed Code Block caught successfully.")

        # Case 5: 보안 시크릿 누출 (AWS Key) -> REJECT 기대
        bad_secret = """---
title: "AWS Credentials Guide"
category: "Cloud & DevOps"
tags: "aws"
---
AWS_KEY = "AKIA1234567890ABCDEF"
"""
        temp_bad_secret = temp_dir / "_test_bad_secret.md"
        temp_bad_secret.write_text(bad_secret, encoding="utf-8")

        report5 = gatekeeper.verify(str(temp_bad_secret), platform_override="dev")
        assert not report5.is_passed, "Case 5: Security secret leak should be REJECTED"
        assert any(v.gate_id == "GATE_7" for v in report5.violations), "Case 5: Gate 7 secret leak caught"
        print("  ✅ Test 5 Passed: Security & Secrets leak caught successfully.")

        # Case 6: 자본시장법 & 금소법 위반 (원금보장, 확정수익, 리딩방) -> REJECT 기대
        bad_finance = """---
title: "특급 급등주 추천 및 확정 수익 비법"
category: "금융 & 재테크"
tags: "주식, 재테크"
---
이번에 발굴한 세력 매집주는 무조건 폭등하며 원금 보장과 함께 연 30% 확정 수익을 약속합니다. 투자의 최종 책임은 본인에게 있습니다.
VIP 리딩방에서만 제공하는 극비 정보주이므로 지금 당장 풀매수하세요.
"""
        temp_bad_fin = temp_dir / "_test_bad_fin.md"
        temp_bad_fin.write_text(bad_finance, encoding="utf-8")

        report6 = gatekeeper.verify(str(temp_bad_fin), platform_override="tistory")
        assert not report6.is_passed, "Case 6: Capital Markets & Consumer Protection violations should be REJECTED"
        assert any("G8_FIN_" in v.rule_id for v in report6.violations), "Case 6: Should detect Capital Markets & Consumer Protection violations"
        assert any(v.rule_id == "G8_FIN_PRINCIPAL_GUARANTEE" for v in report6.violations), "Case 6: Should detect principal guarantee even with disclaimer on same line"
        assert any(v.rule_id == "G8_FIN_CONFIRMED_PROFIT" for v in report6.violations), "Case 6: Should detect confirmed profit"
        print("  ✅ Test 6 Passed: Capital Markets & Financial Consumer Protection Law violations caught successfully.")

        # Case 7: 의료법 & 건강기능식품법 위반 (의약품 오인, 처방약 중단, 의료인 사칭) -> REJECT 기대
        bad_medical = """---
title: "기적의 천연 치료제로 당뇨 잡는 법"
category: "건강"
tags: "당뇨, 영양제"
---
현직 의사로서 보증하건대, 이 성분은 인슐린 약 대신 복용할 수 있는 기적의 천연 치료제입니다. 본 제품은 질병 치료를 목적으로 하지 않으며 의약품이 아닙니다.
기존 병원 처방약을 끊고 이 건강기능식품만 섭취하면 체지방 100% 분해와 함께 완치됩니다.
"""
        temp_bad_med = temp_dir / "_test_bad_med.md"
        temp_bad_med.write_text(bad_medical, encoding="utf-8")

        report7 = gatekeeper.verify(str(temp_bad_med), platform_override="naver")
        assert not report7.is_passed, "Case 7: Medical law & drug confusion claims should be REJECTED"
        assert any("G8_MED_" in v.rule_id for v in report7.violations), "Case 7: Should detect medical law violations"
        assert any(v.rule_id == "G8_MED_NATURAL_MEDICINE" for v in report7.violations), "Case 7: Should detect natural medicine claim"
        assert any(v.rule_id == "G8_MED_STOP_PRESCRIPTION" for v in report7.violations), "Case 7: Should detect stopping prescription"
        assert any(v.rule_id == "G8_MED_IMPERSONATION_PROFESSIONAL" for v in report7.violations), "Case 7: Should detect medical impersonation"
        print("  ✅ Test 7 Passed: Medical Law & Health Functional Food Law violations caught successfully.")

        # Case 8: 공정거래위원회 추천·보증 심사지침 위반 (제휴 링크 있으나 대가성 고지 누락 및 기만적 스텔스 마케팅) -> REJECT 기대
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
        temp_bad_ftc = temp_dir / "_test_bad_ftc.md"
        temp_bad_ftc.write_text(bad_ftc, encoding="utf-8")

        report8 = gatekeeper.verify(str(temp_bad_ftc), platform_override="tistory")
        assert not report8.is_passed, "Case 8: Missing FTC disclosure and covert ad should be REJECTED"
        assert any(v.rule_id == "G8_FTC_MISSING_DISCLOSURE" for v in report8.violations), "Case 8: Should detect missing FTC disclosure"
        assert any(v.rule_id == "G8_FTC_COVERT_MY_MONEY" for v in report8.violations), "Case 8: Should detect deceptive covert marketing"
        print("  ✅ Test 8 Passed: FTC Affiliate & Sponsored Advertising compliance caught successfully.")

        # Case 9: 공공누리(KOGL) 저작권 출처 표기 누락 (정부 지원금/정책 글에서 출처 미표기) -> REJECT 기대
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
        temp_bad_kogl = temp_dir / "_test_bad_kogl.md"
        temp_bad_kogl.write_text(bad_kogl, encoding="utf-8")

        report9 = gatekeeper.verify(str(temp_bad_kogl), platform_override="naver")
        assert not report9.is_passed, "Case 9: Missing KOGL attribution should be REJECTED"
        assert any(v.rule_id == "G8_KOGL_MISSING_ATTRIBUTION" for v in report9.violations), "Case 9: Should detect missing KOGL attribution"
        print("  ✅ Test 9 Passed: KOGL Public Copyright attribution requirement verified successfully.")

        # Case 10: 영문 글로벌 금융 규제 위반 (SEC Investment Advice & Guaranteed Return) -> REJECT 기대
        bad_sec = """---
title: "Guaranteed Profit Trading Strategy"
category: "Global Macro & Finance"
tags: "trading, stocks"
---
# S&P 500 High-Frequency Strategy

This quantitative model delivers a guaranteed return of 45% with risk-free profit.
Buy this stock now before market close today. It has a 100% win rate and cannot lose money.
"""
        temp_bad_sec = temp_dir / "_test_bad_sec.md"
        temp_bad_sec.write_text(bad_sec, encoding="utf-8")

        report10 = gatekeeper.verify(str(temp_bad_sec), platform_override="markets")
        assert not report10.is_passed, "Case 10: Global financial/SEC violations should be REJECTED"
        assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in report10.violations), "Case 10: Should detect guaranteed returns"
        assert any(v.rule_id == "G8_GLOBAL_URGENT_BUY_CALL" for v in report10.violations), "Case 10: Should detect direct buy command"
        assert any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in report10.violations), "Case 10: Should detect missing global financial disclaimer"

        # 동일 라인에 면책문구를 혼합 삽입한 우회 시도 차단 추가 검증
        sec_evasion_text = "This quantitative system delivers a guaranteed profit of 45%. This is for informational purposes only and not financial advice."
        sec_evasion_lines = [sec_evasion_text]
        sec_evasion_v = gatekeeper.verify_gate_8_legal_compliance(
            file_path="test_sec_evasion.md",
            content=sec_evasion_text,
            body=sec_evasion_text,
            fm_data={"category": "Finance", "title": "Trading"},
            lines=sec_evasion_lines,
            platform="markets"
        )
        assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in sec_evasion_v), "Case 10-2: Guaranteed profit must be caught even with disclaimer on same line"
        print("  ✅ Test 10 Passed: English SEC & Global Financial compliance violations caught successfully.")

        # Case 11: 법적 규정 100% 준수한 정상 콘텐츠 통과 검증 (Clean Compliant Post) -> PASS 기대
        # 1. KOGL 정책 공공 저작물 정상 포스트
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
        cp_v = gatekeeper.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_policy.md",
            content=compliant_policy,
            body=cp_body,
            fm_data=cp_fm,
            lines=compliant_policy.splitlines(),
            platform="naver"
        )
        assert len(cp_v) == 0, f"Case 11-1: Compliant policy post should have 0 Gate 8 legal violations, found: {cp_v}"

        # 2. 식약처 고시 건기식 표준 면책문구 포스트
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
        ch_v = gatekeeper.verify_gate_8_legal_compliance(
            file_path="posts/test_compliant_health.md",
            content=compliant_health,
            body=ch_body,
            fm_data=ch_fm,
            lines=compliant_health.splitlines(),
            platform="naver"
        )
        assert len(ch_v) == 0, f"Case 11-2: Compliant health post should have 0 Gate 8 legal violations, found: {ch_v}"

        # 3. 글로벌 영문 제휴 링크 & FTC 면책고지 준수 포스트
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
        ce_v = gatekeeper.verify_gate_8_legal_compliance(
            file_path="blogs/dev/_posts/test_compliant_ftc.md",
            content=compliant_ftc_en,
            body=ce_body,
            fm_data=ce_fm,
            lines=compliant_ftc_en.splitlines(),
            platform="dev"
        )
        assert len(ce_v) == 0, f"Case 11-3: Compliant English affiliate post should have 0 Gate 8 legal violations, found: {ce_v}"

        # 4. 개발 블로그의 Portfolio Dashboard 튜토리얼 (금융 글 오탐 방지 검증)
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
        cd_v = gatekeeper.verify_gate_8_legal_compliance(
            file_path="blogs/dev/_posts/test_portfolio.md",
            content=compliant_dev_portfolio,
            body=cd_body,
            fm_data=cd_fm,
            lines=compliant_dev_portfolio.splitlines(),
            platform="dev"
        )
        assert len(cd_v) == 0, f"Case 11-4: Dev coding tutorial with 'portfolio' should have 0 Gate 8 legal violations, found: {cd_v}"

        print("  ✅ Test 11 Passed: Fully compliant legal & regulatory content verified across all domains with 0 violations.")

        # Case 12: KaTeX 파싱 에러 유발 멀티라인 수식 블록 -> REJECT 기대
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
        temp_bad_math = temp_dir / "_test_bad_math.md"
        temp_bad_math.write_text(bad_math_katex, encoding="utf-8")
        report12 = gatekeeper.verify(str(temp_bad_math), platform_override="tistory")
        assert not report12.is_passed, "Case 12: KaTeX multiline error without \\\\ should be REJECTED"
        assert any(v.rule_id == "G1_KATEX_MULTILINE_SYNTAX" for v in report12.violations), "Case 12: Should detect G1_KATEX_MULTILINE_SYNTAX"
        print("  ✅ Test 12 Passed: KaTeX multiline parse-error syntax caught successfully.")

    finally:
        # 임시 파일 정리
        all_temp_files = [
            temp_bad_en, temp_bad_drama, temp_bad_health, temp_bad_code, temp_bad_secret,
            temp_bad_fin, temp_bad_med, temp_bad_ftc, temp_bad_kogl, temp_bad_sec, temp_bad_math
        ]
        for p in all_temp_files:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

    print(f"\n{Color.GREEN}{Color.BOLD}🎉 ALL 12 SELF-TESTS PASSED: 철벽 게이트 검증 엔진의 8대 품질, 마크다운/수식 무결성 및 법적 컴플라이언스 룰이 100% 정상 동작합니다!{Color.RESET}\n")
    return True


# ==============================================================================
# 💻 CLI 실행 진입점 (Command Line Interface)
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🏛️ 철벽 게이트 검증 시스템 CLI (Ironclad Gatekeeper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
[사용 예시]
  1. 단건 글 정밀 검증:
     python -m blog_core.engine.gatekeeper --file posts/70_trouble_example.md
  2. 개발 블로그 영문 글 검증:
     python -m blog_core.engine.gatekeeper --file blogs/dev/_posts/2026-11-23-example.md --platform dev
  3. 특정 디렉터리 내 전체 글 일괄 검사:
     python -m blog_core.engine.gatekeeper --dir posts/
  4. 내장 자체 무결성 단위 테스트:
     python -m blog_core.engine.gatekeeper --self-test
  5. JSON 결과 출력:
     python -m blog_core.engine.gatekeeper --file posts/70_trouble_example.md --json
        """
    )

    parser.add_argument("--file", "-f", help="검증할 마크다운 파일 경로")
    parser.add_argument("--dir", "-d", help="검증할 마크다운 디렉터리 경로 (내부 .md 일괄 검증)")
    parser.add_argument("--platform", "-p", choices=["auto", "dev", "tistory", "naver", "markets", "stock", "gear"], default="auto", help="타깃 플랫폼 (기본값: auto)")
    parser.add_argument("--strict", action="store_true", help="엄격 모드 (WARNING도 REJECT로 취급)")
    parser.add_argument("--self-test", action="store_true", help="내장 자체 단위 테스트 실행")
    parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
    parser.add_argument("--no-hints", action="store_true", help="교정 팁 출력 생략")

    args = parser.parse_args()

    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    gatekeeper = IroncladGatekeeper(strict_mode=args.strict)
    platform_override = None if args.platform == "auto" else args.platform

    # 단건 파일 검증
    if args.file:
        report = gatekeeper.verify(args.file, platform_override=platform_override)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print_gate_report(report, show_hints=(not args.no_hints))
        sys.exit(0 if report.is_passed else 1)

    # 디렉터리 일괄 검증
    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"❌ 디렉터리를 찾을 수 없습니다: {args.dir}")
            sys.exit(1)

        files = (
            list(dir_path.glob("*.md")) + list(dir_path.glob("**/*.md")) +
            list(dir_path.glob("*.mdx")) + list(dir_path.glob("**/*.mdx"))
        )
        files = sorted(list(set(files)))
        if not files:
            print(f"⚠️ 디렉터리 내에 .md/.mdx 파일이 없습니다: {args.dir}")
            sys.exit(0)

        print(f"\n📂 총 {len(files)}개 마크다운 파일 일괄 철벽 검증 시작...")
        reports: List[GateReport] = []
        fail_count = 0

        for f in files:
            rep = gatekeeper.verify(str(f), platform_override=platform_override)
            reports.append(rep)
            if not rep.is_passed:
                fail_count += 1
                if not args.json:
                    print_gate_report(rep, show_hints=(not args.no_hints))

        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 60)
            print(f"📊 [일괄 검증 종합 결과: 총 {len(files)}편]")
            print(f"  - 통과: {Color.GREEN}{len(files) - fail_count}편{Color.RESET}")
            print(f"  - 차단: {Color.RED}{fail_count}편{Color.RESET}")
            print("=" * 60 + "\n")

        sys.exit(0 if fail_count == 0 else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
