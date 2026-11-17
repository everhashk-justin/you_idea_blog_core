# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.stock - Stock & Context Trading Blog Platform Rules (stock.ideaspot360.com)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


KO_FINANCIAL_DISCLAIMER_PATTERNS = [
    r"투자\s*(?:유의사항|경고|참고)",
    r"면책\s*(?:고지|문구)",
    r"투자를?\s*(?:권유|자문|추천|판단|책임)",
    r"권유가\s*아닙",
    r"자문이\s*아닙",
    r"추천이\s*아닙",
    r"원금\s*손실",
    r"손실\s*(?:의\s*)?위험",
    r"본\s*(?:글|포스팅|아티클|자료|콘텐츠)은?는?\s*.*?(?:참고|정보\s*제공)",
    r"정보\s*제공\s*목적",
    r"투자\s*결정은\s*본인",
    r"투자의\s*책임은\s*(?:투자자|본인)",
    r"금융소비자보호법",
    r"금소법",
]


class StockDisclaimerRule(BaseRule):
    """맥락트레이딩 국문 증시 블로그 필수 투자 유의사항 및 면책고지 검증 규칙 (Gate 8)"""

    rule_id = "G8_FIN_MISSING_DISCLAIMER"
    gate_id = "GATE_8"
    gate_name = "자본시장법·금소법 방벽"
    description = "맥락트레이딩 국문 증시 블로그(stock) 필수 투자 면책고지(Disclaimer) 강제"
    platforms = ["stock"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        has_fin_disclaimer = any(re.search(p, ctx.body) for p in KO_FINANCIAL_DISCLAIMER_PATTERNS)

        if not has_fin_disclaimer:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet="No investment disclaimer found in financial content",
                message="[자본시장법·금소법 방벽] 금융/증시/재테크 관련 포스팅 최하단에 필수적인 '투자 유의사항 및 면책고지(Disclaimer)'가 누락되었습니다.",
                fix_hint="포스팅 최하단에 '본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.'를 명시하십시오."
            ))

        return violations
