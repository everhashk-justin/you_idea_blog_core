# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.gear - Gear & Hardware Blog Platform Rules (gear.ideaspot360.com)
"""

from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class GearFrontmatterRule(BaseRule):
    """기어 블로그 Frontmatter 메타데이터 검증 규칙 (Gate 1)"""

    rule_id = "G1_GEAR_REQ_FRONTMATTER"
    gate_id = "GATE_1"
    gate_name = "구조 및 메타데이터 무결성"
    description = "기어 블로그의 경우 'category' 대신 'series' 필드가 있어도 허용"
    platforms = ["gear"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        has_category = bool(ctx.fm_data.get("category", "").strip())
        has_series = bool(ctx.fm_data.get("series", "").strip())

        if not has_category and not has_series:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G1_REQ_FRONTMATTER",
                severity=self.default_severity,
                line_number=1,
                snippet="Missing both 'category' and 'series'",
                message="기어 블로그 Frontmatter에 'category' 또는 'series' 필드가 누락되었습니다.",
                fix_hint="Frontmatter에 'category: <값>' 또는 'series: <시리즈명>'을 명시하십시오."
            ))

        return violations
