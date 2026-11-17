# -*- coding: utf-8 -*-
"""
blog_core.rules.common.legal_medical - Gate 8: Medical Law & Health Functional Food Law Compliance
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


MEDICAL_LAW_RULES = [
    # 1. 질병 예방/치료 표방 금지
    (
        r"완치",
        "REJECT",
        "G8_MED_CURE_ALL",
        "[식품표시광고법 제8조 위반] '완치' 단어 사용 금지. 건강기능식품/일반식품은 질병 완치를 표방할 수 없습니다.",
        "'완치'를 삭제하고 '체내 흡수율 개선', '영양 공급' 등 객관적 기전으로 서술하십시오."
    ),
    (
        r"특효약",
        "REJECT",
        "G8_MED_MAGIC_CURE",
        "[식품표시광고법 제8조 위반] '특효약' 등 과장 광고 단어 100% 금지.",
        "'특효약' 표현을 삭제하십시오."
    ),
    (
        r"완벽\s*예방",
        "REJECT",
        "G8_MED_PERFECT_PREVENTION",
        "[식품표시광고법 위반] '완벽 예방' 표방 금지.",
        "'완벽 예방' 표현을 삭제하십시오."
    ),
    (
        r"만병통치",
        "REJECT",
        "G8_MED_PANACEA",
        "[식품표시광고법 위반] '만병통치' 표방 금지.",
        "'만병통치' 표현을 삭제하십시오."
    ),
    (
        r"기적의\s*(?:치료|영양제|효능)",
        "REJECT",
        "G8_MED_MIRACLE_CURE",
        "[식품표시광고법 위반] '기적의 치료/영양제' 과장 수식어 금지.",
        "기적 등의 비과학적 수식어를 배제하십시오."
    ),
    (
        r"항암(?:\s*효과|\s*작용|\s*치료)",
        "REJECT",
        "G8_MED_ANTICANCER",
        "[식품표시광고법 위반] 식품/영양소의 '항암 효과/치료' 표방 절대 금지.",
        "항암 표방 표현을 전면 삭제하십시오."
    ),
    (
        r"병이\s*낫는",
        "REJECT",
        "G8_MED_DISEASE_REMEDY",
        "[식품표시광고법 위반] '병이 낫는' 표방 금지.",
        "질병 치유 표방 표현을 삭제하십시오."
    ),

    # 2. 의약품 오인·혼동 표현
    (
        r"천연\s*치료제",
        "REJECT",
        "G8_MED_NATURAL_MEDICINE",
        "[식품표시광고법 제8조 위반] 건강기능식품/식품을 '천연 치료제'로 의약품 오인 유발 금지.",
        "'천연 치료제' 표현을 삭제하고 '식품의약품안전처 고시 기능성 원료'로 서술하십시오."
    ),
    (
        r"약(?:을|\s*)?\s*대신(?:\s*먹는)?",
        "REJECT",
        "G8_MED_INSTEAD_OF_DRUG",
        "[식품표시광고법 위반] '약 대신' 등 의약품 대체 오인 표현 금지.",
        "의약품을 대체할 수 없음을 명시하십시오."
    ),
    (
        r"의약품(?:을|\s*)?\s*(?:대체|대용)",
        "REJECT",
        "G8_MED_DRUG_SUBSTITUTE",
        "[식품표시광고법 위반] '의약품 대체/대용' 표방 금지.",
        "의약품 대체 표현을 삭제하십시오."
    ),
    (
        r"처방약(?:을|은|\s*)?\s*(?:중단|끊고|대체)",
        "REJECT",
        "G8_MED_STOP_PRESCRIPTION",
        "[의료법·식품표시광고법 위반] 환자에게 '처방약 중단/끊고' 유도 절대 금지 (중대한 건강 위해 행위).",
        "전문의 처방약 복용 유지를 안내하십시오."
    ),
    (
        r"부작용(?:이|\s*)?\s*없는\s*(?:치료제|약)",
        "REJECT",
        "G8_MED_NO_SIDE_EFFECT_DRUG",
        "[식품표시광고법 위반] '부작용 없는 치료제/약' 표방 금지.",
        "치료제/약 표현을 삭제하십시오."
    ),
    (
        r"병원(?:에|\s*)?\s*갈\s*필요\s*(?:없는|없음)",
        "REJECT",
        "G8_MED_NO_HOSPITAL_NEED",
        "[의료법 위반] '병원 갈 필요 없는' 등 진료 회피 유도 금지.",
        "이상 증상 시 의사의 진료를 받도록 안내하십시오."
    ),

    # 3. 의료인 사칭 및 추천 보증
    (
        r"(?:현직|임상)\s*(?:의사|약사|한의사)로서",
        "REJECT",
        "G8_MED_IMPERSONATION_PROFESSIONAL",
        "[의료법 제56조 및 표시광고법 위반] 비의료인의 의료인(의사/약사/한의사) 자격 사칭 금지.",
        "소비자 및 영양 데이터 팩트체커 입장에서 객관적으로 서술하십시오."
    ),
    (
        r"(?:의사|약사|한의사)인\s*제가",
        "REJECT",
        "G8_MED_IMPERSONATION_SELF",
        "[의료법 제56조 위반] 의료인 자격 사칭 표현 감지.",
        "의료인 사칭 어투를 삭제하십시오."
    ),
    (
        r"전문의가\s*보증하는",
        "REJECT",
        "G8_MED_DOCTOR_ENDORSEMENT",
        "[식품표시광고법 위반] '전문의가 보증하는' 등 특정 의료인 추천/보증 표방 금지.",
        "공인 학술 논문 및 식약처 공시 자료로 대체하십시오."
    ),
    (
        r"병원장\s*추천",
        "REJECT",
        "G8_MED_HOSPITAL_CHIEF_REC",
        "[식품표시광고법 위반] '병원장 추천' 표방 금지.",
        "병원장 추천 표현을 삭제하십시오."
    ),

    # 4. 거짓·과장된 기능성 광고
    (
        r"체지방\s*100%\s*(?:분해|감소|연소)",
        "REJECT",
        "G8_MED_100PCT_FAT_BURN",
        "[식품표시광고법 위반] '체지방 100% 분해/연소' 비과학적 허위 과장 표현 금지.",
        "식약처 인정 기능성 범위 내로 기재하십시오."
    ),
    (
        r"노화\s*(?:완전\s*)?역전",
        "REJECT",
        "G8_MED_AGING_REVERSAL",
        "[식품표시광고법 위반] '노화 완전 역전' 과장 광고 금지.",
        "항산화 영양소의 체내 작용 기전으로 담백하게 설명하십시오."
    ),
    (
        r"기억력\s*[0-9]+배\s*(?:향상|상승)",
        "REJECT",
        "G8_MED_MEMORY_MULTIPLIER",
        "[식품표시광고법 위반] '기억력 N배 향상' 등 입증되지 않은 수치 과장 금지.",
        "인체적용시험 결과의 통계적 유의성으로 설명하십시오."
    ),
    (
        r"하루만에\s*(?:완치|치료|개선|정상화)",
        "REJECT",
        "G8_MED_ONE_DAY_CURE",
        "[식품표시광고법 위반] '하루만에 완치/개선' 과장 광고 금지.",
        "즉각적인 극적 효과 과장을 삭제하십시오."
    ),
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


class MedicalLawRule(BaseRule):
    """의료법 & 건강기능식품법(식품표시광고법) 위반 차단 규칙 (Gate 8)"""

    rule_id = "G8_MED_MEDICAL_LAW"
    gate_id = "GATE_8"
    gate_name = "의료법·식품표시광고법 방벽"
    description = "천연치료제, 처방약 중단, 의사 사칭, 완치/항암/특효약 등 21대 의료법·건기식법 위반 표현 차단"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        in_code_block = False

        for idx, line in enumerate(ctx.lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            for pat, sev, r_id, msg, hint in MEDICAL_LAW_RULES:
                match = re.search(pat, line)
                if match:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=r_id,
                        severity=sev,
                        line_number=idx,
                        snippet=stripped[:100],
                        message=msg,
                        fix_hint=hint
                    ))

        return violations


class MedicalDisclaimerRule(BaseRule):
    """건강/영양제/건기식 포스팅 필수 법적 면책고지 검증 규칙 (Gate 8)"""

    rule_id = "G8_MED_MISSING_DISCLAIMER"
    gate_id = "GATE_8"
    gate_name = "의료법·식품표시광고법 방벽"
    description = "건강/영양제 콘텐츠 최하단 필수 법적 면책고지(Disclaimer) 누락 차단"
    platforms = None  # 건강 콘텐츠인 경우 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        category = ctx.fm_data.get("category", "").strip()
        title = ctx.fm_data.get("title", "").strip()
        norm_path = ctx.file_path.replace("\\", "/").lower()

        is_health = (
            "infopiece" in norm_path or
            any(k in category for k in ["건강", "영양", "건기식", "의학"]) or
            any(k in title for k in ["영양제", "마그네슘", "비타민", "오메가", "건강기능식품", "유산균", "콜라겐"])
        )

        if is_health:
            has_health_disclaimer = any(re.search(p, ctx.body) for p in HEALTH_DISCLAIMER_PATTERNS)
            if not has_health_disclaimer:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet="No health/medical disclaimer found in health content",
                    message="[의료법·건기식법 방벽] 건강/영양제 포스팅 최하단에 필수적인 '법적 면책 문구(Disclaimer)'가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '본 포스팅은 일반적인 정보 제공을 목적으로 하며, 전문 의료인의 진단 및 처방을 대신할 수 없습니다. 질병의 예방 및 치료를 위한 의약품이 아닙니다.'를 삽입하십시오."
                ))

        return violations
