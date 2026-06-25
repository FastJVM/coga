"""Relay — the repo-level company OS (see docs/vision.md)."""

from __future__ import annotations

import sys


def _require_supported_python(version_info: tuple[int, ...] = sys.version_info) -> None:
    """Fail loud on an unsupported interpreter before any 3.11-only import runs.

    Relay targets Python 3.11+ and imports the stdlib `tomllib` (3.11+) at
    module load in `config.py` / `managed_skills.py` / `commands/update.py`. On
    an older interpreter that otherwise surfaces as a cryptic
    `ModuleNotFoundError: No module named 'tomllib'` deep in an import chain.

    Importing any `relay.*` submodule imports this package first, so this guard
    runs ahead of those imports and turns the failure into one actionable
    message. `pip` already refuses the install via `requires-python = ">=3.11"`;
    this is the backstop for source / `PYTHONPATH` runs that bypass that check.
    """
    if tuple(version_info[:2]) < (3, 11):
        got = f"{version_info[0]}.{version_info[1]}"
        raise RuntimeError(
            "Relay requires Python 3.11 or newer (it uses the stdlib `tomllib`); "
            f"this interpreter is Python {got}. Run Relay with a 3.11+ interpreter "
            "— e.g. `python3.12 -m relay.cli` — or install it into a 3.11+ "
            "virtualenv."
        )


_require_supported_python()

__version__ = "0.1.0"
