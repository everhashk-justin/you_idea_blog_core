# -*- coding: utf-8 -*-
"""
blog_core.rules.common.legal_kogl - Gate 8: Korea Open Government License (KOGL) Attribution Compliance
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


POLICY_TOPIC_PATTERNS = [
    r"정부\s*(?:지원금|정책|보조금)",
    r"복지\s*(?:지원금|정책|급여|혜택)",
    r"청년도약계좌",
    r"청년내일저축계좌",
    r"국민기초생활보장",
    r"근로장려금",
    r"자녀장려금",
    r"소상공인\s*(?:지원금|손실보전금|방역지원금)",
    r"국민취업지원제도",
    r"긴급복지지원",
    r"보건복지부",
    r"고용노동부",
    r"국세청\s*(?:환급금|연말정산)",
    r"정부24",
    r"복지로",
    r"행정안전부",
    r"중소벤처기업부",
]

KOGL_ATTRIBUTION_PATTERNS = [
    r"공공누리",
    r"KOGL",
    r"제[1-4]유형",
    r"공공저작물",
    r"출처\s*:\s*(?:대한민국\s*)?정책브리핑",
    r"출처\s*:\s*공공데이터포털",
    r"출처\s*:\s*(?:보건복지부|고용노동부|국세청|행정안전부|정부24|복지로|기획재정부|금융위원회|중소벤처기업부)",
    r"본\s*저작물은\s*.*?(?:공공누리|출처표시)",
    r"공공기관\s*저작물",
]


class KoglCopyrightRule(BaseRule):
    """공공누리(KOGL) 저작권 출처 표기 의무 검증 규칙 (Gate 8)"""

    rule_id = "G8_KOGL_MISSING_ATTRIBUTION"
    gate_id = "GATE_8"
    gate_name = "공공누리(KOGL) 출처 표기 방벽"
    description = "정부 정책/복지 지원금 포스팅에서 공공누리(KOGL) 출처 미표기 차단"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "").strip()
        title = ctx.fm_data.get("title", "").strip()
        norm_path = ctx.file_path.replace("\\", "/").lower()

        is_policy_content = (
            any(k in category for k in ["정부 정책", "복지 지원금", "복지정책", "행정 절차", "공공누리", "공공"]) or
            "solidlog" in norm_path or
            any(re.search(pat, title) for pat in POLICY_TOPIC_PATTERNS) or
            (
                any(re.search(pat, ctx.body) for pat in POLICY_TOPIC_PATTERNS) and
                bool(re.search(r"(?:신청\s*자격|지원\s*대상|소득\s*기준|신청\s*기간|신청\s*방법|지급\s*방식|선정\s*기준|구비\s*서류)", ctx.body))
            )
        )

        if is_policy_content:
            has_kogl_attribution = any(re.search(pat, ctx.body) for pat in KOGL_ATTRIBUTION_PATTERNS)
            if not has_kogl_attribution:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet="Government policy or welfare content found without KOGL attribution",
                    message="[공공누리(KOGL) 출처 표기 방벽] 정부 정책, 복지 지원금 또는 공공기관 저작물 정보가 포함되어 있으나, 저작권법 제37조 및 공공누리(KOGL) 출처 표기 의무가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)' 또는 '본 저작물은 공공누리 제1유형에 따라 작성되었습니다.'를 명시하십시오."
                ))

        return violations
