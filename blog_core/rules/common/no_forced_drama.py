# -*- coding: utf-8 -*-
"""
blog_core.rules.common.no_forced_drama - Gate 3: Elimination of Forced Drama and Fake Panic Storytelling
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


FORCED_DRAMA_PATTERNS_KO = [
    (r"새벽\s*[0-9]+시(\s*[0-9]+분)?", "REJECT",
     "억지 타임스탬프('새벽 X시') 감지. 3류 소설식 시간 연출을 배제하고 담백한 모니터링 현상(예: '프로덕션 API 게이트웨이 504 스파이크')으로 기술하십시오."),
    (r"새벽\s*한\s*가운데", "REJECT", "작위적인 시간적 배경 묘사 감지."),
    (r"비상\s*(호출|알람|연락)이\s*(울렸다|울려\s*퍼졌다)", "REJECT", "억지 위기 상황 소설화 감지. 실제 모니터링 메트릭 및 알람 룰을 명시하십시오."),
    (r"(등줄기|이마|손)에\s*(식은땀|땀)이\s*(흘렀다|흘러내렸다|송골송골)", "REJECT", "신체 반응 과장 묘사('식은땀') 감지. 엔지니어링 문서에 부적합합니다."),
    (r"(머릿속|머리속)이\s*하얘(졌다|졌다)", "REJECT", "감정적 과장 묘사('머릿속이 하얘졌다') 감지."),
    (r"정신이\s*아득해(졌다|졌다)", "REJECT", "감정적 과장 묘사('정신이 아득해졌다') 감지."),
    (r"패닉에\s*빠(졌다|졌다)", "REJECT", "소설식 연출('패닉에 빠졌다') 감지."),
    (r"심장이\s*(덜컥|멎는|쿵쾅)", "REJECT", "신체 반응 과장 묘사 감지."),
    (r"피가\s*거꾸로\s*솟", "REJECT", "극단적 과장 묘사 감지."),
]

FORCED_DRAMA_PATTERNS_EN = [
    (r"\b(2|3|4|5)\s*(?:am|a\.m\.)\b", "REJECT",
     "Forced drama timestamp ('3 AM') detected. Replace fake emergency storytelling with direct engineering context (e.g., 'During peak ingress traffic...')."),
    (r"\bmiddle of the night\b", "REJECT", "Forced dramatic narrative setting detected."),
    (r"\bpagerduty (alert|notification) (woke|buzzed|screamed)\b", "REJECT", "Cliché PagerDuty wake-up story detected."),
    (r"\bcold sweat\b", "REJECT", "Exaggerated physical reaction ('cold sweat') detected."),
    (r"\bheart sank\b", "REJECT", "Dramatic storytelling phrase ('heart sank') detected."),
    (r"\bpanic ensued\b", "REJECT", "Melodramatic phrase ('panic ensued') detected."),
    (r"\bfrantic (debugging|scramble|effort)\b", "REJECT", "Melodramatic phrase ('frantic scramble') detected."),
    (r"\bnightmare scenario\b", "REJECT", "Sensationalist phrase ('nightmare scenario') detected."),
]


class NoForcedDramaRule(BaseRule):
    """억지 스토리 & 작위적 연출 차단 규칙 (Gate 3)"""

    rule_id = "G3_FORCED_DRAMA"
    gate_id = "GATE_3"
    gate_name = "억지 스토리 & 작위적 연출 차단"
    description = "새벽 X시 알람, 식은땀, 패닉 등 3류 소설식 작위적 위기 연출 패턴 차단 (코드 블록 제외)"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        is_english = ctx.is_english()
        patterns = FORCED_DRAMA_PATTERNS_EN if is_english else FORCED_DRAMA_PATTERNS_KO

        in_code_block = False
        for idx, line in enumerate(ctx.lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            for pattern, severity, msg in patterns:
                match = re.search(pattern, line, re.IGNORECASE if is_english else 0)
                if match:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=severity,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=msg,
                        fix_hint="가짜 위기 스토리(새벽 알람, 식은땀, 패닉 등)를 즉시 삭제하고, '실제 프로덕션에서 발생한 모니터링 수치/장애 증상'으로 객관화하십시오."
                    ))

        return violations
