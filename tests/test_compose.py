from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga.create import create_task
from coga.slugify import slugify
from coga.compose import (
    ComposeError,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from coga.config import load_config
from coga.tasks import list_tasks, read_ticket
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_workflow_less_task(
    repo: Path, *, title: str, mode: str = "interactive", status: str = "active"
) -> str:
    """Write a workflow-less task directly to disk. `create_task` refuses to
    create a workflow-less non-draft task now, but compose handles a
    workflow-less ticket fine, so on-disk construction keeps these
    compose-only tests focused on a minimal (no workflow-step layer) prompt."""
    slug = slugify(title)
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    # Single-file format: body + fence + blackboard region, no sibling
    # blackboard.md / log.md (history lives in the repo-global log).
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        slug: {slug}
        title: {title}
        status: {status}
        autonomy: {mode}
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        ---

        ## Description

        ## Context

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())
    return slug


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "coga"

    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard.
        steps:
          - name: implement
            skills:
              - infra/testing-conventions
          - name: pr
        ---

        ## pr
        Open a PR. Push branch first.
        """,
    )
    _write(
        company / "skills" / "infra" / "testing-conventions" / "SKILL.md",
        "---\nname: infra/testing-conventions\n---\n\nRun tests with pytest.\n",
    )
    _write(
        company / "contexts" / "email" / "payment-flow" / "SKILL.md",
        "---\nname: email/payment-flow\n---\n\nStripe retries on 429.\n",
    )
    _write(company / "context.md", "Email tool is YC-backed.\n")
    return company


def test_compose_includes_all_sections(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # Header
    assert "Coga task — fix-retry-logic" in prompt
    assert "Task directory: coga/tasks/fix-retry-logic" in prompt
    # Base prompt
    assert "You are an agent working on a ticket inside Coga" in prompt
    # Interactive prompt
    assert "Interactive mode" in prompt
    # Repo context
    assert "Email tool is YC-backed" in prompt
    # Ticket context
    assert "Stripe retries on 429" in prompt
    # Step skill
    assert "Run tests with pytest" in prompt
    assert "Current step: implement" in prompt
    # Blackboard present
    assert "Blackboard" in prompt


def test_compose_header_uses_resolved_nested_task_directory(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Fix retry logic")
    top = repo / "tasks" / "fix-retry-logic"
    nested = repo / "tasks" / "auto" / "fix-retry-logic"
    nested.parent.mkdir()
    top.rename(nested)

    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # A nested task is identified by its path under `tasks/`.
    assert "Coga task — auto/fix-retry-logic" in prompt
    assert "Task directory: coga/tasks/auto/fix-retry-logic" in prompt


def test_base_prompt_teaches_exit_after_bump(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="code/with-review",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Run `bump` as the *last* thing in the current step" in prompt
    assert "After bumping, exit cleanly" in prompt
    assert "One step, one session" in prompt
    assert "API/manual sessions don't chain" in prompt
    assert "coga mark done" in prompt
    assert "Never stop silently" in prompt
    # Supervisor respawn/teardown mechanics are reference the agent can't act
    # on; they live in coga/architecture now (loaded only when a ticket
    # attaches it), not in every base prompt. This ticket has no contexts, so
    # those phrases are absent here.
    assert "How the supervisor chains steps is in `coga/architecture`" in prompt
    assert "respawns the next agent step" not in prompt
    assert "clean prompt scope" not in prompt
    # Old continue-in-same-session rule must be gone.
    assert "After bumping, inspect the new state" not in prompt
    assert "continue that next step in this same session" not in prompt
    assert "coga bump` marks the task `done`" not in prompt


def test_compose_prompt_report_tracks_layers_and_refs(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)

    composition = compose_prompt_report(cfg, ref, ticket)
    assert composition.prompt == compose_prompt(cfg, ref, ticket)
    assert composition.byte_count > 0
    assert composition.approx_tokens > 0

    layers = {(layer.layer, layer.ref): layer for layer in composition.layers}
    assert ("ticket_context", "email/payment-flow") in layers
    assert ("workflow_skill", "infra/testing-conventions") in layers
    assert ("blackboard", "ticket.md##blackboard") in layers
    assert layers[("ticket_context", "email/payment-flow")].approx_tokens > 0


def test_compose_auto_mode_uses_auto_block(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Auto task", mode="auto")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Auto mode" in prompt
    assert "Interactive mode" not in prompt


def test_compose_inline_step_instructions(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="T",
        workflow_name="code/with-review",
        contexts=[],
        autonomy="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    # Advance to step 2 (pr) — has inline instructions, no skill
    ticket.frontmatter["step"] = "2 (pr)"
    ticket.write(ref.ticket_path)
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Open a PR. Push branch first." in prompt
    assert "Current step: pr" in prompt


def test_compose_raises_on_missing_context(repo: Path) -> None:
    """A referenced context with no file fails loud instead of silently dropping."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost ctx")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    # Simulate a context ref whose file was deleted after the ticket was authored.
    ticket.frontmatter["contexts"] = ["email/ghost"]

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    msg = str(exc.value)
    assert "email/ghost" in msg
    assert ref.id_slug in msg
    # Names the exact path the user should create.
    assert "email/ghost/SKILL.md" in msg


def test_compose_raises_on_missing_ticket_level_skill(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost skill")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["skills"] = ["infra/ghost"]

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    msg = str(exc.value)
    assert "infra/ghost" in msg
    assert ref.id_slug in msg
    assert "infra/ghost/SKILL.md" in msg


def test_compose_raises_on_missing_step_skill(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Ghost step skill")
    ref = list_tasks(cfg)[0]
    # Hand-build a ticket whose frozen workflow step points at a missing skill.
    ticket = Ticket(
        frontmatter={
            "title": "Ghost step skill",
            "status": "in_progress",
            "autonomy": "interactive",
            "contexts": [],
            "skills": [],
            "workflow": {
                "name": "code/with-review",
                "steps": [{"name": "implement", "skills": ["infra/ghost"]}],
            },
            "step": "1 (implement)",
        },
        body="## Description\n\nDo the thing.\n\n<!-- coga:blackboard -->\n\n# Blackboard\n",
    )

    with pytest.raises(ComposeError) as exc:
        compose_prompt(cfg, ref, ticket)
    assert "infra/ghost" in str(exc.value)


def test_write_prompt_file(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="X")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    out = write_prompt_file(prompt, ref, dest_dir=tmp_path)
    assert out.exists()
    assert out.read_text() == prompt
    assert out.name.startswith("coga-x-")
