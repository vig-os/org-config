"""Parse ``otterdog plan`` text output into structured drift records.

This module owns otterdog's diff syntax. A plan looks like::

    Installed 53 packages in 40ms          <- uv/runner preamble (ignored)
    Planning execution:
    Actions are indicated with the following symbols:
      + create
      ~ modify
      ! forced update
      - delete

    Project vig-os[github_id=vig-os] (1/1)
      there have been 17 validation infos, ...

      ~ repository[name="vs-dolt"] {         <- resource block (2-space indent)
        ~ code_scanning_default_languages = [
          ~ "javascript"  -> "javascript-typescript"
          - "typescript"
        ~ ]
      ~ }

      Plan: 0 to add, 1 to change, 0 to delete.

One record is produced per top-level resource block. Nested lines (deeper
indentation) are captured verbatim as the record ``detail``. Everything before
the ``Project`` header — uv download noise, the symbol legend — is ignored, so
the parser tolerates the exact ``stdout+stderr`` capture the workflow feeds it.
"""

from __future__ import annotations

import re

from .models import CHANGE_TYPES, DriftRecord, ParsedPlan, PlanSummary

# `Project <name>[github_id=<id>] (1/1)` — anchors the start of the plan body
# and yields the org id used in fingerprints.
_PROJECT_RE = re.compile(r"^Project\s+\S+\[github_id=(?P<org>[^\]]+)\]")

# A top-level resource block opener: exactly two leading spaces, an action
# symbol, the resource header, then ` {`. Nested fields are indented deeper, so
# the two-space anchor is what distinguishes a resource from its body.
_RESOURCE_RE = re.compile(r"^  (?P<symbol>[+~!-]) (?P<resource>.+?) \{$")

# The plan trailer with the add/change/delete tallies.
_SUMMARY_RE = re.compile(
    r"^\s*Plan:\s+(?P<add>\d+) to add,\s+(?P<change>\d+) to change,\s+(?P<delete>\d+) to delete\.?"
)


def parse_plan(text: str, *, default_org: str = "unknown") -> ParsedPlan:
    """Parse otterdog plan ``text`` into a :class:`ParsedPlan`.

    ``default_org`` is used only if no ``Project`` header is present (e.g. a
    truncated capture); a well-formed plan always overrides it.
    """
    lines = text.splitlines()
    org = default_org
    records: list[DriftRecord] = []
    summary: PlanSummary | None = None

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        project = _PROJECT_RE.match(line)
        if project:
            org = project.group("org")
            i += 1
            continue

        summ = _SUMMARY_RE.match(line)
        if summ:
            summary = PlanSummary(
                add=int(summ.group("add")),
                change=int(summ.group("change")),
                delete=int(summ.group("delete")),
            )
            i += 1
            continue

        resource = _RESOURCE_RE.match(line)
        if resource:
            block_lines, i = _consume_block(lines, i)
            records.append(
                DriftRecord(
                    org=org,
                    resource=resource.group("resource"),
                    change_type=CHANGE_TYPES[resource.group("symbol")],
                    detail="\n".join(block_lines).rstrip(),
                )
            )
            continue

        i += 1

    return ParsedPlan(org=org, records=records, summary=summary)


def _consume_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect a resource block starting at ``start`` (its ``... {`` opener).

    Returns the block's lines (opener through its matching ``<symbol> }``
    closer) and the index just past the closer. The closer is the first line at
    the same two-space indentation whose content is ``}`` — nested closers are
    deeper-indented and do not match.
    """
    block = [lines[start]]
    j = start + 1
    n = len(lines)
    while j < n:
        block.append(lines[j])
        if re.match(r"^  [+~!-] \}$", lines[j]):
            j += 1
            break
        j += 1
    return block, j
