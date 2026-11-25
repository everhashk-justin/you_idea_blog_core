#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
🏛️ 철벽 게이트 검증 시스템 (Ironclad Gatekeeper Verification System)
================================================================================
파일 명칭: ironclad_gatekeeper.py
버전: 1.0.0 (Production Master)
작성 목적:
  AI의 주관적 의지나 다짐에 기대지 않고, 물리적·소프트웨어적으로 글의 완전무결함을
  검증하여 낮은 품질의 글 발행을 원천 차단(Hard Block)하는 기계적 품질 게이트웨이.

적용 대상:
  1. 글로벌 영문 개발 블로그 (dev.ideaspot360.com / markets.ideaspot360.com)
  2. 국내 국문 티스토리 블로그 (softwin.tistory.com - 트러블슈팅 & 마스터 챕터)
  3. 국내 국문 네이버 블로그 생태계 (solidlog, tidynote, infopiece)
  4. 기타 생태계 블로그 (stock.ideaspot360.com, gear.ideaspot360.com 등)

핵심 철학:
  - ZERO EXTERNAL DEPENDENCY: 파이썬 표준 라이브러리(Standard Library)만으로 100% 구동.
  - HARD BLOCK BY DEFAULT: 치명적 위반(AI 클리셰, 억지 스토리, 엔지니어링 필수요소 누락,
    마크다운 문법 결함, 의료법 위반 등) 적발 시 즉각 Exit Code 1로 발행 차단.
  - TRANSPARENT FEEDBACK: 위반 행 번호, 매칭된 텍스트 스니펫, 구체적 교정 가이드라인(Fix Hint) 즉시 출력.
  - ALL-IN-ONE SINGLE FILE: 다른 블로그 전담 에이전트에게 파일 1개만 전달하면 즉시 복제 및 적용 가능.

7대 검증 게이트 (7-Layer Ironclad Verification Gates) -> 12대 확장 (12-Layer):
  [Gate 1] 구조 & 마크다운 무결성 (YAML Frontmatter, 코드 블록 짝 맞춤, 최소 분량)
  [Gate 2] AI 클리셰 & 기계적 번역투 박멸 (국문 40+ 규칙, 영문 40+ 규칙 정밀 정규식)
  [Gate 3] 억지 스토리 & 작위적 연출 차단 (새벽 몇 시 알람, 식은땀, 패닉 등 소설화 원천 배제)
  [Gate 4] 실무 엔지니어링 5대 아티팩트 검증 (Raw Log, Wrong Fix, Unified Diff, Root Cause, CLI Verify)
  [Gate 5] 사족 & 중언부언 차단 (도입부 과다 서술, 판에 박힌 결론 재요약)
  [Gate 6] 맞춤법, 오타 및 플랫폼별 특화 규격 (네이버 의료법/금지어, 이미지 링크 표기, 해시태그 / 기어 도안 포맷·실존·오버랩 검증)
  [Gate 7] 보안 & 시크릿 누출 방벽 (API Key, AWS, 프라이빗 키 누출 차단)
  [Gate 8] 법적 리스크 & 컴플라이언스 방벽 (자본시장법·금소법, 의료법·식품표시광고법, 공정위 표시광고법, 공공누리 KOGL, 영문 SEC 글로벌 규제)
  [Gate 9] 예약 발행 무결성 및 안티봇 지터 방벽 (선별적 예약 감지, 미래 일시 10분 버퍼 검증, 00분/00초 정각 안티봇 금지, 일반글 선별 스킵)
  [Gate 10] 공인 실측 출처 필수 귀속 관문 (Frontmatter fact_check_sources, verification_date 및 본문 인라인/인용 출처 필수)
  [Gate 11] 도메인별 이론 정합성 및 수치 환각 차단 관문 (복지/세무 2026 기준, 건기식 오메가3/마그네슘 분자구조/흡수율, 개발 sysctl/커널/K8s, 증시 연준 순유동성/SEC 양식)
  [Gate 12] 실시간 팩트체크 및 기억 의존 환각 탐지기 (모호한 시점 지시어, 가상 API/CLI 플래그, 미인증 통계 수치, 리브랜딩/과거 고착 탐지)
================================================================================
"""

import os
import sys
import re
import argparse
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 🎨 터미널 컬러 서식 (ANSI Escape Codes)
# ==============================================================================
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


# ==============================================================================
# 📊 데이터 모델 정의 (Data Models)
# ==============================================================================
@dataclass
class Violation:
    gate_id: str          # GATE_1 ~ GATE_6
    gate_name: str        # 게이트 명칭
    rule_id: str          # 상세 규칙 식별자
    severity: str         # "REJECT" (발행 차단) 또는 "WARNING" (경고/감점)
    line_number: int      # 위반 위치 (1-based, 0이면 전체 레벨)
    snippet: str          # 문제의 문장/스니펫
    message: str          # 위반 사유 설명
    fix_hint: str         # 구체적 교정 가이드


@dataclass
class GateReport:
    file_path: str
    platform: str
    is_passed: bool
    score: int
    reject_count: int
    warning_count: int
    violations: List[Violation] = field(default_factory=list)
    is_reserved: bool = False
    reserve_date: Optional[str] = None
    reserve_time: Optional[str] = None
    target_dt: Optional[datetime] = None

    @property
    def passed(self) -> bool:
        return self.is_passed

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "platform": self.platform,
            "is_passed": self.is_passed,
            "score": self.score,
            "reject_count": self.reject_count,
            "warning_count": self.warning_count,
            "is_reserved": self.is_reserved,
            "reserve_date": self.reserve_date,
            "reserve_time": self.reserve_time,
            "target_dt": self.target_dt.isoformat() if self.target_dt else None,
            "violations": [asdict(v) for v in self.violations]
        }


# ==============================================================================
# 📜 룰셋 데이터베이스 (Ironclad Ruleset Database)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. 영문 AI 클리셰 & 상투어 금지 룰셋 (English Anti-AI Clichés)
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 2. 국문 AI 클리셰 & 상투어 금지 룰셋 (Korean Anti-AI Clichés)
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 3. 억지 스토리 & 작위적 연출 금지 룰셋 (No-Forced-Drama Patterns)
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 4. 네이버 블로그 특화 규격 & 법적 리스크 룰셋 (Naver Specific Rules)
# ------------------------------------------------------------------------------
NAVER_HEALTH_FORBIDDEN = [
    (r"치료", "REJECT", "[의료법 위반 방벽] 건기식 포스팅에 '치료' 단어 100% 금지. '식약처 고시 기능성 보충', '체내 메커니즘 지원' 등으로 대체하십시오."),
    (r"완치", "REJECT", "[의료법 위반 방벽] '완치' 단어 100% 금지."),
    (r"특효약", "REJECT", "[의료법 위반 방벽] '특효약' 과장 광고 단어 100% 금지."),
    (r"완벽\s*예방", "REJECT", "[의료법 위반 방벽] '완벽 예방' 표방 금지."),
    (r"항암", "REJECT", "[의료법 위반 방벽] 질병 치유/항암 표방 절대 금지."),
    (r"만병통치", "REJECT", "[의료법 위반 방벽] '만병통치' 표방 금지."),
    (r"약효", "REJECT", "[의료법 위반 방벽] 건기식에 '약효' 표현 금지. '생체이용률', '흡수 기전' 등으로 대체."),
]

# ------------------------------------------------------------------------------
# 5. 플랫폼 카테고리 정의
# ------------------------------------------------------------------------------
DEV_OFFICIAL_CATEGORIES = [
    "Cloud & DevOps",
    "Database & Storage",
    "Systems & Networking"
]

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

# ------------------------------------------------------------------------------
# 6. 법적 리스크 & 컴플라이언스 룰셋 데이터베이스 (Legal & Compliance Rulesets)
# ------------------------------------------------------------------------------

# [6-1] 자본시장법 & 금융소비자보호법(금소법) 방벽
# (자본시장법 제55조 손실보전 금지, 금소법 제19조~21조 부당권유행위 금지)
CAPITAL_MARKETS_RULES = [
    # 1. 원금보장 및 손실보전 약정
    (
        r"원금(?:을|은|도|\s*)?\s*보장(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*아님|이\s*불가|을\s*하지\s*않|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_PRINCIPAL_GUARANTEE",
        "[자본시장법·금소법 방벽] '원금 보장' 표방 금지 (자본시장법 제55조 및 금소법 제21조). 금융투자상품은 원금 손실 위험이 수반되므로 원금을 보장할 수 없습니다.",
        "원금 보장 표현을 삭제하고 원금 손실 가능성 및 투자 위험 고지 문구를 삽입하십시오."
    ),
    (
        r"원금\s*(?:손실|손실이|손실은)\s*(?:없는|없음|없고|0%|제로)",
        "REJECT",
        "G8_FIN_NO_LOSS_CLAIM",
        "[자본시장법·금소법 방벽] '원금 손실 없음/0%' 단언 금지 (금소법 제19조 부당권유행위).",
        "원금 손실이 없다는 비현실적인 단언을 삭제하고 시장 변동성 위험을 명시하십시오."
    ),
    (
        r"원금(?:을|의|은|\s*)?\s*(?:전액\s*)?보존(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*불가|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_PRINCIPAL_PRESERVATION",
        "[자본시장법·금소법 방벽] '원금 보존' 약정 표현 금지 (자본시장법 제55조).",
        "원금 보존 표현을 삭제하십시오."
    ),
    (
        r"원금\s*(?:회수|반환)\s*100%",
        "REJECT",
        "G8_FIN_PRINCIPAL_RECOVERY",
        "[자본시장법·금소법 방벽] '원금 회수 100%' 표방 금지.",
        "원금 회수 100% 표현을 삭제하십시오."
    ),
    (
        r"손실(?:을|은|\s*)?\s*(?:전액\s*)?보전(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*불가|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_LOSS_COMPENSATION",
        "[자본시장법 제55조 위반] '손실 보전' 약속 금지.",
        "손실 보전 표현을 삭제하십시오."
    ),

    # 2. 확정수익 및 무위험 고수익 표방
    (
        r"확정\s*수익(?:률)?(?!\s*(?:을\s*보장하지\s*않|이\s*아닙|은\s*없|을\s*약속하지\s*않))",
        "REJECT",
        "G8_FIN_CONFIRMED_PROFIT",
        "[자본시장법·금소법 방벽] '확정 수익(률)' 표방 금지 (금소법 제19조). 예적금을 제외한 금융투자상품에 확정 수익률을 표방할 수 없습니다.",
        "확정 수익 표현을 삭제하고 기대 수익과 시나리오별 리스크를 균형 있게 기술하십시오."
    ),
    (
        r"무위험\s*고수익",
        "REJECT",
        "G8_FIN_RISK_FREE_HIGH_RETURN",
        "[자본시장법·금소법 방벽] '무위험 고수익' 기만 표현 금지 (금소법 제19조).",
        "고수익에는 상응하는 고위험이 수반됨을 명시하십시오."
    ),
    (
        r"위험\s*없는\s*(?:고수익|투자)",
        "REJECT",
        "G8_FIN_RISK_FREE_INVESTMENT",
        "[자본시장법·금소법 방벽] '위험 없는 투자' 표방 금지.",
        "투자 리스크를 객관적으로 명시하십시오."
    ),
    (
        r"수익(?:률)?(?:을|은|\s*)?\s*보장(?!\s*(?:하지\s*않|되지\s*않|은\s*없|이\s*없|이\s*아닙|이\s*아님|이\s*불가|을\s*하지\s*않|할\s*수\s*없))",
        "REJECT",
        "G8_FIN_GUARANTEED_PROFIT",
        "[자본시장법·금소법 방벽] '수익(률) 보장' 표현 금지.",
        "수익 보장 표현을 삭제하십시오."
    ),
    (
        r"100%\s*(?:수익|수익률|원금보장)",
        "REJECT",
        "G8_FIN_100_PERCENT_PROFIT",
        "[자본시장법·금소법 방벽] '100% 수익(률)' 단언 금지.",
        "100% 수익 단언을 배제하십시오."
    ),
    (
        r"손실률\s*0%",
        "REJECT",
        "G8_FIN_ZERO_LOSS_RATE",
        "[자본시장법·금소법 방벽] '손실률 0%' 표방 금지.",
        "손실 위험을 솔직하게 기술하십시오."
    ),

    # 3. 사기성 리딩방 어투 및 시세조종 조장
    (
        r"VIP\s*(?:리딩|추천|정보)",
        "REJECT",
        "G8_FIN_VIP_LEADING",
        "[자본시장법 방벽] 불법 사기성 리딩방 어투 'VIP 리딩/추천' 감지 (자본시장법 위반 소지).",
        "사기성 리딩방 마케팅 용어를 전면 삭제하십시오."
    ),
    (
        r"급등주\s*(?:추천|대공개|포착|공개|발굴|무료)",
        "REJECT",
        "G8_FIN_SURGE_STOCK",
        "[자본시장법 방벽] 선동적 투기 조장 '급등주 추천/포착' 감지.",
        "투기 조장 어휘를 삭제하고 펀더멘털 및 매크로 지표 분석으로 전환하십시오."
    ),
    (
        r"특급\s*(?:호재|정보|재료)",
        "REJECT",
        "G8_FIN_SPECIAL_INSIDER_INFO",
        "[자본시장법 방벽] 사기성 미공개 정보 유혹 어투 '특급 호재/재료' 감지.",
        "객관적 공시 및 시장 뉴스 기반으로 서술하십시오."
    ),
    (
        r"무조건\s*(?:폭등|상승|상한가)",
        "REJECT",
        "G8_FIN_UNCONDITIONAL_SURGE",
        "[자본시장법 방벽] '무조건 폭등/상승/상한가' 선동적 과장 표현 감지.",
        "가격 변동을 확언하는 어투를 배제하십시오."
    ),
    (
        r"내일\s*(?:무조건\s*)?상한가",
        "REJECT",
        "G8_FIN_TOMORROW_UPPER_LIMIT",
        "[자본시장법 방벽] '내일 상한가' 허위 유혹 표현 감지.",
        "내일 상한가 표현을 삭제하십시오."
    ),
    (
        r"세력\s*(?:매집|입성|작전)(?:주)?",
        "REJECT",
        "G8_FIN_MARKET_MANIPULATION",
        "[자본시장법 방벽] '세력 매집/작전주' 등 시세조종 및 불법 투기 조장 어휘 감지 (자본시장법 제178조).",
        "세력/작전 관련 불법 투기 표현을 전면 삭제하십시오."
    ),
    (
        r"선취매(?:\s*완료|\s*종목)?",
        "REJECT",
        "G8_FIN_FRONT_RUNNING",
        "[자본시장법 방벽] 불법 선취매 표방 어투 감지 (자본시장법 불공정거래행위 소지).",
        "선취매 표현을 삭제하십시오."
    ),
    (
        r"단타\s*리딩방",
        "REJECT",
        "G8_FIN_LEADING_ROOM",
        "[자본시장법 방벽] '단타 리딩방' 등 불법 유사투자자문 어휘 감지.",
        "리딩방 홍보 및 유인 어휘를 삭제하십시오."
    ),
    (
        r"목표가\s*(?:찍고|도달\s*확정)",
        "REJECT",
        "G8_FIN_GUARANTEED_TARGET_PRICE",
        "[자본시장법 방벽] '목표가 도달 확정' 표방 감지.",
        "목표가 도달을 확언하지 마십시오."
    ),

    # 4. 미등록 투자자문 소지 표현
    (
        r"무료\s*(?:종목\s*)?상담",
        "REJECT",
        "G8_FIN_UNREGISTERED_ADVICE_CONSULT",
        "[자본시장법 제17조 위반] 미등록 투자자문 소지 '무료 종목 상담' 감지.",
        "개별 종목 상담 유도 문구를 삭제하십시오."
    ),
    (
        r"1:1\s*(?:투자\s*)?(?:리딩|자문|코칭|상담)",
        "REJECT",
        "G8_FIN_UNREGISTERED_1ON1",
        "[자본시장법 제17조 위반] 불법 '1:1 투자 리딩/자문' 표현 감지.",
        "1:1 투자 자문 어휘를 삭제하십시오."
    ),
    (
        r"(?:지금|오늘)\s*당장\s*(?:매수|매도)하십시오",
        "REJECT",
        "G8_FIN_URGENT_TRADE_ORDER",
        "[자본시장법 위반] 일방적 매매 지시 어투 감지.",
        "독자에게 특정 매매 행위를 강요하지 마십시오."
    ),
    (
        r"(?:무조건|반드시)\s*(?:풀매수|매수|매도)하세요",
        "REJECT",
        "G8_FIN_FORCED_TRADE_ORDER",
        "[자본시장법 위반] 단정적 매수/매도 권유 어투 감지.",
        "판단은 투자자 본인의 몫임을 존중하는 기술적 분석으로 서술하십시오."
    ),
    (
        r"종목\s*찍어드립니다",
        "REJECT",
        "G8_FIN_PICK_STOCK",
        "[자본시장법 위반] 불법 종목 추천 어투 감지.",
        "종목 찍어주기 식 어투를 배제하십시오."
    ),
]

KO_FINANCIAL_DISCLAIMER_PATTERNS = [
    r"투자\s*(?:유의사항|경고|참고)",
    r"면책\s*(?:고지|문구)",
    r"투자를?\s*(?:권유|자문|추천|판단|책임)",
    r"권유가\s*아닙",
    r"자문이\s*아닙",
    r"추천이\s*아닙",
    r"원금\s*손실",
    r"손실\s*(?:의\s*)?위험",
    r"본\s*(?:글|포스팅|아티클|자료|콘텐츠)은?는?\s*.*?(?:참고|정보\s*제공)",
    r"정보\s*제공\s*목적",
    r"투자\s*결정은\s*본인",
    r"투자의\s*책임은\s*(?:투자자|본인)",
    r"금융소비자보호법",
    r"금소법",
]

# [6-2] 의료법 & 건강기능식품법(식품표시광고법) 방벽
# (식품표시광고법 제8조 부당한 표시·광고 금지, 의료법 제56조 의료광고 금지)
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

# 하위 호환성 유지용 키워드 리스트
HEALTH_DISCLAIMER_KEYWORDS = [
    "면책", "의사의 진료", "처방을 대신", "의료 전문가와 상담", "일반적인 건강 정보",
    "전문 의료인", "의사 또는 약사와 상담", "의약품이 아님", "진단 및 처방", "의료인의 진단"
]

# [6-3] 공정거래위원회 추천·보증 심사지침 (대가성 표시광고법)
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

COVERT_AD_PATTERNS = [
    (
        r"(?:내돈내산|직접\s*구매한|100%\s*자비).*?(?:link\.coupang\.com|amzn\.to|partners\.coupang)",
        "REJECT",
        "G8_FTC_COVERT_MY_MONEY",
        "[공정위 표시광고법 위반] 제휴 링크가 포함되어 있으나 '내돈내산/자비 구매'로 소비자를 오도하는 기만적 스텔스 마케팅 감지.",
        "'내돈내산' 허위 표기를 삭제하고 공정위 표준 대가성 문구를 기재하십시오."
    ),
    (
        r"광고\s*아닙니다.*?(?:link\.coupang\.com|partners\.coupang|amzn\.to)",
        "REJECT",
        "G8_FTC_COVERT_NOT_AD",
        "[공정위 표시광고법 위반] 제휴 수수료 링크가 있으면서 '광고 아닙니다'라고 허위 주장하는 행위 감지.",
        "광고 부인 문구를 삭제하고 수수료 제공 사실을 명시하십시오."
    ),
]

# [6-4] 공공누리(KOGL) 저작권 출처 표기 의무
POLICY_TOPIC_PATTERNS = [
    r"정부\s*(?:지원금|정책|보조금)",
    r"복지\s*(?:지원금|정책|급여|혜택)",
    r"청년도약계좌",
    r"청년내일저축계좌",
    r"국민기초생활보장",
    r"근로장려금",
    r"자녀장려금",
    r"소상공인\s*(?:지원금|손실보전금|방역지원금)",
    r"국민취업지원제도",
    r"긴급복지지원",
    r"보건복지부",
    r"고용노동부",
    r"국세청\s*(?:환급금|연말정산)",
    r"정부24",
    r"복지로",
    r"행정안전부",
    r"중소벤처기업부",
]

KOGL_ATTRIBUTION_PATTERNS = [
    r"공공누리",
    r"KOGL",
    r"제[1-4]유형",
    r"공공저작물",
    r"출처\s*:\s*(?:대한민국\s*)?정책브리핑",
    r"출처\s*:\s*공공데이터포털",
    r"출처\s*:\s*(?:보건복지부|고용노동부|국세청|행정안전부|정부24|복지로|기획재정부|금융위원회|중소벤처기업부)",
    r"본\s*저작물은\s*.*?(?:공공누리|출처표시)",
    r"공공기관\s*저작물",
]

# [6-5] 영문 글로벌 금융 규제 방벽 (SEC Compliance & Global Regulations)
GLOBAL_FINANCIAL_RULES = [
    # 1. Guaranteed Returns & Risk-Free Claims
    (
        r"(?i)(?<!no\s)(?<!not\s)\bguaranteed\s+(?:returns?|profits?|yields?|income|gains?)\b",
        "REJECT",
        "G8_GLOBAL_GUARANTEED_RETURNS",
        "[SEC Global Compliance] Illegal guaranteed returns claim detected (US SEC Rule 10b-5 / FINRA Rule 2210). All securities investments carry market risk.",
        "Remove any guarantee of returns and state potential volatility and market risks objectively."
    ),
    (
        r"(?i)\brisk-free\s+(?:profits?|returns?|yields?|investments?)\b",
        "REJECT",
        "G8_GLOBAL_RISK_FREE_PROFIT",
        "[SEC Global Compliance] Misleading 'risk-free profit/return' claim detected.",
        "Eliminate 'risk-free' claims and provide balanced risk disclosure."
    ),
    (
        r"(?i)\b100%\s*(?:guaranteed|win\s*rate|profit|success\s*rate)\b",
        "REJECT",
        "G8_GLOBAL_100PCT_WIN_RATE",
        "[SEC Global Compliance] Unrealistic '100% win rate / profit' claim detected.",
        "Remove false certainty claims regarding trading performance."
    ),
    (
        r"(?i)\bcannot\s+lose(?:\s+money)?\b",
        "REJECT",
        "G8_GLOBAL_CANNOT_LOSE",
        "[SEC Global Compliance] Deceptive 'cannot lose money' claim detected.",
        "Acknowledge the risk of financial loss in all market conditions."
    ),
    (
        r"(?i)\bzero\s+risk\s+invest(?:ing|ment)\b",
        "REJECT",
        "G8_GLOBAL_ZERO_RISK",
        "[SEC Global Compliance] 'Zero risk investment' claim detected.",
        "Remove zero risk claim and state actual risk parameters."
    ),
    (
        r"(?i)\bguaranteed\s+(?:to\s+double|10x|100x)\b",
        "REJECT",
        "G8_GLOBAL_GUARANTEED_MULTIPLIER",
        "[SEC Global Compliance] Fraudulent multiplier guarantee ('guaranteed 10x') detected.",
        "Remove multiplier promises."
    ),
    (
        r"(?i)\bunconditional\s+returns?\b",
        "REJECT",
        "G8_GLOBAL_UNCONDITIONAL_RETURNS",
        "[SEC Global Compliance] 'Unconditional return' claim detected.",
        "Remove unconditional return statements."
    ),

    # 2. Illegal Investment Advice / Stock Solicitation / Market Manipulation
    (
        r"(?i)\bbuy\s+this\s+stock\s+(?:now|today|immediately)\b",
        "REJECT",
        "G8_GLOBAL_URGENT_BUY_CALL",
        "[SEC Compliance] Unregistered investment solicitation / urgent trade command detected (Investment Advisers Act of 1940).",
        "Present objective fundamental and quantitative analysis without direct buy/sell imperatives."
    ),
    (
        r"(?i)\bsell\s+this\s+stock\s+(?:now|today|immediately)\b",
        "REJECT",
        "G8_GLOBAL_URGENT_SELL_CALL",
        "[SEC Compliance] Direct sell command detected.",
        "Replace trading commands with neutral valuation commentary."
    ),
    (
        r"(?i)\bguaranteed\s+target\s+price\b",
        "REJECT",
        "G8_GLOBAL_TARGET_PRICE_GUARANTEE",
        "[SEC Compliance] Deceptive 'guaranteed target price' claim detected.",
        "State price targets as analyst estimates with associated uncertainty."
    ),
    (
        r"(?i)\bpump\s+and\s+dump\b",
        "REJECT",
        "G8_GLOBAL_PUMP_AND_DUMP",
        "[SEC Rule 10b-5] Pump-and-dump market manipulation language detected.",
        "Remove all references promoting artificial volume or price inflation."
    ),
    (
        r"(?i)\binsider\s+(?:tip|trading|leak)\b",
        "REJECT",
        "G8_GLOBAL_INSIDER_TIP",
        "[SEC Rule 10b5-1] Illegal insider information claim detected.",
        "Rely strictly on publicly disclosed SEC filings and verifiable market data."
    ),
    (
        r"(?i)\byou\s+must\s+buy\s+this\b",
        "REJECT",
        "G8_GLOBAL_MUST_BUY",
        "[SEC Compliance] Coercive trade recommendation detected.",
        "Frame conclusions as analytical insights rather than mandates."
    ),
    (
        r"(?i)\bguaranteed\s+to\s+skyrocket\b",
        "REJECT",
        "G8_GLOBAL_SKYROCKET_CLAIM",
        "[SEC Compliance] Sensationalist stock pumping language detected.",
        "Remove sensationalist hype."
    ),
    (
        r"(?i)\bexclusive\s+(?:trading\s+signal|stock\s+alert)\b",
        "REJECT",
        "G8_GLOBAL_EXCLUSIVE_SIGNAL",
        "[SEC Compliance] Boiler-room style 'exclusive trading signal' lure detected.",
        "Remove boiler-room solicitation language."
    ),
]

GLOBAL_DISCLAIMER_PATTERNS = [
    r"(?i)\bdisclaimer\b",
    r"(?i)\bnot\s+financial\s+advice\b",
    r"(?i)\bnot\s+an\s+investment\s+advice\b",
    r"(?i)\binformational\s+purposes\s+only\b",
    r"(?i)\beducational\s+purposes\s+only\b",
    r"(?i)\bdo\s+your\s+own\s+research\b",
    r"(?i)\bpast\s+performance\s+(?:is\s+no|does\s+not)\s+guarantee\b",
    r"(?i)\bconsult\s+a\s+licensed\s+financial\s+advisor\b",
    r"(?i)\bfor\s+research\s+purposes\s+only\b",
    r"(?i)\brisk\s+of\s+loss\b",
]

# ------------------------------------------------------------------------------
# 7. Gate 10: 공인 실측 출처 필수 귀속 룰셋 (Fact-Check Attribution Patterns)
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 8. Gate 11: 도메인별 이론 정합성 및 수치 환각 차단 룰셋 (Theory & Numerical Integrity)
# ------------------------------------------------------------------------------

# [11-1] 정부 정책 / 복지 / 생활 금융 (solidlog)
WELFARE_TAX_RULES = [
    (
        r"2026년.*?(?:기준\s*중위소득|중위소득).*?(?:50[0-9]|51[0-9]|52[0-9]|53[0-9]|54[0-9]|55[0-9]|56[0-9]|57[0-9]|58[0-9])만\s*원",
        "REJECT",
        "G11_WELFARE_OUTDATED_MEDIAN_INCOME",
        "[기준 중위소득 과거 수치 왜곡] 2026년 4인 가구 기준 중위소득은 6,097,773원(약 609만 원)입니다. 2023년(540만 원)이나 2024년(572만 원) 과거 수치를 제시하는 오류를 금지합니다.",
        "2026년 최신 고시 기준 4인 가구 609만 7,773원으로 수치를 바로잡으십시오."
    ),
    (
        r"생계급여.*?(?:선정\s*기준|수급\s*자격|소득\s*인정액|지원\s*기준).*?중위소득\s*30%",
        "REJECT",
        "G11_WELFARE_OUTDATED_LIVELIHOOD_BENEFIT",
        "[생계급여 선정기준 구 규정 왜곡] 생계급여 선정기준은 2024년부터 기준 중위소득 32%로 상향되었습니다. 30%는 2023년 이전 폐지된 구 규정입니다.",
        "생계급여 선정 기준을 '기준 중위소득 32% 이하'로 수정하십시오."
    ),
    (
        r"청년도약계좌.*?(?:만기\s*2년|2년\s*만기|총급여\s*3,?600만\s*원|3,?600만\s*원\s*이하\s*(?:신청|가입))",
        "REJECT",
        "G11_WELFARE_YOUTH_ACCOUNT_CONFUSION",
        "[청년도약계좌 조건 왜곡] 청년도약계좌는 만기 5년, 총급여 7,500만 원 이하(종합소득 6,300만 원 이하) 기준입니다. 만기 2년 및 총급여 3,600만 원은 폐지된 청년희망적금 스펙과의 혼동입니다.",
        "만기 5년 및 총급여 7,500만 원 이하로 조건을 바로잡으십시오."
    ),
    (
        r"(?:2026년|올해).*?(?:금투세|금융투자소득세).*?(?:시행|도입|과세된다|적용된다|시행되어)",
        "REJECT",
        "G11_TAX_ABOLISHED_FINANCIAL_INVESTMENT_TAX",
        "[금융투자소득세 폐지 사실 미반영 환각] 금융투자소득세(금투세)는 폐지가 확정되었습니다. 2026년에 금투세가 시행되거나 과세된다는 서술은 사전학습 환각입니다.",
        "금투세 폐지 확정 사실을 반영하여 서술을 수정하거나 관련 문장을 삭제하십시오."
    ),
    (
        r"식대\s*(?:비과세|비과세\s*한도).*?월\s*10만\s*원",
        "REJECT",
        "G11_TAX_OUTDATED_MEAL_TAX_EXEMPTION",
        "[식대 비과세 한도 구 규정 오류] 식대 비과세 한도는 2023년 개정 이후 월 20만 원입니다. 월 10만 원은 구 규정입니다.",
        "식대 비과세 한도를 '월 20만 원'으로 수정하십시오."
    ),
]

# [11-2] 건강 / 영양제 성분 과학 (infopiece)
HEALTH_NUTRITION_RULES = [
    (
        r"EE형.*?(?:글리세롤\s*뼈대|글리세롤\s*기반|글리세롤에\s*결합)",
        "REJECT",
        "G11_HEALTH_FALSE_EE_STRUCTURE",
        "[오메가3 분자구조 왜곡] EE형(Ethyl Ester)은 글리세롤 뼈대가 없으며 에탄올(에틸알코올) 1분자에 지방산 1개가 결합된 형태입니다.",
        "EE형의 결합 구조를 '에탄올-지방산 에스테르 결합'으로 정정하십시오."
    ),
    (
        r"rTG형.*?(?:에틸\s*에스테르\s*(?:형태|구조)|에탄올\s*결합)",
        "REJECT",
        "G11_HEALTH_FALSE_RTG_STRUCTURE",
        "[오메가3 분자구조 왜곡] rTG형(re-esterified TG)은 EE형을 재에스테르화하여 글리세롤 뼈대에 결합한 형태이며 에틸에스테르 형태가 아닙니다.",
        "rTG형을 '글리세롤 뼈대에 불포화지방산 3개가 재결합한 구조'로 설명하십시오."
    ),
    (
        r"(?<!r)(?:자연\s*)?TG형.*?(?:가장\s*순도가\s*높|고순도\s*(?:7[0-9]|8[0-9]|9[0-9])%|순도\s*(?:7[0-9]|8[0-9]|9[0-9])%)",
        "REJECT",
        "G11_HEALTH_FALSE_TG_PURITY",
        "[오메가3 순도 왜곡] 자연 TG형은 불필요한 포화지방산이 포함되어 순도가 약 30%로 가장 낮습니다. 80% 이상의 고순도는 EE형 또는 rTG형입니다.",
        "자연 TG형은 순도가 30% 수준으로 낮고, 고순도 정제 형태는 rTG/EE형임을 명시하십시오."
    ),
    (
        r"EE형.*?(?:생체이용률|흡수율).*?(?:rTG\s*보다|더\s*높|가장\s*우수|가장\s*뛰어)",
        "REJECT",
        "G11_HEALTH_FALSE_EE_BIOAVAILABILITY",
        "[생체이용률 과학적 왜곡] EE형은 체내 흡수를 위해 담즙산과 리파아제의 에탄올 분해가 필요하여 rTG형보다 생체이용률(흡수율)이 현저히 낮습니다.",
        "생체이용률은 rTG형이 가장 높고 EE형은 상대적으로 낮음을 객관적으로 기술하십시오."
    ),
    (
        r"IFOS.*?(?:10\s*스타|10-?Star|3\s*스타\s*최고)",
        "REJECT",
        "G11_HEALTH_FALSE_IFOS_GRADE",
        "[IFOS 인증 규격 왜곡] IFOS(International Fish Oil Standards)의 최고 품질 등급은 5-Star입니다. 10스타 등 비존재 등급 표기를 금지합니다.",
        "IFOS 최고 등급인 '5-Star'로 바로잡으십시오."
    ),
    (
        r"IFOS.*?(?:식약처\s*인증\s*면제|품목제조신고\s*면제)",
        "REJECT",
        "G11_HEALTH_FALSE_IFOS_EXEMPTION",
        "[식약처 규제 오인] IFOS 등 해외 민간 인증을 받더라도 대한민국 식약처(MFDS)의 기능성 원료 인정 및 품목제조신고는 법적으로 면제되지 않습니다.",
        "식약처 건강기능식품 정규 인정 절차는 필수임을 명시하십시오."
    ),
    (
        r"중금속.*?(?:0\.000%|완전히\s*0%|절대\s*0%|분자\s*단위까지\s*완전\s*제거)",
        "REJECT",
        "G11_HEALTH_FALSE_ZERO_HEAVY_METALS",
        "[비과학적 허위 과장 단언] 분석 화학적 검출한계(LOD/LOQ)상 중금속이 '0.000% 완전 제로'라는 주장은 불가능한 비과학적 허위 과장입니다.",
        "식약처 및 IFOS 기준치 이하 적합 판정 또는 불검출 규격으로 담백하게 기술하십시오."
    ),
    (
        r"산화\s*마그네슘.*?(?:흡수율이\s*가장\s*높|생체이용률이\s*가장\s*우수|가장\s*흡수가\s*잘)",
        "REJECT",
        "G11_HEALTH_FALSE_OXIDE_ABSORPTION",
        "[마그네슘 흡수율 기전 왜곡] 산화 마그네슘은 원소 함량은 높으나 물에 녹지 않아 생체이용률(흡수율)이 약 4%로 가장 낮습니다.",
        "산화 마그네슘은 흡수율이 낮고 완하작용(배변) 위주이며, 고흡수율 형태는 킬레이트/유기산 마그네슘임을 명시하십시오."
    ),
]

# [11-3] 기술 / 개발 / 인프라 (dev, softwin, tidynote)
TECH_INFRA_RULES = [
    (
        r"net\.ipv4\.tcp_tw_recycle",
        "REJECT",
        "G11_TECH_REMOVED_SYSCTL_TW_RECYCLE",
        "[제거된 리눅스 커널 파라미터] net.ipv4.tcp_tw_recycle은 Linux 4.12 커널에서 영구 제거(Removed)되었습니다. NAT 환경에서 패킷 드롭을 유발하는 대표적인 과거 기억 환각 파라미터입니다.",
        "tcp_tw_recycle을 삭제하고 net.ipv4.tcp_tw_reuse = 1 및 SO_REUSEPORT 아키텍처로 대체하십시오."
    ),
    (
        r"vm\.swappiness\s*=\s*(?:1[0-9]{2}|[2-9][0-9]{2}|-[0-9]+)\b",
        "REJECT",
        "G11_TECH_INVALID_SWAPPINESS_BOUNDS",
        "[sysctl 허용 범위 초과] vm.swappiness의 표준 유효 범위는 0~100입니다.",
        "vm.swappiness를 0~100 사이의 실무 권장 값(예: 10, 60 등)으로 지정하십시오."
    ),
    (
        r"net\.ipv4\.tcp_window_scaling\s*=\s*[2-9]\b",
        "REJECT",
        "G11_TECH_INVALID_WINDOW_SCALING_BOOLEAN",
        "[sysctl 불리언 플래그 오류] net.ipv4.tcp_window_scaling은 0(비활성화) 또는 1(활성화) 불리언 값이어야 합니다.",
        "값을 0 또는 1로 설정하십시오."
    ),
    (
        r"apiVersion:\s*(?:extensions/v1beta1|networking\.k8s\.io/v1beta1)",
        "REJECT",
        "G11_TECH_DEPRECATED_K8S_INGRESS_API",
        "[제거된 Kubernetes API 버전] Ingress의 extensions/v1beta1 및 networking.k8s.io/v1beta1은 k8s v1.22에서 영구 제거되었습니다.",
        "최신 표준인 'apiVersion: networking.k8s.io/v1' 및 pathType 명시 스펙을 사용하십시오."
    ),
    (
        r"kubectl\s+run.*?--generator",
        "REJECT",
        "G11_TECH_REMOVED_KUBECTL_GENERATOR",
        "[제거된 kubectl CLI 옵션] kubectl run의 --generator 플래그는 Kubernetes 1.18에서 영구 삭제되었습니다.",
        "kubectl run의 --generator 옵션을 삭제하고 최신 Pod 생성 문법을 사용하십시오."
    ),
    (
        r"docker\s+run.*?--link\b",
        "REJECT",
        "G11_TECH_DEPRECATED_DOCKER_LINK",
        "[폐지된 Docker legacy 옵션] docker run의 --link는 공식적으로 폐지(Deprecated)된 레거시 기능입니다.",
        "사용자 정의 브리지 네트워크(docker network create)를 생성하여 DNS 이름을 통해 컨테이너를 연결하십시오."
    ),
    (
        r"(?:Linux|리눅스\s*커널)\s*(?:2\.\d+|3\.\d+|4\.\d+).*?io_uring",
        "REJECT",
        "G11_TECH_KERNEL_FEATURE_VERSION_MISMATCH",
        "[커널 기능 버전 불일치] io_uring 비동기 I/O 서브시스템은 Linux 커널 5.1에 최초 도입되었습니다. 2.x~4.x 버전 서술은 명백한 오류입니다.",
        "Linux 커널 5.1+ 이상을 기준으로 기술하십시오."
    ),
    (
        r"(?:Linux\s+kernel|리눅스\s*커널)\s*(?:v?\s*)?(?:7\.\d+|8\.\d+)",
        "REJECT",
        "G11_TECH_NONEXISTENT_KERNEL_VERSION",
        "[비존재 가상 커널 버전 환각] 리눅스 커널 7.x/8.x는 존재하지 않는 가상 버전 환각입니다 (현재 리눅스 커널은 6.x 유지).",
        "공식 출시된 Linux 6.x 커널 버전을 명시하십시오."
    ),
]

# [11-4] 증시 / 매크로 / 금융 (stock, markets)
STOCK_MARKETS_RULES = [
    (
        r"(?:연준\s*순유동성|Fed\s*Net\s*Liquidity|Net\s*Liquidity).*?(?:총자산|WALCL|Total\s*Assets)\s*\+\s*(?:TGA|재무부\s*일반계정)",
        "REJECT",
        "G11_STOCK_FED_LIQUIDITY_ADD_TGA",
        "[연준 순유동성 공식 오류] TGA(재무부 일반계정)는 연준 부채 항목으로 상업은행 지준(Reserve)을 흡수하므로 순유동성 산출 시 마이너스(-)로 차감해야 합니다. 더할(+) 수 없습니다.",
        "공식을 'Fed Net Liquidity = WALCL - TGA - ON RRP'로 정정하십시오."
    ),
    (
        r"(?:WALCL|총자산)\s*\+\s*TGA\b",
        "REJECT",
        "G11_STOCK_FED_LIQUIDITY_ADD_TGA",
        "[연준 순유동성 공식 오류] WALCL + TGA는 유동성 산출 공식 오류입니다. TGA는 차감해야 합니다.",
        "WALCL - TGA로 정정하십시오."
    ),
    (
        r"(?:연준\s*순유동성|Fed\s*Net\s*Liquidity|Net\s*Liquidity).*?(?:총자산|WALCL|Total\s*Assets)\s*\+\s*(?:ON\s*RRP|RRP|역레포)",
        "REJECT",
        "G11_STOCK_FED_LIQUIDITY_ADD_RRP",
        "[연준 순유동성 공식 오류] 역레포(ON RRP)는 연준이 시중 잉여 자금을 흡수하는 창구이므로 순유동성 산출 시 반드시 차감(-)해야 합니다.",
        "공식을 'WALCL - TGA - ON RRP'로 바로잡으십시오."
    ),
    (
        r"(?:WALCL|총자산)\s*\+\s*(?:ON\s*RRP|RRP|역레포)",
        "REJECT",
        "G11_STOCK_FED_LIQUIDITY_ADD_RRP",
        "[연준 순유동성 공식 오류] 역레포는 차감(-)해야 합니다.",
        "차감 공식(- ON RRP)으로 정정하십시오."
    ),
    (
        r"(?:Form\s*10-K|10-K).*?(?:분기\s*보고서|분기별\s*공시|Quarterly\s*Report)",
        "REJECT",
        "G11_STOCK_SEC_10K_CONFUSION",
        "[SEC 공시 양식 혼동] Form 10-K는 연간 사업보고서(Annual Report)입니다. 분기 보고서는 Form 10-Q입니다.",
        "Form 10-K를 '연간 사업보고서(Annual Report)'로 바로잡으십시오."
    ),
    (
        r"(?:Form\s*10-Q|10-Q).*?(?:연간\s*보고서|연례\s*보고서|Annual\s*Report)",
        "REJECT",
        "G11_STOCK_SEC_10Q_CONFUSION",
        "[SEC 공시 양식 혼동] Form 10-Q는 분기 보고서(Quarterly Report)입니다. 연간 보고서는 Form 10-K입니다.",
        "Form 10-Q를 '분기 보고서(Quarterly Report)'로 바로잡으십시오."
    ),
    (
        r"(?:Form\s*13F|13F).*?(?:내부자\s*거래|2영업일\s*이내)",
        "REJECT",
        "G11_STOCK_SEC_13F_CONFUSION",
        "[SEC 공시 양식 혼동] Form 13F는 1억 달러 이상 기관투자자의 분기별 지분 보고서입니다. 2영업일 이내 내부자 거래 공시는 Form 4입니다.",
        "기관투자자 분기 지분보고서(Form 13F)와 내부자 거래 공시(Form 4)를 구분하여 정정하십시오."
    ),
]

# ------------------------------------------------------------------------------
# 9. Gate 12: 실시간 팩트체크 및 기억 의존 환각 탐지 룰셋 (Zero-Memory Hallucination)
# ------------------------------------------------------------------------------
VAGUE_TEMPORAL_PATTERNS = [
    r"최근\s*몇\s*년간",
    r"요\s*몇\s*년\s*사이에",
    r"지난\s*몇\s*년간",
    r"최근\s*수년간",
    r"지난\s*수년간",
    r"최근\s*몇\s*년\s*동안",
    r"최근\s*들어\s*급격히",
    r"과거\s*수년간",
    r"\bin\s+recent\s+years\b",
    r"\bover\s+the\s+past\s+few\s+years\b",
    r"\bin\s+the\s+past\s+few\s+years\b",
    r"\bduring\s+the\s+past\s+few\s+years\b",
]

FABRICATED_API_PATTERNS = [
    (r"git\s+push.*?--instant\b", "git push에는 --instant 옵션이 존재하지 않습니다."),
    (r"git\s+commit.*?--auto-magic\b", "git commit에는 --auto-magic 옵션이 존재하지 않습니다."),
    (r"docker\s+run.*?--super-fast\b", "docker run에는 --super-fast 옵션이 존재하지 않습니다."),
    (r"kubectl\s+apply.*?--force-now\b", "kubectl apply에는 --force-now 옵션이 존재하지 않습니다."),
    (r"pip\s+install.*?--auto-fix\b", "pip install에는 --auto-fix 옵션이 존재하지 않습니다."),
    (r"tensorflow\.quantum_nlp\b", "TensorFlow 표준 패키지에는 'quantum_nlp' 모듈이 존재하지 않습니다."),
    (r"os\.super_kill\b", "Python os 모듈에는 'super_kill' 메서드가 존재하지 않습니다."),
    (r"navigator\.getBatteryLevel\b", "웹 배터리 API 메서드는 navigator.getBattery()입니다."),
]

UNREFERENCED_STATISTICS_PATTERNS = [
    r"(?:약\s*)?[0-9]{2,3}%\s*(?:이상|이하|가\s*넘는|에\s*달하는)?\s*(?:의)?\s*(?:개발자|엔지니어|기업|사용자|회사|사람)(?:가|는|이|들의)?",
    r"(?i)\b[0-9]{2,3}%\s+(?:or\s+more\s+of\s+|of\s+)(?:engineers|developers|companies|enterprises|users|organizations)\b",
]

STALE_BRAND_PATTERNS = [
    (r"\bKINDEX\b", "KINDEX는 2022년 10월 'ACE'(한국투자신탁운용)로 리브랜딩되어 소멸된 구형 브랜드입니다. 최신 명칭인 'ACE'를 사용하십시오."),
    (r"\bKBSTAR\b", "KBSTAR는 2024년 7월 'RISE'(KB자산운용)로 리브랜딩되어 소멸된 구형 브랜드입니다. 최신 명칭인 'RISE'를 사용하십시오."),
    (r"\bARIRANG\b", "ARIRANG은 2024년 7월 한화자산운용에 의해 'PLUS'로 전면 리브랜딩되어 소멸된 구형 브랜드입니다. 최신 명칭인 'PLUS'를 사용하십시오."),
    (r"\bCredit\s+Suisse\b", "크레디트 스위스(Credit Suisse)는 2023년 UBS에 인수 합병되었습니다. 독립 운용 은행으로 기술할 수 없습니다."),
    (r"(?:올해|현재|지금)\s*(?:인|는|은)?\s*202[0-3]년", "2020~2023년 과거 시점을 '현재' 또는 '올해'로 서술하는 LLM 과거 사전학습 고착이 감지되었습니다. 2026년 최신 시점으로 수정하십시오."),
    (r"202[0-3]년\s*(?:현재|기준\s*현재|지금)", "2020~2023년 과거 시점을 현재 기준으로 서술할 수 없습니다."),
    (r"202[0-3]년인\s*올해", "과거 연도를 올해로 서술하는 오류입니다."),
]


@dataclass
class FactCheckAssertionResult:
    domain: str
    assertion_type: str
    is_valid: bool
    snippet: str
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None


# ==============================================================================
# ⚙️ 철벽 게이트 검증 엔진 (Ironclad Gatekeeper Engine)
# ==============================================================================
class IroncladGatekeeper:
    """
    모든 블로그 콘텐츠의 무결성을 기계적으로 판정하는 마스터 검증 엔진.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def detect_platform(self, file_path: str, content: str) -> str:
        """파일 경로 및 본문 패턴으로 플랫폼 자동 감지."""
        norm_path = file_path.replace("\\", "/").lower()
        if "blogs/dev" in norm_path or "dev.ideaspot360" in norm_path:
            return "dev"
        if "markets" in norm_path or "markets.ideaspot360" in norm_path:
            return "markets"
        if "stock" in norm_path or "stock.ideaspot360" in norm_path:
            return "stock"
        if "gear" in norm_path or "gear.ideaspot360" in norm_path:
            return "gear"
        if "naver" in norm_path or "solidlog" in norm_path or "tidynote" in norm_path or "infopiece" in norm_path:
            return "naver"
        # Frontmatter 언어 및 메타데이터 검사
        if re.search(r"^category:\s*(Cloud & DevOps|Database & Storage|Systems & Networking)", content, re.MULTILINE):
            return "dev"
        return "tistory"

    def split_frontmatter_and_body(self, content: str) -> Tuple[Optional[str], str, int]:
        """
        Frontmatter(--- ... ---)와 Body 분리.
        반환: (frontmatter_text, body_text, body_start_line)
        """
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return None, content, 1

        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm_text = "\n".join(lines[1:i])
                body_text = "\n".join(lines[i + 1:])
                return fm_text, body_text, i + 2

        return None, content, 1

    def parse_frontmatter(self, fm_text: Optional[str]) -> Dict[str, Any]:
        """정규식 기반 안전한 Frontmatter 파싱 (PyYAML 미설치 환경 대비, 멀티라인 및 인라인 리스트 지원)."""
        if not fm_text:
            return {}
        data: Dict[str, Any] = {}
        current_list_key: Optional[str] = None
        for raw_line in fm_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # 멀티라인 리스트 아이템: - value
            if line.startswith("-") and current_list_key:
                val = line[1:].strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if isinstance(data.get(current_list_key), list):
                    data[current_list_key].append(val)
                else:
                    data[current_list_key] = [val]
                continue

            match = re.match(r"^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$", line)
            if match:
                k, v = match.group(1).strip(), match.group(2).strip()
                if v == "" or v == "[]":
                    data[k] = []
                    current_list_key = k
                elif v.startswith("[") and v.endswith("]"):
                    inner = v[1:-1].strip()
                    items = []
                    if inner:
                        for item in re.findall(r'(?:"([^"]*)"|\'([^\']*)\'|([^,]+))', inner):
                            extracted = item[0] or item[1] or item[2]
                            items.append(extracted.strip())
                    data[k] = items
                    current_list_key = None
                else:
                    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                        v = v[1:-1]
                    data[k] = v
                    current_list_key = None
            else:
                current_list_key = None
        return data

    def extract_code_blocks(self, body: str) -> List[Tuple[str, str, int]]:
        """
        코드 블록 추출: (language, code_text, start_line)
        """
        blocks = []
        lines = body.splitlines()
        in_block = False
        lang = ""
        current_block = []
        block_start = 0

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```") and not stripped.startswith("+```") and not stripped.startswith("-```"):
                if in_block:
                    blocks.append((lang, "\n".join(current_block), block_start))
                    in_block = False
                    current_block = []
                    lang = ""
                else:
                    in_block = True
                    lang = stripped[3:].strip()
                    block_start = idx
            elif in_block:
                current_block.append(line)

        return blocks

    # --------------------------------------------------------------------------
    # Gate 1: 구조 & 마크다운 무결성 검증
    # --------------------------------------------------------------------------
    def verify_gate_1_structure(self, file_path: str, content: str, fm_data: Dict[str, str], body: str, platform: str) -> List[Violation]:
        violations = []
        
        # 1. Frontmatter 필수 키 검증
        required_keys = ["title", "tags"]
        if platform == "tistory":
            required_keys.extend(["visibility", "category"])
        elif platform == "gear":
            if "category" not in fm_data and "series" not in fm_data:
                required_keys.append("category")
        else:
            required_keys.append("category")
            
        for k in required_keys:
            val = fm_data.get(k)
            if val is None or (isinstance(val, str) and not val.strip()) or (isinstance(val, list) and len(val) == 0):
                violations.append(Violation(
                    gate_id="GATE_1",
                    gate_name="구조 및 메타데이터 무결성",
                    rule_id="G1_REQ_FRONTMATTER",
                    severity="REJECT",
                    line_number=1,
                    snippet=f"Missing key: '{k}'",
                    message=f"YAML Frontmatter에 필수 필드 '{k}'가 누락되었거나 비어 있습니다.",
                    fix_hint=f"파일 최상단 Frontmatter에 '{k}: <값>'을 명시하십시오."
                ))

        # 2. 코드 블록 백틱(```) 짝 맞춤 검증
        backtick_matches = [l for l in content.splitlines() if l.strip().startswith("```") and not l.strip().startswith("+```") and not l.strip().startswith("-```")]
        if len(backtick_matches) % 2 != 0:
            violations.append(Violation(
                gate_id="GATE_1",
                gate_name="구조 및 마크다운 무결성",
                rule_id="G1_UNCLOSED_CODEBLOCK",
                severity="REJECT",
                line_number=0,
                snippet=f"Total backtick rows: {len(backtick_matches)}",
                message="열린 코드 블록(```)이 닫히지 않았습니다. 백틱 개수가 홀수입니다.",
                fix_hint="마크다운 내 모든 ``` 블록이 정상적으로 닫혔는지 확인하십시오."
            ))

        # 3. 수식 블록 ($$) 무결성 검증 (홀수 개수 및 KaTeX 파싱 파괴 멀티라인 차단)
        dollar_block_count = content.count("$$")
        if dollar_block_count % 2 != 0:
            violations.append(Violation(
                gate_id="GATE_1",
                gate_name="구조 및 마크다운 무결성",
                rule_id="G1_UNCLOSED_MATH_BLOCK",
                severity="REJECT",
                line_number=0,
                snippet=f"Total '$$' occurrences: {dollar_block_count}",
                message="수식 디스플레이 블록($$)이 올바르게 닫히지 않았습니다. '$$' 개수가 홀수입니다.",
                fix_hint="마크다운 내 모든 수식 블록($$)이 정상적으로 열리고 닫혔는지 확인하십시오."
            ))

        # KaTeX ParseError를 유발하여 다운스트림 마크다운 및 이미지를 붕괴시키는 위험한 멀티라인 $$ 블록 차단
        math_matches = re.finditer(r"\$\$(.*?)\$\$", content, re.DOTALL)
        for mm in math_matches:
            raw_math = mm.group(1).strip()
            if "\n" in raw_math:
                lines = [l.strip() for l in raw_math.split("\n") if l.strip()]
                has_env = any(env in raw_math for env in [r"\begin{", r"\end{", r"\matrix", r"\cases"])
                if not has_env and len(lines) > 1:
                    has_invalid_break = any(not l.endswith(r"\\") for l in lines[:-1])
                    if has_invalid_break:
                        line_no = content[:mm.start()].count("\n") + 1
                        violations.append(Violation(
                            gate_id="GATE_1",
                            gate_name="구조 및 마크다운 무결성",
                            rule_id="G1_KATEX_MULTILINE_SYNTAX",
                            severity="REJECT",
                            line_number=line_no,
                            snippet=raw_math[:80] + "...",
                            message="KaTeX 수식 블록($$) 내부에 '\\\\' 없이 줄바꿈된 수식이 포함되어 있어 렌더링 붕괴(ParseError)를 유발합니다.",
                            fix_hint="각 수식을 독립된 단일 라인 $$ 블록으로 분리하거나, \\begin{aligned} 환경을 명시하십시오."
                        ))

        # 3. 최소 분량 검증
        if platform == "dev":
            word_count = len(re.findall(r"\b[a-zA-Z0-9_\-]+\b", body))
            if word_count < 700:
                violations.append(Violation(
                    gate_id="GATE_1",
                    gate_name="구조 및 마크다운 무결성",
                    rule_id="G1_MIN_LENGTH_EN",
                    severity="REJECT",
                    line_number=0,
                    snippet=f"Current word count: {word_count} words",
                    message=f"글로벌 기술 백서의 최소 분량(700단어)에 미달합니다. (현재: {word_count}단어)",
                    fix_hint="에러 로그, 근본 커널 원인, 실패한 시도, 재현 CLI를 상세히 보강하여 전문성을 확보하십시오."
                ))
        else:
            char_count = len(body.replace(" ", "").replace("\n", ""))
            if char_count < 1200:
                violations.append(Violation(
                    gate_id="GATE_1",
                    gate_name="구조 및 마크다운 무결성",
                    rule_id="G1_MIN_LENGTH_KO",
                    severity="REJECT",
                    line_number=0,
                    snippet=f"Current char count: {char_count} chars (excl. spaces)",
                    message=f"국내 기술 블로그 최소 분량(공백 제외 1,200자)에 미달합니다. (현재: {char_count}자)",
                    fix_hint="충실한 기술적 설명과 단계별 예시, 비유를 보강하십시오."
                ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 2: AI 클리셰 & 기계적 번역투 박멸 검증
    # --------------------------------------------------------------------------
    def verify_gate_2_anti_ai(self, lines: List[str], platform: str) -> List[Violation]:
        violations = []
        is_english = (platform == "dev")
        patterns = EN_AI_CLICHE_PATTERNS if is_english else KO_AI_CLICHE_PATTERNS

        # 코드 블록 내부 라인은 제외하고 본문 텍스트만 검사
        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            for pattern, severity, msg in patterns:
                match = re.search(pattern, line, re.IGNORECASE if is_english else 0)
                if match:
                    sev = "REJECT" if (severity == "REJECT" or self.strict_mode) else "WARNING"
                    violations.append(Violation(
                        gate_id="GATE_2",
                        gate_name="AI 클리셰 & 기계적 번역투 박멸",
                        rule_id="G2_AI_CLICHE",
                        severity=sev,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=f"{msg} (탐지 패턴: '{pattern}')",
                        fix_hint="AI 특유의 진부한 미사여구를 삭제하고, 현업 엔지니어의 담백하고 직관적인 실무 표현으로 교체하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 3: 억지 스토리 & 작위적 연출 차단 검증
    # --------------------------------------------------------------------------
    def verify_gate_3_no_forced_drama(self, lines: List[str], platform: str) -> List[Violation]:
        violations = []
        is_english = (platform == "dev")
        patterns = FORCED_DRAMA_PATTERNS_EN if is_english else FORCED_DRAMA_PATTERNS_KO

        in_code_block = False
        for idx, line in enumerate(lines, start=1):
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
                        gate_id="GATE_3",
                        gate_name="억지 스토리 & 작위적 연출 차단",
                        rule_id="G3_FORCED_DRAMA",
                        severity="REJECT",
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=msg,
                        fix_hint="가짜 위기 스토리(새벽 알람, 식은땀, 패닉 등)를 즉시 삭제하고, '실제 프로덕션에서 발생한 모니터링 수치/장애 증상'으로 객관화하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 4: 실무 엔지니어링 5대 아티팩트 검증 (트러블슈팅/실무 포스트 전용)
    # --------------------------------------------------------------------------
    def verify_gate_4_engineering_artifacts(self, file_path: str, body: str, fm_data: Dict[str, str], platform: str) -> List[Violation]:
        violations = []
        fname = os.path.basename(file_path).lower()
        category = fm_data.get("category", "").lower()
        title = fm_data.get("title", "").lower()

        # 트러블슈팅 포스트 판별 (Track 1 dev 글 전체, Track 2 국문 트러블슈팅 글)
        is_trouble = (
            platform == "dev" or
            "trouble" in fname or
            "트러블슈팅" in category or
            "post-mortem" in category or
            "장애" in title or
            "트러블슈팅" in title
        )

        if not is_trouble:
            return violations  # 개념 입문서(Track 3)는 제외

        code_blocks = self.extract_code_blocks(body)

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
                gate_name="실무 엔지니어링 5대 아티팩트 검증",
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
        body_lower = body.lower()
        has_wrong_fix = any(k in body_lower for k in wrong_fix_keywords)

        if not has_wrong_fix:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name="실무 엔지니어링 5대 아티팩트 검증",
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
            # 코드 내에 - 라인과 + 라인이 동시에 존재하는지 검사
            has_minus = bool(re.search(r"^\s*-\s+", code, re.MULTILINE))
            has_plus = bool(re.search(r"^\s*\+\s+", code, re.MULTILINE))
            if has_minus and has_plus:
                has_unified_diff = True
                break

        if not has_unified_diff:
            violations.append(Violation(
                gate_id="GATE_4",
                gate_name="실무 엔지니어링 5대 아티팩트 검증",
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
                gate_name="실무 엔지니어링 5대 아티팩트 검증",
                rule_id="G4_MISSING_ROOT_CAUSE",
                severity="WARNING",
                line_number=0,
                snippet="No explicit Root Cause / Architecture analysis header found",
                message="[개선 권장] 근본 원인(Root Cause)이나 커널/런타임 내부 동작 기전에 대한 심층 분석 헤더가 미흡합니다.",
                fix_hint="'## Root Cause Analysis' 또는 '## 장애의 근본 원인 분석' 섹션을 두어 내부 아키텍처 레벨의 원인을 설명하십시오."
            ))

        # 5. Verification CLI (재발 방지 및 검증 명령) 검증
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
                gate_name="실무 엔지니어링 5대 아티팩트 검증",
                rule_id="G4_MISSING_CLI_VERIFICATION",
                severity="WARNING",
                line_number=0,
                snippet="No verification CLI command (curl, ss, kubectl, sysctl, etc.) found in code blocks",
                message="[개선 권장] 수정 사항을 현장에서 즉시 검증할 수 있는 CLI 확인 명령어가 없습니다.",
                fix_hint="수정 후 상태를 검증하는 CLI 명령어(예: curl -v, ss -s, kubectl describe 등) 코드 블록을 추가하십시오."
            ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 5: 사족 & 중언부언 차단 검증
    # --------------------------------------------------------------------------
    def verify_gate_5_anti_fluff(self, body: str, platform: str) -> List[Violation]:
        violations = []
        lines = body.splitlines()

        # 1. 서론 사족 비율 및 기술 밀도 검사 (첫 번째 H2 헤더 이전의 텍스트가 과도하게 긴지 검사)
        intro_lines = []
        for line in lines:
            if re.match(r"^#{1,3}\s+", line.strip()):
                break
            intro_lines.append(line)

        intro_text = "\n".join(intro_lines).strip()
        intro_words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", intro_text)
        body_words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", body)

        if len(body_words) > 0 and len(intro_words) > 250:
            intro_ratio = len(intro_words) / len(body_words)
            if intro_ratio > 0.30:
                violations.append(Violation(
                    gate_id="GATE_5",
                    gate_name="사족 & 중언부언 차단",
                    rule_id="G5_EXCESSIVE_INTRO_FLUFF",
                    severity="WARNING",
                    line_number=1,
                    snippet=intro_text[:120] + "...",
                    message=f"도입부 사족 비율이 전체 본문의 {int(intro_ratio * 100)}%로 과도하게 깁니다. ({len(intro_words)}단어)",
                    fix_hint="원론적인 배경 설명을 대폭 축소하고, 독자가 첫 화면에서 즉시 핵심 문제와 아키텍처를 파악할 수 있도록 바로 본론 헤더를 전진 배치하십시오."
                ))

        # 2. 판에 박힌 결론 재요약 (Parrot Conclusion) 패턴 검사
        last_section = "\n".join(lines[-40:]) if len(lines) >= 40 else body
        parrot_patterns = [
            (r"(지금까지\s+살펴본\s+바와\s+같이|위에서\s+살펴보았듯이|앞서\s+설명한\s+것처럼)", "결론부 상투적 중언부언"),
            (r"(as\s+we\s+have\s+seen\s+above|to\s+recap\s+what\s+we\s+discussed|in\s+this\s+article,\s*we\s+have\s+covered)", "Repetitive conclusion recap")
        ]
        for pattern, label in parrot_patterns:
            match = re.search(pattern, last_section, re.IGNORECASE)
            if match:
                violations.append(Violation(
                    gate_id="GATE_5",
                    gate_name="사족 & 중언부언 차단",
                    rule_id="G5_PARROT_CONCLUSION",
                    severity="WARNING",
                    line_number=0,
                    snippet=match.group(0),
                    message=f"단순 반복 재요약 패턴({label})이 감지되었습니다.",
                    fix_hint="앞서 설명한 내용을 기계적으로 다시 요약하지 말고, 현업 실무자를 위한 '운영 주의점'이나 '모니터링 알람 임계치 설정 팁'으로 실용적 가치를 더하십시오."
                ))

        # 3. Jaccard 유사도 기반 결론부 복제 검증 (Verbose Conclusion Index)
        sections = re.split(r"\n#{1,3}\s+", body)
        if len(sections) >= 3:
            conclusion_text = sections[-1]
            stop_words = {
                "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of",
                "this", "that", "is", "was", "are", "were", "it", "as", "be", "from", "we", "our",
                "you", "your", "will", "can", "not", "if", "when", "then", "into", "which", "all"
            }
            c_words = set(w.lower() for w in re.findall(r"[a-zA-Z0-9_\-]+", conclusion_text) if len(w) > 2 and w.lower() not in stop_words)
            if len(c_words) >= 20:
                for b_idx, b_sec in enumerate(sections[1:-1], start=1):
                    b_words = set(w.lower() for w in re.findall(r"[a-zA-Z0-9_\-]+", b_sec) if len(w) > 2 and w.lower() not in stop_words)
                    if len(b_words) >= 20:
                        intersection = len(c_words & b_words)
                        union = len(c_words | b_words)
                        jaccard = intersection / union if union > 0 else 0.0
                        if jaccard >= 0.65:
                            violations.append(Violation(
                                gate_id="GATE_5",
                                gate_name="사족 & 중언부언 차단",
                                rule_id="G5_JACCARD_REDUNDANCY",
                                severity="WARNING",
                                line_number=0,
                                snippet=f"Section {b_idx} vs Conclusion (Jaccard: {jaccard:.2f})",
                                message=f"결론부 내용이 본문 {b_idx}번 섹션과 자카드 유사도 {int(jaccard*100)}%로 지나치게 중복됩니다.",
                                fix_hint="결론부에서 본문 텍스트를 단순 복제/요약하지 말고, 차별화된 런북 및 체크리스트 가치를 제시하십시오."
                            ))
                            break

        return violations

    # --------------------------------------------------------------------------
    # Gate 6: 맞춤법, 오타 및 플랫폼별 특화 규격 검증
    # --------------------------------------------------------------------------
    def verify_gate_6_platform_compliance(self, file_path: str, body: str, fm_data: Dict[str, str], lines: List[str], platform: str) -> List[Violation]:
        violations = []
        category = fm_data.get("category", "").strip()

        # 1. 개발 블로그 (dev.ideaspot360.com) 카테고리 정규화 검증
        if platform == "dev":
            if category not in DEV_OFFICIAL_CATEGORIES:
                violations.append(Violation(
                    gate_id="GATE_6",
                    gate_name="플랫폼별 특화 규격 검증",
                    rule_id="G6_DEV_CATEGORY_MISMATCH",
                    severity="REJECT",
                    line_number=1,
                    snippet=f"category: {category}",
                    message=f"개발 블로그 공식 4대 카테고리와 불일치합니다. (허용: {', '.join(DEV_OFFICIAL_CATEGORIES)})",
                    fix_hint=f"Frontmatter의 category를 'Cloud & DevOps', 'Database & Storage', 'Systems & Networking', 'AI & Machine Learning' 중 하나로 정확히 일치시키십시오."
                ))

        # 2. 티스토리 (softwin.tistory.com) 카테고리 검증
        elif platform == "tistory":
            if category and category not in TISTORY_OFFICIAL_CATEGORIES:
                violations.append(Violation(
                    gate_id="GATE_6",
                    gate_name="플랫폼별 특화 규격 검증",
                    rule_id="G6_TISTORY_CATEGORY_MISMATCH",
                    severity="WARNING",
                    line_number=1,
                    snippet=f"category: {category}",
                    message=f"티스토리 11대 마스터 카테고리 또는 트러블슈팅 카테고리와 불일치할 수 있습니다. (지정: '{category}')",
                    fix_hint="CATEGORIES.md의 공식 11대 카테고리 명칭과 일치하는지 확인하십시오."
                ))

        # 3. 네이버 블로그 특화 검증 (의료법 위반 단어, 이미지 링크 표기, 해시태그)
        elif platform == "naver":
            is_health = ("infopiece" in file_path.lower() or "건강" in category or "영양" in category)
            
            # (1) 건강 블로그 의료법 위반 단어 100% 하드 블록
            if is_health:
                for idx, line in enumerate(lines, start=1):
                    # 법적 면책 고지 문구 부분(치료를 목적으로 하지 않음 등)만 국소 제거하여 오탐 방지하되, 나머지 본문 단어는 철저 검증
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
                                gate_id="GATE_6",
                                gate_name="네이버 블로그 법적 규격 검증",
                                rule_id="G6_NAVER_MEDICAL_LAW",
                                severity="REJECT",
                                line_number=idx,
                                snippet=line.strip()[:100],
                                message=msg,
                                fix_hint="의료법 위반 소지가 있는 단어를 즉시 제거하고 식약처 공인 기능성 표현으로 수정하십시오."
                            ))

                # 법적 면책 고지(Disclaimer) 필수 포함 검증
                has_disclaimer = any(re.search(p, body) for p in HEALTH_DISCLAIMER_PATTERNS)
                if not has_disclaimer:
                    violations.append(Violation(
                        gate_id="GATE_6",
                        gate_name="네이버 블로그 법적 규격 검증",
                        rule_id="G6_NAVER_MISSING_DISCLAIMER",
                        severity="REJECT",
                        line_number=0,
                        snippet="No medical disclaimer found at the bottom",
                        message="[법적 방벽 결손] 건강/영양제 포스팅 최하단에 필수적인 '법적 면책 문구(Disclaimer)'가 누락되었습니다.",
                        fix_hint="포스팅 최하단에 '본 포스팅은 일반적인 정보 제공을 목적으로 하며, 전문 의료인의 진단 및 처방을 대신할 수 없습니다.'를 삽입하십시오."
                    ))

            # (2) 본문 내 이미지 마크다운 직접 삽입(![...]) 금지 및 링크 표기 강제
            img_tag_matches = re.findall(r"!\[(.*?)\]\((.*?)\)", body)
            if img_tag_matches:
                violations.append(Violation(
                    gate_id="GATE_6",
                    gate_name="네이버 블로그 조판 규격 검증",
                    rule_id="G6_NAVER_INLINE_IMAGE_FORBIDDEN",
                    severity="REJECT",
                    line_number=0,
                    snippet=f"Found {len(img_tag_matches)} inline markdown image tags (![...])",
                    message="네이버 블로그 본문 내에 직접 이미지(![...])를 띄우는 것이 금지되어 있습니다. (스마트에디터 수동 업로드 지원 규격 위반)",
                    fix_hint="본문에는 '[사진 X: 파일명](file:///...)' 형태의 클릭 가능한 로컬 링크만 남기십시오."
                ))

            # (3) 본문 최하단 인라인 해시태그 블록 필수 검증
            hashtag_match = re.search(r"#[가-힣a-zA-Z0-9_]+\s+#[가-힣a-zA-Z0-9_]+", body[-300:])
            if not hashtag_match:
                violations.append(Violation(
                    gate_id="GATE_6",
                    gate_name="네이버 블로그 조판 규격 검증",
                    rule_id="G6_NAVER_MISSING_HASHTAGS",
                    severity="WARNING",
                    line_number=0,
                    snippet="No inline #hashtag block found in the last 300 characters",
                    message="본문 최하단에 네이버 스마트에디터 ONE 자동 태그 완성용 '#태그1 #태그2 ...' 블록이 누락되었습니다.",
                    fix_hint="원고 맨 마지막 줄에 '#태그1 #태그2 #태그3 ...' 형태의 단일 인라인 해시태그를 추가하십시오."
                ))

        # 4. 기어 블로그 (gear.ideaspot360.com) 도안 이미지 및 치형 규격 검증
        elif platform == "gear":
            target_file = Path(file_path).resolve()
            candidate_roots = [
                target_file.parent,
                target_file.parent.parent,
                target_file.parent.parent.parent,
                target_file.parent.parent.parent.parent,
                Path.cwd(),
                Path("blog"),
                Path("blogs/gear"),
                Path("d:/01_ag_gear/01_gear/blog"),
            ]
            img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', body)
            for alt_text, img_src in img_refs:
                if img_src.startswith("http://") or img_src.startswith("https://"):
                    continue
                clean_src = img_src.split("?")[0].split("#")[0]
                # (1) 도안 이미지 확장자 검증 (고해상도 png, svg, webp)
                if not any(clean_src.lower().endswith(ext) for ext in [".png", ".svg", ".webp"]):
                    violations.append(Violation(
                        gate_id="GATE_6",
                        gate_name="기어 공학 블로그 규격 검증",
                        rule_id="G6_GEAR_INVALID_IMAGE_EXT",
                        severity="REJECT",
                        line_number=0,
                        snippet=f"![{alt_text}]({img_src})",
                        message=f"도안 이미지 경로 '{img_src}'의 확장자가 정규 포맷(.png, .svg, .webp)이 아닙니다.",
                        fix_hint="정규 벡터 SVG 또는 고해상도 300DPI PNG 포맷을 사용하십시오."
                    ))

                # (2) 로컬 도안 이미지 디스크 실존 여부 검증
                if target_file.exists():
                    found = False
                    if clean_src.startswith("/"):
                        rel_path = clean_src.lstrip("/")
                        for root in candidate_roots:
                            if (root / "public" / rel_path).is_file() or (root / rel_path).is_file():
                                found = True
                                break
                    else:
                        for root in candidate_roots:
                            if (target_file.parent / clean_src).is_file() or (root / clean_src).is_file():
                                found = True
                                break
                    if not found:
                        violations.append(Violation(
                            gate_id="GATE_6",
                            gate_name="기어 공학 블로그 규격 검증",
                            rule_id="G6_GEAR_MISSING_IMAGE_FILE",
                            severity="REJECT",
                            line_number=0,
                            snippet=f"![{alt_text}]({img_src})",
                            message=f"도안 이미지 파일 '{img_src}'이 디스크의 public 또는 참조 디렉토리에 실제로 존재하지 않습니다.",
                            fix_hint="도안 생성 스크립트를 실행하여 정규 이미지를 public 디렉토리에 생성하십시오."
                        ))

            # (3) 맞물림 치형 도안 치면 오버랩 0.000 mm 무간섭 입증 수치 명시 검증
            mesh_keywords = ["asymmetric_mesh_profile", "실측 2D 맞물림 치형", "Conjugate Meshing Profile", "치형 맞물림", "맞물림 치형"]
            if any(kw in body for kw in mesh_keywords):
                proof_keywords = ["0.000", "오버랩", "Zero-overlap", "zero-overlap", "overlap", "オーバーラップ", "Hinterschnittfreiheit"]
                has_proof = any(term in body for term in proof_keywords)
                if not has_proof:
                    violations.append(Violation(
                        gate_id="GATE_6",
                        gate_name="기어 공학 블로그 규격 검증",
                        rule_id="G6_GEAR_ZERO_OVERLAP_MANDATE",
                        severity="WARNING",
                        line_number=0,
                        snippet="Conjugate Meshing Profile without zero-overlap verification proof",
                        message="맞물림 치형 도안이 포함된 글에서 치면 오버랩 0.000 mm 무간섭 입증 수치가 기술되지 않았습니다.",
                        fix_hint="순수 위상각 정렬에 따른 오버랩 0.000000 mm² 완전 소멸 실측치를 본문에 명시하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 7: 보안 & 시크릿 누출 방벽 (Security & Secret Leak Prevention)
    # --------------------------------------------------------------------------
    def verify_gate_7_security(self, file_path: str, content: str, lines: List[str]) -> List[Violation]:
        violations = []

        dummy_tokens = {
            "your_api_key", "your-api-key", "your_token", "your-token",
            "example_token", "sample_key", "test_token", "placeholder",
            "xxx", "xxxx", "000000", "<token>", "<api_key>", "<api-key>",
            "my_secret", "dummy", "replace_with", "insert_here",
            "secret-key", "secret_key", "super-secure", "my-secret", "sample",
            "example", "demo", "tutorial", "test_key", "change-me", "changeme"
        }

        # 1. AWS Access Key ID
        for idx, line in enumerate(lines, start=1):
            aws_match = re.search(r"\bAKIA[0-9A-Z]{16}\b", line)
            if aws_match:
                matched_val = aws_match.group(0)
                if not any(d in matched_val.lower() for d in dummy_tokens):
                    violations.append(Violation(
                        gate_id="GATE_7",
                        gate_name="보안 & 시크릿 누출 방벽",
                        rule_id="G7_AWS_KEY_LEAK",
                        severity="REJECT",
                        line_number=idx,
                        snippet=matched_val,
                        message="[보안 위험] 실제 AWS Access Key ID 형식의 문자열이 감지되었습니다.",
                        fix_hint="실제 클라우드 자격 증명을 즉시 삭제하고, 환경변수(os.environ['AWS_ACCESS_KEY_ID']) 또는 'YOUR_AWS_ACCESS_KEY'와 같은 플레이스홀더로 대체하십시오."
                    ))

        # 2. GitHub Personal Access Token
        for idx, line in enumerate(lines, start=1):
            gh_match = re.search(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b", line)
            if gh_match:
                matched_val = gh_match.group(0)
                if not any(d in matched_val.lower() for d in dummy_tokens):
                    violations.append(Violation(
                        gate_id="GATE_7",
                        gate_name="보안 & 시크릿 누출 방벽",
                        rule_id="G7_GITHUB_TOKEN_LEAK",
                        severity="REJECT",
                        line_number=idx,
                        snippet=matched_val[:12] + "...",
                        message="[보안 위험] GitHub Personal Access Token(PAT) 형식의 문자열이 감지되었습니다.",
                        fix_hint="실제 GitHub 토큰을 즉시 폐기하고 더미 문자열로 교체하십시오."
                    ))

        # 3. Slack Webhook URL
        for idx, line in enumerate(lines, start=1):
            slack_match = re.search(r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+", line)
            if slack_match:
                violations.append(Violation(
                    gate_id="GATE_7",
                    gate_name="보안 & 시크릿 누출 방벽",
                    rule_id="G7_SLACK_WEBHOOK_LEAK",
                    severity="REJECT",
                    line_number=idx,
                    snippet=slack_match.group(0)[:35] + "...",
                    message="[보안 위험] 실제 슬랙 웹훅 URL(Slack Webhook URL)이 노출되었습니다.",
                    fix_hint="웹훅 URL을 삭제하고 'https://hooks.slack.com/services/T00/B00/XXXX' 형식의 마스킹된 주소를 사용하십시오."
                ))

        # 4. Private Key Headers
        for idx, line in enumerate(lines, start=1):
            pk_match = re.search(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|ENCRYPTED|PRIVATE) KEY-----", line)
            if pk_match:
                violations.append(Violation(
                    gate_id="GATE_7",
                    gate_name="보안 & 시크릿 누출 방벽",
                    rule_id="G7_PRIVATE_KEY_LEAK",
                    severity="REJECT",
                    line_number=idx,
                    snippet=pk_match.group(0),
                    message="[보안 위험] 비공개 암호화 키(Private Key) 헤더가 감지되었습니다.",
                    fix_hint="비공개 키 원문을 마크다운에 절대 삽입하지 마십시오."
                ))

        # 5. 하드코딩된 API Key/Secret 직접 할당문
        secret_assign_pat = re.compile(r"""(?i)\b(?:api_key|apikey|secret_key|client_secret|auth_token)\s*[:=]\s*["']([a-zA-Z0-9_\-\.]{24,})["']""")
        for idx, line in enumerate(lines, start=1):
            m = secret_assign_pat.search(line)
            if m:
                val = m.group(1)
                if not any(d in val.lower() for d in dummy_tokens):
                    violations.append(Violation(
                        gate_id="GATE_7",
                        gate_name="보안 & 시크릿 누출 방벽",
                        rule_id="G7_HARDCODED_SECRET",
                        severity="REJECT",
                        line_number=idx,
                        snippet=line.strip()[:80],
                        message="[보안 위험] 실제 API 키 또는 비밀 시크릿 토큰의 직접 할당문이 감지되었습니다.",
                        fix_hint="비밀번호나 API 키를 코드에 직접 하드코딩하지 말고 환경변수나 시크릿 매니저 참조 코드로 대체하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 8: 법적 리스크 & 컴플라이언스 방벽 (Legal & Compliance Risk Gate)
    # --------------------------------------------------------------------------
    def verify_gate_8_legal_compliance(
        self,
        file_path: str,
        content: str,
        body: str,
        fm_data: Dict[str, str],
        lines: List[str],
        platform: str
    ) -> List[Violation]:
        violations: List[Violation] = []
        category = fm_data.get("category", "").strip()
        title = fm_data.get("title", "").strip()
        norm_path = file_path.replace("\\", "/").lower()

        # ----------------------------------------------------------------------
        # 1. 자본시장법 & 금융소비자보호법(금소법) 방벽 검증
        # ----------------------------------------------------------------------
        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            for pat, sev, rule_id, msg, hint in CAPITAL_MARKETS_RULES:
                match = re.search(pat, line)
                if match:
                    violations.append(Violation(
                        gate_id="GATE_8",
                        gate_name="자본시장법·금소법 방벽",
                        rule_id=rule_id,
                        severity=sev,
                        line_number=idx,
                        snippet=stripped[:100],
                        message=msg,
                        fix_hint=hint
                    ))

        # [1-2] 금융/투자/증시/재테크 포스팅 필수 투자 면책고지 검증
        is_kr_financial = (
            platform in ["stock"] or
            "stock.ideaspot360" in norm_path or
            ("stock" in norm_path and "posts" not in norm_path) or
            any(k in category for k in ["주식", "증시", "ETF", "금융", "재테크", "투자", "가상화폐", "암호화폐", "코인", "펀드", "채권", "커버드콜", "배당"]) or
            any(k in title for k in ["주식", "증시", "ETF", "재테크", "투자전략", "매수", "매도", "배당주", "커버드콜", "코스피", "나스닥 투자"])
        )
        if is_kr_financial:
            has_fin_disclaimer = any(re.search(p, body) for p in KO_FINANCIAL_DISCLAIMER_PATTERNS)
            if not has_fin_disclaimer:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="자본시장법·금소법 방벽",
                    rule_id="G8_FIN_MISSING_DISCLAIMER",
                    severity="REJECT",
                    line_number=0,
                    snippet="No investment disclaimer found in financial content",
                    message="[자본시장법·금소법 방벽] 금융/증시/재테크 관련 포스팅 최하단에 필수적인 '투자 유의사항 및 면책고지(Disclaimer)'가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.'를 명시하십시오."
                ))

        # ----------------------------------------------------------------------
        # 2. 의료법 & 건강기능식품법(식품표시광고법) 방벽 검증
        # ----------------------------------------------------------------------
        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            for pat, sev, rule_id, msg, hint in MEDICAL_LAW_RULES:
                match = re.search(pat, line)
                if match:
                    violations.append(Violation(
                        gate_id="GATE_8",
                        gate_name="의료법·식품표시광고법 방벽",
                        rule_id=rule_id,
                        severity=sev,
                        line_number=idx,
                        snippet=stripped[:100],
                        message=msg,
                        fix_hint=hint
                    ))

        # [2-2] 건강/영양제/건기식 포스팅 필수 법적 면책고지 검증
        is_health = (
            "infopiece" in norm_path or
            any(k in category for k in ["건강", "영양", "건기식", "의학"]) or
            any(k in title for k in ["영양제", "마그네슘", "비타민", "오메가", "건강기능식품", "유산균", "콜라겐"])
        )
        if is_health:
            has_health_disclaimer = any(re.search(p, body) for p in HEALTH_DISCLAIMER_PATTERNS)
            if not has_health_disclaimer:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="의료법·식품표시광고법 방벽",
                    rule_id="G8_MED_MISSING_DISCLAIMER",
                    severity="REJECT",
                    line_number=0,
                    snippet="No health/medical disclaimer found in health content",
                    message="[의료법·건기식법 방벽] 건강/영양제 포스팅 최하단에 필수적인 '법적 면책 문구(Disclaimer)'가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '본 포스팅은 일반적인 정보 제공을 목적으로 하며, 전문 의료인의 진단 및 처방을 대신할 수 없습니다. 질병의 예방 및 치료를 위한 의약품이 아닙니다.'를 삽입하십시오."
                ))

        # ----------------------------------------------------------------------
        # 3. 공정거래위원회 추천·보증 심사지침 준수 검증 (대가성 표시광고법)
        # ----------------------------------------------------------------------
        # 제휴 링크 또는 협찬 키워드 존재 시 검증
        has_affiliate_link = any(re.search(pat, body, re.IGNORECASE) for pat in AFFILIATE_LINK_PATTERNS)
        has_affiliate_kw = any(re.search(pat, body) for pat in AFFILIATE_KEYWORD_PATTERNS)

        if has_affiliate_link or has_affiliate_kw:
            # (1) 기만적 스텔스 마케팅/위장 광고 차단 (어휘 순서 무관)
            my_money_match = re.search(r"(?:내돈내산|직접\s*구매한|100%\s*자비)", body)
            if my_money_match:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="공정위 표시광고법 방벽",
                    rule_id="G8_FTC_COVERT_MY_MONEY",
                    severity="REJECT",
                    line_number=0,
                    snippet=my_money_match.group(0),
                    message="[공정위 표시광고법 위반] 제휴 링크 또는 대가성 상업 활동이 포함되어 있으나 '내돈내산/자비 구매'로 소비자를 오도하는 기만적 스텔스 마케팅이 감지되었습니다.",
                    fix_hint="'내돈내산' 허위 표기를 삭제하고 공정위 표준 대가성 문구를 기재하십시오."
                ))

            not_ad_match = re.search(r"(?:광고|협찬)\s*(?:가\s*)?아닙니다", body)
            if not_ad_match:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="공정위 표시광고법 방벽",
                    rule_id="G8_FTC_COVERT_NOT_AD",
                    severity="REJECT",
                    line_number=0,
                    snippet=not_ad_match.group(0),
                    message="[공정위 표시광고법 위반] 제휴 수수료 링크가 있으면서 '광고/협찬 아닙니다'라고 허위 주장하는 행위가 감지되었습니다.",
                    fix_hint="광고 부인 문구를 삭제하고 수수료 제공 사실을 명시하십시오."
                ))

            # (2) 대가성 공개 문구 필수 검증
            has_ftc_disclosure = any(re.search(pat, body) for pat in FTC_DISCLOSURE_PATTERNS)
            if not has_ftc_disclosure:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="공정위 표시광고법 방벽",
                    rule_id="G8_FTC_MISSING_DISCLOSURE",
                    severity="REJECT",
                    line_number=0,
                    snippet="Affiliate links or sponsorship keywords detected without FTC disclosure",
                    message="[공정위 표시광고법 방벽] 제휴 링크(쿠팡 파트너스 등) 또는 대가성 상업 활동 내용이 포함되어 있으나, 공정거래위원회 「추천·보증 등에 관한 표시·광고 심사지침」에 따른 경제적 이해관계(대가성) 고지 문구가 누락되었습니다.",
                    fix_hint="포스팅 최상단 또는 최하단에 '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.' 또는 '소정의 수수료를 제공받을 수 있습니다.'를 명시하십시오."
                ))

        # ----------------------------------------------------------------------
        # 4. 공공누리(KOGL) 저작권 출처 표기 의무 검증
        # ----------------------------------------------------------------------
        is_policy_content = (
            any(k in category for k in ["정부 정책", "복지 지원금", "복지정책", "행정 절차", "공공누리", "공공"]) or
            "solidlog" in norm_path or
            any(re.search(pat, title) for pat in POLICY_TOPIC_PATTERNS) or
            (any(re.search(pat, body) for pat in POLICY_TOPIC_PATTERNS) and
             bool(re.search(r"(?:신청\s*자격|지원\s*대상|소득\s*기준|신청\s*기간|신청\s*방법|지급\s*방식|선정\s*기준|구비\s*서류)", body)))
        )
        if is_policy_content:
            has_kogl_attribution = any(re.search(pat, body) for pat in KOGL_ATTRIBUTION_PATTERNS)
            if not has_kogl_attribution:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="공공누리(KOGL) 출처 표기 방벽",
                    rule_id="G8_KOGL_MISSING_ATTRIBUTION",
                    severity="REJECT",
                    line_number=0,
                    snippet="Government policy or welfare content found without KOGL attribution",
                    message="[공공누리(KOGL) 출처 표기 방벽] 정부 정책, 복지 지원금 또는 공공기관 저작물 정보가 포함되어 있으나, 저작권법 제37조 및 공공누리(KOGL) 출처 표기 의무가 누락되었습니다.",
                    fix_hint="포스팅 최하단에 '출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)' 또는 '본 저작물은 공공누리 제1유형에 따라 작성되었습니다.'를 명시하십시오."
                ))

        # ----------------------------------------------------------------------
        # 5. 영문 법적 리스크 (SEC 투자 자문 위반 및 글로벌 금융 규제) 검증
        # ----------------------------------------------------------------------
        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue

            for pat, sev, rule_id, msg, hint in GLOBAL_FINANCIAL_RULES:
                match = re.search(pat, line)
                if match:
                    violations.append(Violation(
                        gate_id="GATE_8",
                        gate_name="영문 글로벌 금융 규제 방벽 (SEC Compliance)",
                        rule_id=rule_id,
                        severity=sev,
                        line_number=idx,
                        snippet=stripped[:100],
                        message=msg,
                        fix_hint=hint
                    ))

        # [5-2] 영문 금융/시장/매크로 포스팅 글로벌 면책문구 누락 검증
        is_en_financial = (
            platform in ["markets"] or
            "markets" in norm_path or
            (platform == "dev" and any(k in category.lower() for k in ["finance", "market", "macro", "quant", "stock", "trading", "investment"])) or
            (bool(re.search(r"(?i)\b(?:s&p\s*500|nasdaq|treasury\s+yield|fed\s+liquidity|equity\s+market|stock\s+market|quantitative\s+trading|macroeconomic)\b", body)) and
             len(re.findall(r"[가-힣]", body[:500])) == 0)
        )
        if is_en_financial:
            has_global_disclaimer = any(re.search(pat, body) for pat in GLOBAL_DISCLAIMER_PATTERNS)
            if not has_global_disclaimer:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name="영문 글로벌 금융 규제 방벽 (SEC Compliance)",
                    rule_id="G8_GLOBAL_MISSING_DISCLAIMER",
                    severity="REJECT",
                    line_number=0,
                    snippet="No global financial disclaimer found in English financial content",
                    message="[SEC Global Compliance] English financial/market article lacks a mandatory global investment disclaimer.",
                    fix_hint="Add standard disclaimer at the bottom: 'Disclaimer: This article is for informational and educational purposes only and does not constitute financial, investment, or legal advice. Past performance is not indicative of future results.'"
                ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 9: 예약 발행 무결성 및 안티봇 지터 방벽 (Reservation & Anti-Bot Jitter Gate)
    # --------------------------------------------------------------------------
    def _parse_datetime_flexible(self, raw_date: str, raw_time: str, now_dt: Optional[datetime] = None) -> Tuple[Optional[datetime], bool]:
        """date와 time 문자열을 유연하게 파싱. 반환: (parsed_datetime, has_explicit_seconds)"""
        if now_dt is None:
            now_dt = datetime.now()

        raw_date = (raw_date or "").strip()
        raw_time = (raw_time or "").strip()

        norm_date = ""
        if raw_date:
            if "-" in raw_date:
                parts = raw_date.split("-")
                if len(parts) == 3:
                    try:
                        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                        datetime(y, m, d)
                        norm_date = f"{y:04d}-{m:02d}-{d:02d}"
                    except ValueError:
                        return None, False
                else:
                    return None, False
            elif raw_date.isdigit():
                day_val = int(raw_date)
                if not (1 <= day_val <= 31):
                    return None, False
                try:
                    datetime(now_dt.year, now_dt.month, day_val)
                    norm_date = f"{now_dt.year:04d}-{now_dt.month:02d}-{day_val:02d}"
                except ValueError:
                    return None, False
            else:
                return None, False
        else:
            norm_date = now_dt.strftime("%Y-%m-%d")

        has_sec = False
        norm_time = ""
        if raw_time:
            if ":" in raw_time:
                t_parts = raw_time.split(":")
                if len(t_parts) == 3:
                    try:
                        h, m, s = int(t_parts[0]), int(t_parts[1]), int(t_parts[2])
                        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                            return None, False
                        norm_time = f"{h:02d}:{m:02d}:{s:02d}"
                        has_sec = True
                    except ValueError:
                        return None, False
                elif len(t_parts) == 2:
                    try:
                        h, m = int(t_parts[0]), int(t_parts[1])
                        if not (0 <= h <= 23 and 0 <= m <= 59):
                            return None, False
                        norm_time = f"{h:02d}:{m:02d}:00"
                        has_sec = False
                    except ValueError:
                        return None, False
                else:
                    return None, False
            elif raw_time.isdigit():
                try:
                    h = int(raw_time)
                    if not (0 <= h <= 23):
                        return None, False
                    norm_time = f"{h:02d}:00:00"
                    has_sec = False
                except ValueError:
                    return None, False
            else:
                return None, False
        else:
            norm_time = "18:00:00"
            has_sec = False

        try:
            dt = datetime.strptime(f"{norm_date} {norm_time}", "%Y-%m-%d %H:%M:%S")
            return dt, has_sec
        except ValueError:
            return None, False

    def _parse_datetime_string(self, dt_str: str, now_dt: Optional[datetime] = None) -> Tuple[Optional[datetime], bool]:
        """단일 일시 문자열 파싱 (예: '2026-12-04 18:24:37 +0900', '2026-12-04 18:24')"""
        if not dt_str or not dt_str.strip():
            return None, False

        clean_str = dt_str.strip()
        clean_str = re.sub(r"\s*([+-]\d{2}:?\d{2}|Z)$", "", clean_str).strip()

        m3 = re.match(r"^(\d{4}-\d{2}-\d{2})[T\s](\d{1,2}):(\d{1,2}):(\d{1,2})$", clean_str)
        if m3:
            try:
                dt = datetime.strptime(f"{m3.group(1)} {int(m3.group(2)):02d}:{int(m3.group(3)):02d}:{int(m3.group(4)):02d}", "%Y-%m-%d %H:%M:%S")
                return dt, True
            except ValueError:
                return None, False

        m2 = re.match(r"^(\d{4}-\d{2}-\d{2})[T\s](\d{1,2}):(\d{1,2})$", clean_str)
        if m2:
            try:
                dt = datetime.strptime(f"{m2.group(1)} {int(m2.group(2)):02d}:{int(m2.group(3)):02d}:00", "%Y-%m-%d %H:%M:%S")
                return dt, False
            except ValueError:
                return None, False

        if " " in clean_str:
            d_part, t_part = clean_str.split(" ", 1)
            return self._parse_datetime_flexible(d_part, t_part, now_dt)

        return self._parse_datetime_flexible(clean_str, "", now_dt)

    def verify_gate_9_reservation(
        self,
        content: str,
        fm_data: Dict[str, str],
        platform: str,
        is_reserved: Optional[bool] = None,
        reserve_date: Optional[str] = None,
        reserve_time: Optional[str] = None,
        reserve_composite: Optional[str] = None,
        now_dt: Optional[datetime] = None,
        min_buffer_minutes: int = 10
    ) -> List[Violation]:
        violations: List[Violation] = []
        now = now_dt or datetime.now()

        # [1] 예약 여부 선별 판별 (Selective Reservation Detection)
        has_cli_reservation = bool(is_reserved or reserve_composite or reserve_date or reserve_time)

        pub_type = fm_data.get("publish_type", "").lower()
        is_res_fm = str(fm_data.get("is_reserved", "")).lower() in ["true", "yes", "1"]
        reserve_at = fm_data.get("reserve_at") or fm_data.get("scheduled_at") or fm_data.get("reserved_at")
        reserve_date_fm = fm_data.get("reserve_date")
        reserve_time_fm = fm_data.get("reserve_time")
        date_fm = fm_data.get("date")

        is_fm_reservation = (
            pub_type in ["scheduled", "reserved", "reservation"] or
            is_res_fm or
            bool(reserve_at) or
            bool(reserve_date_fm and reserve_time_fm)
        )

        is_target_reservation = False
        raw_target_str = ""
        target_dt: Optional[datetime] = None
        has_explicit_sec = False

        if has_cli_reservation:
            is_target_reservation = True
            raw_d = (reserve_date or "").strip()
            raw_t = (reserve_time or "").strip()
            comp = (reserve_composite or "").strip()
            if comp:
                if " " in comp:
                    parts = comp.split(" ", 1)
                    raw_d = raw_d or parts[0].strip()
                    raw_t = raw_t or parts[1].strip()
                elif "-" in comp:
                    raw_d = raw_d or comp
                elif ":" in comp:
                    raw_t = raw_t or comp
            if not raw_d:
                raw_d = reserve_date_fm or ""
            if not raw_t:
                raw_t = reserve_time_fm or ""
            raw_target_str = f"{raw_d} {raw_t}".strip() or comp
            target_dt, has_explicit_sec = self._parse_datetime_flexible(raw_d, raw_t, now)

        elif is_fm_reservation:
            is_target_reservation = True
            raw_target_str = str(reserve_at or f"{reserve_date_fm or ''} {reserve_time_fm or ''}".strip() or date_fm or "")
            target_dt, has_explicit_sec = self._parse_datetime_string(raw_target_str, now)

        elif date_fm:
            # date 속성이 존재하고 미래 일시인 경우에만 예약 글로 판별하여 지터 및 버퍼 검증 수행
            # (과거 일시이고 publish_type이 scheduled가 아니면 이미 발행된 과거 글이므로 스킵)
            parsed_date_dt, parsed_sec = self._parse_datetime_string(str(date_fm), now)
            if parsed_date_dt and parsed_date_dt > now:
                is_target_reservation = True
                raw_target_str = str(date_fm)
                target_dt = parsed_date_dt
                has_explicit_sec = parsed_sec

        # 일반/즉시공개 글은 예약 검사를 안전하게 건너뜀 (선별적 적용 헌법)
        if not is_target_reservation:
            self._last_reservation_info = {
                "is_reserved": False,
                "target_dt": None,
                "reserve_date": None,
                "reserve_time": None
            }
            return []

        self._last_reservation_info = {
            "is_reserved": True,
            "target_dt": target_dt,
            "reserve_date": target_dt.strftime("%Y-%m-%d") if target_dt else None,
            "reserve_time": target_dt.strftime("%H:%M:%S" if has_explicit_sec else "%H:%M") if target_dt else None
        }

        # [2] 포맷 정합성 검증
        if target_dt is None:
            violations.append(Violation(
                gate_id="GATE_9",
                gate_name="예약 발행 무결성 및 안티봇 지터 방벽",
                rule_id="G9_RESERVATION_INVALID_FORMAT",
                severity="REJECT",
                line_number=1,
                snippet=f"Invalid format: '{raw_target_str}'",
                message=f"[예약 무결성 방벽] 예약 일시 형식이 올바르지 않거나 유효하지 않은 날짜/시간입니다: '{raw_target_str}'",
                fix_hint="예약 일시를 'YYYY-MM-DD HH:MM' 또는 'YYYY-MM-DD HH:MM:SS' 형식으로 정확히 지정하십시오."
            ))
            return violations

        target_str = target_dt.strftime("%Y-%m-%d %H:%M:%S" if has_explicit_sec else "%Y-%m-%d %H:%M")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # [3] 미래 일시 검증 (과거 일시 오발행 차단)
        if target_dt < now:
            violations.append(Violation(
                gate_id="GATE_9",
                gate_name="예약 발행 무결성 및 안티봇 지터 방벽",
                rule_id="G9_RESERVATION_PAST_TIME",
                severity="REJECT",
                line_number=1,
                snippet=f"Target: {target_str} < Now: {now_str}",
                message=f"[오발행 차단] 예약 일시({target_str})가 현재 시각({now_str})보다 과거입니다. 즉시 공개 오발행 방지를 위해 발행을 물리적으로 차단합니다.",
                fix_hint="현재 시각보다 미래의 예약 일시를 지정하십시오."
            ))
            return violations

        # [4] 최소 버퍼 검증 (기본 10분)
        min_allowed = now + timedelta(minutes=min_buffer_minutes)
        if target_dt < min_allowed:
            diff_mins = (target_dt - now).total_seconds() / 60.0
            violations.append(Violation(
                gate_id="GATE_9",
                gate_name="예약 발행 무결성 및 안티봇 지터 방벽",
                rule_id="G9_RESERVATION_BUFFER_UNDERFLOW",
                severity="REJECT",
                line_number=1,
                snippet=f"Buffer: {diff_mins:.1f} mins < Required: {min_buffer_minutes} mins",
                message=f"[오발행 차단] 예약 일시({target_str})는 현재 시각({now_str}) 기준 최소 {min_buffer_minutes}분 이후여야 합니다. (현재 버퍼: {diff_mins:.1f}분)",
                fix_hint=f"충분한 발행 버퍼(최소 {min_buffer_minutes}분 이상)를 확보하여 예약 일시를 재설정하십시오."
            ))

        # [5] 안티봇 지터 검증 (00분 정각 영구 금지)
        if target_dt.minute == 0:
            violations.append(Violation(
                gate_id="GATE_9",
                gate_name="예약 발행 무결성 및 안티봇 지터 방벽",
                rule_id="G9_RESERVATION_BOT_COLLISION_MINUTE",
                severity="REJECT",
                line_number=1,
                snippet=f"Minute collision: '{target_dt.strftime('%H:%M')}'",
                message=f"[안티봇 지터 헌법 위반] 예약 시각의 분이 '00분' 정각({target_dt.strftime('%H:%M')})입니다. 포털 자동화 봇 감지 레이더에 노출될 수 있으므로 정각 발행은 영구 금지됩니다.",
                fix_hint="05~52분 사이의 불규칙한 임의의 분(예: 08분, 14분, 23분, 37분, 46분 등)을 적용하여 인간의 자연스러운 발행 흔적을 보존하십시오."
            ))

        # [6] 개발 블로그 초 단위 랜덤 지터 검증 (00초 정각 영구 금지 및 초 단위 생략 차단)
        is_dev_platform = (platform == "dev" or "dev" in platform or platform == "markets")
        if (has_explicit_sec and target_dt.second == 0) or (is_dev_platform and not has_explicit_sec):
            sec_display = target_dt.strftime('%H:%M:%S') if has_explicit_sec else f"{target_dt.strftime('%H:%M')}:00 (초 생략)"
            violations.append(Violation(
                gate_id="GATE_9",
                gate_name="예약 발행 무결성 및 안티봇 지터 방벽",
                rule_id="G9_RESERVATION_BOT_COLLISION_SECOND",
                severity="REJECT",
                line_number=1,
                snippet=f"Seconds collision: '{sec_display}'",
                message=f"[안티봇 지터 헌법 위반] 예약 타임스탬프의 초가 '00초' 정각이거나 초 단위가 누락({sec_display})되었습니다. 개발 블로그 랜덤 초 지터 헌법을 위반했습니다.",
                fix_hint="Frontmatter의 date 속성에 정각(00초)을 배제하고 05~58초 사이의 불규칙한 랜덤 초(예: 10:52:43 +0900)를 적용하십시오."
            ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 10: 공인 실측 출처 필수 귀속 관문 (Mandatory Real-Time Fact-Check Attribution Gate)
    # --------------------------------------------------------------------------
    def verify_gate_10_fact_check_attribution(
        self,
        file_path: str,
        fm_data: Dict[str, Any],
        body: str,
        platform: str
    ) -> List[Violation]:
        """
        [Gate 10] 공인 실측 출처 필수 귀속 검증:
        1. Frontmatter에 'fact_check_sources'(공인 실측 출처 목록) 필수 및 공인 규격 검증
        2. Frontmatter에 'verification_date'(실측 검증 일자) 필수 및 유효 연도(2025~2027) 검증
        3. 본문 내 핵심 주장 또는 수치에 대한 공인 출처 인용('[출처: ...]', '> 출처: ...' 등) 필수
        """
        violations = []

        # 1. Frontmatter fact_check_sources 검증
        sources = fm_data.get("fact_check_sources") or fm_data.get("fact_check_source") or fm_data.get("sources")
        if not sources:
            violations.append(Violation(
                gate_id="GATE_10",
                gate_name="공인 실측 출처 필수 귀속 관문",
                rule_id="G10_MISSING_FM_SOURCES",
                severity="REJECT",
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
                    gate_id="GATE_10",
                    gate_name="공인 실측 출처 필수 귀속 관문",
                    rule_id="G10_INVALID_FM_SOURCES",
                    severity="REJECT",
                    line_number=1,
                    snippet=f"Sources: {sources}",
                    message="[공인 실측 출처 규격 미달] 'fact_check_sources'에 공인된 공식 출처(공식 URL, 정부 고시, 커널 커밋 해시, PubMed DOI, RFC/W3C 표준 사양 등)가 식별되지 않습니다.",
                    fix_hint="도메인별 공인 공식 URL(github, kernel.org, gov/go.kr, sec.gov 등) 또는 법령/고시/RFC 규격을 명시하십시오."
                ))

        # 2. Frontmatter verification_date 검증
        ver_date = fm_data.get("verification_date") or fm_data.get("verified_at") or fm_data.get("fact_check_date")
        if not ver_date:
            violations.append(Violation(
                gate_id="GATE_10",
                gate_name="공인 실측 출처 필수 귀속 관문",
                rule_id="G10_MISSING_FM_VERIFICATION_DATE",
                severity="REJECT",
                line_number=1,
                snippet="Missing 'verification_date' in Frontmatter",
                message="[실측 검증 일자 누락] YAML Frontmatter에 'verification_date'(실측 검증 일자)가 누락되었습니다.",
                fix_hint="Frontmatter에 'verification_date: \"YYYY-MM-DD\"' 형식으로 공인 실측 교차 검증을 완료한 날짜를 명시하십시오."
            ))
        else:
            m_date = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(ver_date).strip())
            if not m_date:
                violations.append(Violation(
                    gate_id="GATE_10",
                    gate_name="공인 실측 출처 필수 귀속 관문",
                    rule_id="G10_INVALID_FM_VERIFICATION_DATE",
                    severity="REJECT",
                    line_number=1,
                    snippet=f"verification_date: '{ver_date}'",
                    message="[실측 검증 일자 형식 오류] 'verification_date'는 YYYY-MM-DD 형식이어야 합니다.",
                    fix_hint="예: 'verification_date: \"2026-11-22\"' 형식으로 유효한 연월일을 기재하십시오."
                ))
            else:
                year = int(m_date.group(1))
                if year < 2025 or year > 2027:
                    violations.append(Violation(
                        gate_id="GATE_10",
                        gate_name="공인 실측 출처 필수 귀속 관문",
                        rule_id="G10_OUTDATED_FM_VERIFICATION_DATE",
                        severity="REJECT",
                        line_number=1,
                        snippet=f"Year: {year}",
                        message=f"[실측 검증 일자 연도 오류] 실측 검증 일자({year}년)가 당해 운영 연도(2025~2027년) 범위를 벗어났습니다.",
                        fix_hint="현재 운영 시점인 당해 연도 날짜를 기재하십시오."
                    ))

        # 3. 본문 내 공인 출처 귀속 인용 검증 (코드 블록 제외 산문 본문 대상)
        body_prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        has_body_attribution = any(re.search(pat, body_prose, re.IGNORECASE | re.MULTILINE) for pat in BODY_ATTRIBUTION_PATTERNS)
        if not has_body_attribution:
            violations.append(Violation(
                gate_id="GATE_10",
                gate_name="공인 실측 출처 필수 귀속 관문",
                rule_id="G10_MISSING_BODY_ATTRIBUTION",
                severity="REJECT",
                line_number=1,
                snippet="No in-body source attribution found in prose",
                message="[본문 공인 출처 인용 누락] 본문 내 핵심 주장 또는 수치에 대한 공인 출처 인용('[출처: ...]', '> 출처: ...', 또는 참고문헌 섹션)이 누락되었습니다.",
                fix_hint="본문 내에 '[출처: 공인기관 공식문서]' 또는 '> 출처: https://...' 형태의 인용을 의무 삽입하십시오."
            ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 11: 도메인별 이론 정합성 및 수치 환각 차단 관문 (Theoretical & Numerical Integrity)
    # --------------------------------------------------------------------------
    def verify_gate_11_theory_and_numerical_integrity(
        self,
        file_path: str,
        body: str,
        fm_data: Dict[str, Any],
        lines: List[str],
        platform: str
    ) -> List[Violation]:
        """
        [Gate 11] 도메인별 이론 정합성 및 수치 환각 차단:
        1. 정부 정책 / 복지 / 생활 금융 (solidlog): 2026 기준 중위소득, 생계급여 32%, 청년도약계좌, 금투세 폐지
        2. 건강 / 영양제 성분 과학 (infopiece): 오메가3 TG/EE/rTG 분자결합/생체이용률, IFOS 5-Star, 마그네슘 흡수율
        3. 기술 / 개발 / 인프라 (dev, softwin, tidynote): net.ipv4.tcp_tw_recycle 제거, sysctl 범위, k8s Ingress v1, Linux 커널
        4. 증시 / 매크로 / 금융 (stock, markets): 연준 순유동성 공식 (WALCL - TGA - ON RRP), SEC 10-K/10-Q/13F 공시 양식
        """
        violations = []
        in_code_block = False
        code_lang = ""

        for idx, line in enumerate(lines, start=1):
            s_line = line.strip()
            if s_line.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_lang = ""
                else:
                    in_code_block = True
                    code_lang = s_line[3:].strip().lower()
                continue
            if not s_line:
                continue

            # diff 코드 블록 내의 제거 라인(-)은 폐지 설정 제거이므로 허용
            if in_code_block and code_lang in ["diff", "patch"] and (s_line.startswith("-") or s_line.startswith("- ")):
                continue

            # 마크다운 강조 서식(**, _, ` 등) 및 인라인 태그 제거 버전 생성하여 포착 누락 방지
            clean_line = re.sub(r"[*_`]", "", line)
            clean_line = re.sub(r"</?[a-zA-Z0-9]+[^>]*>", "", clean_line)

            # [11-1] Welfare & Tax
            for pattern, severity, rule_id, message, fix_hint in WELFARE_TAX_RULES:
                matched = re.search(pattern, line) or re.search(pattern, clean_line)
                if matched:
                    # 1) 기준 중위소득: 609만 원/6,097,773원 정답 수치와 과거 비교 서술 시 오탐 방지
                    if rule_id == "G11_WELFARE_OUTDATED_MEDIAN_INCOME" and ("609만" in line or "6,097,773" in line):
                        continue
                    # 2) 생계급여: 32% 정답 수치와 과거 30% 비교 서술 시 오탐 방지
                    if rule_id == "G11_WELFARE_OUTDATED_LIVELIHOOD_BENEFIT" and "32%" in line:
                        continue
                    # 3) 청년도약계좌: 5년 만기 및 7,500만원 기준 적시하면서 과거 적금 비교 시 오탐 방지
                    if rule_id == "G11_WELFARE_YOUTH_ACCOUNT_CONFUSION" and ("만기 5년" in line or "5년 만기" in line or "7,500" in line):
                        continue
                    # 4) 금투세: 폐지/철회/유예 사실 적시 시 오탐 방지
                    if rule_id == "G11_TAX_ABOLISHED_FINANCIAL_INVESTMENT_TAX" and any(w in line for w in ["폐지", "철회", "유예", "무산", "취소", "사라진"]):
                        continue

                    violations.append(Violation(
                        gate_id="GATE_11",
                        gate_name="도메인별 이론 정합성 및 수치 환각 차단 관문",
                        rule_id=rule_id,
                        severity=severity,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=message,
                        fix_hint=fix_hint
                    ))

            # [11-2] Health & Nutrition Science
            for pattern, severity, rule_id, message, fix_hint in HEALTH_NUTRITION_RULES:
                matched = re.search(pattern, line) or re.search(pattern, clean_line)
                if matched:
                    # rTG형이 EE형을 재에스테르화/정제하여 글리세롤에 결합한 형태임을 정확히 설명한 과학적 서술 허용
                    if rule_id == "G11_HEALTH_FALSE_RTG_STRUCTURE" and any(w in line for w in ["재에스테르화", "정제하여", "정제한", "가공하여", "결합한", "결합시킨", "만들어진", "원료로"]):
                        continue

                    violations.append(Violation(
                        gate_id="GATE_11",
                        gate_name="도메인별 이론 정합성 및 수치 환각 차단 관문",
                        rule_id=rule_id,
                        severity=severity,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=message,
                        fix_hint=fix_hint
                    ))

            # [11-3] Tech & Dev & Infra
            for pattern, severity, rule_id, message, fix_hint in TECH_INFRA_RULES:
                matched = re.search(pattern, line) or re.search(pattern, clean_line)
                if matched:
                    # tcp_tw_recycle 제거/삭제 사실 설명 허용
                    if rule_id == "G11_TECH_REMOVED_SYSCTL_TW_RECYCLE" and any(w in line for w in ["제거", "삭제", "폐지", "deprecated", "removed", "지원하지", "사라진", "권장하지", "사용하면 안", "쓰면 안"]):
                        continue
                    # 엔터프라이즈 리눅스 배포판 버전(RHEL 7.9, CentOS 7 등) 오탐 방지
                    if rule_id == "G11_TECH_NONEXISTENT_KERNEL_VERSION" and any(d in line for d in ["Enterprise Linux", "RHEL", "CentOS", "Oracle Linux", "AlmaLinux", "Rocky Linux", "Debian", "Ubuntu", "SUSE"]):
                        continue
                    # io_uring 커널 버전 미지원 설명 허용
                    if rule_id == "G11_TECH_KERNEL_FEATURE_VERSION_MISMATCH" and any(w in line for w in ["지원하지 않", "지원 안", "미지원", "사용할 수 없", "도입되지 않", "없었", "이전에는 없"]):
                        continue

                    violations.append(Violation(
                        gate_id="GATE_11",
                        gate_name="도메인별 이론 정합성 및 수치 환각 차단 관문",
                        rule_id=rule_id,
                        severity=severity,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=message,
                        fix_hint=fix_hint
                    ))

            # [11-4] Stock & Markets
            for pattern, severity, rule_id, message, fix_hint in STOCK_MARKETS_RULES:
                matched = re.search(pattern, line) or re.search(pattern, clean_line)
                if matched:
                    # 10-K 연간 보고서 vs 10-Q 분기 보고서 대비 서술 허용
                    if rule_id == "G11_STOCK_SEC_10K_CONFUSION" and ("10-Q" in line and ("연간" in line or "Annual" in line)):
                        continue
                    if rule_id == "G11_STOCK_SEC_10Q_CONFUSION" and ("10-K" in line and ("분기" in line or "Quarterly" in line)):
                        continue
                    if rule_id == "G11_STOCK_SEC_13F_CONFUSION" and ("Form 4" in line or "Form-4" in line):
                        continue

                    violations.append(Violation(
                        gate_id="GATE_11",
                        gate_name="도메인별 이론 정합성 및 수치 환각 차단 관문",
                        rule_id=rule_id,
                        severity=severity,
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=message,
                        fix_hint=fix_hint
                    ))

        return violations

    # --------------------------------------------------------------------------
    # Gate 12: 실시간 팩트체크 및 기억 의존 환각 탐지기 (Zero-Memory Hallucination)
    # --------------------------------------------------------------------------
    def verify_gate_12_zero_memory_hallucination(
        self,
        file_path: str,
        body: str,
        fm_data: Dict[str, Any],
        lines: List[str],
        platform: str
    ) -> List[Violation]:
        """
        [Gate 12] 실시간 팩트체크 및 기억 의존 환각 탐지:
        1. 기준 연도가 결여된 모호한 시점 지시어('최근 몇 년간') 차단
        2. 존재하지 않는 조작된 CLI 플래그 및 API 메서드 차단
        3. 구체적 연구/설문 출처가 결여된 조작된 통계 수치 assertion 차단
        4. 과거 낡은 데이터 현재화 및 리브랜딩 소멸 브랜드(KINDEX, KBSTAR 등) 차단
        """
        violations = []

        in_code_block = False
        for idx, line in enumerate(lines, start=1):
            s_line = line.strip()
            if s_line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if not s_line:
                continue

            # 1. 모호한 시점 지시어 탐지 (기준 연도 202[0-9] 미포함 시 차단 - 본문 산문 대상)
            if not in_code_block:
                for pat in VAGUE_TEMPORAL_PATTERNS:
                    m = re.search(pat, line, re.IGNORECASE)
                    if m:
                        if not re.search(r"202[4-7]", line):
                            violations.append(Violation(
                                gate_id="GATE_12",
                                gate_name="실시간 팩트체크 및 기억 의존 환각 탐지기",
                                rule_id="G12_VAGUE_TEMPORAL_MARKER",
                                severity="REJECT",
                                line_number=idx,
                                snippet=line.strip()[:100],
                                message=f"[모호한 시점 표기 및 과거 기억 환각] '{m.group(0)}'과 같이 기준 연도가 결여된 모호한 시점 표기가 감지되었습니다. 사전학습 기억에 의존한 모호한 시점 표기를 금지합니다.",
                                fix_hint="'2024~2026년' 또는 '2026년 현재 기준'과 같이 구체적 실측 기준 연도를 명시하십시오."
                            ))

            # 2. 존재하지 않는 가상 API / 조작된 CLI 플래그 탐지 (코드 블록 내부 포함)
            for pat, reason in FABRICATED_API_PATTERNS:
                if re.search(pat, line):
                    violations.append(Violation(
                        gate_id="GATE_12",
                        gate_name="실시간 팩트체크 및 기억 의존 환각 탐지기",
                        rule_id="G12_FABRICATED_API_OR_FLAG",
                        severity="REJECT",
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=f"[존재하지 않는 가상 API/CLI 옵션 환각] {reason}",
                        fix_hint="공식 도큐먼트 사양에 존재하는 실제 명령어 옵션 또는 메서드로 수정하십시오."
                    ))

            # 3. 출처 미상의 조작된 통계 수치 assertion 탐지 (본문 산문 대상)
            if not in_code_block:
                for pat in UNREFERENCED_STATISTICS_PATTERNS:
                    m_stat = re.search(pat, line)
                    if m_stat:
                        has_citation = bool(re.search(r"(?:조사|설문|보고서|통계|출처|에\s*따르면|기준|Survey|Report|Study|According)", line))
                        if not has_citation:
                            violations.append(Violation(
                                gate_id="GATE_12",
                                gate_name="실시간 팩트체크 및 기억 의존 환각 탐지기",
                                rule_id="G12_FABRICATED_STATISTICS",
                                severity="REJECT",
                                line_number=idx,
                                snippet=line.strip()[:100],
                                message=f"[출처 미상의 조작된 통계 수치 환각] 구체적 연구 기관, 공식 설문, 리포트 명칭이 결여된 모호한 통계 수치('{m_stat.group(0)}')가 감지되었습니다.",
                                fix_hint="공식 설문조사(예: Stack Overflow 2025 개발자 설문, DORA 2024 Report 등)의 명칭과 연도를 명확히 적시하십시오."
                            ))

            # 4. 과거 낡은 데이터 현재화 및 리브랜딩 소멸 브랜드 탐지 (코드 블록 내부 포함)
            # 역사적 리브랜딩 설명 문맥(예: '과거 KINDEX에서 ACE로 리브랜딩', '구 KBSTAR')은 허용
            is_historical_rebranding = bool(
                re.search(
                    r"(?:과거\s*(?:KINDEX|KBSTAR|ARIRANG|Credit\s+Suisse)|(?:구\s*|\(구\s*)(?:KINDEX|KBSTAR|ARIRANG|Credit\s+Suisse)|(?:KINDEX|KBSTAR|ARIRANG)\s*(?:에서|이|가)?\s*(?:ACE|RISE|PLUS)로|리브랜딩|rebrand|인수\s*합병|인수되어|합병되어)",
                    line,
                    re.IGNORECASE,
                )
            )

            for pat, reason in STALE_BRAND_PATTERNS:
                if any(k in pat for k in ["KINDEX", "KBSTAR", "ARIRANG", "Credit"]) and is_historical_rebranding:
                    continue
                if re.search(pat, line):
                    violations.append(Violation(
                        gate_id="GATE_12",
                        gate_name="실시간 팩트체크 및 기억 의존 환각 탐지기",
                        rule_id="G12_OUTDATED_STALE_BRAND_OR_YEAR",
                        severity="REJECT",
                        line_number=idx,
                        snippet=line.strip()[:100],
                        message=f"[낡은 데이터 및 리브랜딩 소멸 명칭 환각] {reason}",
                        fix_hint="최신 실측 데이터 및 2026년 기준 공식 명칭을 반영하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # 🔍 공인 실측 데이터 교차 검증 CLI/API 러너 (Cross-Reference Runner)
    # --------------------------------------------------------------------------
    def cross_reference_assertions(self, content: str, platform: str = "auto") -> List[FactCheckAssertionResult]:
        """
        본문 내 주요 사실(수치, 파라미터, 공시 공식 등)을 공인 마스터 데이터와 교차 검증하는 러너.
        정합성 확인(is_valid=True) 및 불일치/환각(is_valid=False) 모두 판정 리포트 생성.
        """
        results: List[FactCheckAssertionResult] = []

        # 1. Welfare & Tax cross-checks
        if re.search(r"중위소득", content):
            if re.search(r"2026년.*?중위소득.*?(?:609만|6,097,773)", content):
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="2026_median_income",
                    is_valid=True,
                    snippet="2026년 기준 중위소득 (6,097,773원)",
                    message="보건복지부 2026년 기준 중위소득 고시 데이터와 100% 일치합니다.",
                    expected="6,097,773원 (4인 가구 기준)"
                ))
            elif re.search(r"2026년.*?중위소득.*?(?:5[0-9]{2}만)", content):
                m_out = re.search(r"2026년.*?중위소득.*?(5[0-9]{2}만\s*원)", content)
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="2026_median_income",
                    is_valid=False,
                    snippet=m_out.group(0) if m_out else "2026년 중위소득 과거 수치",
                    message="2026년 기준 중위소득이 과거 수치(2023~2024년)로 왜곡 기술되었습니다.",
                    expected="6,097,773원 (4인 가구 기준)",
                    actual=m_out.group(1) if m_out else "5xx만 원"
                ))

        if re.search(r"생계급여", content):
            if re.search(r"생계급여.*?(?:32%|32\s*퍼센트)", content):
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="livelihood_benefit_threshold",
                    is_valid=True,
                    snippet="생계급여 선정기준 32%",
                    message="2024~2026년 보건복지부 생계급여 선정기준(중위소득 32% 이하)과 일치합니다.",
                    expected="기준 중위소득 32% 이하"
                ))
            elif re.search(r"생계급여.*?(?:선정\s*기준|수급).*?(?:30%)", content):
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="livelihood_benefit_threshold",
                    is_valid=False,
                    snippet="생계급여 선정기준 30%",
                    message="생계급여 선정기준이 2023년 이전 폐지된 구 규정(30%)으로 서술되었습니다.",
                    expected="기준 중위소득 32% 이하",
                    actual="30%"
                ))

        if re.search(r"(?:금투세|금융투자소득세)", content):
            if re.search(r"(?:금투세|금융투자소득세).*?(?:폐지|철회)", content):
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="financial_investment_tax_status",
                    is_valid=True,
                    snippet="금융투자소득세 폐지 확정",
                    message="금융투자소득세(금투세) 폐지 확정 사실과 정확히 일치합니다."
                ))
            elif re.search(r"(?:2026년|올해).*?(?:금투세|금융투자소득세).*?(?:시행|과세)", content):
                results.append(FactCheckAssertionResult(
                    domain="welfare_tax",
                    assertion_type="financial_investment_tax_status",
                    is_valid=False,
                    snippet="2026년 금투세 시행/과세",
                    message="폐지 확정된 금투세가 2026년에 시행되거나 과세된다는 사전학습 환각이 감지되었습니다.",
                    expected="폐지 확정",
                    actual="2026년 시행/과세 주장"
                ))

        # 2. Nutrition Science cross-checks
        if re.search(r"rTG", content):
            if re.search(r"rTG.*?(?:글리세롤|재에스테르화)", content):
                results.append(FactCheckAssertionResult(
                    domain="health_nutrition",
                    assertion_type="rtg_molecular_structure",
                    is_valid=True,
                    snippet="rTG형 글리세롤 재에스테르화 결합 구조",
                    message="식약처 및 생화학 표준 분자구조 사양과 100% 일치합니다."
                ))

        if re.search(r"산화\s*마그네슘", content):
            if re.search(r"산화\s*마그네슘.*?(?:4%|낮|완하)", content):
                results.append(FactCheckAssertionResult(
                    domain="health_nutrition",
                    assertion_type="magnesium_oxide_absorption",
                    is_valid=True,
                    snippet="산화 마그네슘 저흡수율(약 4%) 및 완하작용 기전",
                    message="식약처 및 임상 약리학 흡수율 데이터와 일치합니다."
                ))

        # 3. Fed Net Liquidity cross-checks
        if re.search(r"(?:Fed\s*Net\s*Liquidity|연준\s*순유동성)", content):
            if re.search(r"WALCL\s*-\s*TGA\s*-\s*ON\s*RRP", content) or re.search(r"총자산\s*-\s*TGA\s*-\s*역레포", content):
                results.append(FactCheckAssertionResult(
                    domain="stock_markets",
                    assertion_type="fed_liquidity_formula",
                    is_valid=True,
                    snippet="WALCL - TGA - ON RRP",
                    message="연준 대차대조표 및 순유동성 정합 공식과 100% 일치합니다.",
                    expected="WALCL - TGA - ON RRP"
                ))
            elif re.search(r"(?:WALCL|총자산)\s*\+\s*(?:TGA|ON\s*RRP|역레포)", content):
                results.append(FactCheckAssertionResult(
                    domain="stock_markets",
                    assertion_type="fed_liquidity_formula",
                    is_valid=False,
                    snippet="연준 순유동성 TGA/역레포 가산(+) 오류",
                    message="TGA 및 역레포는 연준 부채 항목으로 상업은행 지준을 흡수하므로 순유동성에서 차감(-)해야 합니다.",
                    expected="WALCL - TGA - ON RRP",
                    actual="TGA 또는 역레포 가산(+)"
                ))

        # 4. Tech & Dev cross-checks
        if re.search(r"tcp_tw_recycle", content):
            if re.search(r"tcp_tw_recycle.*?(?:4\.12|제거|삭제|폐지|removed)", content):
                results.append(FactCheckAssertionResult(
                    domain="tech_infra",
                    assertion_type="sysctl_tw_recycle_status",
                    is_valid=True,
                    snippet="net.ipv4.tcp_tw_recycle Linux 4.12 제거 사실",
                    message="리눅스 커널 4.12 영구 제거 공식 커밋 명세와 일치합니다."
                ))

        return results


    # --------------------------------------------------------------------------
    # 🛡️ [Gate 13] 동적 구문, 아티팩트 및 정합성 검증 관문 (Dynamic Syntax & Diff Integrity)
    # --------------------------------------------------------------------------
    def verify_gate_13_dynamic_syntax_and_diff(
        self,
        file_path: str,
        body: str,
        fm_data: Dict[str, Any],
        lines: List[str],
        platform: str
    ) -> List[Violation]:
        """
        [Gate 13] 본문 내 diff 블록 문법 무결성, Prometheus PromQL 집계 연산자 누락 방지,
        실존하지 않는 허위 메트릭 차단 및 리눅스 커널 procfs 규격을 정밀 검증합니다.
        """
        violations: List[Violation] = []
        code_blocks = self.extract_code_blocks(body)

        # 1. Unified Diff 블록 Hunk 문법 및 라인 수 무결성 검증
        hunk_header_re = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$")
        for lang, code, start_line in code_blocks:
            if lang.lower() in ("diff", "patch"):
                diff_lines = code.splitlines()
                in_hunk = False
                idx = 0
                while idx < len(diff_lines):
                    d_line = diff_lines[idx]
                    if d_line.startswith("@@ "):
                        in_hunk = True
                        m = hunk_header_re.match(d_line)
                        if not m:
                            violations.append(Violation(
                                gate_id="GATE_13",
                                gate_name="동적 구문 및 아티팩트 정합성",
                                rule_id="G13_DIFF_HUNK_CORRUPTION",
                                severity="REJECT",
                                line_number=start_line + idx,
                                snippet=d_line,
                                message="Unified Diff Hunk 헤더 형식이 손상되었습니다 (정규 표현식: @@ -a,b +c,d @@).",
                                fix_hint="표준 Unified Diff 형식에 맞추어 hunk 헤더를 교정하십시오."
                            ))
                            idx += 1
                            continue

                        # Hunk 내부 실제 라인 수 검증 (git apply 호환성)
                        old_count = int(m.group(2)) if m.group(2) is not None else 1
                        new_count = int(m.group(4)) if m.group(4) is not None else 1
                        actual_old = 0
                        actual_new = 0
                        j = idx + 1
                        while j < len(diff_lines):
                            hl = diff_lines[j]
                            if hl.startswith("@@ ") or hl.startswith("--- ") or hl.startswith("+++ "):
                                break
                            if hl.startswith("+"):
                                actual_new += 1
                            elif hl.startswith("-"):
                                actual_old += 1
                            elif hl.startswith("\\"):
                                pass
                            else:
                                actual_old += 1
                                actual_new += 1
                            j += 1

                        if (actual_old != old_count) or (actual_new != new_count):
                            violations.append(Violation(
                                gate_id="GATE_13",
                                gate_name="동적 구문 및 아티팩트 정합성",
                                rule_id="G13_DIFF_HUNK_LINE_COUNT_MISMATCH",
                                severity="REJECT",
                                line_number=start_line + idx,
                                snippet=f"{d_line} (명시: -{old_count}/+{new_count}, 실제: -{actual_old}/+{actual_new})",
                                message=f"Unified Diff Hunk 헤더의 행 수(-{old_count}/+{new_count})와 실제 행 수(-{actual_old}/+{actual_new})가 불일치하여 git apply 실패를 유발합니다.",
                                fix_hint="Hunk 헤더의 라인 수를 실제 diff 본문 라인 수와 정확히 일치하도록 교정하십시오."
                            ))
                        idx = j
                    elif in_hunk:
                        if d_line.startswith("--- ") or d_line.startswith("+++ "):
                            violations.append(Violation(
                                gate_id="GATE_13",
                                gate_name="동적 구문 및 아티팩트 정합성",
                                rule_id="G13_DIFF_HUNK_CORRUPTION",
                                severity="REJECT",
                                line_number=start_line + idx,
                                snippet=d_line,
                                message="Diff Hunk 내부에 파일 헤더 접두사('--- ' 또는 '+++ ')가 노출되어 표준 diff 파서에서 파일 헤더로 오인되는 치명적 구문 오류가 발견되었습니다.",
                                fix_hint="diff 내부 주석 앞에는 '- -- ' 형식으로 공백을 두어 파일 헤더와 분리하십시오."
                            ))
                        idx += 1
                    else:
                        idx += 1

        # 2. Prometheus Alert 룰 및 PromQL 다차원 카운터 집계 누락(Alert Storm) 검증
        prom_alert_pattern = re.compile(r"alert:\s*([a-zA-Z0-9_-]+).*?expr:\s*([^\r\n]+)", re.DOTALL)
        for match in prom_alert_pattern.finditer(body):
            alert_name = match.group(1)
            expr = match.group(2).strip()
            multidim_counters = ["node_cpu_seconds_total", "container_cpu_usage_seconds_total"]
            for counter in multidim_counters:
                if counter in expr and "rate(" in expr:
                    if not any(agg in expr for agg in ["avg by", "sum by", "avg(", "sum(", "max by", "min by"]):
                        violations.append(Violation(
                            gate_id="GATE_13",
                            gate_name="동적 구문 및 아티팩트 정합성",
                            rule_id="G13_PROMQL_MISSING_AGGREGATION",
                            severity="REJECT",
                            line_number=1,
                            snippet=f"{alert_name}: {expr}",
                            message=f"다차원 레이블 카운터({counter})에 차원 집계(avg by, sum by) 연산자가 누락되어 다중 코어/디바이스 환경에서 알람 폭풍(Alert Storm)을 유발합니다.",
                            fix_hint="expr: avg by (instance) (rate(...)) > ... 형식으로 호스트 단위 집계를 적용하십시오."
                        ))

        # 3. 실존하지 않는 Prometheus 허위 메트릭 검출
        nonexistent_metrics = [
            ("mysql_global_status_innodb_page_splits", "MySQL SHOW GLOBAL STATUS에 Innodb_page_splits 상태 변수는 존재하지 않습니다. mysql_info_schema_innodb_metrics_index_page_splits_total 또는 mysql_global_status_innodb_pages_created를 사용하십시오."),
            ("node_netstat_softnet_dropped", "공식 node_exporter 정규 메트릭은 node_softnet_dropped_total입니다."),
            ("node_netstat_softnet_timesqueeze", "공식 node_exporter 정규 메트릭은 node_softnet_times_squeezed_total입니다."),
            ("node_softnet_timesqueeze_total", "공식 node_exporter 정규 메트릭은 node_softnet_times_squeezed_total입니다."),
            ("rabbitmq_process_count", "공식 rabbitmq_prometheus 정규 메트릭은 erlang_vm_process_count입니다."),
            ("rabbitmq_process_limit", "공식 rabbitmq_prometheus 정규 메트릭은 erlang_vm_process_limit입니다."),
            ("rabbitmq_channel_messages_confirmed_duration_seconds_bucket", "공식 rabbitmq_prometheus 플러그인에는 confirm duration 히스토그램 메트릭이 존재하지 않습니다.")
        ]
        for bad_metric, hint in nonexistent_metrics:
            if bad_metric in body:
                violations.append(Violation(
                    gate_id="GATE_13",
                    gate_name="동적 구문 및 아티팩트 정합성",
                    rule_id="G13_NONEXISTENT_PROMETHEUS_METRIC",
                    severity="REJECT",
                    line_number=1,
                    snippet=bad_metric,
                    message=f"공식 exporter에 존재하지 않는 허위/비표준 메트릭('{bad_metric}')이 검출되었습니다.",
                    fix_hint=hint
                ))

        # 4. 리눅스 커널 procfs 덤프 열 개수 정합성 검증 (/proc/net/softnet_stat)
        if "/proc/net/softnet_stat" in body:
            # hex 덤프 줄 검출 (예: 00049281 00000000 ...)
            for l_idx, line in enumerate(lines):
                tokens = line.strip().split()
                if len(tokens) >= 8 and all(re.match(r"^[0-9a-fA-F]{8}$", t) for t in tokens):
                    if len(tokens) != 11:
                        violations.append(Violation(
                            gate_id="GATE_13",
                            gate_name="동적 구문 및 아티팩트 정합성",
                            rule_id="G13_PROCFS_COLUMN_MISMATCH",
                            severity="REJECT",
                            line_number=l_idx + 1,
                            snippet=line.strip(),
                            message=f"/proc/net/softnet_stat의 커널 표준 출력은 정확히 11개 16진수 열(net/core/net-procfs.c softnet_seq_show)이어야 하나, {len(tokens)}개 열로 왜곡되었습니다.",
                            fix_hint="커널 5.x/6.x 공식 규격인 11열 형식으로 교정하십시오."
                        ))

        # 5. 폐지된 파라미터를 해결책으로 권장하는 안티패턴 검출
        # (단, 헛발질/오진 분석에서 언급하는 것은 허용하고, sysctl.conf나 해결책 블록에서 활성화하는 경우만 차단)
        for lang, code, start_line in code_blocks:
            if any(k in code for k in ["net.ipv4.tcp_tw_recycle = 1", "tcp_tw_recycle=1", "net.ipv4.tcp_tw_recycle=1"]):
                # 이것이 '해결책' 코드 블록인지 검사
                surrounding = (body[max(0, body.find(code)-250):body.find(code)] + "\n" + code).lower()
                if not any(neg in surrounding for neg in ["오진", "실패", "failed", "mistake", "wrong", "안티패턴", "flawed", "anti-pattern", "do not use", "dangerous", "deprecated"]):
                    violations.append(Violation(
                        gate_id="GATE_13",
                        gate_name="동적 구문 및 아티팩트 정합성",
                        rule_id="G13_DEPRECATED_PARAM_AS_FIX",
                        severity="REJECT",
                        line_number=start_line,
                        snippet="tcp_tw_recycle = 1",
                        message="리눅스 커널 4.12에서 영구 제거(removed)된 net.ipv4.tcp_tw_recycle을 해결책으로 적용하려는 치명적 오류가 발견되었습니다.",
                        fix_hint="tcp_tw_recycle 활성화를 완전히 제거하고 tcp_tw_reuse=1을 적용하십시오."
                    ))

        return violations

    # --------------------------------------------------------------------------
    # 🛡️ [Gate 14] 독립 감사 서브에이전트(Red Team Critic) 검증 관문 (Subagent Audit Gate)
    # --------------------------------------------------------------------------
    def verify_gate_14_subagent_redteam_audit(
        self,
        file_path: str,
        body: str,
        fm_data: Dict[str, Any],
        platform: str,
        require_subagent_audit: bool = False
    ) -> List[Violation]:
        """
        [Gate 14] 오케스트레이터의 invoke_subagent(TypeName='research', Role='Independent Red Team Post Auditor')
        독립 제3자 감사 서브에이전트 실측 감사 및 승인 토큰 존재 여부를 검증합니다.
        """
        violations: List[Violation] = []

        # 서브에이전트 감사 증적 확인
        has_audit_env = os.environ.get("SUBAGENT_AUDIT_PASSED") == "1"
        has_audit_fm = bool(fm_data.get("subagent_audit"))
        
        # 파일별 서명 토큰 파일 확인
        token_path = Path(".subagent_audit_token")
        file_token_path = Path(file_path).with_suffix(".audit_token")
        has_token_file = token_path.exists() or file_token_path.exists()

        is_audited = has_audit_env or has_audit_fm or has_token_file

        # 배포 모드이거나 강제 검증 모드인 경우
        force_require = (
            require_subagent_audit or
            os.environ.get("REQUIRE_SUBAGENT_AUDIT") == "1" or
            os.environ.get("STRICT_GATEKEEPER") == "1"
        )

        if force_require and not is_audited:
            violations.append(Violation(
                gate_id="GATE_14",
                gate_name="독립 감사 서브에이전트 의무 감사 관문",
                rule_id="G14_SUBAGENT_AUDIT_REQUIRED",
                severity="REJECT",
                line_number=1,
                snippet=Path(file_path).name,
                message="[독립 감사 미수행] 독립 감사용 서브에이전트(Red Team Auditor)의 실측 정밀 감사가 선행되지 않았습니다. 오케스트레이터의 invoke_subagent(TypeName='research', Role='Independent Red Team Post Auditor') 호출 및 승인 토큰이 필수적입니다.",
                fix_hint="오케스트레이터가 research 서브에이전트를 호출하여 제3자 엔지니어링 감사를 완료한 후 발행 파이프라인을 속행하십시오."
            ))
        elif not is_audited:
            # 일반 점검 모드에서는 WARNING으로 안내
            violations.append(Violation(
                gate_id="GATE_14",
                gate_name="독립 감사 서브에이전트 의무 감사 관문",
                rule_id="G14_SUBAGENT_AUDIT_PENDING",
                severity="WARNING",
                line_number=1,
                snippet=Path(file_path).name,
                message="[독립 감사 대기 중] 독립 감사용 서브에이전트(Red Team Critic)의 최종 검수 승인 토큰이 아직 발행되지 않았습니다. 최종 배포 전 독립 감사가 권장됩니다.",
                fix_hint="오케스트레이터에게 독립 감사 서브에이전트 가동을 요청하십시오."
            ))

        return violations

    # --------------------------------------------------------------------------
    # 🚀 마스터 통합 검증 실행기 (Master Verification Method)
    # --------------------------------------------------------------------------
    def verify(
        self,
        file_path: str,
        platform_override: Optional[str] = None,
        platform: Optional[str] = None,
        is_reserved: Optional[bool] = None,
        reserve_date: Optional[str] = None,
        reserve_time: Optional[str] = None,
        reserve_composite: Optional[str] = None,
        now_dt: Optional[datetime] = None,
        min_buffer_minutes: int = 10,
        require_subagent_audit: bool = False
    ) -> GateReport:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return GateReport(
                file_path=file_path,
                platform="unknown",
                is_passed=False,
                score=0,
                reject_count=1,
                warning_count=0,
                violations=[Violation(
                    gate_id="GATE_0",
                    gate_name="파일 접근성",
                    rule_id="G0_FILE_NOT_FOUND",
                    severity="REJECT",
                    line_number=0,
                    snippet=file_path,
                    message="지정된 파일을 찾을 수 없습니다.",
                    fix_hint="파일 경로가 정확한지 확인하십시오."
                )]
            )

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        platform = platform or platform_override or self.detect_platform(file_path, content)
        fm_text, body, body_start_line = self.split_frontmatter_and_body(content)
        fm_data = self.parse_frontmatter(fm_text)
        lines = content.splitlines()

        violations: List[Violation] = []

        # Gate 1: 구조 및 메타데이터 무결성
        violations.extend(self.verify_gate_1_structure(file_path, content, fm_data, body, platform))

        # Gate 2: AI 클리셰 & 기계적 번역투 박멸
        violations.extend(self.verify_gate_2_anti_ai(lines, platform))

        # Gate 3: 억지 스토리 & 작위적 연출 차단
        violations.extend(self.verify_gate_3_no_forced_drama(lines, platform))

        # Gate 4: 실무 엔지니어링 5대 아티팩트 검증
        violations.extend(self.verify_gate_4_engineering_artifacts(file_path, body, fm_data, platform))

        # Gate 5: 사족 & 중언부언 차단
        violations.extend(self.verify_gate_5_anti_fluff(body, platform))

        # Gate 6: 플랫폼별 특화 규격 (네이버 조판/의료법 및 기어 도안 포맷/실존/치형)
        violations.extend(self.verify_gate_6_platform_compliance(file_path, body, fm_data, lines, platform))

        # Gate 7: 보안 & 시크릿 누출 방벽
        violations.extend(self.verify_gate_7_security(file_path, content, lines))

        # Gate 8: 법적 리스크 & 컴플라이언스 방벽 (자본시장법·금소법, 의료법·건기식법, 공정위 표시광고법, 공공누리 KOGL, 영문 SEC/글로벌 규제)
        violations.extend(self.verify_gate_8_legal_compliance(file_path, content, body, fm_data, lines, platform))

        # Gate 9: 예약 발행 무결성 및 안티봇 지터 방벽 (선별적 예약 감지, 미래 일시 버퍼, 정각 금지)
        violations.extend(self.verify_gate_9_reservation(
            content=content,
            fm_data=fm_data,
            platform=platform,
            is_reserved=is_reserved,
            reserve_date=reserve_date,
            reserve_time=reserve_time,
            reserve_composite=reserve_composite,
            now_dt=now_dt,
            min_buffer_minutes=min_buffer_minutes
        ))

        # Gate 10: 공인 실측 출처 필수 귀속 관문 (Mandatory Real-Time Fact-Check Attribution Gate)
        violations.extend(self.verify_gate_10_fact_check_attribution(file_path, fm_data, body, platform))

        # Gate 11: 도메인별 이론 정합성 및 수치 환각 차단 관문 (Theoretical & Numerical Integrity)
        violations.extend(self.verify_gate_11_theory_and_numerical_integrity(file_path, body, fm_data, lines, platform))

        # Gate 12: 실시간 팩트체크 및 기억 의존 환각 탐지기 (Zero-Memory Hallucination)
        violations.extend(self.verify_gate_12_zero_memory_hallucination(file_path, body, fm_data, lines, platform))

        # Gate 13: 동적 아티팩트 및 구문·규격 정밀 검증기 (Dynamic Syntax & Diff Integrity)
        violations.extend(self.verify_gate_13_dynamic_syntax_and_diff(file_path, body, fm_data, lines, platform))

        # Gate 14: 독립 감사 서브에이전트(Red Team Critic) 검증 관문 (Subagent Audit Gate)
        req_audit = require_subagent_audit or getattr(self, "require_subagent_audit", False)
        violations.extend(self.verify_gate_14_subagent_redteam_audit(file_path, body, fm_data, platform, require_subagent_audit=req_audit))

        # 점수 계산 및 판정
        reject_count = sum(1 for v in violations if v.severity == "REJECT")
        warning_count = sum(1 for v in violations if v.severity == "WARNING")

        score = max(0, 100 - (reject_count * 25) - (warning_count * 5))
        is_passed = (reject_count == 0)

        res_info = getattr(self, "_last_reservation_info", {
            "is_reserved": False,
            "target_dt": None,
            "reserve_date": None,
            "reserve_time": None
        })

        return GateReport(
            file_path=file_path,
            platform=platform,
            is_passed=is_passed,
            score=score,
            reject_count=reject_count,
            warning_count=warning_count,
            violations=violations,
            is_reserved=res_info.get("is_reserved", False),
            reserve_date=res_info.get("reserve_date"),
            reserve_time=res_info.get("reserve_time"),
            target_dt=res_info.get("target_dt")
        )

    # 12대 철벽게이트 전수 정밀 감사 표준 alias
    verify_all_gates = verify


# ==============================================================================
# 📢 리포트 출력 및 하드 블록(Hard Block) 실행 함수
# ==============================================================================
def print_gate_report(report: GateReport, show_hints: bool = True):
    """검증 결과를 터미널에 미려한 ANSI 박스로 출력."""
    status_color = Color.GREEN if report.is_passed else Color.RED
    status_text = "PASSED (발행 승인)" if report.is_passed else "REJECTED (발행 원천 차단)"

    print("\n" + "=" * 80)
    print(f"🛡️  {Color.BOLD}철벽 게이트 검증 보고서 (Ironclad Gatekeeper Report){Color.RESET}")
    print("=" * 80)
    print(f"📄 대상 파일: {Color.CYAN}{report.file_path}{Color.RESET}")
    print(f"🌐 타깃 플랫폼: {Color.YELLOW}{report.platform.upper()}{Color.RESET}")
    print(f"⚖️  최종 판정: {status_color}{Color.BOLD}[{status_text}]{Color.RESET}")
    print(f"📈 품질 점수: {Color.BOLD}{report.score}/100{Color.RESET} (치명적 결함: {Color.RED}{report.reject_count}건{Color.RESET}, 경고: {Color.YELLOW}{report.warning_count}건{Color.RESET})")
    print("-" * 80)

    if not report.violations:
        print(f"{Color.GREEN}✨ 축하합니다! 단 하나의 결함도 발견되지 않은 완전무결한 콘텐츠입니다.{Color.RESET}")
        print("=" * 80 + "\n")
        return

    for idx, v in enumerate(report.violations, start=1):
        sev_color = Color.RED if v.severity == "REJECT" else Color.YELLOW
        line_info = f"Line {v.line_number}" if v.line_number > 0 else "전체/글로벌"
        print(f"\n{sev_color}{Color.BOLD}[{v.severity}] #{idx} {v.gate_id} ({v.gate_name}) - {line_info}{Color.RESET}")
        print(f"  🔍 사유: {v.message}")
        if v.snippet:
            print(f"  📝 원문: {Color.WHITE}\"{v.snippet}\"{Color.RESET}")
        if show_hints and v.fix_hint:
            print(f"  💡 교정 팁: {Color.GREEN}{v.fix_hint}{Color.RESET}")

    print("\n" + "=" * 80)
    if not report.is_passed:
        print(f"{Color.BG_RED}{Color.WHITE}{Color.BOLD} ❌ HARD BLOCK: 품질 기준 미달로 인해 글 발행 파이프라인이 물리적으로 중단됩니다. {Color.RESET}")
        print(f"{Color.RED}위 REJECT 항목을 100% 해소한 후 다시 발행 명령을 실행하십시오.{Color.RESET}")
    else:
        print(f"{Color.GREEN}✅ 검증 통과: 발행 시스템으로 작업을 안전하게 인계합니다.{Color.RESET}")
    print("=" * 80 + "\n")


def verify_or_abort(
    file_path: str,
    platform: Optional[str] = None,
    strict: bool = False,
    show_hints: bool = True,
    is_reserved: Optional[bool] = None,
    reserve_date: Optional[str] = None,
    reserve_time: Optional[str] = None,
    reserve_composite: Optional[str] = None,
    now_dt: Optional[datetime] = None,
    min_buffer_minutes: int = 10
):
    """
    글 발행 시스템(create_post.py, publish_to_dev.py 등) 연동용 함수.
    검증 실패 시 즉각 sys.exit(1)을 호출하여 후속 발행 트랜잭션을 물리적으로 차단함.
    """
    gatekeeper = IroncladGatekeeper(strict_mode=strict)
    report = gatekeeper.verify(
        file_path,
        platform_override=platform,
        is_reserved=is_reserved,
        reserve_date=reserve_date,
        reserve_time=reserve_time,
        reserve_composite=reserve_composite,
        now_dt=now_dt,
        min_buffer_minutes=min_buffer_minutes
    )
    print_gate_report(report, show_hints=show_hints)

    if not report.is_passed:
        sys.exit(1)

    return report


# ==============================================================================
# 🧪 내장 자체 단위 테스트 스위트 (Self-Test Suite)
# ==============================================================================
def run_self_test():
    """다른 에이전트가 본 파일을 복제한 직후 자가 무결성을 검증할 수 있는 테스트 스위트."""
    print("\n🧪 [철벽 게이트 검증 시스템 내장 Self-Test 시작]")
    gatekeeper = IroncladGatekeeper()

    # Case 1: AI 클리셰 포함 케이스 (영문) -> REJECT 기대
    bad_en = """---
title: "Test AI Post"
category: "Cloud & DevOps"
tags: "k8s, dev"
---
In the modern cloud landscape, we must delve into kubernetes issues.
By doing so, the cluster becomes immune to failures.
Here is the exact diagnostic breakdown.
"""
    # 임시 파일 없이 메모리 상 직접 테스트 위해 임시 저장
    temp_dir = Path("scratch")
    temp_dir.mkdir(exist_ok=True)
    temp_bad_en = temp_dir / "_test_bad_en.md"
    temp_bad_en.write_text(bad_en, encoding="utf-8")

    report1 = gatekeeper.verify(str(temp_bad_en), platform_override="dev")
    assert not report1.is_passed, "Case 1: Bad EN AI clichés should be REJECTED"
    assert any(v.rule_id == "G2_AI_CLICHE" for v in report1.violations), "Case 1: Should detect AI cliché"
    print("  ✅ Test 1 Passed: Bad English AI Clichés caught successfully.")

    # Case 2: 억지 스토리 포함 케이스 (국문) -> REJECT 기대
    bad_drama_ko = """---
title: "새벽 장애 일지"
category: "백엔드 & 서버 아키텍처"
tags: "spring"
visibility: "public"
---
새벽 3시 40분, 비상 호출이 울렸다.
등줄기에 식은땀이 흘렀고 머릿속이 하얘졌다.
패닉에 빠진 채로 로그를 보았다.
"""
    temp_bad_drama = temp_dir / "_test_bad_drama.md"
    temp_bad_drama.write_text(bad_drama_ko, encoding="utf-8")

    report2 = gatekeeper.verify(str(temp_bad_drama), platform_override="tistory")
    assert not report2.is_passed, "Case 2: Forced drama should be REJECTED"
    assert any(v.rule_id == "G3_FORCED_DRAMA" for v in report2.violations), "Case 2: Should detect forced drama"
    print("  ✅ Test 2 Passed: Forced Drama Story caught successfully.")

    # Case 3: 네이버 건강 블로그 의료법 위반 단어 -> REJECT 기대
    bad_health_naver = """---
title: "마그네슘 복용법"
category: "건강"
tags: "마그네슘"
---
이 영양제는 불면증 완치와 고혈압 치료에 특효약입니다.
"""
    temp_bad_health = temp_dir / "_test_bad_health.md"
    temp_bad_health.write_text(bad_health_naver, encoding="utf-8")

    report3 = gatekeeper.verify(str(temp_bad_health), platform_override="naver")
    assert not report3.is_passed, "Case 3: Medical claim in health blog should be REJECTED"
    assert any(v.rule_id == "G6_NAVER_MEDICAL_LAW" for v in report3.violations), "Case 3: Medical law violation caught"
    print("  ✅ Test 3 Passed: Naver Medical Law violation caught successfully.")

    # Case 4: 코드 블록 백틱 홀수 (닫히지 않은 코드) -> REJECT 기대
    bad_codeblock = """---
title: "Unclosed Code"
category: "Systems & Networking"
tags: "linux"
---
```bash
echo "Hello"
"""
    temp_bad_code = temp_dir / "_test_bad_code.md"
    temp_bad_code.write_text(bad_codeblock, encoding="utf-8")

    report4 = gatekeeper.verify(str(temp_bad_code), platform_override="dev")
    assert not report4.is_passed, "Case 4: Unclosed code block should be REJECTED"
    assert any(v.rule_id == "G1_UNCLOSED_CODEBLOCK" for v in report4.violations), "Case 4: Unclosed code caught"
    print("  ✅ Test 4 Passed: Unclosed Code Block caught successfully.")

    # Case 5: 보안 시크릿 누출 (AWS Key) -> REJECT 기대
    bad_secret = """---
title: "AWS Credentials Guide"
category: "Cloud & DevOps"
tags: "aws"
---
AWS_KEY = "AKIA1234567890ABCDEF"
"""
    temp_bad_secret = temp_dir / "_test_bad_secret.md"
    temp_bad_secret.write_text(bad_secret, encoding="utf-8")

    report5 = gatekeeper.verify(str(temp_bad_secret), platform_override="dev")
    assert not report5.is_passed, "Case 5: Security secret leak should be REJECTED"
    assert any(v.gate_id == "GATE_7" for v in report5.violations), "Case 5: Gate 7 secret leak caught"
    print("  ✅ Test 5 Passed: Security & Secrets leak caught successfully.")

    # Case 6: 자본시장법 & 금소법 위반 (원금보장, 확정수익, 리딩방) -> REJECT 기대
    # (동일 라인에 면책문구를 혼합 삽입한 지능형 우회 시도 차단 검증 포함)
    bad_finance = """---
title: "특급 급등주 추천 및 확정 수익 비법"
category: "금융 & 재테크"
tags: "주식, 재테크"
---
이번에 발굴한 세력 매집주는 무조건 폭등하며 원금 보장과 함께 연 30% 확정 수익을 약속합니다. 투자의 최종 책임은 본인에게 있습니다.
VIP 리딩방에서만 제공하는 극비 정보주이므로 지금 당장 풀매수하세요.
"""
    temp_bad_fin = temp_dir / "_test_bad_fin.md"
    temp_bad_fin.write_text(bad_finance, encoding="utf-8")

    report6 = gatekeeper.verify(str(temp_bad_fin), platform_override="tistory")
    assert not report6.is_passed, "Case 6: Capital Markets & Consumer Protection violations should be REJECTED"
    assert any("G8_FIN_" in v.rule_id for v in report6.violations), "Case 6: Should detect Capital Markets & Consumer Protection violations"
    assert any(v.rule_id == "G8_FIN_PRINCIPAL_GUARANTEE" for v in report6.violations), "Case 6: Should detect principal guarantee even with disclaimer on same line"
    assert any(v.rule_id == "G8_FIN_CONFIRMED_PROFIT" for v in report6.violations), "Case 6: Should detect confirmed profit"
    print("  ✅ Test 6 Passed: Capital Markets & Financial Consumer Protection Law violations caught successfully.")

    # Case 7: 의료법 & 건강기능식품법 위반 (의약품 오인, 처방약 중단, 의료인 사칭) -> REJECT 기대
    # (동일 라인에 '의약품이 아닙니다' 면책 어구를 혼합한 우회 시도 차단 검증 포함)
    bad_medical = """---
title: "기적의 천연 치료제로 당뇨 잡는 법"
category: "건강"
tags: "당뇨, 영양제"
---
현직 의사로서 보증하건대, 이 성분은 인슐린 약 대신 복용할 수 있는 기적의 천연 치료제입니다. 본 제품은 질병 치료를 목적으로 하지 않으며 의약품이 아닙니다.
기존 병원 처방약을 끊고 이 건강기능식품만 섭취하면 체지방 100% 분해와 함께 완치됩니다.
"""
    temp_bad_med = temp_dir / "_test_bad_med.md"
    temp_bad_med.write_text(bad_medical, encoding="utf-8")

    report7 = gatekeeper.verify(str(temp_bad_med), platform_override="naver")
    assert not report7.is_passed, "Case 7: Medical law & drug confusion claims should be REJECTED"
    assert any("G8_MED_" in v.rule_id for v in report7.violations), "Case 7: Should detect medical law violations"
    assert any(v.rule_id == "G8_MED_NATURAL_MEDICINE" for v in report7.violations), "Case 7: Should detect natural medicine claim"
    assert any(v.rule_id == "G8_MED_STOP_PRESCRIPTION" for v in report7.violations), "Case 7: Should detect stopping prescription"
    assert any(v.rule_id == "G8_MED_IMPERSONATION_PROFESSIONAL" for v in report7.violations), "Case 7: Should detect medical impersonation"
    print("  ✅ Test 7 Passed: Medical Law & Health Functional Food Law violations caught successfully.")

    # Case 8: 공정거래위원회 추천·보증 심사지침 위반 (제휴 링크 있으나 대가성 고지 누락 및 기만적 스텔스 마케팅) -> REJECT 기대
    # (제휴 링크가 상단에 있고 내돈내산이 하단에 배치된 역순 기만 광고 차단 검증 포함)
    bad_ftc = """---
title: "내돈내산 무선 마우스 솔직 후기"
category: "IT / 소프트웨어 리뷰"
tags: "마우스, IT리뷰"
---
# 가성비 최고 무선 마우스 사용기

제품 구매 링크: https://link.coupang.com/a/bCdEf1234
쿠팡 파트너스 추천 상품으로 적극 권장합니다.
직접 구매해서 3달간 써본 솔직한 내돈내산 후기입니다. 광고 아닙니다.
"""
    temp_bad_ftc = temp_dir / "_test_bad_ftc.md"
    temp_bad_ftc.write_text(bad_ftc, encoding="utf-8")

    report8 = gatekeeper.verify(str(temp_bad_ftc), platform_override="tistory")
    assert not report8.is_passed, "Case 8: Missing FTC disclosure and covert ad should be REJECTED"
    assert any(v.rule_id == "G8_FTC_MISSING_DISCLOSURE" for v in report8.violations), "Case 8: Should detect missing FTC disclosure"
    assert any(v.rule_id == "G8_FTC_COVERT_MY_MONEY" for v in report8.violations), "Case 8: Should detect deceptive covert marketing"
    print("  ✅ Test 8 Passed: FTC Affiliate & Sponsored Advertising compliance caught successfully.")

    # Case 9: 공공누리(KOGL) 저작권 출처 표기 누락 (정부 지원금/정책 글에서 출처 미표기) -> REJECT 기대
    bad_kogl = """---
title: "2026 청년도약계좌 지원 조건 및 신청 방법 총정리"
category: "정부 정책 / 복지 지원금"
tags: "청년도약계좌, 정부지원금"
---
# 2026 청년도약계좌 완벽 가이드

보건복지부와 서민금융진흥원에서 발표한 2026년 청년도약계좌 정부 지원금 정책 안내입니다.
정부 지원금 매칭 혜택과 비과세 혜택을 통해 5천만 원의 목돈을 마련할 수 있습니다.
신청 자격은 만 19세~34세 청년이며 총급여 7,500만 원 이하입니다.
"""
    temp_bad_kogl = temp_dir / "_test_bad_kogl.md"
    temp_bad_kogl.write_text(bad_kogl, encoding="utf-8")

    report9 = gatekeeper.verify(str(temp_bad_kogl), platform_override="naver")
    assert not report9.is_passed, "Case 9: Missing KOGL attribution should be REJECTED"
    assert any(v.rule_id == "G8_KOGL_MISSING_ATTRIBUTION" for v in report9.violations), "Case 9: Should detect missing KOGL attribution"
    print("  ✅ Test 9 Passed: KOGL Public Copyright attribution requirement verified successfully.")

    # Case 10: 영문 글로벌 금융 규제 위반 (SEC Investment Advice & Guaranteed Return) -> REJECT 기대
    bad_sec = """---
title: "Guaranteed Profit Trading Strategy"
category: "Global Macro & Finance"
tags: "trading, stocks"
---
# S&P 500 High-Frequency Strategy

This quantitative model delivers a guaranteed return of 45% with risk-free profit.
Buy this stock now before market close today. It has a 100% win rate and cannot lose money.
"""
    temp_bad_sec = temp_dir / "_test_bad_sec.md"
    temp_bad_sec.write_text(bad_sec, encoding="utf-8")

    report10 = gatekeeper.verify(str(temp_bad_sec), platform_override="markets")
    assert not report10.is_passed, "Case 10: Global financial/SEC violations should be REJECTED"
    assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in report10.violations), "Case 10: Should detect guaranteed returns"
    assert any(v.rule_id == "G8_GLOBAL_URGENT_BUY_CALL" for v in report10.violations), "Case 10: Should detect direct buy command"
    assert any(v.rule_id == "G8_GLOBAL_MISSING_DISCLAIMER" for v in report10.violations), "Case 10: Should detect missing global financial disclaimer"

    # 동일 라인에 면책문구를 혼합 삽입한 우회 시도 차단 추가 검증
    sec_evasion_text = "This quantitative system delivers a guaranteed profit of 45%. This is for informational purposes only and not financial advice."
    sec_evasion_lines = [sec_evasion_text]
    sec_evasion_v = gatekeeper.verify_gate_8_legal_compliance(
        file_path="test_sec_evasion.md",
        content=sec_evasion_text,
        body=sec_evasion_text,
        fm_data={"category": "Finance", "title": "Trading"},
        lines=sec_evasion_lines,
        platform="markets"
    )
    assert any(v.rule_id == "G8_GLOBAL_GUARANTEED_RETURNS" for v in sec_evasion_v), "Case 10-2: Guaranteed profit must be caught even with disclaimer on same line"
    print("  ✅ Test 10 Passed: English SEC & Global Financial compliance violations caught successfully.")

    # Case 11: 법적 규정 100% 준수한 정상 콘텐츠 통과 검증 (Clean Compliant Post) -> PASS 기대
    # 1. KOGL 정책 공공 저작물 정상 포스트
    compliant_policy = """---
title: "2026 청년 자산 형성 정책 분석 가이드"
category: "정부 정책 / 복지 지원금"
tags: "청년도약계좌, 정책금융"
---
# 2026 청년 자산 형성 지원 정책 분석

본 포스팅은 대한민국 정부의 청년 금융 지원 복지 정책 구조를 객관적으로 분석합니다.
소득 구간별 정부기여금 매칭과 우대 금리 요건을 꼼꼼히 확인하여 자산 형성 계획을 수립해야 합니다.

신청 전 서민금융진흥원 및 취급 시중은행의 공식 공고를 확인하시기 바랍니다.

---
출처: 대한민국 정책브리핑 (공공누리 제1유형: 출처표시)

※ 본 글은 금융 지원 정책 이해를 돕기 위한 객관적 정보 제공용이며, 특정 금융회사나 금융투자상품 가입을 권유하지 않습니다.
"""
    cp_fm_text, cp_body, _ = gatekeeper.split_frontmatter_and_body(compliant_policy)
    cp_fm = gatekeeper.parse_frontmatter(cp_fm_text)
    cp_v = gatekeeper.verify_gate_8_legal_compliance(
        file_path="posts/test_compliant_policy.md",
        content=compliant_policy,
        body=cp_body,
        fm_data=cp_fm,
        lines=compliant_policy.splitlines(),
        platform="naver"
    )
    assert len(cp_v) == 0, f"Case 11-1: Compliant policy post should have 0 Gate 8 legal violations, found: {cp_v}"

    # 2. 식약처 고시 건기식 표준 면책문구 포스트
    compliant_health = """---
title: "마그네슘 흡수율 비교 분석"
category: "건강"
tags: "마그네슘"
---
# 마그네슘 형태별 생체이용률 과학

식약처 고시 기준에 따른 마그네슘 형태별 체내 흡수 메커니즘을 객관적으로 분석합니다.
킬레이트 마그네슘과 산화 마그네슘의 용해도 차이를 인체적용시험 데이터로 비교합니다.

---
※ 본 제품은 질병의 예방 및 치료를 위한 의약품이 아니며, 건강 증진을 위한 건강기능식품 정보입니다. 전문 의료인의 진단 및 처방을 대신할 수 없습니다.
"""
    ch_fm_text, ch_body, _ = gatekeeper.split_frontmatter_and_body(compliant_health)
    ch_fm = gatekeeper.parse_frontmatter(ch_fm_text)
    ch_v = gatekeeper.verify_gate_8_legal_compliance(
        file_path="posts/test_compliant_health.md",
        content=compliant_health,
        body=ch_body,
        fm_data=ch_fm,
        lines=compliant_health.splitlines(),
        platform="naver"
    )
    assert len(ch_v) == 0, f"Case 11-2: Compliant health post should have 0 Gate 8 legal violations, found: {ch_v}"

    # 3. 글로벌 영문 제휴 링크 & FTC 면책고지 준수 포스트
    compliant_ftc_en = """---
title: "Top Developer Keyboards"
category: "Cloud & DevOps"
tags: "hardware, dev"
---
# Essential Hardware for Engineers

A detailed review of ergonomic mechanical keyboards for infrastructure engineers.
Product link: https://amzn.to/3xyz123

Disclosure: This post contains affiliate links. As an Amazon Associate I earn from qualifying purchases at no additional cost to you.
"""
    ce_fm_text, ce_body, _ = gatekeeper.split_frontmatter_and_body(compliant_ftc_en)
    ce_fm = gatekeeper.parse_frontmatter(ce_fm_text)
    ce_v = gatekeeper.verify_gate_8_legal_compliance(
        file_path="blogs/dev/_posts/test_compliant_ftc.md",
        content=compliant_ftc_en,
        body=ce_body,
        fm_data=ce_fm,
        lines=compliant_ftc_en.splitlines(),
        platform="dev"
    )
    assert len(ce_v) == 0, f"Case 11-3: Compliant English affiliate post should have 0 Gate 8 legal violations, found: {ce_v}"

    # 4. 개발 블로그의 Portfolio Dashboard 튜토리얼 (금융 글 오탐 방지 검증)
    compliant_dev_portfolio = """---
title: "Building a Portfolio Dashboard with FastAPI"
category: "Cloud & DevOps"
tags: "fastapi, python"
---
# Building a Portfolio Dashboard

In this engineering tutorial, we implement an asynchronous worker pipeline to aggregate user metrics with FastAPI and Redis.
We deploy the containerized cluster across multiple availability zones.
"""
    cd_fm_text, cd_body, _ = gatekeeper.split_frontmatter_and_body(compliant_dev_portfolio)
    cd_fm = gatekeeper.parse_frontmatter(cd_fm_text)
    cd_v = gatekeeper.verify_gate_8_legal_compliance(
        file_path="blogs/dev/_posts/test_portfolio.md",
        content=compliant_dev_portfolio,
        body=cd_body,
        fm_data=cd_fm,
        lines=compliant_dev_portfolio.splitlines(),
        platform="dev"
    )
    assert len(cd_v) == 0, f"Case 11-4: Dev coding tutorial with 'portfolio' should have 0 Gate 8 legal violations, found: {cd_v}"

    print("  ✅ Test 11 Passed: Fully compliant legal & regulatory content verified across all domains with 0 violations.")

    # Case 12: KaTeX 파싱 에러 유발 멀티라인 수식 블록 -> REJECT 기대
    bad_math_katex = """---
title: "수식 파싱 테스트"
category: "기어 공학"
tags: "gear, math"
---
# 전위 기어 수식 검증

수식 블록 내에서 줄바꿈이 잘못되어 파서가 터지는 케이스:

$$d_{a1} = m(z_1 + 2 + 2x_1 - 2k), \\quad d_{a2} = m(z_2 + 2 + 2x_2 - 2k)
d_{f1} = m(z_1 - 2.5 + 2x_1), \\quad d_{f2} = m(z_2 - 2.5 + 2x_2)$$

본문 텍스트가 계속 이어집니다. 공백 제외 1200자 이상 충족을 위해 긴 텍스트를 기술합니다.
우리는 기계공학 현장에서 전위 기어의 물림률과 치형 밸런싱을 엄밀하게 해석해야 합니다.
인볼류트 치형 곡선의 기초원과 피치원의 관계를 명확히 정립하고,
운전 압력각과 이끝원 지름, 이뿌리원 지름을 정확하게 계산하여 조립 간섭을 방지해야 합니다.
""" * 10
    temp_bad_math = temp_dir / "_test_bad_math.md"
    temp_bad_math.write_text(bad_math_katex, encoding="utf-8")
    report12 = gatekeeper.verify(str(temp_bad_math), platform_override="tistory")
    assert not report12.is_passed, "Case 12: KaTeX multiline error without \\\\ should be REJECTED"
    assert any(v.rule_id == "G1_KATEX_MULTILINE_SYNTAX" for v in report12.violations), "Case 12: Should detect G1_KATEX_MULTILINE_SYNTAX"
    print("  ✅ Test 12 Passed: KaTeX multiline parse-error syntax caught successfully.")

    # 기준 테스트 시각 (2026-11-20 15:00:00)
    fixed_now = datetime(2026, 11, 20, 15, 0, 0)

    # Case 13: 예약 일시가 과거인 경우 -> REJECT 기대 (G9_RESERVATION_PAST_TIME)
    bad_res_past = """---
title: "과거 예약 테스트 포스트"
category: "컴퓨터 과학 핵심 기초"
tags: "cs, test"
visibility: public
publish_type: scheduled
reserve_at: "2026-11-19 14:24"
---
# 과거 예약 테스트
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
""" * 20
    temp_res_past = temp_dir / "_test_res_past.md"
    temp_res_past.write_text(bad_res_past, encoding="utf-8")
    rep13 = gatekeeper.verify(str(temp_res_past), platform_override="tistory", now_dt=fixed_now)
    assert not rep13.is_passed, "Case 13: Past reservation time should be REJECTED"
    assert any(v.rule_id == "G9_RESERVATION_PAST_TIME" for v in rep13.violations), "Case 13: Should catch G9_RESERVATION_PAST_TIME"
    print("  ✅ Test 13 Passed: Past reservation time caught and rejected successfully.")

    # Case 14: 최소 버퍼 미달 (현재 시각 기준 5분 뒤) -> REJECT 기대 (G9_RESERVATION_BUFFER_UNDERFLOW)
    bad_res_buf = """---
title: "버퍼 미달 예약 테스트"
category: "컴퓨터 과학 핵심 기초"
tags: "cs, test"
visibility: public
publish_type: scheduled
reserve_at: "2026-11-20 15:05"
---
# 버퍼 미달 예약 테스트
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
""" * 20
    temp_res_buf = temp_dir / "_test_res_buf.md"
    temp_res_buf.write_text(bad_res_buf, encoding="utf-8")
    rep14 = gatekeeper.verify(str(temp_res_buf), platform_override="tistory", now_dt=fixed_now)
    assert not rep14.is_passed, "Case 14: Buffer under 10m should be REJECTED"
    assert any(v.rule_id == "G9_RESERVATION_BUFFER_UNDERFLOW" for v in rep14.violations), "Case 14: Should catch G9_RESERVATION_BUFFER_UNDERFLOW"
    print("  ✅ Test 14 Passed: Reservation buffer underflow (<10m) caught and rejected successfully.")

    # Case 15: 안티봇 00분 정각 충돌 (18:00) -> REJECT 기대 (G9_RESERVATION_BOT_COLLISION_MINUTE)
    bad_res_min = """---
title: "정각 00분 충돌 테스트"
category: "컴퓨터 과학 핵심 기초"
tags: "cs, test"
visibility: public
publish_type: scheduled
reserve_at: "2026-11-21 18:00"
---
# 정각 00분 충돌 테스트
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
""" * 20
    temp_res_min = temp_dir / "_test_res_min.md"
    temp_res_min.write_text(bad_res_min, encoding="utf-8")
    rep15 = gatekeeper.verify(str(temp_res_min), platform_override="tistory", now_dt=fixed_now)
    assert not rep15.is_passed, "Case 15: 00-minute collision should be REJECTED"
    assert any(v.rule_id == "G9_RESERVATION_BOT_COLLISION_MINUTE" for v in rep15.violations), "Case 15: Should catch G9_RESERVATION_BOT_COLLISION_MINUTE"
    print("  ✅ Test 15 Passed: Anti-bot 00-minute collision caught and rejected successfully.")

    # Case 16: 개발 블로그 안티봇 00초 정각 충돌 (10:48:00) -> REJECT 기대 (G9_RESERVATION_BOT_COLLISION_SECOND)
    bad_res_sec = """---
title: "Fixing Container Network Interfaces: CNI Pod Lifecycle Failures"
category: "Cloud & DevOps"
tags: [kubernetes, devops, network]
date: 2026-11-21 10:48:00 +0900
publish_type: scheduled
---
In production clusters, we observed severe pod eviction due to interface configuration.
Here is the raw error log from the node daemonset:
```text
level=error msg="failed to setup network for sandbox: CNI plugin failed" error="ipam: no IP addresses available"
```
Wrong fix attempt:
We initially increased the IPAM pool CIDR range blindly, but this naive fix failed because the secondary ENI attachments were leaking orphaned interfaces.
Unified diff of the fix:
```diff
--- a/cni-daemon.yaml
+++ b/cni-daemon.yaml
-      - name: WARM_ENI_TARGET
-        value: "1"
+      - name: WARM_ENI_TARGET
+        value: "4"
```
Root cause analysis:
The underlying CNI ipam daemon was failing to reclaim freed pod interfaces during rapid rolling restart cycles.
Verification CLI:
```bash
kubectl get nodes -o wide
curl -v http://localhost:8080/healthz
```
""" * 5
    temp_res_sec = temp_dir / "_test_res_sec.md"
    temp_res_sec.write_text(bad_res_sec, encoding="utf-8")
    rep16 = gatekeeper.verify(str(temp_res_sec), platform_override="dev", now_dt=fixed_now)
    assert not rep16.is_passed, "Case 16: 00-seconds collision should be REJECTED"
    assert any(v.rule_id == "G9_RESERVATION_BOT_COLLISION_SECOND" for v in rep16.violations), "Case 16: Should catch G9_RESERVATION_BOT_COLLISION_SECOND"
    print("  ✅ Test 16 Passed: Anti-bot 00-seconds collision caught and rejected successfully.")

    # Case 17: 정상 지터 예약 포스트 통과 검증 (2026-11-21 18:42, 42분) -> Gate 9 통과 기대
    good_res = """---
title: "정상 예약 포스트"
category: "컴퓨터 과학 핵심 기초"
tags: "cs, test"
visibility: public
publish_type: scheduled
reserve_at: "2026-11-21 18:42"
---
# 정상 예약 포스트
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
""" * 20
    temp_good_res = temp_dir / "_test_good_res.md"
    temp_good_res.write_text(good_res, encoding="utf-8")
    rep17 = gatekeeper.verify(str(temp_good_res), platform_override="tistory", now_dt=fixed_now)
    g9_viols_17 = [v for v in rep17.violations if v.gate_id == "GATE_9"]
    assert len(g9_viols_17) == 0, f"Case 17: Valid reservation should have 0 Gate 9 violations, found: {g9_viols_17}"
    print("  ✅ Test 17 Passed: Valid jittered reservation time verified with 0 Gate 9 violations.")

    # Case 18: 일반 즉시공개 포스트 선별 검증 (예약 메타데이터 부재) -> Gate 9 안전한 스킵 검증
    immediate_post = """---
title: "일반 즉시공개 포스트"
category: "컴퓨터 과학 핵심 기초"
tags: "cs, test"
visibility: public
---
# 일반 즉시공개 포스트
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
""" * 20
    temp_immediate = temp_dir / "_test_immediate.md"
    temp_immediate.write_text(immediate_post, encoding="utf-8")
    rep18 = gatekeeper.verify(str(temp_immediate), platform_override="tistory", now_dt=fixed_now)
    g9_viols_18 = [v for v in rep18.violations if v.gate_id == "GATE_9"]
    assert len(g9_viols_18) == 0, f"Case 18: Immediate post should have 0 Gate 9 violations, found: {g9_viols_18}"
    print("  ✅ Test 18 Passed: Immediate post safely skips reservation check with 0 Gate 9 violations.")

    # Case 19: 기어 블로그 도안 이미지 확장자 검증 (비정규 .jpg 확장자) -> REJECT 기대
    bad_gear_img = """---
title: "기어 도안 테스트"
category: "기어 공학"
tags: "gear, cad"
---
# 기어 도안 규격 검증
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
![치형 도안](/images/mesh_profile.jpg)
""" * 20
    temp_gear_img = temp_dir / "_test_gear_img.md"
    temp_gear_img.write_text(bad_gear_img, encoding="utf-8")
    rep19 = gatekeeper.verify(str(temp_gear_img), platform_override="gear")
    assert not rep19.is_passed, "Case 19: Non-standard gear diagram ext (.jpg) should be REJECTED"
    assert any(v.rule_id == "G6_GEAR_INVALID_IMAGE_EXT" for v in rep19.violations), "Case 19: Should catch G6_GEAR_INVALID_IMAGE_EXT"
    print("  ✅ Test 19 Passed: Gear diagram invalid image format caught and rejected successfully.")

    # Case 20: 네이버 블로그 인라인 마크다운 이미지 삽입 금지 및 육안 검수 링크 강제 규격 -> REJECT 기대
    bad_naver_img = """---
title: "네이버 이미지 조판 테스트"
category: "IT / 소프트웨어 리뷰"
tags: "naver, it"
---
# 네이버 본문 이미지 조판 검증
본문 내용이 충분히 길게 들어갑니다. 기술적 본질을 다루는 충실한 아티클 본문으로 분량 요건을 충족합니다.
![테스트 이미지](file:///D:/images/screen.png)

#태그1 #태그2 #태그3
""" * 10
    temp_naver_img = temp_dir / "_test_naver_img.md"
    temp_naver_img.write_text(bad_naver_img, encoding="utf-8")
    rep20 = gatekeeper.verify(str(temp_naver_img), platform_override="naver")
    assert not rep20.is_passed, "Case 20: Naver inline markdown image should be REJECTED"
    assert any(v.rule_id == "G6_NAVER_INLINE_IMAGE_FORBIDDEN" for v in rep20.violations), "Case 20: Should catch G6_NAVER_INLINE_IMAGE_FORBIDDEN"
    print("  ✅ Test 20 Passed: Naver inline markdown image forbidden (visual inspection link mandate) verified successfully.")

    # Case 21: Gate 10 Frontmatter fact_check_sources 누락 -> REJECT 기대 (G10_MISSING_FM_SOURCES)
    bad_g10_sources = """---
title: "최신 커널 튜닝 가이드"
category: "Cloud & DevOps"
tags: ["linux", "kernel"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 리눅스 네트워크 성능 튜닝
본문 내용이 충분히 길게 기술됩니다.
[출처: https://docs.kernel.org]
""" * 10
    temp_g10_sources = temp_dir / "_test_g10_sources.md"
    temp_g10_sources.write_text(bad_g10_sources, encoding="utf-8")
    rep21 = gatekeeper.verify(str(temp_g10_sources), platform_override="dev")
    assert not rep21.is_passed, "Case 21: Missing fact_check_sources should be REJECTED"
    assert any(v.rule_id == "G10_MISSING_FM_SOURCES" for v in rep21.violations), "Case 21: Should catch G10_MISSING_FM_SOURCES"
    print("  ✅ Test 21 Passed: Missing fact_check_sources caught and rejected successfully.")

    # Case 22: Gate 10 Frontmatter verification_date 누락 -> REJECT 기대 (G10_MISSING_FM_VERIFICATION_DATE)
    bad_g10_date = """---
title: "최신 커널 튜닝 가이드"
category: "Cloud & DevOps"
tags: ["linux", "kernel"]
fact_check_sources: ["https://docs.kernel.org"]
---
# 리눅스 네트워크 성능 튜닝
본문 내용이 충분히 길게 기술됩니다.
[출처: https://docs.kernel.org]
""" * 10
    temp_g10_date = temp_dir / "_test_g10_date.md"
    temp_g10_date.write_text(bad_g10_date, encoding="utf-8")
    rep22 = gatekeeper.verify(str(temp_g10_date), platform_override="dev")
    assert not rep22.is_passed, "Case 22: Missing verification_date should be REJECTED"
    assert any(v.rule_id == "G10_MISSING_FM_VERIFICATION_DATE" for v in rep22.violations), "Case 22: Should catch G10_MISSING_FM_VERIFICATION_DATE"
    print("  ✅ Test 22 Passed: Missing verification_date caught and rejected successfully.")

    # Case 23: Gate 10 본문 내 출처 귀속 인용 누락 -> REJECT 기대 (G10_MISSING_BODY_ATTRIBUTION)
    bad_g10_body = """---
title: "최신 커널 튜닝 가이드"
category: "Cloud & DevOps"
tags: ["linux", "kernel"]
fact_check_sources: ["https://docs.kernel.org"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 리눅스 네트워크 성능 튜닝
본문 내용이 충분히 길게 기술되지만 본문에 출처 인용 태그가 전혀 없는 상태입니다.
네트워크 패킷 버퍼링 메커니즘을 엄밀히 분석합니다.
""" * 10
    temp_g10_body = temp_dir / "_test_g10_body.md"
    temp_g10_body.write_text(bad_g10_body, encoding="utf-8")
    rep23 = gatekeeper.verify(str(temp_g10_body), platform_override="dev")
    assert not rep23.is_passed, "Case 23: Missing in-body attribution should be REJECTED"
    assert any(v.rule_id == "G10_MISSING_BODY_ATTRIBUTION" for v in rep23.violations), "Case 23: Should catch G10_MISSING_BODY_ATTRIBUTION"
    print("  ✅ Test 23 Passed: Missing in-body source attribution caught and rejected successfully.")

    # Case 24: Gate 11 복지 기준 중위소득 과거 수치 왜곡 (540만원) -> REJECT 기대 (G11_WELFARE_OUTDATED_MEDIAN_INCOME)
    bad_g11_welfare = """---
title: "2026 복지 지원금 가이드"
category: "정부 정책 / 복지 지원금"
tags: ["복지", "지원금"]
fact_check_sources: ["https://www.bokjiro.go.kr"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 2026 지원 정책
2026년 기준 중위소득 540만 원 이하 가구에 지원금을 지급합니다.
[출처: 복지로 공고]
""" * 10
    temp_g11_welfare = temp_dir / "_test_g11_welfare.md"
    temp_g11_welfare.write_text(bad_g11_welfare, encoding="utf-8")
    rep24 = gatekeeper.verify(str(temp_g11_welfare), platform_override="naver")
    assert not rep24.is_passed, "Case 24: Outdated median income should be REJECTED"
    assert any(v.rule_id == "G11_WELFARE_OUTDATED_MEDIAN_INCOME" for v in rep24.violations), "Case 24: Should catch G11_WELFARE_OUTDATED_MEDIAN_INCOME"
    print("  ✅ Test 24 Passed: Outdated welfare median income caught and rejected successfully.")

    # Case 25: Gate 11 건기식 오메가3 분자구조 왜곡 (EE형이 글리세롤 뼈대 결합 주장) -> REJECT 기대 (G11_HEALTH_FALSE_EE_STRUCTURE)
    bad_g11_health = """---
title: "오메가3 분자구조 분석"
category: "건강"
tags: ["오메가3"]
fact_check_sources: ["식품의약품안전처 고시 제2026-12호"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 오메가3 분자구조
EE형은 글리세롤 뼈대에 지방산이 1개 결합된 형태입니다.
[출처: 식약처 건강기능식품 데이터베이스]
※ 본 제품은 질병의 예방 및 치료를 위한 의약품이 아닙니다.
""" * 10
    temp_g11_health = temp_dir / "_test_g11_health.md"
    temp_g11_health.write_text(bad_g11_health, encoding="utf-8")
    rep25 = gatekeeper.verify(str(temp_g11_health), platform_override="naver")
    assert not rep25.is_passed, "Case 25: False EE molecular structure should be REJECTED"
    assert any(v.rule_id == "G11_HEALTH_FALSE_EE_STRUCTURE" for v in rep25.violations), "Case 25: Should catch G11_HEALTH_FALSE_EE_STRUCTURE"
    print("  ✅ Test 25 Passed: False omega-3 EE molecular structure caught and rejected successfully.")

    # Case 26: Gate 11 제거된 리눅스 커널 sysctl 파라미터 (net.ipv4.tcp_tw_recycle) -> REJECT 기대 (G11_TECH_REMOVED_SYSCTL_TW_RECYCLE)
    bad_g11_tech = """---
title: "TCP 성능 최적화 sysctl 세팅"
category: "Cloud & DevOps"
tags: ["linux", "tcp"]
fact_check_sources: ["https://docs.kernel.org"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 커널 파라미터 튜닝
성능 향상을 위해 net.ipv4.tcp_tw_recycle = 1 옵션을 활성화합니다.
[출처: Linux Kernel Documentation]
""" * 10
    temp_g11_tech = temp_dir / "_test_g11_tech.md"
    temp_g11_tech.write_text(bad_g11_tech, encoding="utf-8")
    rep26 = gatekeeper.verify(str(temp_g11_tech), platform_override="dev")
    assert not rep26.is_passed, "Case 26: Removed tcp_tw_recycle should be REJECTED"
    assert any(v.rule_id == "G11_TECH_REMOVED_SYSCTL_TW_RECYCLE" for v in rep26.violations), "Case 26: Should catch G11_TECH_REMOVED_SYSCTL_TW_RECYCLE"
    print("  ✅ Test 26 Passed: Removed sysctl tcp_tw_recycle caught and rejected successfully.")

    # Case 27: Gate 11 연준 순유동성 공식 오류 (TGA 가산 오류) -> REJECT 기대 (G11_STOCK_FED_LIQUIDITY_ADD_TGA)
    bad_g11_stock = """---
title: "연준 순유동성 지표 분석"
category: "Global Macro & Finance"
tags: ["fed", "liquidity"]
fact_check_sources: ["https://www.federalreserve.gov/monetarypolicy/bst_fedsbalancesheet.htm"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 연준 순유동성 계산
미국 증시 유동성을 파악할 때 연준 순유동성은 총자산 + TGA 공식으로 계산합니다.
[출처: Federal Reserve H.4.1 Release]
This is for informational purposes only and not financial advice.
""" * 10
    temp_g11_stock = temp_dir / "_test_g11_stock.md"
    temp_g11_stock.write_text(bad_g11_stock, encoding="utf-8")
    rep27 = gatekeeper.verify(str(temp_g11_stock), platform_override="markets")
    assert not rep27.is_passed, "Case 27: Fed liquidity add TGA should be REJECTED"
    assert any(v.rule_id == "G11_STOCK_FED_LIQUIDITY_ADD_TGA" for v in rep27.violations), "Case 27: Should catch G11_STOCK_FED_LIQUIDITY_ADD_TGA"
    print("  ✅ Test 27 Passed: Fed liquidity add TGA formula error caught and rejected successfully.")

    # Case 28: Gate 12 기준 연도 없는 모호한 시점 지시어 ("최근 몇 년간") -> REJECT 기대 (G12_VAGUE_TEMPORAL_MARKER)
    bad_g12_vague = """---
title: "클라우드 네이티브 발전사"
category: "Cloud & DevOps"
tags: ["cloud"]
fact_check_sources: ["https://docs.kernel.org"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# 아키텍처 동향
최근 몇 년간 쿠버네티스 도입이 급격히 증가하고 있습니다.
[출처: CNCF Annual Survey]
""" * 10
    temp_g12_vague = temp_dir / "_test_g12_vague.md"
    temp_g12_vague.write_text(bad_g12_vague, encoding="utf-8")
    rep28 = gatekeeper.verify(str(temp_g12_vague), platform_override="dev")
    assert not rep28.is_passed, "Case 28: Vague temporal marker without year should be REJECTED"
    assert any(v.rule_id == "G12_VAGUE_TEMPORAL_MARKER" for v in rep28.violations), "Case 28: Should catch G12_VAGUE_TEMPORAL_MARKER"
    print("  ✅ Test 28 Passed: Vague temporal marker without baseline anchor caught and rejected successfully.")

    # Case 29: Gate 12 존재하지 않는 조작된 CLI 플래그 (git push --instant) -> REJECT 기대 (G12_FABRICATED_API_OR_FLAG)
    bad_g12_api = """---
title: "Git 고급 실무 명령어"
category: "컴퓨터 과학 핵심 기초"
tags: ["git"]
visibility: public
fact_check_sources: ["https://git-scm.com/docs"]
verification_date: "2026-11-22"
subagent_audit: "verified"
---
# Git 빠른 푸시
긴급 배포 시 git push --instant 명령어를 사용하면 즉시 반영됩니다.
[출처: Git Official Documentation]
""" * 10
    temp_g12_api = temp_dir / "_test_g12_api.md"
    temp_g12_api.write_text(bad_g12_api, encoding="utf-8")
    rep29 = gatekeeper.verify(str(temp_g12_api), platform_override="tistory")
    assert not rep29.is_passed, "Case 29: Fabricated CLI flag should be REJECTED"
    assert any(v.rule_id == "G12_FABRICATED_API_OR_FLAG" for v in rep29.violations), "Case 29: Should catch G12_FABRICATED_API_OR_FLAG"
    print("  ✅ Test 29 Passed: Fabricated CLI flag/API caught and rejected successfully.")

    # Case 30: 12대 철벽 게이트를 100% 무결하게 준수한 완전무결 포스트 -> PASS 기대 (score 100, reject_count 0)
    good_compliant_12 = """---
title: "리눅스 네트워크 스택 커널 소프트IRQ 처리 메커니즘 분석"
category: "컴퓨터 과학 핵심 기초"
tags: ["linux", "kernel", "network"]
visibility: public
fact_check_sources:
  - "https://docs.kernel.org/networking/napi.html"
  - "RFC 9110"
verification_date: "2026-11-22"
subagent_audit: "verified"
---

# 리눅스 네트워크 스택 커널 소프트IRQ 처리 메커니즘

2026년 현재 기준 고성능 분산 네트워크 인프라에서 대규모 패킷 인그레스가 발생할 때 리눅스 커널의 인터럽트 처리 흐름을 정밀하게 분석합니다. 시스템 엔지니어는 대규모 트래픽 유입 시 발생하는 CPU 스파이크의 물리적 원인을 파악하고 운영 안정성을 확보해야 합니다.

## 1. 하드웨어 인터럽트와 소프트IRQ의 디커플링 구조

네트워크 인터페이스 카드(NIC)로 패킷이 수신되면 하드웨어 인터럽트(Top-Half)가 발생하여 CPU를 즉시 선점합니다. 그러나 하드웨어 인터럽트 핸들러가 길어지면 다른 하드웨어 인터럽트가 마스킹되는 문제가 발생합니다. 리눅스 커널은 이를 해결하기 위해 최소한의 패킷 수신 등록만 수행하고 즉시 복귀한 뒤, 나머지 실질적인 프로토콜 스택 처리를 비동기 소프트웨어 인터럽트인 소프트IRQ(Bottom-Half)로 위임합니다.

소프트IRQ는 `NET_RX_SOFTIRQ` 벡터를 통해 구동되며 각 CPU 코어마다 전용으로 할당된 ksoftirqd 커널 스레드에 의해 스케줄링됩니다. NAPI 인터페이스는 인터럽트 구동 방식과 폴링 방식을 혼합하여 패킷 수신량이 임계치를 초과할 때 인터럽트를 비활성화하고 폴링 모드로 전환함으로써 시스템의 불필요한 컨텍스트 스위칭 오버헤드를 줄입니다.

## 2. RPS 및 RSS를 활용한 멀티코어 부하 분산 전략

단일 CPU 코어에 네트워크 인터럽트가 집중되면 해당 코어의 소프트IRQ 점유율이 100%에 도달하여 패킷 드롭이 발생합니다. 최신 멀티큐 네트워크 카드는 RSS 기술을 통해 하드웨어 해시 기반으로 패킷을 여러 수신 큐에 균등 분산합니다.

하드웨어 멀티큐를 지원하지 않거나 가상화 환경인 경우에는 커널 계층에서 제공하는 RPS를 활성화해야 합니다. sysfs 디렉터리의 rps_cpus 설정 파일에 CPU 마스크 비트맵을 할당함으로써 네트워크 소프트IRQ 패킷 파싱 작업을 가용한 모든 물리 CPU 코어로 확장할 수 있습니다.

## 3. 실무 운영 및 프로덕션 점검 체크리스트

프로덕션 클러스터의 안정적인 네트워크 처리를 위해 엔지니어는 다음 운영 지표를 주기적으로 점검해야 합니다.

1. proc softirqs 파일의 NET_RX 카운터 증가율을 실시간 모니터링하여 특정 코어의 쏠림 현상을 감지합니다.
2. mpstat 명령어를 통해 각 CPU 코어별 소프트 인터럽트 점유율을 계측하고 70% 초과 코어가 존재하는지 확인합니다.
3. NAPI 폴링 버짓과 패킷 백로그를 트래픽 대역폭에 비례하여 적절히 튜닝하여 네트워크 인터페이스 큐를 보존합니다.
4. 패킷 링 버퍼 디스크립터 크기와 드라이버 메모리 할당 상태를 ethtool 명령어로 주기적 진단합니다.
5. 시스템 엔지니어링 표준 절차에 따라 장애 발생 시 즉시 커널 메시지와 메트릭 수집을 병행합니다.

---

> 📌 [출처: Linux Kernel Networking Documentation (https://docs.kernel.org/networking/napi.html) 및 RFC 9110 HTTP Semantics]
"""
    temp_good_12 = temp_dir / "_test_good_12.md"
    temp_good_12.write_text(good_compliant_12, encoding="utf-8")
    rep30 = gatekeeper.verify(str(temp_good_12), platform_override="tistory")
    assert rep30.is_passed, f"Case 30: Compliant post should PASS with 0 violations, but got: {rep30.violations}"
    assert rep30.reject_count == 0
    assert rep30.score == 100
    print("  ✅ Test 30 Passed: Fully compliant 12-Gate article passed with 100/100 score!")

    # 임시 파일 정리
    all_temp_files = [
        temp_bad_en, temp_bad_drama, temp_bad_health, temp_bad_code, temp_bad_secret,
        temp_bad_fin, temp_bad_med, temp_bad_ftc, temp_bad_kogl, temp_bad_sec, temp_bad_math,
        temp_res_past, temp_res_buf, temp_res_min, temp_res_sec, temp_good_res, temp_immediate,
        temp_gear_img, temp_naver_img, temp_g10_sources, temp_g10_date, temp_g10_body,
        temp_g11_welfare, temp_g11_health, temp_g11_tech, temp_g11_stock, temp_g12_vague,
        temp_g12_api, temp_good_12
    ]
    for p in all_temp_files:
        if p.exists():
            p.unlink()

    print(f"\n{Color.GREEN}{Color.BOLD}🎉 ALL 30 SELF-TESTS PASSED: 철벽 게이트 검증 엔진의 12대 품질, 마크다운/수식 무결성, 공인 실측 출처, 이론 정합성 및 실시간 팩트체크 방벽이 100% 정상 동작합니다!{Color.RESET}\n")


# ==============================================================================
# 💻 CLI 실행 진입점 (Command Line Interface)
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🏛️ 철벽 게이트 검증 시스템 CLI (Ironclad Gatekeeper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
[사용 예시]
  1. 단건 글 정밀 검증:
     python ironclad_gatekeeper.py --file posts/70_trouble_example.md
  2. 예약 일시 선별 검증:
     python ironclad_gatekeeper.py --file posts/125_example.md --reserve "2026-12-07 18:42"
  3. 개발 블로그 영문 글 검증:
     python ironclad_gatekeeper.py --file blogs/dev/_posts/2026-11-23-example.md --platform dev
  4. 특정 디렉터리 내 전체 글 일괄 검사:
     python ironclad_gatekeeper.py --dir posts/
  5. 내장 자체 무결성 단위 테스트:
     python ironclad_gatekeeper.py --self-test
  6. JSON 결과 출력:
     python ironclad_gatekeeper.py --file posts/70_trouble_example.md --json
        """
    )

    parser.add_argument("file_pos", nargs="?", default=None, help="검증할 마크다운 파일 경로 (위치 인자)")
    parser.add_argument("--file", "-f", help="검증할 마크다운 파일 경로")
    parser.add_argument("--dir", "-d", help="검증할 마크다운 디렉터리 경로 (내부 .md 일괄 검증)")
    parser.add_argument("--platform", "-p", choices=["auto", "dev", "tistory", "naver", "markets", "stock", "gear"], default="auto", help="타깃 플랫폼 (기본값: auto)")
    parser.add_argument("--reserve", "-R", help="통합 발행 예약 일시 (예: '2026-12-07 18:42')")
    parser.add_argument("--reserve-date", "-D", help="발행 예약 날짜 (예: '2026-12-07')")
    parser.add_argument("--reserve-time", "-T", help="발행 예약 시간 (예: '18:42')")
    parser.add_argument("--is-reserved", action="store_true", help="예약 모드 강제 지정")
    parser.add_argument("--strict", action="store_true", help="엄격 모드 (WARNING도 REJECT로 취급)")
    parser.add_argument("--require-subagent-audit", action="store_true", help="독립 감사 서브에이전트 승인 토큰 필수화 (코드1 배포 시 필수)")
    parser.add_argument("--self-test", action="store_true", help="내장 자체 단위 테스트 실행")
    parser.add_argument("--check-facts", action="store_true", help="공인 실측 마스터 데이터 교차 검증 러너 실행")
    parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
    parser.add_argument("--no-hints", action="store_true", help="교정 팁 출력 생략")

    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    gatekeeper = IroncladGatekeeper(strict_mode=args.strict)
    gatekeeper.require_subagent_audit = getattr(args, "require_subagent_audit", False)
    platform_override = None if args.platform == "auto" else args.platform
    target_file = args.file or args.file_pos

    # 단건 파일 검증
    if target_file:
        if args.check_facts:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            facts = gatekeeper.cross_reference_assertions(content, platform=args.platform)
            print("\n" + "=" * 80)
            print(f"🔍 {Color.BOLD}공인 실측 데이터 교차 검증 리포트 (Live Fact-Check Runner){Color.RESET}")
            print("=" * 80)
            if not facts:
                print("  ℹ️ 본문에서 교차 검증 가능한 특정 도메인 assertion이 식별되지 않았습니다.")
            else:
                for idx, fact in enumerate(facts, start=1):
                    if fact.is_valid:
                        print(f"  #{idx} [{fact.domain.upper()}] {fact.assertion_type}: {Color.GREEN}VERIFIED (정합성 확인){Color.RESET}")
                    else:
                        print(f"  #{idx} [{fact.domain.upper()}] {fact.assertion_type}: {Color.RED}MISMATCH (수치/이론 불일치 발견){Color.RESET}")
                    print(f"      📝 스니펫: \"{fact.snippet}\"")
                    print(f"      🔍 판정: {fact.message}")
                    if fact.expected:
                        print(f"      📌 공인 규격: {fact.expected}")
                    if fact.actual:
                        print(f"      ⚠️ 본문 수치: {fact.actual}")
            print("=" * 80 + "\n")

        report = gatekeeper.verify(
            target_file,
            platform_override=platform_override,
            is_reserved=args.is_reserved,
            reserve_date=args.reserve_date,
            reserve_time=args.reserve_time,
            reserve_composite=args.reserve
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print_gate_report(report, show_hints=(not args.no_hints))
        sys.exit(0 if report.is_passed else 1)

    # 디렉터리 일괄 검증
    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"❌ 디렉터리를 찾을 수 없습니다: {args.dir}")
            sys.exit(1)

        files = list(dir_path.glob("*.md")) + list(dir_path.glob("**/*.md"))
        # 중복 제거
        files = sorted(list(set(files)))
        if not files:
            print(f"⚠️ 디렉터리 내에 .md 파일이 없습니다: {args.dir}")
            sys.exit(0)

        print(f"\n📂 총 {len(files)}개 마크다운 파일 일괄 철벽 검증 시작...")
        reports: List[GateReport] = []
        fail_count = 0

        for f in files:
            rep = gatekeeper.verify(
                str(f),
                platform_override=platform_override,
                is_reserved=args.is_reserved,
                reserve_date=args.reserve_date,
                reserve_time=args.reserve_time,
                reserve_composite=args.reserve
            )
            reports.append(rep)
            if not rep.is_passed:
                fail_count += 1
                if not args.json:
                    print_gate_report(rep, show_hints=(not args.no_hints))

        if args.json:
            print(json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 60)
            print(f"📊 [일괄 검증 종합 결과: 총 {len(files)}편]")
            print(f"  - 통과: {Color.GREEN}{len(files) - fail_count}편{Color.RESET}")
            print(f"  - 차단: {Color.RED}{fail_count}편{Color.RESET}")
            print("=" * 60 + "\n")

        sys.exit(0 if fail_count == 0 else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
