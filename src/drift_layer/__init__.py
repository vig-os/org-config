"""Strict-drift layer: otterdog plan -> deduplicated drift+critical issues.

Pure-function core (parser -> reconcile) with the GitHub client injected at the
edge, per ADR-0002 (drift semantics) and ADR-0007 (CI & testing).
"""

from .models import DriftRecord, Issue, IssueAction, ParsedPlan, PlanSummary

__all__ = [
    "DriftRecord",
    "Issue",
    "IssueAction",
    "ParsedPlan",
    "PlanSummary",
]
