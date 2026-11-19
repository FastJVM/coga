"""Separator-aware help recognition shared by dispatch and publication."""
from __future__ import annotations

from collections.abc import Sequence


def help_requested(args: Sequence[str]) -> bool:
    """Recognize Typer's exact help token before an operand separator."""
    before_separator = list(args)
    if "--" in before_separator:
        before_separator = before_separator[:before_separator.index("--")]
    return "--help" in before_separator


def command_help_requested(args: Sequence[str]) -> bool:
    """Launch's first separator passes script argv; the second is its own."""
    args = list(args)
    if args[:1] == ["launch"] and "--" in args:
        separator = args.index("--")
        return help_requested(args[:separator]) or help_requested(args[separator + 1:])
    return help_requested(args)
