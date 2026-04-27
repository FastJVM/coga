from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.commands.create import scaffold_task
from relay.compose import compose_prompt, write_prompt_file
from relay.config import load_config
from relay.tasks import list_tasks, read_ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "relay-os"
    project = tmp_path / "projects" / "email-tool"
    project.mkdir(parents=True)

    _write(
        company / "relay.toml",
        f"""
        version = 1
        [projects.email-tool]
        type = "local"
        default_status = "ready"
        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        [assignees.marc]
        agents = {{"claude1" = "claude"}}
        """,
    )
    _write(
        company / "relay.local.toml",
        f'user = "marc"\n[paths]\nemail-tool = "{project}"\n',
    )
    _write(company / "rules.md", "Never commit secrets.\n")
    _write(
        company / "workflows" / "code" / "with-review.md",
        """
        ---
        name: code/with-review
        description: Standard.
        steps:
          - name: implement
            skill: infra/testing-conventions
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
    _write(project / "relay-os" / "context.md", "Email tool is YC-backed.\n")
    return company


def test_compose_includes_all_sections(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        project="email-tool",
        title="Fix retry logic",
        workflow_name="code/with-review",
        contexts=["email/payment-flow"],
        mode="interactive",
        owner="marc",
        assignee="claude1",
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg, "email-tool")[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)

    # Header
    assert "Relay task — email-tool/001-fix-retry-logic" in prompt
    # Base prompt
    assert "You are an agent working on a ticket inside Relay" in prompt
    # Interactive prompt
    assert "Interactive mode" in prompt
    # Rules
    assert "Never commit secrets" in prompt
    # Project context
    assert "Email tool is YC-backed" in prompt
    # Ticket context
    assert "Stripe retries on 429" in prompt
    # Step skill
    assert "Run tests with pytest" in prompt
    assert "Current step: implement" in prompt
    # Blackboard present
    assert "Blackboard" in prompt


def test_compose_auto_mode_uses_auto_block(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        project="email-tool",
        title="Auto task",
        workflow_name=None,
        contexts=[],
        mode="auto",
        owner=None,
        assignee=None,
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg, "email-tool")[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    assert "Auto mode" in prompt
    assert "Interactive mode" not in prompt


def test_compose_inline_step_instructions(repo: Path) -> None:
    cfg = load_config(repo)
    scaffold_task(
        cfg=cfg,
        project="email-tool",
        title="T",
        workflow_name="code/with-review",
        contexts=[],
        mode="interactive",
        owner=None,
        assignee=None,
        watchers=[],
        status="active",
    )
    ref = list_tasks(cfg, "email-tool")[0]
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
        cfg=cfg, project="email-tool", title="X", workflow_name=None,
        contexts=[], mode="interactive", owner=None, assignee=None,
        watchers=[], status="active",
    )
    ref = list_tasks(cfg, "email-tool")[0]
    ticket = read_ticket(ref)
    prompt = compose_prompt(cfg, ref, ticket)
    out = write_prompt_file(prompt, ref, dest_dir=tmp_path)
    assert out.exists()
    assert out.read_text() == prompt
    assert out.name.startswith("relay-001-x-")
