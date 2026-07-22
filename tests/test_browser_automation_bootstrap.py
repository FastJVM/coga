from __future__ import annotations

from pathlib import Path

from coga.ticket import Ticket


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "src" / "coga" / "resources" / "templates" / "coga"
LAUNCHER = TEMPLATES / "bootstrap" / "browser-automation" / "ticket.md"
ROUTER_SKILL = (
    TEMPLATES
    / "bootstrap"
    / "skills"
    / "browser"
    / "build-automation"
    / "SKILL.md"
)


def test_browser_automation_launcher_is_stateless_and_skill_backed() -> None:
    ticket = Ticket.read(LAUNCHER)

    assert set(ticket.frontmatter) == {"title", "assignee", "contexts", "skills"}
    assert ticket.contexts == ["browser/api-first"]
    assert ticket.skills == ["browser/build-automation"]
    assert ticket.status == ""
    assert ticket.workflow is None
    assert ticket.step is None
    assert "coga launch bootstrap/browser-automation" in ticket.body
    assert "launching it does not\ncreate a generic browser task" in ticket.body


def test_browser_router_methodology_moved_from_workflow_to_bundled_skill() -> None:
    text = ROUTER_SKILL.read_text()

    assert "## 1. Understand the task" in text
    assert "## 2. Choose the approach" in text
    assert "## 3. Choose the workflow" in text
    assert "## 4. Create and launch the concrete ticket" in text
    assert "browser/api-first" in text
    assert "browser/dom-backed" in text
    assert "browser/playwright" in text
    assert "all-agent workflow" in text
    assert "human or owner gate" in text
    assert "the human performs it" in text
    assert "autonomy" not in text.lower()
    assert not (
        REPO_ROOT / "coga" / "workflows" / "browser" / "build-automation.md"
    ).exists()
    assert not (
        TEMPLATES / "workflows" / "browser" / "build-automation.md"
    ).exists()


def test_browser_capability_remains_without_seeded_task_or_audit_line() -> None:
    assert not (TEMPLATES / "tasks" / "browser-automation.md").exists()
    assert "[browser-automation]" not in (TEMPLATES / "log.md").read_text()
    assert (
        TEMPLATES / "contexts" / "browser" / "api-first" / "SKILL.md"
    ).is_file()
    assert (
        TEMPLATES / "contexts" / "browser" / "dom-backed" / "SKILL.md"
    ).is_file()
    assert (
        TEMPLATES / "bootstrap" / "skills" / "browser" / "playwright" / "SKILL.md"
    ).is_file()
    packaged_workflow = TEMPLATES / "workflows" / "draft-for-human.md"
    live_workflow = REPO_ROOT / "coga" / "workflows" / "draft-for-human.md"
    assert packaged_workflow.is_file()
    assert live_workflow.read_bytes() == packaged_workflow.read_bytes()
    assert not (TEMPLATES / "workflows" / "autonomy").exists()
    assert not (REPO_ROOT / "coga" / "workflows" / "autonomy").exists()
    assert not (TEMPLATES / "contexts" / "autonomy").exists()
    assert not (REPO_ROOT / "coga" / "contexts" / "autonomy").exists()


def test_reference_documents_browser_router_and_runner_roles() -> None:
    # The README is the marketing hook and delegates command-level detail to
    # docs/; the browser launcher is documented in the command reference.
    text = (REPO_ROOT / "docs" / "reference.md").read_text()

    assert "coga launch bootstrap/browser-automation" in text
    assert "`browser/build-automation` is the orchestration skill" in text
    assert "`browser/playwright` is the lower-level execution skill" in text
