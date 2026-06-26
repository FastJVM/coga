"""Shared helpers for command stubs."""

from __future__ import annotations

import sys

import typer


def not_implemented(name: str) -> None:
    typer.secho(f"{name} is not yet implemented.", fg=typer.colors.YELLOW, err=True)
    sys.exit(2)
