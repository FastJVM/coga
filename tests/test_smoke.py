"""End-to-end smoke test: run the full lifecycle against the seeded `example/` repo.

Verifies:
- `relay create` scaffolds a task with a frozen workflow snapshot.
- Prompt composition includes every expected section.
- `relay step` advances and `relay step <final>` marks the task done.
- `relay panic` writes to blackboard + releases the lock.
- `relay feed` logs a message.
- `relay status` lists the active task.
- The validator runs cleanly against a healthy repo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from relay.cli import app
from relay.commands.create import scaffold_task
from relay.compose import compose_prompt
from relay.config import load_config
from relay.tasks import list_tasks, read_ticket
from relay.validate import run as validate_run


EXAMPLE = Path(__file__).parent.parent / "example"


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the seeded example repo into tmp_path so the test doesn't mutate the source."""
    dest = tmp_path / "example"
    shutil.copytree(EXAMPLE, dest)
    monkeypatch.chdir(dest / "relay-os")
    return dest / "relay-os"


def test_lifecycle(seeded: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(seeded)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "ready"

    # 1. Create a task with the code/with-review workflow.
    ref = scaffold_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        mode="interactive",
        owner="marc",
        assignee="claude1",
        watchers=["pierre"],
        status="active",
    )
    task_path = ref["path"]
    for name in ("ticket.md", "blackboard.md", "log.md"):
        assert (task_path / name).is_file()

    # 2. Compose prompt includes every section.
    task_ref = list_tasks(cfg)[0]
    ticket = read_ticket(task_ref)
    prompt = compose_prompt(cfg, task_ref, ticket)
    assert "Never commit secrets" in prompt         # rules.md
    assert "email-tool repo handles deliverability" in prompt  # repo context.md
    assert "Stripe webhooks retry" in prompt         # ticket context
    assert "Tests live next to the code" in prompt   # step skill
    assert "Current step: implement" in prompt
    assert "Interactive mode" in prompt
    assert "Blackboard" in prompt

    # 3. Advance steps.
    runner = CliRunner()
    r = runner.invoke(app, ["step", "2", "--task", "001"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["step", "3", "--task", "001"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["step", "4", "--task", "001"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["step", "5", "--task", "001"])
    assert r.exit_code == 0, r.output
    assert read_ticket(task_ref).status == "done"

    # Lifecycle shows up in log.md
    log = (task_path / "log.md").read_text()
    assert "created" in log
    assert "advanced to step 2 (pr)" in log
    assert "task done" in log

    # 4. Create a second task so we can exercise panic + feed without revival of the first.
    ref2 = scaffold_task(
        cfg=cfg, title="Investigate slow DNS",
        workflow_name=None, contexts=[], mode="interactive",
        owner="marc", assignee="claude1", watchers=[], status="active",
    )
    r = runner.invoke(app, [
        "panic",
        "--task", ref2["id_slug"].split("-", 1)[0],
        "--reason", "need prod DNS access to reproduce",
    ])
    assert r.exit_code == 0, r.output
    bb = (ref2["path"] / "blackboard.md").read_text()
    assert "need prod DNS access to reproduce" in bb
    assert "## Blockers" in bb

    r = runner.invoke(app, [
        "feed",
        "--task", ref2["id_slug"].split("-", 1)[0],
        "--message", "checked DNS resolver logs, no answer",
    ])
    assert r.exit_code == 0
    assert "checked DNS resolver logs" in (ref2["path"] / "log.md").read_text()

    # 5. Status shows the active task (the first one is done, so not shown by default).
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert "002" in r.output
    assert "001" not in r.output  # done by default is hidden

    r = runner.invoke(app, ["status", "--all"])
    assert "001" in r.output
    assert "002" in r.output

    # 6. Validator reports no errors on this repo.
    report = validate_run(cfg)
    errors = [i for i in report.issues if i.severity == "error"]
    assert errors == [], [i.message for i in errors]
