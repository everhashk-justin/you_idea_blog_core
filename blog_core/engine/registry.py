# -*- coding: utf-8 -*-
"""
blog_core.engine.registry - Dynamic rule auto-discovery and platform whitelist registry (RuleRegistry)
"""

import importlib
import inspect
import pkgutil
from typing import Dict, List, Optional, Type, Union

from blog_core.engine.base_rule import BaseRule


class RuleRegistry:
    """
    모든 검증 규칙을 보관하고 플랫폼 화이트리스트에 따라 필터링하는 레지스트리.
    - pkgutil.walk_packages를 이용한 동적 자동 탐색 (Auto-Discovery)
    - 플랫폼별 엄격한 화이트리스트 필터링 (Platform Whitelist Filtering)
    """

    def __init__(self):
        self._rules: Dict[str, BaseRule] = {}
        self._discovered: bool = False

    def register(self, rule: Union[BaseRule, Type[BaseRule]]) -> BaseRule:
        """단일 규칙 인스턴스 또는 클래스를 레지스트리에 등록."""
        instance = rule() if inspect.isclass(rule) else rule
        if not hasattr(instance, "rule_id") or not instance.rule_id:
            raise ValueError(f"Rule {rule} must have a non-empty 'rule_id' attribute.")
        self._rules[instance.rule_id] = instance
        return instance

    def unregister(self, rule_id: str) -> Optional[BaseRule]:
        """규칙 식별자로 등록 해제 (테스트 및 동적 제거용)."""
        return self._rules.pop(rule_id, None)

    def clear(self):
        """모든 등록된 규칙 초기화."""
        self._rules.clear()
        self._discovered = False

    def discover(self, package_names: Optional[List[str]] = None, force_reload: bool = False):
        """
        지정된 패키지 경로 하위의 모든 모듈을 동적 임포트하여 BaseRule 서브클래스 자동 등록.
        기본 패키지: ['blog_core.rules.common', 'blog_core.rules.platforms']
        """
        if self._discovered and not force_reload:
            return

        if package_names is None:
            package_names = ["blog_core.rules.common", "blog_core.rules.platforms"]

        for pkg_name in package_names:
            try:
                pkg = importlib.import_module(pkg_name)
            except ImportError:
                continue

            if not hasattr(pkg, "__path__"):
                continue

            for _, modname, _ in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg_name}."):
                try:
                    mod = importlib.import_module(modname)
                except Exception:
                    continue

                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, BaseRule)
                        and attr is not BaseRule
                        and not inspect.isabstract(attr)
                    ):
                        try:
                            self.register(attr)
                        except Exception:
                            pass

        self._discovered = True

    def get_rules(
        self,
        platform: Optional[str] = None,
        gate_id: Optional[str] = None,
        auto_discover: bool = True
    ) -> List[BaseRule]:
        """
        플랫폼 화이트리스트 및 게이트 필터링.
        - rule.platforms is None: 모든 플랫폼 공통 적용
        - rule.platforms is not None: platform이 명시되어 있고 대소문자 무관하게 일치할 때만 실행
        """
        if auto_discover and not self._discovered:
            self.discover()

        matched: List[BaseRule] = []
        for rule in self._rules.values():
            # 게이트 필터링
            if gate_id and getattr(rule, "gate_id", None) != gate_id:
                continue

            # 플랫폼 화이트리스트 필터링
            if rule.platforms is None:
                # 공통 규칙은 항상 포함
                matched.append(rule)
            elif platform:
                target_platform = platform.lower().strip()
                allowed_platforms = [p.lower().strip() for p in rule.platforms]
                if target_platform in allowed_platforms:
                    matched.append(rule)

        # 게이트 ID 및 룰 ID 순으로 안정적 정렬
        gate_sort_order = {
            "GATE_0": 0, "GATE_1": 1, "GATE_2": 2, "GATE_3": 3,
            "GATE_4": 4, "GATE_5": 5, "GATE_6": 6, "GATE_7": 7, "GATE_8": 8
        }
        return sorted(
            matched,
            key=lambda r: (gate_sort_order.get(r.gate_id, 99), getattr(r, "rule_id", ""))
        )

    @property
    def rules(self) -> Dict[str, BaseRule]:
        return dict(self._rules)


# 전역 기본 레지스트리 싱글톤 인스턴스
default_registry = RuleRegistry()
