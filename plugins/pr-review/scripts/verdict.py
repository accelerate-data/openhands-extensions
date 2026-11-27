"""Decide the review's GitHub event from what the review posted.

Pure: takes already-fetched bodies and returns the event or a relabelled body. The model posts its
findings as a COMMENT review; this caps an unproven Critical at Important, then decides whether the run
also approves.
"""

from __future__ import annotations

import re

CRITICAL_MARKER = "🔴"
# A finding opens with its priority label "🔴 Critical", after any list bullet, quote, heading or bold
# markup. A 🔴 mentioned mid-sentence ("the earlier 🔴 Critical no longer applies"), or one that a hard
# wrap puts at the start of a line ("🔴. `review_event` then ..."), is not a finding.
_FINDING_LINE = re.compile(r"^[\s>*_\-+#\d.]*" + CRITICAL_MARKER + r"[\s*_]*Critical")
_CRITICAL_LABEL = re.compile(r"🔴([\s*_]*)Critical")
# A ``` or ~~~ fence, indented or not (a proof under a list item), closed by the same marker.
_FENCE = re.compile(r"^[ \t]*(```|~~~)[ \t]*([^\n]*)\n(.*?)^[ \t]*\1", re.M | re.S)
# A suggestion or diff block quotes code, not a command's output.
_NOT_OUTPUT = {"suggestion", "diff"}


_FENCE_LINE = re.compile(r"^[ \t]*(```|~~~)")


def _openers(lines: list[str]) -> list[int]:
    """Indexes of the lines that open a 🔴 Critical finding, skipping lines inside a fenced block (a quoted
    example or command output is not a finding)."""
    openers, fence = [], None
    for i, line in enumerate(lines):
        mark = _FENCE_LINE.match(line)
        if mark:
            fence = None if fence == mark.group(1) else (fence or mark.group(1))
        elif fence is None and _FINDING_LINE.match(line):
            openers.append(i)
    return openers


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
    """The body with each 🔴 Critical finding that quotes no reproducing command and its output (a fenced
    block with a `$ ` line and an output line) relabelled 🟠 Important.

    A finding runs from its opening line to the next finding's, so each Critical finding in a review body
    needs its own proof.
    """
    if not body:
        return body
    lines = body.split("\n")
    openers = _openers(lines)
    for start, end in zip(openers, openers[1:] + [len(lines)]):
        if not _has_proof("\n".join(lines[start:end])):
            lines[start] = _CRITICAL_LABEL.sub(r"🟠\1Important", lines[start], count=1)
    return "\n".join(lines)


def review_event(bodies: list[str | None]) -> str:
    """`APPROVE` when no line of a posted body (review body or kept inline comment) opens a 🔴 Critical
    finding, else `COMMENT`. Never `REQUEST_CHANGES`."""
    for body in bodies:
        if _openers((body or "").split("\n")):
            return "COMMENT"
    return "APPROVE"
