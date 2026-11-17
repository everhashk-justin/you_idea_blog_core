# -*- coding: utf-8 -*-
"""
blog_core.rules.common.legal_ftc - Gate 8: Fair Trade Commission (FTC) Endorsement & Covert Advertising Compliance
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


AFFILIATE_LINK_PATTERNS = [
    r"link\.coupang\.com",
    r"coupang\.com\/vp\/products",
    r"partners\.coupang\.com",
    r"linkprice\.com",
    r"adpick\.co\.kr",
    r"tenping\.kr",
    r"clix\.kr",
    r"amzn\.to",
    r"amazon\.com\/.*[?&]tag=",
    r"aliexpress\.com\/.*[?&]aff_",
]

AFFILIATE_KEYWORD_PATTERNS = [
    r"쿠팡\s*파트너스",
    r"제휴\s*(?:마케팅|링크|수수료)",
    r"원고료(?:를|\s*)?\s*(?:지원|지급)",
    r"제품(?:을|\s*)?\s*(?:협찬|지원)",
    r"수수료(?:를|\s*)?\s*(?:발생|제공받)",
    r"파트너스\s*활동",
    r"스폰서\s*링크",
]

FTC_DISCLOSURE_PATTERNS = [
    r"소정의\s*수수료",
    r"일정액의\s*수수료",
    r"수수료를\s*(?:제공|지원|지급)받",
    r"수수료를\s*받(?:을\s*수|을\s*있|았)",
    r"경제적\s*대가",
    r"공정거래위원회\s*(?:지침|문구)",
    r"추천[·\s]보증\s*(?:등에\s*관한\s*)?심사지침",
    r"원고료를\s*(?:지급|지원)받",
    r"제품을\s*(?:제공|협찬)받",
    r"파트너스\s*활동의\s*일환",
    r"대가성\s*(?:광고|표시|문구)",
    r"유료\s*광고\s*포함",
    # English & Global FTC Disclosures (US FTC 16 CFR § 255.5)
    r"(?i)\baffiliate\s+(?:link|links|commission|commissions)\b",
    r"(?i)\bearn\s+from\s+qualifying\s+purchases\b",
    r"(?i)\bpaid\s+(?:link|links|ad|advertisement|partnership)\b",
    r"(?i)\bcommission\s+at\s+no(?:\s+additional)?\s+cost\b",
    r"(?i)\b(?:sponsored|promoted)\s+content\b",
]


class FtcAffiliateRule(BaseRule):
    """공정거래위원회 추천·보증 심사지침 준수 검증 규칙 (Gate 8)"""

    rule_id = "G8_FTC_AFFILIATE"
    gate_id = "GATE_8"
    gate_name = "공정위 표시광고법 방벽"
    description = "제휴 링크(쿠팡 파트너스 등) 또는 협찬 시 기만 광고 차단 및 대가성 고지 필수 검증"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []

        has_affiliate_link = any(re.search(pat, ctx.body, re.IGNORECASE) for pat in AFFILIATE_LINK_PATTERNS)
        has_affiliate_kw = any(re.search(pat, ctx.body) for pat in AFFILIATE_KEYWORD_PATTERNS)

        if has_affiliate_link or has_affiliate_kw:
            # (1) 기만적 스텔스 마케팅/위장 광고 차단 (내돈내산)
            my_money_match = re.search(r"(?:내돈내산|직접\s*구매한|100%\s*자비)", ctx.body)
            if my_money_match:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G8_FTC_COVERT_MY_MONEY",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=my_money_match.group(0),
                    message="[공정위 표시광고법 위반] 제휴 링크 또는 대가성 상업 활동이 포함되어 있으나 '내돈내산/자비 구매'로 소비자를 오도하는 기만적 스텔스 마케팅이 감지되었습니다.",
                    fix_hint="'내돈내산' 허위 표기를 삭제하고 공정위 표준 대가성 문구를 기재하십시오."
                ))

            # (2) 기만적 스텔스 마케팅/위장 광고 차단 (광고 아닙니다)
            not_ad_match = re.search(r"(?:광고|협찬)\s*(?:가\s*)?아닙니다", ctx.body)
            if not_ad_match:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G8_FTC_COVERT_NOT_AD",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=not_ad_match.group(0),
                    message="[공정위 표시광고법 위반] 제휴 수수료 링크가 있으면서 '광고/협찬 아닙니다'라고 허위 주장하는 행위가 감지되었습니다.",
                    fix_hint="광고 부인 문구를 삭제하고 수수료 제공 사실을 명시하십시오."
                ))

            # (3) 대가성 공개 문구 필수 검증
            has_ftc_disclosure = any(re.search(pat, ctx.body) for pat in FTC_DISCLOSURE_PATTERNS)
            if not has_ftc_disclosure:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G8_FTC_MISSING_DISCLOSURE",
                    severity=self.default_severity,
                    line_number=0,
                    snippet="Affiliate links or sponsorship keywords detected without FTC disclosure",
                    message="[공정위 표시광고법 방벽] 제휴 링크(쿠팡 파트너스 등) 또는 대가성 상업 활동 내용이 포함되어 있으나, 공정거래위원회 「추천·보증 등에 관한 표시·광고 심사지침」에 따른 경제적 이해관계(대가성) 고지 문구가 누락되었습니다.",
                    fix_hint="포스팅 최상단 또는 최하단에 '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.' 또는 '소정의 수수료를 제공받을 수 있습니다.'를 명시하십시오."
                ))

        return violations
