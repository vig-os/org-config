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

Pure and offline: the workflows are parsed as text, since this project declares
no runtime dependencies (ADR-0005) and therefore has no YAML parser.
"""

from __future__ import annotations

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
