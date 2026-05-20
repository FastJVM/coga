from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.scaffold import scaffold_task
from relay.compose import compose_prompt, compose_prompt_report, write_prompt_file
from relay.config import load_config
from relay.tasks import list_tasks, read_ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "relay-os"

    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
    _write(company / "rules.md", "Never commit secrets.\n")
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
    scaffold_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        mode="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # Header
    assert "Relay task — fix-retry-logic" in prompt
    # Base prompt
    assert "You are an agent working on a ticket inside Relay" in prompt
    # Interactive prompt
    assert "Interactive mode" in prompt
    # Rules
    assert "Never commit secrets" in prompt
    # Repo context
    assert "Email tool is YC-backed" in prompt
    # Ticket context
    assert "Stripe retries on 429" in prompt
    # Step skill
    assert "Run tests with pytest" in prompt
    assert "Current step: implement" in prompt
    # Blackboard present
    assert "Blackboard" in prompt


def test_base_prompt_teaches_exit_after_bump(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Chain work",
        workflow_name="code/with-review",
        contexts=[],
        mode="interactive",
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
    assert "respawns the next agent step" in prompt
    assert "clean prompt scope" in prompt
    assert "API/manual sessions don't chain" in prompt
    assert "relay mark done" in prompt
    # Old continue-in-same-session rule must be gone.
    assert "After bumping, inspect the new state" not in prompt
    assert "continue that next step in this same session" not in prompt
    assert "relay bump` marks the task `done`" not in prompt


def test_compose_prompt_report_tracks_layers_and_refs(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        mode="interactive",
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
    assert ("blackboard", "blackboard.md") in layers
    assert layers[("ticket_context", "email/payment-flow")].approx_tokens > 0


def test_compose_auto_mode_uses_auto_block(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="Auto task",
        workflow_name=None,
        contexts=[],
        mode="auto",
        owner=None,
        assignee=None,
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Auto mode" in prompt
    assert "Interactive mode" not in prompt


def test_compose_inline_step_instructions(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        title="T",
        workflow_name="code/with-review",
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    # Advance to step 2 (pr) — has inline instructions, no skill
    ticket.frontmatter["step"] = "2 (pr)"
    ticket.write(ref.path / "ticket.md")
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Open a PR. Push branch first." in prompt
    assert "Current step: pr" in prompt


def test_write_prompt_file(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg, title="X", workflow_name=None,
        contexts=[], mode="interactive", owner=None, assignee=None,
        watchers=[], status="active",
    )
    ref = list_tasks(cfg)[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    out = write_prompt_file(prompt, ref, dest_dir=tmp_path)
    assert out.exists()
    assert out.read_text() == prompt
    assert out.name.startswith("relay-x-")
