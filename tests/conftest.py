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
REPO_ROOT = Path(__file__).resolve().parents[1]

# The real declared repo set committed in otterdog/vig-os/vig-os.jsonnet. Kept
# here as the L1 ground truth: the inventory sweep must extract exactly this set
# from the committed config (verified equal to a full go-jsonnet evaluation of
# the same file — see test_inventory).
DECLARED_REPOS: frozenset[str] = frozenset(
    {
        "commit-action",
        "devkit",
        "devkit-smoke-test",
        "h5v",
        "nvd-mirror",
        "org-config",
        "org-config-testbed",
        "qms",
        "qx",
        "scitadel",
        "sync-issues-action",
        "tessera",
        "vigos-mvp",
        "vs-dolt",
    }
)


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
    """Allow-list flagging vs-dolt (expected) + two `[[unmanaged]]` repos."""
    return FIXTURES / "allowlist.toml"


@pytest.fixture
def declared_jsonnet() -> str:
    """The real committed otterdog config — the declared-set extraction source."""
    return (REPO_ROOT / "otterdog" / "vig-os" / "vig-os.jsonnet").read_text()


@pytest.fixture
def declared_repos() -> frozenset[str]:
    """The known committed declared repo set (ground truth)."""
    return DECLARED_REPOS
