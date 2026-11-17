# -*- coding: utf-8 -*-
"""
blog_core.engine.base_rule - Abstract base class for all verification rules (BaseRule)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class BaseRule(ABC):
    """
    모든 검증 규칙이 상속받아야 하는 추상 기본 클래스.
    - rule_id: 규칙 고유 식별자 (예: G1_REQ_FRONTMATTER)
    - gate_id: 소속 게이트 ID ("GATE_1" ~ "GATE_8")
    - gate_name: 소속 게이트 명칭 (예: "구조 및 메타데이터 무결성")
    - description: 규칙에 대한 부가 설명
    - platforms: 적용 대상 플랫폼 목록. None이면 모든 플랫폼에 적용(공통 규칙),
                 리스트(예: ["dev"])이면 지정된 플랫폼 검증 시에만 화이트리스트 필터링되어 실행.
    - default_severity: 기본 심각도 ("REJECT" 또는 "WARNING")
    """

    rule_id: str
    gate_id: str
    gate_name: str
    description: str = ""
    platforms: Optional[List[str]] = None
    default_severity: str = "REJECT"

    @abstractmethod
    def check(self, ctx: RuleContext) -> List[Violation]:
        """
        주어진 RuleContext를 검사하여 위반 사항 목록을 반환.
        위반이 없으면 빈 리스트 []를 반환.
        """
        pass

    def __repr__(self) -> str:
        plat_str = ",".join(self.platforms) if self.platforms else "all"
        return f"<{self.__class__.__name__} rule_id={getattr(self, 'rule_id', '?')} gate={getattr(self, 'gate_id', '?')} platforms=[{plat_str}]>"
