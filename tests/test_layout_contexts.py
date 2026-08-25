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
from coga.compose import compose_prompt
from coga.config import load_config
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
          - name: pr
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
        assignee="claude",
        watchers=[],
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

    # sync — an edit to a relocated context is Coga state and reaches origin.
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
    assert "Retry-After is authoritative." in committed


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
