# -*- coding: utf-8 -*-
"""
blog_core.engine.models - Data models for violations, reports, severity, and styling
"""

from dataclasses import dataclass, field, asdict
from typing import List


class Severity:
    REJECT = "REJECT"
    WARNING = "WARNING"


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


@dataclass
class Violation:
    gate_id: str          # GATE_1 ~ GATE_8
    gate_name: str        # 게이트 명칭
    rule_id: str          # 상세 규칙 식별자
    severity: str         # "REJECT" 또는 "WARNING"
    line_number: int      # 위반 위치 (1-based, 0이면 전체/글로벌)
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
            "violations": [asdict(v) for v in self.violations],
        }

    @staticmethod
    def calculate_score(rejects: int, warnings: int) -> int:
        """점수 계산: 기본 100점에서 REJECT는 25점 감점, WARNING은 5점 감점 (최저 0점)."""
        return max(0, 100 - (rejects * 25) - (warnings * 5))
