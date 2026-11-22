# -*- coding: utf-8 -*-
"""
blog_core.rules.common.theory_integrity - Gate 11: Theoretical & Mathematical Integrity Guard
검증 대상:
1. 커버드콜 / 옵션 이론:
   - 내재가치와 시간가치 분해 공식 (내재가치 >= 0, OTM 내재가치 0)
   - 머니니스(ITM/ATM/OTM) 정의 및 가격 대소 관계 모순
   - 커버드콜 콜옵션 매도 상방 제한(Capped) 및 하방 노출(Uncapped) 비대칭 손익 왜곡 (단, 교육적 부정/오해 반박문 예외 인정)
   - 그릭스(Greeks: 세타 손익 방향성, 델타 부호) 정합성
2. 기술적 분석 / 캔들 이론:
   - 양봉/음봉 시가·종가(OHLC) 기하학적 정합성
   - 윗꼬리(상방 저항/매도) vs 밑꼬리(하방 지지/매수) 공방 심리 원리
3. 매크로 / 퀀트 이론:
   - 금리 인상/인하와 미래 현금흐름 할인율 및 성장주 밸류에이션 전이
   - CVD(누적 볼륨 델타) 시장가 체결량 정의 및 수급 다이버전스
   - 딜러 감마 익스포저(GEX: 포지티브=변동성 억제 vs 네거티브=변동성 증폭)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


def _is_negated_or_question(line: str) -> bool:
    """질문문 또는 오해 반박/부정문 여부 판별 (단정적 왜곡 서술만 정확히 차단)"""
    if re.search(r"(\?|을까요|는가요|을까\b|인가요|인지\b|여부)", line):
        return True
    # 부정 및 반박 키워드 (오해, 착각 바로잡기 등 교육적 문맥)
    negation_patterns = [
        r"(?:아닙니다|아니며|아닌|아니다|아닐|아니고|아니라|아니므로)",
        r"(?:않습니다|않으며|않다|않고|않은|않는|않도록)",
        r"(?:오해|착각|미신|허구|거짓|틀린|위험한\s*생각)",
        r"(?:불가능|존재하지\s*않|배제할\s*수\s*없|될\s*수\s*없|일어날\s*수\s*없)",
        r"\b(?:not|never|neither|nor|myth|misconception|false|incorrect|untrue|cannot|impossible)\b",
    ]
    return any(re.search(p, line, re.IGNORECASE) for p in negation_patterns)


class OptionCoveredCallTheoryRule(BaseRule):
    """커버드콜 및 옵션 이론 정합성 검증 규칙 (Gate 11)"""

    rule_id = "G11_OPTION_COVERED_CALL_INTEGRITY"
    gate_id = "GATE_11"
    gate_name = "금융 이론 및 수학적 메커니즘 방벽 (Theoretical & Mathematical Integrity Guard)"
    description = "옵션 내재가치 비음수성, OTM 순수 시간가치, 머니니스 판별, 커버드콜 비대칭 손익 및 그릭스 정의 정합성 검증"
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

            # 1. 내재가치 음수 주장 탐지 (수학적으로 max(0, S-K) >= 0)
            # 공백 포함 부등호: 내재가치 < 0, 내재가치 <= -1 등 지원
            has_negative_intrinsic = (
                re.search(r"내재가치(?:가|는)?\s*(?:마이너스|음수|음의\s*값|<\s*0|0\s*미만|≤\s*-)", line)
                or re.search(r"음(?:수)?의\s*내재가치", line)
                or re.search(r"\bintrinsic\s*value\b.*?\b(?:is\s*)?(?:negative|<\s*0|below\s*0)\b", line, re.IGNORECASE)
                or re.search(r"\bnegative\s*intrinsic\s*value\b", line, re.IGNORECASE)
            )
            if has_negative_intrinsic and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[내재가치 비음수성 위반] 내재가치는 max(0, S-K)(콜) 또는 max(0, K-S)(풋)으로 정의되므로 수학적으로 음수가 될 수 없습니다 (항상 >= 0).",
                    fix_hint="내재가치가 0이 되는 외가격(OTM) 상태로 표현하거나 시간가치(Time Value) 소멸로 수정하십시오."
                ))

            # 2. OTM(외가격) 옵션의 내재가치 보유/증가 왜곡 탐지
            has_otm_intrinsic = (
                re.search(r"(?:외가격|OTM)(?:\s*옵션)?(?:의|은|는)?\s*내재가치(?:가|를)?\s*.*?(?:크다|증가|발생|보유|가진다|존재)", line)
                or re.search(r"내재가치(?:가|를)?\s*(?:가진|포함한)\s*(?:외가격|OTM)", line)
                or re.search(r"\b(?:OTM|out-of-the-money)\s*options?\s*.*?(?:have|possess|contain|yield)\s*(?:positive\s*)?intrinsic\s*value\b", line, re.IGNORECASE)
            )
            if has_otm_intrinsic and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[외가격 내재가치 모순] 외가격(OTM) 옵션의 내재가치는 수학적으로 0이며, 프리미엄은 100% 시간가치(Time Value)로만 구성됩니다.",
                    fix_hint="OTM 옵션의 가치는 시간가치로만 설명하거나, 내가격(ITM) 옵션으로 정정하십시오."
                ))

            # 3. 콜옵션 머니니스 모순
            # 콜옵션: 주가 < 행사가인데 내가격(ITM) 주장
            call_itm_contradiction = (
                re.search(r"(?:콜옵션|Call\s*Option).*?(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:낮|밑돌|밑도|하회|미만).*?(?:내가격|ITM)", line)
                or re.search(r"(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:낮|밑돌|밑도|하회|미만).*?(?:콜옵션|Call\s*Option).*?(?:내가격|ITM)", line)
                or re.search(r"\bcall\s*options?\s*(?:are|is)\s*(?:in-the-money|ITM)\s*when\s*.*?(?:price|stock)\s*(?:is\s*)?(?:below|lower\s*than|under)\s*(?:the\s*)?strike\b", line, re.IGNORECASE)
            )
            if call_itm_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[콜옵션 머니니스 모순] 콜옵션은 기초자산 가격이 행사가격보다 낮을 때(S < K) 외가격(OTM)이며, 내가격(ITM)이 될 수 없습니다.",
                    fix_hint="주가가 행사가격 미만인 상태는 외가격(OTM)으로 바로잡으십시오."
                ))

            # 콜옵션: 주가 > 행사가인데 외가격(OTM) 주장
            call_otm_contradiction = (
                re.search(r"(?:콜옵션|Call\s*Option).*?(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:높|웃돌|웃도|상회|초과).*?(?:외가격|OTM)", line)
                or re.search(r"(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:높|웃돌|웃도|상회|초과).*?(?:콜옵션|Call\s*Option).*?(?:외가격|OTM)", line)
                or re.search(r"\bcall\s*options?\s*(?:are|is)\s*(?:out-of-the-money|OTM)\s*when\s*.*?(?:price|stock)\s*(?:is\s*)?(?:above|higher\s*than|exceeds)\s*(?:the\s*)?strike\b", line, re.IGNORECASE)
            )
            if call_otm_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[콜옵션 머니니스 모순] 콜옵션은 기초자산 가격이 행사가격을 상회할 때(S > K) 내가격(ITM)이며, 외가격(OTM)이 아닙니다.",
                    fix_hint="주가가 행사가격을 상회하는 상태는 내가격(ITM)으로 바로잡으십시오."
                ))

            # 4. 풋옵션 머니니스 모순
            put_itm_contradiction = (
                re.search(r"(?:풋옵션|Put\s*Option).*?(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:높|웃돌|웃도|상회|초과).*?(?:내가격|ITM)", line)
                or re.search(r"(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:높|웃돌|웃도|상회|초과).*?(?:풋옵션|Put\s*Option).*?(?:내가격|ITM)", line)
                or re.search(r"\bput\s*options?\s*(?:are|is)\s*(?:in-the-money|ITM)\s*when\s*.*?(?:price|stock)\s*(?:is\s*)?(?:above|higher\s*than|exceeds)\s*(?:the\s*)?strike\b", line, re.IGNORECASE)
            )
            if put_itm_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[풋옵션 머니니스 모순] 풋옵션은 기초자산 가격이 행사가격보다 높을 때(S > K) 외가격(OTM)이며, 내가격(ITM)이 될 수 없습니다.",
                    fix_hint="주가가 행사가격을 상회할 때 풋옵션은 외가격(OTM)으로 바로잡으십시오."
                ))

            put_otm_contradiction = (
                re.search(r"(?:풋옵션|Put\s*Option).*?(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:낮|밑돌|밑도|하회|미만).*?(?:외가격|OTM)", line)
                or re.search(r"(?:주가|기초자산|가격)(?:가|는|이)?\s*행사가(?:격)?(?:보다|를|을)?\s*(?:낮|밑돌|밑도|하회|미만).*?(?:풋옵션|Put\s*Option).*?(?:외가격|OTM)", line)
                or re.search(r"\bput\s*options?\s*(?:are|is)\s*(?:out-of-the-money|OTM)\s*when\s*.*?(?:price|stock)\s*(?:is\s*)?(?:below|lower\s*than|under)\s*(?:the\s*)?strike\b", line, re.IGNORECASE)
            )
            if put_otm_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[풋옵션 머니니스 모순] 풋옵션은 기초자산 가격이 행사가격보다 낮을 때(S < K) 내가격(ITM)이며, 외가격(OTM)이 아닙니다.",
                    fix_hint="주가가 행사가격을 밑돌 때 풋옵션은 내가격(ITM)으로 바로잡으십시오."
                ))

            # 5. 커버드콜 하방 완전 차단 / 원금 무손실 왜곡 단정문 탐지 (반박/부정문 제외)
            if not _is_negated_or_question(line):
                downside_false_claim = (
                    re.search(r"(?:커버드콜|Covered\s*Call).*?(?:하방(?:이|은)?\s*(?:완전히\s*)?(?:막혀\s*있|차단되어\s*(?:있|손실이\s*없)|닫혀\s*있)|원금\s*손실(?:이|은)?\s*(?:전혀\s*)?(?:없다|없습니다|없는\s*(?:상품|구조))|원금(?:이\s*)?(?:100%\s*)?보장|폭락(?:해도|시에도)\s*(?:원금\s*)?(?:손실\s*없다|손실이\s*발생하지\s*않는다))", line)
                    or re.search(r"(?:하방(?:이|은)?\s*(?:완전히\s*)?(?:막혀\s*있|차단되어\s*(?:있|손실이\s*없)|닫혀\s*있)|원금\s*손실(?:이|은)?\s*(?:전혀\s*)?(?:없다|없습니다|없는\s*(?:상품|구조))|원금(?:이\s*)?(?:100%\s*)?보장).*?(?:커버드콜|Covered\s*Call)", line)
                    or re.search(r"\bcovered\s*calls?\s*(?:eliminate[s]?\s*all\s*downside|guarantee[s]?\s*principal|have\s*no\s*(?:downside|capital\s*loss))\b", line, re.IGNORECASE)
                )
                if downside_false_claim:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=idx,
                        snippet=line[:100],
                        message="[커버드콜 하방 비대칭성 왜곡] 커버드콜은 기초자산의 하방 위험(Uncapped Downside)에 그대로 노출되며 프리미엄 수취분만큼만 완충(Cushion)됩니다. 하방이 완전히 막혀 있거나 원금 손실이 없다는 주장은 허위이자 중대한 오류입니다.",
                        fix_hint="'하방 완충(Downside Buffer/Cushion)' 효과로 표현을 완화하고 기초자산 급락 시 원금 손실 위험이 존재함을 명시하십시오."
                    ))

            # 6. 커버드콜 상방 무한 향유 왜곡 (반박/부정문 제외)
            if not _is_negated_or_question(line):
                upside_false_claim = (
                    re.search(r"(?:커버드콜|Covered\s*Call).*?(?:상방(?:이|은)?\s*(?:무한(?:대)?로\s*열려|제한이\s*없)|주가\s*(?:상승|폭등)분을?\s*(?:100%|전부|온전히)\s*(?:향유|누린다|다\s*가져))", line)
                    or re.search(r"\bcovered\s*calls?\s*(?:offer|provide|have)\s*(?:unlimited|uncapped)\s*upside\b", line, re.IGNORECASE)
                    or re.search(r"\bfully\s*capture[s]?\s*(?:all|100%)\s*stock\s*(?:gains|upside)\b", line, re.IGNORECASE)
                )
                if upside_false_claim:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=idx,
                        snippet=line[:100],
                        message="[커버드콜 상방 제한(Capped Upside) 무시] 커버드콜은 콜옵션 매도 포지션으로 인해 행사가격 이상의 주가 상승 이익이 상방 제한(Capped)됩니다.",
                        fix_hint="상방 이익이 행사가격 수준으로 제한(Capped)되는 구조적 한계와 기회비용을 명시하십시오."
                    ))

            # 7. 그릭스(Greeks) 정의 및 방향성 오류
            theta_error = (
                re.search(r"(?:옵션|콜옵션|풋옵션)\s*매수자(?:에게|는)?\s*(?:만기가\s*다가올수록\s*)?(?:세타(?:가|는)?\s*유리|시간가치(?:가|를)?\s*(?:증가|수취|이익))", line)
                or re.search(r"\boption\s*buyers?\s*(?:benefit[s]?|gain[s]?)\s*from\s*(?:theta\s*decay|time\s*decay)\b", line, re.IGNORECASE)
            )
            if theta_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[세타 손익 방향성 오류] 옵션 매수자는 만기 접근 시 시간가치 소멸(-Theta)로 손실을 입으며, 시간가치 수취는 옵션 매도자의 수익 원천입니다.",
                    fix_hint="옵션 매수자의 시간가치 잠식(-Theta Drag)과 매도자의 시간가치 수취(+Theta)로 방향성을 수정하십시오."
                ))

            delta_error = (
                re.search(r"콜옵션\s*(?:매도|숏)(?:는|은|가)?\s*(?:양의\s*델타|\+Delta|델타가\s*양수)", line)
                or re.search(r"콜옵션\s*(?:매도|숏).*?주가\s*상승(?:시|할수록)\s*(?:옵션\s*수익|이익이\s*증가)", line)
                or re.search(r"\b(?:short\s*calls?|selling\s*calls?)\s*(?:has|have|yields?)\s*(?:positive\s*delta|\+delta)\b", line, re.IGNORECASE)
            )
            if delta_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[옵션 델타 부호 오류] 콜옵션 매도는 음의 델타(-Delta) 포지션이며, 기초자산 주가 상승 시 옵션 포지션에서 손실이 발생합니다.",
                    fix_hint="콜옵션 매도는 음의 델타(-Delta)를 가지며 주가 하락/횡보 시 프리미엄을 방어하는 메커니즘으로 수정하십시오."
                ))

        return violations


class CandleTechnicalAnalysisIntegrityRule(BaseRule):
    """기술적 분석 OHLC 캔들 및 꼬리 공방 심리 원리 정합성 검증 규칙 (Gate 11)"""

    rule_id = "G11_CANDLE_TECHNICAL_ANALYSIS_INTEGRITY"
    gate_id = "GATE_11"
    gate_name = "금융 이론 및 수학적 메커니즘 방벽 (Theoretical & Mathematical Integrity Guard)"
    description = "OHLC 캔들 기하학(양봉: 종가>시가, 음봉: 종가<시가) 및 꼬리(윗꼬리=매도압력, 밑꼬리=매수지지) 공방 심리 정합성 검증"
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

            # 1. 양봉 모순 (시가 > 종가인데 양봉 주장)
            bullish_contradiction = (
                re.search(r"(?:시가가\s*종가보다\s*높|종가가\s*시가보다\s*낮).*?(?:양봉|Bullish\s*candle)", line)
                or re.search(r"(?:양봉|Bullish\s*candle).*?(?:시가가\s*종가보다\s*높|종가가\s*시가보다\s*낮)", line)
                or re.search(r"\bbullish\s*candle\b.*?\bopen\s*(?:is\s*)?(?:higher|above|greater)\s*than\s*close\b", line, re.IGNORECASE)
            )
            if bullish_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[양봉 OHLC 정의 모순] 양봉(Bullish Candle)은 종가가 시가보다 높아야(Close > Open) 성립합니다.",
                    fix_hint="종가가 시가보다 높은 양봉 또는 시가가 종가보다 높은 음봉으로 바로잡으십시오."
                ))

            # 2. 음봉 모순 (종가 > 시가인데 음봉 주장)
            bearish_contradiction = (
                re.search(r"(?:종가가\s*시가보다\s*높|시가가\s*종가보다\s*낮|종가가\s*시가를\s*(?:웃돌|웃도)|종가가\s*시가를\s*상회).*?(?:음봉|Bearish\s*candle)", line)
                or re.search(r"(?:음봉|Bearish\s*candle).*?(?:종가가\s*시가보다\s*높|시가가\s*종가보다\s*낮|종가가\s*시가를\s*(?:웃돌|웃도)|종가가\s*시가를\s*상회)", line)
                or re.search(r"\bbearish\s*candle\b.*?\bclose\s*(?:is\s*)?(?:higher|above|greater)\s*than\s*open\b", line, re.IGNORECASE)
            )
            if bearish_contradiction and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[음봉 OHLC 정의 모순] 음봉(Bearish Candle)은 종가가 시가보다 낮아야(Close < Open) 성립합니다.",
                    fix_hint="종가가 시가보다 낮은 음봉 또는 종가가 시가를 상회하는 양봉으로 바로잡으십시오."
                ))

            # 3. 윗꼬리 심리 모순 (윗꼬리를 매수 지지로 오설명)
            upper_wick_error = (
                re.search(r"(?:긴\s*)?윗꼬리(?:가|는)?\s*.*?(?:강력한\s*(?:매수\s*지지|하방\s*지지)|아래에서\s*받쳐주는\s*매수)", line)
                or re.search(r"\bupper\s*(?:wick|shadow)\b.*?(?:buying\s*support|support\s*from\s*buyers)\b", line, re.IGNORECASE)
            )
            if upper_wick_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[캔들 윗꼬리 심리 원리 모순] 윗꼬리는 장중 고가에서 매도 압력(저항)에 밀려 내려온 흔적이며, 하방 지지나 매수세의 승리가 아닙니다.",
                    fix_hint="윗꼬리는 '상방 저항' 및 '차익실현 매도 압력'으로 해석을 수정하십시오."
                ))

            # 4. 밑꼬리 심리 모순 (밑꼬리를 매도 저항으로 오설명)
            lower_wick_error = (
                re.search(r"(?:긴\s*)?밑꼬리(?:가|는)?\s*.*?(?:강력한\s*(?:매도\s*저항|상방\s*저항)|위에서\s*내리누르는\s*매도)", line)
                or re.search(r"\blower\s*(?:wick|shadow)\b.*?(?:selling\s*resistance|resistance\s*from\s*sellers)\b", line, re.IGNORECASE)
            )
            if lower_wick_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[캔들 밑꼬리 심리 원리 모순] 밑꼬리는 장중 저가에서 저가 매수세(지지)가 유입되어 가격을 밀어올린 흔적이며, 매도 저항이 아닙니다.",
                    fix_hint="밑꼬리는 '저가 매수 유입' 및 '하방 지지력'으로 해석을 수정하십시오."
                ))

        return violations


class MacroQuantIntegrityRule(BaseRule):
    """매크로 금리-밸류에이션, CVD, 딜러 GEX 이론 정합성 검증 규칙 (Gate 11)"""

    rule_id = "G11_MACRO_QUANT_INTEGRITY"
    gate_id = "GATE_11"
    gate_name = "금융 이론 및 수학적 메커니즘 방벽 (Theoretical & Mathematical Integrity Guard)"
    description = "금리-할인율-밸류에이션 전이 공식, CVD 시장가 체결량 정의, 딜러 감마 익스포저(GEX) 변동성 메커니즘 정합성 검증"
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

            # 1. 금리-할인율-밸류에이션 전이 모순
            rate_hike_error = (
                re.search(r"금리\s*(?:인상|상승).*?(?:할인율(?:을|이)?\s*(?:낮추|하락)|성장주.*?(?:밸류에이션\s*확장|유리|호재))", line)
                or re.search(r"\brate\s*hikes?\s*.*?(?:lower[s]?\s*(?:the\s*)?discount\s*rate|expand[s]?\s*growth\s*valuations?)\b", line, re.IGNORECASE)
            )
            if rate_hike_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[금리-할인율 전이 모순] 금리 상승은 할인율을 높여 미래 현금흐름의 현재가치(성장주 밸류에이션)를 축소시키는 압력으로 작용합니다.",
                    fix_hint="금리 인상이 할인율 상승을 유발하여 성장주 밸류에이션에 부담으로 작용한다는 정합적 메커니즘으로 수정하십시오."
                ))

            rate_cut_error = (
                re.search(r"금리\s*(?:인하|하락).*?(?:할인율(?:을|이)?\s*(?:높이|상승)|성장주.*?(?:밸류에이션\s*축소|악재))", line)
                or re.search(r"\brate\s*cuts?\s*.*?(?:raise[s]?|increase[s]?)\s*(?:the\s*)?discount\s*rate\b", line, re.IGNORECASE)
            )
            if rate_cut_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[금리-할인율 전이 모순] 금리 인하는 할인율을 낮추어 미래 현금흐름 가치(성장주 밸류에이션) 확장을 유도합니다.",
                    fix_hint="금리 하락이 할인율을 낮추어 밸류에이션 확장에 기여한다는 원리로 수정하십시오."
                ))

            # 2. CVD (Cumulative Volume Delta) 정의 및 다이버전스 모순
            # 단순 나열("CVD, Limit Order Book depth...")이 아닌, CVD 자체를 지정가/미체결 잔량으로 정의·등치한 경우만 정확히 포착
            cvd_def_error = (
                re.search(r"CVD(?:는|가)?\s*.*?(?:지정가\s*주문의\s*(?:단순\s*)?(?:합계|잔량)|미체결\s*주문\s*잔량)", line)
                or re.search(r"\bCVD\s*(?:is|represents|measures|equals|means|refers\s*to)\s*(?:the\s*)?(?:limit\s*order\s*book|unfilled\s*orders)\b", line, re.IGNORECASE)
                or re.search(r"\bCVD\s*.*?\b(?:is\s*defined\s*as|equals\s*the)\s*(?:limit\s*order\s*book|unfilled\s*orders)\b", line, re.IGNORECASE)
            )
            if cvd_def_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[CVD 정의 모순] CVD(누적 볼륨 델타)는 시장가 매수 체결량에서 시장가 매도 체결량을 차감한 순체결 볼륨의 누적치이며 미체결 지정가 잔량이 아닙니다.",
                    fix_hint="CVD를 '공격적 시장가 체결 볼륨의 누적 델타'로 정확히 정의하십시오."
                ))

            cvd_div_error = (
                re.search(r"(?:가격|주가)가\s*(?:상승|신고가).*?CVD(?:가|는)?\s*(?:하락|급락|신저가).*?(?:매수세(?:가|의)\s*(?:강화|지속|폭발)|강력한\s*공격적\s*매수)", line)
                or re.search(r"\bprice\s*(?:rises|new\s*high).*?CVD\s*(?:falls|drops).*?(?:strengthening\s*buyers|bullish\s*momentum)\b", line, re.IGNORECASE)
            )
            if cvd_div_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[CVD 약세 다이버전스 해석 오류] 가격 상승 중 CVD 급락은 시장가 매수세의 소진 및 숨은 매도벽 흡수(약세 다이버전스)를 의미하며 매수세 강화가 아닙니다.",
                    fix_hint="가격 상승과 CVD 하락의 괴리를 '시장가 매수세 소진에 따른 약세 다이버전스'로 해석하십시오."
                ))

            # 3. 딜러 감마 익스포저 (GEX) 변동성 메커니즘 모순
            positive_gex_error = (
                re.search(r"(?:포지티브\s*감마|\+GEX).*?(?:변동성(?:을|이)?\s*(?:폭발|증폭|극대화)|추세\s*가속)", line)
                or re.search(r"\b(?:positive\s*gamma|\+GEX)\b.*?(?:amplifies?|explodes?|boosts?)\s*volatility\b", line, re.IGNORECASE)
            )
            if positive_gex_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[GEX 포지티브 감마 메커니즘 모순] 포지티브 감마(+GEX) 영역에서는 딜러가 주가 상승 시 매도, 하락 시 매수하는 역방향 헤징을 수행하여 변동성을 억제(Volatility Dampening)합니다.",
                    fix_hint="포지티브 감마 구간을 '딜러 역방향 헤징에 의한 변동성 억제 및 평균 회귀(Mean-Reversion)'로 수정하십시오."
                ))

            negative_gex_error = (
                re.search(r"(?:네거티브\s*감마|-GEX).*?(?:변동성(?:을|이)?\s*(?:억제|잠재|완화)|평균\s*회귀)", line)
                or re.search(r"\b(?:negative\s*gamma|-GEX)\b.*?(?:suppresses?|dampens?|dulls?)\s*volatility\b", line, re.IGNORECASE)
            )
            if negative_gex_error and not _is_negated_or_question(line):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=line[:100],
                    message="[GEX 네거티브 감마 메커니즘 모순] 네거티브 감마(-GEX) 영역에서는 딜러가 주가 상승 시 추가 매수, 하락 시 추가 매도하여 변동성을 증폭(Volatility Acceleration)시킵니다.",
                    fix_hint="네거티브 감마 구간을 '딜러 순방향 추격 헤징에 의한 변동성 증폭 및 추세 가속'으로 수정하십시오."
                ))

        return violations
