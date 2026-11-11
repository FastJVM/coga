"""Tests for `coga.git` — one `publish`, one `refresh`, no local commits.

Each test is named after the guarantee it pins (the acceptance list of
`simplify-git-sync`): control is canonical and local `main` only ever
fast-forwards; an offline write stays dirty and is retried by the sweep; a
stale same-ticket write is refused with the `git checkout origin/main -- …`
hint while different tickets from one base both land; `coga/log.md` is
union-merged; a pending megalaunch claim is sealed; `refresh` fast-forwards a
control checkout and leaves a feature checkout alone; the sweep publishes
every eligible file under the Coga and contexts roots and nothing else.

Real git throughout, via the `git_repo` fixture in conftest (a working tree
with a bare `origin`); `real_git` opts a non-repo test out of the suite-wide
stub.
"""

from __future__ import annotations

import itertools
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import replace
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import remove_test_checkout, windows_skip, write_executable
from typer.testing import CliRunner

from coga import git
from coga.cli import app
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log, log_path
from coga.ticket import Ticket

from conftest import init_git_repo

runner = CliRunner()


# --- helpers -------------------------------------------------------------------


def _cfg(repo_root: Path, **over) -> Config:
    """Minimal Config for unit tests that only touch the git fields."""
    base: dict = dict(
        repo_root=repo_root,
        current_user="marc",
        default_status="draft",
        agents={},
        slack_webhook=None,
        slack_enabled=False,
    )
    base.update(over)
    return Config(**base)


def _global_log(cfg: Config) -> str:
    log = cfg.repo_root / "log.md"
    return log.read_text(encoding="utf-8") if log.is_file() else ""


def _ticket_text(
    *,
    status: str = "in_progress",
    step: str = "1 (implement)",
    blackboard: str = "notes\n",
    generation: str | None = None,
) -> str:
    head = dedent(f"""
        ---
        title: demo
        status: {status}
        owner: marc
        agent: claude
        workflow:
          name: code
          steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: agent
        step: {step}
        ---

        ## Description

        Demo.

        <!-- coga:blackboard -->

    """).lstrip()
    ticket = Ticket.parse(head + blackboard)
    if generation is not None:
        ticket.frontmatter["launch_generation"] = generation
    if status in {"done", "canceled"}:
        ticket.frontmatter.pop("step", None)
    return ticket.render()


def _seed_ticket(git_repo, slug: str = "demo", **kwargs) -> Path:
    """Write a file-form ticket, commit it, push it, and return its path."""
    path = git_repo.coga_os / "tasks" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ticket_text(**kwargs), encoding="utf-8", newline="\n")
    git_repo.git("add", "--", f"coga/tasks/{slug}.md")
    git_repo.git("commit", "-m", f"seed {slug}")
    git_repo.git("push", "origin", "main")
    return path


def _control(git_repo, rel: str) -> str | None:
    """`rel` as committed on `origin/main`, or None when absent there."""
    if rel not in git_repo.git(
        "ls-tree", "-r", "--name-only", "main", cwd=git_repo.origin
    ).splitlines():
        return None
    return git_repo.git("show", f"main:{rel}", cwd=git_repo.origin)


@pytest.mark.parametrize("tracked_executable", [False, True])
def test_publication_preserves_git_modes_and_can_prepare_checkout(
    git_repo, tracked_executable: bool,
):
    cfg = load_config(git_repo.coga_os)
    path = _seed_ticket(git_repo)
    rel = "coga/tasks/demo.md"
    if tracked_executable:
        if os.name == "posix":
            path.chmod(0o755)
        git_repo.git("update-index", "--chmod=+x", rel)
        git_repo.git("commit", "-m", "executable fixture")
        git_repo.git("push", "origin", "main")
    git_repo.git("checkout", "-b", "feature")
    path.write_text(_ticket_text(blackboard="Café 東京\n"), encoding="utf-8", newline="\n")
    new_path = git_repo.coga_os / "tasks" / "new.md"
    new_path.write_text(_ticket_text(), encoding="utf-8", newline="\n")

    assert git.publish(cfg, [path, new_path], "publish modes")

    expected_mode = "100755" if tracked_executable else "100644"
    assert git_repo.git("ls-tree", "origin/main", rel).startswith(expected_mode + " ")
    assert git_repo.git("ls-tree", "origin/main", "coga/tasks/new.md").startswith("100644 ")
    result = git.prepare_control_checkout(cfg)
    assert result.kind != "refused", result
    assert git_repo.git("status", "--porcelain") == ""


def _dirty(git_repo, cwd: Path | None = None) -> set[str]:
    out = git_repo.git("status", "--porcelain", "--untracked-files=all", cwd=cwd)
    return {line[3:] for line in out.splitlines()}


def _ahead_of_origin(git_repo) -> int:
    return int(git_repo.git("rev-list", "--count", "origin/main..main").strip())


def _clone(git_repo, name: str) -> Path:
    """A second checkout of the same origin, on `main`, with a local config."""
    clone = git_repo.origin.parent / name
    git_repo.git("clone", str(git_repo.origin), str(clone), cwd=git_repo.origin.parent)
    for key, value in (
        ("user.email", "peer@example.com"),
        ("user.name", "Peer"),
        ("commit.gpgsign", "false"),
    ):
        git_repo.git("config", key, value, cwd=clone)
    git_repo.git("checkout", "-B", "main", "origin/main", cwd=clone)
    shutil.copy(git_repo.coga_os / "coga.local.toml", clone / "coga")
    return clone


def _write_config(tmp_path: Path, *, shared_extra: str = "", local_extra: str = "") -> Path:
    root = tmp_path / "coga"
    root.mkdir()
    (root / "coga.toml").write_text(f"version = 1\n{shared_extra}", encoding="utf-8", newline="\n")
    (root / "coga.local.toml").write_text(f'user = "marc"\n{local_extra}', encoding="utf-8", newline="\n")
    return root


# --- [git] config ---------------------------------------------------------------


def test_git_config_defaults(tmp_path):
    cfg = load_config(_write_config(tmp_path))
    assert cfg.git_enabled is True
    assert cfg.git_remote == "origin"
    assert cfg.git_control_branch == "main"


def test_git_config_overrides(tmp_path):
    cfg = load_config(
        _write_config(
            tmp_path,
            shared_extra='[git]\nremote = "upstream"\ncontrol_branch = "trunk"\n',
        )
    )
    assert cfg.git_remote == "upstream"
    assert cfg.git_control_branch == "trunk"


def test_git_enabled_local_overrides_shared(tmp_path):
    cfg = load_config(
        _write_config(
            tmp_path,
            shared_extra="[git]\nenabled = true\n",
            local_extra="[git]\nenabled = false\n",
        )
    )
    assert cfg.git_enabled is False


def test_git_enabled_must_be_bool(tmp_path):
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_config(_write_config(tmp_path, shared_extra='[git]\nenabled = "yes"\n'))


def test_git_remote_must_be_nonempty(tmp_path):
    with pytest.raises(ConfigError, match="remote must be a non-empty string"):
        load_config(_write_config(tmp_path, shared_extra='[git]\nremote = ""\n'))


# --- canonical: control is the only durable home, local main only fast-forwards


def test_publish_lands_on_control_and_never_commits_locally(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    append_log(cfg, "demo", "agent:claude", "advanced to step 2 (review)")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — step 2") is True

    assert "step: 2 (review)" in _control(git_repo, "coga/tasks/demo.md")
    assert "advanced to step 2" in _control(git_repo, "coga/log.md")
    assert git_repo.origin_subjects()[0] == "Ticket: demo — step 2"
    # The checkout fast-forwarded to the published commit: nothing ahead,
    # nothing dirty, no stash.
    assert _ahead_of_origin(git_repo) == 0
    assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
        "rev-parse", "main", cwd=git_repo.origin
    ).strip()
    assert _dirty(git_repo) == set()
    assert git_repo.git("stash", "list") == ""


def test_publish_from_feature_checkout_lands_on_control_and_leaves_branch_alone(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    feature_tip = git_repo.git("rev-parse", "HEAD").strip()
    (git_repo.root / "wip.py").write_text("# half-written\n", encoding="utf-8", newline="\n")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is True

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert not git_repo.origin_tracks("wip.py")
    # No commit on the feature branch; the live ticket stays dirty there by
    # design, and the (unheld) local `main` was moved to the new control tip.
    assert git_repo.git("rev-parse", "HEAD").strip() == feature_tip
    assert _dirty(git_repo) == {"coga/tasks/demo.md", "wip.py"}
    assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
        "rev-parse", "main", cwd=git_repo.origin
    ).strip()


def test_publish_reports_nothing_to_publish_for_a_clean_task(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    before = git_repo.origin_subjects()

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — noop") is False
    assert git_repo.origin_subjects() == before


def test_publish_carries_a_task_directory_with_attachments(git_repo):
    cfg = load_config(git_repo.coga_os)
    task = git_repo.coga_os / "tasks" / "dir-form"
    task.mkdir(parents=True)
    (task / "ticket.md").write_text(_ticket_text(), encoding="utf-8", newline="\n")
    (task / "notes.md").write_text("attachment\n", encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, task, message="Ticket: dir-form — created") is True

    assert _control(git_repo, "coga/tasks/dir-form/ticket.md") is not None
    assert _control(git_repo, "coga/tasks/dir-form/notes.md") == "attachment\n"
    assert _dirty(git_repo) == set()


def test_publish_lands_a_deletion(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.unlink()

    assert git.publish(cfg, [ticket], "Ticket: demo — deleted") is True
    assert _control(git_repo, "coga/tasks/demo.md") is None
    assert _dirty(git_repo) == set()


def test_publish_without_fast_forward_leaves_the_control_checkout_alone(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    tip = git_repo.git("rev-parse", "main").strip()
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", fast_forward=False) is True

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "main").strip() == tip
    assert _dirty(git_repo) == {"coga/tasks/demo.md"}


def test_publish_with_no_remote_commits_on_local_control_only(git_repo, capsys):
    """The stated I1 exception: no remote means local `main` is canonical."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.git("remote", "remove", "origin")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is True

    assert "no 'origin' remote configured" in capsys.readouterr().err
    assert git_repo.git("log", "-1", "--format=%s", "main").strip() == "Ticket: demo — blocked"
    assert "status: blocked" in git_repo.git("show", "main:coga/tasks/demo.md")
    assert _dirty(git_repo) == set()


def test_publish_with_no_remote_fails_when_local_control_cannot_advance(
    git_repo, tmp_path, capsys
):
    """With no remote, local control is the only durable destination: a
    refused fast-forward is a failed publish, not a dangling commit."""
    ticket = _seed_ticket(git_repo)
    git_repo.git("remote", "remove", "origin")
    tip = git_repo.git("rev-parse", "main").strip()
    # The primary checkout holds `main` with conflicting dirty state, so the
    # feature worktree's publish cannot `merge --ff-only` it forward.
    ticket.write_text(_ticket_text(status="paused"), encoding="utf-8", newline="\n")
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
        written = wt_ticket.read_bytes()
        assert git.sync_task_state(
            load_config(worktree / "coga"), wt_ticket, message="Ticket: demo — blocked"
        ) is None
        assert wt_ticket.read_bytes() == written
        assert _dirty(git_repo, cwd=worktree) >= {"coga/tasks/demo.md"}
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))
        git_repo.git("branch", "-D", "feature/wt")

    err = capsys.readouterr().err
    assert "sync failed" in err
    assert "could not be fast-forwarded" in err
    assert git_repo.git("rev-parse", "main").strip() == tip
    assert "status: paused" in ticket.read_text(encoding="utf-8")


def test_publish_refuses_a_symlinked_task_file(git_repo, tmp_path, capsys):
    """`read_bytes` follows links: publishing one would land its target's
    bytes — possibly from outside the repo — on control as a regular file."""
    cfg = load_config(git_repo.coga_os)
    secret = tmp_path / "outside.md"
    secret.write_text("token = do-not-publish\n", encoding="utf-8", newline="\n")
    link = git_repo.coga_os / "tasks" / "linked.md"
    link.symlink_to(secret)

    assert git.sync_task_state(cfg, link, message="Ticket: linked") is None

    assert "is a symlink" in capsys.readouterr().err
    assert _control(git_repo, "coga/tasks/linked.md") is None
    assert not git_repo.origin_tracks("coga/tasks/linked.md")
    assert link.is_symlink()


def test_publish_refuses_to_delete_a_missing_union_merged_log(git_repo, capsys):
    """A missing `coga/log.md` skips the union merge; its deletion must be
    refused rather than published as the loss of the audit history."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    append_log(cfg, "demo", "human:marc", "history line")
    git_repo.git("add", "--", "coga/log.md")
    git_repo.git("commit", "-m", "seed log")
    git_repo.git("push", "origin", "main")
    (git_repo.coga_os / "log.md").unlink()
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is None

    err = capsys.readouterr().err
    assert "sync refused" in err
    assert "coga/log.md: append-only file is missing locally" in err
    assert "git checkout origin/main -- coga/log.md" in err
    assert "history line" in _control(git_repo, "coga/log.md")
    # Nothing landed, and the refusal did not recreate a one-line log.
    assert "status: in_progress" in _control(git_repo, "coga/tasks/demo.md")
    assert not (git_repo.coga_os / "log.md").exists()


# --- nothing is lost: offline writes stay dirty and the sweep retries them -----


def test_offline_publish_leaves_the_write_dirty_and_the_sweep_retries_it(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    url = git_repo.git("remote", "get-url", "origin").strip()
    git_repo.git("remote", "set-url", "origin", str(git_repo.origin.parent / "missing.git"))
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    written = ticket.read_bytes()

    # Exits 0 (returns), reports once, keeps the file exactly as written.
    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is None
    assert capsys.readouterr().err.count("sync failed") == 1
    assert _global_log(cfg).count("sync failed") == 1
    assert ticket.read_bytes() == written
    assert _dirty(git_repo) == {"coga/tasks/demo.md", "coga/log.md"}
    assert _ahead_of_origin(git_repo) == 0

    # The remote comes back: the next command's sweep publishes it.
    git_repo.git("remote", "set-url", "origin", url)
    git.sync_coga_state(cfg)

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert "sync failed" in _control(git_repo, "coga/log.md")
    assert _dirty(git_repo) == set()


def test_a_push_accepted_before_the_connection_dropped_counts_as_published(
    git_repo, monkeypatch
):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    real_push = git._push

    def push_then_lose_the_ack(root, remote, refspec):  # type: ignore[no-untyped-def]
        assert real_push(root, remote, refspec) is None
        return "fatal: the remote end hung up unexpectedly"

    monkeypatch.setattr(git, "_push", push_then_lose_the_ack)

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked") is True
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert _dirty(git_repo) == set()


def test_a_push_failure_control_cannot_be_reread_is_uncertain(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    monkeypatch.setattr(git, "_push", lambda *a: "fatal: the remote end hung up")

    def offline_fetch(*args):  # type: ignore[no-untyped-def]
        raise git.GitError("could not resolve host")

    monkeypatch.setattr(git, "_fetch_control", offline_fetch)

    with pytest.raises(git.UncertainPublishError):
        git.publish(cfg, [ticket], "Ticket: demo — blocked")
    assert _dirty(git_repo) == {"coga/tasks/demo.md"}


# --- contention and the compare-and-swap ------------------------------------


def test_two_checkouts_publishing_different_tickets_both_land(git_repo):
    cfg = load_config(git_repo.coga_os)
    first = _seed_ticket(git_repo, "first")
    second = _seed_ticket(git_repo, "second")
    peer = _clone(git_repo, "peer")
    peer_cfg = load_config(peer / "coga")

    (peer / "coga" / "tasks" / "second.md").write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    assert git.sync_task_state(
        peer_cfg, peer / "coga" / "tasks" / "second.md", message="Ticket: second — blocked"
    ) is True
    # This checkout's base is now stale: the push is rejected once, the
    # rebuild lands on the peer's tip.
    first.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, first, message="Ticket: first — step 2") is True

    assert "step: 2 (review)" in _control(git_repo, "coga/tasks/first.md")
    assert "status: blocked" in _control(git_repo, "coga/tasks/second.md")
    assert git_repo.origin_subjects()[:2] == [
        "Ticket: first — step 2",
        "Ticket: second — blocked",
    ]
    assert _dirty(git_repo) == set()
    assert second.read_text(encoding="utf-8") == _ticket_text(status="blocked")


def test_publishing_the_same_ticket_from_a_stale_base_is_refused_with_the_fix(
    git_repo, capsys
):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    original = ticket.read_bytes()
    git_repo.push_competing_commit(
        "coga/tasks/demo.md", _ticket_text(blackboard="peer prose\n")
    )
    ticket.write_text(_ticket_text(blackboard="my prose\n"), encoding="utf-8", newline="\n")

    with pytest.raises(git.StateRegressionError) as excinfo:
        git.publish(cfg, [ticket], "Ticket: demo — blackboard")

    reason = str(excinfo.value)
    assert "control copy changed since this checkout last saw it" in reason
    assert "git checkout origin/main -- coga/tasks/demo.md" in reason
    assert "sync refused" in _global_log(cfg)
    # Nothing landed, nothing moved: the peer's prose is on control, mine is
    # still on disk, and this checkout's `main` did not advance.
    assert "peer prose" in _control(git_repo, "coga/tasks/demo.md")
    assert "my prose" in ticket.read_text(encoding="utf-8")
    assert git_repo.git("show", "HEAD:coga/tasks/demo.md").encode() == original


def test_log_appended_on_both_sides_keeps_both_lines(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    control_log = _control(git_repo, "coga/log.md") or ""
    git_repo.push_competing_commit(
        "coga/log.md", control_log + "2026-01-01 00:00 [rival] [system] rival line\n"
    )
    append_log(cfg, "demo", "agent:claude", "my line")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is True

    landed = _control(git_repo, "coga/log.md")
    assert "rival line" in landed
    assert "my line" in landed
    # The control checkout's working log carries the union result and is clean.
    assert (git_repo.coga_os / "log.md").read_text(encoding="utf-8") == landed
    assert _dirty(git_repo) == set()


def _lines(spec: str) -> bytes:
    """`"A X"` -> `b"A\\nX\\n"`: one newline-terminated line per token."""
    return b"".join(f"{token}\n".encode() for token in spec.split())


@pytest.mark.parametrize(
    ("base", "control", "working", "landed"),
    [
        # Control already has X at another position: it is not re-added.
        ("A", "A X Y", "A Z X", "A X Y Z"),
        # Concurrent appends from the same base both land once.
        ("A", "A P", "A M", "A P M"),
        # A control line the base never saw comes back.
        ("A", "A L", "A Z", "A L Z"),
        # A deletion the base saw still lands.
        ("A L B", "A L B", "A B", "A B"),
        # A clean move keeps raw-merge order.
        ("A L B", "A L B", "A B L", "A B L"),
        # Repeated lines: no side deleted anything, so every control line stays.
        ("A C A C", "A C A C A", "A C B A C", "A C B A C A"),
        # A clean partial deletion of a historical duplicate still lands.
        ("A X X", "A X X", "A X", "A X"),
        # No merge-base: lines control has anywhere are not re-added.
        ("", "A X", "Q A X Z", "A X Q Z"),
    ],
)
def test_union_merge_never_re_adds_a_control_line(base, control, working, landed, tmp_path):
    merged = git._merge_union_bytes(
        current=_lines(control), base=_lines(base), other=_lines(working),
        scratch=tmp_path,
    )
    assert merged == _lines(landed)


def _is_subsequence(needle: list[bytes], haystack: list[bytes]) -> bool:
    remaining = iter(haystack)
    return all(line in remaining for line in needle)


def test_drop_reinserted_lines_caps_counts_and_keeps_order():
    sequences = [
        [f"{token}\n".encode() for token in combo]
        for size in range(5)
        for combo in itertools.product("AB", repeat=size)
    ]
    for control, merged in itertools.product(sequences, repeat=2):
        result = git._drop_reinserted_lines(b"".join(control), b"".join(merged))
        lines = result.splitlines(keepends=True)
        have, raw, cap = Counter(lines), Counter(merged), Counter(control)
        for line in raw:
            expected = min(cap[line], raw[line]) if line in cap else raw[line]
            assert have[line] == expected, (control, merged)
        assert _is_subsequence(lines, merged), (control, merged)
        if _is_subsequence(control, merged):
            assert _is_subsequence(control, lines), (control, merged)
        assert git._drop_reinserted_lines(b"".join(control), result) == result


@pytest.mark.parametrize(
    ("current", "merged"),
    [(b"A\nX\nX\n", b"A\nX\nX\n"), (b"A", b"A\nA"), (b"A", b"AB\nA"), (b"A\n", b"A\nA")],
)
def test_drop_reinserted_lines_compares_whole_lines_with_their_ends(current, merged):
    assert git._drop_reinserted_lines(current, merged) == merged


def test_drop_reinserted_lines_splits_only_at_lf():
    """A bare CR is content inside a Git line, never a line boundary."""
    assert git._drop_reinserted_lines(b"A\rB\n", b"A\rB\nC\rB\n") == b"A\rB\nC\rB\n"


def test_union_publish_caps_control_lines_after_clean_filtering(git_repo):
    """Under `core.autocrlf=true` the working log is CRLF while control's
    blob is LF; the cap must compare the clean-filtered copy, or a line
    already on control lands twice once `git add` normalizes it."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("config", "core.autocrlf", "true")
    git_repo.checkout_branch("feature/x")
    append_log(cfg, "demo", "agent:claude", "first line")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True
    log = git.log_path(cfg)
    log.write_bytes(log.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    append_log(cfg, "demo", "agent:claude", "second line")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True

    landed = _control(git_repo, "coga/log.md")
    assert landed.count("first line") == 1
    assert "second line" in landed


# --- publication scratch files live in the Git dir, not $TMPDIR ---------------


def _scratch_leftovers(git_dir: Path) -> list[str]:
    return sorted(
        entry.name for entry in git_dir.iterdir()
        if entry.name.startswith(("coga-git-index-", "coga-union-merge-"))
    )


def _union_worklist(git_repo) -> Path:
    """A `merge=union` worklist (not the log, which publishes through its own
    reconciler) that control and this checkout each appended to."""
    attributes = git_repo.coga_os / ".gitattributes"
    attributes.write_text(
        attributes.read_text(encoding="utf-8") + "**/retires.md merge=union\n",
        encoding="utf-8", newline="\n",
    )
    git_repo.git("add", "coga/.gitattributes")
    rel = "coga/recurring/weekly/retires.md"
    _hand_commit(git_repo, rel, "A\n")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit(rel, "A\nP\n")
    git_repo.git("fetch", "--quiet", "origin")
    worklist = git_repo.root / rel
    worklist.write_text("A\nM\n", encoding="utf-8", newline="\n")
    return worklist


def test_publication_scratch_files_never_touch_the_temp_dir(git_repo, monkeypatch, tmp_path):
    """The 2026-10-27 ENOSPC: a full `/tmp` failed a publish at its temporary
    index. Tree construction, the published-blob record, and both union
    merge callers now work with no usable temp dir at all."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    worklist = _union_worklist(git_repo)
    git_repo.checkout_branch("feature/x")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    git_dir = Path(git_repo.git("rev-parse", "--absolute-git-dir").strip())
    real_merge = git._merge_union_bytes
    scratches: list[Path] = []

    def merge(**kwargs):  # type: ignore[no-untyped-def]
        scratches.append(kwargs["scratch"])
        return real_merge(**kwargs)

    monkeypatch.setattr(git, "_merge_union_bytes", merge)
    missing = tmp_path / "no-such-tmp"
    # The state lock lives in the temp dir and is out of scope here; hold it
    # (it is reentrant) before the temp dir disappears.
    with git.state_lock(cfg):
        monkeypatch.setattr(tempfile, "tempdir", str(missing))
        assert git.publish(cfg, [ticket, worklist], "Ticket: demo — blocked") is True
        # A feature checkout keeps the published worklist dirty; returning to
        # control proves it is on control through the union proof.
        outcome = git.prepare_control_checkout(cfg)

    _assert_prepared(git_repo, outcome)
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert _control(git_repo, "coga/recurring/weekly/retires.md") == "A\nP\nM\n"
    assert len(scratches) >= 2 and set(scratches) == {git_dir}
    assert not missing.exists()
    assert _scratch_leftovers(git_dir) == []


def test_publication_scratch_is_per_worktree_and_removed_on_failure(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    linked = git_repo.root.parent / "linked"
    git_repo.git("worktree", "add", "--quiet", "-b", "feature/x", str(linked))
    own = Path(git_repo.git("rev-parse", "--absolute-git-dir", cwd=linked).strip())
    assert own != git_repo.root / ".git" and own.parent.name == "worktrees"
    assert git._scratch_dir(linked) == own

    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    real_run_git = git.run_git

    def failing_write_tree(root, *args, **kwargs):  # type: ignore[no-untyped-def]
        if args[:1] == ("write-tree",):
            assert _scratch_leftovers(git_repo.root / ".git"), "index not in the Git dir"
            raise git.GitError("injected write-tree failure")
        return real_run_git(root, *args, **kwargs)

    monkeypatch.setattr(git, "run_git", failing_write_tree)
    git.sync_coga_state(cfg)

    assert "status: in_progress" in _control(git_repo, "coga/tasks/demo.md")
    assert _scratch_leftovers(git_repo.root / ".git") == []
    assert _scratch_leftovers(own) == []


def test_unwritable_scratch_dir_fails_publication_as_git_error(git_repo, monkeypatch, capsys):
    """A sandbox's read-only `.git` with a pending deletion: the provenance
    guard writes no blob, so scratch allocation is the first write. Its
    `OSError` must surface as `GitError`, which the sync wrappers report."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.unlink()
    git_dir = Path(git_repo.git("rev-parse", "--absolute-git-dir").strip())
    real_mkstemp = tempfile.mkstemp
    real_tempdir = tempfile.TemporaryDirectory

    def read_only(dir):  # type: ignore[no-untyped-def]
        if dir is not None and Path(dir) == git_dir:
            raise PermissionError(13, "Permission denied", str(dir))

    def mkstemp(*args, dir=None, **kwargs):  # type: ignore[no-untyped-def]
        read_only(dir)
        return real_mkstemp(*args, dir=dir, **kwargs)

    def temporary_directory(*args, dir=None, **kwargs):  # type: ignore[no-untyped-def]
        read_only(dir)
        return real_tempdir(*args, dir=dir, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", mkstemp)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", temporary_directory)

    with pytest.raises(git.GitError, match="scratch index"):
        git.publish(cfg, [ticket], "Ticket: demo — deleted")
    with pytest.raises(git.GitError, match="union-merge scratch"):
        git._merge_union_bytes(current=b"A\n", base=b"", other=b"B\n", scratch=git_dir)

    capsys.readouterr()
    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — deleted") is None
    git.sync_coga_state(cfg)
    assert "sync failed" in capsys.readouterr().err
    assert _control(git_repo, "coga/tasks/demo.md") is not None
    assert not ticket.exists()


def test_expect_pins_the_exact_control_copy(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    read = ticket.read_bytes()
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", expect={ticket: read}) is True

    # A second writer holding the same pre-write bytes loses.
    ticket.write_text(_ticket_text(status="paused"), encoding="utf-8", newline="\n")
    with pytest.raises(git.StateRegressionError):
        git.publish(cfg, [ticket], "Ticket: demo — paused", expect={ticket: read})
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")


def test_expect_none_means_the_path_must_not_exist_on_control(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo, "taken")
    new = git_repo.coga_os / "tasks" / "taken.md"
    new.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    with pytest.raises(git.StateRegressionError):
        git.publish(cfg, [new], "Ticket: taken — created", expect={new: None})


def test_guard_sees_every_base_the_publish_pushes_on(git_repo, monkeypatch):
    """`guard` runs before each attempt with the control commit it builds on —
    re-fetched after a rejected push — so a decision that depends on control's
    *content* (not one blob) is re-made against the tip that actually wins."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    stale = git_repo.git("rev-parse", "refs/remotes/origin/main").strip()
    git_repo.push_competing_commit("coga/log.md", "peer line\n")
    tip = git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    bases: list[str] = []

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", guard=bases.append) is True

    assert bases == [stale, tip]
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")


def test_guard_refusal_lands_nothing_and_leaves_the_write_dirty(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    before = git_repo.origin_subjects()
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    def refuse(base: str) -> None:
        raise git.StateRegressionError(f"not on {base[:7]}")

    with pytest.raises(git.StateRegressionError, match="not on"):
        git.publish(cfg, [ticket], "Ticket: demo — blocked", guard=refuse)

    assert git_repo.origin_subjects() == before
    assert "status: blocked" not in (_control(git_repo, "coga/tasks/demo.md") or "")
    assert ticket.read_text(encoding="utf-8") == _ticket_text(status="blocked")


def test_a_feature_checkout_keeps_publishing_its_own_ticket(git_repo):
    """Its HEAD never advances with control; its own publishes are provenance."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")

    ticket.write_text(_ticket_text(status="in_progress", blackboard="first\n"), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, ticket, message="one") is True
    ticket.write_text(_ticket_text(step="2 (review)", blackboard="first\nsecond\n"), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, ticket, message="two") is True

    assert "step: 2 (review)" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "-q", "--verify", git.PUBLISHED_REF).strip()


# --- the launch-claim seal ----------------------------------------------------


def test_pending_claim_on_control_accepts_only_its_own_admission(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo, generation="pending:abc")

    # A bump from a checkout that read the pending copy is sealed out …
    ticket.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    with pytest.raises(git.StateRegressionError, match="pending launch admission"):
        git.publish(cfg, [ticket], "Ticket: demo — step 2")
    assert "sync refused" in _global_log(cfg)

    # … while the exact prefix-stripped admission lands.
    ticket.write_text(_ticket_text(generation="abc"), encoding="utf-8", newline="\n")
    assert git.publish(cfg, [ticket], "Ticket: demo — launch admitted") is True
    assert "launch_generation: abc" in _control(git_repo, "coga/tasks/demo.md")


def test_a_released_witness_is_never_published(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo, generation="pending:abc")
    ticket.write_text(_ticket_text(generation="released:abc"), encoding="utf-8", newline="\n")

    with pytest.raises(git.StateRegressionError, match="released launch witness"):
        git.publish(cfg, [ticket], "Ticket: demo — released")
    git.sync_coga_state(cfg)
    assert "pending:abc" in _control(git_repo, "coga/tasks/demo.md")


def test_ticket_regression_reason_rules():
    pending = _ticket_text(generation="pending:abc").encode()
    admitted = _ticket_text(generation="abc").encode()
    bumped = _ticket_text(step="2 (review)").encode()
    released = _ticket_text(generation="released:abc").encode()
    assert git.ticket_regression_reason("t", control=pending, working=admitted) is None
    assert git.ticket_regression_reason("t", control=pending, working=pending) is None
    assert "pending launch admission" in git.ticket_regression_reason(
        "t", control=pending, working=bumped
    )
    assert "released launch witness" in git.ticket_regression_reason(
        "t", control=None, working=released
    )
    assert git.ticket_regression_reason("t", control=None, working=bumped) is None
    assert git.ticket_regression_reason("t", control=admitted, working=bumped) is None


# --- fast_forward_control and refresh ------------------------------------------


@pytest.mark.parametrize("tracked", [True, False], ids=["tracked", "untracked"])
def test_fast_forward_names_files_that_local_changes_would_overwrite(
    git_repo, capsys, tracked
):
    cfg = load_config(git_repo.coga_os)
    rel = "coga/log.md"
    path = git_repo.root / rel
    if tracked:
        path.write_text("original\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "--", rel)
        git_repo.git("commit", "-m", "seed log")
        git_repo.git("push", "origin", "main")
    tip = git_repo.git("rev-parse", "main").strip()
    path.write_text("local changes\n", encoding="utf-8", newline="\n")
    git_repo.push_competing_commit(rel, "remote changes\n")
    git_repo.git("fetch", "origin", "main")
    new = git_repo.git("rev-parse", "origin/main").strip()

    assert git.fast_forward_control(cfg, git_repo.root, new) is False

    note = capsys.readouterr().err
    assert "not fast-forwarded" in note
    assert "would be overwritten by merge:" in note
    assert rel in note
    assert path.read_text(encoding="utf-8") == "local changes\n"
    assert git_repo.git("rev-parse", "main").strip() == tip


def test_fast_forward_parses_git_output_in_a_pinned_locale(
    git_repo, monkeypatch
):
    cfg = load_config(git_repo.coga_os)
    git_repo.push_competing_commit("coga/log.md", "remote changes\n")
    git_repo.git("fetch", "origin", "main")
    new = git_repo.git("rev-parse", "origin/main").strip()
    monkeypatch.setenv("LC_ALL", "de_DE.UTF-8")
    real_run = git._run
    merge_envs = []

    def spy(argv, *, env=None, input=None):
        if "merge" in argv:
            merge_envs.append(env)
        return real_run(argv, env=env, input=input)

    monkeypatch.setattr(git, "_run", spy)

    assert git.fast_forward_control(cfg, git_repo.root, new) is True
    assert merge_envs == [git._MESSAGE_LOCALE]


def test_publish_from_a_worktree_fast_forwards_the_main_checkout(git_repo, tmp_path):
    ticket = _seed_ticket(git_repo)
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
        assert git.sync_task_state(
            load_config(worktree / "coga"), wt_ticket, message="Ticket: demo — blocked"
        ) is True

        # The primary checkout holding `main` advanced: ref, index, and file.
        assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
            "rev-parse", "main", cwd=git_repo.origin
        ).strip()
        assert "status: blocked" in ticket.read_text(encoding="utf-8")
        assert _dirty(git_repo) == set()
        # The worktree kept its own branch and its dirty live copy.
        assert _dirty(git_repo, cwd=worktree) == {"coga/tasks/demo.md"}
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))


def test_fast_forward_leaves_an_ahead_main_alone_and_names_the_fix(
    git_repo, tmp_path, capsys
):
    ticket = _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "local.txt")
    git_repo.git("commit", "-m", "local unpushed")
    ahead_tip = git_repo.git("rev-parse", "main").strip()
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "origin/main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
        assert git.sync_task_state(
            load_config(worktree / "coga"), wt_ticket, message="Ticket: demo — blocked"
        ) is True
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "main").strip() == ahead_tip
    assert "status: in_progress" in ticket.read_text(encoding="utf-8")
    assert _dirty(git_repo) == set()
    assert "git pull --rebase --autostash origin main" in capsys.readouterr().err
    # The human's commit was neither pushed nor rebased.
    assert not git_repo.origin_tracks("local.txt")


def test_refresh_fast_forwards_a_behind_control_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(status="blocked"))

    assert git.refresh(cfg) is True

    assert "status: blocked" in ticket.read_text(encoding="utf-8")
    assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
        "rev-parse", "main", cwd=git_repo.origin
    ).strip()
    assert _dirty(git_repo) == set()


def test_refresh_refuses_an_ahead_or_diverged_control_checkout(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "local.txt")
    git_repo.git("commit", "-m", "local unpushed")
    tip = git_repo.git("rev-parse", "main").strip()

    assert git.refresh(cfg) is False  # ahead: `merge --ff-only` would say "up to date"
    assert "git pull --rebase --autostash origin main" in capsys.readouterr().err

    git_repo.push_competing_commit("other.txt", "remote\n")
    assert git.refresh(cfg) is False  # diverged
    assert git_repo.git("rev-parse", "main").strip() == tip
    assert git_repo.git("status", "--porcelain") == ""


def test_refresh_on_a_feature_checkout_touches_nothing(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(step="2 (review)"))

    assert git.refresh(cfg) is True

    assert "step: 1 (implement)" in ticket.read_text(encoding="utf-8")
    assert git_repo.git("status", "--porcelain") == ""
    # The fetch still landed, so `coga status` can warn.
    assert git.stale_coga_task_rels(cfg) == ["coga/tasks/demo.md"]


def test_teardown_refresh_then_claim_from_a_moved_remote_admits_the_pick(git_repo):
    """The `fix-git-sync-failure` shape: a checkout whose remote moved
    meanwhile is brought level by `refresh`, and a claim then lands."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo, status="active")
    git_repo.push_competing_commit("other.txt", "someone else's work\n")

    assert git.refresh(cfg) is True
    pre_write = ticket.read_bytes()
    ticket.write_text(_ticket_text(status="in_progress", generation="pending:xyz"), encoding="utf-8", newline="\n")

    assert git.publish(
        cfg, [ticket], "Ticket: demo — in_progress", expect={ticket: pre_write}
    ) is True
    assert "pending:xyz" in _control(git_repo, "coga/tasks/demo.md")
    assert _dirty(git_repo) == set()


def test_no_private_fetch_refs_are_left_behind(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.push_competing_commit("other.txt", "remote\n")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is True

    refs = git_repo.git("for-each-ref", "--format=%(refname)").split()
    assert not [ref for ref in refs if ref.startswith("refs/coga/")]
    assert "refs/remotes/origin/main" in refs


# --- the sweep ----------------------------------------------------------------


@pytest.mark.parametrize("layout", ["nested", "root", "relocated"])
@pytest.mark.parametrize("feature", [False, True])
@pytest.mark.parametrize("finalize", [False, True])
def test_sweep_publishes_every_eligible_file_under_the_coga_roots(
    git_repo, monkeypatch, capsys, layout, feature, finalize,
):
    """Owner decision 2026-10-07: tickets, log, recurring templates, contexts,
    skills, workflows, and shared config all publish — added, modified,
    deleted, or renamed — while ignored files and source outside the roots
    stay local."""
    from coga.authoring import finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_task

    _seed_ticket(git_repo)
    if layout == "root":
        monkeypatch.chdir(git_repo.root)
        for path in git_repo.coga_os.iterdir():
            path.rename(git_repo.root / path.name)
        git_repo.coga_os.rmdir()
        git_repo.coga_os = git_repo.root
        (git_repo.root / ".gitignore").write_text("coga.local.toml\n.agent-skills/\n", encoding="utf-8", newline="\n")
        monkeypatch.chdir(git_repo.root)
    elif layout == "relocated":
        contexts = git_repo.root / "docs" / "contexts"
        contexts.mkdir(parents=True)
        (contexts / ".gitkeep").write_text("", encoding="utf-8", newline="\n")
        with (git_repo.coga_os / "coga.toml").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write('[layout]\ncontexts = "docs/contexts"\n')
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    moved_from = cfg.contexts_root / "old" / "SKILL.md"
    skill = git_repo.coga_os / "skills" / "team" / "SKILL.md"
    for path in (context, moved_from, skill):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: team\ndescription: team.\n---\noriginal\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed knowledge and layout")
    git_repo.git("push", "origin", "main")
    ticket = git_repo.coga_os / "tasks" / "demo.md"
    if feature:
        git_repo.git("switch", "-c", "feature")
    ref = resolve_task(cfg, "demo")
    monkeypatch.setenv("COGA_TASK_TICKET", str(ticket))
    monkeypatch.setenv("COGA_TASK_SLUG", "demo")
    before = snapshot_authoring_state(cfg)
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    append_log(cfg, "demo", "human:marc", "hand edit")
    recurring = git_repo.coga_os / "recurring" / "weekly" / "ticket.md"
    recurring.parent.mkdir(parents=True)
    recurring.write_text("---\ntitle: weekly\n---\n", encoding="utf-8", newline="\n")
    context.write_text(context.read_text(encoding="utf-8") + "owner decision\n", encoding="utf-8", newline="\n")
    moved_to = cfg.contexts_root / "renamed" / "SKILL.md"
    moved_to.parent.mkdir(parents=True)
    moved_from.rename(moved_to)
    skill.unlink()
    new_skill = skill.parent / "notes.md"
    new_skill.write_text("new knowledge\n", encoding="utf-8", newline="\n")
    workflow = git_repo.coga_os / "workflows" / "code.md"
    workflow.write_text(workflow.read_text(encoding="utf-8") + "\nEdited workflow prose.\n", encoding="utf-8", newline="\n")
    config = git_repo.coga_os / "coga.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n# shared config\n", encoding="utf-8", newline="\n")
    published = (context, moved_from, moved_to, skill, new_skill, workflow, config)
    local_config = git_repo.coga_os / "coga.local.toml"
    local_config.write_text(local_config.read_text(encoding="utf-8") + "# machine-local\n", encoding="utf-8", newline="\n")
    view = git_repo.coga_os / ".agent-skills" / "team" / "SKILL.md"
    view.parent.mkdir(parents=True)
    view.write_text("generated view\n", encoding="utf-8", newline="\n")
    unrelated = git_repo.root / "src.py"
    if layout != "root":
        unrelated.write_text("code under review\n", encoding="utf-8", newline="\n")

    if finalize:
        finalize_authored(cfg, before_snapshot=before, ref=ref)
        assert "status: blocked" in _control(git_repo, ticket.relative_to(git_repo.root).as_posix())
        assert _control(git_repo, context.relative_to(git_repo.root).as_posix()) == context.read_text(encoding="utf-8")
        err = capsys.readouterr().err
        assert str(context) in err
        assert str(log_path(cfg)) not in err and str(local_config) not in err
    git.sync_coga_state(cfg)

    def landed(path):
        return _control(git_repo, path.relative_to(git_repo.root).as_posix())

    assert "status: blocked" in landed(ticket)
    assert "hand edit" in landed(git_repo.coga_os / "log.md")
    assert landed(recurring) == recurring.read_text(encoding="utf-8")
    for path in published:
        assert landed(path) == (path.read_text(encoding="utf-8") if path.exists() else None)
    for path in (local_config, view):
        assert landed(path) is None
    if layout != "root":
        assert not git_repo.origin_tracks("src.py")
    if not feature:
        assert _dirty(git_repo) <= {"src.py"}


def test_sweep_publishes_knowledge_once_when_the_roots_overlap(git_repo):
    """The default `coga/contexts/` sits inside the Coga root: one pathspec."""
    cfg = load_config(git_repo.coga_os)
    assert git.coga_root_paths(cfg) == (git_repo.coga_os.resolve(),)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("---\nname: team\ndescription: team.\n---\nbody\n", encoding="utf-8", newline="\n")
    before = _origin_tip(git_repo)

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/contexts/team/SKILL.md") == context.read_text(encoding="utf-8")
    assert git_repo.git("rev-list", "--count", f"{before}..{_origin_tip(git_repo)}").strip() == "1"


def test_coga_root_paths_lists_a_relocated_contexts_root_separately(git_repo):
    contexts = git_repo.root / "docs" / "contexts"
    contexts.mkdir(parents=True)
    (contexts / ".gitkeep").write_text("", encoding="utf-8", newline="\n")
    with (git_repo.coga_os / "coga.toml").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write('[layout]\ncontexts = "docs/contexts"\n')

    cfg = load_config(git_repo.coga_os)

    assert git.coga_root_paths(cfg) == (git_repo.coga_os.resolve(), contexts.resolve())


def test_sweep_skips_an_untracked_symlink_and_still_publishes_the_rest(git_repo, tmp_path):
    """A generated view of symlinks in a repo missing its ignore rule must not
    stall every publish behind the guard's symlink refusal."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    target = tmp_path / "skill"
    target.mkdir()
    (target / "SKILL.md").write_text("outside\n", encoding="utf-8", newline="\n")
    link = git_repo.coga_os / "views" / "skill"
    link.parent.mkdir()
    link.symlink_to(target, target_is_directory=True)
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    git.sync_coga_state(cfg)

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert not git_repo.origin_tracks("coga/views/skill")
    assert link.is_symlink()


def test_authoring_refused_over_a_concurrent_context_edit_keeps_everything(git_repo):
    """A context a peer changed on control while the interview ran is refused
    with the authored ticket: nothing lands, every edit stays on disk, and
    the interview fails instead of claiming a completed handoff."""
    from coga.authoring import AuthoringError, finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    context = cfg.contexts_root / "product" / "vision" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("original\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed vision")
    git_repo.git("push", "origin", "main")
    before = snapshot_authoring_state(cfg)
    git_repo.push_competing_commit("coga/contexts/product/vision/SKILL.md", "peer\n")
    git_repo.git("fetch", "origin")
    context.write_text("agreed vision\n", encoding="utf-8", newline="\n")
    ticket.write_text(_ticket_text(blackboard="authored\n"), encoding="utf-8", newline="\n")
    tip = _origin_tip(git_repo)

    with pytest.raises(AuthoringError, match="not published"):
        finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert _origin_tip(git_repo) == tip
    assert context.read_text(encoding="utf-8") == "agreed vision\n"
    assert "authored" in ticket.read_text(encoding="utf-8")


@pytest.mark.parametrize("change", ["add", "modify", "delete", "mode"])
@pytest.mark.parametrize("already_published", [False, True])
def test_authoring_requires_committed_knowledge_to_be_on_control(
    git_repo, capsys, change, already_published,
):
    from coga.authoring import AuthoringError, finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    if change != "add":
        context.write_text("original\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "coga/contexts")
        git_repo.git("commit", "-m", "seed context")
        git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/interview")
    before = snapshot_authoring_state(cfg)
    if change == "delete":
        context.unlink()
    elif change == "mode":
        if os.name == "posix":
            context.chmod(0o755)
    else:
        context.write_text("authored knowledge\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/contexts")
    if change == "mode" and os.name != "posix":
        git_repo.git("update-index", "--chmod=+x", "coga/contexts/team/SKILL.md")
    git_repo.git("commit", "-m", "authored knowledge for review")
    if already_published:
        git_repo.git("push", "origin", "HEAD:main")
    ticket.write_text(_ticket_text(blackboard="authored task\n"), encoding="utf-8", newline="\n")
    tip = _origin_tip(git_repo)

    if already_published:
        finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))
        assert "authored task" in _control(git_repo, "coga/tasks/demo.md")
    else:
        with pytest.raises(AuthoringError, match="excluded from publication"):
            finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))
        assert _origin_tip(git_repo) == tip
        assert "Published these knowledge edits" not in capsys.readouterr().err
    assert "authored task" in ticket.read_text(encoding="utf-8")
    assert context.exists() == (change != "delete")
    if change == "mode":
        assert context.read_text(encoding="utf-8") == "original\n"
    elif context.exists():
        assert context.read_text(encoding="utf-8") == "authored knowledge\n"


@pytest.mark.parametrize(
    "failure", ["committed_context", "push", "invalid_sibling", "duplicate_sibling"],
)
def test_ticket_command_withholds_sweep_after_failed_authoring(
    git_repo, monkeypatch, capsys, failure, tmp_path,
):
    import importlib
    import sys
    from types import SimpleNamespace
    from coga import cli

    command = importlib.import_module("coga.commands.ticket")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "true", "pass\n")
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    task = _seed_ticket(git_repo)
    sibling = (
        _seed_ticket(git_repo, "sibling")
        if failure in {"invalid_sibling", "duplicate_sibling"} else None
    )
    config = git_repo.coga_os / "coga.toml"
    config.write_text(config.read_text(encoding="utf-8").replace('cli = "claude"', 'cli = "true"'), encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "configure test agent")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/interview")
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"

    def interview(*args, **kwargs):
        context.parent.mkdir(parents=True)
        context.write_text("---\nname: team\ndescription: Team.\n---\nKnowledge.\n", encoding="utf-8", newline="\n")
        if failure == "committed_context":
            git_repo.git("add", "coga/contexts")
            git_repo.git("commit", "-m", "review-bound knowledge")
        elif failure == "push":
            monkeypatch.setattr(git, "_push", lambda *args: "offline")
        elif failure == "duplicate_sibling":
            # An interrupted promotion leaves both ticket shapes discoverable.
            directory = sibling.with_suffix("")
            directory.mkdir()
            (directory / "ticket.md").write_bytes(sibling.read_bytes())
        else:
            ticket = Ticket.read(sibling)
            ticket.frontmatter["contexts"] = ["missing/context"]
            ticket.write(sibling)
        ticket = Ticket.read(task)
        ticket.frontmatter["contexts"] = ["team"]
        ticket.write(task)
        return SimpleNamespace(exit_code=0)

    monkeypatch.setattr(command, "_interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr(command, "spawn_agent_session", interview)
    monkeypatch.chdir(git_repo.coga_os)
    monkeypatch.setattr(sys, "argv", ["coga", "ticket", "demo"])
    tip = _origin_tip(git_repo)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert _origin_tip(git_repo) == tip
    assert not git_repo.origin_tracks("coga/contexts/team/SKILL.md")
    assert Ticket.read(task).frontmatter["contexts"] == ["team"]
    assert context.is_file()
    err = capsys.readouterr().err
    assert "Published these knowledge edits" not in err
    assert "state sweep withheld" in err
    assert "coga run publish-state" in err
    if failure == "invalid_sibling":
        assert Ticket.read(sibling).contexts == ["missing/context"]
        assert "missing/context" not in _control(git_repo, "coga/tasks/sibling.md")
    elif failure == "duplicate_sibling":
        assert "Duplicate task slug 'sibling'" in err
        assert sibling.is_file()
        assert (sibling.with_suffix("") / "ticket.md").is_file()
        assert not git_repo.origin_tracks("coga/tasks/sibling/ticket.md")


@pytest.mark.parametrize("contexts", ["coga/contexts", "docs/contexts"])
def test_sweep_leaves_knowledge_committed_on_a_feature_branch_for_its_pr(git_repo, contexts):
    """A commit on a feature branch is review work: a code PR's committed
    context edit (and its packaged twin) waits for the merge, while routine
    ticket state committed beside it is still adopted."""
    context = git_repo.root / contexts / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("original\n", encoding="utf-8", newline="\n")
    config = git_repo.coga_os / "coga.toml"
    with config.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f'\n[layout]\ncontexts = "{contexts}"\n')
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    skill = git_repo.coga_os / "skills" / "team" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("original skill\n", encoding="utf-8", newline="\n")
    packaged = git_repo.root / "src" / "templates" / "team.md"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("original packaged copy\n", encoding="utf-8", newline="\n")
    source = git_repo.root / "src.py"
    source.write_text("# original source\n", encoding="utf-8", newline="\n")
    workflow = git_repo.coga_os / "workflows" / "code.md"
    originals = {
        path.relative_to(git_repo.root).as_posix(): path.read_text(encoding="utf-8")
        for path in (context, skill, workflow, config, packaged, source)
    }
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed context")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    for rel, original in originals.items():
        (git_repo.root / rel).write_text(original + "\n# review in PR\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "--", *originals)
    _hand_commit(git_repo, "coga/tasks/demo.md", _ticket_text(blackboard="handoff\n"))

    git.sync_coga_state(cfg)

    for rel, original in originals.items():
        assert _control(git_repo, rel) == original
    assert "handoff" in _control(git_repo, "coga/tasks/demo.md")


@pytest.mark.parametrize("existing_link", [False, True])
def test_authoring_does_not_publish_source_reached_through_a_symlink(git_repo, existing_link):
    from coga.authoring import finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    source = git_repo.root / "src.py"
    source.write_text("reviewed source\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "src.py")
    git_repo.git("commit", "-m", "seed source")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    link = git_repo.coga_os / "source-reference"
    if existing_link:
        link.symlink_to(source)
    before = snapshot_authoring_state(cfg)
    if not existing_link:
        link.symlink_to(source)
    source.write_text("unreviewed source\n", encoding="utf-8", newline="\n")
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("authored knowledge\n", encoding="utf-8", newline="\n")

    finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert _control(git_repo, "src.py") == "reviewed source\n"
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "authored knowledge\n"
    assert source.read_text(encoding="utf-8") == "unreviewed source\n"
    assert link.is_symlink()


@pytest.mark.parametrize("mode", ["authoring", "sweep", "explicit"])
@pytest.mark.parametrize("target_location", ["inside", "outside", "missing"])
def test_publication_refuses_a_skill_directory_replaced_by_a_symlink(
    git_repo, tmp_path, capsys, mode, target_location,
):
    from coga.authoring import AuthoringError, finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    skill = cfg.repo_root / "skills" / "team"
    skill.mkdir(parents=True)
    child = skill / "helper.py"
    child.write_text("original skill\n", encoding="utf-8", newline="\n")
    source = (git_repo.root if target_location == "inside" else tmp_path) / "source"
    source.mkdir()
    source_child = source / "helper.py"
    source_child.write_text("reviewed source\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/skills")
    if target_location == "inside":
        git_repo.git("add", "source")
    git_repo.git("commit", "-m", "seed skill and source")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/interview")
    before = snapshot_authoring_state(cfg)
    tip = _origin_tip(git_repo)
    child.unlink()
    skill.rmdir()
    skill.symlink_to(source if target_location != "missing" else tmp_path / "missing")
    source_child.write_text("unreviewed source\n", encoding="utf-8", newline="\n")

    if mode == "authoring":
        with pytest.raises(AuthoringError, match="symlinked ancestor"):
            finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))
    elif mode == "explicit":
        with pytest.raises(git.StateRegressionError, match="symlinked ancestor"):
            git.publish(cfg, [child], "Publish skill")
    else:
        git.sync_coga_state(cfg)
        assert "symlinked ancestor" in capsys.readouterr().err

    assert _origin_tip(git_repo) == tip
    assert _control(git_repo, "coga/skills/team/helper.py") == "original skill\n"
    if target_location == "inside":
        assert _control(git_repo, "source/helper.py") == "reviewed source\n"
    assert source_child.read_text(encoding="utf-8") == "unreviewed source\n"
    assert skill.is_symlink()


def test_authoring_keeps_newly_ignored_files_local_without_blocking_publication(
    git_repo, capsys,
):
    from coga.authoring import finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    scratch = cfg.repo_root / "scratch.txt"
    scratch.write_text("local scratch\n", encoding="utf-8", newline="\n")
    before = snapshot_authoring_state(cfg)
    ignore = cfg.repo_root / ".gitignore"
    ignore.write_text("scratch.txt\n", encoding="utf-8", newline="\n")
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("authored knowledge\n", encoding="utf-8", newline="\n")

    finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert scratch.read_text(encoding="utf-8") == "local scratch\n"
    assert not git_repo.origin_tracks("coga/scratch.txt")
    assert "scratch.txt" not in capsys.readouterr().err
    assert _control(git_repo, "coga/.gitignore") == ignore.read_text(encoding="utf-8")
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "authored knowledge\n"
    assert git_repo.git("status", "--porcelain").strip() == ""


def test_default_context_symlink_does_not_expand_publication_roots(git_repo):
    cfg = load_config(git_repo.coga_os)
    source = git_repo.root / "source"
    source.mkdir()
    child = source / "helper.py"
    child.write_text("reviewed source\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "source")
    git_repo.git("commit", "-m", "seed source")
    git_repo.git("push", "origin", "main")
    cfg.contexts_root.symlink_to(source, target_is_directory=True)
    child.write_text("unreviewed source\n", encoding="utf-8", newline="\n")
    tip = _origin_tip(git_repo)

    assert git.coga_root_paths(cfg) == (cfg.repo_root,)
    git.sync_coga_state(cfg)

    assert _origin_tip(git_repo) == tip
    assert _control(git_repo, "source/helper.py") == "reviewed source\n"


def test_checkout_return_refuses_symlinked_ancestors_even_with_published_bytes(
    git_repo, tmp_path,
):
    cfg = load_config(git_repo.coga_os)
    skill = cfg.repo_root / "skills" / "team"
    skill.mkdir(parents=True)
    child = skill / "helper.py"
    child.write_text("published\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/skills")
    git_repo.git("commit", "-m", "seed skill")
    git_repo.git("push", "origin", "main")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "helper.py").write_text("published\n", encoding="utf-8", newline="\n")
    child.unlink()
    skill.rmdir()
    skill.symlink_to(outside, target_is_directory=True)
    # Hide the untracked directory link, leaving only the tracked child's
    # apparent deletion for the cleanup proof to examine.
    (git_repo.root / ".git" / "info" / "exclude").write_text("coga/skills/team\n", encoding="utf-8", newline="\n")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert any("coga/skills/team/helper.py" in item for item in outcome.blocking)
    assert skill.is_symlink()
    assert (outside / "helper.py").read_text(encoding="utf-8") == "published\n"


@pytest.mark.parametrize("feature", [False, True])
@pytest.mark.parametrize("invalid_config", [False, True])
def test_authoring_reloads_config_and_publishes_context_relocation_atomically(
    git_repo, feature, invalid_config
):
    from coga.authoring import AuthoringError, finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_task

    cfg = load_config(git_repo.coga_os)
    task = _seed_ticket(git_repo)
    context = cfg.contexts_root / "team" / "note" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("---\nname: team/note\ndescription: A note.\n---\nKnowledge.\n", encoding="utf-8", newline="\n")
    ticket = Ticket.read(task)
    ticket.frontmatter["contexts"] = ["team/note"]
    ticket.write(task)
    git_repo.git("add", "coga")
    git_repo.git("commit", "-m", "seed authored context")
    git_repo.git("push", "origin", "main")
    if feature:
        git_repo.checkout_branch("feature/x")
    before = snapshot_authoring_state(cfg)
    tip = _origin_tip(git_repo)
    destination = git_repo.root / "docs" / "contexts"
    destination.parent.mkdir()
    cfg.contexts_root.rename(destination)
    config_path = cfg.repo_root / "coga.toml"
    config = config_path.read_text(encoding="utf-8") + '\n[layout]\ncontexts = "docs/contexts"\n'
    if invalid_config:
        config = config.replace("version = 1", "version = 999")
    config_path.write_text(config, encoding="utf-8", newline="\n")

    if invalid_config:
        with pytest.raises(AuthoringError, match="configuration is invalid"):
            finalize_authored(cfg, before_snapshot=before, ref=resolve_task(cfg, "demo"))
        assert _origin_tip(git_repo) == tip
    else:
        finalize_authored(cfg, before_snapshot=before, ref=resolve_task(cfg, "demo"))
        assert _control(git_repo, "coga/coga.toml") == config
        assert _control(git_repo, "coga/contexts/team/note/SKILL.md") is None
        assert _control(git_repo, "docs/contexts/team/note/SKILL.md") == (
            destination / "team" / "note" / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert git_repo.git("rev-parse", "origin/main^").strip() == tip
    assert (destination / "team" / "note" / "SKILL.md").is_file()


@pytest.mark.parametrize("feature", [False, True])
@pytest.mark.parametrize("relocated", [False, True])
@pytest.mark.parametrize("config_change", ["relocate", "invalid", "destination"])
def test_checkout_return_reloads_config_before_publishing(
    git_repo, feature, relocated, config_change,
):
    from coga.launch import _CheckoutBoundary

    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("---\nname: team\ndescription: Team.\n---\nKnowledge.\n", encoding="utf-8", newline="\n")
    config_path = cfg.repo_root / "coga.toml"
    if relocated:
        old_root = git_repo.root / "docs" / "contexts"
        old_root.parent.mkdir()
        cfg.contexts_root.rename(old_root)
        config_path.write_text(config_path.read_text(encoding="utf-8") + '\n[layout]\ncontexts = "docs/contexts"\n', encoding="utf-8", newline="\n")
        cfg = load_config(cfg.repo_root)
    old_rel = (cfg.contexts_root.relative_to(git_repo.root) / "team" / "SKILL.md").as_posix()
    git_repo.git("add", "coga", "docs" if relocated else "coga/contexts")
    git_repo.git("commit", "-m", "seed context")
    git_repo.git("push", "origin", "main")
    boundary = _CheckoutBoundary()
    boundary.enter(cfg, "demo")
    if feature:
        git_repo.checkout_branch("feature/interview")
    tip = _origin_tip(git_repo)
    destination = git_repo.root / "docs" / "topics"
    destination.parent.mkdir(exist_ok=True)
    cfg.contexts_root.rename(destination)
    config = config_path.read_text(encoding="utf-8")
    if relocated:
        config = config.replace('contexts = "docs/contexts"', 'contexts = "docs/topics"')
    else:
        config += '\n[layout]\ncontexts = "docs/topics"\n'
    if config_change == "invalid":
        config = config.replace("version = 1", "version = 999")
    elif config_change == "destination":
        config += '\n[git]\ncontrol_branch = "other"\n'
    config_path.write_text(config, encoding="utf-8", newline="\n")
    token = git.state_sweep_withheld.set(False)
    try:
        settled = boundary.settle(cfg, subject="context relocation")
        if config_change == "relocate":
            assert settled
            assert git_repo.git("status", "--porcelain").strip() == ""
            assert git_repo.git("branch", "--show-current").strip() == "main"
            assert _control(git_repo, "docs/topics/team/SKILL.md") == (
                destination / "team" / "SKILL.md"
            ).read_text(encoding="utf-8")
            assert _control(git_repo, old_rel) is None
            assert _control(git_repo, "coga/coga.toml") == config
            assert git_repo.git("rev-parse", "origin/main^").strip() == tip
            assert load_config(cfg.repo_root).contexts_root == destination
        else:
            assert not settled
            assert boundary.stopped
            assert git.state_sweep_withheld.get()
            assert _origin_tip(git_repo) == tip
            assert config_path.read_text(encoding="utf-8") == config
            assert (destination / "team" / "SKILL.md").is_file()
    finally:
        git.state_sweep_withheld.reset(token)


@pytest.mark.parametrize("change", ["dirty", "committed", "deleted", "added"])
def test_sweep_refuses_submodules_without_deleting_them(git_repo, capsys, change):
    cfg = load_config(git_repo.coga_os)
    rel = "coga/skills/external"
    sub = git_repo.root / rel
    sub.mkdir(parents=True)
    git_repo.git("-C", str(sub), "init", "-b", "main")
    git_repo.git("-C", str(sub), "config", "user.name", "Test")
    git_repo.git("-C", str(sub), "config", "user.email", "test@example.com")
    knowledge = sub / "SKILL.md"
    knowledge.write_text("original\n", encoding="utf-8", newline="\n")
    git_repo.git("-C", str(sub), "add", ".")
    git_repo.git("-C", str(sub), "commit", "-m", "seed module")
    git_repo.git("add", rel)
    if change != "added":
        git_repo.git("commit", "-m", "seed gitlink")
        git_repo.git("push", "origin", "main")
    original = git_repo.git("ls-tree", "origin/main", "--", rel)
    if change == "deleted":
        remove_test_checkout(sub)
    elif change != "added":
        knowledge.write_text("edited\n", encoding="utf-8", newline="\n")
        if change == "committed":
            git_repo.git("-C", str(sub), "commit", "-am", "edit module")

    git.sync_coga_state(cfg)

    assert "is a submodule" in capsys.readouterr().err
    assert git_repo.git("ls-tree", "origin/main", "--", rel) == original
    if change != "deleted":
        assert knowledge.read_text(encoding="utf-8") == ("original\n" if change == "added" else "edited\n")


@pytest.mark.parametrize("rel", [
    "coga/skills/team/SKILL.md",
    "coga/recurring/weekly/ticket.md",
    "coga/recurring/weekly/ticket.py",
    "coga/recurring/weekly/retires.md",
])
def test_sweep_publishes_hand_committed_knowledge_from_a_clean_control_checkout(git_repo, rel):
    cfg = load_config(git_repo.coga_os)
    tip = _hand_commit(git_repo, rel, "hand knowledge\n")
    assert _dirty(git_repo) == set()

    git.sync_coga_state(cfg)

    assert _control(git_repo, rel) == "hand knowledge\n"
    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert tip in git_repo.git("reflog", "--format=%H", "main")
    assert _dirty(git_repo) == set()


def test_sweep_refuses_a_stale_context_overwrite(git_repo, capsys):
    """Compare-and-swap covers knowledge too: a context a peer changed on
    control since this checkout read it is refused, not overwritten."""
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("original\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed context")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit("coga/contexts/team/SKILL.md", "peer edit\n")
    git_repo.git("fetch", "origin")
    context.write_text("local edit\n", encoding="utf-8", newline="\n")

    git.sync_coga_state(cfg)

    assert "sync refused" in capsys.readouterr().err
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "peer edit\n"
    assert context.read_text(encoding="utf-8") == "local edit\n"


def test_sweep_leaves_a_stale_ticket_refused_but_converges_a_fresh_one(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    stale = _seed_ticket(git_repo, "stale")
    fresh = _seed_ticket(git_repo, "fresh")
    git_repo.push_competing_commit("coga/tasks/stale.md", _ticket_text(status="done"))
    stale.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    fresh.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    git.sync_coga_state(cfg)
    err = capsys.readouterr().err
    assert "sync refused" in err
    assert "git checkout origin/main -- coga/tasks/stale.md" in err
    assert "status: done" in _control(git_repo, "coga/tasks/stale.md")
    # A refused path blocks that publish; the fresh ticket lands once the
    # stale one is taken from control as the hint says.
    git_repo.git("checkout", "origin/main", "--", "coga/tasks/stale.md")
    git.sync_coga_state(cfg)
    assert "status: blocked" in _control(git_repo, "coga/tasks/fresh.md")
    assert _dirty(git_repo) == set()


def _hand_commit(git_repo, rel: str, text: str | None, message: str = "hand commit") -> str:
    """Commit a write (or, with `None`, a deletion) of `rel` on the current branch."""
    path = git_repo.root / rel
    if text is None:
        git_repo.git("rm", "-r", "--quiet", "--", rel)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        git_repo.git("add", "--", rel)
    git_repo.git("commit", "-m", message)
    return git_repo.git("rev-parse", "HEAD").strip()


def test_sweep_publishes_a_hand_committed_ticket_from_a_clean_control_checkout(
    git_repo, capsys
):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    hand = _ticket_text(blackboard="hand edit\n")
    tip = _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    assert _dirty(git_repo) == set()

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/tasks/demo.md") == hand
    # Publication made its own commit; the hand commit was realigned away,
    # named on stderr, and kept in the reflog.
    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert _dirty(git_repo) == set()
    err = capsys.readouterr().err
    assert f"realigned local 'main' to origin/main" in err and tip[:12] in err
    assert tip in git_repo.git("reflog", "--format=%H", "main")


@pytest.mark.parametrize("detached", [False, True])
def test_sweep_publishes_committed_state_from_a_feature_checkout(git_repo, detached):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    hand = _ticket_text(blackboard="feature handoff\n")
    (git_repo.root / "src.py").write_text("code\n", encoding="utf-8", newline="\n")
    period = git_repo.coga_os / "tasks" / "recurring" / "weekly" / "ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text(_ticket_text(), encoding="utf-8", newline="\n")
    script = period.with_suffix(".py")
    script.write_text("print('period')\n", encoding="utf-8", newline="\n")
    append_log(cfg, "demo", "agent:claude", "committed handoff")
    log = log_path(cfg).read_text(encoding="utf-8")
    git_repo.git("add", "src.py", "coga/tasks/recurring", "coga/log.md")
    tip = _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    if detached:
        git_repo.git("checkout", "--detach")
    assert _dirty(git_repo) == set()

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/tasks/demo.md") == hand
    assert _control(git_repo, "coga/tasks/recurring/weekly/ticket.md") == _ticket_text()
    assert _control(git_repo, "coga/tasks/recurring/weekly/ticket.py") == "print('period')\n"
    assert _control(git_repo, "coga/log.md") == log
    assert not git_repo.origin_tracks("src.py")
    assert _head(git_repo) == ("HEAD" if detached else "feature/x", tip)
    assert _dirty(git_repo) == set()
    assert git_repo.git("rev-parse", "main").strip() == _origin_tip(git_repo)


def test_sweep_leaves_clean_state_behind_control_alone(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(status="blocked"))
    git_repo.git("fetch", "origin")
    before = _origin_tip(git_repo)

    git.sync_coga_state(cfg)

    assert _origin_tip(git_repo) == before


def test_sweep_does_not_republish_a_ticket_this_feature_checkout_lacks(git_repo):
    """Control holds a copy this worktree published, but HEAD's copy is merely
    older (here: absent since the branch point) — not a write to carry."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    fresh = git_repo.coga_os / "tasks" / "fresh.md"
    fresh.write_text(_ticket_text(), encoding="utf-8", newline="\n")
    assert git.publish(cfg, [fresh], "Ticket: fresh — created") is True
    fresh.unlink()
    before = _origin_tip(git_repo)

    git.sync_coga_state(cfg)

    assert _origin_tip(git_repo) == before
    assert _control(git_repo, "coga/tasks/fresh.md") == _ticket_text()


def test_sweep_publishes_a_committed_deletion_of_an_absent_state_directory(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    _hand_commit(git_repo, "coga/tasks", None, "drop tasks")
    assert not (git_repo.coga_os / "tasks").exists()

    git.sync_coga_state(cfg)

    assert not git_repo.origin_tracks("coga/tasks/demo.md")


def _sweep_checkout_snapshot(git_repo):
    """HEAD, index entries, dirt and eligible working bytes/modes, not Git refs."""
    rels = git_repo.git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    working = {}
    for rel in filter(None, rels.split("\x00")):
        path = git_repo.root / rel
        working[rel] = (path.read_bytes(), path.stat().st_mode) if path.exists() else None
    return (
        _head(git_repo), git_repo.git("ls-files", "--stage", "-z"),
        git_repo.git("status", "--porcelain", "-z"), working,
    )


@pytest.mark.parametrize("layout", ["nested", "custom", "root"])
@pytest.mark.parametrize("detached", [False, True])
@pytest.mark.parametrize("change", ["add", "edit", "delete", "delete-directory", "rename", "mode"])
def test_sweep_keeps_committed_recurring_files_on_the_branch(
    git_repo, monkeypatch, layout, detached, change,
):
    if layout != "nested":
        monkeypatch.chdir(git_repo.root)
        destination = git_repo.root if layout == "root" else git_repo.root / "workbench"
        destination.mkdir(exist_ok=True)
        for path in git_repo.coga_os.iterdir():
            path.rename(destination / path.name)
        git_repo.coga_os.rmdir()
        git_repo.coga_os = destination
        prefix = "" if layout == "root" else "workbench/"
        (git_repo.root / ".gitignore").write_text(
            f"{prefix}coga.local.toml\n{prefix}.agent-skills/\n", encoding="utf-8", newline="\n",
        )
    cfg = load_config(git_repo.coga_os)
    recurring = cfg.repo_root / "recurring"
    weekly = recurring / "weekly"
    weekly.mkdir(parents=True)
    originals = {
        "ticket.md": "---\ntitle: weekly\n---\n\n<!-- coga:blackboard -->\nold cursor\n",
        "ticket.py": "print('original')\n",
        "retires.md": "original sibling\n",
    }
    for name, content in originals.items():
        (weekly / name).write_text(content, encoding="utf-8", newline="\n")
    packaged = git_repo.root / "src" / "templates" / "weekly.py"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("print('packaged original')\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed recurring and layout")
    git_repo.git("push", "origin", "main")
    rel = recurring.relative_to(git_repo.root).as_posix()
    control_tree = git_repo.git("ls-tree", "-r", "main", "--", rel, "src", cwd=git_repo.origin)
    git_repo.checkout_branch("feature/x")
    if change in {"add", "edit"}:
        target = recurring / "new" if change == "add" else weekly
        target.mkdir(exist_ok=True)
        for name, content in originals.items():
            (target / name).write_text(content + "# branch change\n", encoding="utf-8", newline="\n")
    elif change == "delete":
        (weekly / "ticket.md").unlink()
        (weekly / "retires.md").unlink()
    elif change == "delete-directory":
        shutil.rmtree(recurring)
    elif change == "rename":
        weekly.rename(recurring / "renamed")
    else:
        if os.name == "posix":
            (weekly / "ticket.py").chmod(0o755)
        git_repo.git("update-index", "--chmod=+x", f"{rel}/weekly/ticket.py")
    packaged.write_text("print('packaged branch')\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "recurring changes pending review")
    if detached:
        git_repo.git("checkout", "--detach")
    assert _dirty(git_repo) == set()
    before = _sweep_checkout_snapshot(git_repo)
    control_tip = _origin_tip(git_repo)

    # A completely clean checkout is enough to reproduce the original leak.
    git.sync_coga_state(cfg)

    assert _origin_tip(git_repo) == control_tip
    assert _sweep_checkout_snapshot(git_repo) == before
    task = cfg.repo_root / "tasks" / "fresh.md"
    task.parent.mkdir(exist_ok=True)
    task.write_text(_ticket_text(), encoding="utf-8", newline="\n")
    append_log(cfg, "fresh", "agent:claude", "dirty handoff")
    before = _sweep_checkout_snapshot(git_repo)
    for _ in range(2):
        git.sync_coga_state(cfg)
        assert git_repo.git("ls-tree", "-r", "main", "--", rel, "src", cwd=git_repo.origin) == control_tree
        assert _control(git_repo, task.relative_to(git_repo.root).as_posix()) == _ticket_text()
        assert "dirty handoff" in _control(git_repo, log_path(cfg).relative_to(git_repo.root).as_posix())
        assert _sweep_checkout_snapshot(git_repo) == before


@pytest.mark.parametrize("detached", [False, True])
def test_sweep_does_not_readopt_committed_recurring_after_control_reverts(git_repo, detached):
    cfg = load_config(git_repo.coga_os)
    rel = "coga/recurring/weekly/ticket.md"
    _hand_commit(git_repo, rel, "original template\n")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    path = git_repo.root / rel
    path.write_text("branch template\n", encoding="utf-8", newline="\n")
    # Model a prior publication, including this checkout's provenance record.
    git.sync_coga_state(cfg)
    assert _control(git_repo, rel) == "branch template\n"
    _hand_commit(git_repo, rel, "branch template\n")
    if detached:
        git_repo.git("checkout", "--detach")
    git_repo.push_competing_commit(rel, "original template\n")
    git_repo.git("fetch", "origin")
    assert _dirty(git_repo) == set()
    before = _sweep_checkout_snapshot(git_repo)
    control_tip = _origin_tip(git_repo)

    for _ in range(2):
        git.sync_coga_state(cfg)
        assert _origin_tip(git_repo) == control_tip
        assert _control(git_repo, rel) == "original template\n"
        assert _sweep_checkout_snapshot(git_repo) == before


@pytest.mark.parametrize("feature", [False, True])
@pytest.mark.parametrize("staged", [False, True])
def test_sweep_publishes_dirty_recurring_runtime_files(git_repo, feature, staged):
    from coga.retire_worklist import RetireFollowUp, reconcile_worklist
    from coga.taskfile import replace_blackboard

    cfg = load_config(git_repo.coga_os)
    template = "coga/recurring/weekly/ticket.md"
    script = "coga/recurring/weekly/ticket.py"
    sibling = "coga/recurring/weekly/operations.md"
    _hand_commit(git_repo, template, "original definition\n<!-- coga:blackboard -->\n")
    _hand_commit(git_repo, script, "print('original')\n")
    _hand_commit(git_repo, sibling, "original operations\n")
    git_repo.git("push", "origin", "main")
    if feature:
        git_repo.checkout_branch("feature/x")
        _hand_commit(git_repo, template, "committed definition\n<!-- coga:blackboard -->\n")
        _hand_commit(git_repo, sibling, "committed operations\n")
    replace_blackboard(git_repo.root / template, "\nnew runtime cursor\n")
    (git_repo.root / script).write_text("print('dirty script')\n", encoding="utf-8", newline="\n")
    worklist = git_repo.root / "coga/recurring/weekly/retires.md"
    reconcile_worklist(
        cfg, worklist, root=git_repo.root,
        pending=[RetireFollowUp("demo", "feature/debt", str(git_repo.root), "2026-10-01")],
    )
    expected = {
        rel: (git_repo.root / rel).read_text(encoding="utf-8")
        for rel in (template, script, "coga/recurring/weekly/retires.md")
    }
    if staged:
        git_repo.git("add", "--", *expected)
    before = _sweep_checkout_snapshot(git_repo)

    git.sync_coga_state(cfg)

    for rel, content in expected.items():
        assert _control(git_repo, rel) == content
    assert _control(git_repo, sibling) == "original operations\n"
    if feature:
        # A dirty blackboard publishes its whole template, including the
        # committed definition. The clean committed sibling remains excluded.
        assert "committed definition" in _control(git_repo, template)
        assert _sweep_checkout_snapshot(git_repo) == before
    else:
        assert _dirty(git_repo) == set()


# --- object-write failures: where Git was writing, and the recovery -----------


def _failing_hash_object(monkeypatch, stderr: bytes, *, probe_fails: bool = False):
    """Inject a `hash-object -w` failure (and optionally a failed location probe)."""
    real_run = git._run

    def fake(argv, *, env=None, input=None):  # type: ignore[no-untyped-def]
        if "hash-object" in argv:
            return subprocess.CompletedProcess(argv, 128, b"", stderr)
        if probe_fails and "--git-path" in argv:
            raise git.GitError("`git` not found on PATH")
        return real_run(argv, env=env, input=input)

    monkeypatch.setattr(git, "_run", fake)


_EROFS = (
    b"error: unable to create temporary file: Read-only file system\n"
    b"fatal: Unable to add coga/tasks/demo.md to database.\n"
)


def test_object_dir_is_the_ordinary_git_objects(git_repo):
    assert git._object_dir(git_repo.root) == (git_repo.root / ".git" / "objects").resolve()


def test_object_dir_of_a_linked_checkout_is_the_shared_store(git_repo):
    linked = git_repo.origin.parent / "linked checkout"
    git_repo.git("worktree", "add", "-b", "side", str(linked))

    assert git._object_dir(linked) == (git_repo.root / ".git" / "objects").resolve()


def test_object_dir_follows_a_relative_override_from_another_cwd(
    git_repo, tmp_path, monkeypatch
):
    store = git_repo.root / "alt objects"
    store.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    # Relative to the checkout: Git resolves it after `-C`, as the write does.
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "alt objects")

    assert git._object_dir(git_repo.root) == store.resolve()


@windows_skip("POSIX directory write permissions")
def test_unwritable_object_dir_names_checkout_destination_and_cause(
    git_repo, tmp_path, monkeypatch
):
    store = tmp_path / "restricted objects"
    store.mkdir()
    store.chmod(0o555)
    try:
        if os.access(store, os.W_OK):
            pytest.skip("chmod does not restrict this user (e.g. root)")
        monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(store))

        with pytest.raises(git.ObjectWriteError) as caught:
            git._hash_blob(git_repo.root, b"x\n", "coga/tasks/demo.md")
    finally:
        store.chmod(0o755)

    exc = caught.value
    assert exc.rel == "coga/tasks/demo.md"
    assert exc.checkout == git_repo.root
    assert exc.object_dir == store
    # Observed as permission denied, not EROFS (that is covered by injection).
    assert "insufficient permission" in exc.detail
    assert f"object directory {store}" in str(exc)


def test_erofs_hash_failure_keeps_git_stderr_and_the_location(git_repo, monkeypatch):
    _failing_hash_object(monkeypatch, _EROFS)

    with pytest.raises(git.ObjectWriteError) as caught:
        git._hash_blob(git_repo.root, b"x\n", "coga/tasks/demo.md")

    message = str(caught.value)
    assert "`git hash-object -w` failed for coga/tasks/demo.md" in message
    assert f"checkout {git_repo.root}" in message
    assert f"object directory {(git_repo.root / '.git' / 'objects').resolve()}" in message
    assert "Read-only file system" in message
    assert "Unable to add coga/tasks/demo.md to database" in message


def test_failed_location_probe_keeps_the_original_error(git_repo, monkeypatch):
    _failing_hash_object(monkeypatch, _EROFS, probe_fails=True)

    with pytest.raises(git.ObjectWriteError) as caught:
        git._hash_blob(git_repo.root, b"x\n", "coga/tasks/demo.md")

    assert caught.value.object_dir is None
    assert "object directory unavailable" in str(caught.value)
    assert "Read-only file system" in str(caught.value)


def test_a_failing_clean_filter_is_an_object_write_failure_without_a_cause(git_repo):
    git_repo.git("config", "filter.broken.clean", "false")
    git_repo.git("config", "filter.broken.required", "true")
    (git_repo.root / ".gitattributes").write_text("*.md filter=broken\n", encoding="utf-8", newline="\n")

    with pytest.raises(git.ObjectWriteError) as caught:
        git._hash_blob(git_repo.root, b"x\n", "coga/tasks/demo.md")

    assert "filter" in caught.value.detail
    assert "permission" not in str(caught.value).lower()


def test_best_effort_task_sync_separates_saved_state_from_failed_publication(
    git_repo, monkeypatch, capsys
):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    written = ticket.read_bytes()
    _failing_hash_object(monkeypatch, _EROFS)

    assert git.sync_task_state(
        cfg, ticket, message="Ticket: demo — step 2 (review)", command="bump"
    ) is None

    err = capsys.readouterr().err
    assert "[git] sync failed: `git hash-object -w` failed" in err
    assert "Message was: Ticket: demo — step 2 (review)" in err
    assert "Local task state was saved; Git publication failed." in err
    assert "Do not rerun `coga bump` to recover." in err
    assert "If Git could not write to the object storage shown above" in err
    required = shlex.quote(str(Path("tasks") / "demo.md"))
    assert (
        f"`coga run publish-state {required} log.md` "
        f"from {shlex.quote(str(git_repo.coga_os))}"
    ) in err
    assert ticket.read_bytes() == written
    # The audit line stays concise: the failure, not the remedy.
    log = _global_log(cfg)
    assert "sync failed: `git hash-object -w` failed" in log
    assert "publish-state" not in log


def test_strict_task_sync_stays_neutral_and_raises(git_repo, monkeypatch, capsys):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    _failing_hash_object(monkeypatch, _EROFS)

    with pytest.raises(git.ObjectWriteError):
        git.sync_task_state(cfg, ticket, message="Ticket: demo — step 1", strict=True)

    err = capsys.readouterr().err
    assert "[git] sync failed: `git hash-object -w` failed" in err
    assert "saved" not in err
    assert "publish-state" not in err


def test_failure_report_quotes_recovery_paths_and_drops_missing_ones(tmp_path):
    root = tmp_path / "my repo" / "coga"
    task = root / "tasks" / "with space"
    task.mkdir(parents=True)
    (task / "ticket.md").write_text("x\n", encoding="utf-8", newline="\n")
    exc = git.GitError("`git push origin` failed (exit 1): fatal: unreachable")

    text = git.sync_failure_report(
        _cfg(root), exc, message="m", retained="Local task state was saved",
        recovery_paths=(task, root / "log.md"),
    )

    required = shlex.quote(str(Path("tasks") / "with space" / "ticket.md"))
    assert f"coga run publish-state {required}`" in text
    assert f"from {shlex.quote(str(root))}" in text
    assert "Do not rerun the command to recover." in text
    # A transport failure gets no storage-access diagnosis.
    assert "object storage" not in text


def test_failure_report_keeps_uncertainty_and_refusal_distinct(tmp_path):
    cfg = _cfg(tmp_path)
    uncertain = git.sync_failure_report(
        cfg, git.UncertainPublishError("control unreadable"), retained="Kept"
    )
    refused = git.sync_failure_report(
        cfg, git.StateRegressionError("stale"), label="sync refused", retained="Kept"
    )

    assert "Git publication could not be confirmed" in uncertain
    assert "Git publication failed" not in uncertain
    assert refused == "[git] sync refused: stale.\n"


def test_failed_failure_log_never_masks_the_sync_failure(git_repo, monkeypatch, capsys):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(step="2 (review)"), encoding="utf-8", newline="\n")
    _failing_hash_object(monkeypatch, _EROFS)

    def unwritable_log(*args):  # type: ignore[no-untyped-def]
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(git, "append_log", unwritable_log)

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — step 2") is None
    git.sync_coga_state(cfg)
    with pytest.raises(git.ObjectWriteError):
        git.sync_task_state(cfg, ticket, message="Ticket: demo — step 2", strict=True)

    err = capsys.readouterr().err
    assert err.count("[git] sync failed: `git hash-object -w` failed") == 3
    assert err.count("could not record the sync failure in the log") == 3
    assert "Local Coga files were retained" in err


# --- soft skips ---------------------------------------------------------------


def test_sync_noop_when_not_a_git_repo(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text(), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, task, message="Ticket: demo — created") is None
    assert "not a git repo" in capsys.readouterr().err


def test_sync_suppressed_when_disabled(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path, git_enabled=False)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text(), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, task, message="Ticket: demo — created") is None
    assert "disabled" in capsys.readouterr().err
    assert git.refresh(cfg) is True


def test_sync_skips_with_guidance_when_control_branch_absent(git_repo, capsys):
    """The fresh-repo mismatch: `main` does not exist (the repo is on `master`)."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.git("branch", "-m", "main", "master")
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    git_repo.git("remote", "remove", "origin")
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is None

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist (you are on 'master')" in err
    assert 'control_branch = "master"' in err
    assert git_repo.git("log", "-1", "--format=%s").strip() == "seed demo"


def test_sync_nonfatal_on_rev_parse_failure(tmp_path, monkeypatch, real_git, capsys):
    cfg = _cfg(tmp_path)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text(), encoding="utf-8", newline="\n")

    class Result:
        returncode = 128
        stdout = b""
        stderr = b"fatal: detected dubious ownership in repository"

    monkeypatch.setattr(git.subprocess, "run", lambda *a, **k: Result())

    assert git.sync_task_state(cfg, task, message="Ticket: demo — created") is None
    assert "sync skipped" in capsys.readouterr().err


def test_sync_log_reports_on_stderr_only(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    append_log(cfg, "bootstrap/orient", "human:marc", "launched")
    git_repo.git("remote", "set-url", "origin", str(git_repo.origin.parent / "missing.git"))

    assert git.sync_log(cfg, message="Log: bootstrap/orient") is None
    err = capsys.readouterr().err
    assert "log sync failed" in err
    assert "The local log was retained" in err
    assert "sync failed" not in _global_log(cfg)


def test_sync_log_refuses_an_ignored_untracked_log(git_repo, capsys):
    """A written log excluded by Git must not look like a published no-op."""
    cfg = load_config(git_repo.coga_os)
    (git_repo.root / ".git" / "info" / "exclude").write_text("coga/log.md\n", encoding="utf-8", newline="\n")
    append_log(cfg, "bootstrap/orient", "system", "session usage")
    before = _global_log(cfg)

    assert git.sync_log(cfg, message="Log: bootstrap/orient") is None

    err = capsys.readouterr().err
    assert "log sync failed" in err
    assert "excluded from publication" in err
    assert _global_log(cfg) == before
    assert not git_repo.origin_tracks("coga/log.md")

    # Follow the actual printed remedy: it must require the excluded log,
    # not let a no-path sweep report success while the log is still ignored.
    recovery = shlex.split(err.split("Run `", 1)[1].split("`", 1)[0])
    assert recovery[:3] == ["coga", "run", "publish-state"]
    command = [sys.executable, "-m", "coga.cli", *recovery[1:]]
    refused = subprocess.run(command, capture_output=True, text=True)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "excluded from publication" in refused.stderr
    assert _global_log(cfg) == before
    assert not git_repo.origin_tracks("coga/log.md")

    (git_repo.root / ".git" / "info" / "exclude").write_text("", encoding="utf-8", newline="\n")
    recovered = subprocess.run(command, capture_output=True, text=True)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert _control(git_repo, "coga/log.md") == before
    assert git_repo.git("status", "--porcelain") == ""


def test_sync_log_distinguishes_already_published_from_failure(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    append_log(cfg, "bootstrap/orient", "system", "session usage")

    assert git.sync_log(cfg, message="Log: bootstrap/orient") is True
    assert git.sync_log(cfg, message="Log: bootstrap/orient") is False
    assert "log sync failed" not in capsys.readouterr().err
    assert _control(git_repo, "coga/log.md") == _global_log(cfg)


# --- state_lock ---------------------------------------------------------------


def test_state_lock_is_reentrant_within_a_thread(git_repo):
    cfg = load_config(git_repo.coga_os)
    with git.state_lock(cfg):
        with git.state_lock(cfg):
            ticket = _seed_ticket(git_repo)
            ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
            # `publish` takes the lock again inside megalaunch's admission window.
            assert git.publish(cfg, [ticket], "Ticket: demo — blocked") is True
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")


# --- read-only probes ---------------------------------------------------------


def test_stale_coga_task_rels_names_only_provably_newer_remote_copies(git_repo):
    cfg = load_config(git_repo.coga_os)
    ahead = _seed_ticket(git_repo, "ahead")
    _seed_ticket(git_repo, "edited")
    git_repo.push_competing_commit("coga/tasks/ahead.md", _ticket_text(step="2 (review)"))
    git_repo.push_competing_commit("coga/tasks/edited.md", _ticket_text(blackboard="prose\n"))
    git_repo.push_competing_commit("coga/tasks/new.md", _ticket_text())
    git_repo.git("fetch", "origin", "main")
    assert "step: 1" in ahead.read_text(encoding="utf-8")

    assert git.stale_coga_task_rels(cfg) == ["coga/tasks/ahead.md", "coga/tasks/new.md"]


def test_last_commit_times_keys_paths_under_tasks(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo, "demo")
    times = git.last_commit_times(cfg)
    assert list(times) == ["demo.md"]


def test_last_commit_times_narrows_to_requested_paths(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo, "demo")
    _seed_ticket(git_repo, "other")

    assert list(git.last_commit_times(cfg, ["other.md"])) == ["other.md"]

    # Every task covered by the log: nothing to ask, so git never runs.
    def fail(*args, **kwargs):
        raise AssertionError("git should not run for an empty path list")

    monkeypatch.setattr(git, "run_git", fail)
    assert git.last_commit_times(cfg, []) == {}


def test_is_linked_worktree(git_repo, tmp_path):
    assert git.is_linked_worktree(git_repo.root) is False
    worktree = tmp_path / "linked"
    git_repo.git("worktree", "add", "-b", "linked", str(worktree), "main")
    try:
        assert git.is_linked_worktree(worktree) is True
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))


def test_classify_checkout_primary_and_linked(git_repo, tmp_path):
    worktree = tmp_path / "linked"
    git_repo.git("worktree", "add", "-b", "linked", str(worktree), "main")

    assert git.classify_checkout(git_repo.root, git_repo.root) == git.CheckoutRelation(
        "primary"
    )
    assert git.classify_checkout(git_repo.root, worktree) == git.CheckoutRelation(
        "linked"
    )
    # The verdict is by common dir, so it holds from a linked worktree too —
    # the recurring runner sweeps from one.
    assert git.classify_checkout(worktree, git_repo.root).kind == "primary"
    assert git.classify_checkout(worktree, worktree).kind == "linked"


def test_classify_checkout_other_repositories(git_repo, tmp_path):
    other_root = tmp_path / "other-root"
    other_root.mkdir()
    other = init_git_repo(other_root)
    foreign = tmp_path / "other-wt"
    other.git("worktree", "add", "-b", "fix", str(foreign), "main")
    clone = tmp_path / "clone"
    git_repo.git("clone", "-q", str(git_repo.root), str(clone), cwd=tmp_path)

    assert git.classify_checkout(git_repo.root, foreign) == git.CheckoutRelation(
        "foreign-linked", owner=other.root.resolve()
    )
    assert git.classify_checkout(git_repo.root, other.root) == git.CheckoutRelation(
        "foreign-primary", owner=other.root.resolve()
    )
    assert git.classify_checkout(git_repo.root, clone) == git.CheckoutRelation(
        "foreign-primary", owner=clone.resolve()
    )


def test_classify_checkout_has_no_answer_for_what_it_cannot_prove(git_repo, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    # A directory inside the primary checkout is not the checkout itself.
    inside = git_repo.root / "coga"

    assert git.classify_checkout(git_repo.root, plain) is None
    assert git.classify_checkout(git_repo.root, inside) is None
    assert git.classify_checkout(git_repo.root, tmp_path / "missing") is None
    assert git.classify_checkout(plain, git_repo.root) is None


def test_union_merge_paths_reads_gitattributes(git_repo):
    assert git.union_merge_paths(git_repo.root, ["coga/log.md", "coga/tasks/x.md"]) == {
        "coga/log.md"
    }


def test_summarize_git_failure_keeps_only_actionable_lines():
    raw = dedent(
        """
        Rebasing (1/14)
        error: could not apply 09b7e643... Ticket: write-real-docs — active
        hint: Resolve all conflicts manually, mark them as resolved with
        Created autostash: 99273fe4
        Auto-merging coga/log.md
        CONFLICT (content): Merge conflict in coga/tasks/write-real-docs.md
        """
    )
    summary = git.summarize_git_failure(raw)
    assert "error: could not apply 09b7e643" in summary
    assert "CONFLICT (content): Merge conflict in coga/tasks/write-real-docs.md" in summary
    assert "Rebasing" not in summary
    assert "hint:" not in summary


def test_summarize_git_failure_dedupes_and_falls_back_to_last_line():
    raw = (
        "Rebasing (1/2)\rRebasing (2/2)\rerror: could not apply abc123... x\n"
        "error: could not apply abc123... x\n"
    )
    assert git.summarize_git_failure(raw) == "error: could not apply abc123... x"
    assert git.summarize_git_failure("some odd message\nfinal line\n") == "final line"
    assert git.summarize_git_failure("") == ""


@pytest.mark.parametrize(
    "heading",
    [
        "error: Your local changes to the following files would be overwritten by merge:",
        "error: The following untracked working tree files would be overwritten by merge:",
    ],
)
def test_summarize_git_failure_keeps_overwrite_paths(heading):
    raw = (
        f"Updating abc123..def456\n{heading}\n"
        "\t leading and trailing spaces.md \n"
        "\t \n"
        "\tcoga/log.md\n"
        "\tdocs/a file with spaces.md\n"
        '\t"quoted\\tpath.md"\n'
        "Please commit your changes or stash them before you merge.\n"
        "\tunrelated indented advice\n"
        "Aborting\n"
    )

    assert git.summarize_git_failure(raw) == (
        f"{heading}  leading and trailing spaces.md ,  , "
        "coga/log.md, docs/a file with spaces.md, "
        '"quoted\\tpath.md"'
    )


@pytest.mark.parametrize("path_count", [10, 12])
@pytest.mark.parametrize("trailer", ["", "Aborting\nfatal: merge failed\n"])
def test_summarize_git_failure_bounds_overwrite_paths(path_count, trailer):
    heading = "error: Your local changes to the following files would be overwritten by merge:"
    paths = [f"file-{index:02}.md" for index in range(path_count)]
    raw = heading + "\n" + "".join(f"\t{path}\n" for path in paths) + trailer
    expected = f"{heading} " + ", ".join(paths[:10])
    if path_count > 10:
        expected += f", ... (+{path_count - 10} more files)"
    if trailer:
        expected += "; fatal: merge failed"

    assert git.summarize_git_failure(raw) == expected


def test_windows_git_env_keeps_auto_maintenance_attached():
    env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "x"}
    git._keep_maintenance_attached(env)
    assert env == {
        "GIT_CONFIG_COUNT": "3",
        "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "x",
        "GIT_CONFIG_KEY_1": "gc.autoDetach", "GIT_CONFIG_VALUE_1": "false",
        "GIT_CONFIG_KEY_2": "maintenance.autoDetach", "GIT_CONFIG_VALUE_2": "false",
    }


@pytest.mark.skipif(os.name != "nt", reason="the detach override is Windows-only")
def test_git_env_on_windows_disables_detached_maintenance(git_repo):
    env = git._git_env()
    for key in ("gc.autoDetach", "maintenance.autoDetach"):
        value = subprocess.run(
            ["git", "-C", str(git_repo.root), "config", "--get", key],
            env=env, capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert value == "false"


def test_git_env_keeps_the_ambient_locale_unless_pinned(monkeypatch):
    monkeypatch.setenv("LC_ALL", "de_DE.UTF-8")

    assert git._git_env()["LC_ALL"] == "de_DE.UTF-8"
    assert git._git_env(git._MESSAGE_LOCALE)["LC_ALL"] == "C"


def test_summarize_git_failure_dedupes_complete_overwrite_lists():
    heading = "error: Your local changes to the following files would be overwritten by merge:"
    raw = (
        f"{heading}\n\tfirst.md\nAborting\n"
        f"{heading}\n\tsecond.md\nAborting\n"
        f"{heading}\n\tfirst.md\nAborting\n"
    )

    assert git.summarize_git_failure(raw) == (
        f"{heading} first.md; {heading} second.md"
    )


# --- CLI integration ------------------------------------------------------------


def test_cli_block_syncs_blocker_to_origin(git_repo):
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    activated = runner.invoke(app, ["mark", "active", slug])
    assert activated.exit_code == 0, activated.output

    blocked = runner.invoke(
        app, ["block", "--task", slug, "--reason", "retry ceiling unspecified"]
    )
    assert blocked.exit_code == 0, blocked.output

    assert git_repo.origin_subjects()[0] == f"Ticket: {slug} — blocked"
    assert "retry ceiling unspecified" in _control(git_repo, f"coga/tasks/{slug}.md")
    assert _ahead_of_origin(git_repo) == 0
    assert git_repo.git("stash", "list") == ""


def test_cli_block_from_feature_branch_leaves_code_untouched(git_repo):
    result = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = result.output.split(":", 1)[0].strip()
    assert runner.invoke(app, ["mark", "active", slug]).exit_code == 0
    git_repo.checkout_branch("feature/x")
    (git_repo.root / "wip.py").write_text("# half-written change\n", encoding="utf-8", newline="\n")

    blocked = runner.invoke(
        app, ["block", "--task", slug, "--reason", "blocked on design"]
    )
    assert blocked.exit_code == 0, blocked.output

    assert git_repo.origin_subjects()[0] == f"Ticket: {slug} — blocked"
    assert not git_repo.origin_tracks("wip.py")
    assert "wip.py" in git_repo.git("status", "--porcelain")
    assert git_repo.git("log", "-1", "--format=%s").strip() != f"Ticket: {slug} — blocked"


def test_cli_delete_from_linked_worktree_keeps_primary_checkout(
    git_repo, monkeypatch, tmp_path
):
    """Retro's isolated delete reaches origin without refreshing primary main."""
    created = runner.invoke(app, ["create", "Demo task", "--workflow", "code"])
    slug = created.output.split(":", 1)[0].strip()
    rel = f"coga/tasks/{slug}.md"
    primary_tip = git_repo.git("rev-parse", "HEAD").strip()
    primary_ticket = git_repo.root / rel
    assert primary_ticket.is_file()

    worktree = tmp_path / "retro-delete-worktree"
    git_repo.git("worktree", "add", "-b", "retro-delete-test", str(worktree), "main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        monkeypatch.chdir(worktree / "coga")
        deleted = runner.invoke(app, ["delete", slug, "--keep-control-checkout"])
        assert deleted.exit_code == 0, deleted.output
        git.sync_coga_state(load_config(worktree / "coga"))

        assert not git_repo.origin_tracks(rel)
        assert f"Ticket: {slug} — deleted" in git_repo.origin_subjects()
        # The primary checkout is intentionally stale but internally coherent.
        assert git_repo.git("rev-parse", "HEAD").strip() == primary_tip
        assert git_repo.git("rev-parse", "main").strip() == primary_tip
        assert primary_ticket.is_file()
        assert git_repo.git("status", "--porcelain", cwd=git_repo.root) == ""
        assert not (worktree / rel).exists()
    finally:
        monkeypatch.chdir(git_repo.coga_os)
        git_repo.git("worktree", "remove", "--force", str(worktree))


# --- `recurring --all` child: one sweep, from the control worktree ------------
#
# An off-control host child services the repo from a temporary control-branch
# worktree, whose inner CLI performs the real catch-all sweep. The outer child
# must not sweep the host feature checkout on top of that.


_RECURRING_ALL_CHILD_ARGV = ["coga", "run", "recurring-scan", "--require-fresh-control"]


def test_recurring_all_child_does_not_sweep_the_off_control_host(
    git_repo, monkeypatch
):
    from coga import cli

    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed", "--allow-empty")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/wip")
    wip = git_repo.coga_os / "contexts" / "wip" / "SKILL.md"
    wip.parent.mkdir(parents=True)
    wip.write_text("---\nname: wip\n---\n\nunfinished\n", encoding="utf-8", newline="\n")
    before = git_repo.origin_subjects()
    monkeypatch.setattr(cli, "_register_alias_placeholder", lambda *_: None)
    dispatched: list[bool] = []
    monkeypatch.setattr(cli, "app", lambda: dispatched.append(True))
    monkeypatch.setattr(cli.sys, "argv", list(_RECURRING_ALL_CHILD_ARGV))

    cli.main()

    assert dispatched == [True]
    assert git_repo.origin_subjects() == before
    assert not git_repo.origin_tracks("coga/contexts/wip/SKILL.md")
    assert "?? coga/contexts/" in git_repo.git("status", "--porcelain")


def test_recurring_all_child_retains_the_control_worktree_sweep(
    git_repo, monkeypatch
):
    """On control this is the inner child (or a direct run) and still sweeps."""
    from coga import cli

    cfg = load_config(git_repo.coga_os)
    calls: list[Config] = []
    monkeypatch.setattr(cli.git, "sync_coga_state", calls.append)
    monkeypatch.setattr(cli.sys, "argv", list(_RECURRING_ALL_CHILD_ARGV))

    cli._sweep_coga_state(cfg)

    assert len(calls) == 1
    assert calls[0].repo_root == cfg.repo_root


def test_recurring_all_child_sweeps_on_control_despite_a_same_named_tag(
    git_repo, monkeypatch
):
    """`rev-parse --abbrev-ref HEAD` answers `heads/main` once a tag `main`
    exists; the probe must still read the control checkout as on control."""
    from coga import cli

    cfg = load_config(git_repo.coga_os)
    git_repo.git("tag", cfg.git_control_branch)
    calls: list[Config] = []
    monkeypatch.setattr(cli.git, "sync_coga_state", calls.append)
    monkeypatch.setattr(cli.sys, "argv", list(_RECURRING_ALL_CHILD_ARGV))

    cli._sweep_coga_state(cfg)

    assert len(calls) == 1


def test_ordinary_run_still_sweeps_off_control(git_repo, monkeypatch):
    """Only the `recurring --all` child shape is exempt: the documented
    publish-from-any-branch contract of every other mutating command holds."""
    from coga import cli

    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/wip")
    calls: list[Config] = []
    monkeypatch.setattr(cli.git, "sync_coga_state", calls.append)
    monkeypatch.setattr(cli.sys, "argv", ["coga", "run", "autoclose"])

    cli._sweep_coga_state(cfg)

    assert len(calls) == 1


def test_worktree_holding_branch_finds_a_linked_checkout(git_repo, tmp_path):
    """The public lookup names the worktree holding a branch, or None."""
    assert git.worktree_holding_branch(git_repo.root, "main") == git_repo.root

    git_repo.git("checkout", "-b", "feature/lookup")
    linked = tmp_path / "linked"
    git_repo.git("worktree", "add", str(linked), "main")

    assert git.worktree_holding_branch(git_repo.root, "main") == linked
    assert git.worktree_holding_branch(git_repo.root, "nope") is None


def test_worktree_holding_branch_raises_when_the_listing_fails(tmp_path):
    """Unlike the ref-update variant, it does not fold failure into a sentinel."""
    with pytest.raises(git.GitError):
        git.worktree_holding_branch(tmp_path, "main")


# --- prepare_control_checkout -----------------------------------------------------


def _head(git_repo) -> tuple[str, str]:
    """(current branch, HEAD commit) of the main test checkout."""
    return (
        git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        git_repo.git("rev-parse", "HEAD").strip(),
    )


def _origin_tip(git_repo) -> str:
    return git_repo.git("rev-parse", "main", cwd=git_repo.origin).strip()


def _assert_prepared(git_repo, outcome) -> None:
    assert outcome.kind == "prepared", outcome
    assert outcome.commit == _origin_tip(git_repo)
    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert _dirty(git_repo) == set()


def _feature_with_published_ticket(git_repo, cfg: Config) -> Path:
    """A feature checkout whose ticket edit is published to control but still dirty here."""
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    ticket.write_text(_ticket_text(blackboard="handoff\n"), encoding="utf-8", newline="\n")
    assert git.publish(cfg, [ticket], "Ticket: demo — handoff") is True
    assert _dirty(git_repo) == {"coga/tasks/demo.md"}
    return ticket


def test_prepare_moves_a_clean_feature_checkout_to_a_fresh_control(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(step="2 (review)"))

    outcome = git.prepare_control_checkout(cfg)

    _assert_prepared(git_repo, outcome)
    assert "step: 2 (review)" in ticket.read_text(encoding="utf-8")
    # The feature branch is kept, never deleted.
    assert git_repo.git("branch", "--list", "feature/x").strip()


def test_prepare_fast_forwards_a_behind_control_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.push_competing_commit("other.txt", "remote\n")

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert (git_repo.root / "other.txt").read_text(encoding="utf-8") == "remote\n"


@pytest.mark.parametrize("shape", ["ahead", "diverged"])
def test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing(git_repo, shape):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "local.txt")
    git_repo.git("commit", "-m", "local unpushed")
    if shape == "diverged":
        git_repo.push_competing_commit("other.txt", "remote\n")
    git_repo.checkout_branch("feature/x")
    before = _head(git_repo)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("main",)
    assert "git pull --rebase --autostash origin main" in outcome.reason
    assert _head(git_repo) == before


def test_prepare_refuses_a_detached_head(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("checkout", "--detach", "HEAD")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "detached" in outcome.reason
    assert git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "HEAD"


def test_prepare_refuses_an_in_progress_merge(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    (git_repo.root / "a.txt").write_text("feature\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "a.txt")
    git_repo.git("commit", "-m", "feature a")
    git_repo.git("checkout", "main")
    (git_repo.root / "a.txt").write_text("main\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "a.txt")
    git_repo.git("commit", "-m", "main a")
    git_repo.git("push", "origin", "main")
    git_repo.git("checkout", "feature/x")
    subprocess.run(
        ["git", "-C", str(git_repo.root), "merge", "main"], capture_output=True, check=False
    )

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "merge is in progress" in outcome.reason
    assert _head(git_repo)[0] == "feature/x"


def test_prepare_refuses_when_control_is_held_by_another_worktree(git_repo, tmp_path):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    linked = tmp_path / "held"
    git_repo.git("worktree", "add", str(linked), "main")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert f"git worktree remove {linked}" in outcome.reason
    assert _head(git_repo)[0] == "feature/x"


def test_prepare_cleans_a_published_ticket_edit_from_a_feature_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert "handoff" in ticket.read_text(encoding="utf-8")


@pytest.mark.parametrize("relocated", [False, True])
def test_prepare_cleans_a_published_context_and_skill_from_a_feature_checkout(
    git_repo, relocated
):
    """Checkout return reads the publication roots: a context or skill the
    sweep landed is proven and cleaned, not refused as foreign dirt."""
    if relocated:
        contexts = git_repo.root / "docs" / "contexts"
        contexts.mkdir(parents=True)
        (contexts / ".gitkeep").write_text("", encoding="utf-8", newline="\n")
        with (git_repo.coga_os / "coga.toml").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write('[layout]\ncontexts = "docs/contexts"\n')
        git_repo.git("add", "-A")
        git_repo.git("commit", "-m", "relocate contexts")
        git_repo.git("push", "origin", "main")
    cfg = load_config(git_repo.coga_os)
    git_repo.checkout_branch("feature/x")
    context = cfg.contexts_root / "team" / "SKILL.md"
    skill = git_repo.coga_os / "skills" / "team" / "SKILL.md"
    for path in (context, skill):
        path.parent.mkdir(parents=True)
        path.write_text("authored on the branch\n", encoding="utf-8", newline="\n")

    git.sync_coga_state(cfg)

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert context.read_text(encoding="utf-8") == skill.read_text(encoding="utf-8") == "authored on the branch\n"


def test_prepare_still_refuses_dirty_source_outside_the_coga_roots(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    (git_repo.root / "src.py").write_text("unreviewed code\n", encoding="utf-8", newline="\n")

    git.sync_coga_state(cfg)
    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("src.py (not Coga state)",)
    assert not git_repo.origin_tracks("src.py")


def test_prepare_realigns_over_a_hand_committed_context_already_on_control(git_repo, capsys):
    """State-only commit recovery uses the same roots: a local commit of a
    context control already carries is realigned, not refused as foreign."""
    cfg = load_config(git_repo.coga_os)
    tip = _hand_commit(git_repo, "coga/contexts/team/SKILL.md", "decision\n")
    git_repo.push_competing_commit("coga/contexts/team/SKILL.md", "decision\n")

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert tip[:12] in capsys.readouterr().err


@pytest.mark.parametrize("autocrlf", ["input", "true"])
def test_a_crlf_working_copy_publishes_the_blob_git_add_stages(git_repo, autocrlf):
    """Under `core.autocrlf`, publish must hash through the clean filters.

    Raw bytes landed a CRLF blob on control while `git add` staged LF, so
    the staged copy never matched and the checkout return refused forever.
    """
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("config", "core.autocrlf", autocrlf)
    git_repo.checkout_branch("feature/x")
    task = git_repo.coga_os / "tasks" / "recurring" / "sweep"
    task.mkdir(parents=True)
    (task / "ticket.md").write_bytes(_ticket_text(blackboard="Café — 語\n").replace("\n", "\r\n").encode())
    (task / "ticket.py").write_bytes(b"print('hi')\r\nraise SystemExit(0)\r\n")
    git_repo.git("add", "--", "coga/tasks/recurring/sweep")
    assert git.publish(cfg, [task], "Recurring: create sweep") is True

    published = subprocess.run(
        ["git", "show", "main:coga/tasks/recurring/sweep/ticket.py"],
        cwd=git_repo.origin, capture_output=True, check=True,
    ).stdout
    assert published == b"print('hi')\nraise SystemExit(0)\n"
    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))


def test_prepare_cleans_published_untracked_and_deleted_state(git_repo):
    cfg = load_config(git_repo.coga_os)
    gone = _seed_ticket(git_repo, slug="gone")
    git_repo.checkout_branch("feature/x")
    fresh = git_repo.coga_os / "tasks" / "fresh" / "ticket.md"
    fresh.parent.mkdir(parents=True)
    fresh.write_text(_ticket_text(), encoding="utf-8", newline="\n")
    gone.unlink()
    assert git.publish(cfg, [fresh.parent, gone], "Ticket: create and delete") is True

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert fresh.read_text(encoding="utf-8") == _ticket_text()
    assert not gone.exists()


def test_prepare_proves_a_union_log_published_after_control_moved(git_repo):
    """Control gained log lines after the branch point: byte equality can
    never hold on the feature branch, but every local line is on control."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    git_repo.push_competing_commit("coga/log.md", "peer line\n")
    append_log(cfg, "demo", "agent:claude", "my line")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True
    assert (git_repo.coga_os / "log.md").read_bytes() != _control(
        git_repo, "coga/log.md"
    ).encode()

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    log = (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
    assert "peer line" in log and "my line" in log


def test_prepare_refuses_an_unpublished_log_line(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    append_log(cfg, "demo", "agent:claude", "published")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True
    git_repo.checkout_branch("feature/x")
    append_log(cfg, "demo", "agent:claude", "not published")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("coga/log.md (lines not yet on control)",)
    assert "not published" in (git_repo.coga_os / "log.md").read_text(encoding="utf-8")


def _publish_feature_log_twice(git_repo, cfg: Config) -> None:
    """A feature checkout publishes once after a peer line, then publishes again.

    HEAD never advances, so the second publish still merges from the old base
    while control already carries this checkout's first line.
    """
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    base = _control(git_repo, "coga/log.md") or ""
    git_repo.push_competing_commit("coga/log.md", base + "peer line\n")
    append_log(cfg, "demo", "agent:claude", "mine one")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True
    append_log(cfg, "demo", "agent:claude", "mine two")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True


def test_feature_checkout_second_publish_does_not_re_add_a_landed_line(git_repo):
    cfg = load_config(git_repo.coga_os)
    _publish_feature_log_twice(git_repo, cfg)

    landed = _control(git_repo, "coga/log.md")
    assert landed.count("mine one") == 1
    assert landed.count("peer line") == 1
    assert landed.count("mine two") == 1


def test_prepare_proves_a_feature_log_published_twice(git_repo):
    cfg = load_config(git_repo.coga_os)
    _publish_feature_log_twice(git_repo, cfg)

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    log = (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
    assert log.count("mine one") == 1 and "mine two" in log


def test_publish_from_a_far_back_merge_base_lands_no_duplicate(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    base = _control(git_repo, "coga/log.md") or ""
    for count in range(1, 4):
        git_repo.push_competing_commit(
            "coga/log.md", base + "".join(f"peer {n}\n" for n in range(1, count + 1))
        )
    # The working log carries control's later lines at different positions.
    git.log_path(cfg).write_text(base + "peer 2\npeer 1\nmine\n", encoding="utf-8", newline="\n")

    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo") is True

    assert _control(git_repo, "coga/log.md") == base + "peer 1\npeer 2\npeer 3\nmine\n"


def _blob(git_repo, data: bytes) -> str:
    path = git_repo.origin.parent / "blob-input"
    path.write_bytes(data)
    return git_repo.git("hash-object", "-w", str(path)).strip()


@pytest.mark.parametrize(
    ("working", "reason"),
    [
        ("A Y X", None),
        ("A X", None),
        ("A Z X", "lines not yet on control"),
    ],
)
def test_published_proof_filters_lines_already_on_control(git_repo, working, reason):
    control = ("100644", _blob(git_repo, _lines("A X Y")))
    head = ("100644", _blob(git_repo, _lines("A")))

    proof = git._published_proof(
        git_repo.root, "coga/log.md", ("100644", _lines(working)), control,
        head_entry=head, union=True,
    )

    assert proof == reason


def test_prepare_refuses_mixed_state_without_partial_cleanup(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    (git_repo.root / "src.py").write_text("feature work\n", encoding="utf-8", newline="\n")
    edited = ticket.read_text(encoding="utf-8")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("src.py (not Coga state)",)
    assert ticket.read_text(encoding="utf-8") == edited
    assert _dirty(git_repo) == {"coga/tasks/demo.md", "src.py"}
    assert _head(git_repo)[0] == "feature/x"


def test_prepare_refuses_staged_content_that_is_not_published(git_repo):
    """The working copy matches control, but the index holds a third version."""
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    published = ticket.read_text(encoding="utf-8")
    ticket.write_text(_ticket_text(blackboard="staged draft\n"), encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/tasks/demo.md")
    ticket.write_text(published, encoding="utf-8", newline="\n")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "staged content" in outcome.blocking[0]
    assert "staged draft" in git_repo.git("show", ":coga/tasks/demo.md")


@pytest.mark.parametrize("on_control", [False, True])
@pytest.mark.parametrize("stage_renames", [False, True])
def test_publish_then_prepare_preserves_distinct_staged_renames(
    git_repo, on_control, stage_renames,
):
    cfg = load_config(git_repo.coga_os)
    old = [_seed_ticket(git_repo, slug=f"old-{i}") for i in range(3)]
    if not on_control:
        git_repo.checkout_branch("feature/chat")
    new = [path.with_name(f"new-{i}.md") for i, path in enumerate(old)]
    for source, destination in zip(old, new):
        source.rename(destination)
    if stage_renames:
        git_repo.git("add", "--all", "--", "coga/tasks")
    for path in new:
        path.write_text(_ticket_text(blackboard="working prose\n"), encoding="utf-8", newline="\n")
    before_head = _head(git_repo)
    before_index = git_repo.git("ls-files", "--stage")
    working = [path.read_bytes() for path in new]

    assert git.publish(cfg, git.coga_root_paths(cfg), "Rename tickets")

    for source, destination in zip(old, new):
        assert _control(git_repo, source.relative_to(git_repo.root).as_posix()) is None
        assert "working prose" in _control(git_repo, destination.relative_to(git_repo.root).as_posix())
    if stage_renames:
        assert _head(git_repo) == before_head
        assert git_repo.git("ls-files", "--stage") == before_index
    before = _snapshot(git_repo)
    refs = git_repo.git("show-ref")
    outcome = git.prepare_control_checkout(cfg)

    if stage_renames:
        assert outcome.kind == "refused"
        assert len(outcome.blocking) == 3
        destinations = [o for o in outcome.observations if o.index == "differs"]
        assert len(destinations) == 3
        assert all(o.working == "matches" for o in destinations)
        assert outcome.commit == git_repo.git("rev-parse", "origin/main").strip()
        assert _snapshot(git_repo) == before
        assert git_repo.git("show-ref") == refs
        assert [path.read_bytes() for path in new] == working
    else:
        _assert_prepared(git_repo, outcome)
        assert not any(path.exists() for path in old)
        assert [path.read_bytes() for path in new] == working


def test_control_publication_preserves_staged_draft_before_any_landed_staging(git_repo):
    cfg = load_config(git_repo.coga_os)
    first = _seed_ticket(git_repo, slug="a")
    draft = _seed_ticket(git_repo, slug="z")
    draft.write_text(_ticket_text(blackboard="unique staged intent\n"), encoding="utf-8", newline="\n")
    git_repo.git("add", "--", "coga/tasks/z.md")
    for path in (first, draft):
        path.write_text(_ticket_text(blackboard="working prose\n"), encoding="utf-8", newline="\n")
    before = _snapshot(git_repo)

    assert git.publish(cfg, git.coga_root_paths(cfg), "Working state")

    assert "working prose" in _control(git_repo, "coga/tasks/z.md")
    assert _snapshot(git_repo) == before
    assert "unique staged intent" in git_repo.git("show", ":coga/tasks/z.md")
    assert git.prepare_control_checkout(cfg).kind == "refused"


@pytest.mark.parametrize("on_control", [False, True])
def test_exact_staged_rename_still_publishes_and_returns(git_repo, on_control):
    cfg = load_config(git_repo.coga_os)
    old = _seed_ticket(git_repo)
    if not on_control:
        git_repo.checkout_branch("feature/chat")
    new = old.with_name("renamed.md")
    old.rename(new)
    git_repo.git("add", "--all", "--", "coga/tasks")

    assert git.publish(cfg, git.coga_root_paths(cfg), "Exact rename")
    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert not old.exists() and new.exists()


@pytest.mark.parametrize("on_control", [False, True])
def test_staged_union_log_draft_is_not_proved_by_published_working_lines(git_repo, on_control):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    append_log(cfg, "demo", "agent:claude", "seed")
    git.publish(cfg, [git.log_path(cfg)], "seed log")
    if not on_control:
        git_repo.checkout_branch("feature/chat")
    log = git.log_path(cfg)
    original = log.read_bytes()
    append_log(cfg, "demo", "agent:claude", "unique staged draft")
    git_repo.git("add", "--", "coga/log.md")
    log.write_bytes(original)
    append_log(cfg, "demo", "agent:claude", "working event")
    before = _snapshot(git_repo)

    assert git.publish(cfg, [log], "Working log")
    assert "working event" in _control(git_repo, "coga/log.md")
    assert git_repo.git("ls-files", "--stage") == before[2]
    before_return = _snapshot(git_repo)
    outcome = git.prepare_control_checkout(cfg)
    assert outcome.kind == "refused"
    assert "staged content" in outcome.blocking[0]
    assert outcome.observations[0].working in {"matches", "published"}
    assert _snapshot(git_repo) == before_return


def test_control_publication_rechecks_index_before_staging_any_path(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(blackboard="working prose\n"), encoding="utf-8", newline="\n")
    working = ticket.read_bytes()
    real = git.run_git
    real_modes = git._index_modes
    probes = 0
    reading_modes = False

    def modes(root):  # type: ignore[no-untyped-def]
        # Windows also reads index modes (Git owns executable bits there);
        # that lookup is not one of the staging rechecks this test races.
        nonlocal reading_modes
        reading_modes = True
        try:
            return real_modes(root)
        finally:
            reading_modes = False

    def race(root, *args, **kwargs):
        nonlocal probes
        if args[:3] == ("ls-files", "--stage", "-z") and not reading_modes:
            probes += 1
            if probes == 2:
                ticket.write_text(_ticket_text(blackboard="concurrent staged draft\n"), encoding="utf-8", newline="\n")
                git_repo.git("add", "--", "coga/tasks/demo.md")
                ticket.write_bytes(working)
        return real(root, *args, **kwargs)

    monkeypatch.setattr(git, "run_git", race)
    monkeypatch.setattr(git, "_index_modes", modes)
    head = _head(git_repo)
    assert git.publish(cfg, [ticket], "Working prose")
    assert probes == 2
    assert _head(git_repo) == head
    assert ticket.read_bytes() == working
    assert "concurrent staged draft" in git_repo.git("show", ":coga/tasks/demo.md")


@windows_skip("POSIX filesystem mode bits and permissions")
def test_prepare_refuses_a_mode_change_with_equal_bytes(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    ticket.chmod(0o755)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "file mode" in outcome.blocking[0]


def test_prepare_refuses_a_symlinked_state_file(git_repo, tmp_path):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    target = tmp_path / "elsewhere.md"
    target.write_text(_ticket_text(), encoding="utf-8", newline="\n")
    (git_repo.coga_os / "tasks" / "linked.md").symlink_to(target)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("coga/tasks/linked.md (not a regular file)",)
    assert (git_repo.coga_os / "tasks" / "linked.md").is_symlink()


def test_prepare_refuses_an_ignored_file_the_move_would_overwrite(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    (git_repo.root / ".gitignore").write_text(
        "coga/coga.local.toml\ncoga/.agent-skills/\nbuild/\n",
        encoding="utf-8", newline="\n",
    )
    git_repo.git("add", ".gitignore")
    git_repo.git("commit", "-m", "ignore build")
    git_repo.git("checkout", "main")
    git_repo.push_competing_commit("build/out.txt", "published\n")
    git_repo.git("checkout", "feature/x")
    (git_repo.root / "build").mkdir()
    (git_repo.root / "build" / "out.txt").write_text("local only\n", encoding="utf-8", newline="\n")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("build/out.txt",)
    assert (git_repo.root / "build" / "out.txt").read_text(encoding="utf-8") == "local only\n"


def test_prepare_refuses_when_evidence_changes_before_mutation(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    real = git._plan_preparation
    calls = []

    def plan_then_edit(*args, **kwargs):
        plan = real(*args, **kwargs)
        if not calls:
            ticket.write_text(_ticket_text(blackboard="concurrent edit\n"), encoding="utf-8", newline="\n")
        calls.append(plan)
        return plan

    monkeypatch.setattr(git, "_plan_preparation", plan_then_edit)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "concurrent edit" in ticket.read_text(encoding="utf-8")
    assert _head(git_repo)[0] == "feature/x"


def _sibling_publishes_a_log_line(git_repo) -> str:
    """What a sibling worktree's publish leaves in the shared refs.

    It pushes a log line, its push advances `origin/main`, and its
    fast-forward moves the shared local `main`: this checkout's own state lock
    never sees it. Returns the new control commit.
    """
    git_repo.push_competing_commit("coga/log.md", "- sibling launch\n")
    git_repo.git("fetch", "--quiet", "origin", "+refs/heads/main:refs/remotes/origin/main")
    tip = git_repo.git("rev-parse", "refs/remotes/origin/main").strip()
    git_repo.git("update-ref", "refs/heads/main", tip)
    return tip


@pytest.mark.parametrize("call", [0, 1], ids=["plan", "re-observation"])
def test_prepare_repins_when_control_moves_under_it(git_repo, monkeypatch, call):
    """The 2026-10-16 shape: control moved forward after the pin was taken.

    A publish between the pin and the read of local `main` made local look
    ahead of a stale pin and refused `unpublished`; it must re-pin instead,
    including when the move lands between the plan and its re-observation.
    """
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    real = git._plan_preparation
    calls = []

    def plan_with_interleaved_publish(*args, **kwargs):
        if len(calls) == call:
            calls.append(_sibling_publishes_a_log_line(git_repo))
        else:
            calls.append(None)
        return real(*args, **kwargs)

    monkeypatch.setattr(git, "_plan_preparation", plan_with_interleaved_publish)

    outcome = git.prepare_control_checkout(cfg)

    moved = next(tip for tip in calls if tip is not None)
    _assert_prepared(git_repo, outcome)
    assert outcome.commit == moved
    assert (git_repo.coga_os / "log.md").read_text(encoding="utf-8") == "- sibling launch\n"


@pytest.mark.parametrize("on_control", [False, True], ids=["feature", "control"])
def test_prepare_retries_a_delayed_published_control_advance(
    git_repo, monkeypatch, on_control,
):
    """A sibling's push and its local fast-forward are separate operations."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    if not on_control:
        git_repo.checkout_branch("feature/x")
    real = git._plan_preparation
    calls = []
    moved = []

    def plan_with_delayed_fast_forward(*args, **kwargs):
        plan = real(*args, **kwargs)
        if not calls:
            git_repo.push_competing_commit("coga/log.md", "- sibling launch\n")
            git_repo.git("fetch", "--quiet", "origin")
            moved.append(git_repo.git("rev-parse", "origin/main").strip())
        elif len(calls) == 1:
            if on_control:
                git_repo.git("merge", "--ff-only", "--quiet", moved[0])
            else:
                git_repo.git("update-ref", "refs/heads/main", moved[0])
        calls.append(plan)
        return plan

    monkeypatch.setattr(git, "_plan_preparation", plan_with_delayed_fast_forward)

    outcome = git.prepare_control_checkout(cfg)

    _assert_prepared(git_repo, outcome)
    assert outcome.commit == moved[0]
    assert (git_repo.coga_os / "log.md").read_text(encoding="utf-8") == "- sibling launch\n"


@pytest.mark.parametrize("change", ["working", "index", "branch", "head"])
def test_prepare_refuses_other_changes_during_a_published_control_advance(
    git_repo, monkeypatch, change,
):
    """Published control moving must not hide other changed evidence."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    published = _ticket_text(blackboard="already published\n")
    git_repo.push_competing_commit("coga/tasks/demo.md", published)
    if change == "index":
        ticket.write_text(published, encoding="utf-8", newline="\n")
    real = git._plan_preparation
    snapshots = []

    def plan_then_change(*args, **kwargs):
        plan = real(*args, **kwargs)
        if not snapshots:
            git_repo.git("update-ref", "refs/heads/main", "origin/main")
            if change == "working":
                ticket.write_text(published, encoding="utf-8", newline="\n")
            elif change == "index":
                git_repo.git("add", "coga/tasks/demo.md")
            elif change == "branch":
                git_repo.checkout_branch("feature/y")
            else:
                git_repo.git("merge", "--ff-only", "--quiet", "origin/main")
            snapshots.append(_snapshot(git_repo))
        return plan

    monkeypatch.setattr(git, "_plan_preparation", plan_then_change)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "changed while it was being examined" in outcome.reason
    assert _snapshot(git_repo) == snapshots[0]


def test_prepare_bounds_retries_when_only_local_control_keeps_advancing(
    git_repo, monkeypatch,
):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    tips = []
    for number in range(git.PREPARATION_ATTEMPTS):
        git_repo.push_competing_commit("coga/log.md", f"- sibling {number}\n")
        tips.append(_origin_tip(git_repo))
    real = git._plan_preparation
    calls = []

    def plan_then_advance(*args, **kwargs):
        plan = real(*args, **kwargs)
        if len(calls) % 2 == 0:
            git_repo.git("update-ref", "refs/heads/main", tips[len(calls) // 2])
        calls.append(plan)
        return plan

    monkeypatch.setattr(git, "_plan_preparation", plan_then_advance)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "kept moving" in outcome.reason
    assert len(calls) == 2 * git.PREPARATION_ATTEMPTS
    assert _head(git_repo)[0] == "feature/x"
    assert _dirty(git_repo) == set()


def test_prepare_refuses_when_control_keeps_moving(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    real = git._plan_preparation
    lines = itertools.count()

    def plan_while_control_moves(*args, **kwargs):
        git_repo.push_competing_commit("coga/log.md", f"- sibling {next(lines)}\n")
        git_repo.git("fetch", "--quiet", "origin")
        return real(*args, **kwargs)

    monkeypatch.setattr(git, "_plan_preparation", plan_while_control_moves)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "kept moving" in outcome.reason
    assert _head(git_repo)[0] == "feature/x"


def test_fast_forward_treats_control_already_moved_past_new_as_level(git_repo, capsys):
    """A peer published past `new` before this caller read local control."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    stale = git_repo.git("rev-parse", "main").strip()
    moved = _sibling_publishes_a_log_line(git_repo)

    assert git.fast_forward_control(cfg, git_repo.root, stale) is True

    assert git_repo.git("rev-parse", "main").strip() == moved
    assert "note" not in capsys.readouterr().err


def test_prepare_is_exempt_without_git_or_a_remote(git_repo, tmp_path, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    assert git.prepare_control_checkout(replace(cfg, git_enabled=False)).kind == "exempt"
    git_repo.checkout_branch("feature/x")
    git_repo.git("remote", "remove", "origin")

    assert git.prepare_control_checkout(cfg).kind == "exempt"
    missing = git.prepare_control_checkout(cfg, require_remote_control=True)
    assert missing.kind == "refused"
    assert _head(git_repo)[0] == "feature/x"


def test_prepare_uses_the_configured_remote_and_control_names(git_repo):
    toml = git_repo.coga_os / "coga.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + '\n[git]\nremote = "upstream"\ncontrol_branch = "trunk"\n', encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "custom git names")
    git_repo.git("branch", "-m", "main", "trunk")
    git_repo.git("remote", "rename", "origin", "upstream")
    git_repo.git("push", "upstream", "trunk")
    git_repo.checkout_branch("feature/x")
    cfg = load_config(git_repo.coga_os)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "prepared", outcome
    assert _head(git_repo) == (
        "trunk",
        git_repo.git("rev-parse", "trunk", cwd=git_repo.origin).strip(),
    )


# --- realigning a state-only divergence ---------------------------------------


def _peer_commit(git_repo, mutate, message: str = "peer") -> None:
    """Commit `mutate(clone)`'s changes on origin/main from a peer clone."""
    clone = git_repo.origin.parent / "peer-clone"
    if not clone.exists():
        _clone(git_repo, "peer-clone")
    else:
        git_repo.git("pull", "--quiet", "--ff-only", "origin", "main", cwd=clone)
    mutate(clone)
    git_repo.git("add", "-A", cwd=clone)
    git_repo.git("commit", "-m", message, cwd=clone)
    git_repo.git("push", "--quiet", "origin", "main", cwd=clone)


def _subsumed_divergence(git_repo) -> tuple[str, str]:
    """Local main carries a hand-committed ticket edit whose bytes control
    already holds, and control moved on elsewhere: (hand commit, edited text)."""
    _seed_ticket(git_repo)
    hand = _ticket_text(blackboard="hand edit\n")
    tip = _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    git_repo.push_competing_commit("coga/tasks/demo.md", hand)
    git_repo.push_competing_commit("coga/tasks/other.md", _ticket_text())
    git_repo.git("fetch", "--quiet", "origin")
    return tip, hand


def _snapshot(git_repo) -> tuple[object, ...]:
    """HEAD, branch tip, index, working status, and operation markers."""
    git_dir = git_repo.root / ".git"
    return (
        _head(git_repo),
        git_repo.git("rev-parse", "main").strip(),
        git_repo.git("ls-files", "--stage"),
        git_repo.git("status", "--porcelain", "--untracked-files=all"),
        (git_repo.coga_os / "log.md").read_bytes() if (git_repo.coga_os / "log.md").exists() else None,
        sorted(marker for marker, _ in git._IN_PROGRESS_MARKERS if (git_dir / marker).exists()),
    )


def _subsumed(git_repo, cfg: Config, local: str = "main", target: str = "origin/main"):
    rev = lambda name: git_repo.git("rev-parse", name).strip()  # noqa: E731
    return git._local_control_subsumed(cfg, git_repo.root, rev(local), rev(target))


def test_launch_entry_order_recovers_a_hand_commit_with_unpublished_log_lines(git_repo):
    """The 2026-10-01 shape: a state-only hand commit on local main, log lines
    appended since, and control moved on another state path."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    append_log(cfg, "demo", "human:marc", "seeded")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "seed log")
    git_repo.git("push", "origin", "main")
    hand = _ticket_text(blackboard="hand edit\n")
    _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    append_log(cfg, "demo", "agent:claude", "unpublished one")
    append_log(cfg, "demo", "agent:claude", "unpublished two")
    git_repo.push_competing_commit("coga/tasks/other.md", _ticket_text())

    git.sync_coga_state(cfg)
    outcome = git.prepare_control_checkout(cfg)

    _assert_prepared(git_repo, outcome)
    assert _control(git_repo, "coga/tasks/demo.md") == hand
    log = _control(git_repo, "coga/log.md")
    assert "seeded" in log and "unpublished one" in log and "unpublished two" in log


def test_prepare_names_the_rebase_for_an_unpublished_hand_commit_and_retry_recovers(
    git_repo,
):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    append_log(cfg, "demo", "human:marc", "seeded")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "seed log")
    git_repo.git("push", "origin", "main")
    _hand_commit(git_repo, "coga/tasks/demo.md", _ticket_text(blackboard="hand edit\n"))
    append_log(cfg, "demo", "agent:claude", "unpublished line")
    # Control's copy of the same ticket moved after the merge base, on a line
    # well away from the hand edit: the sweep cannot carry the hand commit.
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(status="blocked"))

    git.sync_coga_state(cfg)
    before = _snapshot(git_repo)
    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused", outcome
    assert outcome.blocking == ("main", "coga/tasks/demo.md (content differs from control)")
    assert _snapshot(git_repo) == before
    command = "git pull --rebase --autostash origin main"
    assert f"run `{command}` on 'main', then retry" in outcome.reason
    pulled = subprocess.run(
        command.split(), cwd=git_repo.root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert pulled.returncode == 0, pulled.stderr

    git.sync_coga_state(cfg)
    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    ticket = _control(git_repo, "coga/tasks/demo.md")
    assert "status: blocked" in ticket and "hand edit" in ticket
    log = _control(git_repo, "coga/log.md")
    assert "seeded" in log and "unpublished line" in log


def test_prepare_remedy_says_to_switch_to_control_from_a_feature_branch(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    _hand_commit(git_repo, "coga/tasks/demo.md", _ticket_text(blackboard="hand\n"))
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(status="blocked"))
    git_repo.checkout_branch("feature/x")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert (
        "switch to 'main' (`git switch main`), run "
        "`git pull --rebase --autostash origin main` there" in outcome.reason
    )


def test_prepare_refuses_a_local_commit_touching_state_and_code(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    hand = _ticket_text(blackboard="hand\n")
    (git_repo.root / "local.txt").write_text("code\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "local.txt")
    _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    git_repo.push_competing_commit("coga/tasks/demo.md", hand)
    before = _snapshot(git_repo)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("main",)
    assert "touches local.txt" in outcome.reason
    assert "git pull --rebase --autostash origin main` and push" in outcome.reason
    assert _snapshot(git_repo) == before


def _hand_commit_after_offline_sync(git_repo, cfg: Config, *, code: bool) -> str:
    """The 2026-09-29 Multiply chain up to the divergence: an offline sync
    fails and keeps the ticket and its `sync failed` line dirty, an agent
    hand-commits that retained state (plus, with `code`, a non-state file)
    on `main`, the remote returns, and a peer advances control."""
    ticket = _seed_ticket(git_repo)
    url = git_repo.git("remote", "get-url", "origin").strip()
    git_repo.git("remote", "set-url", "origin", str(git_repo.origin.parent / "missing.git"))
    ticket.write_text(_ticket_text(status="blocked"), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is None
    assert _dirty(git_repo) == {"coga/tasks/demo.md", "coga/log.md"}
    if code:
        (git_repo.root / "local.txt").write_text("code\n", encoding="utf-8", newline="\n")
        git_repo.git("add", "local.txt")
    git_repo.git("add", "coga/tasks/demo.md", "coga/log.md")
    git_repo.git("commit", "-m", "hand commit of retained state")
    tip = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.git("remote", "set-url", "origin", url)
    git_repo.push_competing_commit("coga/tasks/other.md", _ticket_text())
    return tip


def test_a_hand_commit_of_state_an_offline_sync_retained_is_realigned(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    _hand_commit_after_offline_sync(git_repo, cfg, code=False)
    capsys.readouterr()

    git.sync_coga_state(cfg)

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert "sync failed" in _control(git_repo, "coga/log.md")
    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert _dirty(git_repo) == set()
    assert "realigned local 'main' to origin/main" in capsys.readouterr().err


def test_a_mixed_hand_commit_after_an_offline_sync_lands_state_and_keeps_main(
    git_repo, capsys
):
    cfg = load_config(git_repo.coga_os)
    tip = _hand_commit_after_offline_sync(git_repo, cfg, code=True)
    capsys.readouterr()

    git.sync_coga_state(cfg)

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert _head(git_repo) == ("main", tip)
    assert "git pull --rebase --autostash origin main" in capsys.readouterr().err


def test_prepare_realigns_from_a_feature_branch_with_no_control_holder(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    tip, hand = _subsumed_divergence(git_repo)
    git_repo.checkout_branch("feature/x")

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))

    assert (git_repo.coga_os / "tasks" / "demo.md").read_text(encoding="utf-8") == hand
    assert (git_repo.coga_os / "tasks" / "other.md").exists()
    err = capsys.readouterr().err
    assert err.count("[git] realigned local 'main'") == 1
    assert f"{tip[:12]} hand commit" in err and "reflog" in err
    assert tip in git_repo.git("reflog", "--format=%H", "main")


def test_prepare_realigns_a_subsumed_control_checkout_to_a_clean_tip(git_repo):
    cfg = load_config(git_repo.coga_os)
    _tip, hand = _subsumed_divergence(git_repo)
    append_log(cfg, "demo", "agent:claude", "already published")
    assert git.publish(cfg, [git.log_path(cfg)], "Log: demo", fast_forward=False) is True
    # Still diverged, with a dirty log whose lines control already carries.
    assert _dirty(git_repo) == {"coga/log.md"}

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert (git_repo.coga_os / "tasks" / "demo.md").read_text(encoding="utf-8") == hand
    assert "already published" in (git_repo.coga_os / "log.md").read_text(encoding="utf-8")


def test_prepare_refuses_when_the_realignment_proof_changes_before_apply(
    git_repo, monkeypatch
):
    cfg = load_config(git_repo.coga_os)
    _subsumed_divergence(git_repo)
    real = git._local_control_subsumed
    calls = []

    def drifting(*args, **kwargs):
        verdict = real(*args, **kwargs)
        calls.append(verdict)
        if len(calls) > 1:
            return replace(verdict, evidence=(*verdict.evidence, "drift"))
        return verdict

    monkeypatch.setattr(git, "_local_control_subsumed", drifting)
    before = _snapshot(git_repo)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "changed while it was being examined" in outcome.reason
    assert len(calls) == 2
    assert _snapshot(git_repo) == before


def test_refresh_realigns_a_subsumed_diverged_control_checkout(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    tip, hand = _subsumed_divergence(git_repo)

    assert git.refresh(cfg) is True

    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert _dirty(git_repo) == set()
    assert (git_repo.coga_os / "tasks" / "other.md").exists()
    assert tip[:12] in capsys.readouterr().err


def test_fast_forward_realigns_an_unheld_control_and_leaves_another_holder_alone(
    git_repo, tmp_path, capsys
):
    cfg = load_config(git_repo.coga_os)
    _subsumed_divergence(git_repo)
    git_repo.checkout_branch("feature/x")
    origin_tip = git_repo.git("rev-parse", "origin/main").strip()
    held_tip = git_repo.git("rev-parse", "main").strip()
    linked = tmp_path / "held"
    git_repo.git("worktree", "add", "--quiet", str(linked), "main")
    try:
        assert git.fast_forward_control(cfg, git_repo.root, origin_tip) is False
        assert git_repo.git("rev-parse", "main").strip() == held_tip
        assert f"in {linked} has commits not on origin/main; left alone" in (
            capsys.readouterr().err
        )
    finally:
        git_repo.git("worktree", "remove", "--force", str(linked))

    assert git.fast_forward_control(cfg, git_repo.root, origin_tip) is True
    assert git_repo.git("rev-parse", "main").strip() == origin_tip
    assert _head(git_repo)[0] == "feature/x"


def test_realignment_refuses_an_unfinished_merge_before_staging_anything(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    _subsumed_divergence(git_repo)
    append_log(cfg, "demo", "agent:claude", "local line")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "log")
    git_repo.git("checkout", "--quiet", "-b", "feature/code", "HEAD~1")
    (git_repo.root / "code.txt").write_text("feature code\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "code.txt")
    git_repo.git("commit", "-m", "code")
    git_repo.git("checkout", "--quiet", "main")
    git_repo.git("merge", "--no-commit", "--no-ff", "feature/code")
    assert (git_repo.root / ".git" / "MERGE_HEAD").exists()
    log_rel = "coga/log.md"
    log_bytes = (git_repo.coga_os / "log.md").read_bytes()
    before = _snapshot(git_repo)

    assert git.refresh(cfg) is False
    assert "a merge is in progress" in capsys.readouterr().err
    assert _snapshot(git_repo) == before

    staged = {log_rel: (log_bytes, b"would be written if staging ran\n")}
    origin_tip = git_repo.git("rev-parse", "origin/main").strip()
    assert git.fast_forward_control(cfg, git_repo.root, origin_tip, staged=staged) is False
    assert "finish or abort it and retry" in capsys.readouterr().err
    assert _snapshot(git_repo) == before


@pytest.mark.parametrize("marker, what", git._IN_PROGRESS_MARKERS)
def test_realignment_refuses_every_in_progress_operation(git_repo, capsys, marker, what):
    cfg = load_config(git_repo.coga_os)
    _subsumed_divergence(git_repo)
    path = git_repo.root / ".git" / marker
    if marker.startswith("rebase-"):
        path.mkdir()
    else:
        path.write_text(git_repo.git("rev-parse", "HEAD"), encoding="utf-8", newline="\n")
    log = git_repo.coga_os / "log.md"
    log.write_text("dirty\n", encoding="utf-8", newline="\n")
    staged = {"coga/log.md": (b"dirty\n", b"landed\n")}
    before = _snapshot(git_repo)

    origin_tip = git_repo.git("rev-parse", "origin/main").strip()
    assert git.fast_forward_control(cfg, git_repo.root, origin_tip, staged=staged) is False

    assert f"{what} is in progress" in capsys.readouterr().err
    assert _snapshot(git_repo) == before


def test_realignment_refuses_when_the_operation_check_cannot_inspect(
    git_repo, monkeypatch, capsys
):
    cfg = load_config(git_repo.coga_os)
    _subsumed_divergence(git_repo)
    (git_repo.coga_os / "log.md").write_text("dirty\n", encoding="utf-8", newline="\n")
    staged = {"coga/log.md": (b"dirty\n", b"landed\n")}
    before = _snapshot(git_repo)
    real = git.run_git

    def failing(root, *args, **kwargs):
        if "--git-dir" in args:
            raise git.GitError("`git rev-parse --git-dir` failed (exit 128): boom")
        return real(root, *args, **kwargs)

    monkeypatch.setattr(git, "run_git", failing)
    origin_tip = real(git_repo.root, "rev-parse", "origin/main").strip()

    assert git.fast_forward_control(cfg, git_repo.root, origin_tip, staged=staged) is False

    assert "could not inspect" in capsys.readouterr().err
    monkeypatch.setattr(git, "run_git", real)
    assert _snapshot(git_repo) == before


def test_subsumed_guard_accepts_state_already_on_control(git_repo):
    cfg = load_config(git_repo.coga_os)
    tip, _hand = _subsumed_divergence(git_repo)

    verdict = _subsumed(git_repo, cfg)

    assert verdict.kind == "ok", verdict
    assert verdict.dropped == ((tip, "hand commit"),)
    origin_tip = git_repo.git("rev-parse", "origin/main").strip()
    assert verdict.evidence[:2] == (tip, origin_tip)


def test_subsumed_guard_refuses_code_changed_then_reverted(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    code = _hand_commit(git_repo, "local.txt", "code\n", "add code")
    _hand_commit(git_repo, "local.txt", None, "revert code")
    hand = _ticket_text(blackboard="hand\n")
    _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    git_repo.push_competing_commit("coga/tasks/demo.md", hand)
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)

    assert verdict.kind == "foreign"
    assert verdict.blocking == ("local.txt",)
    assert code[:12] in verdict.reason


def test_subsumed_guard_refuses_a_merge_commit_with_non_state_changes(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    hand = _ticket_text(blackboard="hand\n")
    git_repo.git("checkout", "--quiet", "-b", "side")
    _hand_commit(git_repo, "coga/tasks/demo.md", hand)
    git_repo.git("checkout", "--quiet", "main")
    git_repo.git("merge", "--no-ff", "--no-commit", "side")
    (git_repo.root / "evil.txt").write_text("snuck into the merge\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "evil.txt")
    git_repo.git("commit", "-m", "merge side")
    merge = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.push_competing_commit("coga/tasks/demo.md", hand)
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)

    assert verdict.kind == "foreign"
    assert verdict.blocking == ("evil.txt",)
    assert merge[:12] in verdict.reason


def test_subsumed_guard_needs_exactly_one_merge_base(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("checkout", "--quiet", "--orphan", "orphan")
    git_repo.git("commit", "--quiet", "-m", "unrelated history")

    verdict = _subsumed(git_repo, cfg, local="orphan", target="main")
    assert verdict.kind == "unproven"
    assert "no merge bases" in verdict.reason

    # A criss-cross: x and y each merged the other, so they have two bases.
    git_repo.git("checkout", "--quiet", "-b", "x", "main")
    _hand_commit(git_repo, "coga/tasks/x.md", "x\n", "x")
    git_repo.git("checkout", "--quiet", "-b", "y", "main")
    _hand_commit(git_repo, "coga/tasks/y.md", "y\n", "y")
    git_repo.git("checkout", "--quiet", "-b", "mx", "x")
    git_repo.git("merge", "--quiet", "--no-ff", "-m", "mx", "y")
    git_repo.git("checkout", "--quiet", "-b", "my", "y")
    git_repo.git("merge", "--quiet", "--no-ff", "-m", "my", "x")

    verdict = _subsumed(git_repo, cfg, local="mx", target="my")
    assert verdict.kind == "unproven"
    assert "2 merge bases" in verdict.reason


@pytest.mark.parametrize("on_control", [True, False])
def test_subsumed_guard_proves_a_committed_deletion(git_repo, on_control):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    _hand_commit(git_repo, "coga/tasks/demo.md", None, "drop demo")
    if on_control:
        _peer_commit(git_repo, lambda clone: (clone / "coga/tasks/demo.md").unlink())
    else:
        git_repo.push_competing_commit("coga/tasks/other.md", "other\n")
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)

    if on_control:
        assert verdict.kind == "ok", verdict
    else:
        assert verdict.kind == "unpublished"
        assert verdict.blocking == (
            "coga/tasks/demo.md (deleted here but present on control)",
        )


def test_subsumed_guard_compares_executable_modes(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("update-index", "--chmod=+x", "coga/tasks/demo.md")
    git_repo.git("commit", "-m", "make executable")
    git_repo.push_competing_commit("coga/tasks/other.md", "other\n")
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)

    assert verdict.kind == "unpublished"
    assert verdict.blocking == ("coga/tasks/demo.md (file mode differs from control)",)

    _peer_commit(git_repo, lambda clone: (
        (clone / "coga/tasks/demo.md").chmod(0o755) if os.name == "posix"
        else git.run_git(clone, "update-index", "--chmod=+x", "coga/tasks/demo.md")
    ))
    git_repo.git("fetch", "--quiet", "origin")
    assert _subsumed(git_repo, cfg).kind == "ok"


@pytest.mark.parametrize("entry", ["symlink", "submodule"])
def test_subsumed_guard_cannot_prove_symlinks_or_submodules(git_repo, entry):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    rel = "coga/tasks/odd"
    if entry == "symlink":
        (git_repo.root / rel).symlink_to("demo.md")
        git_repo.git("add", rel)
    else:
        head = git_repo.git("rev-parse", "HEAD").strip()
        git_repo.git("update-index", "--add", "--cacheinfo", f"160000,{head},{rel}")
    git_repo.git("commit", "-m", f"add {entry}")
    git_repo.push_competing_commit("coga/tasks/other.md", "other\n")
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)

    assert verdict.kind == "unproven"
    assert verdict.blocking == (rel,)
    assert "non-regular" in verdict.reason


def test_subsumed_guard_union_merges_committed_log_lines(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    append_log(cfg, "demo", "human:marc", "seeded")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "seed log")
    git_repo.git("push", "origin", "main")
    seed = (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
    append_log(cfg, "demo", "agent:claude", "committed line")
    mine = (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "log by hand")
    git_repo.push_competing_commit("coga/log.md", seed + "peer line\n")
    git_repo.git("fetch", "--quiet", "origin")

    verdict = _subsumed(git_repo, cfg)
    assert verdict.kind == "unpublished"
    assert verdict.blocking == ("coga/log.md (lines not yet on control)",)

    git_repo.push_competing_commit("coga/log.md", seed + "peer line\n" + mine[len(seed):])
    git_repo.git("fetch", "--quiet", "origin")
    verdict = _subsumed(git_repo, cfg)
    assert verdict.kind == "ok", verdict
    assert verdict.evidence[-1] == ("coga/log.md",)


def test_stage_a_handoff_sweep_publishes_state_but_never_definitions(git_repo):
    """v1/package-definitions stage A: a feature branch edits package-owned
    definitions (committed with the code) and the live copies of shipped
    skills, while ordinary ticket and recurring-state edits stay dirty. The
    handoff sweep publishes only that ordinary state: control keeps its live
    recurring definition, its sibling script and its package bytes unchanged
    until the PR merges."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    definition = (
        "---\nschedule: \"0 9 * * 1\"\n---\n\n## Description\n\nOld body.\n\n"
        "<!-- coga:blackboard -->\n\ncursor: 1\n"
    )
    seeds = {
        "coga/recurring/dream/ticket.md": definition,
        "coga/recurring/dream/ticket.py": "raise SystemExit(0)\n",
        "coga/skills/code/implement/SKILL.md": "live skill\n",
        "src/coga/resources/templates/coga/recurring/dream/ticket.md": definition,
    }
    for rel, text in seeds.items():
        path = git_repo.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed pre-A control")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/package-definitions")
    _hand_commit(
        git_repo, "src/coga/resources/templates/coga/recurring/dream/ticket.md",
        definition.replace("Old body.", "New packaged body."),
    )
    _hand_commit(git_repo, "coga/skills/code/implement/SKILL.md", "linked to the package owner\n")
    # Ordinary mutable state stays ordinary published state.
    parent = git_repo.root / "coga/recurring/dream/ticket.md"
    parent.write_text(definition.replace("cursor: 1", "cursor: 2"), encoding="utf-8", newline="\n")
    (git_repo.coga_os / "tasks/demo.md").write_text(
        _ticket_text(blackboard="stage A handoff\n"), encoding="utf-8", newline="\n"
    )

    git.sync_coga_state(cfg)

    assert "stage A handoff" in _control(git_repo, "coga/tasks/demo.md")
    published = _control(git_repo, "coga/recurring/dream/ticket.md")
    assert "cursor: 2" in published
    assert published.split("<!-- coga:blackboard -->")[0] == definition.split("<!-- coga:blackboard -->")[0]
    assert _control(git_repo, "coga/recurring/dream/ticket.py") == "raise SystemExit(0)\n"
    assert _control(git_repo, "coga/skills/code/implement/SKILL.md") == "live skill\n"
    assert _control(
        git_repo, "src/coga/resources/templates/coga/recurring/dream/ticket.md"
    ) == definition


# Stage A is deliberately pinned: B must never prove its transition with B's
# imports or strict packaging policy standing in for the compatibility release.
_PACKAGE_DEFINITIONS_STAGE_A = "bbca5cb0ed7c2bfb3187465c0a1d3fe49f85a019"


def _package_publication_environment(root: Path) -> dict[str, str]:
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("COGA_")
        and key not in {"PYTHONPATH", "SLACK_WEBHOOK_URL"}
    }
    env.update(PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1", TERM="dumb")
    return env


def _package_publication_owner(git_repo, owner: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "owner", "publication-proof", owner],
        cwd=git_repo.root, env=_package_publication_environment(git_repo.root),
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sync failed" not in result.stderr and "sync refused" not in result.stderr


def _check_package_control(
    git_repo, tmp_path: Path, label: str, *, stage_a_fixture: bool = False,
) -> None:
    """Run the published control tree's own imports and tests, in a fresh clone."""
    control = tmp_path / label
    git_repo.git("clone", "--config", "core.autocrlf=false", "--branch", "main",
                 str(git_repo.origin), str(control))
    if stage_a_fixture:
        # Backport only the pinned test's LF fixture write. Its product code
        # and byte-equality assertions remain the historical control's own.
        fixture = control / "tests/test_packaging.py"
        text = fixture.read_text(encoding="utf-8")
        original = 'parent.write_text(render_carrier(read_blackboard(parent)), encoding="utf-8")'
        assert text.count(original) == 1
        fixture.write_text(
            text.replace(original, original[:-1] + ', newline="\\n")'),
            encoding="utf-8", newline="\n",
        )
    env = _package_publication_environment(control)
    imported = subprocess.run(
        [sys.executable, "-c", "import coga; print(coga.__file__)"],
        cwd=control, env=env, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert Path(imported.stdout.strip()).is_relative_to(control / "src")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_packaging.py", "tests/test_paths.py", "tests/test_recurring_state.py",
         "tests/test_recurring_shims.py", "tests/test_init.py",
         f"--basetemp={tmp_path / (label + '-fixtures')}"],
        cwd=control, env=env, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _configure_package_publication_checkout(git_repo) -> None:
    (git_repo.coga_os / "coga.local.toml").write_text(
        'user = "marc"\n[notification.slack]\nenabled = false\n',
        encoding="utf-8", newline="\n",
    )
    path = git_repo.coga_os / "tasks/publication-proof.md"
    path.write_text(
        "---\ntitle: Publication proof\nstatus: draft\nowner: marc\nworkflow: null\n---\n\n"
        "## Description\n\nExercise ordinary publication.\n\n<!-- coga:blackboard -->\n",
        encoding="utf-8", newline="\n",
    )
    git_repo.git("add", "--", "coga/tasks/publication-proof.md")
    git_repo.git("commit", "-m", "seed publication proof")
    git_repo.git("push", "origin", "main")


def test_stage_b_first_deletion_and_carrier_publish_against_stage_a_control(git_repo, tmp_path):
    from coga.recurring_state import CARRIER_PREFIX

    source = Path(__file__).resolve().parents[1]
    available = subprocess.run(
        ["git", "cat-file", "-e", _PACKAGE_DEFINITIONS_STAGE_A + "^{commit}"],
        cwd=source, capture_output=True, check=False,
    )
    if available.returncode:
        pytest.skip("transition receipt requires Git history containing the pinned Stage A merge")
    git_repo.git("fetch", str(source), _PACKAGE_DEFINITIONS_STAGE_A)
    git_repo.git("checkout", "-B", "main", "FETCH_HEAD")
    # This force push seeds only the fixture's private bare remote.
    git_repo.git("push", "--force", "origin", "main")
    _configure_package_publication_checkout(git_repo)
    git_repo.checkout_branch("feature/first-package-cutover")
    package_tree = git_repo.git("rev-parse", "origin/main:src/coga/resources").strip()
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    original = parent.read_bytes()
    siblings = {name: parent.with_name(name).read_bytes() for name in ("ticket.py", "operations.md")}
    worklist = _control(git_repo, "coga/recurring/autoclose-merged/retires.md")
    frozen = git_repo.git("rev-parse", "origin/main:coga/tasks/recurring").strip()
    custom = {
        name: git_repo.git("rev-parse", f"origin/main:coga/recurring/{name}").strip()
        for name in ("usage-report", "upstream-coga")
    }
    selection = git_repo.coga_os / "recurring/jobs.toml"
    assert not selection.exists()
    selection.write_text("[jobs]\nphone-home = true\n", encoding="utf-8", newline="\n")
    _package_publication_owner(git_repo, "zach")
    assert _control(git_repo, "coga/recurring/jobs.toml") == selection.read_text()
    _check_package_control(git_repo, tmp_path, "stage-a-selection", stage_a_fixture=True)

    parent.write_bytes(CARRIER_PREFIX.encode() + original.split(b"<!-- coga:blackboard -->", 1)[1])
    for name in siblings:
        parent.with_name(name).unlink()
    # Legacy user topics link to one another. Remove the reviewed set as one
    # change, so an intermediate control tree never has dangling live links.
    topics = [
        row.split("\t")[0]
        for row in (git_repo.root / "tests/legacy_removal_inventory.txt").read_text().splitlines()
        if row.startswith("docs/contexts/coga/")
    ]
    assert topics
    for topic in topics:
        (git_repo.root / topic).unlink()
    repo_context = git_repo.coga_os / "context.md"
    repo_context.write_text(repo_context.read_text() + "\nCutover publication proof.\n", encoding="utf-8")
    _package_publication_owner(git_repo, "marc")

    for topic in topics:
        assert _control(git_repo, topic) is None
    # Text-mode subprocess output normalizes CRLF; compare the actual Git bytes.
    published = subprocess.run(
        ["git", "show", "main:coga/recurring/phone-home/ticket.md"],
        cwd=git_repo.origin, capture_output=True, check=True,
    ).stdout
    assert published == parent.read_bytes()
    for name in siblings:
        assert _control(git_repo, "coga/recurring/phone-home/" + name) is None
    assert "Cutover publication proof." in _control(git_repo, "coga/context.md")
    assert _control(git_repo, "coga/recurring/autoclose-merged/retires.md") == worklist
    assert git_repo.git("rev-parse", "origin/main:coga/tasks/recurring").strip() == frozen
    for name, tree in custom.items():
        assert git_repo.git("rev-parse", f"origin/main:coga/recurring/{name}").strip() == tree
    assert git_repo.git("rev-parse", "origin/main:src/coga/resources").strip() == package_tree
    _check_package_control(git_repo, tmp_path, "stage-a-first-conversion", stage_a_fixture=True)


@pytest.mark.parametrize("committed", [False, True], ids=["dirty-package", "committed-package"])
def test_final_package_edits_never_escape_a_mutating_cli_sweep(git_repo, tmp_path, committed):
    from test_packaging import _pristine_source

    # Reuse the ordinary GitRepo remote and pristine-artifact snapshot helper;
    # the snapshot includes current uncommitted implementation bytes as well.
    source = _pristine_source(tmp_path)
    git_repo.git("rm", "-r", "--ignore-unmatch", ".")
    shutil.copytree(source, git_repo.root, dirs_exist_ok=True)
    # The source tracks package starters that its own .gitignore ignores.
    # Preserve the exact snapshot, including those required wheel files.
    names = sorted(path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file())
    for offset in range(0, len(names), 100):
        git_repo.git("add", "-f", "--", *names[offset:offset + 100])
    git_repo.git("commit", "-m", "seed package-only control")
    git_repo.git("push", "origin", "main")
    _configure_package_publication_checkout(git_repo)
    git_repo.checkout_branch("feature/package-content")
    package_tree = git_repo.git("rev-parse", "origin/main:src/coga/resources").strip()
    resources = [
        "src/coga/resources/prompt.md",
        "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md",
        "src/coga/resources/templates/coga/bootstrap/skills/direct/body/SKILL.md",
        "src/coga/resources/templates/coga/bootstrap/workflows/direct/body.md",
        "src/coga/resources/templates/coga/bootstrap/resolve-conflicts/ticket.md",
        "src/coga/resources/templates/coga/recurring/phone-home/operations.md",
    ]
    for name in resources:
        path = git_repo.root / name
        path.write_text(path.read_text() + "\n<!-- reviewed package edit -->\n", encoding="utf-8")
    if committed:
        git_repo.git("add", "--", *resources)
        git_repo.git("commit", "-m", "edit package definitions")
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    parent.write_bytes(parent.read_bytes() + b"\nPublication proof: preserve unrelated state.\n")
    context = git_repo.root / "docs/contexts/coga-dev/publication-proof/SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("# Local publication proof\n", encoding="utf-8")
    repo_context = git_repo.coga_os / "context.md"
    repo_context.write_bytes(repo_context.read_bytes() + b"\nLocal repo context proof.\n")
    _package_publication_owner(git_repo, "zach")

    assert "owner: zach" in _control(git_repo, "coga/tasks/publication-proof.md")
    # Text-mode subprocess output normalizes CRLF; compare the actual Git bytes.
    published = subprocess.run(
        ["git", "show", "main:coga/recurring/phone-home/ticket.md"],
        cwd=git_repo.origin, capture_output=True, check=True,
    ).stdout
    assert published == parent.read_bytes()
    assert _control(git_repo, "docs/contexts/coga-dev/publication-proof/SKILL.md") == context.read_text()
    assert "Local repo context proof." in _control(git_repo, "coga/context.md")
    assert git_repo.git("rev-parse", "origin/main:src/coga/resources").strip() == package_tree
    _check_package_control(git_repo, tmp_path, "package-only-control")


# --- prepared ticket transactions (read control before modifying) -------------
#
# `git.prepare_ticket` fetches control, reconciles this checkout's ticket with
# control's copy over the newest proven shared snapshot, and lifecycle
# commands decide, write, and publish from that view (`coga/state-publication`,
# "Prepared ticket transactions").

_FOUR_STEPS = ("implement", "review", "fix", "ship")


def _lifecycle_text(
    *, status: str = "in_progress", step: int | None = 1, blackboard: str = "notes\n",
    body: str = "Demo.\n",
) -> str:
    steps = "".join(f"  - name: {name}\n    assignee: agent\n" for name in _FOUR_STEPS)
    step_line = "" if step is None else f"step: {step} ({_FOUR_STEPS[step - 1]})\n"
    return (
        f"---\ntitle: demo\nstatus: {status}\nowner: marc\nagent: claude\n"
        f"workflow:\n  name: four\n  steps:\n{steps}{step_line}---\n\n"
        f"## Description\n\n{body}\n<!-- coga:blackboard -->\n\n{blackboard}"
    )


def _seed_lifecycle(git_repo, **kwargs) -> tuple[Path, str]:
    workflow = git_repo.coga_os / "workflows" / "four.md"
    workflow.write_text(
        "---\nname: four\ndescription: four steps.\nsteps:\n"
        + "".join(f"  - name: {name}\n    assignee: agent\n" for name in _FOUR_STEPS)
        + "---\n\n" + "".join(f"## {name}\nDo {name}.\n\n" for name in _FOUR_STEPS),
        encoding="utf-8", newline="\n",
    )
    path = git_repo.coga_os / "tasks" / "demo.md"
    path.write_text(_lifecycle_text(**kwargs), encoding="utf-8", newline="\n")
    git_repo.git("add", "--", "coga/tasks/demo.md", "coga/workflows/four.md")
    git_repo.git("commit", "-m", "seed demo")
    git_repo.git("push", "origin", "main")
    return path, "coga/tasks/demo.md"


def _peer_writes(git_repo, rel: str, text: str) -> None:
    def mutate(clone: Path) -> None:
        (clone / rel).write_text(text, encoding="utf-8", newline="\n")

    _peer_commit(git_repo, mutate, message=f"peer: {rel}")


def _index_and_head(git_repo) -> tuple[str, str, str]:
    return (
        git_repo.git("rev-parse", "HEAD").strip(),
        git_repo.git("symbolic-ref", "-q", "HEAD").strip(),
        git_repo.git("ls-files", "--stage"),
    )


def test_prepare_adopts_control_for_an_unedited_stale_feature_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/stale")
    before = path.read_bytes()
    _peer_writes(git_repo, rel, _lifecycle_text(step=2, blackboard="notes\npeer note\n"))

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.fresh and prepared.outcome == "adopted"
    assert prepared.ticket.step == "2 (review)"
    assert "peer note" in prepared.ticket.body
    assert prepared.control == _control(git_repo, rel).encode()
    # Preparation writes nothing.
    assert path.read_bytes() == before == prepared.local


def test_stale_feature_checkout_bump_advances_controls_step(git_repo, monkeypatch):
    """Local step 1, control step 2: one bump lands step 3 on control."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/stale")
    # Unrelated dirt and a staged unrelated file must survive untouched.
    (git_repo.root / "README.scratch").write_text("dirt\n", encoding="utf-8")
    git_repo.git("add", "README.scratch")
    snapshot = _index_and_head(git_repo)
    _peer_writes(git_repo, rel, _lifecycle_text(step=2, blackboard="notes\npeer note\n"))

    result = runner.invoke(app, ["bump", "demo"])

    assert result.exit_code == 0, result.output
    control = Ticket.parse(_control(git_repo, rel))
    assert control.step == "3 (fix)"
    assert "peer note" in control.body
    assert Ticket.read(path).step == "3 (fix)"
    assert _index_and_head(git_repo) == snapshot


def test_three_way_merge_keeps_both_notes_and_later_step(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo, blackboard="## Notes\n\nbase\n\n## Peer\n\nnone\n")
    git_repo.checkout_branch("feature/merge")
    # Unpublished local edit: step 2 plus a note in the first section.
    path.write_text(
        _lifecycle_text(step=2, blackboard="## Notes\n\nbase\nlocal note\n\n## Peer\n\nnone\n"),
        encoding="utf-8", newline="\n",
    )
    _peer_writes(
        git_repo, rel,
        _lifecycle_text(step=3, blackboard="## Notes\n\nbase\n\n## Peer\n\nnone\npeer note\n"),
    )

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.outcome == "merged"
    assert prepared.ticket.step == "3 (fix)"
    assert "local note" in prepared.ticket.body and "peer note" in prepared.ticket.body

    result = runner.invoke(app, ["bump", "demo"])
    assert result.exit_code == 0, result.output
    control = Ticket.parse(_control(git_repo, rel))
    assert control.step == "4 (ship)"
    assert "local note" in control.body and "peer note" in control.body


def test_terminal_winner_carries_no_step(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/terminal")
    path.write_text(_lifecycle_text(step=2), encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, _lifecycle_text(status="done", step=None))

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.ticket.status == "done"
    assert "step" not in prepared.ticket.frontmatter


def test_a_later_publication_is_the_base_so_a_deliberate_rewind_is_kept(git_repo):
    """HEAD holds step 1, this worktree published step 2, local rewinds to 1."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/rewind")
    path.write_text(_lifecycle_text(step=2), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, path, message="step 2") is True
    path.write_text(_lifecycle_text(step=1), encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, _lifecycle_text(step=2, blackboard="notes\npeer note\n"))

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.outcome == "merged"
    assert prepared.ticket.step == "1 (implement)"
    assert "peer note" in prepared.ticket.body


def test_an_unpublished_feature_commit_is_a_local_edit_not_a_base(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/committed")
    path.write_text(_lifecycle_text(step=1, body="Local prose.\n"), encoding="utf-8", newline="\n")
    git_repo.git("commit", "-am", "local ticket edit")
    _peer_writes(git_repo, rel, _lifecycle_text(step=2))

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.outcome == "merged"
    assert prepared.ticket.step == "2 (review)"
    assert "Local prose." in prepared.ticket.body


def test_overlapping_blackboard_edits_refuse_before_any_write(git_repo, monkeypatch):
    from coga import cli

    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/conflict")
    path.write_text(_lifecycle_text(blackboard="local rewrite\n"), encoding="utf-8", newline="\n")
    original = path.read_bytes()
    _peer_writes(git_repo, rel, _lifecycle_text(blackboard="peer rewrite\n"))
    control_before = _control(git_repo, rel)
    log_before = log_path(cfg).read_bytes() if log_path(cfg).exists() else b""

    with pytest.raises(git.TicketConflictError) as conflict:
        git.prepare_ticket(cfg, path)
    assert not conflict.value.status_conflict

    monkeypatch.setattr("sys.argv", ["coga", "bump", "demo"])
    sweeps = []
    monkeypatch.setattr(cli, "_sweep_coga_state", lambda cfg: sweeps.append(cfg))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert not sweeps
    assert path.read_bytes() == original
    assert _control(git_repo, rel) == control_before
    assert (log_path(cfg).read_bytes() if log_path(cfg).exists() else b"") == log_before


@pytest.mark.parametrize(
    ("base", "local", "control"),
    [
        ("active", "paused", "in_progress"),
        ("in_progress", "blocked", "done"),
        ("in_progress", "done", "canceled"),
    ],
)
def test_undecidable_status_changes_are_a_status_conflict(git_repo, base, local, control):
    cfg = load_config(git_repo.coga_os)

    def text(status: str) -> str:
        return _lifecycle_text(status=status, step=None if status in {"done", "canceled"} else 1)

    path, rel = _seed_lifecycle(git_repo, status=base)
    git_repo.checkout_branch("feature/status")
    path.write_text(text(local), encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, text(control))

    with pytest.raises(git.TicketConflictError) as conflict:
        git.prepare_ticket(cfg, path)
    assert conflict.value.status_conflict
    assert "human must decide" in str(conflict.value)


def test_deleted_on_control_after_a_shared_base_refuses(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/deleted")
    _peer_commit(git_repo, lambda clone: (clone / rel).unlink(), message="peer delete")

    with pytest.raises(git.TicketConflictError, match="deleted"):
        git.prepare_ticket(cfg, path)


def test_a_never_published_ticket_keeps_the_create_path(git_repo):
    cfg = load_config(git_repo.coga_os)
    path = git_repo.coga_os / "tasks" / "fresh.md"
    path.write_text(_lifecycle_text(), encoding="utf-8", newline="\n")

    prepared = git.prepare_ticket(cfg, path)

    assert prepared.outcome == "new" and prepared.control is None


def test_failed_fetch_keeps_the_local_read(git_repo, monkeypatch, capsys):
    cfg = load_config(git_repo.coga_os)
    path, _rel = _seed_lifecycle(git_repo)
    real = git.run_git

    def offline(root, *args, env=None):  # type: ignore[no-untyped-def]
        if args and args[0] == "fetch":
            raise git.GitError("`git fetch` failed: could not resolve host")
        return real(root, *args, env=env)

    monkeypatch.setattr(git, "run_git", offline)
    prepared = git.prepare_ticket(cfg, path)

    assert not prepared.fresh and prepared.outcome == "local"
    assert prepared.expect() is None
    assert "could not read current control" in capsys.readouterr().err


def test_missing_remote_control_with_a_cached_ref_is_not_fresh(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    path, _rel = _seed_lifecycle(git_repo)
    git_repo.git("branch", "-m", "main", "trunk", cwd=git_repo.origin)
    assert git_repo.git("rev-parse", "-q", "--verify", "refs/remotes/origin/main").strip()

    fetched = git.fetch_control_state(cfg, git_repo.root)
    prepared = git.prepare_ticket(cfg, path)

    assert fetched.state == "missing" and fetched.revision is None
    assert not prepared.fresh
    assert "could not read current control" in capsys.readouterr().err


def test_same_ticket_race_after_preparation_refuses_and_is_remembered(git_repo):
    """Prepared against C; a peer then restores B, which this worktree once
    published. The exact expectation refuses, and the remembered refusal
    keeps the sweep from landing those bytes through broader provenance."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/race")
    b_text = _lifecycle_text(step=2)
    path.write_text(b_text, encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, path, message="B") is True
    c_text = _lifecycle_text(step=3)
    _peer_writes(git_repo, rel, c_text)

    prepared = git.prepare_ticket(cfg, path)
    assert prepared.ticket.step == "3 (fix)"
    prepared.ticket.frontmatter["step"] = "4 (ship)"
    git.write_ticket(cfg, prepared.ticket, path, prepared=prepared)
    _peer_writes(git_repo, rel, b_text)

    assert git.sync_task_state(cfg, path, message="step 4", prepared=prepared) is None
    assert _control(git_repo, rel) == b_text
    git.sync_coga_state(cfg)
    assert _control(git_repo, rel) == b_text
    assert Ticket.read(path).step == "4 (ship)"


def test_prepared_write_refuses_a_ticket_changed_after_preparation(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, _rel = _seed_lifecycle(git_repo)
    prepared = git.prepare_ticket(cfg, path)
    path.write_text(_lifecycle_text(blackboard="hand edit\n"), encoding="utf-8", newline="\n")
    prepared.ticket.frontmatter["step"] = "2 (review)"

    with pytest.raises(git.TicketChangedError):
        git.write_ticket(cfg, prepared.ticket, path, prepared=prepared)
    assert "hand edit" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("control_status", ["active", "in_progress"])
def test_prepare_refuses_progress_across_a_replaced_workflow(git_repo, control_status):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo, status="active")
    git_repo.checkout_branch("feature/replaced-workflow")
    path.write_text(_lifecycle_text(step=4), encoding="utf-8", newline="\n")
    original = path.read_bytes()
    control = Ticket.parse(_lifecycle_text(status=control_status))
    control.frontmatter["workflow"]["steps"] = control.frontmatter["workflow"]["steps"][:2]
    _peer_writes(git_repo, rel, control.render())

    with pytest.raises(git.TicketConflictError, match="replaced its frozen workflow") as exc:
        git.prepare_ticket(cfg, path)
    assert not exc.value.status_conflict  # ordinary workflow conflict, not human-review status escalation
    assert path.read_bytes() == original


def test_retryable_prepared_failure_keeps_its_expectation_for_the_retry(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/sandbox")
    b_text = _lifecycle_text(step=2)
    path.write_text(b_text, encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, path, message="B") is True
    _peer_writes(git_repo, rel, _lifecycle_text(step=3))
    prepared = git.prepare_ticket(cfg, path)
    prepared.ticket.frontmatter["step"] = "4 (ship)"
    git.write_ticket(cfg, prepared.ticket, path, prepared=prepared)

    real_run = git._run

    def read_only(argv, *, env=None, input=None):  # type: ignore[no-untyped-def]
        if "hash-object" in argv and "-w" in argv:
            return subprocess.CompletedProcess(argv, 128, b"", _EROFS)
        return real_run(argv, env=env, input=input)

    monkeypatch.setattr(git, "_run", read_only)
    assert git.sync_task_state(cfg, path, message="step 4", prepared=prepared) is None
    monkeypatch.setattr(git, "_run", real_run)
    assert "pending" in (cfg.repo_root / git._PENDING_FILE).read_text(encoding="utf-8")

    # A peer restores B; the retry must not land step 4 over it.
    _peer_writes(git_repo, rel, b_text)
    git.retry_session_publication(cfg, path, slug="demo")
    assert _control(git_repo, rel) == b_text


def test_retry_publishes_a_remembered_ticket_restored_to_its_head_bytes(git_repo, monkeypatch):
    """A prepared transition can land on the exact bytes HEAD holds (rewinding
    to the step a feature branch committed). When that publication fails
    retryably, the retry must still select the clean ticket from its remembered
    expectation instead of publishing only the log."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/rewind")
    b_text = _lifecycle_text(step=2)
    path.write_text(b_text, encoding="utf-8", newline="\n")
    git_repo.git("add", "--", rel)
    git_repo.git("commit", "-m", "feature records step 2")
    assert git.sync_task_state(cfg, path, message="B") is True
    _peer_writes(git_repo, rel, _lifecycle_text(step=3))

    prepared = git.prepare_ticket(cfg, path)
    assert prepared.ticket.step == "3 (fix)"
    prepared.ticket.frontmatter["step"] = "2 (review)"
    git.write_ticket(cfg, prepared.ticket, path, prepared=prepared)
    assert path.read_text(encoding="utf-8") == b_text  # equal to HEAD

    real_run = git._run

    def read_only(argv, *, env=None, input=None):  # type: ignore[no-untyped-def]
        if "hash-object" in argv and "-w" in argv:
            return subprocess.CompletedProcess(argv, 128, b"", _EROFS)
        return real_run(argv, env=env, input=input)

    monkeypatch.setattr(git, "_run", read_only)
    assert git.sync_task_state(cfg, path, message="rewind", prepared=prepared) is None
    monkeypatch.setattr(git, "_run", real_run)
    assert "pending" in (cfg.repo_root / git._PENDING_FILE).read_text(encoding="utf-8")

    git.retry_session_publication(cfg, path, slug="demo")
    assert _control(git_repo, rel) == b_text
    assert not (cfg.repo_root / git._PENDING_FILE).exists()


def test_retry_publishes_a_remembered_transition_that_restored_head_bytes(git_repo, monkeypatch):
    """A prepared rewind back to HEAD's exact bytes fails to publish; the
    retry (no explicit expectation) must still select the clean ticket from
    the remembered pending expectation and land it."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/rewind")
    path.write_text(_lifecycle_text(step=2), encoding="utf-8", newline="\n")
    assert git.sync_task_state(cfg, path, message="step 2") is True
    prepared = git.prepare_ticket(cfg, path)
    assert prepared.fresh
    path.write_text(_lifecycle_text(), encoding="utf-8", newline="\n")
    assert git_repo.git("status", "--porcelain", "--", rel) == ""

    real_run = git._run

    def read_only(argv, *, env=None, input=None):  # type: ignore[no-untyped-def]
        if "hash-object" in argv and "-w" in argv:
            return subprocess.CompletedProcess(argv, 128, b"", _EROFS)
        return real_run(argv, env=env, input=input)

    monkeypatch.setattr(git, "_run", read_only)
    assert git.sync_task_state(cfg, path, message="rewind", prepared=prepared) is None
    monkeypatch.setattr(git, "_run", real_run)
    assert rel in (cfg.repo_root / git._PENDING_FILE).read_text(encoding="utf-8")

    assert git.retry_session_publication(cfg, path, slug="demo") is True
    assert _control(git_repo, rel) == _lifecycle_text()
    assert not (cfg.repo_root / git._PENDING_FILE).exists()


def test_retry_session_publication_refuses_an_ignored_untracked_log(git_repo, capsys):
    """Like `sync_log`, the teardown retry must not report an excluded usage
    record as published (or already held): it returns None so launch warns."""
    cfg = load_config(git_repo.coga_os)
    path, _rel = _seed_lifecycle(git_repo)
    (git_repo.root / ".git" / "info" / "exclude").write_text("coga/log.md\n", encoding="utf-8", newline="\n")
    append_log(cfg, "demo", "system", "session usage")

    assert git.retry_session_publication(cfg, path, slug="demo") is None
    assert "excluded from publication" in capsys.readouterr().err
    assert not git_repo.origin_tracks("coga/log.md")


def _child_bump_without_object_writes(git_repo, monkeypatch, cfg, path) -> bytes:
    """A sandboxed child's bump: local ticket/log change, publication fails."""
    real_run = git._run

    def read_only(argv, *, env=None, input=None):  # type: ignore[no-untyped-def]
        if "fetch" in argv or ("hash-object" in argv and "-w" in argv):
            return subprocess.CompletedProcess(argv, 128, b"", _EROFS)
        return real_run(argv, env=env, input=input)

    real_run_git = git.run_git

    def no_fetch(root, *args, env=None):  # type: ignore[no-untyped-def]
        if args and args[0] == "fetch":
            raise git.GitError("`git fetch` failed: Read-only file system")
        return real_run_git(root, *args, env=env)

    monkeypatch.setattr(git, "_run", read_only)
    monkeypatch.setattr(git, "run_git", no_fetch)
    try:
        result = runner.invoke(app, ["bump", "demo"])
    finally:
        monkeypatch.setattr(git, "_run", real_run)
        monkeypatch.setattr(git, "run_git", real_run_git)
    assert result.exit_code == 0, result.output
    return path.read_bytes()


def test_improve_banners_sequence_peer_published_then_parent_confirms(git_repo, monkeypatch):
    """2026-09-27 multiply improve-banners: a child bump could not write Git
    objects, a peer published the exact ticket, the parent confirmed it and
    recorded provenance, and the next human bump in the feature checkout
    succeeds."""
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/improve-banners")

    child_bytes = _child_bump_without_object_writes(git_repo, monkeypatch, cfg, path)
    assert Ticket.read(path).step == "2 (review)"
    assert _control(git_repo, rel) == _lifecycle_text()
    _peer_writes(git_repo, rel, child_bytes.decode())

    git.retry_session_publication(cfg, path, slug="demo")
    published = git_repo.git("rev-parse", f"{git.PUBLISHED_REF}:{rel}").strip()
    assert published == git_repo.git("rev-parse", f"origin/main:{rel}").strip()

    result = runner.invoke(app, ["bump", "demo"])
    assert result.exit_code == 0, result.output
    assert Ticket.parse(_control(git_repo, rel)).step == "3 (fix)"


def test_improve_banners_sequence_recovers_without_a_peer(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/improve-banners")

    _child_bump_without_object_writes(git_repo, monkeypatch, cfg, path)
    assert git.retry_session_publication(cfg, path, slug="demo") is True

    assert Ticket.parse(_control(git_repo, rel)).step == "2 (review)"
    result = runner.invoke(app, ["bump", "demo"])
    assert result.exit_code == 0, result.output
    assert Ticket.parse(_control(git_repo, rel)).step == "3 (fix)"


def test_equal_tree_confirmation_records_only_this_worktrees_provenance(git_repo):
    cfg = load_config(git_repo.coga_os)
    path, rel = _seed_lifecycle(git_repo)
    linked = git_repo.origin.parent / "linked"
    git_repo.git("worktree", "add", "-b", "side", str(linked))
    git_repo.checkout_branch("feature/equal")
    text = _lifecycle_text(step=2)
    path.write_text(text, encoding="utf-8", newline="\n")
    _peer_writes(git_repo, rel, text)
    git_repo.git("fetch", "origin")
    before = git_repo.origin_subjects()

    assert git.publish(cfg, [path], "equal") is False

    assert git_repo.origin_subjects() == before
    assert git_repo.git("rev-parse", f"{git.PUBLISHED_REF}:{rel}").strip()
    # `refs/worktree/*` is private to each checkout: the linked one has none.
    linked_ref = subprocess.run(
        ["git", "-C", str(linked), "rev-parse", "-q", "--verify", git.PUBLISHED_REF],
        capture_output=True,
    )
    assert linked_ref.returncode != 0


def test_supervised_bump_refuses_when_control_moved_past_its_step(git_repo, monkeypatch):
    from coga.repl_supervisor import EXPECTED_STEP_ENV, EXPECTED_TASK_ENV

    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/supervised")
    _peer_writes(git_repo, rel, _lifecycle_text(step=2))
    monkeypatch.setenv("COGA_SUPERVISED", "1")
    monkeypatch.setenv(EXPECTED_TASK_ENV, str(path))
    monkeypatch.setenv(EXPECTED_STEP_ENV, "1 (implement)")

    result = runner.invoke(app, ["bump", "demo"])

    assert result.exit_code == 2
    assert "composed for step '1 (implement)'" in result.output
    assert Ticket.parse(_control(git_repo, rel)).step == "2 (review)"
    assert Ticket.read(path).step == "1 (implement)"


def test_block_writes_its_ask_onto_controls_copy(git_repo):
    path, rel = _seed_lifecycle(git_repo)
    git_repo.checkout_branch("feature/block")
    _peer_writes(git_repo, rel, _lifecycle_text(step=2, blackboard="notes\npeer note\n"))

    result = runner.invoke(app, ["block", "--task", "demo", "--reason", "Need the retry cap"])

    assert result.exit_code == 0, result.output
    control = Ticket.parse(_control(git_repo, rel))
    assert control.status == "blocked" and control.step == "2 (review)"
    assert "peer note" in control.body and "Need the retry cap" in control.body


def test_unblock_refusal_exits_without_the_sweep(git_repo, monkeypatch):
    from coga import cli

    path, rel = _seed_lifecycle(
        git_repo, status="blocked",
        blackboard="## Blockers\n\n- [ ] [2026-11-05 10:00] [agent:claude] id=20261105T100000 Need input\n",
    )
    git_repo.checkout_branch("feature/unblock")
    path.write_text(
        _lifecycle_text(status="blocked", blackboard="local rewrite\n"), encoding="utf-8", newline="\n",
    )
    original = path.read_bytes()
    _peer_writes(git_repo, rel, _lifecycle_text(status="blocked", blackboard="peer rewrite\n"))
    monkeypatch.setattr("sys.argv", ["coga", "unblock", "demo", "--answer", "go"])
    sweeps = []
    monkeypatch.setattr(cli, "_sweep_coga_state", lambda cfg: sweeps.append(cfg))

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == git.RETRY_WITHOUT_SWEEP_EXIT_CODE
    assert not sweeps and path.read_bytes() == original


# --- optional index locks and the feature-sync plan ----------------------------


def test_git_env_forces_optional_locks_off(monkeypatch):
    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "1")
    assert git._git_env()["GIT_OPTIONAL_LOCKS"] == "0"
    assert git._git_env({"GIT_OPTIONAL_LOCKS": "1"})["GIT_OPTIONAL_LOCKS"] == "0"


def test_feature_sweep_never_rewrites_the_real_index(git_repo, monkeypatch):
    """A killed `git status` refresh leaves `index.lock`; Coga never takes it.

    A stat-dirty tracked file makes any opportunistic refresh rewrite the
    index, so an unchanged inode and mtime prove the sweep never did.
    """
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    ticket.write_text(_ticket_text(blackboard="dirty\n"), encoding="utf-8", newline="\n")
    touched = git_repo.coga_os / "coga.toml"
    later = touched.stat().st_mtime + 10
    os.utime(touched, (later, later))
    index = git_repo.root / ".git" / "index"
    before = index.stat()
    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "1")

    calls: list[tuple[list[str], dict]] = []
    real_run = subprocess.run

    def recording_run(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            calls.append((list(argv), kwargs.get("env") or dict(os.environ)))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(git.subprocess, "run", recording_run)
    git.sync_coga_state(cfg)
    monkeypatch.undo()

    assert "dirty" in _control(git_repo, "coga/tasks/demo.md")
    assert any("status" in argv for argv, _env in calls)
    assert all(env.get("GIT_OPTIONAL_LOCKS") == "0" for _argv, env in calls)
    after = index.stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)


def _feature_with_published(git_repo, files: dict[str, str]) -> None:
    """Feature checkout whose control copy of each file is `files[rel]`."""
    for rel, text in files.items():
        git_repo.push_competing_commit(rel, text)
    git_repo.checkout_branch("feature/x")
    git_repo.git("fetch", "origin")


def test_feature_sync_plan_offers_the_shortcut_for_identical_state(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    published = _ticket_text(step="2 (review)")
    _feature_with_published(git_repo, {
        "coga/tasks/demo.md": published,
        "coga/tasks/it's new.md": "fresh\n",
    })
    (git_repo.coga_os / "tasks" / "demo.md").write_text(published, encoding="utf-8", newline="\n")
    (git_repo.coga_os / "tasks" / "it's new.md").write_text("fresh\n", encoding="utf-8", newline="\n")

    plan = git.feature_sync_plan(cfg)

    assert plan is not None
    assert (plan.tracked, plan.untracked, plan.manual) == (
        ("coga/tasks/demo.md",), ("coga/tasks/it's new.md",), (),
    )
    assert plan.target == "origin/main"
    assert plan.root == git_repo.root


@pytest.mark.skipif(os.name == "nt", reason="runs the POSIX rendering")
def test_feature_sync_command_merges_control_from_a_nested_cwd(git_repo):
    from coga.views import feature_sync_message

    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    published = _ticket_text(step="2 (review)")
    _feature_with_published(git_repo, {
        "coga/tasks/demo.md": published,
        "coga/tasks/it's new.md": "fresh\n",
    })
    (git_repo.coga_os / "tasks" / "demo.md").write_text(published, encoding="utf-8", newline="\n")
    (git_repo.coga_os / "tasks" / "it's new.md").write_text("fresh\n", encoding="utf-8", newline="\n")
    message = feature_sync_message(git.feature_sync_plan(cfg), windows=False)
    command = message.split("run:\n  ", 1)[1].split("\n", 1)[0]

    nested = git_repo.coga_os / "workflows"
    result = subprocess.run(["sh", "-c", command], cwd=nested, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert git_repo.git("status", "--porcelain") == ""
    assert git_repo.git("rev-parse", "HEAD").strip() == git_repo.git("rev-parse", "origin/main").strip()


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        ("differs", "differs from control"),
        ("staged", "has staged changes"),
        ("staged-deletion", "has staged changes"),
        ("deleted", "deleted in the working tree"),
        ("untracked-differs", "differs from control"),
        ("untracked-local-only", "not on control"),
    ],
)
def test_feature_sync_plan_routes_unsafe_states_to_manual(git_repo, setup, reason):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    published = _ticket_text(step="2 (review)")
    _feature_with_published(git_repo, {"coga/tasks/demo.md": published, "coga/tasks/new.md": "fresh\n"})
    rel = "coga/tasks/demo.md"
    if setup == "differs":
        ticket.write_text(_ticket_text(blackboard="local only\n"), encoding="utf-8", newline="\n")
    elif setup == "staged":
        ticket.write_text(published, encoding="utf-8", newline="\n")
        git_repo.git("add", "--", rel)
    elif setup == "staged-deletion":
        git_repo.git("rm", "-q", "--", rel)
    elif setup == "deleted":
        ticket.unlink()
    elif setup == "untracked-differs":
        rel = "coga/tasks/new.md"
        (git_repo.root / rel).write_text("mine\n", encoding="utf-8", newline="\n")
    else:
        rel = "coga/tasks/draft.md"
        (git_repo.root / rel).write_text("draft\n", encoding="utf-8", newline="\n")

    plan = git.feature_sync_plan(cfg)

    assert plan is not None
    assert (rel, reason) in plan.manual


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable bit")
def test_feature_sync_plan_treats_a_mode_change_as_unsafe(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    _feature_with_published(git_repo, {"coga/tasks/other.md": "x\n"})
    ticket.chmod(0o755)

    plan = git.feature_sync_plan(cfg)

    assert plan is not None
    assert plan.manual == (("coga/tasks/demo.md", "file mode differs from control"),)


def test_feature_sync_plan_writes_no_objects(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    git_repo.git("fetch", "origin")
    unique = "never stored anywhere 6f1e\n"
    ticket.write_text(unique, encoding="utf-8", newline="\n")
    oid = subprocess.run(
        ["git", "-C", str(git_repo.root), "hash-object", "--stdin"],
        input=unique, capture_output=True, text=True, check=True,
    ).stdout.strip()

    plan = git.feature_sync_plan(cfg)

    assert plan is not None and plan.manual == (("coga/tasks/demo.md", "differs from control"),)
    missing = subprocess.run(["git", "-C", str(git_repo.root), "cat-file", "-e", oid])
    assert missing.returncode != 0


def test_feature_sync_plan_is_silent_without_feature_dirt(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(blackboard="dirty\n"), encoding="utf-8", newline="\n")
    assert git.feature_sync_plan(cfg) is None  # control checkout

    git_repo.git("stash", "-q")
    git_repo.checkout_branch("feature/x")
    assert git.feature_sync_plan(cfg) is None  # no dirt

    git_repo.git("stash", "pop", "-q")
    git_repo.git("update-ref", "-d", "refs/remotes/origin/main")
    assert git.feature_sync_plan(cfg) is None  # no remote-tracking ref


def test_stale_index_lock_reports_without_removing(git_repo):
    cfg = load_config(git_repo.coga_os)
    assert git.stale_index_lock(cfg) is None
    lock = git_repo.root / ".git" / "index.lock"
    lock.write_bytes(b"")
    assert git.stale_index_lock(cfg) == lock
    assert lock.exists()
