#!/usr/bin/env python3
"""Thin wrapper for the validate-drift Dream worker.

Invoked by the bootstrap/dream skill from within the agent's session.
"""

from __future__ import annotations

import sys

from relay.dream_validate_drift import main as validate_drift_main


def main(argv: list[str] | None = None) -> int:
    return validate_drift_main(argv)


if __name__ == "__main__":
    sys.exit(main())
