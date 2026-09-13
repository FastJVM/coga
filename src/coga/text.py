"""Small text helpers shared by modules that read captured child output."""

from __future__ import annotations

import re

# Any CSI sequence — colour, cursor movement, erase-line — as emitted by a
# child that believes it has a TTY.
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Drop terminal control sequences captured from a child's coloured output."""
    return ANSI_RE.sub("", text)


__all__ = ["ANSI_RE", "strip_ansi"]
