"""`python -m coga_edge.migrate_step_scripts` rewrites in-flight branch tickets."""

from __future__ import annotations

import os

import pytest

from coga.blackboard import set_dev_fields
from coga.config import load_config
from coga.create import create_task
from coga.taskfile import read_blackboard, replace_blackboard
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
            edit=None, force_directory: bool = False):  # type: ignore[no-untyped-def]
    cfg = load_config(repo.coga_os)
    created = create_task(
        cfg=cfg, title=title, workflow_name=workflow, contexts=[],
        owner=cfg.current_user, agent=cfg.default_agent().name, status=status,
        force_directory=force_directory,
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


def _advance_legacy_branch(repo, path, *, base="main"):
    repo.git("switch", "-c", "legacy")
    ticket = Ticket.read(path)
    ticket.frontmatter.update(status="in_progress", step="3 (review)")
    ticket.write(path)
    replace_blackboard(
        path, set_dev_fields(read_blackboard(path), branch="legacy", base=base, remote="origin"),
    )
    slug = "legacy-branch"
    with (repo.coga_os / "log.md").open("a", encoding="utf-8") as stream:
        stream.write(f"2026-11-25 14:00 v1 [{slug}] [system] advanced from the branch\n")
        stream.write("2026-11-25 14:00 v1 [unrelated] [system] unrelated note\n")
    (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
    if path.name == "ticket.md":
        (path.parent / "old.txt").unlink()
        (path.parent / "new.txt").write_text("new attachment\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-qm", "Advance a legacy branch ticket")
    repo.git("push", "-q", "origin", "legacy")
    repo.git("switch", "main")


@pytest.mark.parametrize("directory", [False, True])
def test_migration_moves_live_branch_state_and_keeps_only_code_in_pr(repo, directory):
    path = _ticket(repo, "Legacy branch", "old", step=1, force_directory=directory)
    rel = path.relative_to(repo.root).as_posix()
    if directory:
        (path.parent / "old.txt").write_text("old attachment\n", encoding="utf-8")
    _seed(repo)
    _advance_legacy_branch(repo, path)
    old_branch = repo.git("rev-parse", "origin/legacy").strip()
    old_base = repo.git("rev-parse", "origin/main").strip()

    assert migrate.main(["--apply"]) == 0

    live = Ticket.parse(repo.git("show", f"origin/main:{rel}"))
    assert live.status == "in_progress"
    assert live.step == "2 (review)"
    assert live.workflow["enter"] == "git/ticket-enter"
    assert repo.git("rev-parse", "origin/legacy^").strip() == old_branch
    assert repo.git("rev-parse", "origin/main^").strip() == old_base
    assert repo.git("rev-parse", "legacy").strip() == repo.git("rev-parse", "origin/legacy").strip()
    assert repo.git("diff", "--name-only", "origin/main...origin/legacy").splitlines() == [
        "feature.txt",
    ]
    log = repo.git("show", "origin/main:coga/log.md")
    assert "[legacy-branch] [system] advanced from the branch" in log
    assert "unrelated note" not in log
    if directory:
        prefix = path.parent.relative_to(repo.root).as_posix()
        assert repo.git("show", f"origin/main:{prefix}/new.txt") == "new attachment\n"
        assert "old.txt" not in repo.git("ls-tree", "origin/main", f"{prefix}/")
    assert migrate.main([]) == 0


@pytest.mark.parametrize("case", ["different base", "changed base"])
def test_migration_refuses_ambiguous_live_branch_state(repo, capsys, case):
    path = _ticket(repo, "Legacy branch", "old", step=1)
    _seed(repo)
    _advance_legacy_branch(repo, path, base="missing" if case == "different base" else "main")
    if case == "changed base":
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\nA newer note on the base.\n")
        _seed(repo)
    old_base = repo.git("rev-parse", "origin/main")
    old_branch = repo.git("rev-parse", "origin/legacy")

    assert migrate.main(["--apply"]) == 1
    error = capsys.readouterr().err
    assert ("recorded base 'missing'" if case == "different base" else "both the base") in error
    assert repo.git("rev-parse", "origin/main") == old_base
    assert repo.git("rev-parse", "origin/legacy") == old_branch


def test_migration_keeps_both_remote_refs_if_the_branch_update_is_rejected(repo):
    path = _ticket(repo, "Legacy branch", "old", step=1)
    _seed(repo)
    _advance_legacy_branch(repo, path)
    old_base = repo.git("rev-parse", "main", cwd=repo.origin)
    old_branch = repo.git("rev-parse", "legacy", cwd=repo.origin)
    hook = repo.origin / "hooks" / "update"
    hook.write_text(
        '#!/bin/sh\n[ "$1" != refs/heads/legacy ]\n', encoding="utf-8",
    )
    hook.chmod(0o755)

    assert migrate.main(["--apply"]) == 1
    assert repo.git("rev-parse", "main", cwd=repo.origin) == old_base
    assert repo.git("rev-parse", "legacy", cwd=repo.origin) == old_branch
