#!/usr/bin/env python3
"""Thin wrapper that runs `python -m relay.validate --json`.

Invoked by the meta/dream skill from within the agent's session.
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "relay.validate", "--json"],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
