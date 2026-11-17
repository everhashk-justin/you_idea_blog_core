# -*- coding: utf-8 -*-
"""
blog_core.rules.common.markdown_structure - Gate 1: Structure, Frontmatter, and Markdown Syntax Integrity
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class FrontmatterRequiredRule(BaseRule):
    """YAML Frontmatter 필수 키 검증 규칙"""

    rule_id = "G1_REQ_FRONTMATTER"
    gate_id = "GATE_1"
    gate_name = "구조 및 메타데이터 무결성"
    description = "YAML Frontmatter에 필수 메타데이터 필드(title, tags, category 등) 존재 여부 검증"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        required_keys = ["title", "tags"]

        if ctx.platform == "gear":
            # gear 플랫폼은 category 대신 series 필드 허용
            if "category" not in ctx.fm_data and "series" not in ctx.fm_data:
                required_keys.append("category")
        else:
            required_keys.append("category")

        for k in required_keys:
            if k not in ctx.fm_data or not ctx.fm_data[k].strip():
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet=f"Missing key: '{k}'",
                    message=f"YAML Frontmatter에 필수 필드 '{k}'가 누락되었거나 비어 있습니다.",
                    fix_hint=f"파일 최상단 Frontmatter에 '{k}: <값>'을 명시하십시오."
                ))

        return violations


class UnclosedCodeBlockRule(BaseRule):
    """코드 블록 백틱(```) 짝 맞춤 무결성 검증 규칙"""

    rule_id = "G1_UNCLOSED_CODEBLOCK"
    gate_id = "GATE_1"
    gate_name = "구조 및 마크다운 무결성"
    description = "열린 코드 블록(```)이 정상적으로 닫혔는지 백틱 개수 홀짝 검증"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        backtick_matches = [
            l for l in ctx.content.splitlines()
            if l.strip().startswith("```") and not l.strip().startswith("+```") and not l.strip().startswith("-```")
        ]
        if len(backtick_matches) % 2 != 0:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet=f"Total backtick rows: {len(backtick_matches)}",
                message="열린 코드 블록(```)이 닫히지 않았습니다. 백틱 개수가 홀수입니다.",
                fix_hint="마크다운 내 모든 ``` 블록이 정상적으로 닫혔는지 확인하십시오."
            ))
        return violations


class UnclosedMathBlockRule(BaseRule):
    """수식 디스플레이 블록($$) 짝 맞춤 무결성 검증 규칙"""

    rule_id = "G1_UNCLOSED_MATH_BLOCK"
    gate_id = "GATE_1"
    gate_name = "구조 및 마크다운 무결성"
    description = "수식 블록($$)의 짝이 맞지 않아 홀수 개수인 경우 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        dollar_block_count = ctx.content.count("$$")
        if dollar_block_count % 2 != 0:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet=f"Total '$$' occurrences: {dollar_block_count}",
                message="수식 디스플레이 블록($$)이 올바르게 닫히지 않았습니다. '$$' 개수가 홀수입니다.",
                fix_hint="마크다운 내 모든 수식 블록($$)이 정상적으로 열리고 닫혔는지 확인하십시오."
            ))
        return violations


class KatexMultilineSyntaxRule(BaseRule):
    """KaTeX 멀티라인 수식 블록 내 개행 문법 검증 규칙"""

    rule_id = "G1_KATEX_MULTILINE_SYNTAX"
    gate_id = "GATE_1"
    gate_name = "구조 및 마크다운 무결성"
    description = "KaTeX 수식 블록($$) 내 줄바꿈 시 '\\\\' 없이 줄바꿈되어 렌더링 붕괴를 유발하는 문법 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        math_matches = re.finditer(r"\$\$(.*?)\$\$", ctx.content, re.DOTALL)
        for mm in math_matches:
            raw_math = mm.group(1).strip()
            if "\n" in raw_math:
                lines = [l.strip() for l in raw_math.split("\n") if l.strip()]
                has_env = any(env in raw_math for env in [r"\begin{", r"\end{", r"\matrix", r"\cases"])
                if not has_env and len(lines) > 1:
                    has_invalid_break = any(not l.endswith(r"\\") for l in lines[:-1])
                    if has_invalid_break:
                        line_no = ctx.content[:mm.start()].count("\n") + 1
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id=self.rule_id,
                            severity=self.default_severity,
                            line_number=line_no,
                            snippet=raw_math[:80] + "...",
                            message="KaTeX 수식 블록($$) 내부에 '\\\\' 없이 줄바꿈된 수식이 포함되어 있어 렌더링 붕괴(ParseError)를 유발합니다.",
                            fix_hint="각 수식을 독립된 단일 라인 $$ 블록으로 분리하거나, \\begin{aligned} 환경을 명시하십시오."
                        ))
        return violations
