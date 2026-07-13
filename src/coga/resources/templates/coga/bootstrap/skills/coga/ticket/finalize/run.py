#!/usr/bin/env python3
"""Finalize a guided ticket-authoring session."""

from __future__ import annotations

import sys

from coga.authoring import AuthoringError, finalize_authored_from_env
from coga.config import ConfigError


def main() -> int:
    try:
        finalize_authored_from_env()
    except ConfigError as exc:
        sys.stderr.write(f"[ticket-finalize] {exc}\n")
        return 2
    except AuthoringError as exc:
        sys.stderr.write(f"[ticket-finalize] {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
