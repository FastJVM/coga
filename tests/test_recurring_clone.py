"""`scope: clone` recurring templates: serviced per clone, with no period task."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import recurring_runner as recurring_cmd
from coga.cli import app
from coga.config import load_config
from coga.recurring import (
    RecurringError,
    Template,
    list_templates,
    scan_clone_due,
    scan_due,
)
from coga.recurring_autofix import RunRecord
from coga.recurring_clone import clone_state_dir, read_clone_ledger
from coga.tasks import list_tasks


NOW = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday; the daily 7am firing is due

CLONE_TEMPLATE = """
---
schedule: "0 7 * * *"
title: "Local sweep"
scope: clone
---

## Description

Sweep this clone's local state.

<!-- coga:blackboard -->
"""

# Records what the runner handed the script, then exits with `EXIT_CODE`.
CLONE_SCRIPT = """
import json, os, sys
from pathlib import Path
out = Path(os.environ["COGA_COGA_OS_ROOT"]) / "runs.jsonl"
keys = ("COGA_RECURRING_SCOPE", "COGA_RECURRING_TEMPLATE", "COGA_RECURRING_PERIOD",
        "COGA_TASK_SLUG", "COGA_TASK_BLACKBOARD")
with out.open("a") as fh:
    fh.write(json.dumps({key: os.environ.get(key) for key in keys}) + "\\n")
print("swept local state")
sys.exit(EXIT_CODE)
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _clone_template(company: Path, name: str = "local-sweep", *, exit_code: int = 0) -> None:
    _write(company / "recurring" / name / "ticket.md", CLONE_TEMPLATE)
    _write(
        company / "recurring" / name / "ticket.py",
        CLONE_SCRIPT.replace("EXIT_CODE", str(exit_code)),
    )


def _runs(company: Path) -> list[dict[str, str | None]]:
    path = company / "runs.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(company / "coga.toml", "version = 1\n")
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


@pytest.mark.parametrize(
    ("extra", "script", "message"),
    [
        ("", False, "requires a reserved `ticket.py`"),
        ("delegate: bootstrap/orient\n", True, "`delegate` needs a period task"),
        ("state_keys: [cursor]\n", True, "`state_keys` needs a period task"),
        ("workflow: direct/body\n", True, "`workflow` needs a period task"),
    ],
)
def test_clone_scope_rejects_what_needs_a_period_task(
    repo: Path, extra: str, script: bool, message: str
) -> None:
    text = CLONE_TEMPLATE.replace("scope: clone\n", f"scope: clone\n{extra}")
    _write(repo / "recurring" / "local-sweep" / "ticket.md", text)
    if script:
        _write(repo / "recurring" / "local-sweep" / "ticket.py", "raise SystemExit(0)\n")
    with pytest.raises(RecurringError, match=message):
        Template.load(repo / "recurring" / "local-sweep", now=NOW)


def test_unknown_scope_is_a_template_error(repo: Path) -> None:
    _clone_template(repo)
    path = repo / "recurring" / "local-sweep" / "ticket.md"
    path.write_text(path.read_text().replace("scope: clone", "scope: machine"))
    with pytest.raises(RecurringError, match="`scope` must be one of repo, clone"):
        Template.load(path.parent, now=NOW)


def test_shared_scan_creates_no_period_task_for_a_clone_template(repo: Path) -> None:
    _clone_template(repo)
    cfg = load_config(repo)

    scan = scan_due(cfg, now=NOW)

    assert scan.tasks == [] and scan.errors == []
    assert list_tasks(cfg) == []
    assert not (repo / "log.md").exists()
    assert [due.template.name for due in scan_clone_due(cfg, now=NOW).due] == [
        "local-sweep"
    ]


def test_clone_run_records_the_period_locally_and_runs_once(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    cfg = load_config(repo)
    monkeypatch.setattr("coga.recurring.datetime", _frozen_datetime())
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/leaked")

    record = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, record) is False

    assert _runs(repo) == [
        {
            "COGA_RECURRING_SCOPE": "clone",
            "COGA_RECURRING_TEMPLATE": "local-sweep",
            "COGA_RECURRING_PERIOD": "2026-04-22",
            # No period task: nothing for the script to bump or report onto.
            "COGA_TASK_SLUG": None,
            "COGA_TASK_BLACKBOARD": None,
        }
    ]
    entry = read_clone_ledger(cfg, "local-sweep")
    assert entry is not None and entry.period == "2026-04-22"
    log = (clone_state_dir(cfg) / "local-sweep.log").read_text()
    assert "swept local state" in log
    [outcome] = record.outcomes
    assert (outcome.slug, outcome.result) == ("recurring/local-sweep", "completed")
    assert list_tasks(cfg) == []

    # Serviced here this period: the next sweep of this clone skips it.
    again = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, again) is False
    assert len(_runs(repo)) == 1
    assert again.outcomes == []
    [status] = list_templates(cfg, NOW)
    assert (status.scope, status.serviced, status.due) == ("clone", True, False)


def test_failed_clone_run_is_a_problem_and_retries_next_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo, exit_code=3)
    cfg = load_config(repo)
    monkeypatch.setattr("coga.recurring.datetime", _frozen_datetime())

    record = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, record) is True

    assert read_clone_ledger(cfg, "local-sweep") is None
    [outcome] = record.outcomes
    assert (outcome.result, outcome.exit_code) == ("failed", 3)
    assert "swept local state" in outcome.blackboard
    assert recurring_cmd._run_clone_scoped(cfg, RunRecord(started=NOW)) is True
    assert len(_runs(repo)) == 2


def test_inactive_repo_skips_non_exempt_clone_templates(repo: Path) -> None:
    _clone_template(repo)
    cfg = load_config(repo)

    scan = scan_clone_due(cfg, now=NOW, inactive_since="2026-01-01")

    assert scan.due == [] and scan.inactivity_skips == ["local-sweep"]


def test_named_launch_runs_a_clone_template_now(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    monkeypatch.setattr(recurring_cmd, "_relay_off_control_single_repo_run", lambda *a: None)
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *a, **k: None)

    first = CliRunner().invoke(app, ["recurring", "launch", "local-sweep"])
    second = CliRunner().invoke(app, ["recurring", "launch", "local-sweep"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    # A named launch ignores the clone ledger, as it ignores the shared one.
    assert len(_runs(repo)) == 2
    assert list_tasks(load_config(repo)) == []


def test_clone_only_sweep_skips_shared_templates(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    _write(
        repo / "recurring" / "shared" / "ticket.md",
        CLONE_TEMPLATE.replace("scope: clone\n", ""),
    )
    _write(repo / "recurring" / "shared" / "ticket.py", "raise SystemExit(0)\n")
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *a, **k: None)

    assert recurring_cmd.run_recurring_scan(load_config(repo), clone_only=True) == 0

    assert len(_runs(repo)) == 1
    assert list_tasks(load_config(repo)) == []


def test_ledger_lives_in_the_primary_checkout_for_a_linked_worktree(git_repo) -> None:
    """A run from a temporary control worktree counts for the clone that owns it."""
    linked = git_repo.root.parent / "linked"
    git_repo.git("worktree", "add", "--detach", str(linked))

    cfg = load_config(linked / "coga", require_user=False)

    assert clone_state_dir(cfg) == git_repo.coga_os / ".coga" / "recurring-clone"


def _frozen_datetime() -> type[datetime]:
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def,override]
            return NOW

    return Frozen
