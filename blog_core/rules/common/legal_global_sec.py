# -*- coding: utf-8 -*-
"""
blog_core.rules.common.legal_global_sec - Gate 8: SEC Compliance & Global Financial Regulations
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


GLOBAL_FINANCIAL_RULES = [
    # 1. Guaranteed Returns & Risk-Free Claims
    (
        r"(?i)(?<!no\s)(?<!not\s)\bguaranteed\s+(?:returns?|profits?|yields?|income|gains?)\b",
        "REJECT",
        "G8_GLOBAL_GUARANTEED_RETURNS",
        "[SEC Global Compliance] Illegal guaranteed returns claim detected (US SEC Rule 10b-5 / FINRA Rule 2210). All securities investments carry market risk.",
        "Remove any guarantee of returns and state potential volatility and market risks objectively."
    ),
    (
        r"(?i)\brisk-free\s+(?:profits?|returns?|yields?|investments?)\b",
        "REJECT",
        "G8_GLOBAL_RISK_FREE_PROFIT",
        "[SEC Global Compliance] Misleading 'risk-free profit/return' claim detected.",
        "Eliminate 'risk-free' claims and provide balanced risk disclosure."
    ),
    (
        r"(?i)\b100%\s*(?:guaranteed|win\s*rate|profit|success\s*rate)\b",
        "REJECT",
        "G8_GLOBAL_100PCT_WIN_RATE",
        "[SEC Global Compliance] Unrealistic '100% win rate / profit' claim detected.",
        "Remove false certainty claims regarding trading performance."
    ),
    (
        r"(?i)\bcannot\s+lose(?:\s+money)?\b",
        "REJECT",
        "G8_GLOBAL_CANNOT_LOSE",
        "[SEC Global Compliance] Deceptive 'cannot lose money' claim detected.",
        "Acknowledge the risk of financial loss in all market conditions."
    ),
    (
        r"(?i)\bzero\s+risk\s+invest(?:ing|ment)\b",
        "REJECT",
        "G8_GLOBAL_ZERO_RISK",
        "[SEC Global Compliance] 'Zero risk investment' claim detected.",
        "Remove zero risk claim and state actual risk parameters."
    ),
    (
        r"(?i)\bguaranteed\s+(?:to\s+double|10x|100x)\b",
        "REJECT",
        "G8_GLOBAL_GUARANTEED_MULTIPLIER",
        "[SEC Global Compliance] Fraudulent multiplier guarantee ('guaranteed 10x') detected.",
        "Remove multiplier promises."
    ),
    (
        r"(?i)\bunconditional\s+returns?\b",
        "REJECT",
        "G8_GLOBAL_UNCONDITIONAL_RETURNS",
        "[SEC Global Compliance] 'Unconditional return' claim detected.",
        "Remove unconditional return statements."
    ),

    # 2. Illegal Investment Advice / Stock Solicitation / Market Manipulation
    (
        r"(?i)\bbuy\s+this\s+stock\s+(?:now|today|immediately)\b",
        "REJECT",
        "G8_GLOBAL_URGENT_BUY_CALL",
        "[SEC Compliance] Unregistered investment solicitation / urgent trade command detected (Investment Advisers Act of 1940).",
        "Present objective fundamental and quantitative analysis without direct buy/sell imperatives."
    ),
    (
        r"(?i)\bsell\s+this\s+stock\s+(?:now|today|immediately)\b",
        "REJECT",
        "G8_GLOBAL_URGENT_SELL_CALL",
        "[SEC Compliance] Direct sell command detected.",
        "Replace trading commands with neutral valuation commentary."
    ),
    (
        r"(?i)\bguaranteed\s+target\s+price\b",
        "REJECT",
        "G8_GLOBAL_TARGET_PRICE_GUARANTEE",
        "[SEC Compliance] Deceptive 'guaranteed target price' claim detected.",
        "State price targets as analyst estimates with associated uncertainty."
    ),
    (
        r"(?i)\bpump\s+and\s+dump\b",
        "REJECT",
        "G8_GLOBAL_PUMP_AND_DUMP",
        "[SEC Rule 10b-5] Pump-and-dump market manipulation language detected.",
        "Remove all references promoting artificial volume or price inflation."
    ),
    (
        r"(?i)\binsider\s+(?:tip|trading|leak)\b",
        "REJECT",
        "G8_GLOBAL_INSIDER_TIP",
        "[SEC Rule 10b5-1] Illegal insider information claim detected.",
        "Rely strictly on publicly disclosed SEC filings and verifiable market data."
    ),
    (
        r"(?i)\byou\s+must\s+buy\s+this\b",
        "REJECT",
        "G8_GLOBAL_MUST_BUY",
        "[SEC Compliance] Coercive trade recommendation detected.",
        "Frame conclusions as analytical insights rather than mandates."
    ),
    (
        r"(?i)\bguaranteed\s+to\s+skyrocket\b",
        "REJECT",
        "G8_GLOBAL_SKYROCKET_CLAIM",
        "[SEC Compliance] Sensationalist stock pumping language detected.",
        "Remove sensationalist hype."
    ),
    (
        r"(?i)\bexclusive\s+(?:trading\s+signal|stock\s+alert)\b",
        "REJECT",
        "G8_GLOBAL_EXCLUSIVE_SIGNAL",
        "[SEC Compliance] Boiler-room style 'exclusive trading signal' lure detected.",
        "Remove boiler-room solicitation language."
    ),
]


class SecGlobalFinanceRule(BaseRule):
    """영문 SEC 글로벌 금융 규제 방벽 규칙 (Gate 8)"""

    rule_id = "G8_GLOBAL_SEC_FINANCE"
    gate_id = "GATE_8"
    gate_name = "영문 글로벌 금융 규제 방벽 (SEC Compliance)"
    description = "guaranteed returns, urgent buy calls, 100% win rate 등 15대 SEC 글로벌 금융 규제 위반 차단"
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

            for pat, sev, r_id, msg, hint in GLOBAL_FINANCIAL_RULES:
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
