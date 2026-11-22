"""Load report owners for unit tests and exercise actual CLI alias dispatch."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from functools import lru_cache
from types import SimpleNamespace, ModuleType


@lru_cache(maxsize=None)
def report_module(name: str) -> ModuleType:
    path = (Path(__file__).resolve().parents[1]
            / f"src/coga/resources/templates/coga/bootstrap/{name}/ticket.py")
    spec = importlib.util.spec_from_file_location("coga_report_" + name.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# pytest's basetemp is deeper than the 64-byte socket threshold, so every
# subprocess launch warns (`coga/launch` "Run state"); in-process launches are
# quieted by conftest instead.
RUN_STATE_PATH_WARNING = "Warning: run-state tmp path is "


def report_cli(args: list[str], *, env: dict[str, str] | None = None) -> SimpleNamespace:
    """Run a fresh CLI and its report child, retaining separate stderr."""
    child_env = dict(os.environ)
    child_env.update(PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"), TERM="dumb")
    child_env.update(env or {})
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", *args], env=child_env,
        capture_output=True, text=True,
    )
    return SimpleNamespace(exit_code=result.returncode, stdout=result.stdout,
                           stderr=result.stderr, output=result.stdout + "\n".join(
                               line for line in result.stderr.splitlines()
                               if not line.startswith(("→ coga ", RUN_STATE_PATH_WARNING))),
                           exception=None)
