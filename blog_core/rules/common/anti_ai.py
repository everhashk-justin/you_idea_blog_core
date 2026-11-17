# -*- coding: utf-8 -*-
"""
blog_core.rules.common.anti_ai - Gate 2: Anti-AI Clichés and Mechanical Translation Detection (EN & KO)
"""

import re
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


EN_AI_CLICHE_PATTERNS = [
    # 단어 수준 상투어
    (r"\bdelve\b", "REJECT", "AI 단골 어휘 'delve' 감지. 'analyze', 'examine', 'inspect', 'trace' 등으로 대체하십시오."),
    (r"\btapestry\b", "REJECT", "AI 수식어 'tapestry' 감지. 사실적 아키텍처 용어로 대체하십시오."),
    (r"\bseamlessly\b", "REJECT", "AI 상투적 부사 'seamlessly' 감지. 구체적 연동 메커니즘을 명시하십시오."),
    (r"\btestament\b", "REJECT", "AI 미사여구 'testament' 감지. 객관적 지표로 서술하십시오."),
    (r"\bgame-changer\b", "REJECT", "과장된 표현 'game-changer' 감지. 기술적 효익을 구체적 수치로 제시하십시오."),
    (r"\brevolutionize\b", "REJECT", "과장된 동사 'revolutionize' 감지. 실제 개선된 성능이나 처리량을 명시하십시오."),
    (r"\bbeacon\b", "REJECT", "AI 은유 표현 'beacon' 감지."),
    (r"\bmultifaceted\b", "REJECT", "상투적 수식어 'multifaceted' 감지."),
    (r"\bplethora\b", "REJECT", "상투적 수식어 'plethora' 감지. 'multiple', 'several' 또는 구체적 개수를 쓰십시오."),
    (r"\blinchpin\b", "REJECT", "AI 단골 은유 'linchpin' 감지. 'core component', 'critical dependency'로 쓰십시오."),
    (r"\bparamount\b", "WARNING", "상투적 강조어 'paramount' 감지. 과도한 강조를 지양하십시오."),
    (r"\bdemystify\b", "REJECT", "AI 전형적 표현 'demystify' 감지. 담백한 기술 분석 표현을 사용하십시오."),
    (r"\borchestrate\b", "WARNING", "AI 단골 동사 'orchestrate' 감지. (Kubernetes 등의 고유명사가 아닐 경우 구체적 행위 기술)"),
    (r"\bharnessing the power\b", "REJECT", "AI 관용구 'harnessing the power' 감지."),
    (r"\bat the end of the day\b", "REJECT", "구어체 상투어 'at the end of the day' 감지."),
    (r"\bwithout further ado\b", "REJECT", "AI 전형적 도입구 'without further ado' 감지. 즉시 본론으로 진입하십시오."),
    (r"\blet's dive (in|deep)\b", "REJECT", "AI 전형적 챕터 진입구 'let's dive' 감지. 본론으로 바로 들어가십시오."),

    # 문장/구절 수준 상투어
    (r"\bIn (the modern|today's) (fast-paced|digital|cloud|software) (world|landscape|era|environment)\b", "REJECT",
     "AI 전형적 도입 클리셰 'In the modern ... world/landscape' 감지. 공허한 배경 설명을 삭제하고 실제 장애 현상으로 시작하십시오."),
    (r"\bBy doing so,\s*.*?\bbecomes immune\b", "REJECT",
     "AI 과장 클리셰 'becomes immune' 감지. 엔지니어링에 '면역'은 없습니다. 방어 기전과 허용 한계를 서술하십시오."),
    (r"\bHere is the (exact|step-by-step) (diagnostic|solution|breakdown|guide)\b", "REJECT",
     "AI 전형적 튜토리얼 어투 'Here is the exact ...' 감지. 엔지니어의 담백한 관찰 서술로 바꾸십시오."),
    (r"\bIt is worth noting that\b", "WARNING", "AI 습관적 필러 'It is worth noting that' 감지. 문장을 간결하게 줄이십시오."),
    (r"\bIn conclusion,\s*", "REJECT", "AI 형식적 결론 시작 'In conclusion' 감지. 판에 박힌 요약 대신 프로덕션 런북 체크포인트를 제시하십시오."),
    (r"\bIn summary,\s*", "REJECT", "AI 형식적 결론 시작 'In summary' 감지."),
    (r"\bNow that we have (seen|understood|explored)\b", "REJECT", "AI 교과서식 전환구 감지."),
    (r"\bIt's not just a .*?;\s*it's a\b", "REJECT", "AI 이분법적 수사구 'It's not just A, it's B' 감지."),
]

KO_AI_CLICHE_PATTERNS = [
    # 상투적 인트로
    (r"현대\s+(소프트웨어|클라우드|개발|비즈니스|IT)\s+(생태계|환경|사회|시장)에서는?", "REJECT",
     "AI 전형적 인트로 '현대 ... 환경에서는' 감지. 교과서적 서론을 배제하고 구체적인 문제 현상으로 직행하십시오."),
    (r"눈부신\s+발전을\s+거듭하며", "REJECT", "AI 판에 박힌 수식어 '눈부신 발전을 거듭하며' 감지."),
    (r"지금부터\s+자세히\s+(살펴보겠습니다|알아보겠습니다)", "REJECT", "AI 전형적 유튜브/튜토리얼 말투 감지. 즉시 본론으로 진입하십시오."),
    (r"필수불가결한", "REJECT", "AI 상투어 '필수불가결한' 감지. 구체적인 의존성이나 필요성을 서술하십시오."),
    (r"큰\s+의의를\s+(지닙니다|갖습니다)", "REJECT", "공허한 수식어 '큰 의의를 지닙니다' 감지."),
    (r"매우\s+중요하다고\s+할\s+수\s+있습니다", "REJECT", "AI 특유의 모호한 피동 단정 '매우 중요하다고 할 수 있습니다' 감지."),
    (r"~?라\s+할\s+수\s+있겠습니다", "WARNING", "AI 피동/간접 화법 감지. 명확한 종결 어미(~이다, ~한다)를 사용하십시오."),
    (r"~?에\s+다름\s+아닙니다", "REJECT", "일본어 번역투/AI 관용구 '~에 다름 아닙니다' 감지."),
    (r"~?의\s+경우에\s+있어서", "REJECT", "번역투 '~의 경우에 있어서' 감지. '~의 경우', '~할 때'로 간결화하십시오."),
    (r"주목할\s+만한\s+점은", "WARNING", "상투적 환기구 '주목할 만한 점은' 감지."),

    # 상투적 아웃트로/결론
    (r"결론적으로\s+(말씀드리면|말하자면)", "REJECT", "AI 전형적 결론 도입구 감지. 상투적 결론 대신 실무 점검 체크리스트로 마무리하십시오."),
    (r"지금까지\s+.*?에\s+대해\s+(알아보았습니다|살펴보았습니다)", "REJECT", "AI 클로징 멘트 '~에 대해 알아보았습니다' 감지. 기계적 정리를 금지합니다."),
    (r"앞으로도\s+.*?많은\s+관심\s+부탁드립니다", "WARNING", "마케팅 블로그형 맺음말 감지. 기술 백서다운 전문적 마무리를 적용하십시오."),
]


class AntiAiClicheRule(BaseRule):
    """AI 클리셰 & 기계적 번역투 박멸 규칙 (Gate 2)"""

    rule_id = "G2_AI_CLICHE"
    gate_id = "GATE_2"
    gate_name = "AI 클리셰 & 기계적 번역투 박멸"
    description = "영문 20여 개 / 국문 13개 AI 클리셰 정규식 패턴 검출 (코드 블록 제외)"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        is_english = ctx.is_english()
        patterns = EN_AI_CLICHE_PATTERNS if is_english else KO_AI_CLICHE_PATTERNS

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
                    sev = "REJECT" if (severity == "REJECT" or ctx.strict_mode) else "WARNING"
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id=self.rule_id,
                        severity=sev,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=f"{msg} (탐지 패턴: '{pattern}')",
                        fix_hint="AI 특유의 진부한 미사여구를 삭제하고, 현업 엔지니어의 담백하고 직관적인 실무 표현으로 교체하십시오."
                    ))

        return violations
