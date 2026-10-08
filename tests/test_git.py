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

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from textwrap import dedent

import pytest
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
    return log.read_text() if log.is_file() else ""


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
    path.write_text(_ticket_text(**kwargs))
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
    (root / "coga.toml").write_text(f"version = 1\n{shared_extra}")
    (root / "coga.local.toml").write_text(f'user = "marc"\n{local_extra}')
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
    ticket.write_text(_ticket_text(step="2 (review)"))
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
    (git_repo.root / "wip.py").write_text("# half-written\n")
    ticket.write_text(_ticket_text(status="blocked"))

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
    (task / "ticket.md").write_text(_ticket_text())
    (task / "notes.md").write_text("attachment\n")

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
    ticket.write_text(_ticket_text(status="blocked"))

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", fast_forward=False) is True

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "main").strip() == tip
    assert _dirty(git_repo) == {"coga/tasks/demo.md"}


def test_publish_with_no_remote_commits_on_local_control_only(git_repo, capsys):
    """The stated I1 exception: no remote means local `main` is canonical."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.git("remote", "remove", "origin")
    ticket.write_text(_ticket_text(status="blocked"))

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
    ticket.write_text(_ticket_text(status="paused"))
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"))
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
    assert "status: paused" in ticket.read_text()


def test_publish_refuses_a_symlinked_task_file(git_repo, tmp_path, capsys):
    """`read_bytes` follows links: publishing one would land its target's
    bytes — possibly from outside the repo — on control as a regular file."""
    cfg = load_config(git_repo.coga_os)
    secret = tmp_path / "outside.md"
    secret.write_text("token = do-not-publish\n")
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
    ticket.write_text(_ticket_text(status="blocked"))

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
    ticket.write_text(_ticket_text(status="blocked"))
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
    ticket.write_text(_ticket_text(status="blocked"))
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
    ticket.write_text(_ticket_text(status="blocked"))
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

    (peer / "coga" / "tasks" / "second.md").write_text(_ticket_text(status="blocked"))
    assert git.sync_task_state(
        peer_cfg, peer / "coga" / "tasks" / "second.md", message="Ticket: second — blocked"
    ) is True
    # This checkout's base is now stale: the push is rejected once, the
    # rebuild lands on the peer's tip.
    first.write_text(_ticket_text(step="2 (review)"))
    assert git.sync_task_state(cfg, first, message="Ticket: first — step 2") is True

    assert "step: 2 (review)" in _control(git_repo, "coga/tasks/first.md")
    assert "status: blocked" in _control(git_repo, "coga/tasks/second.md")
    assert git_repo.origin_subjects()[:2] == [
        "Ticket: first — step 2",
        "Ticket: second — blocked",
    ]
    assert _dirty(git_repo) == set()
    assert second.read_text() == _ticket_text(status="blocked")


def test_publishing_the_same_ticket_from_a_stale_base_is_refused_with_the_fix(
    git_repo, capsys
):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    original = ticket.read_bytes()
    git_repo.push_competing_commit(
        "coga/tasks/demo.md", _ticket_text(blackboard="peer prose\n")
    )
    ticket.write_text(_ticket_text(blackboard="my prose\n"))

    with pytest.raises(git.StateRegressionError) as excinfo:
        git.publish(cfg, [ticket], "Ticket: demo — blackboard")

    reason = str(excinfo.value)
    assert "control copy changed since this checkout last saw it" in reason
    assert "git checkout origin/main -- coga/tasks/demo.md" in reason
    assert "sync refused" in _global_log(cfg)
    # Nothing landed, nothing moved: the peer's prose is on control, mine is
    # still on disk, and this checkout's `main` did not advance.
    assert "peer prose" in _control(git_repo, "coga/tasks/demo.md")
    assert "my prose" in ticket.read_text()
    assert git_repo.git("show", "HEAD:coga/tasks/demo.md").encode() == original


def test_log_appended_on_both_sides_keeps_both_lines(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    control_log = _control(git_repo, "coga/log.md") or ""
    git_repo.push_competing_commit(
        "coga/log.md", control_log + "2026-01-01 00:00 [rival] [system] rival line\n"
    )
    append_log(cfg, "demo", "agent:claude", "my line")
    ticket.write_text(_ticket_text(status="blocked"))

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is True

    landed = _control(git_repo, "coga/log.md")
    assert "rival line" in landed
    assert "my line" in landed
    # The control checkout's working log carries the union result and is clean.
    assert (git_repo.coga_os / "log.md").read_text() == landed
    assert _dirty(git_repo) == set()


def test_expect_pins_the_exact_control_copy(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    read = ticket.read_bytes()
    ticket.write_text(_ticket_text(status="blocked"))

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", expect={ticket: read}) is True

    # A second writer holding the same pre-write bytes loses.
    ticket.write_text(_ticket_text(status="paused"))
    with pytest.raises(git.StateRegressionError):
        git.publish(cfg, [ticket], "Ticket: demo — paused", expect={ticket: read})
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")


def test_expect_none_means_the_path_must_not_exist_on_control(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo, "taken")
    new = git_repo.coga_os / "tasks" / "taken.md"
    new.write_text(_ticket_text(status="blocked"))

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
    ticket.write_text(_ticket_text(status="blocked"))
    bases: list[str] = []

    assert git.publish(cfg, [ticket], "Ticket: demo — blocked", guard=bases.append) is True

    assert bases == [stale, tip]
    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")


def test_guard_refusal_lands_nothing_and_leaves_the_write_dirty(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    before = git_repo.origin_subjects()
    ticket.write_text(_ticket_text(status="blocked"))

    def refuse(base: str) -> None:
        raise git.StateRegressionError(f"not on {base[:7]}")

    with pytest.raises(git.StateRegressionError, match="not on"):
        git.publish(cfg, [ticket], "Ticket: demo — blocked", guard=refuse)

    assert git_repo.origin_subjects() == before
    assert "status: blocked" not in (_control(git_repo, "coga/tasks/demo.md") or "")
    assert ticket.read_text() == _ticket_text(status="blocked")


def test_a_feature_checkout_keeps_publishing_its_own_ticket(git_repo):
    """Its HEAD never advances with control; its own publishes are provenance."""
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")

    ticket.write_text(_ticket_text(status="in_progress", blackboard="first\n"))
    assert git.sync_task_state(cfg, ticket, message="one") is True
    ticket.write_text(_ticket_text(step="2 (review)", blackboard="first\nsecond\n"))
    assert git.sync_task_state(cfg, ticket, message="two") is True

    assert "step: 2 (review)" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "-q", "--verify", git.PUBLISHED_REF).strip()


# --- the launch-claim seal ----------------------------------------------------


def test_pending_claim_on_control_accepts_only_its_own_admission(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo, generation="pending:abc")

    # A bump from a checkout that read the pending copy is sealed out …
    ticket.write_text(_ticket_text(step="2 (review)"))
    with pytest.raises(git.StateRegressionError, match="pending launch admission"):
        git.publish(cfg, [ticket], "Ticket: demo — step 2")
    assert "sync refused" in _global_log(cfg)

    # … while the exact prefix-stripped admission lands.
    ticket.write_text(_ticket_text(generation="abc"))
    assert git.publish(cfg, [ticket], "Ticket: demo — launch admitted") is True
    assert "launch_generation: abc" in _control(git_repo, "coga/tasks/demo.md")


def test_a_released_witness_is_never_published(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo, generation="pending:abc")
    ticket.write_text(_ticket_text(generation="released:abc"))

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


def test_publish_from_a_worktree_fast_forwards_the_main_checkout(git_repo, tmp_path):
    ticket = _seed_ticket(git_repo)
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"))
        assert git.sync_task_state(
            load_config(worktree / "coga"), wt_ticket, message="Ticket: demo — blocked"
        ) is True

        # The primary checkout holding `main` advanced: ref, index, and file.
        assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
            "rev-parse", "main", cwd=git_repo.origin
        ).strip()
        assert "status: blocked" in ticket.read_text()
        assert _dirty(git_repo) == set()
        # The worktree kept its own branch and its dirty live copy.
        assert _dirty(git_repo, cwd=worktree) == {"coga/tasks/demo.md"}
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))


def test_fast_forward_leaves_an_ahead_main_alone_and_names_the_fix(
    git_repo, tmp_path, capsys
):
    ticket = _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n")
    git_repo.git("add", "local.txt")
    git_repo.git("commit", "-m", "local unpushed")
    ahead_tip = git_repo.git("rev-parse", "main").strip()
    worktree = tmp_path / "feature-worktree"
    git_repo.git("worktree", "add", "-b", "feature/wt", str(worktree), "origin/main")
    shutil.copy(git_repo.coga_os / "coga.local.toml", worktree / "coga")
    try:
        wt_ticket = worktree / "coga" / "tasks" / "demo.md"
        wt_ticket.write_text(_ticket_text(status="blocked"))
        assert git.sync_task_state(
            load_config(worktree / "coga"), wt_ticket, message="Ticket: demo — blocked"
        ) is True
    finally:
        git_repo.git("worktree", "remove", "--force", str(worktree))

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert git_repo.git("rev-parse", "main").strip() == ahead_tip
    assert "status: in_progress" in ticket.read_text()
    assert _dirty(git_repo) == set()
    assert "git pull --rebase --autostash origin main" in capsys.readouterr().err
    # The human's commit was neither pushed nor rebased.
    assert not git_repo.origin_tracks("local.txt")


def test_refresh_fast_forwards_a_behind_control_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.push_competing_commit("coga/tasks/demo.md", _ticket_text(status="blocked"))

    assert git.refresh(cfg) is True

    assert "status: blocked" in ticket.read_text()
    assert git_repo.git("rev-parse", "main").strip() == git_repo.git(
        "rev-parse", "main", cwd=git_repo.origin
    ).strip()
    assert _dirty(git_repo) == set()


def test_refresh_refuses_an_ahead_or_diverged_control_checkout(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n")
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

    assert "step: 1 (implement)" in ticket.read_text()
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
    ticket.write_text(_ticket_text(status="in_progress", generation="pending:xyz"))

    assert git.publish(
        cfg, [ticket], "Ticket: demo — in_progress", expect={ticket: pre_write}
    ) is True
    assert "pending:xyz" in _control(git_repo, "coga/tasks/demo.md")
    assert _dirty(git_repo) == set()


def test_no_private_fetch_refs_are_left_behind(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    git_repo.push_competing_commit("other.txt", "remote\n")
    ticket.write_text(_ticket_text(status="blocked"))

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
        for path in git_repo.coga_os.iterdir():
            path.rename(git_repo.root / path.name)
        git_repo.coga_os.rmdir()
        git_repo.coga_os = git_repo.root
        (git_repo.root / ".gitignore").write_text("coga.local.toml\n.agent-skills/\n")
        monkeypatch.chdir(git_repo.root)
    elif layout == "relocated":
        contexts = git_repo.root / "docs" / "contexts"
        contexts.mkdir(parents=True)
        (contexts / ".gitkeep").write_text("")
        with (git_repo.coga_os / "coga.toml").open("a") as stream:
            stream.write('[layout]\ncontexts = "docs/contexts"\n')
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    moved_from = cfg.contexts_root / "old" / "SKILL.md"
    skill = git_repo.coga_os / "skills" / "team" / "SKILL.md"
    for path in (context, moved_from, skill):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: team\ndescription: team.\n---\noriginal\n")
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
    ticket.write_text(_ticket_text(status="blocked"))
    append_log(cfg, "demo", "human:marc", "hand edit")
    recurring = git_repo.coga_os / "recurring" / "weekly" / "ticket.md"
    recurring.parent.mkdir(parents=True)
    recurring.write_text("---\ntitle: weekly\n---\n")
    context.write_text(context.read_text() + "owner decision\n")
    moved_to = cfg.contexts_root / "renamed" / "SKILL.md"
    moved_to.parent.mkdir(parents=True)
    moved_from.rename(moved_to)
    skill.unlink()
    new_skill = skill.parent / "notes.md"
    new_skill.write_text("new knowledge\n")
    workflow = git_repo.coga_os / "workflows" / "code.md"
    workflow.write_text(workflow.read_text() + "\nEdited workflow prose.\n")
    config = git_repo.coga_os / "coga.toml"
    config.write_text(config.read_text() + "\n# shared config\n")
    published = (context, moved_from, moved_to, skill, new_skill, workflow, config)
    local_config = git_repo.coga_os / "coga.local.toml"
    local_config.write_text(local_config.read_text() + "# machine-local\n")
    view = git_repo.coga_os / ".agent-skills" / "team" / "SKILL.md"
    view.parent.mkdir(parents=True)
    view.write_text("generated view\n")
    unrelated = git_repo.root / "src.py"
    if layout != "root":
        unrelated.write_text("code under review\n")

    if finalize:
        finalize_authored(cfg, before_snapshot=before, ref=ref)
        assert "status: blocked" in _control(git_repo, ticket.relative_to(git_repo.root).as_posix())
        assert _control(git_repo, context.relative_to(git_repo.root).as_posix()) == context.read_text()
        err = capsys.readouterr().err
        assert str(context) in err
        assert str(log_path(cfg)) not in err and str(local_config) not in err
    git.sync_coga_state(cfg)

    def landed(path):
        return _control(git_repo, path.relative_to(git_repo.root).as_posix())

    assert "status: blocked" in landed(ticket)
    assert "hand edit" in landed(git_repo.coga_os / "log.md")
    assert landed(recurring) == recurring.read_text()
    for path in published:
        assert landed(path) == (path.read_text() if path.exists() else None)
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
    context.write_text("---\nname: team\ndescription: team.\n---\nbody\n")
    before = _origin_tip(git_repo)

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/contexts/team/SKILL.md") == context.read_text()
    assert git_repo.git("rev-list", "--count", f"{before}..{_origin_tip(git_repo)}").strip() == "1"


def test_coga_root_paths_lists_a_relocated_contexts_root_separately(git_repo):
    contexts = git_repo.root / "docs" / "contexts"
    contexts.mkdir(parents=True)
    (contexts / ".gitkeep").write_text("")
    with (git_repo.coga_os / "coga.toml").open("a") as stream:
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
    (target / "SKILL.md").write_text("outside\n")
    link = git_repo.coga_os / "views" / "skill"
    link.parent.mkdir()
    link.symlink_to(target, target_is_directory=True)
    ticket.write_text(_ticket_text(status="blocked"))

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
    context.write_text("original\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed vision")
    git_repo.git("push", "origin", "main")
    before = snapshot_authoring_state(cfg)
    git_repo.push_competing_commit("coga/contexts/product/vision/SKILL.md", "peer\n")
    git_repo.git("fetch", "origin")
    context.write_text("agreed vision\n")
    ticket.write_text(_ticket_text(blackboard="authored\n"))
    tip = _origin_tip(git_repo)

    with pytest.raises(AuthoringError, match="not published"):
        finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert _origin_tip(git_repo) == tip
    assert context.read_text() == "agreed vision\n"
    assert "authored" in ticket.read_text()


@pytest.mark.parametrize("change", ["add", "modify", "delete"])
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
        context.write_text("original\n")
        git_repo.git("add", "coga/contexts")
        git_repo.git("commit", "-m", "seed context")
        git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/interview")
    before = snapshot_authoring_state(cfg)
    if change == "delete":
        context.unlink()
    else:
        context.write_text("authored knowledge\n")
    git_repo.git("add", "coga/contexts")
    git_repo.git("commit", "-m", "authored knowledge for review")
    if already_published:
        git_repo.git("push", "origin", "HEAD:main")
    ticket.write_text(_ticket_text(blackboard="authored task\n"))
    tip = _origin_tip(git_repo)

    if already_published:
        finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))
        assert "authored task" in _control(git_repo, "coga/tasks/demo.md")
    else:
        with pytest.raises(AuthoringError, match="excluded from publication"):
            finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))
        assert _origin_tip(git_repo) == tip
        assert "Published these knowledge edits" not in capsys.readouterr().err
    assert "authored task" in ticket.read_text()
    assert context.exists() == (change != "delete")
    if context.exists():
        assert context.read_text() == "authored knowledge\n"


@pytest.mark.parametrize("failure", ["committed_context", "push"])
def test_ticket_command_withholds_sweep_after_failed_authoring(
    git_repo, monkeypatch, capsys, failure,
):
    import importlib
    import sys
    from types import SimpleNamespace
    from coga import cli

    command = importlib.import_module("coga.commands.ticket")
    task = _seed_ticket(git_repo)
    config = git_repo.coga_os / "coga.toml"
    config.write_text(config.read_text().replace('cli = "claude"', 'cli = "true"'))
    git_repo.git("add", "coga/coga.toml")
    git_repo.git("commit", "-m", "configure test agent")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/interview")
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"

    def interview(*args, **kwargs):
        context.parent.mkdir(parents=True)
        context.write_text("---\nname: team\ndescription: Team.\n---\nKnowledge.\n")
        if failure == "committed_context":
            git_repo.git("add", "coga/contexts")
            git_repo.git("commit", "-m", "review-bound knowledge")
        else:
            monkeypatch.setattr(git, "_push", lambda *args: "offline")
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
    assert "Published these knowledge edits" not in capsys.readouterr().err


def test_sweep_leaves_knowledge_committed_on_a_feature_branch_for_its_pr(git_repo):
    """A commit on a feature branch is review work: a code PR's committed
    context edit (and its packaged twin) waits for the merge, while routine
    ticket state committed beside it is still adopted."""
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("original\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed context")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    context.write_text("reviewed in the PR\n")
    git_repo.git("add", "--", "coga/contexts/team/SKILL.md")
    _hand_commit(git_repo, "coga/tasks/demo.md", _ticket_text(blackboard="handoff\n"))

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "original\n"
    assert "handoff" in _control(git_repo, "coga/tasks/demo.md")


@pytest.mark.parametrize("existing_link", [False, True])
def test_authoring_does_not_publish_source_reached_through_a_symlink(git_repo, existing_link):
    from coga.authoring import finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    source = git_repo.root / "src.py"
    source.write_text("reviewed source\n")
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
    source.write_text("unreviewed source\n")
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("authored knowledge\n")

    finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert _control(git_repo, "src.py") == "reviewed source\n"
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "authored knowledge\n"
    assert source.read_text() == "unreviewed source\n"
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
    child.write_text("original skill\n")
    source = (git_repo.root if target_location == "inside" else tmp_path) / "source"
    source.mkdir()
    source_child = source / "helper.py"
    source_child.write_text("reviewed source\n")
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
    source_child.write_text("unreviewed source\n")

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
    assert source_child.read_text() == "unreviewed source\n"
    assert skill.is_symlink()


def test_authoring_keeps_newly_ignored_files_local_without_blocking_publication(
    git_repo, capsys,
):
    from coga.authoring import finalize_authored, snapshot_authoring_state
    from coga.tasks import resolve_bootstrap

    cfg = load_config(git_repo.coga_os)
    scratch = cfg.repo_root / "scratch.txt"
    scratch.write_text("local scratch\n")
    before = snapshot_authoring_state(cfg)
    ignore = cfg.repo_root / ".gitignore"
    ignore.write_text("scratch.txt\n")
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("authored knowledge\n")

    finalize_authored(cfg, before_snapshot=before, ref=resolve_bootstrap(cfg, "ticket"))

    assert scratch.read_text() == "local scratch\n"
    assert not git_repo.origin_tracks("coga/scratch.txt")
    assert "scratch.txt" not in capsys.readouterr().err
    assert _control(git_repo, "coga/.gitignore") == ignore.read_text()
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "authored knowledge\n"
    assert git_repo.git("status", "--porcelain").strip() == ""


def test_default_context_symlink_does_not_expand_publication_roots(git_repo):
    cfg = load_config(git_repo.coga_os)
    source = git_repo.root / "source"
    source.mkdir()
    child = source / "helper.py"
    child.write_text("reviewed source\n")
    git_repo.git("add", "source")
    git_repo.git("commit", "-m", "seed source")
    git_repo.git("push", "origin", "main")
    cfg.contexts_root.symlink_to(source, target_is_directory=True)
    child.write_text("unreviewed source\n")
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
    child.write_text("published\n")
    git_repo.git("add", "coga/skills")
    git_repo.git("commit", "-m", "seed skill")
    git_repo.git("push", "origin", "main")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "helper.py").write_text("published\n")
    child.unlink()
    skill.rmdir()
    skill.symlink_to(outside, target_is_directory=True)
    # Hide the untracked directory link, leaving only the tracked child's
    # apparent deletion for the cleanup proof to examine.
    (git_repo.root / ".git" / "info" / "exclude").write_text("coga/skills/team\n")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert any("coga/skills/team/helper.py" in item for item in outcome.blocking)
    assert skill.is_symlink()
    assert (outside / "helper.py").read_text() == "published\n"


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
    context.write_text("---\nname: team/note\ndescription: A note.\n---\nKnowledge.\n")
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
    config = config_path.read_text() + '\n[layout]\ncontexts = "docs/contexts"\n'
    if invalid_config:
        config = config.replace("version = 1", "version = 999")
    config_path.write_text(config)

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
        ).read_text()
        assert git_repo.git("rev-parse", "origin/main^").strip() == tip
    assert (destination / "team" / "note" / "SKILL.md").is_file()


@pytest.mark.parametrize("feature", [False, True])
@pytest.mark.parametrize("relocated", [False, True])
@pytest.mark.parametrize("config_change", ["relocate", "invalid", "destination"])
def test_checkout_return_reloads_config_before_publishing(
    git_repo, feature, relocated, config_change,
):
    from coga.commands.launch import _CheckoutBoundary

    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("---\nname: team\ndescription: Team.\n---\nKnowledge.\n")
    config_path = cfg.repo_root / "coga.toml"
    if relocated:
        old_root = git_repo.root / "docs" / "contexts"
        old_root.parent.mkdir()
        cfg.contexts_root.rename(old_root)
        config_path.write_text(config_path.read_text() + '\n[layout]\ncontexts = "docs/contexts"\n')
        cfg = load_config(cfg.repo_root)
    old_rel = str(cfg.contexts_root.relative_to(git_repo.root) / "team" / "SKILL.md")
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
    config = config_path.read_text()
    if relocated:
        config = config.replace('contexts = "docs/contexts"', 'contexts = "docs/topics"')
    else:
        config += '\n[layout]\ncontexts = "docs/topics"\n'
    if config_change == "invalid":
        config = config.replace("version = 1", "version = 999")
    elif config_change == "destination":
        config += '\n[git]\ncontrol_branch = "other"\n'
    config_path.write_text(config)
    token = git.state_sweep_withheld.set(False)
    try:
        settled = boundary.settle(cfg, subject="context relocation")
        if config_change == "relocate":
            assert settled
            assert git_repo.git("status", "--porcelain").strip() == ""
            assert git_repo.git("branch", "--show-current").strip() == "main"
            assert _control(git_repo, "docs/topics/team/SKILL.md") == (
                destination / "team" / "SKILL.md"
            ).read_text()
            assert _control(git_repo, old_rel) is None
            assert _control(git_repo, "coga/coga.toml") == config
            assert git_repo.git("rev-parse", "origin/main^").strip() == tip
            assert load_config(cfg.repo_root).contexts_root == destination
        else:
            assert not settled
            assert boundary.stopped
            assert git.state_sweep_withheld.get()
            assert _origin_tip(git_repo) == tip
            assert config_path.read_text() == config
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
    knowledge.write_text("original\n")
    git_repo.git("-C", str(sub), "add", ".")
    git_repo.git("-C", str(sub), "commit", "-m", "seed module")
    git_repo.git("add", rel)
    if change != "added":
        git_repo.git("commit", "-m", "seed gitlink")
        git_repo.git("push", "origin", "main")
    original = git_repo.git("ls-tree", "origin/main", "--", rel)
    if change == "deleted":
        shutil.rmtree(sub)
    elif change != "added":
        knowledge.write_text("edited\n")
        if change == "committed":
            git_repo.git("-C", str(sub), "commit", "-am", "edit module")

    git.sync_coga_state(cfg)

    assert "is a submodule" in capsys.readouterr().err
    assert git_repo.git("ls-tree", "origin/main", "--", rel) == original
    if change != "deleted":
        assert knowledge.read_text() == ("original\n" if change == "added" else "edited\n")


def test_sweep_publishes_a_hand_committed_skill_from_a_clean_control_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    tip = _hand_commit(git_repo, "coga/skills/team/SKILL.md", "hand skill\n")

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/skills/team/SKILL.md") == "hand skill\n"
    assert _head(git_repo) == ("main", _origin_tip(git_repo))
    assert tip in git_repo.git("reflog", "--format=%H", "main")
    assert _dirty(git_repo) == set()


def test_sweep_refuses_a_stale_context_overwrite(git_repo, capsys):
    """Compare-and-swap covers knowledge too: a context a peer changed on
    control since this checkout read it is refused, not overwritten."""
    cfg = load_config(git_repo.coga_os)
    context = cfg.contexts_root / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("original\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-m", "seed context")
    git_repo.git("push", "origin", "main")
    git_repo.push_competing_commit("coga/contexts/team/SKILL.md", "peer edit\n")
    git_repo.git("fetch", "origin")
    context.write_text("local edit\n")

    git.sync_coga_state(cfg)

    assert "sync refused" in capsys.readouterr().err
    assert _control(git_repo, "coga/contexts/team/SKILL.md") == "peer edit\n"
    assert context.read_text() == "local edit\n"


def test_sweep_leaves_a_stale_ticket_refused_but_converges_a_fresh_one(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    stale = _seed_ticket(git_repo, "stale")
    fresh = _seed_ticket(git_repo, "fresh")
    git_repo.push_competing_commit("coga/tasks/stale.md", _ticket_text(status="done"))
    stale.write_text(_ticket_text(status="blocked"))
    fresh.write_text(_ticket_text(status="blocked"))

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
        path.write_text(text)
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


def test_sweep_publishes_committed_state_from_a_feature_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    hand = _ticket_text(blackboard="feature handoff\n")
    (git_repo.root / "src.py").write_text("code\n")
    git_repo.git("add", "src.py")
    tip = _hand_commit(git_repo, "coga/tasks/demo.md", hand)

    git.sync_coga_state(cfg)

    assert _control(git_repo, "coga/tasks/demo.md") == hand
    assert not git_repo.origin_tracks("src.py")
    assert _head(git_repo) == ("feature/x", tip)
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
    fresh.write_text(_ticket_text())
    assert git.publish(cfg, [fresh], "Ticket: fresh — created") is True
    fresh.unlink()
    before = _origin_tip(git_repo)

    git.sync_coga_state(cfg)

    assert _origin_tip(git_repo) == before
    assert _control(git_repo, "coga/tasks/fresh.md") == _ticket_text()


def test_sweep_publishes_a_committed_deletion_of_an_absent_state_directory(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    weekly = git_repo.coga_os / "recurring" / "weekly" / "ticket.md"
    weekly.parent.mkdir(parents=True)
    weekly.write_text("---\ntitle: weekly\n---\n")
    git_repo.git("add", "coga/recurring")
    git_repo.git("commit", "-m", "seed recurring")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    _hand_commit(git_repo, "coga/recurring", None, "drop recurring")
    assert not (git_repo.coga_os / "recurring").exists()

    git.sync_coga_state(cfg)

    assert not git_repo.origin_tracks("coga/recurring/weekly/ticket.md")


# --- soft skips ---------------------------------------------------------------


def test_sync_noop_when_not_a_git_repo(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text())

    assert git.sync_task_state(cfg, task, message="Ticket: demo — created") is None
    assert "not a git repo" in capsys.readouterr().err


def test_sync_suppressed_when_disabled(tmp_path, capsys, real_git):
    cfg = _cfg(tmp_path, git_enabled=False)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text())

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
    ticket.write_text(_ticket_text(status="blocked"))

    assert git.sync_task_state(cfg, ticket, message="Ticket: demo — blocked") is None

    err = capsys.readouterr().err
    assert "control branch 'main' does not exist (you are on 'master')" in err
    assert 'control_branch = "master"' in err
    assert git_repo.git("log", "-1", "--format=%s").strip() == "seed demo"


def test_sync_nonfatal_on_rev_parse_failure(tmp_path, monkeypatch, real_git, capsys):
    cfg = _cfg(tmp_path)
    task = tmp_path / "tasks" / "demo.md"
    task.parent.mkdir(parents=True)
    task.write_text(_ticket_text())

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

    assert git.sync_log(cfg, message="Log: bootstrap/orient") is False
    assert "log sync failed" in capsys.readouterr().err
    assert "sync failed" not in _global_log(cfg)


# --- state_lock ---------------------------------------------------------------


def test_state_lock_is_reentrant_within_a_thread(git_repo):
    cfg = load_config(git_repo.coga_os)
    with git.state_lock(cfg):
        with git.state_lock(cfg):
            ticket = _seed_ticket(git_repo)
            ticket.write_text(_ticket_text(status="blocked"))
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
    assert "step: 1" in ahead.read_text()

    assert git.stale_coga_task_rels(cfg) == ["coga/tasks/ahead.md", "coga/tasks/new.md"]


def test_last_commit_times_keys_paths_under_tasks(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo, "demo")
    times = git.last_commit_times(cfg)
    assert list(times) == ["demo.md"]


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
    (git_repo.root / "wip.py").write_text("# half-written change\n")

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
    wip.write_text("---\nname: wip\n---\n\nunfinished\n")
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
    ticket.write_text(_ticket_text(blackboard="handoff\n"))
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
    assert "step: 2 (review)" in ticket.read_text()
    # The feature branch is kept, never deleted.
    assert git_repo.git("branch", "--list", "feature/x").strip()


def test_prepare_fast_forwards_a_behind_control_checkout(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.push_competing_commit("other.txt", "remote\n")

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert (git_repo.root / "other.txt").read_text() == "remote\n"


@pytest.mark.parametrize("shape", ["ahead", "diverged"])
def test_prepare_refuses_an_ahead_or_diverged_control_and_changes_nothing(git_repo, shape):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    (git_repo.root / "local.txt").write_text("human commit\n")
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
    (git_repo.root / "a.txt").write_text("feature\n")
    git_repo.git("add", "a.txt")
    git_repo.git("commit", "-m", "feature a")
    git_repo.git("checkout", "main")
    (git_repo.root / "a.txt").write_text("main\n")
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
    assert "handoff" in ticket.read_text()


@pytest.mark.parametrize("relocated", [False, True])
def test_prepare_cleans_a_published_context_and_skill_from_a_feature_checkout(
    git_repo, relocated
):
    """Checkout return reads the publication roots: a context or skill the
    sweep landed is proven and cleaned, not refused as foreign dirt."""
    if relocated:
        contexts = git_repo.root / "docs" / "contexts"
        contexts.mkdir(parents=True)
        (contexts / ".gitkeep").write_text("")
        with (git_repo.coga_os / "coga.toml").open("a") as stream:
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
        path.write_text("authored on the branch\n")

    git.sync_coga_state(cfg)

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert context.read_text() == skill.read_text() == "authored on the branch\n"


def test_prepare_still_refuses_dirty_source_outside_the_coga_roots(git_repo):
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.checkout_branch("feature/x")
    (git_repo.root / "src.py").write_text("unreviewed code\n")

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


def test_a_crlf_working_copy_publishes_the_blob_git_add_stages(git_repo):
    """Under `core.autocrlf`, publish must hash through the clean filters.

    Raw bytes landed a CRLF blob on control while `git add` staged LF, so
    the staged copy never matched and the checkout return refused forever.
    """
    cfg = load_config(git_repo.coga_os)
    _seed_ticket(git_repo)
    git_repo.git("config", "core.autocrlf", "input")
    git_repo.checkout_branch("feature/x")
    task = git_repo.coga_os / "tasks" / "recurring" / "sweep"
    task.mkdir(parents=True)
    (task / "ticket.md").write_bytes(_ticket_text().replace("\n", "\r\n").encode())
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
    fresh.write_text(_ticket_text())
    gone.unlink()
    assert git.publish(cfg, [fresh.parent, gone], "Ticket: create and delete") is True

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))
    assert fresh.read_text() == _ticket_text()
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
    log = (git_repo.coga_os / "log.md").read_text()
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
    assert "not published" in (git_repo.coga_os / "log.md").read_text()


def test_prepare_refuses_mixed_state_without_partial_cleanup(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    (git_repo.root / "src.py").write_text("feature work\n")
    edited = ticket.read_text()

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("src.py (not Coga state)",)
    assert ticket.read_text() == edited
    assert _dirty(git_repo) == {"coga/tasks/demo.md", "src.py"}
    assert _head(git_repo)[0] == "feature/x"


def test_prepare_refuses_staged_content_that_is_not_published(git_repo):
    """The working copy matches control, but the index holds a third version."""
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    published = ticket.read_text()
    ticket.write_text(_ticket_text(blackboard="staged draft\n"))
    git_repo.git("add", "coga/tasks/demo.md")
    ticket.write_text(published)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "staged content" in outcome.blocking[0]
    assert "staged draft" in git_repo.git("show", ":coga/tasks/demo.md")


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
    target.write_text(_ticket_text())
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
        "coga/coga.local.toml\ncoga/.agent-skills/\nbuild/\n"
    )
    git_repo.git("add", ".gitignore")
    git_repo.git("commit", "-m", "ignore build")
    git_repo.git("checkout", "main")
    git_repo.push_competing_commit("build/out.txt", "published\n")
    git_repo.git("checkout", "feature/x")
    (git_repo.root / "build").mkdir()
    (git_repo.root / "build" / "out.txt").write_text("local only\n")

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert outcome.blocking == ("build/out.txt",)
    assert (git_repo.root / "build" / "out.txt").read_text() == "local only\n"


def test_prepare_refuses_when_evidence_changes_before_mutation(git_repo, monkeypatch):
    cfg = load_config(git_repo.coga_os)
    ticket = _feature_with_published_ticket(git_repo, cfg)
    real = git._plan_preparation
    calls = []

    def plan_then_edit(*args, **kwargs):
        plan = real(*args, **kwargs)
        if not calls:
            ticket.write_text(_ticket_text(blackboard="concurrent edit\n"))
        calls.append(plan)
        return plan

    monkeypatch.setattr(git, "_plan_preparation", plan_then_edit)

    outcome = git.prepare_control_checkout(cfg)

    assert outcome.kind == "refused"
    assert "concurrent edit" in ticket.read_text()
    assert _head(git_repo)[0] == "feature/x"


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
    toml.write_text(toml.read_text() + '\n[git]\nremote = "upstream"\ncontrol_branch = "trunk"\n')
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
        command.split(), cwd=git_repo.root, capture_output=True, text=True, check=False
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
    (git_repo.root / "local.txt").write_text("code\n")
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


def test_prepare_realigns_from_a_feature_branch_with_no_control_holder(git_repo, capsys):
    cfg = load_config(git_repo.coga_os)
    tip, hand = _subsumed_divergence(git_repo)
    git_repo.checkout_branch("feature/x")

    _assert_prepared(git_repo, git.prepare_control_checkout(cfg))

    assert (git_repo.coga_os / "tasks" / "demo.md").read_text() == hand
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
    assert (git_repo.coga_os / "tasks" / "demo.md").read_text() == hand
    assert "already published" in (git_repo.coga_os / "log.md").read_text()


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
    (git_repo.root / "code.txt").write_text("feature code\n")
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
        path.write_text(git_repo.git("rev-parse", "HEAD"))
    log = git_repo.coga_os / "log.md"
    log.write_text("dirty\n")
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
    (git_repo.coga_os / "log.md").write_text("dirty\n")
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
    (git_repo.root / "evil.txt").write_text("snuck into the merge\n")
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

    _peer_commit(git_repo, lambda clone: (clone / "coga/tasks/demo.md").chmod(0o755))
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
    seed = (git_repo.coga_os / "log.md").read_text()
    append_log(cfg, "demo", "agent:claude", "committed line")
    mine = (git_repo.coga_os / "log.md").read_text()
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
