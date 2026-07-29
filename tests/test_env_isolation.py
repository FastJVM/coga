"""The autouse guard that detaches this suite from a supervising `coga launch`.

A supervisor exports its session metadata into the agent's env, and the agent
running `python -m pytest` hands the whole set to the suite. Two things then go
wrong: `emit_done_marker` writes the *live* sentinel and the supervisor kills
the test run, and a recipe under test reads the *live* `COGA_TASK_BLACKBOARD`
and appends its fixture report to the outer ticket. The second one really
happened — twenty-plus bogus `## Dream Skill: validate-drift` sections, each
reporting a fix to a task named `x`, landed across four live tickets.

`conftest.py::_clear_supervised_session_env` is the fix; these tests are what
keeps it complete.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from coga.repl_supervisor import (
    EXPECTED_STEP_ENV,
    EXPECTED_TASK_ENV,
    SENTINEL_ENV,
)
from coga.task_env import TASK_ENV_KEYS

_REPO_ROOT = Path(__file__).resolve().parents[1]

_EXPECTED_LAUNCH_OWNED_ENV = (
    SENTINEL_ENV,
    "COGA_SUPERVISED",
    EXPECTED_TASK_ENV,
    EXPECTED_STEP_ENV,
    *TASK_ENV_KEYS,
)

_CLEAN_ENV_TEST = (
    "tests/test_env_isolation.py::test_no_launch_owned_variable_reaches_a_test"
)


def _source_pythonpath() -> str:
    src_path = str(_REPO_ROOT / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if not existing_pythonpath:
        return src_path
    return src_path + os.pathsep + existing_pythonpath


def test_no_launch_owned_variable_reaches_a_test() -> None:
    """The assertion the guard exists for — and the one the child run below
    re-runs with the whole namespace poisoned."""
    leaked = sorted(
        key for key in _EXPECTED_LAUNCH_OWNED_ENV if key in os.environ
    )
    assert leaked == []


def test_guard_scrubs_metadata_inherited_from_a_supervised_parent(
    tmp_path: Path,
) -> None:
    """Re-run one test in a child `pytest` that inherits a full launch env.

    This is the only way to prove the *autouse* behavior: a test cannot poison
    its own process before the fixture that scrubs it has run. Every
    launch-owned variable is pointed at a stand-in outer ticket, and the child
    must still see a clean environment — and leave the file untouched.
    """
    outer_ticket = tmp_path / "coga" / "tasks" / "outer-ticket.md"
    outer_ticket.parent.mkdir(parents=True)
    outer_ticket.write_text("---\ntitle: Outer\n---\n\n<!-- coga:blackboard -->\n")
    before = outer_ticket.read_text()

    env = os.environ.copy()
    env.update({key: str(outer_ticket) for key in _EXPECTED_LAUNCH_OWNED_ENV})
    env["PYTHONPATH"] = _source_pythonpath()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            _CLEAN_ENV_TEST,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=_REPO_ROOT,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert outer_ticket.read_text() == before
