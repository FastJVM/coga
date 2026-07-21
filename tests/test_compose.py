from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from textwrap import dedent

import pytest

from coga.blackboard import append_blocker, resolve_open_blockers
from coga.create import create_task
from coga.slugify import slugify
from coga.compose import (
    ComposeError,
    compose_prompt,
    compose_prompt_report,
    write_prompt_file,
)
from coga.config import load_config
from coga.tasks import list_tasks, read_ticket, resolve_bootstrap
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_workflow_less_task(
    repo: Path, *, title: str, status: str = "active"
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
    # Agent prompt
    assert "Agent mode" in prompt
    # Repo context
    assert "Email tool is YC-backed" in prompt
    # Ticket context
    assert "Stripe retries on 429" in prompt
    # Step skill
    assert "Run tests with pytest" in prompt
    assert "Current step: implement" in prompt
    # Blackboard present
    assert "Blackboard" in prompt


def test_compose_agent_prompt_attended_ask_and_wait(repo: Path) -> None:
    """A full ordinary step prompt directs the agent to ask the present human
    and wait; blocking is reserved for an explicit human request, and no layer
    carries a generic direction to block merely because input is needed."""
    # Exercise the shipped inline peer-review step, not the fixture's neutral
    # local workflow/skill, so a later-composed stock layer cannot contradict
    # the attended mode unnoticed.
    (repo / "workflows" / "code" / "with-review.md").unlink()
    cfg = load_config(repo)
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
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = "2 (peer-review)"
    ticket.write(ref.ticket_path)
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    normalized_prompt = " ".join(prompt.split())

    # The attended default: the human is in the REPL — ask and wait.
    assert "This launch is attended — ask and wait." in normalized_prompt
    assert "ask them directly and wait for their answer" in normalized_prompt
    # Blocking is reserved for an explicit human request to park the ticket.
    assert (
        "block only when the human explicitly asks you to park or block the"
        " ticket" in normalized_prompt
    )
    # The attended rule wins over generic block wording in downstream layers.
    assert (
        "This attended rule is authoritative over any generic instruction"
        in normalized_prompt
    )
    assert "Current step: peer-review" in normalized_prompt
    assert "escalate per your launch mode" in normalized_prompt
    # No layer steers the agent to block merely because input is needed.
    assert "Ask or block when uncertain" not in normalized_prompt
    assert "call `coga block` with a specific ask" not in normalized_prompt
    assert "that's `coga block` — never a quiet exit" not in normalized_prompt
    assert (
        "Use `coga block` when progress needs a concrete decision"
        not in normalized_prompt
    )
    assert "blackboard and `coga block` instead" not in normalized_prompt
    assert (
        "If your review tool isn't on PATH, `coga block`"
        not in normalized_prompt
    )
    assert (
        "If a conflict needs a call you can't make, `coga block`"
        not in normalized_prompt
    )
    # The queue directive is a megalaunch suffix, never an ordinary layer.
    assert "Megalaunch queue execution" not in normalized_prompt


@pytest.mark.parametrize(
    ("workflow_name", "step", "heading", "legacy_direction"),
    [
        (
            "code/with-self-review",
            "2 (self-qa)",
            "Self-QA the diff",
            "`coga block` — something is off",
        ),
        (
            "code/with-review",
            "3 (open-pr)",
            "Push and open the PR",
            "earlier-step gap — `coga block` with a one-line reason",
        ),
        (
            "direct/body",
            "1 (execute)",
            "Run the ticket body directly",
            "If you are blocked before completion, `coga block` with a reason",
        ),
    ],
)
def test_stock_step_prompt_escalates_per_launch_mode(
    repo: Path,
    workflow_name: str,
    step: str,
    heading: str,
    legacy_direction: str,
) -> None:
    """Other shipped agent steps do not append a generic block command."""
    if workflow_name == "code/with-review":
        (repo / "workflows" / "code" / "with-review.md").unlink()
    elif workflow_name == "direct/body":
        resources = files("coga.resources").joinpath("templates/coga")
        _write(
            repo / "workflows" / "direct" / "body.md",
            resources.joinpath("workflows/direct/body.md").read_text(),
        )
        _write(
            repo / "skills" / "direct" / "body" / "SKILL.md",
            resources.joinpath("skills/direct/body/SKILL.md").read_text(),
        )
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Check stock escalation",
        workflow_name=workflow_name,
        contexts=[],
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    ticket.frontmatter["step"] = step
    ticket.write(ref.ticket_path)

    normalized_prompt = " ".join(
        compose_prompt(cfg, ref, read_ticket(ref)).split()
    )

    assert heading in normalized_prompt
    assert "escalate per your launch mode" in normalized_prompt
    assert legacy_direction not in normalized_prompt


def test_compose_browser_automation_bootstrap_uses_bundled_router_skill(
    repo: Path,
) -> None:
    """The browser entry point composes package-backed orchestration without
    creating a standing task or loading the lower-level runner prematurely."""
    _write(
        repo / "contexts" / "browser" / "api-first" / "SKILL.md",
        "---\nname: browser/api-first\n---\n\nPrefer the API marker.\n",
    )
    cfg = load_config(repo)
    ref = resolve_bootstrap(cfg, "browser-automation")
    ticket = read_ticket(ref)

    composition = compose_prompt_report(cfg, ref, ticket)
    prompt = composition.prompt
    normalized_prompt = " ".join(prompt.split())
    layers = {(layer.layer, layer.ref) for layer in composition.layers}

    assert ticket.status == ""
    assert ticket.workflow is None
    assert ticket.step is None
    assert ("ticket_context", "browser/api-first") in layers
    assert ("top_level_skill", "browser/build-automation") in layers
    assert "Coga task — bootstrap/browser-automation" in prompt
    assert "Prefer the API marker." in prompt
    assert "Skill: browser/build-automation" in prompt
    assert "The skill does not drive the browser itself" in normalized_prompt
    assert "# Playwright CLI Skill" not in prompt
    assert list_tasks(cfg) == []


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


def test_compose_llm_mode_uses_llm_block(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Agent task")
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Agent mode" in prompt


def test_compose_open_blockers_add_resolution_preamble(repo: Path) -> None:
    """An Agent ticket with open asks composes the resolve-or-re-block
    preamble, listing each ask verbatim (stale/junk ones included)."""
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Blocked work")
    ref = list_tasks(cfg)[0]
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    append_blocker(ref.ticket_path, "human:marc", "test")

    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Resolve the open blocker first" in prompt
    assert "which retry ceiling?" in prompt
    assert "test" in prompt
    assert f"coga unblock {ref.id_slug} --answer" in prompt
    assert f"coga block --task {ref.id_slug} --reason" in prompt
    # Leading: the preamble sits before the repo context layer.
    assert prompt.index("Resolve the open blocker first") < prompt.index(
        "Email tool is YC-backed"
    )

    composition = compose_prompt_report(cfg, ref, ticket)
    assert any(layer.layer == "blocker_preamble" for layer in composition.layers)


def test_compose_resolved_blockers_compose_no_preamble(repo: Path) -> None:
    cfg = load_config(repo)
    _write_workflow_less_task(repo, title="Answered work")
    ref = list_tasks(cfg)[0]
    append_blocker(ref.ticket_path, "agent:claude", "which retry ceiling?")
    resolve_open_blockers(ref.ticket_path, "human:marc", "cap at 5 minutes")

    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    assert "Resolve the open blocker first" not in prompt


def test_compose_inline_step_instructions(repo: Path) -> None:
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="T",
        workflow_name="code/with-review",
        contexts=[],
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
            "mode": "agent",
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
