"""`coga run publish-state` and the `build/onboarding` handoff that uses it.

Onboarding's generate-batch step may offer `coga launch <slug>` only after the
agreed `product/vision` and the starter tickets are confirmed on the control
branch. These tests walk that publish-then-handoff path from an empty
repository through a real `coga init`, a bare `origin`, and a fresh clone,
rather than trusting the template's prose: the reported failure was a
starter ticket whose vision context never reached Git.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
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
        check=True, capture_output=True, text=True,
    ).stdout


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
        toml.write_text(toml.read_text() + f'\n[layout]\ncontexts = "{contexts}"\n')
        _git(checkout, "commit", "-q", "-am", "Relocate contexts")
    _git(checkout, "push", "-q", "-u", "origin", "main")

    cfg = load_config(coga_os)
    contexts_dir = checkout / (contexts or "coga/contexts")
    assert cfg.contexts_root == contexts_dir
    vision = contexts_dir / "product" / "vision" / "SKILL.md"
    vision.parent.mkdir(parents=True)
    vision.write_text(
        "---\nname: product/vision\ndescription: What we are building.\n---\n\n"
        f"{VISION_BODY}\n"
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

    result = CliRunner().invoke(app, ["run", "publish-state", *rels])

    assert result.exit_code == 0, result.output
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

    result = CliRunner().invoke(app, ["run", "publish-state", *rels])

    assert result.exit_code == 1, result.output
    assert "publish-state: publication" in result.stderr
    assert "published to" not in result.stdout
    # Recoverable: every file is still on disk exactly where onboarding wrote it.
    for path in files:
        assert path.is_file()
    assert VISION_BODY in files[0].read_text()
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
    source.write_text("print('hi')\n")
    before = _origin_files(origin)

    outside = CliRunner().invoke(app, ["run", "publish-state", "app.py"])
    missing = CliRunner().invoke(
        app, ["run", "publish-state", "coga/contexts/product/missing/SKILL.md"]
    )

    assert outside.exit_code == 2
    assert "outside the Coga roots" in outside.stderr
    assert missing.exit_code == 2
    assert "not a regular file" in missing.stderr
    assert _origin_files(origin) == before


def test_publish_state_disabled_git_reports_local_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, real_git,
) -> None:
    checkout, origin, files = _onboarded_repo(tmp_path, monkeypatch, None)
    toml = checkout / "coga" / "coga.toml"
    toml.write_text(toml.read_text() + "\n[git]\nenabled = false\n")

    result = CliRunner().invoke(
        app, ["run", "publish-state", files[0].relative_to(checkout).as_posix()]
    )

    assert result.exit_code == 0, result.output
    assert "[git].enabled = false" in result.stdout
