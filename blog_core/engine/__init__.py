"""
blog_core.engine - Core rule engine framework and models
"""

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
    "print_gate_report",
]


def __getattr__(name):
    if name in ("IroncladGatekeeper", "verify_or_abort", "print_gate_report"):
        from blog_core.engine import gatekeeper
        return getattr(gatekeeper, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
