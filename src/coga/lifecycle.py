"""Shared ticket lifecycle vocabulary.

Status transitions still live in their owning commands/modules. This module
only names the values and the terminal subset so validators, read views, git
guards, and launchers do not each grow a slightly different status enum.
"""

from __future__ import annotations


VALID_STATUSES: frozenset[str] = frozenset(
    {"draft", "active", "in_progress", "blocked", "paused", "done", "canceled"}
)

TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "canceled"})

CANCELABLE_STATUSES: frozenset[str] = VALID_STATUSES - TERMINAL_STATUSES

# Stable human-facing order for `coga status` totals.
STATUS_DISPLAY_ORDER: tuple[str, ...] = (
    "in_progress",
    "blocked",
    "active",
    "draft",
    "paused",
    "done",
    "canceled",
)


__all__ = [
    "VALID_STATUSES",
    "TERMINAL_STATUSES",
    "CANCELABLE_STATUSES",
    "STATUS_DISPLAY_ORDER",
]
