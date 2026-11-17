# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.naver - Naver Blog Platform Rules (solidlog, tidynote, infopiece)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


NAVER_HEALTH_FORBIDDEN = [
    (r"치료", "REJECT", "[의료법 위반 방벽] 건기식 포스팅에 '치료' 단어 100% 금지. '식약처 고시 기능성 보충', '체내 메커니즘 지원' 등으로 대체하십시오."),
    (r"완치", "REJECT", "[의료법 위반 방벽] '완치' 단어 100% 금지."),
    (r"특효약", "REJECT", "[의료법 위반 방벽] '특효약' 과장 광고 단어 100% 금지."),
    (r"완벽\s*예방", "REJECT", "[의료법 위반 방벽] '완벽 예방' 표방 금지."),
    (r"항암", "REJECT", "[의료법 위반 방벽] 질병 치유/항암 표방 절대 금지."),
    (r"만병통치", "REJECT", "[의료법 위반 방벽] '만병통치' 표방 금지."),
    (r"약효", "REJECT", "[의료법 위반 방벽] 건기식에 '약효' 표현 금지. '생체이용률', '흡수 기전' 등으로 대체."),
]

HEALTH_DISCLAIMER_PATTERNS = [
    r"면책",
    r"의사의\s*진료",
    r"처방을\s*대신",
    r"의료\s*전문가와\s*상담",
    r"전문\s*의료인",
    r"의사\s*(?:또는|및)\s*약사와\s*상담",
    r"의약품이\s*(?:아님|아니|아닙)",
    r"진단\s*및\s*처방",
    r"의료인의\s*진단",
    r"건강\s*정보\s*제공",
    r"일반적인\s*건강\s*정보",
    r"질병의\s*(?:예방\s*및\s*)?치료를\s*(?:위한\s*의약품이\s*아닙|목적으로\s*하지\s*않)",
    r"의학적\s*치료\s*행위가\s*아닙",
]


class NaverHealthMedicalRule(BaseRule):
    """네이버 건강 블로그 의료법 위반 단어 100% 하드 블록 규칙 (Gate 6)"""

    rule_id = "G6_NAVER_MEDICAL_LAW"
    gate_id = "GATE_6"
    gate_name = "네이버 블로그 법적 규격 검증"
    description = "네이버 건강 블로그(infopiece) 내 '완치', '치료', '특효약' 등 의료법 위반 단어 차단"
    platforms = ["naver"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "")
        is_health = ("infopiece" in ctx.file_path.lower() or "건강" in category or "영양" in category)

        if not is_health:
            return violations

        for idx, line in enumerate(ctx.lines, start=1):
            # 법적 면책 고지 문구 부분만 국소 제거하여 오탐 방지하되 본문 단어는 철저 검증
            clean_line = re.sub(
                r"(?:(?:특정\s*)?질병의\s*[^.\n]*?(?:치료|예방)[^.\n]*?(?:목적으로\s*하지\s*않[가-힣]*|의약품이\s*아니[가-힣]*|행위가\s*아니[가-힣]*)|"
                r"의학적\s*(?:처방이나\s*)?치료\s*(?:행위가\s*아니[가-힣]*|를\s*대신[가-힣]*)|"
                r"진단\s*및\s*치료를\s*대신[가-힣]*|"
                r"질환\s*치료\s*(?:중[가-힣]*|를\s*받[가-힣]*))",
                "",
                line
            )
            for pattern, sev, msg in NAVER_HEALTH_FORBIDDEN:
                match = re.search(pattern, clean_line)
                if match:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=sev,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=msg,
                        fix_hint="의료법 위반 소지가 있는 단어를 즉시 제거하고 식약처 공인 기능성 표현으로 수정하십시오."
                    ))

        return violations


class NaverMedicalDisclaimerRule(BaseRule):
    """네이버 건강 블로그 필수 법적 면책 문구(Disclaimer) 누락 검증 (Gate 6)"""

    rule_id = "G6_NAVER_MISSING_DISCLAIMER"
    gate_id = "GATE_6"
    gate_name = "네이버 블로그 법적 규격 검증"
    description = "건강/영양제 포스팅 최하단에 필수적인 '법적 면책 문구(Disclaimer)' 누락 차단"
    platforms = ["naver"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "")
        is_health = ("infopiece" in ctx.file_path.lower() or "건강" in category or "영양" in category)

        if is_health:
            has_disclaimer = any(re.search(p, ctx.body) for p in HEALTH_DISCLAIMER_PATTERNS)
            if not has_disclaimer:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet="No medical disclaimer found at the bottom",
                    message="[법적 방벽 결손] 건강/영양제 포스팅 최하단에 필수적인 '법적 면책 문구(Disclaimer)'가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '본 포스팅은 일반적인 정보 제공을 목적으로 하며, 전문 의료인의 진단 및 처방을 대신할 수 없습니다.'를 삽입하십시오."
                ))

        return violations


class NaverInlineImageForbiddenRule(BaseRule):
    """네이버 블로그 인라인 마크다운 이미지(![...]) 삽입 금지 규칙 (Gate 6)"""

    rule_id = "G6_NAVER_INLINE_IMAGE_FORBIDDEN"
    gate_id = "GATE_6"
    gate_name = "네이버 블로그 조판 규격 검증"
    description = "스마트에디터 수동 조판 최적화를 위해 인라인 마크다운 이미지 태그 금지"
    platforms = ["naver"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        img_tag_matches = re.findall(r"!\[(.*?)\]\((.*?)\)", ctx.body)
        if img_tag_matches:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet=f"Found {len(img_tag_matches)} inline markdown image tags (![...])",
                message="네이버 블로그 본문 내에 직접 이미지(![...])를 띄우는 것이 금지되어 있습니다. (스마트에디터 수동 업로드 지원 규격 위반)",
                fix_hint="본문에는 '[사진 X: 파일명](file:///...)' 형태의 클릭 가능한 로컬 링크만 남기십시오."
            ))
        return violations


class NaverHashtagsRule(BaseRule):
    """네이버 스마트에디터 ONE 자동 태그 등록용 인라인 해시태그 블록 검증 규칙 (Gate 6)"""

    rule_id = "G6_NAVER_MISSING_HASHTAGS"
    gate_id = "GATE_6"
    gate_name = "네이버 블로그 조판 규격 검증"
    description = "본문 최하단 300자 내 '#태그1 #태그2 ...' 인라인 해시태그 블록 존재 검증"
    platforms = ["naver"]
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        hashtag_match = re.search(r"#[가-힣a-zA-Z0-9_]+\s+#[가-힣a-zA-Z0-9_]+", ctx.body[-300:])
        if not hashtag_match:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet="No inline #hashtag block found in the last 300 characters",
                message="본문 최하단에 네이버 스마트에디터 ONE 자동 태그 완성용 '#태그1 #태그2 ...' 블록이 누락되었습니다.",
                fix_hint="원고 맨 마지막 줄에 '#태그1 #태그2 #태그3 ...' 형태의 단일 인라인 해시태그를 추가하십시오."
            ))
        return violations
