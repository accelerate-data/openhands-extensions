"""Decide the review's GitHub event from what the review posted.

Pure: takes already-fetched bodies and returns the event or a relabelled body. The model posts its
findings as a COMMENT review; this caps an unproven Critical at Important, then decides whether the run
also approves.
"""

from __future__ import annotations

import re

CRITICAL_MARKER = "🔴"
# A finding opens with its priority label, after any list bullet, quote or bold markup; a 🔴 mentioned
# mid-sentence ("the earlier 🔴 Critical no longer applies") is not a finding.
_FINDING_LINE = re.compile(r"^[\s>*_\-+\d.]*" + CRITICAL_MARKER)
_CRITICAL_LABEL = re.compile(r"🔴(\s*\**\s*)Critical")
_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)


def _has_proof(body: str) -> bool:
    """A fenced block holding a `$ ` command line and at least one line of its output."""
    for block in _FENCE.findall(body):
        lines = [line for line in block.splitlines() if line.strip()]
        if any(line.startswith("$ ") for line in lines) and any(
            not line.startswith("$ ") for line in lines
        ):
            return True
    return False


def relabel_unproven(body: str | None) -> str | None:
    """The body with each line that opens a 🔴 Critical finding relabelled 🟠 Important, unless the body
    quotes a reproducing command and its output (a fenced block with a `$ ` line and an output line).

    One body is one finding (an inline comment); a review body listing several shares one proof.
    """
    if not body or _has_proof(body):
        return body
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if _FINDING_LINE.match(line):
            relabelled = _CRITICAL_LABEL.sub(r"🟠\1Important", line, count=1)
            lines[i] = relabelled if relabelled != line else line.replace(CRITICAL_MARKER, "🟠", 1)
    return "\n".join(lines)


def review_event(bodies: list[str | None]) -> str:
    """`APPROVE` when no line of a posted body (review body or kept inline comment) opens a 🔴 Critical
    finding, else `COMMENT`. Never `REQUEST_CHANGES`."""
    for body in bodies:
        if any(_FINDING_LINE.match(line) for line in (body or "").splitlines()):
            return "COMMENT"
    return "APPROVE"
