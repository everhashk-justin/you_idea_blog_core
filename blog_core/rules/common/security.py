# -*- coding: utf-8 -*-
"""
blog_core.rules.common.security - Gate 7: Security and Secrets Leak Prevention
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


DUMMY_TOKENS = {
    "your_api_key", "your-api-key", "your_token", "your-token",
    "example_token", "sample_key", "test_token", "placeholder",
    "xxx", "xxxx", "000000", "<token>", "<api_key>", "<api-key>",
    "my_secret", "dummy", "replace_with", "insert_here",
    "secret-key", "secret_key", "super-secure", "my-secret", "sample",
    "example", "demo", "tutorial", "test_key", "change-me", "changeme"
}


class AwsKeyLeakRule(BaseRule):
    """AWS Access Key ID 누출 차단 규칙 (Gate 7)"""

    rule_id = "G7_AWS_KEY_LEAK"
    gate_id = "GATE_7"
    gate_name = "보안 & 시크릿 누출 방벽"
    description = "실제 AWS Access Key ID 형식(AKIA...)의 문자열 노출 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        for idx, line in enumerate(ctx.lines, start=1):
            aws_match = re.search(r"\bAKIA[0-9A-Z]{16}\b", line)
            if aws_match:
                matched_val = aws_match.group(0)
                if not any(d in matched_val.lower() for d in DUMMY_TOKENS):
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=idx,
                        snippet=matched_val,
                        message="[보안 위험] 실제 AWS Access Key ID 형식의 문자열이 감지되었습니다.",
                        fix_hint="실제 클라우드 자격 증명을 즉시 삭제하고, 환경변수(os.environ['AWS_ACCESS_KEY_ID']) 또는 'YOUR_AWS_ACCESS_KEY'와 같은 플레이스홀더로 대체하십시오."
                    ))
        return violations


class GithubTokenLeakRule(BaseRule):
    """GitHub Personal Access Token(PAT) 누출 차단 규칙 (Gate 7)"""

    rule_id = "G7_GITHUB_TOKEN_LEAK"
    gate_id = "GATE_7"
    gate_name = "보안 & 시크릿 누출 방벽"
    description = "실제 GitHub Personal Access Token(ghp_..., github_pat_...) 노출 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        for idx, line in enumerate(ctx.lines, start=1):
            gh_match = re.search(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b", line)
            if gh_match:
                matched_val = gh_match.group(0)
                if not any(d in matched_val.lower() for d in DUMMY_TOKENS):
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=idx,
                        snippet=matched_val[:12] + "...",
                        message="[보안 위험] GitHub Personal Access Token(PAT) 형식의 문자열이 감지되었습니다.",
                        fix_hint="실제 GitHub 토큰을 즉시 폐기하고 더미 문자열로 교체하십시오."
                    ))
        return violations


class SlackWebhookLeakRule(BaseRule):
    """Slack Webhook URL 누출 차단 규칙 (Gate 7)"""

    rule_id = "G7_SLACK_WEBHOOK_LEAK"
    gate_id = "GATE_7"
    gate_name = "보안 & 시크릿 누출 방벽"
    description = "실제 슬랙 수신 웹훅 URL(https://hooks.slack.com/services/...) 노출 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        for idx, line in enumerate(ctx.lines, start=1):
            slack_match = re.search(r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+", line)
            if slack_match:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=slack_match.group(0)[:35] + "...",
                    message="[보안 위험] 실제 슬랙 웹훅 URL(Slack Webhook URL)이 노출되었습니다.",
                    fix_hint="웹훅 URL을 삭제하고 'https://hooks.slack.com/services/T00/B00/XXXX' 형식의 마스킹된 주소를 사용하십시오."
                ))
        return violations


class PrivateKeyLeakRule(BaseRule):
    """비공개 암호화 키(Private Key) 헤더 노출 차단 규칙 (Gate 7)"""

    rule_id = "G7_PRIVATE_KEY_LEAK"
    gate_id = "GATE_7"
    gate_name = "보안 & 시크릿 누출 방벽"
    description = "BEGIN RSA/EC/DSA/OPENSSH/PGP/ENCRYPTED/PRIVATE KEY 헤더 노출 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        for idx, line in enumerate(ctx.lines, start=1):
            pk_match = re.search(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|ENCRYPTED|PRIVATE) KEY-----", line)
            if pk_match:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=idx,
                    snippet=pk_match.group(0),
                    message="[보안 위험] 비공개 암호화 키(Private Key) 헤더가 감지되었습니다.",
                    fix_hint="비공개 키 원문을 마크다운에 절대 삽입하지 마십시오."
                ))
        return violations


class HardcodedSecretRule(BaseRule):
    """하드코딩된 API Key/Secret 직접 할당문 차단 규칙 (Gate 7)"""

    rule_id = "G7_HARDCODED_SECRET"
    gate_id = "GATE_7"
    gate_name = "보안 & 시크릿 누출 방벽"
    description = "api_key = '...' 등 24자 이상의 실제 시크릿 문자열 직접 할당 차단"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        secret_assign_pat = re.compile(
            r"""(?i)\b(?:api_key|apikey|secret_key|client_secret|auth_token)\s*[:=]\s*["']([a-zA-Z0-9_\-\.]{24,})["']"""
        )
        for idx, line in enumerate(ctx.lines, start=1):
            m = secret_assign_pat.search(line)
            if m:
                val = m.group(1)
                if not any(d in val.lower() for d in DUMMY_TOKENS):
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        line_number=idx,
                        snippet=line.strip()[:80],
                        message="[보안 위험] 실제 API 키 또는 비밀 시크릿 토큰의 직접 할당문이 감지되었습니다.",
                        fix_hint="비밀번호나 API 키를 코드에 직접 하드코딩하지 말고 환경변수나 시크릿 매니저 참조 코드로 대체하십시오."
                    ))
        return violations
