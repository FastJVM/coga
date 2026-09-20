"""End-to-end coverage for `[layout] contexts`.

The knob's risk is coverage, not logic: every stage that touches a context has
its own way of naming the directory, and a stage that keeps the old hardcoded
join fails silently rather than loudly. So this walks one relocated directory
through the whole chain — ref resolution, ticket creation, prompt composition,
validation, and the git state sweep — in a single repo, rather than trusting
each module's unit test to have been updated.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga import git
from coga.compose import ComposeError, compose_prompt
from coga.config import ConfigError, load_config
from coga.create import create_task
from coga.paths import resolve_context_path
from coga.tasks import read_ticket, resolve_task
from coga.validate import validate_task


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True,
    ).stdout


@pytest.fixture
def relocated_repo(tmp_path: Path) -> Path:
    """A nested-layout coga repo whose contexts live in `<checkout>/docs/contexts`.

    Deliberately the nested layout with a *sibling* contexts directory: that is
    the combination the old code got wrong everywhere, since `coga/` no longer
    contains the contexts and the single `coga` pathspec no longer covers them.
    Returns the coga root (where `coga.toml` lives).
    """
    checkout = tmp_path / "repo"
    origin = tmp_path / "origin.git"
    coga_os = checkout / "coga"
    coga_os.mkdir(parents=True)

    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"

        [layout]
        contexts = "docs/contexts"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(
        coga_os / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard.
        steps:
          - name: implement
            assignee: agent
          - name: pr
            assignee: agent
        ---

        ## implement
        Write the code.

        ## pr
        Open a PR.
        """,
    )
    _write(
        checkout / "docs" / "contexts" / "email" / "payment-flow" / "SKILL.md",
        """
        ---
        name: email/payment-flow
        description: Retry rules.
        ---

        Stripe retries on 429.
        """,
    )

    subprocess.run(
        ["git", "init", "--bare", "-q", str(origin)], check=True,
    )
    _git(checkout, "init", "-q", "-b", "main")
    _git(checkout, "config", "user.email", "test@example.com")
    _git(checkout, "config", "user.name", "Coga Test")
    _git(checkout, "config", "commit.gpgsign", "false")
    _git(checkout, "remote", "add", "origin", str(origin))
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "-q", "-m", "init coga")
    _git(checkout, "push", "-q", "-u", "origin", "main")
    return coga_os


def test_relocated_contexts_resolve_compose_validate_and_sync(
    relocated_repo: Path,
    real_git,
) -> None:
    # `real_git` opts this test out of the suite-wide `sync_coga_state` no-op,
    # so the final stage exercises the actual pathspec derivation.
    checkout = relocated_repo.parent
    cfg = load_config(relocated_repo)

    # resolve — the ref points at the relocated file, not the packaged battery.
    resolved = resolve_context_path(cfg, "email/payment-flow")
    assert resolved == checkout / "docs" / "contexts" / "email" / "payment-flow" / "SKILL.md"

    # create — a ref outside `coga/` is accepted, not reported as unknown.
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        owner="marc",
        agent="claude",
        status="active",
    )
    ref = resolve_task(cfg, "fix-retry-logic")

    # compose — the relocated context's body lands in the prompt. Without this
    # the ref would silently fall through to the packaged bootstrap batteries.
    prompt = compose_prompt(cfg, ref, read_ticket(ref))
    assert "Stripe retries on 429." in prompt

    # validate — no broken-context issue for a ref that lives outside `coga/`.
    report = validate_task(cfg, "fix-retry-logic")
    assert [i for i in report.issues if i.kind == "broken-context"] == []

    # sync — the created task reaches origin; an edit to a relocated context
    # is review work, not machine state, and the sweep leaves it dirty.
    resolved.write_text(resolved.read_text() + "\nRetry-After is authoritative.\n")
    git.sync_coga_state(cfg, message="Sync coga state")

    tracked = _git(
        tmp_origin := checkout.parent / "origin.git",
        "ls-tree", "-r", "--name-only", "main",
    ).splitlines()
    assert "docs/contexts/email/payment-flow/SKILL.md" in tracked
    assert "coga/tasks/fix-retry-logic.md" in tracked
    committed = _git(
        tmp_origin, "show", "main:docs/contexts/email/payment-flow/SKILL.md"
    )
    assert "Retry-After is authoritative." not in committed
    assert "Retry-After is authoritative." in resolved.read_text()

    clone = checkout.parent / "fresh-clone"
    _git(checkout.parent, "clone", "--branch", "main", str(tmp_origin), str(clone))
    clone_cfg = load_config(clone / "coga", require_user=False)
    clone_ref = resolve_task(clone_cfg, "fix-retry-logic")
    clone_prompt = compose_prompt(clone_cfg, clone_ref, read_ticket(clone_ref))
    assert "Stripe retries on 429." in clone_prompt
    assert "Retry-After is authoritative." in clone_prompt


def test_default_layout_still_resolves_inside_coga_root(tmp_path: Path) -> None:
    """The unset default is unchanged: contexts stay at `coga/contexts/`."""
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(
        coga_os / "contexts" / "email" / "payment-flow" / "SKILL.md",
        "---\nname: email/payment-flow\n---\n\nStripe retries on 429.\n",
    )

    cfg = load_config(coga_os)
    assert cfg.contexts_dir is None
    assert resolve_context_path(cfg, "email/payment-flow") == (
        coga_os / "contexts" / "email" / "payment-flow" / "SKILL.md"
    )


@pytest.mark.parametrize("relocated", [False, True])
@pytest.mark.parametrize("kind", [
    "external", "chain", "dangling", "cycle", "internal", "ignored",
    "ancestor", "dangling-ancestor", "cyclic-ancestor", "tracked-internal",
])
def test_context_artifacts_rejected_before_fallback(
    relocated_repo: Path, tmp_path: Path, relocated: bool, kind: str,
) -> None:
    if not relocated:
        config = relocated_repo / "coga.toml"
        config.write_text(config.read_text().replace(
            '[layout]\ncontexts = "docs/contexts"', "",
        ))
    cfg = load_config(relocated_repo)
    # Use a bundled ref: an invalid local artifact must never become a miss.
    create_task(
        cfg=cfg, title="Check artifact", workflow_name="code/with-review",
        contexts=["coga/sync"], owner="marc", agent="claude", status="active",
    )
    artifact = cfg.contexts_root / "coga" / "sync" / "SKILL.md"
    artifact.parent.mkdir(parents=True)
    target = tmp_path / "machine-local.md"
    target.write_text("MACHINE LOCAL MARKER\n")
    if kind == "chain":
        middle = cfg.contexts_root / "middle.md"
        middle.symlink_to(target)
        artifact.symlink_to(middle)
    elif kind == "dangling":
        artifact.symlink_to(tmp_path / "missing.md")
    elif kind == "cycle":
        artifact.symlink_to("SKILL.md")
    elif kind in {"internal", "ignored", "tracked-internal"}:
        target = relocated_repo.parent / "product-not-swept.md"
        target.write_text("unpublished target\n")
        if kind == "ignored":
            _write(relocated_repo.parent / ".gitignore", "product-not-swept.md\n")
        if kind == "tracked-internal":
            _git(relocated_repo.parent, "add", str(target))
            _git(relocated_repo.parent, "commit", "-m", "tracked internal target")
        artifact.symlink_to(target)
    elif kind in {"dangling-ancestor", "cyclic-ancestor"}:
        artifact.parent.rmdir()
        artifact.parent.symlink_to("sync" if kind == "cyclic-ancestor" else "missing")
    elif kind == "ancestor":
        artifact.parent.rmdir()
        target = tmp_path / "external-context"
        _write(target / "SKILL.md", "external ancestor\n")
        artifact.parent.symlink_to(target, target_is_directory=True)
    else:
        artifact.symlink_to(target)

    with pytest.raises(ConfigError, match="symlink"):
        resolve_context_path(cfg, "coga/sync")
    ref = resolve_task(cfg, "check-artifact")
    with pytest.raises(ComposeError, match="symlink"):
        compose_prompt(cfg, ref, read_ticket(ref))
    report = validate_task(cfg, "check-artifact")
    assert any(
        i.kind == "broken-context" and "symlink" in i.message for i in report.issues
    )

    # Preserve the invalid entry in Git, remove the external bytes, and prove
    # a fresh checkout rejects it too (including when the target is absent).
    _git(relocated_repo.parent, "add", "-A")
    _git(relocated_repo.parent, "commit", "-m", "invalid context")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(relocated_repo.parent), str(clone))
    if kind in {"external", "chain"}:
        target.unlink()
    try:
        clone_cfg = load_config(clone / "coga")
    except ConfigError as exc:
        assert relocated and "symlink" in str(exc)
    else:
        with pytest.raises(ConfigError, match="symlink"):
            resolve_context_path(clone_cfg, "coga/sync")


@pytest.mark.parametrize("relocated", [False, True])
@pytest.mark.parametrize("kind", ["ignored", "nested-checkout", "directory"])
def test_unpublishable_regular_context_rejected(
    relocated_repo: Path, relocated: bool, kind: str,
) -> None:
    if not relocated:
        config = relocated_repo / "coga.toml"
        config.write_text(config.read_text().replace(
            '[layout]\ncontexts = "docs/contexts"', "",
        ))
    cfg = load_config(relocated_repo)
    artifact = cfg.contexts_root / "coga" / "sync" / "SKILL.md"
    _write(artifact, "unpublishable context\n")
    if kind == "ignored":
        _write(relocated_repo.parent / ".gitignore", "**/sync/SKILL.md\n")
    elif kind == "nested-checkout":
        _git(artifact.parent, "init", "-q")
    else:
        artifact.unlink()
        artifact.mkdir()
    with pytest.raises(ConfigError):
        resolve_context_path(cfg, "coga/sync")


def test_context_attachment_symlink_does_not_change_resolution(relocated_repo: Path) -> None:
    cfg = load_config(relocated_repo)
    artifact = resolve_context_path(cfg, "email/payment-flow")
    assert artifact is not None
    (artifact.parent / "notes.md").symlink_to("missing-notes.md")
    (artifact.parent / "attachments").symlink_to(relocated_repo, target_is_directory=True)
    assert resolve_context_path(load_config(relocated_repo), "email/payment-flow") == artifact
