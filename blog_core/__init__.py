"""
🏛️ 01_you_idea_blog_core - Core Package for IdeaSpot360 Ecosystem
"""

__version__ = "0.1.0"

from blog_core.engine.models import Violation, GateReport, Severity, Color
from blog_core.engine.context import RuleContext
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.registry import RuleRegistry, default_registry

__all__ = [
    "Violation",
    "GateReport",
    "Severity",
    "Color",
    "RuleContext",
    "BaseRule",
    "RuleRegistry",
    "default_registry",
    "IroncladGatekeeper",
    "verify_or_abort",
]


def __getattr__(name):
    if name in ("IroncladGatekeeper", "verify_or_abort"):
        from blog_core.engine import gatekeeper
        return getattr(gatekeeper, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
