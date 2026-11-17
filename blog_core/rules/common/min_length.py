# -*- coding: utf-8 -*-
"""
blog_core.rules.common.min_length - Gate 1: Minimum Content Length Requirements (EN & KO)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class MinLengthRule(BaseRule):
    """콘텐츠 최소 분량 검증 규칙 (글로벌 영문 백서 700단어, 국내 국문 기술블로그 공백제외 1,200자)"""

    rule_id = "G1_MIN_LENGTH"
    gate_id = "GATE_1"
    gate_name = "구조 및 마크다운 무결성"
    description = "플랫폼에 따른 최소 본문 분량(영문 700단어, 국문 공백제외 1,200자) 충족 검증"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []

        # 홈 랜딩 페이지(Starlight splash 또는 index)는 최소 분량 검사 제외
        if ctx.fm_data.get("template") == "splash" or ctx.file_path.replace("\\", "/").endswith(("/index.md", "/index.mdx", "index.md", "index.mdx")):
            return []

        if ctx.platform == "dev":
            word_count = len(re.findall(r"\b[a-zA-Z0-9_\-]+\b", ctx.body))
            if word_count < 700:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G1_MIN_LENGTH_EN",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=f"Current word count: {word_count} words",
                    message=f"글로벌 기술 백서의 최소 분량(700단어)에 미달합니다. (현재: {word_count}단어)",
                    fix_hint="에러 로그, 근본 커널 원인, 실패한 시도, 재현 CLI를 상세히 보강하여 전문성을 확보하십시오."
                ))
        else:
            char_count = len(ctx.body.replace(" ", "").replace("\n", ""))
            if char_count < 1200:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G1_MIN_LENGTH_KO",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=f"Current char count: {char_count} chars (excl. spaces)",
                    message=f"국내 기술 블로그 최소 분량(공백 제외 1,200자)에 미달합니다. (현재: {char_count}자)",
                    fix_hint="충실한 기술적 설명과 단계별 예시, 비유를 보강하십시오."
                ))

        return violations
