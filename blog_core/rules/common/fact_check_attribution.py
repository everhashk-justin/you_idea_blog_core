# -*- coding: utf-8 -*-
"""
blog_core.rules.common.fact_check_attribution - Gate 10: Mandatory Real-Time Fact-Check Attribution Gate
공인 실측 출처 필수 귀속 관문:
1. Frontmatter 'fact_check_sources'(공인 실측 출처 목록) 필수 및 공인 공식 규격 검증
2. Frontmatter 'verification_date'(실측 검증 일자) 필수 및 유효 연도(2025~2027) 검증
3. 본문 산문(코드 블록 제외) 내 핵심 주장/수치에 대한 공인 출처 인용 필수
"""

import re
from typing import List, Any
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


OFFICIAL_SOURCE_PATTERNS = [
    r"^https?://[^\s]+",
    r"고시", r"공고", r"법률", r"시행령", r"대통령령",
    r"보건복지부", r"기획재정부", r"국세청", r"식품의약품안전처", r"식약처", r"금융감독원",
    r"공공누리", r"KOGL", r"대한민국\s*정책브리핑",
    r"commit\s+[0-9a-f]{7,40}", r"Linux\s+kernel\s+v?\d+", r"git\s+commit",
    r"PMID[:\s]*\d+", r"PMC\d+", r"10\.\d{4,9}/[^\s]+", r"doi[:\s]+10\.\d{4,9}",
    r"RFC\s*\d+", r"W3C\s+Recommendation", r"ISO/IEC\s*\d+", r"IEEE\s*\d+",
    r"SEC\s+EDGAR", r"Form\s+(?:10-K|10-Q|8-K|13F|4)", r"Federal\s+Reserve\s+(?:H\.4\.1|Balance\s+Sheet)"
]

BODY_ATTRIBUTION_PATTERNS = [
    r"\[(?:출처|자료|Source|Reference|참고)[:：]\s*[^\]]+\]",
    r"(?:^|\n)>\s*(?:출처|자료|Source|Reference)[:：]\s*.+",
    r"\[\^[\w\d]+\]:\s*.+",
    r"\[(?:공식\s*출처|공식\s*문서|출처|Source|Docs?|고시|RFC|논문|Reference)\]\(https?://.+?\)",
    r"(?:^|\n)#{1,4}\s*(?:공식\s*)?(?:출처|참고\s*문헌|참고\s*자료|References?|Sources?)\b",
    r"출처\s*[:：]\s*.*?공공누리",
    r"공공저작물\s*자유이용허락\s*표시",
    r"대한민국\s*정책브리핑"
]


class FactCheckAttributionRule(BaseRule):
    """Gate 10: 공인 실측 출처 필수 귀속 관문 규칙"""

    rule_id = "G10_FACT_CHECK_ATTRIBUTION"
    gate_id = "GATE_10"
    gate_name = "공인 실측 출처 필수 귀속 관문"
    description = "Frontmatter 실측 출처(fact_check_sources) 및 검증 일자(verification_date), 본문 출처 인용 필수 검증"
    platforms = ["dev", "tistory", "naver", "gear", "stock", "markets"]  # 블로그 생태계 6대 플랫폼 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        fm = ctx.fm_data

        # 1. Frontmatter fact_check_sources 검증
        sources = fm.get("fact_check_sources") or fm.get("fact_check_source") or fm.get("sources")
        if not sources:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G10_MISSING_FM_SOURCES",
                severity=self.default_severity,
                line_number=1,
                snippet="Missing 'fact_check_sources' in Frontmatter",
                message="[공인 실측 출처 누락] YAML Frontmatter에 'fact_check_sources'(공인 실측 출처 목록)가 누락되었거나 비어 있습니다.",
                fix_hint="Frontmatter에 'fact_check_sources: [\"https://공식문서링크...\", \"RFC 9110\", \"보건복지부 고시...\"]' 형식으로 공인 실측 출처를 1개 이상 명시하십시오."
            ))
        else:
            src_list = sources if isinstance(sources, list) else [sources]
            has_valid_source = False
            for s in src_list:
                s_str = str(s).strip()
                if any(re.search(pat, s_str, re.IGNORECASE) for pat in OFFICIAL_SOURCE_PATTERNS):
                    has_valid_source = True
                    break
            if not has_valid_source:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G10_INVALID_FM_SOURCES",
                    severity=self.default_severity,
                    line_number=1,
                    snippet=f"Sources: {sources}",
                    message="[공인 실측 출처 규격 미달] 'fact_check_sources'에 공인된 공식 출처(공식 URL, 정부 고시, 커널 커밋 해시, PubMed DOI, RFC/W3C 표준 사양 등)가 식별되지 않습니다.",
                    fix_hint="도메인별 공인 공식 URL(github, kernel.org, gov/go.kr, sec.gov 등) 또는 법령/고시/RFC 규격을 명시하십시오."
                ))

        # 2. Frontmatter verification_date 검증
        ver_date = fm.get("verification_date") or fm.get("verified_at") or fm.get("fact_check_date")
        if not ver_date:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G10_MISSING_FM_VERIFICATION_DATE",
                severity=self.default_severity,
                line_number=1,
                snippet="Missing 'verification_date' in Frontmatter",
                message="[실측 검증 일자 누락] YAML Frontmatter에 'verification_date'(실측 검증 일자)가 누락되었습니다.",
                fix_hint="Frontmatter에 'verification_date: \"YYYY-MM-DD\"' 형식으로 공인 실측 교차 검증을 완료한 날짜를 명시하십시오."
            ))
        else:
            m_date = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(ver_date).strip())
            if not m_date:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G10_INVALID_FM_VERIFICATION_DATE",
                    severity=self.default_severity,
                    line_number=1,
                    snippet=f"verification_date: '{ver_date}'",
                    message="[실측 검증 일자 형식 오류] 'verification_date'는 YYYY-MM-DD 형식이어야 합니다.",
                    fix_hint="예: 'verification_date: \"2026-11-22\"' 형식으로 유효한 연월일을 기재하십시오."
                ))
            else:
                year = int(m_date.group(1))
                if year < 2025 or year > 2027:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id="G10_OUTDATED_FM_VERIFICATION_DATE",
                        severity=self.default_severity,
                        line_number=1,
                        snippet=f"Year: {year}",
                        message=f"[실측 검증 일자 연도 오류] 실측 검증 일자({year}년)가 당해 운영 연도(2025~2027년) 범위를 벗어났습니다.",
                        fix_hint="현재 운영 시점인 당해 연도 날짜를 기재하십시오."
                    ))

        # 3. 본문 내 공인 출처 귀속 인용 검증 (코드 블록 제외 산문 본문 대상)
        body_prose = re.sub(r"```.*?```", "", ctx.body, flags=re.DOTALL)
        has_body_attribution = any(re.search(pat, body_prose, re.IGNORECASE | re.MULTILINE) for pat in BODY_ATTRIBUTION_PATTERNS)
        if not has_body_attribution:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G10_MISSING_BODY_ATTRIBUTION",
                severity=self.default_severity,
                line_number=1,
                snippet="No in-body source attribution found in prose",
                message="[본문 공인 출처 인용 누락] 본문 내 핵심 주장 또는 수치에 대한 공인 출처 인용('[출처: ...]', '> 출처: ...', 또는 참고문헌 섹션)이 누락되었습니다.",
                fix_hint="본문 내에 '[출처: 공인기관 공식문서]' 또는 '> 출처: https://...' 형태의 인용을 의무 삽입하십시오."
            ))

        return violations
