# -*- coding: utf-8 -*-
"""
blog_core.rules.common.legal_financial - Gate 8: Capital Markets Act & Financial Consumer Protection Law Compliance
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


CAPITAL_MARKETS_RULES = [
    # 1. 원금보장 및 손실보전 약정
    (
        r"원금(?:을|은|도|\s*)?\s*보장(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*아님|이\s*불가|을\s*하지\s*않|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_PRINCIPAL_GUARANTEE",
        "[자본시장법·금소법 방벽] '원금 보장' 표방 금지 (자본시장법 제55조 및 금소법 제21조). 금융투자상품은 원금 손실 위험이 수반되므로 원금을 보장할 수 없습니다.",
        "원금 보장 표현을 삭제하고 원금 손실 가능성 및 투자 위험 고지 문구를 삽입하십시오."
    ),
    (
        r"원금\s*(?:손실|손실이|손실은)\s*(?:없는|없음|없고|0%|제로)",
        "REJECT",
        "G8_FIN_NO_LOSS_CLAIM",
        "[자본시장법·금소법 방벽] '원금 손실 없음/0%' 단언 금지 (금소법 제19조 부당권유행위).",
        "원금 손실이 없다는 비현실적인 단언을 삭제하고 시장 변동성 위험을 명시하십시오."
    ),
    (
        r"원금(?:을|의|은|\s*)?\s*(?:전액\s*)?보존(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*불가|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_PRINCIPAL_PRESERVATION",
        "[자본시장법·금소법 방벽] '원금 보존' 약정 표현 금지 (자본시장법 제55조).",
        "원금 보존 표현을 삭제하십시오."
    ),
    (
        r"원금\s*(?:회수|반환)\s*100%",
        "REJECT",
        "G8_FIN_PRINCIPAL_RECOVERY",
        "[자본시장법·금소법 방벽] '원금 회수 100%' 표방 금지.",
        "원금 회수 100% 표현을 삭제하십시오."
    ),
    (
        r"손실(?:을|은|\s*)?\s*(?:전액\s*)?보전(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*불가|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_LOSS_COMPENSATION",
        "[자본시장법 제55조 위반] '손실 보전' 약속 금지.",
        "손실 보전 표현을 삭제하십시오."
    ),

    # 2. 확정수익 및 무위험 고수익 표방
    (
        r"확정\s*수익(?:률)?(?!\s*(?:을\s*보장하지\s*않|이\s*아닙|은\s*없|을\s*약속하지\s*않))",
        "REJECT",
        "G8_FIN_CONFIRMED_PROFIT",
        "[자본시장법·금소법 방벽] '확정 수익(률)' 표방 금지 (금소법 제19조). 예적금을 제외한 금융투자상품에 확정 수익률을 표방할 수 없습니다.",
        "확정 수익 표현을 삭제하고 기대 수익과 시나리오별 리스크를 균형 있게 기술하십시오."
    ),
    (
        r"무위험\s*고수익",
        "REJECT",
        "G8_FIN_RISK_FREE_HIGH_RETURN",
        "[자본시장법·금소법 방벽] '무위험 고수익' 기만 표현 금지 (금소법 제19조).",
        "고수익에는 상응하는 고위험이 수반됨을 명시하십시오."
    ),
    (
        r"위험\s*없는\s*(?:고수익|투자)",
        "REJECT",
        "G8_FIN_RISK_FREE_INVESTMENT",
        "[자본시장법·금소법 방벽] '위험 없는 투자' 표방 금지.",
        "투자 리스크를 객관적으로 명시하십시오."
    ),
    (
        r"수익(?:률)?(?:을|은|\s*)?\s*보장(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*아님|이\s*불가|을\s*하지\s*않|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_GUARANTEED_PROFIT",
        "[자본시장법·금소법 방벽] '수익(률) 보장' 표현 금지.",
        "수익 보장 표현을 삭제하십시오."
    ),
    (
        r"100%\s*(?:수익|수익률|원금보장)",
        "REJECT",
        "G8_FIN_100_PERCENT_PROFIT",
        "[자본시장법·금소법 방벽] '100% 수익(률)' 단언 금지.",
        "100% 수익 단언을 배제하십시오."
    ),
    (
        r"손실률\s*0%",
        "REJECT",
        "G8_FIN_ZERO_LOSS_RATE",
        "[자본시장법·금소법 방벽] '손실률 0%' 표방 금지.",
        "손실 위험을 솔직하게 기술하십시오."
    ),

    # 3. 사기성 리딩방 어투 및 시세조종 조장
    (
        r"VIP\s*(?:리딩|추천|정보)",
        "REJECT",
        "G8_FIN_VIP_LEADING",
        "[자본시장법 방벽] 불법 사기성 리딩방 어투 'VIP 리딩/추천' 감지 (자본시장법 위반 소지).",
        "사기성 리딩방 마케팅 용어를 전면 삭제하십시오."
    ),
    (
        r"급등주\s*(?:추천|대공개|포착|공개|발굴|무료)",
        "REJECT",
        "G8_FIN_SURGE_STOCK",
        "[자본시장법 방벽] 선동적 투기 조장 '급등주 추천/포착' 감지.",
        "투기 조장 어휘를 삭제하고 펀더멘털 및 매크로 지표 분석으로 전환하십시오."
    ),
    (
        r"특급\s*(?:호재|정보|재료)",
        "REJECT",
        "G8_FIN_SPECIAL_INSIDER_INFO",
        "[자본시장법 방벽] 사기성 미공개 정보 유혹 어투 '특급 호재/재료' 감지.",
        "객관적 공시 및 시장 뉴스 기반으로 서술하십시오."
    ),
    (
        r"무조건\s*(?:폭등|상승|상한가)",
        "REJECT",
        "G8_FIN_UNCONDITIONAL_SURGE",
        "[자본시장법 방벽] '무조건 폭등/상승/상한가' 선동적 과장 표현 감지.",
        "가격 변동을 확언하는 어투를 배제하십시오."
    ),
    (
        r"내일\s*(?:무조건\s*)?상한가",
        "REJECT",
        "G8_FIN_TOMORROW_UPPER_LIMIT",
        "[자본시장법 방벽] '내일 상한가' 허위 유혹 표현 감지.",
        "내일 상한가 표현을 삭제하십시오."
    ),
    (
        r"세력\s*(?:매집|입성|작전)(?:주)?",
        "REJECT",
        "G8_FIN_MARKET_MANIPULATION",
        "[자본시장법 방벽] '세력 매집/작전주' 등 시세조종 및 불법 투기 조장 어휘 감지 (자본시장법 제178조).",
        "세력/작전 관련 불법 투기 표현을 전면 삭제하십시오."
    ),
    (
        r"선취매(?:\s*완료|\s*종목)?",
        "REJECT",
        "G8_FIN_FRONT_RUNNING",
        "[자본시장법 방벽] 불법 선취매 표방 어투 감지 (자본시장법 불공정거래행위 소지).",
        "선취매 표현을 삭제하십시오."
    ),
    (
        r"단타\s*리딩방",
        "REJECT",
        "G8_FIN_LEADING_ROOM",
        "[자본시장법 방벽] '단타 리딩방' 등 불법 유사투자자문 어휘 감지.",
        "리딩방 홍보 및 유인 어휘를 삭제하십시오."
    ),
    (
        r"목표가\s*(?:찍고|도달\s*확정)",
        "REJECT",
        "G8_FIN_GUARANTEED_TARGET_PRICE",
        "[자본시장법 방벽] '목표가 도달 확정' 표방 감지.",
        "목표가 도달을 확언하지 마십시오."
    ),

    # 4. 미등록 투자자문 소지 표현
    (
        r"무료\s*(?:종목\s*)?상담",
        "REJECT",
        "G8_FIN_UNREGISTERED_ADVICE_CONSULT",
        "[자본시장법 제17조 위반] 미등록 투자자문 소지 '무료 종목 상담' 감지.",
        "개별 종목 상담 유도 문구를 삭제하십시오."
    ),
    (
        r"1:1\s*(?:투자\s*)?(?:리딩|자문|코칭|상담)",
        "REJECT",
        "G8_FIN_UNREGISTERED_1ON1",
        "[자본시장법 제17조 위반] 불법 '1:1 투자 리딩/자문' 표현 감지.",
        "1:1 투자 자문 어휘를 삭제하십시오."
    ),
    (
        r"(?:지금|오늘)\s*당장\s*(?:매수|매도)하십시오",
        "REJECT",
        "G8_FIN_URGENT_TRADE_ORDER",
        "[자본시장법 위반] 일방적 매매 지시 어투 감지.",
        "독자에게 특정 매매 행위를 강요하지 마십시오."
    ),
    (
        r"(?:무조건|반드시)\s*(?:풀매수|매수|매도)하세요",
        "REJECT",
        "G8_FIN_FORCED_TRADE_ORDER",
        "[자본시장법 위반] 단정적 매수/매도 권유 어투 감지.",
        "판단은 투자자 본인의 몫임을 존중하는 기술적 분석으로 서술하십시오."
    ),
    (
        r"종목\s*찍어드립니다",
        "REJECT",
        "G8_FIN_PICK_STOCK",
        "[자본시장법 위반] 불법 종목 추천 어투 감지.",
        "종목 찍어주기 식 어투를 배제하십시오."
    ),
]


class CapitalMarketsRule(BaseRule):
    """자본시장법 & 금융소비자보호법(금소법) 방벽 규칙 (Gate 8)"""

    rule_id = "G8_FIN_CAPITAL_MARKETS"
    gate_id = "GATE_8"
    gate_name = "자본시장법·금소법 방벽"
    description = "원금보장, 확정수익, 손실보전, VIP 리딩방, 시세조종, 1:1 자문 등 25대 금융 법령 위반 차단"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        in_code_block = False

        for idx, line in enumerate(ctx.lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            for pat, sev, r_id, msg, hint in CAPITAL_MARKETS_RULES:
                match = re.search(pat, line)
                if match:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=r_id,
                        severity=sev,
                        line_number=idx,
                        snippet=stripped[:100],
                        message=msg,
                        fix_hint=hint
                    ))

        return violations
