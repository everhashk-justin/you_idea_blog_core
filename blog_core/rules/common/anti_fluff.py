# -*- coding: utf-8 -*-
"""
blog_core.rules.common.anti_fluff - Gate 5: Elimination of Excessive Intro Fluff and Redundant Recap
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class ExcessiveIntroFluffRule(BaseRule):
    """서론 사족 비율 및 기술 밀도 검증 규칙 (Gate 5)"""

    rule_id = "G5_EXCESSIVE_INTRO_FLUFF"
    gate_id = "GATE_5"
    gate_name = "사족 & 중언부언 차단"
    description = "첫 번째 헤더 이전의 도입부가 250단어 초과 및 전체 본문의 30%를 초과하는 사족 차단"
    platforms = None
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        lines = ctx.body.splitlines()

        intro_lines = []
        for line in lines:
            if re.match(r"^#{1,3}\s+", line.strip()):
                break
            intro_lines.append(line)

        intro_text = "\n".join(intro_lines).strip()
        intro_words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", intro_text)
        body_words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", ctx.body)

        if len(body_words) > 0 and len(intro_words) > 250:
            intro_ratio = len(intro_words) / len(body_words)
            if intro_ratio > 0.30:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=1,
                    snippet=intro_text[:120] + "...",
                    message=f"도입부 사족 비율이 전체 본문의 {int(intro_ratio * 100)}%로 과도하게 깁니다. ({len(intro_words)}단어)",
                    fix_hint="원론적인 배경 설명을 대폭 축소하고, 독자가 첫 화면에서 즉시 핵심 문제와 아키텍처를 파악할 수 있도록 바로 본론 헤더를 전진 배치하십시오."
                ))

        return violations


class ParrotConclusionRule(BaseRule):
    """판에 박힌 결론 재요약(Parrot Conclusion) 패턴 검증 규칙 (Gate 5)"""

    rule_id = "G5_PARROT_CONCLUSION"
    gate_id = "GATE_5"
    gate_name = "사족 & 중언부언 차단"
    description = "본문 결론부의 판에 박힌 단순 요약 반복 어구 차단"
    platforms = None
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        lines = ctx.body.splitlines()
        last_section = "\n".join(lines[-40:]) if len(lines) >= 40 else ctx.body

        parrot_patterns = [
            (r"(지금까지\s+살펴본\s+바와\s+같이|위에서\s+살펴보았듯이|앞서\s+설명한\s+것처럼)", "결론부 상투적 중언부언"),
            (r"(as\s+we\s+have\s+seen\s+above|to\s+recap\s+what\s+we\s+discussed|in\s+this\s+article,\s*we\s+have\s+covered)", "Repetitive conclusion recap")
        ]

        for pattern, label in parrot_patterns:
            match = re.search(pattern, last_section, re.IGNORECASE)
            if match:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet=match.group(0),
                    message=f"단순 반복 재요약 패턴({label})이 감지되었습니다.",
                    fix_hint="앞서 설명한 내용을 기계적으로 다시 요약하지 말고, 현업 실무자를 위한 '운영 주의점'이나 '모니터링 알람 임계치 설정 팁'으로 실용적 가치를 더하십시오."
                ))

        return violations


class JaccardRedundancyRule(BaseRule):
    """자카드 유사도 기반 결론부 복제 검증 규칙 (Gate 5)"""

    rule_id = "G5_JACCARD_REDUNDANCY"
    gate_id = "GATE_5"
    gate_name = "사족 & 중언부언 차단"
    description = "결론부와 본문 섹션 간 자카드 유사도가 65% 이상으로 단순 복제된 경우 경고"
    platforms = None
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        sections = re.split(r"\n#{1,3}\s+", ctx.body)
        if len(sections) >= 3:
            conclusion_text = sections[-1]
            stop_words = {
                "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of",
                "this", "that", "is", "was", "are", "were", "it", "as", "be", "from", "we", "our",
                "you", "your", "will", "can", "not", "if", "when", "then", "into", "which", "all"
            }
            c_words = set(
                w.lower() for w in re.findall(r"[a-zA-Z0-9_\-]+", conclusion_text)
                if len(w) > 2 and w.lower() not in stop_words
            )
            if len(c_words) >= 20:
                for b_idx, b_sec in enumerate(sections[1:-1], start=1):
                    b_words = set(
                        w.lower() for w in re.findall(r"[a-zA-Z0-9_\-]+", b_sec)
                        if len(w) > 2 and w.lower() not in stop_words
                    )
                    if len(b_words) >= 20:
                        intersection = len(c_words & b_words)
                        union = len(c_words | b_words)
                        jaccard = intersection / union if union > 0 else 0.0
                        if jaccard >= 0.65:
                            violations.append(Violation(
                                gate_id=self.gate_id,
                                gate_name=self.gate_name,
                                rule_id=self.rule_id,
                                severity=self.default_severity,
                                line_number=0,
                                snippet=f"Section {b_idx} vs Conclusion (Jaccard: {jaccard:.2f})",
                                message=f"결론부 내용이 본문 {b_idx}번 섹션과 자카드 유사도 {int(jaccard*100)}%로 지나치게 중복됩니다.",
                                fix_hint="결론부에서 본문 텍스트를 단순 복제/요약하지 말고, 차별화된 런북 및 체크리스트 가치를 제시하십시오."
                            ))
                            break

        return violations
