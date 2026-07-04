"""Cross-worktree divergence detection (`task_live_in_other_worktrees`).

Coga has no filesystem mutex — ticket `status` is a git-tracked file, so the
same ticket worked in two worktrees at once diverges silently (the failure this
repo hit). The helper reads each *other* worktree's copy of the same ticket and
reports where it is already live, so `coga ticket` can refuse to fork it.
"""

from __future__ import annotations

from pathlib import Path

from conftest import GitRepo
from coga.config import load_config
from coga.tasks import resolve_task, task_live_in_other_worktrees
from coga.ticket import Ticket


def _seed_task(repo: GitRepo, status: str = "active") -> Path:
    ticket = repo.coga_os / "tasks" / "shared-task.md"
    ticket.parent.mkdir(parents=True, exist_ok=True)
    ticket.write_text(
        "---\n"
        "slug: shared-task\n"
        "title: Shared task\n"
        f"status: {status}\n"
        "mode: agent\n"
        "owner: marc\n"
        "assignee: claude\n"
        "workflow:\n"
        "  name: code\n"
        "  steps:\n"
        "  - name: implement\n"
        "    skills: []\n"
        "    assignee: agent\n"
        "step: 1 (implement)\n"
        "---\n\n"
        "## Description\n\nwork\n\n"
        "<!-- coga:blackboard -->\n\nnotes\n"
    )
    repo.git("add", "-A")
    repo.git("commit", "-m", "seed shared-task")
    return ticket


def test_detects_same_ticket_in_progress_in_other_worktree(git_repo: GitRepo) -> None:
    _seed_task(git_repo, status="active")

    # A second worktree on a feature branch flips the shared ticket to
    # in_progress — the exact "same ticket, two branches" divergence.
    wt = git_repo.root.parent / "wt-b"
    git_repo.git("worktree", "add", "-b", "branch-b", str(wt), "main")
    other = wt / "coga" / "tasks" / "shared-task.md"
    t = Ticket.read(other)
    t.frontmatter["status"] = "in_progress"
    t.write(other)

    cfg = load_config(git_repo.coga_os)
    ref = resolve_task(cfg, "shared-task")
    hits = task_live_in_other_worktrees(cfg, ref)

    assert len(hits) == 1
    path, branch, status = hits[0]
    assert branch == "branch-b"
    assert status == "in_progress"
    assert Path(path).resolve() == wt.resolve()


def test_no_hit_when_other_worktree_is_not_live(git_repo: GitRepo) -> None:
    _seed_task(git_repo, status="active")

    # Second worktree exists but its copy stays active — not a collision.
    wt = git_repo.root.parent / "wt-idle"
    git_repo.git("worktree", "add", "-b", "idle", str(wt), "main")

    cfg = load_config(git_repo.coga_os)
    ref = resolve_task(cfg, "shared-task")
    assert task_live_in_other_worktrees(cfg, ref) == []


def test_current_worktree_in_progress_is_not_a_hit(git_repo: GitRepo) -> None:
    # The current checkout being in_progress is normal (resume) — the helper
    # reports only *other* worktrees, never itself.
    _seed_task(git_repo, status="in_progress")
    cfg = load_config(git_repo.coga_os)
    ref = resolve_task(cfg, "shared-task")
    assert task_live_in_other_worktrees(cfg, ref) == []
