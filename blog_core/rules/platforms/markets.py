# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.markets - Global Macro & Markets Platform Rules (markets.ideaspot360.com)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


GLOBAL_DISCLAIMER_PATTERNS = [
    r"(?i)\bdisclaimer\b",
    r"(?i)\bnot\s+financial\s+advice\b",
    r"(?i)\bnot\s+an\s+investment\s+advice\b",
    r"(?i)\binformational\s+purposes\s+only\b",
    r"(?i)\beducational\s+purposes\s+only\b",
    r"(?i)\bdo\s+your\s+own\s+research\b",
    r"(?i)\bpast\s+performance\s+(?:is\s+no|does\s+not)\s+guarantee\b",
    r"(?i)\bconsult\s+a\s+licensed\s+financial\s+advisor\b",
    r"(?i)\bfor\s+research\s+purposes\s+only\b",
    r"(?i)\brisk\s+of\s+loss\b",
]


class MarketsDisclaimerRule(BaseRule):
    """영문 글로벌 금융/매크로 포스팅 필수 투자 면책고지(Disclaimer) 검증 규칙 (Gate 8)"""

    rule_id = "G8_GLOBAL_MISSING_DISCLAIMER"
    gate_id = "GATE_8"
    gate_name = "영문 글로벌 금융 규제 방벽 (SEC Compliance)"
    description = "글로벌 매크로·증시 블로그(markets) 필수 영문 투자 면책문구(Disclaimer) 강제"
    platforms = ["markets"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        has_global_disclaimer = any(re.search(pat, ctx.body) for pat in GLOBAL_DISCLAIMER_PATTERNS)

        if not has_global_disclaimer:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet="No global financial disclaimer found in English financial content",
                message="[SEC Global Compliance] English financial/market article lacks a mandatory global investment disclaimer.",
                fix_hint="Add standard disclaimer at the bottom: 'Disclaimer: This article is for informational and educational purposes only and does not constitute financial, investment, or legal advice. Past performance is not indicative of future results.'"
            ))

        return violations
