"""Shared fixtures: recorded otterdog plan outputs (ADR-0007 L1).

The plan fixtures are real captured outputs from this repo's history — PR #41
(ECA drift, 17 changes), PR #42 (vs-dolt-only), a synthetic empty plan, and a
synthetic mixed-symbols plan exercising +/!/- top-level resources. The otterdog
version pin (justfile.project) anchors this format's stability.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def plan_pr41() -> str:
    """PR #41: ECA status-check drift across 16 rulesets + vs-dolt, 17 changes."""
    return _read("plan_pr41_eca.txt")


@pytest.fixture
def plan_pr42() -> str:
    """PR #42: the lone benign vs-dolt code-scanning drift, 1 change."""
    return _read("plan_pr42_vsdolt.txt")


@pytest.fixture
def plan_empty() -> str:
    """Synthetic empty plan: 0 to add, 0 to change, 0 to delete."""
    return _read("plan_empty.txt")


@pytest.fixture
def plan_mixed() -> str:
    """Synthetic plan with top-level +, !, and - resource blocks."""
    return _read("plan_mixed_symbols.txt")


@pytest.fixture
def allowlist_path() -> Path:
    """Allow-list flagging the vs-dolt divergence as expected."""
    return FIXTURES / "allowlist.toml"
