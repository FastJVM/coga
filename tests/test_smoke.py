"""End-to-end smoke test: run the full lifecycle against the seeded `example/` repo.

Verifies:
- task creating creates a task with a frozen workflow snapshot.
- Prompt composition includes every expected section.
- `coga bump` advances; `coga mark done` finishes the final step.
- `coga panic` writes to blackboard + releases the lock.
- `coga slack` logs a message.
- `coga status` lists the task queue.
- The validator runs cleanly against a healthy repo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.create import create_task
from coga.compose import compose_prompt
from coga.config import load_config
from coga.logfile import task_log_lines
from coga.taskfile import fence_count, read_blackboard
from coga.tasks import list_tasks, read_ticket
from coga.validate import run as validate_run


EXAMPLE = Path(__file__).parent.parent / "example"


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the seeded example repo into tmp_path so the test doesn't mutate the source.

    `.claude/` and `.codex/` are gitignored, agent-skill materializations that
    coga regenerates on demand — not part of the seeded fixture. They contain
    `skills/coga` symlinks into `.agent-skills`, which may be stale/dangling on
    a developer's machine after running coga against `example/`. Excluding them
    keeps the copy reproducible (and avoids `shutil` choking on a dead symlink).
    """
    dest = tmp_path / "example"
    shutil.copytree(
        EXAMPLE,
        dest,
        ignore=shutil.ignore_patterns(".claude", ".codex", ".git", ".venv*", "venv"),
        ignore_dangling_symlinks=True,
    )
    monkeypatch.chdir(dest / "coga-os")
    return dest / "coga-os"


def test_lifecycle(seeded: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_config(seeded)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "draft"

    # 1. Create a task with the code/with-review workflow.
    ref = create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=["pierre"],
        status="in_progress",
    )
    # File-form task: the result path is the self-contained `tasks/<slug>.md`
    # ticket (with a blackboard fence) — no companion directory or siblings.
    task_path = ref["path"]
    assert task_path == seeded / "tasks" / "fix-retry-logic.md"
    assert task_path.is_file()
    assert not (seeded / "tasks" / "fix-retry-logic").exists()
    assert fence_count(task_path.read_text()) == 1

    # Discovery sees both the created top-level task and the seeded
    # fixture task nested one level inside the `tasks/auto/` directory.
    by_slug = {t.slug: t for t in list_tasks(cfg)}
    assert "triage-inbound-email" in by_slug
    assert by_slug["triage-inbound-email"].path.parent == seeded / "tasks" / "auto"

    # 2. Compose prompt includes every section.
    task_ref = by_slug[ref["slug"]]
    ticket = read_ticket(task_ref)
    prompt = compose_prompt(cfg, task_ref, ticket)
    assert "email-tool repo handles deliverability" in prompt  # repo context.md
    assert "Stripe webhooks retry" in prompt         # ticket context
    assert "Tests live next to the code" in prompt   # step skill
    assert "Current step: implement" in prompt
    assert "Interactive mode" in prompt
    assert "Blackboard" in prompt

    # 3. Advance steps. Workflow has 4 steps; 3 bumps walk to the last step,
    #    then `coga mark done` finishes the ticket.
    runner = CliRunner()
    slug = ref["slug"]
    for _ in range(3):
        r = runner.invoke(app, ["bump", slug])
        assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["mark", "done", slug])
    assert r.exit_code == 0, r.output
    assert read_ticket(task_ref).status == "done"

    # Lifecycle shows up in the repo-global log, tagged with this task's ref.
    log = "\n".join(task_log_lines(cfg, slug))
    assert "created" in log
    assert "advanced to step 2 (pr)" in log
    assert "task done" in log

    # 4. Create a second task so we can exercise panic + slack without revival of the first.
    ref2 = create_task(
        cfg=cfg, title="Investigate slow DNS",
        workflow_name="code/with-review", contexts=[], autonomy="interactive",
        owner="marc", assignee="claude", watchers=[], status="in_progress",
    )
    r = runner.invoke(app, [
        "panic",
        "--task", ref2["slug"],
        "--reason", "need prod DNS access to reproduce",
    ])
    assert r.exit_code == 1, r.output
    bb = read_blackboard(ref2["path"])
    assert "need prod DNS access to reproduce" in bb
    assert "## Blockers" in bb

    r = runner.invoke(app, [
        "slack",
        "--task", ref2["slug"],
        "--message", "checked DNS resolver logs, no answer",
    ])
    assert r.exit_code == 0
    log2 = "\n".join(task_log_lines(cfg, ref2["slug"]))
    assert "checked DNS resolver logs" in log2

    # 5. Status hides done tasks by default; --all includes them.
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert ref["slug"] not in r.output  # done — hidden by default
    assert ref2["slug"] in r.output
    r = runner.invoke(app, ["status", "--all"])
    assert r.exit_code == 0
    assert ref["slug"] in r.output
    assert ref2["slug"] in r.output

    # 6. Validator reports no errors on this repo.
    report = validate_run(cfg)
    errors = [i for i in report.issues if i.severity == "error"]
    assert errors == [], [i.message for i in errors]
