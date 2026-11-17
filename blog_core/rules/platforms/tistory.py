# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.tistory - Tistory Blog Platform Rules (softwin.tistory.com)
"""

import os
import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


TISTORY_OFFICIAL_CATEGORIES = [
    "프로그래밍 언어 & 패러다임",
    "컴퓨터 과학 핵심 기초",
    "네트워크 & 웹 통신 기술",
    "백엔드 & 서버 아키텍처",
    "프론트엔드 & 클라이언트",
    "데이터베이스 & 스토리지",
    "클라우드, DevOps & 인프라",
    "보안 & 인증 기술",
    "AI, 머신러닝 & 빅데이터",
    "소프트웨어 공학 & 아키텍처",
    "임베디드 & 차세대 기술",
    "실무 장애 트러블슈팅 (Post-Mortem)",
    "실무 장애 트러블슈팅"
]


class TistoryFrontmatterRule(BaseRule):
    """티스토리 필수 Frontmatter (visibility 등) 검증 규칙 (Gate 1)"""

    rule_id = "G1_TISTORY_REQ_FRONTMATTER"
    gate_id = "GATE_1"
    gate_name = "구조 및 메타데이터 무결성"
    description = "티스토리 필수 메타데이터 필드(visibility: public/private) 검증"
    platforms = ["tistory"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        if "visibility" not in ctx.fm_data or not ctx.fm_data["visibility"].strip():
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G1_REQ_FRONTMATTER",
                severity=self.default_severity,
                line_number=1,
                snippet="Missing key: 'visibility'",
                message="YAML Frontmatter에 필수 필드 'visibility'가 누락되었거나 비어 있습니다.",
                fix_hint="파일 최상단 Frontmatter에 'visibility: public' 또는 'visibility: private'을 명시하십시오."
            ))
        return violations


class TistoryCategoryRule(BaseRule):
    """티스토리 11대 마스터 카테고리 일치 검증 규칙 (Gate 6)"""

    rule_id = "G6_TISTORY_CATEGORY_MISMATCH"
    gate_id = "GATE_6"
    gate_name = "플랫폼별 특화 규격 검증"
    description = "티스토리 공식 11대 마스터 카테고리 및 트러블슈팅 카테고리 일치 검증"
    platforms = ["tistory"]
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "").strip()

        if category and category not in TISTORY_OFFICIAL_CATEGORIES:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=1,
                snippet=f"category: {category}",
                message=f"티스토리 11대 마스터 카테고리 또는 트러블슈팅 카테고리와 불일치할 수 있습니다. (지정: '{category}')",
                fix_hint="CATEGORIES.md의 공식 11대 카테고리 명칭과 일치하는지 확인하십시오."
            ))

        return violations


class TistoryTroubleshootingArtifactsRule(BaseRule):
    """티스토리 실무 장애 트러블슈팅 포스트 5대 아티팩트 검증 규칙 (Gate 4)"""

    rule_id = "G4_TISTORY_TROUBLESHOOTING_ARTIFACTS"
    gate_id = "GATE_4"
    gate_name = "실무 엔지니어링 5대 아티팩트 검증"
    description = "티스토리 트러블슈팅 포스트에 대한 5대 엔지니어링 아티팩트 검증"
    platforms = ["tistory"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        fname = os.path.basename(ctx.file_path).lower()
        category = ctx.fm_data.get("category", "").lower()
        title = ctx.fm_data.get("title", "").lower()

        is_trouble = (
            "trouble" in fname or
            "트러블슈팅" in category or
            "post-mortem" in category or
            "장애" in title or
            "트러블슈팅" in title
        )

        if not is_trouble:
            return violations

        code_blocks = ctx.code_blocks

        # 1. Raw Log 검증
        log_keywords = [
            "error", "fatal", "exception", "failed", "panic:", "oomkilled",
            "timeout", "http/1.1 5", "http/2 5", "stderr:", "dmesg:", "status code 5",
            "502 bad gateway", "504 gateway timeout", "http 502", "http 504", "status code 502", "status code 504",
            "traceback (most recent call last):", "connection refused", "broken pipe",
            "deadlock", "latest detected deadlock", "waiting for this lock", "we roll back",
            "[trace]", "[metric]", "[alert]", "[critical]", "saturation", "iops",
            "exit code 13", "exit code 137", "exit code 1", "exit code 255", "sigkill", "sigterm", "sigbus", "sigsegv",
            "cannot assign requested address", "eaddrnotavail", "upstream prematurely closed", "upstream timed out",
            "에러", "실패", "타임아웃", "예외", "데드락", "종료코드"
        ]
        has_raw_log = any(
            any(k in code.lower() for k in log_keywords)
            for _, code, _ in code_blocks
        )
        if not has_raw_log:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_RAW_LOG",
                severity="REJECT",
                line_number=0,
                snippet="No raw error stacktrace / kernel log block found in code blocks",
                message="[필수 아티팩트 결손] 날것의 시스템 에러 로그(Raw Log / Stacktrace) 블록이 존재하지 않습니다.",
                fix_hint="터미널이나 컨테이너 로그에서 발생한 실제 에러 로그 스택트레이스를 코드 블록으로 필수 삽입하십시오."
            ))

        # 2. Wrong Fix 검증
        wrong_fix_keywords = [
            "wrong fix", "wrong approach", "initial incorrect", "failed attempt", "what didn't work",
            "what doesn't work", "common missteps", "misstep", "common false fix", "false fix",
            "the flawed fix", "flawed fix", "anti-pattern", "antipattern", "common anti-patterns",
            "what we tried first", "dangerous workaround", "dangerous workarounds", "why naive",
            "naive fix", "naive attempt", "why it fails", "why this fails", "why it backfires",
            "오진", "잘못된 접근", "실패했던 시도", "처음 시도했던", "오판", "삽질", "효과가 없었다", "해결되지 않았다",
            "초기 접근", "임시방편", "처음에는", "기대와 달리", "오류를 잡지 못했다"
        ]
        body_lower = ctx.body.lower()
        if not any(k in body_lower for k in wrong_fix_keywords):
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_WRONG_FIX",
                severity="REJECT",
                line_number=0,
                snippet="No 'Wrong Fix' or failed troubleshooting attempt mentioned",
                message="[필수 아티팩트 결손] 처음 시도했으나 실패했던 잘못된 접근(Wrong Fix / 오진) 섹션이 누락되었습니다.",
                fix_hint="처음에는 왜 해결되지 않았는지 현업의 오진/삽질 과정을 반드시 포함하십시오."
            ))

        # 3. Unified Diff 검증
        has_unified_diff = any(
            lang.lower() == "diff" or (
                bool(re.search(r"^\s*-\s+", code, re.MULTILINE)) and
                bool(re.search(r"^\s*\+\s+", code, re.MULTILINE))
            )
            for lang, code, _ in code_blocks
        )
        if not has_unified_diff:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_UNIFIED_DIFF",
                severity="REJECT",
                line_number=0,
                snippet="No unified diff (- / +) code block found",
                message="[필수 아티팩트 결손] Before/After 변경 내역을 명확히 대조하는 Unified Diff 블록이 없습니다.",
                fix_hint="```diff 형식으로 수정 전(-)과 수정 후(+)가 한눈에 대비되는 설정/코드 diff 블록을 삽입하십시오."
            ))

        return violations
