"""Process runner for skill installation and skill update tooling."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


def run_subprocess(
    args: Sequence[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    argv = list(args)
    return subprocess.run(
        argv,
        cwd=cwd,
        text=True, encoding="utf-8",
        capture_output=True,
        check=False,
    )
