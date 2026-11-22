# -*- coding: utf-8 -*-
"""
blog_core.rules.common.live_fact_check - Gate 12: Live Fact-Check & Anti-Stale Guard
검증 대상:
1. 명확한 기준 시점(예: '2026년 11월 기준', '[2026년 11월]', '2026년 11월 20일 기준', 'November 2026' 등) 표기 검증.
2. 낡은 과거 데이터(2021~2023년 과거 수치, 이미 폐지/합병된 명칭 등) 및 LLM 사전학습 기억 환각 탐지:
   - KINDEX (2022년 10월 ACE로 리브랜딩, 단 역사적 회고/리브랜딩 설명 제외)
   - KBSTAR (2024년 7월 RISE로 리브랜딩, 단 역사적 회고/리브랜딩 설명 제외)
   - Credit Suisse (2023년 UBS 인수 합병)
   - 비현실적 금융 이상치 (총보수 > 10%, 분배율 > 100%, 정확한 키워드 1:1 바인딩 파싱)
3. ETF 메타데이터(티커, 상장일, 분배율, 총보수, 기초지수 등) 추출 및 규격 검증 (단일/비교/스펙 표 다중 레이아웃 지원).
4. 외부 실측 데이터 또는 공시와의 정합성을 검증할 수 있는 확장 가능한 교차 검증 인터페이스(LiveFactCheckInterface) 및 실측 SSOT 캐시.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


@dataclass
class FactCheckResult:
    """공시 및 실측 데이터 교차 검증 결과"""
    is_valid: bool
    discrepancy_message: str = ""
    field_name: str = ""
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None


class LiveFactCheckInterface(ABC):
    """외부 실측 데이터 및 공시 교차 검증기 인터페이스"""

    @abstractmethod
    def verify_ticker(self, ticker: str, platform: str = "stock") -> FactCheckResult:
        """티커 유효성 검증"""
        pass

    @abstractmethod
    def verify_metadata(self, ticker: str, metadata: Dict[str, Any], platform: str = "stock") -> List[FactCheckResult]:
        """ETF 메타데이터(운용사, 총보수, 기초지수 등) 교차 검증"""
        pass


class LocalCacheFactChecker(LiveFactCheckInterface):
    """
    내장 실측 마스터 데이터 기반 교차 검증기 (SSOT 캐시).
    국내 주요 커버드콜 및 글로벌 대표 ETF의 실측 메타데이터를 보유합니다.
    """

    KNOWN_ETFS: Dict[str, Dict[str, Any]] = {
        # 1. 국내 상장 대표 커버드콜 및 본주 (공식 실측 공시 데이터)
        "482730": {
            "name": "TIGER 미국S&P500타겟데일리커버드콜",
            "manager": "미래에셋자산운용",
            "benchmark": "S&P500 10% Daily Premium Covered Call",
            "target_div": 10.0,
        },
        "486290": {
            "name": "TIGER 미국나스닥100타겟데일리커버드콜",
            "manager": "미래에셋자산운용",
            "benchmark": "Nasdaq100 15% Daily Covered Call",
            "target_div": 15.0,
        },
        "483290": {
            "name": "KODEX 미국배당다우존스타겟커버드콜",
            "manager": "삼성자산운용",
            "benchmark": "Dow Jones U.S. Dividend 100",
            "target_div": 10.0,
        },
        "494300": {
            "name": "KODEX 미국나스닥100데일리커버드콜OTM",
            "manager": "삼성자산운용",
            "benchmark": "Nasdaq 100",
            "target_div": 12.0,
        },
        "491620": {
            "name": "RISE 미국테크100데일리고정커버드콜",
            "manager": "KB자산운용",
            "benchmark": "미국테크100",
            "target_div": 12.0,
        },
        "441680": {
            "name": "TIGER 미국나스닥100커버드콜(합성)",
            "manager": "미래에셋자산운용",
            "benchmark": "Cboe NASDAQ-100 BuyWrite Index",
            "target_div": 12.0,
        },
        "458760": {
            "name": "TIGER 미국배당다우존스타겟커버드콜2호",
            "manager": "미래에셋자산운용",
            "benchmark": "Dow Jones U.S. Dividend 100",
            "target_div": 7.0,
        },
        "402970": {
            "name": "ACE 미국배당다우존스",
            "manager": "한국투자신탁운용",
            "benchmark": "Dow Jones U.S. Dividend 100",
            "target_div": 3.8,
        },
        "458730": {
            "name": "TIGER 미국배당다우존스",
            "manager": "미래에셋자산운용",
            "benchmark": "Dow Jones U.S. Dividend 100",
            "target_div": 3.8,
        },
        "360750": {
            "name": "TIGER 미국S&P500",
            "manager": "미래에셋자산운용",
            "benchmark": "S&P 500 Index",
            "target_div": 1.5,
        },
        "133690": {
            "name": "TIGER 미국나스닥100",
            "manager": "미래에셋자산운용",
            "benchmark": "Nasdaq-100 Index",
            "target_div": 0.8,
        },
        # 2. 미국 직투 주요 인컴 및 커버드콜 ETF
        "JEPI": {
            "name": "JPMorgan Equity Premium Income ETF",
            "manager": "JPMorgan",
            "benchmark": "S&P 500",
        },
        "JEPQ": {
            "name": "JPMorgan Nasdaq Equity Premium Income ETF",
            "manager": "JPMorgan",
            "benchmark": "Nasdaq 100",
        },
        "SPYI": {
            "name": "NEOS S&P 500 High Income ETF",
            "manager": "NEOS",
            "benchmark": "S&P 500",
        },
        "QQQI": {
            "name": "NEOS Nasdaq 100 High Income ETF",
            "manager": "NEOS",
            "benchmark": "Nasdaq 100",
        },
        "XYLD": {
            "name": "Global X S&P 500 Covered Call ETF",
            "manager": "Global X",
            "benchmark": "Cboe S&P 500 BuyWrite Index",
        },
        "QYLD": {
            "name": "Global X NASDAQ 100 Covered Call ETF",
            "manager": "Global X",
            "benchmark": "Cboe NASDAQ 100 BuyWrite Index",
        },
    }

    def verify_ticker(self, ticker: str, platform: str = "stock") -> FactCheckResult:
        clean_t = ticker.strip().upper()
        if platform == "stock" and clean_t.isdigit():
            if len(clean_t) != 6:
                return FactCheckResult(
                    is_valid=False,
                    field_name="ticker",
                    discrepancy_message=f"국내 상장 ETF 단축코드는 6자리 숫자여야 합니다 (현재: '{clean_t}').",
                    actual_value=clean_t,
                )
        return FactCheckResult(is_valid=True, actual_value=clean_t)

    def verify_metadata(self, ticker: str, metadata: Dict[str, Any], platform: str = "stock") -> List[FactCheckResult]:
        results: List[FactCheckResult] = []
        clean_t = ticker.strip().upper()
        if clean_t not in self.KNOWN_ETFS:
            return results

        expected = self.KNOWN_ETFS[clean_t]

        # 1. 운용사 대조
        if "manager" in metadata and "manager" in expected:
            act_mgr = metadata["manager"].strip()
            exp_mgr = expected["manager"].strip()
            if act_mgr and exp_mgr and (act_mgr not in exp_mgr and exp_mgr not in act_mgr):
                results.append(FactCheckResult(
                    is_valid=False,
                    field_name="운용사",
                    discrepancy_message=f"티커 [{clean_t}]의 운용사 불일치 (공시: '{exp_mgr}' vs 본문: '{act_mgr}').",
                    expected_value=exp_mgr,
                    actual_value=act_mgr,
                ))

        # 2. 기초지수 대조 (주요 지수 키워드 교차 검증)
        if "benchmark" in metadata and "benchmark" in expected:
            act_bm = metadata["benchmark"].strip()
            exp_bm = expected["benchmark"].strip()
            # S&P500 종목인데 본문 기초지수가 나스닥이나 코스피로 둔갑한 경우
            if ("S&P" in exp_bm or "S&P500" in exp_bm) and not ("S&P" in act_bm or "S&P500" in act_bm):
                results.append(FactCheckResult(
                    is_valid=False,
                    field_name="기초지수",
                    discrepancy_message=f"티커 [{clean_t}]의 기초지수 불일치 (공시: '{exp_bm}' vs 본문: '{act_bm}').",
                    expected_value=exp_bm,
                    actual_value=act_bm,
                ))
            elif ("Nasdaq" in exp_bm or "나스닥" in exp_bm) and not ("Nasdaq" in act_bm or "나스닥" in act_bm or "테크" in act_bm):
                results.append(FactCheckResult(
                    is_valid=False,
                    field_name="기초지수",
                    discrepancy_message=f"티커 [{clean_t}]의 기초지수 불일치 (공시: '{exp_bm}' vs 본문: '{act_bm}').",
                    expected_value=exp_bm,
                    actual_value=act_bm,
                ))
            elif ("Dow Jones" in exp_bm or "다우존스" in exp_bm or "SCHD" in exp_bm) and not ("Dow" in act_bm or "다우" in act_bm or "SCHD" in act_bm or "배당" in act_bm):
                results.append(FactCheckResult(
                    is_valid=False,
                    field_name="기초지수",
                    discrepancy_message=f"티커 [{clean_t}]의 기초지수 불일치 (공시: '{exp_bm}' vs 본문: '{act_bm}').",
                    expected_value=exp_bm,
                    actual_value=act_bm,
                ))

        return results


# 전역 팩트체커 레지스트리 (테스트 목킹 및 외부 확장 지원)
_GLOBAL_FACT_CHECKER: LiveFactCheckInterface = LocalCacheFactChecker()


def get_global_fact_checker() -> LiveFactCheckInterface:
    return _GLOBAL_FACT_CHECKER


def set_global_fact_checker(checker: LiveFactCheckInterface):
    global _GLOBAL_FACT_CHECKER
    _GLOBAL_FACT_CHECKER = checker


def extract_metadata_from_tables(body: str) -> Dict[str, Dict[str, str]]:
    """
    마크다운 테이블에서 ETF 메타데이터(티커, 운용사, 총보수, 기초지수, 상장일 등)를 추출.
    각 티커별로 독립적인 메타데이터 딕셔너리를 구성하여 다종목 비교 시 간섭을 방지합니다.
    지원 레이아웃:
    - Layout 1: 표준 [안 A] 스펙 표 (Key-Value 페어 테이블)
    - Layout 2: 열(Column) 기준 다종목 비교 표 (헤더에 티커 나열)
    - Layout 3: 행(Row) 기준 다종목 비교 표 (각 행에 티커 및 스펙 나열)
    """
    etfs: Dict[str, Dict[str, str]] = {}

    lines = body.splitlines()
    table_blocks: List[List[str]] = []
    current_block: List[str] = []

    for line in lines:
        if line.strip().startswith("|"):
            current_block.append(line.strip())
        else:
            if current_block:
                table_blocks.append(current_block)
                current_block = []
    if current_block:
        table_blocks.append(current_block)

    for block in table_blocks:
        if len(block) < 2:
            continue
        parsed_rows: List[List[str]] = []
        for line in block:
            parts = [p.strip().replace("**", "").replace("*", "") for p in line.split("|")]
            if parts and parts[0] == "":
                parts = parts[1:]
            if parts and parts[-1] == "":
                parts = parts[:-1]
            if parts and not all(c in "-: " for c in "".join(parts)):
                parsed_rows.append(parts)

        if not parsed_rows:
            continue

        header = parsed_rows[0]

        # Layout 1 판별: Key-Value 테이블 (예: 항목 | 상세 내용 | 항목 | 상세 내용)
        is_kv_table = (
            any(c.strip() in ["항목", "구분", "Key", "Property", "지표"] for c in header)
            and any(c.strip() in ["상세 내용", "내용", "상세", "Value", "Details", "스펙"] for c in header)
        )

        if is_kv_table:
            block_ticker = None
            block_meta: Dict[str, str] = {}
            for row in parsed_rows:
                for i in range(0, len(row) - 1, 2):
                    k = row[i]
                    v = row[i + 1] if i + 1 < len(row) else ""
                    if any(t in k for t in ["종목코드", "티커", "Ticker", "단축코드"]):
                        m = re.search(r"([0-9]{6})", v)
                        if not m:
                            m = re.search(r"\b([A-Za-z0-9]{4,6})\b", v)
                        if m:
                            block_ticker = m.group(1).upper()
                    if any(t in k for t in ["운용사", "발행사", "Manager"]):
                        block_meta["manager"] = v
                    elif any(t in k for t in ["기초지수", "Benchmark"]):
                        block_meta["benchmark"] = v
                    elif any(t in k for t in ["총보수", "수수료", "Expense"]):
                        block_meta["expense"] = v
                    elif any(t in k for t in ["상장일", "Inception"]):
                        block_meta["listing_date"] = v
                    elif any(t in k for t in ["분배율", "배당률", "Yield", "Distribution"]):
                        block_meta["distribution_rate"] = v

            if block_ticker:
                if block_ticker not in etfs:
                    etfs[block_ticker] = {}
                etfs[block_ticker].update(block_meta)
            continue

        # Layout 2 판별: 열(Column)에 티커가 배치된 비교 테이블 (예: | 구분 | 482730 | 483290 |)
        col_tickers: Dict[int, str] = {}
        for col_idx, col_name in enumerate(header):
            m = re.search(r"\b([0-9]{6})\b", col_name)
            if not m:
                m = re.search(r"\b(JEPI|JEPQ|SPYI|QQQI|XYLD|QYLD)\b", col_name)
            if m:
                cand = m.group(1).upper()
                col_tickers[col_idx] = cand
                if cand not in etfs:
                    etfs[cand] = {}

        if col_tickers:
            for row in parsed_rows[1:]:
                row_label = row[0] if row else ""
                for col_idx, ticker in col_tickers.items():
                    if col_idx < len(row):
                        val = row[col_idx]
                        if any(k in row_label for k in ["운용사", "발행사", "Manager"]):
                            etfs[ticker]["manager"] = val
                        elif any(k in row_label for k in ["총보수", "수수료", "Expense"]):
                            etfs[ticker]["expense"] = val
                        elif any(k in row_label for k in ["기초지수", "지수", "Benchmark"]):
                            etfs[ticker]["benchmark"] = val
                        elif any(k in row_label for k in ["상장일", "Inception"]):
                            etfs[ticker]["listing_date"] = val
                        elif any(k in row_label for k in ["분배율", "배당률", "Yield"]):
                            etfs[ticker]["distribution_rate"] = val
            continue

        # Layout 3 판별: 행(Row) 단위로 티커가 배치된 테이블 (예: | 482730 | 미래에셋자산운용 | ...)
        for row in parsed_rows[1:]:
            row_ticker = None
            for cell in row:
                m = re.search(r"\b([0-9]{6})\b", cell)
                if not m:
                    m = re.search(r"\b(JEPI|JEPQ|SPYI|QQQI|XYLD|QYLD)\b", cell)
                if m:
                    cand = m.group(1).upper()
                    # 비교 대상 본주(예: 360750) 행 단독인 경우 메인 티커 목록과 분리
                    row_ticker = cand
                    break
            if row_ticker:
                if row_ticker not in etfs:
                    etfs[row_ticker] = {}
                for col_idx, cell in enumerate(row):
                    col_name = header[col_idx] if col_idx < len(header) else ""
                    if any(k in col_name for k in ["운용사", "발행사", "Manager"]):
                        etfs[row_ticker]["manager"] = cell
                    elif any(k in col_name for k in ["총보수", "수수료", "Expense"]):
                        etfs[row_ticker]["expense"] = cell
                    elif any(k in col_name for k in ["기초지수", "지수", "Benchmark"]):
                        etfs[row_ticker]["benchmark"] = cell
                    elif any(k in col_name for k in ["상장일", "Inception"]):
                        etfs[row_ticker]["listing_date"] = cell
                    elif any(k in col_name for k in ["분배율", "배당률", "Yield"]):
                        etfs[row_ticker]["distribution_rate"] = cell

    return etfs


class ExplicitTemporalAnchorRule(BaseRule):
    """명확한 기준 시점(예: 2026년 11월 기준) 표기 의무화 검증 규칙 (Gate 12)"""

    rule_id = "G12_EXPLICIT_TEMPORAL_ANCHOR"
    gate_id = "GATE_12"
    gate_name = "최신 실측 데이터 및 팩트 교차 검증 방벽 (Live Fact-Check & Anti-Stale Guard)"
    description = "실측 금융 수치 및 ETF 분석 포스팅의 명확한 기준 시점(연월/일) 표기 검증 (시점 없는 모호한 단정 수치 차단)"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    # 기준 시점 정규식 패턴 (국문 및 영문 시점 앵커 지원)
    TEMPORAL_ANCHOR_PATTERNS = [
        # 국문 연월일 기준 (예: 2026년 11월 기준, 2026년 11월 20일 기준, 2026년 11월 현재)
        r"202[4-9]년\s*\d{1,2}월(?:\s*\d{1,2}일)?(?:\s*말|\s*초|\s*중순)?\s*(?:기준|현재|실측|공시|데이터|비교)",
        r"\[202[4-9]년\s*\d{1,2}월(?:\s*\d{1,2}일)?\]",
        r"\[202[4-9]-\d{2}(?:-\d{2})?\]",
        r"202[4-9]-\d{2}(?:-\d{2})?\s*기준",
        r"202[4-9]\s*(?:상반기|하반기)\s*(?:기준|현재)",
        # 영문 날짜 앵커 (예: As of November 2026, November 20, 2026, Nov 2026 등)
        r"(?:As of|as of)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Q[1-4]|202[4-9])",
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?202[4-9]",
        r"기준일?\s*[:：]\s*202[4-9]",
        r"기준\s*시점\s*[:：]\s*202[4-9]",
        r"실측\s*시점\s*[:：]\s*202[4-9]",
    ]

    def check(self, ctx: RuleContext) -> List[Violation]:
        # 홈 랜딩이나 기술 튜토리얼은 제외
        if ctx.platform in ["dev", "gear"] and not any(k in ctx.body for k in ["커버드콜", "분배율", "총보수", "배당", "ETF"]):
            return []

        # 금융/ETF 콘텐츠 여부 판별 (수치 및 금융 키워드 탐지)
        has_financial_metrics = any(
            k in ctx.body for k in [
                "커버드콜", "분배금", "분배율", "배당률", "총보수", "기초지수", "순자산", "NAV", "AUM",
                "TIGER", "KODEX", "ACE", "RISE", "JEPI", "SPYI", "0DTE", "Covered Call", "dividend yield"
            ]
        )
        if not has_financial_metrics:
            return []

        # 1. 포스트 제목 검사
        title = ctx.fm_data.get("title", "")
        has_title_anchor = any(re.search(p, title) for p in self.TEMPORAL_ANCHOR_PATTERNS)

        # 2. 본문 서두 및 테이블 검사
        has_body_anchor = any(re.search(p, ctx.body) for p in self.TEMPORAL_ANCHOR_PATTERNS)

        # 3. Frontmatter date 필드 검사 (Jekyll 예약 포스트의 YYYY-MM-DD 시점 앵커)
        fm_date = ctx.fm_data.get("date", "")
        has_fm_date_anchor = bool(re.search(r"202[4-9]-\d{2}-\d{2}", str(fm_date)))

        if not has_title_anchor and not has_body_anchor and not has_fm_date_anchor:
            return [
                Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet=f"Title: {title[:80]}",
                    message="[명확한 실측 기준 시점 누락] 금융 수치 및 ETF 분석이 포함된 포스팅에 명확한 기준 시점(예: '[2026년 11월]' 또는 '2026년 11월 기준')이 명시되지 않았습니다. 시점 없는 모호한 단정 수치는 독자에게 혼선을 줄 수 있습니다.",
                    fix_hint="글 제목 앞에 '[YYYY년 M월]'을 표기하거나 본문 서두/요약표에 '2026년 11월 기준 실측 데이터'와 같이 명확한 기준 연월을 명시하십시오."
                )
            ]

        return []


class AntiStaleAndHallucinationRule(BaseRule):
    """과거 낡은 데이터 현재화 오인 및 리브랜딩 소멸 명칭 등 LLM 과거 기억 환각 탐지 규칙 (Gate 12)"""

    rule_id = "G12_ANTI_STALE_AND_HALLUCINATION"
    gate_id = "GATE_12"
    gate_name = "최신 실측 데이터 및 팩트 교차 검증 방벽 (Live Fact-Check & Anti-Stale Guard)"
    description = "2021~2023년 과거 시점 현재화 오인, 소멸된 구형 브랜드(KINDEX, KBSTAR 등) 환각, 비현실적 금융 이상치 차단"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        lines = ctx.lines

        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            # 1. 과거 연도(2020~2023년)를 '현재'나 '올해'로 오인 서술하는 낡은 사전학습 기억 고착
            if re.search(r"(?:올해|현재|최근|지금|금년)\s*(?:인|는|은)?\s*202[0-3]년", line) or \
               re.search(r"202[0-3]년\s*(?:현재|기준\s*현재|지금)", line) or \
               re.search(r"202[0-3]년인\s*올해", line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[낡은 과거 시점 고착 환각] 2021~2023년 과거 시점을 '현재' 또는 '올해'로 서술하는 LLM 과거 사전학습 고착이 감지되었습니다.",
                    fix_hint="현재 운영 시점인 2026년 기준으로 최신 실측 데이터를 반영하여 서술하십시오."
                ))

            # 역사적 리브랜딩 설명 문맥(예: '과거 KINDEX에서 ACE로 리브랜딩', '구 KBSTAR', '구 ARIRANG')은 허용
            is_historical_rebranding = bool(
                re.search(
                    r"(?:과거\s*(?:KINDEX|KBSTAR|ARIRANG)|(?:구\s*|\(구\s*)(?:KINDEX|KBSTAR|ARIRANG)|(?:KINDEX|KBSTAR|ARIRANG)\s*(?:에서|이|가)?\s*(?:ACE|RISE|PLUS)로|리브랜딩|rebrand)",
                    line,
                    re.IGNORECASE,
                )
            )

            # 2. 리브랜딩으로 소멸된 구형 ETF 브랜드 환각: KINDEX
            # 2022년 10월 한국투자신탁운용이 'ACE'로 전면 변경
            # 한국어 조사(KINDEX는, KINDEX의 등)가 붙는 경우도 정확히 탐지하기 위해 영문/숫자 경계 사용
            if not is_historical_rebranding and re.search(r"(?<![A-Za-z0-9])KINDEX(?![A-Za-z0-9])", line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[소멸된 브랜드 환각] 'KINDEX'는 2022년 10월 한국투자신탁운용에 의해 'ACE'로 전면 리브랜딩되었습니다. 2026년 현재 글에서 KINDEX를 사용하는 것은 과거 기억 의존 오류입니다.",
                    fix_hint="'KINDEX'를 현재 공식 명칭인 'ACE'로 수정하십시오."
                ))

            # 3. 리브랜딩으로 소멸된 구형 ETF 브랜드 환각: KBSTAR
            # 2024년 7월 KB자산운용이 'RISE'로 전면 변경
            if not is_historical_rebranding and re.search(r"(?<![A-Za-z0-9])KBSTAR(?![A-Za-z0-9])", line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[소멸된 브랜드 환각] 'KBSTAR'는 2024년 7월 KB자산운용에 의해 'RISE'로 전면 리브랜딩되었습니다. 2026년 현재 상품에 KBSTAR를 사용하는 것은 과거 기억 의존 오류입니다.",
                    fix_hint="'KBSTAR'를 현재 공식 명칭인 'RISE'로 수정하십시오."
                ))

            # 3-2. 리브랜딩으로 소멸된 구형 ETF 브랜드 환각: ARIRANG
            # 2024년 7월 한화자산운용이 'PLUS'로 전면 변경
            if not is_historical_rebranding and re.search(r"(?<![A-Za-z0-9])ARIRANG(?![A-Za-z0-9])", line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[소멸된 브랜드 환각] 'ARIRANG'은 2024년 7월 한화자산운용에 의해 'PLUS'로 전면 리브랜딩되었습니다. 2026년 현재 상품에 ARIRANG을 사용하는 것은 과거 기억 의존 오류입니다.",
                    fix_hint="'ARIRANG'을 현재 공식 명칭인 'PLUS'로 수정하십시오."
                ))

            # 4. 크레디트 스위스(Credit Suisse) 독립 은행 환각 (2023년 UBS 인수 합병)
            if not is_historical_rebranding and re.search(r"(?<![A-Za-z0-9])Credit\s+Suisse(?![A-Za-z0-9]).*?(?:현재|독립|운용|발행)", line, re.IGNORECASE):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[피인수 기관 환각] 크레디트 스위스(Credit Suisse)는 2023년 UBS에 인수 합병되어 독립 기관으로 존재하지 않습니다.",
                    fix_hint="UBS 또는 현재 인수 주체로 명칭을 수정하십시오."
                ))

            # 5. 비현실적 금융 이상치(Outlier) 환각
            # 수치와 수치 범주를 1:1로 엄격히 결합하여 오탐(동일 행의 다른 퍼센트 오인) 차단

            # 커버드콜 연 분배율 > 100%
            dist_patterns = [
                r"(?:연\s*|연간\s*|목표\s*|추정\s*)?([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:수준)?(?:의|인)?\s*(?:연간\s*|추정\s*)?(?:분배율|배당수익률|배당률|distribution\s*rate|dividend\s*yield)",
                r"(?:분배율|배당수익률|배당률|distribution\s*rate|dividend\s*yield)(?:는|가|은|이)?\s*(?:약\s*|수준이\s*)?(?:연\s*|연간\s*)?([0-9]+(?:\.[0-9]+)?)\s*%",
                r"\|\s*(?:\*\*)?(?:최근\s*)?(?:연환산\s*)?(?:분배율|배당률)(?:\*\*)?\s*\|\s*(?:\*\*)?(?:연\s*)?([0-9]+(?:\.[0-9]+)?)\s*%",
            ]
            for p in dist_patterns:
                for m in re.finditer(p, line, re.IGNORECASE):
                    try:
                        val = float(m.group(1))
                        if val > 100.0:
                            violations.append(Violation(
                                gate_id=self.gate_id,
                                gate_name=self.gate_name,
                                rule_id=self.rule_id,
                                severity=self.default_severity,
                                line_number=idx,
                                snippet=line[:100],
                                message=f"[비현실적 분배율 환각] 커버드콜 분배율이 연 {val}%로 표기되었습니다. 연 100%를 초과하는 비현실적인 환각 수치입니다.",
                                fix_hint="실측 공시 분배율(통상 연 8%~15% 수준)로 바로잡으십시오."
                            ))
                            break
                    except ValueError:
                        pass

            # 총보수 > 10%
            fee_patterns = [
                r"(?:연\s*|연간\s*)?([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:수준)?(?:의|인)?\s*(?:저렴한\s*|높은\s*|합리적인\s*)?(?:총보수|운용보수|수수료|expense\s*ratio)",
                r"(?:총보수|운용보수|수수료|expense\s*ratio)(?:는|가|은|이)?\s*(?:약\s*|수준이\s*)?(?:연\s*|연간\s*)?([0-9]+(?:\.[0-9]+)?)\s*%",
                r"\|\s*(?:\*\*)?(?:총보수|운용보수)(?:\s*\(수수료\))?(?:\*\*)?\s*\|\s*(?:\*\*)?(?:연\s*)?([0-9]+(?:\.[0-9]+)?)\s*%",
            ]
            for p in fee_patterns:
                for m in re.finditer(p, line, re.IGNORECASE):
                    try:
                        val = float(m.group(1))
                        if val > 10.0:
                            violations.append(Violation(
                                gate_id=self.gate_id,
                                gate_name=self.gate_name,
                                rule_id=self.rule_id,
                                severity=self.default_severity,
                                line_number=idx,
                                snippet=line[:100],
                                message=f"[비현실적 총보수 환각] ETF 총보수가 연 {val}%로 표기되었습니다. 연 10%를 초과하는 비정상적인 수치입니다.",
                                fix_hint="실제 ETF 총보수(통상 연 0.1%~1.0% 수준)로 바로잡으십시오."
                            ))
                            break
                    except ValueError:
                        pass

        return violations


class LiveFactCheckInterfaceRule(BaseRule):
    """ETF 메타데이터 추출 및 외부 공시/실측 데이터 1:1 교차 검증 규칙 (Gate 12)"""

    rule_id = "G12_FACT_CHECK_INTERFACE"
    gate_id = "GATE_12"
    gate_name = "최신 실측 데이터 및 팩트 교차 검증 방벽 (Live Fact-Check & Anti-Stale Guard)"
    description = "포스트 본문에서 ETF 메타데이터(티커, 운용사 등)를 자동 추출하여 실측 데이터 인터페이스와 1:1 대조 검증"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        checker = get_global_fact_checker()

        # 본문 내 테이블에서 티커별 메타데이터 추출 (간섭 없는 1:1 매핑)
        tickers_found = extract_metadata_from_tables(ctx.body)

        # 2. 실측 인터페이스를 통한 티커 및 메타데이터 교차 검증
        for code, meta in tickers_found.items():
            # 티커 유효성 검증
            t_res = checker.verify_ticker(code, platform=ctx.platform)
            if not t_res.is_valid:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet=f"Ticker: {code}",
                    message=f"[실측 데이터 불일치] {t_res.discrepancy_message}",
                    fix_hint="정확한 실측 6자리 종목코드(국내) 또는 표준 티커(미국)로 수정하십시오."
                ))

            # 메타데이터(운용사, 기초지수 등) 교차 검증
            m_res_list = checker.verify_metadata(code, meta, platform=ctx.platform)
            for m_res in m_res_list:
                if not m_res.is_valid:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=1,
                        snippet=f"Ticker: {code}, {m_res.field_name}: {m_res.actual_value}",
                        message=f"[실측 메타데이터 불일치] {m_res.discrepancy_message}",
                        fix_hint=f"공시된 정확한 정보('{m_res.expected_value}')로 수정하십시오."
                    ))

        return violations
