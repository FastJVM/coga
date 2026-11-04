"""`coga run publish-state` and the `build/onboarding` handoff that uses it.

Onboarding's generate-batch step may offer `coga launch <slug>` only after the
agreed `product/vision` and the starter tickets are confirmed on the control
branch. These tests walk that publish-then-handoff path from an empty
repository through a real `coga init`, a bare `origin`, and a fresh clone,
rather than trusting the template's prose: the reported failure was a
starter ticket whose vision context never reached Git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import windows_skip
from typer.testing import CliRunner

from coga import validate
from coga.aliases import ONBOARDING_TASK
from coga.cli import app
from coga.compose import compose_prompt
from coga.config import load_config
from coga.create import create_task
from coga.taskfile import read_blackboard
from coga.tasks import read_ticket, resolve_task


VISION_BODY = "A habit tracker for night-shift nurses. v1 is a CLI."
STARTERS = (
    ("Build the habit log CLI", "code/design-then-implement"),
    ("Decide the storage format", "draft-for-human"),
)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout



def _publish_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Exercise cli.main too: its final sweep must respect refusals."""
    return subprocess.run(
        [sys.executable, "-m", "coga.cli", "run", "publish-state", *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def _origin_files(origin: Path) -> list[str]:
    return _git(origin, "ls-tree", "-r", "--name-only", "main").splitlines()


def _onboarded_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contexts: str | None
) -> tuple[Path, Path, list[Path]]:
    """Init an empty repo, then do what onboarding writes before its handoff.

    Returns (checkout, origin, files onboarding names to publish-state). The
    vision and the starter tickets are left unpublished — creation's own
    best-effort sync is stubbed out — so only the explicit publish can land
    them, the shape of a missed sweep or a session that ended before `bump`.
    """
    origin = tmp_path / "origin.git"
    checkout = tmp_path / "company"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(checkout))
    _git(checkout, "config", "user.email", "test@example.com")
    _git(checkout, "config", "user.name", "Coga Test")
    _git(checkout, "config", "commit.gpgsign", "false")
    _git(checkout, "remote", "add", "origin", str(origin))

    result = CliRunner().invoke(app, ["init", str(checkout), "--user", "tester"])
    assert result.exit_code == 0, result.output
    coga_os = checkout / "coga"
    assert (coga_os / "tasks" / f"{ONBOARDING_TASK}.md").is_file()
    if contexts is not None:
        (checkout / contexts).parent.mkdir(parents=True, exist_ok=True)
        _git(checkout, "mv", "coga/contexts", contexts)
        toml = coga_os / "coga.toml"
        toml.write_text(toml.read_text(encoding="utf-8") + f'\n[layout]\ncontexts = "{contexts}"\n', encoding="utf-8", newline="\n")
        _git(checkout, "commit", "-q", "-am", "Relocate contexts")
    _git(checkout, "push", "-q", "-u", "origin", "main")

    cfg = load_config(coga_os)
    contexts_dir = checkout / (contexts or "coga/contexts")
    assert cfg.contexts_root == contexts_dir
    vision = contexts_dir / "product" / "vision" / "SKILL.md"
    vision.parent.mkdir(parents=True)
    vision.write_text(
        "---\nname: product/vision\ndescription: What we are building.\n---\n\n"
        f"{VISION_BODY}\n",
        encoding="utf-8", newline="\n",
    )
    with monkeypatch.context() as m:
        m.setattr("coga.git.sync_task_state", lambda *a, **k: None)
        tickets = [
            Path(
                create_task(
                    cfg=cfg,
                    title=title,
                    workflow_name=workflow,
                    contexts=["product/vision"],
                    owner="tester",
                    status="draft",
                    body="## Description\n\nStarter work from the vision.\n",
                )["path"]
            )
            for title, workflow in STARTERS
        ]
    tickets = [path / "ticket.md" if path.is_dir() else path for path in tickets]
    published = _origin_files(origin)
    for path in (vision, *tickets):
        assert path.relative_to(checkout).as_posix() not in published
    monkeypatch.chdir(checkout)
    return checkout, origin, [vision, *tickets]


@pytest.mark.parametrize("contexts", [None, "docs/contexts"])
def test_onboarding_publish_then_handoff_from_empty_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git, contexts: str | None,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, contexts)
    rels = [path.relative_to(checkout).as_posix() for path in files]

    result = _publish_cli(*rels)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "publish-state: published to origin/main" in result.stdout
    for rel in rels:
        assert f"  {rel}\n" in result.stdout
        assert rel in _origin_files(origin)

    # The handoff's promise: a teammate's fresh clone can launch any starter.
    clone = tmp_path / "fresh-clone"
    _git(tmp_path, "clone", "-q", "--branch", "main", str(origin), str(clone))
    clone_cfg = load_config(clone / "coga", require_user=False)
    for path in files[1:]:
        slug = path.parent.name if path.name == "ticket.md" else path.stem
        ref = resolve_task(clone_cfg, slug)
        assert VISION_BODY in compose_prompt(clone_cfg, ref, read_ticket(ref))
    report = validate.run(clone_cfg)
    errors = [issue for issue in report.issues if issue.severity == "error"]
    assert errors == []


def test_onboarding_publish_failure_leaves_unfinished_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    rels = [path.relative_to(checkout).as_posix() for path in files]
    onboarding = checkout / "coga" / "tasks" / f"{ONBOARDING_TASK}.md"
    cfg = load_config(checkout / "coga")
    step_before = read_ticket(resolve_task(cfg, ONBOARDING_TASK)).frontmatter["step"]
    # The remote goes away between the handoff's writes and its publication.
    shutil.move(origin, tmp_path / "gone.git")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(onboarding))
    monkeypatch.setenv("COGA_TASK_SLUG", ONBOARDING_TASK)

    result = _publish_cli(*rels)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "publish-state: publication" in result.stderr
    assert "published to" not in result.stdout
    # Recoverable: every file is still on disk exactly where onboarding wrote it.
    for path in files:
        assert path.is_file()
    assert VISION_BODY in files[0].read_text(encoding="utf-8")
    # No bump: the step a successful handoff would advance is unchanged.
    after = read_ticket(resolve_task(cfg, ONBOARDING_TASK))
    assert after.frontmatter["step"] == step_before
    # The explicit record on the onboarding ticket's blackboard.
    blackboard = read_blackboard(onboarding)
    assert "## Recipe Failure" in blackboard
    assert "publish-state" in blackboard
    assert "publication" in blackboard


def test_publish_state_refuses_paths_outside_the_coga_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    source = checkout / "app.py"
    source.write_text("print('hi')\n", encoding="utf-8", newline="\n")
    before = _origin_files(origin)

    outside = _publish_cli("app.py")
    missing = _publish_cli("coga/contexts/product/missing/SKILL.md")

    assert outside.returncode == 2
    assert "outside the Coga roots" in outside.stderr
    assert missing.returncode == 2
    assert "not a regular file" in missing.stderr
    assert _origin_files(origin) == before


def test_publish_state_disabled_git_reports_local_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    toml = checkout / "coga" / "coga.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + "\n[git]\nenabled = false\n", encoding="utf-8", newline="\n")

    result = _publish_cli(files[0].relative_to(checkout).as_posix())

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[git].enabled = false" in result.stdout


@pytest.mark.parametrize("remote_change", ["unreachable", "deleted-vision", "deleted-branch"])
def test_publish_state_rechecks_control_on_unchanged_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git, remote_change: str,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    rels = [path.relative_to(checkout).as_posix() for path in files]
    first = _publish_cli(*rels)
    assert first.returncode == 0, first.stderr
    before = [path.read_bytes() for path in files]
    if remote_change == "unreachable":
        shutil.move(origin, tmp_path / "gone.git")
    elif remote_change == "deleted-branch":
        _git(origin, "update-ref", "-d", "refs/heads/main")
    else:
        other = tmp_path / "other"
        _git(tmp_path, "clone", "-q", "-b", "main", str(origin), str(other))
        _git(other, "config", "user.email", "test@example.com")
        _git(other, "config", "user.name", "Coga Test")
        _git(other, "config", "commit.gpgsign", "false")
        _git(other, "rm", rels[0])
        _git(other, "commit", "-qm", "Remove vision")
        _git(other, "push", "-q", "origin", "main")

    retry = _publish_cli(*rels)

    assert retry.returncode == 1, retry.stdout + retry.stderr
    assert "already on" not in retry.stdout
    assert [path.read_bytes() for path in files] == before


def test_publish_state_refusal_does_not_sweep_tickets_without_their_vision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    rels = [path.relative_to(checkout).as_posix() for path in files]
    _git(checkout, "switch", "-c", "feature")
    _git(checkout, "add", rels[0])
    _git(checkout, "commit", "-qm", "Vision pending review")
    published_before = _origin_files(origin)

    result = _publish_cli(*rels)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "excluded from publication" in result.stderr
    assert _origin_files(origin) == published_before
    assert all(path.is_file() for path in files)


@pytest.mark.parametrize("detached", [False, True])
@pytest.mark.parametrize("filename,change", [
    ("ticket.md", "content"), ("ticket.py", "content"),
    ("retires.md", "content"), ("ticket.py", "mode"),
])
def test_publish_state_refusal_does_not_sweep_state_without_required_recurring(
    git_repo, detached, filename, change,
) -> None:
    from coga.logfile import append_log, log_path

    cfg = load_config(git_repo.coga_os)
    template = git_repo.coga_os / "recurring" / "weekly" / filename
    template.parent.mkdir(parents=True)
    template.write_text("original\n", encoding="utf-8", newline="\n")
    rel = template.relative_to(git_repo.root).as_posix()
    git_repo.git("add", rel)
    git_repo.git("commit", "-m", "seed recurring")
    git_repo.git("push", "origin", "main")
    git_repo.checkout_branch("feature/x")
    if change == "content":
        template.write_text("pending review\n", encoding="utf-8", newline="\n")
        git_repo.git("add", rel)
    else:
        if os.name == "posix":
            template.chmod(0o755)
        git_repo.git("update-index", "--chmod=+x", rel)
    git_repo.git("commit", "-m", "recurring pending review")
    if detached:
        git_repo.git("checkout", "--detach")
    task = git_repo.coga_os / "tasks" / "demo.md"
    task.write_text(_RESTRICTED_TICKET, encoding="utf-8", newline="\n")
    append_log(cfg, "demo", "agent:claude", "pending handoff")
    paths = (template, task, log_path(cfg))
    before = [path.read_bytes() for path in paths]
    head = git_repo.git("rev-parse", "HEAD")
    index = git_repo.git("ls-files", "--stage")
    control = git_repo.git("rev-parse", "main", cwd=git_repo.origin)

    result = _publish_cli(*(str(path) for path in paths))

    assert result.returncode == 1, result.stdout + result.stderr
    assert "required file is excluded from publication" in result.stderr
    assert "merge its reviewed change before retrying" in result.stderr
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == control
    assert git_repo.git("rev-parse", "HEAD") == head
    assert git_repo.git("ls-files", "--stage") == index
    assert [path.read_bytes() for path in paths] == before


@pytest.mark.parametrize("detached", [False, True])
def test_publish_state_accepts_committed_recurring_already_identical_to_control(git_repo, detached):
    template = git_repo.coga_os / "recurring" / "weekly" / "ticket.py"
    template.parent.mkdir(parents=True)
    git_repo.checkout_branch("feature/x")
    template.write_text("print('reviewed')\n", encoding="utf-8", newline="\n")
    rel = template.relative_to(git_repo.root).as_posix()
    git_repo.git("add", rel)
    git_repo.git("commit", "-m", "recurring on branch")
    if detached:
        git_repo.git("checkout", "--detach")
    git_repo.push_competing_commit(rel, template.read_text(encoding="utf-8"))
    control = git_repo.git("rev-parse", "main", cwd=git_repo.origin)

    result = _publish_cli(str(template))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "already on origin/main" in result.stdout
    assert git_repo.git("rev-parse", "main", cwd=git_repo.origin) == control
    assert git_repo.git("status", "--porcelain") == ""


@pytest.mark.parametrize("separator", [[], ["--"]])
def test_publish_state_missing_user_does_not_sweep_before_recipe_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git, separator: list[str],
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    rels = [path.relative_to(checkout).as_posix() for path in files]
    _git(checkout, "switch", "-c", "feature")
    _git(checkout, "add", rels[0])
    _git(checkout, "commit", "-qm", "Vision pending review")
    (checkout / "coga" / "coga.local.toml").write_text("", encoding="utf-8", newline="\n")
    published_before = _git(origin, "rev-parse", "main")
    bytes_before = [path.read_bytes() for path in files]

    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "run", *separator, "publish-state", *rels],
        capture_output=True, text=True, encoding="utf-8",
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "user" in result.stderr
    assert _git(origin, "rev-parse", "main") == published_before
    assert [path.read_bytes() for path in files] == bytes_before


_RESTRICTED_TICKET = """---
title: demo
status: in_progress
owner: marc
agent: claude
workflow:
  name: code
  steps:
  - name: implement
    assignee: agent
  - name: review
    assignee: agent
step: 1 (implement)
---

## Description

Demo.

<!-- coga:blackboard -->

notes
"""


@windows_skip("POSIX filesystem mode bits and permissions")
def test_publish_state_recovers_a_bump_whose_object_writes_were_denied(
    git_repo, tmp_path: Path
) -> None:
    """One transition, two failed publications, then recovery without another bump."""
    ticket = git_repo.coga_os / "tasks" / "demo.md"
    ticket.write_text(_RESTRICTED_TICKET, encoding="utf-8", newline="\n")
    git_repo.git("add", "--", "coga/tasks/demo.md")
    git_repo.git("commit", "-qm", "seed demo")
    git_repo.git("push", "-q", "origin", "main")
    store = tmp_path / "restricted objects"
    store.mkdir()
    store.chmod(0o555)
    if os.access(store, os.W_OK):
        store.chmod(0o755)
        pytest.skip("chmod does not restrict this user (e.g. root)")
    # The checkout stays writable; only the object database Git writes to is not.
    denied = {
        **os.environ,
        "GIT_OBJECT_DIRECTORY": str(store),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(git_repo.root / ".git" / "objects"),
    }

    def cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "coga.cli", *args],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def origin_ticket() -> str:
        return _git(git_repo.origin, "show", "main:coga/tasks/demo.md")

    def origin_log() -> str:
        return _git(git_repo.origin, "show", "main:coga/log.md")

    try:
        bumped = cli("bump", "demo", env=denied)

        assert bumped.returncode == 0, bumped.stdout + bumped.stderr
        assert "review" in bumped.stdout
        # Task sync and the exit sweep each fail once. The retained-log warning
        # also echoes their audit lines; those are not additional attempts.
        assert sum(
            line.startswith("[git] sync failed: `git hash-object -w` failed")
            for line in bumped.stderr.splitlines()
        ) == 2
        assert "advanced to step 2" in bumped.stderr
        assert f"object directory {store}" in bumped.stderr
        assert "Message was: Sync coga state" in bumped.stderr
        assert "Local task state was saved; Git publication failed." in bumped.stderr
        assert "Do not rerun `coga bump` to recover." in bumped.stderr
        assert "coga run publish-state tasks/demo.md log.md" in bumped.stderr
        assert "step: 2 (review)" in ticket.read_text(encoding="utf-8")
        assert "step: 1 (implement)" in origin_ticket()
        local_log = (git_repo.coga_os / "log.md").read_text(encoding="utf-8")
        assert local_log.count("advanced to step 2") == 1

        # Recovery while access is still denied fails loudly and keeps state.
        still_denied = cli("run", "publish-state", "tasks/demo.md", "log.md", env=denied)
        assert still_denied.returncode == 1, still_denied.stdout + still_denied.stderr
        assert "publication failed" in still_denied.stderr
        assert "step: 2 (review)" in ticket.read_text(encoding="utf-8")
        assert "step: 1 (implement)" in origin_ticket()
    finally:
        store.chmod(0o755)

    subjects = len(git_repo.origin_subjects())
    recovered = cli("run", "publish-state", "tasks/demo.md", "log.md")

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert "published to origin/main" in recovered.stdout
    assert "step: 2 (review)" in origin_ticket()
    assert "step: 2 (review)" in ticket.read_text(encoding="utf-8")
    assert origin_log().count("advanced to step 2") == 1
    assert len(git_repo.origin_subjects()) == subjects + 1

    repeated = cli("run", "publish-state", "tasks/demo.md", "log.md")

    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert "already on origin/main" in repeated.stdout
    assert len(git_repo.origin_subjects()) == subjects + 1
    assert origin_log().count("advanced to step 2") == 1
    assert "step: 2 (review)" in ticket.read_text(encoding="utf-8")
