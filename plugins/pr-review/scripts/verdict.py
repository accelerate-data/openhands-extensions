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
# A ``` or ~~~ fence, indented or not (a proof under a list item), closed by the same marker.
_FENCE = re.compile(r"^[ \t]*(```|~~~)[ \t]*([^\n]*)\n(.*?)^[ \t]*\1", re.M | re.S)
# A suggestion or diff block quotes code, not a command's output.
_NOT_OUTPUT = {"suggestion", "diff"}


def _has_proof(body: str) -> bool:
    """A fenced block (not a suggestion or diff) holding a `$ ` command line and a line of its output."""
    for _marker, info, block in _FENCE.findall(body):
        if info.strip().split(" ")[0].lower() in _NOT_OUTPUT:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
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
