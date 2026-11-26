"""`python -m coga_edge.migrate_step_scripts` rewrites in-flight branch tickets."""

from __future__ import annotations

import os

import pytest

from coga.config import load_config
from coga.create import create_task
from coga.tasks import resolve_task
from coga.ticket import Ticket
from coga_edge import migrate_step_scripts as migrate

OLD_WORKFLOW = """---
name: old
description: A branch workflow from before step scripts.
steps:
  - name: open-branch
    assignee: agent
    run: git/open-branch
  - name: implement
    assignee: agent
  - name: review
    assignee: owner
---

## implement
Implement it.

## review
Review it.
"""

NEW_WORKFLOW = """---
name: new
description: A branch workflow that declares step scripts.
enter: git/ticket-enter
exit: git/ticket-exit
steps:
  - name: implement
    assignee: agent
  - name: review
    assignee: owner
---

## implement
Implement it.

## review
Review it.
"""

PLAIN_WORKFLOW = """---
name: plain
description: No branch at all.
steps:
  - name: work
    assignee: agent
---

## work
Work.
"""


@pytest.fixture
def repo(git_repo, monkeypatch):
    for name, text in (("old", OLD_WORKFLOW), ("new", NEW_WORKFLOW), ("plain", PLAIN_WORKFLOW)):
        (git_repo.coga_os / "workflows" / f"{name}.md").write_text(text, encoding="utf-8")
    for key in [k for k in os.environ if k.startswith("COGA_") and k != "COGA_SYSTEM_TMPDIR"]:
        monkeypatch.delenv(key)
    monkeypatch.chdir(git_repo.root)
    return git_repo


def _ticket(repo, title: str, workflow: str, *, status: str = "active", step: int | None = None,
            edit=None):  # type: ignore[no-untyped-def]
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title=title, workflow_name=workflow, contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status=status,
    )
    path = resolve_task(cfg, created["slug"]).ticket_path
    ticket = Ticket.read(path)
    if step is not None:
        name = ticket.workflow["steps"][step - 1]["name"]
        ticket.frontmatter["step"] = f"{step} ({name})"
    if edit is not None:
        edit(ticket)
    ticket.write(path)
    return path


def _strip_scripts(ticket: Ticket) -> None:
    for key in ("enter", "exit"):
        ticket.workflow.pop(key, None)


def _set_status(status: str):  # type: ignore[no-untyped-def]
    def edit(ticket: Ticket) -> None:
        ticket.frontmatter["status"] = status
    return edit


def _seed(repo) -> None:  # type: ignore[no-untyped-def]
    repo.git("add", "-A")
    repo.git("commit", "-qm", "Seed tickets")
    repo.git("push", "-q", "origin", "main")


def test_ticket_at_open_branch_resumes_at_the_next_step(repo):
    path = _ticket(repo, "At open branch", "old", step=1)
    rewrite = migrate.migrate_text(path.read_text(encoding="utf-8"), load_config(repo.coga_os))
    ticket = Ticket.parse(rewrite.text)
    assert ticket.workflow["enter"] == "git/ticket-enter"
    assert ticket.workflow["exit"] == "git/ticket-exit"
    assert [s["name"] for s in ticket.workflow["steps"]] == ["implement", "review"]
    assert ticket.step == "1 (implement)"
    assert list(ticket.workflow)[:3] == ["name", "enter", "exit"]


def test_ticket_past_open_branch_keeps_its_step(repo):
    path = _ticket(repo, "Past open branch", "old", step=3)
    rewrite = migrate.migrate_text(path.read_text(encoding="utf-8"), load_config(repo.coga_os))
    assert Ticket.parse(rewrite.text).step == "2 (review)"


def test_git_ticket_branch_is_replaced(repo):
    def edit(ticket: Ticket) -> None:
        _strip_scripts(ticket)
        ticket.frontmatter["workflow"] = {"name": "new", "git": "ticket-branch",
                                          **{k: v for k, v in ticket.workflow.items() if k != "name"}}

    path = _ticket(repo, "Git mode", "new", step=1, edit=edit)
    rewrite = migrate.migrate_text(path.read_text(encoding="utf-8"), load_config(repo.coga_os))
    wf = Ticket.parse(rewrite.text).workflow
    assert "git" not in wf
    assert (wf["enter"], wf["exit"]) == ("git/ticket-enter", "git/ticket-exit")


def test_snapshot_lacking_its_definitions_scripts_gains_them(repo):
    path = _ticket(repo, "Older snapshot", "new", step=2, edit=_strip_scripts)
    text = path.read_text(encoding="utf-8")
    rewrite = migrate.migrate_text(text, load_config(repo.coga_os))
    ticket = Ticket.parse(rewrite.text)
    assert ticket.workflow["enter"] == "git/ticket-enter"
    assert ticket.step == "2 (review)"
    # Only the two lines are added; the rest of the ticket is byte-identical.
    added = [line for line in rewrite.text.splitlines() if line not in text.splitlines()]
    assert added == ["  enter: git/ticket-enter", "  exit: git/ticket-exit"]


@pytest.mark.parametrize("case", ["done", "canceled", "migrated", "plain"])
def test_tickets_that_need_no_change_are_left_alone(repo, case):
    if case in ("done", "canceled"):
        path = _ticket(repo, f"Finished {case}", "old", step=2, edit=_set_status(case))
    elif case == "migrated":
        path = _ticket(repo, "Already migrated", "new", step=1)
    else:
        path = _ticket(repo, "No branch", "plain", step=1)
    assert migrate.migrate_text(path.read_text(encoding="utf-8"), load_config(repo.coga_os)) is None


def test_report_only_pushes_nothing(repo, capsys):
    _ticket(repo, "At open branch", "old", step=1)
    _seed(repo)
    before = repo.git("rev-parse", "origin/main").strip()
    assert migrate.main([]) == 0
    printed = capsys.readouterr().out
    assert "removed `open-branch`" in printed
    assert "rerun with --apply" in printed
    repo.git("fetch", "-q", "origin")
    assert repo.git("rev-parse", "origin/main").strip() == before


def test_apply_publishes_only_the_rewritten_tickets_from_the_base(repo):
    migrated = _ticket(repo, "At open branch", "old", step=1)
    untouched = _ticket(repo, "No branch", "plain", step=1)
    _seed(repo)
    # Local edits and unpushed commits stay local: the commit is built from
    # the remote base, not the work tree.
    untouched_text = untouched.read_text(encoding="utf-8")
    untouched.write_text(untouched_text + "\nlocal note\n", encoding="utf-8")
    (repo.root / "local.txt").write_text("x\n", encoding="utf-8")
    repo.git("add", "local.txt")
    repo.git("commit", "-qm", "local only")
    parent = repo.git("rev-parse", "origin/main").strip()

    assert migrate.main(["--apply"]) == 0

    repo.git("fetch", "-q", "origin")
    head = repo.git("rev-parse", "origin/main").strip()
    assert repo.git("rev-parse", f"{head}^").strip() == parent
    rel = migrated.resolve().relative_to(repo.root.resolve()).as_posix()
    assert repo.git("diff", "--name-only", parent, head).split() == [rel]
    assert Ticket.parse(repo.git("show", f"{head}:{rel}")).step == "1 (implement)"
    assert untouched.read_text(encoding="utf-8").endswith("local note\n")
    # A second run finds nothing left to do.
    assert migrate.main([]) == 0


def test_path_rewrites_one_work_tree_ticket_in_place(repo, capsys):
    path = _ticket(repo, "Live copy", "old", step=2)
    assert migrate.main(["--path", str(path)]) == 0
    assert Ticket.read(path).step == "1 (implement)"
    assert migrate.main(["--path", str(path)]) == 0
    assert "needs no change" in capsys.readouterr().out
