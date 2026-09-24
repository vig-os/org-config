"""L1 guard: every mirror of the otterdog pin equals the ADR-0005 SSoT (#228).

`justfile.project`'s `otterdog_version` is the single source of truth. Since
#228 the pin is also the `workflow_call` default of the three reusable engine
workflows, so a downstream caller inherits it with the engine ref it already
pins instead of hand-mirroring the literal in its own `with:` block. That
deliberate duplication is what this module guards: a bump that moves the
justfile and forgets a workflow default fails here, in this repo's own CI,
rather than silently in a consumer org.

`template/.github/workflows/import.yml` joins the same assertion — it is a
standalone `workflow_dispatch` bootstrap, not a caller of a reusable workflow,
so it keeps its own literal (and it is the literal the 1.4.0 bump missed, #164
item 7).

Since #250 the pin is also machine-bumpable: each literal carries a
`# renovate: datasource=pypi depName=otterdog` marker that `renovate.json`'s
`custom.regex` manager reads. Deleting a marker would silently drop that site
from Renovate's view and quietly restore the hand-edit failure mode, so the
markers are asserted here too — and the manager's own regex is run against the
real files, which is what makes "the regex matches all five" a checked claim
rather than a hope.

Pure and offline: the workflows are parsed as text, since this project declares
no runtime dependencies (ADR-0005) and therefore has no YAML parser.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT

# Mirrors of the pin: (path relative to the repo root, input name).
PIN_MIRRORS: list[tuple[str, str]] = [
    (".github/workflows/plan.yml", "otterdog_version"),
    (".github/workflows/apply.yml", "otterdog_version"),
    (".github/workflows/drift.yml", "otterdog_version"),
    ("template/.github/workflows/import.yml", "otterdog_version"),
]

# Every file holding a pin literal: the SSoT plus the four mirrors above. This
# is the set Renovate's custom manager must see in full (#250).
PIN_SITES: list[str] = ["justfile.project", *(path for path, _ in PIN_MIRRORS)]

# The marker that carries datasource/depName to the custom manager. It sits on
# the line immediately above each literal.
RENOVATE_MARKER = "# renovate: datasource=pypi depName=otterdog"

_SSOT = re.compile(r'^otterdog_version\s*:=\s*"([^"]+)"', re.MULTILINE)


def read_ssot_pin() -> str:
    """The ADR-0005 single source of truth: `justfile.project`'s pin."""
    text = (REPO_ROOT / "justfile.project").read_text()
    match = _SSOT.search(text)
    assert match is not None, 'no `otterdog_version := "..."` line in justfile.project'
    return match.group(1)


def read_input_default(relative_path: str, input_name: str) -> str:
    """The `default:` of one workflow input, read by indentation.

    Finds the `<input_name>:` key, then scans the block indented under it for
    its `default:` — the same shape whether the input sits under `workflow_call`
    or `workflow_dispatch`. Surrounding quotes are stripped.
    """
    lines = (REPO_ROOT / relative_path).read_text().splitlines()
    key = re.compile(rf"^(\s*){re.escape(input_name)}:\s*$")
    for index, line in enumerate(lines):
        header = key.match(line)
        if header is None:
            continue
        indent = len(header.group(1))
        for candidate in lines[index + 1 :]:
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                break  # left the input's block without finding a default
            default = re.match(r"\s*default:\s*(.*?)\s*$", candidate)
            if default is not None:
                return default.group(1).strip("\"'")
    raise AssertionError(f"no `{input_name}:` input with a `default:` in {relative_path}")


def test_ssot_pin_parses() -> None:
    pin = read_ssot_pin()
    assert re.fullmatch(r"\d+\.\d+\.\d+", pin), f"unexpected pin format: {pin!r}"


@pytest.mark.parametrize(("relative_path", "input_name"), PIN_MIRRORS)
def test_mirror_equals_ssot_pin(relative_path: str, input_name: str) -> None:
    assert read_input_default(relative_path, input_name) == read_ssot_pin()


def test_every_mirror_path_exists() -> None:
    # A mirror that was renamed or deleted must fail loudly, not silently stop
    # being checked.
    missing = [path for path, _ in PIN_MIRRORS if not (REPO_ROOT / path).is_file()]
    assert missing == []


def test_template_callers_do_not_pin_the_version() -> None:
    # Since #228 the `template/` callers inherit the pin from the engine ref they
    # already pin; re-adding the input would restore the unenforced hand mirror.
    callers = [
        Path("template/.github/workflows/plan.yml"),
        Path("template/.github/workflows/apply.yml"),
        Path("template/.github/workflows/drift.yml"),
    ]
    offenders = [
        str(caller)
        for caller in callers
        if re.search(r"^\s*otterdog_version:", (REPO_ROOT / caller).read_text(), re.MULTILINE)
    ]
    assert offenders == []


def find_pin_line(relative_path: str) -> tuple[list[str], int]:
    """The file's lines and the index of the one carrying the pin literal.

    Matches only a real pin site — the justfile assignment or a workflow input
    `default:` — never the prose around it, which mentions past versions (e.g.
    plan.yml's "(1.4.0 -> 1.5.0)" comment).
    """
    pin = read_ssot_pin()
    lines = (REPO_ROOT / relative_path).read_text().splitlines()
    assignment = re.compile(r"^\s*otterdog_version\s*:=")
    default = re.compile(rf"^\s*default:\s*[\"']?{re.escape(pin)}[\"']?\s*$")
    for index, line in enumerate(lines):
        if pin in line and (assignment.match(line) or default.match(line)):
            return lines, index
    raise AssertionError(f"no line carrying the pin {pin!r} in {relative_path}")


def read_renovate_custom_manager() -> dict:
    """The single `custom.regex` manager that owns the otterdog pin (#250)."""
    config = json.loads((REPO_ROOT / "renovate.json").read_text())
    managers = config["customManagers"]
    assert len(managers) == 1, "expected exactly one customManagers entry"
    return managers[0]


def _as_python_regex(match_string: str) -> re.Pattern[str]:
    """Renovate matchStrings are JS/re2; `re` spells named groups differently.

    A faithful-enough translation for the shapes used here: no lookbehind, so
    rewriting `(?<name>` to `(?P<name>` is the whole difference. This checks the
    pattern's INTENT offline; `renovate-config-validator` checks its syntax.
    """
    return re.compile(match_string.replace("(?<", "(?P<"))


@pytest.mark.parametrize("relative_path", PIN_SITES)
def test_pin_site_carries_the_renovate_marker(relative_path: str) -> None:
    lines, index = find_pin_line(relative_path)
    assert index > 0, f"the pin is the first line of {relative_path}, so nothing sits above it"
    assert lines[index - 1].strip() == RENOVATE_MARKER, (
        f"{relative_path}:{index + 1} has no Renovate marker directly above the pin \u2014 "
        f"the custom manager would silently stop bumping it (#250)"
    )


def test_renovate_enables_the_custom_manager() -> None:
    config = json.loads((REPO_ROOT / "renovate.json").read_text())
    assert "custom.regex" in config["enabledManagers"], (
        "`enabledManagers` is an allowlist: dropping `custom.regex` disables the manager"
    )


@pytest.mark.parametrize("relative_path", PIN_SITES)
def test_custom_manager_regex_matches_the_pin_site(relative_path: str) -> None:
    """The manager's own regex, run against the real file (#250).

    This is the offline half of "the regex is validated, not assumed": it fails
    if a marker drifts from the literal, if a matchString stops matching, or if
    a file grows a second thing that looks like a pin.
    """
    manager = read_renovate_custom_manager()
    text = (REPO_ROOT / relative_path).read_text()
    matches = [
        match
        for match_string in manager["matchStrings"]
        for match in _as_python_regex(match_string).finditer(text)
    ]
    assert len(matches) == 1, (
        f"expected exactly one pin match in {relative_path}, got {len(matches)}"
    )
    groups = matches[0].groupdict()
    assert groups["currentValue"] == read_ssot_pin()
    assert groups["datasource"] == "pypi"
    assert groups["depName"] == "otterdog"
