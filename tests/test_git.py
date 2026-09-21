"""Tests for `coga.git` — one `publish`, one `refresh`, no local commits.

Each test is named after the guarantee it pins (the acceptance list of
`simplify-git-sync`): control is canonical and local `main` only ever
fast-forwards; an offline write stays dirty and is retried by the sweep; a
stale same-ticket write is refused with the `git checkout origin/main -- …`
hint while different tickets from one base both land; `coga/log.md` is
union-merged; a pending megalaunch claim is sealed; `refresh` fast-forwards a
control checkout and leaves a feature checkout alone; the sweep touches only
task, log, and recurring state.

Real git throughout, via the `git_repo` fixture in conftest (a working tree
with a bare `origin`); `real_git` opts a non-repo test out of the suite-wide
stub.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import git
from coga.cli import app
from coga.config import Config, ConfigError, load_config
from coga.logfile import append_log
from coga.ticket import Ticket

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
    assert "git pull --rebase origin main" in capsys.readouterr().err
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
    assert "git pull --rebase origin main" in capsys.readouterr().err

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


def test_sweep_publishes_only_task_log_and_recurring_state(git_repo):
    cfg = load_config(git_repo.coga_os)
    ticket = _seed_ticket(git_repo)
    ticket.write_text(_ticket_text(status="blocked"))
    append_log(cfg, "demo", "human:marc", "hand edit")
    recurring = git_repo.coga_os / "recurring" / "weekly" / "ticket.md"
    recurring.parent.mkdir(parents=True)
    recurring.write_text("---\ntitle: weekly\n---\n")
    context = git_repo.coga_os / "contexts" / "team" / "SKILL.md"
    context.parent.mkdir(parents=True)
    context.write_text("---\nname: team\n---\nreview me\n")
    (git_repo.coga_os / "workflows" / "code.md").write_text("edited workflow\n")

    git.sync_coga_state(cfg)

    assert "status: blocked" in _control(git_repo, "coga/tasks/demo.md")
    assert "hand edit" in _control(git_repo, "coga/log.md")
    assert _control(git_repo, "coga/recurring/weekly/ticket.md") is not None
    assert _control(git_repo, "coga/contexts/team/SKILL.md") is None
    assert "edited workflow" not in (_control(git_repo, "coga/workflows/code.md") or "")
    assert _dirty(git_repo) == {"coga/contexts/team/SKILL.md", "coga/workflows/code.md"}


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
