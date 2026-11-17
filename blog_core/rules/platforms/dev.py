# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.dev - Dev Blog Platform Rules (dev.ideaspot360.com)
"""

import os
import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


DEV_OFFICIAL_CATEGORIES = [
    "Cloud & DevOps",
    "Database & Storage",
    "Systems & Networking"
]


class DevCategoryRule(BaseRule):
    """개발 블로그 공식 카테고리 일치 검증 규칙 (Gate 6)"""

    rule_id = "G6_DEV_CATEGORY_MISMATCH"
    gate_id = "GATE_6"
    gate_name = "플랫폼별 특화 규격 검증"
    description = "개발 블로그 공식 카테고리(Cloud & DevOps, Database & Storage, Systems & Networking) 일치 검증"
    platforms = ["dev"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "").strip()

        if category not in DEV_OFFICIAL_CATEGORIES:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=1,
                snippet=f"category: {category}",
                message=f"개발 블로그 공식 4대 카테고리와 불일치합니다. (허용: {', '.join(DEV_OFFICIAL_CATEGORIES)})",
                fix_hint="Frontmatter의 category를 'Cloud & DevOps', 'Database & Storage', 'Systems & Networking', 'AI & Machine Learning' 중 하나로 정확히 일치시키십시오."
            ))

        return violations


class DevTroubleshootingArtifactsRule(BaseRule):
    """실무 엔지니어링 5대 아티팩트 검증 규칙 (Gate 4)"""

    rule_id = "G4_DEV_ENGINEERING_ARTIFACTS"
    gate_id = "GATE_4"
    gate_name = "실무 엔지니어링 5대 아티팩트 검증"
    description = "Raw Log, Wrong Fix, Unified Diff, Root Cause, CLI Verification 등 5대 아티팩트 검증"
    platforms = ["dev"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        code_blocks = ctx.code_blocks

        # 1. Raw Log 검증 (에러/로그 패턴 존재 여부)
        has_raw_log = False
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
        for lang, code, _ in code_blocks:
            code_lower = code.lower()
            if any(k in code_lower for k in log_keywords):
                has_raw_log = True
                break

        if not has_raw_log:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_RAW_LOG",
                severity="REJECT",
                line_number=0,
                snippet="No raw error stacktrace / kernel log block found in code blocks",
                message="[필수 아티팩트 결손] 날것의 시스템 에러 로그(Raw Log / Stacktrace) 블록이 존재하지 않습니다.",
                fix_hint="터미널이나 컨테이너 로그에서 발생한 실제 에러 로그 스택트레이스(Error, Exception, Failed 등)를 코드 블록으로 필수 삽입하십시오."
            ))

        # 2. Wrong Fix (오진/실패한 시도) 검증
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
        has_wrong_fix = any(k in body_lower for k in wrong_fix_keywords)

        if not has_wrong_fix:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_WRONG_FIX",
                severity="REJECT",
                line_number=0,
                snippet="No 'Wrong Fix' or failed troubleshooting attempt mentioned",
                message="[필수 아티팩트 결손] 처음 시도했으나 실패했던 잘못된 접근(Wrong Fix / 오진) 섹션이 누락되었습니다.",
                fix_hint="정답으로 직행하지 말고, '처음에는 X 설정을 변경했으나 왜 해결되지 않았는지' 현업의 오진/삽질 과정을 반드시 포함하십시오."
            ))

        # 3. Unified Diff (Before/After) 검증
        has_unified_diff = False
        for lang, code, _ in code_blocks:
            if lang.lower() == "diff":
                has_unified_diff = True
                break
            has_minus = bool(re.search(r"^\s*-\s+", code, re.MULTILINE))
            has_plus = bool(re.search(r"^\s*\+\s+", code, re.MULTILINE))
            if has_minus and has_plus:
                has_unified_diff = True
                break

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

        # 4. Root Cause 분석 섹션 검증
        root_cause_keywords = [
            "root cause", "architectural cause", "kernel mechanism", "deep dive into",
            "원인 분석", "근본 원인", "동작 기전", "내부 동작", "발생 원인"
        ]
        has_root_cause = any(k in body_lower for k in root_cause_keywords)
        if not has_root_cause:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_ROOT_CAUSE",
                severity="WARNING",
                line_number=0,
                snippet="No explicit Root Cause / Architecture analysis header found",
                message="[개선 권장] 근본 원인(Root Cause)이나 커널/런타임 내부 동작 기전에 대한 심층 분석 헤더가 미흡합니다.",
                fix_hint="'## Root Cause Analysis' 또는 '## 장애의 근본 원인 분석' 섹션을 두어 내부 아키텍처 레벨의 원인을 설명하십시오."
            ))

        # 5. Verification CLI 검증
        cli_commands = ["curl", "kubectl", "ss", "netstat", "tcpdump", "strace", "sysctl", "dmesg", "systemctl", "journalctl", "vmstat", "sar", "dig", "ping"]
        has_cli_verify = False
        for lang, code, _ in code_blocks:
            code_lower = code.lower()
            if any(re.search(rf"\b{cmd}\b", code_lower) for cmd in cli_commands):
                has_cli_verify = True
                break

        if not has_cli_verify:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name=self.gate_name,
                rule_id="G4_MISSING_CLI_VERIFICATION",
                severity="WARNING",
                line_number=0,
                snippet="No verification CLI command (curl, ss, kubectl, sysctl, etc.) found in code blocks",
                message="[개선 권장] 수정 사항을 현장에서 즉시 검증할 수 있는 CLI 확인 명령어가 없습니다.",
                fix_hint="수정 후 상태를 검증하는 CLI 명령어(예: curl -v, ss -s, kubectl describe 등) 코드 블록을 추가하십시오."
            ))

        return violations
