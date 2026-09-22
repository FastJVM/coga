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

    assert set(ticket.frontmatter) == {"title", "agent", "contexts", "skills"}
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
    # Routing is by real workflow handoff shape, not by the removed tier names.
    assert "human or owner gate" in text
    assert "autonomy/" not in text.lower()
    assert not (
        REPO_ROOT / "coga" / "workflows" / "browser" / "build-automation.md"
    ).exists()
    assert not (
        TEMPLATES / "workflows" / "browser" / "build-automation.md"
    ).exists()


def test_browser_capability_remains_without_seeded_task_or_audit_line() -> None:
    assert not (TEMPLATES / "tasks" / "browser-automation.md").exists()
    assert "[browser-automation]" not in (TEMPLATES / "log.md").read_text()
    # The bundled launcher attaches `browser/api-first`, so both browser
    # contexts must live where `resolve_context_path` falls back to —
    # `bootstrap/contexts/` — not in the init-seeded `contexts/` tree.
    assert (
        TEMPLATES / "bootstrap" / "contexts" / "browser" / "api-first" / "SKILL.md"
    ).is_file()
    assert (
        TEMPLATES / "bootstrap" / "contexts" / "browser" / "dom-backed" / "SKILL.md"
    ).is_file()
    assert not (TEMPLATES / "contexts" / "browser").exists()
    assert (
        TEMPLATES / "bootstrap" / "skills" / "browser" / "playwright" / "SKILL.md"
    ).is_file()


def test_autonomy_triage_apparatus_is_gone_from_both_trees() -> None:
    """The router used to send tickets at `autonomy/*` tier workflows. Those
    and the `autonomy/triage` context are removed from the live and packaged
    trees alike; `draft-for-human` is the one survivor of the namespace.
    Packaging (wheel inclusion, live/packaged parity) is owned by
    `tests/test_packaging.py`.
    """
    for tree in (TEMPLATES, REPO_ROOT / "coga"):
        assert not (tree / "workflows" / "autonomy").exists()
        assert not (tree / "contexts" / "autonomy").exists()
        assert (tree / "workflows" / "draft-for-human.md").is_file()


def test_command_guide_links_to_browser_router_and_runner_reference() -> None:
    # The docs index points at the coga/cli command index and the browser
    # topics; the bundled launcher itself names the router skill and the
    # separate runner, so the command index does not restate them.
    guide = (REPO_ROOT / "docs" / "README.md").read_text()
    reference = REPO_ROOT / "docs" / "contexts" / "coga" / "cli" / "SKILL.md"
    packaged = TEMPLATES / "bootstrap" / "contexts" / "coga" / "cli" / "SKILL.md"

    assert "(contexts/coga/cli/SKILL.md)" in guide
    assert "(contexts/browser/api-first/SKILL.md)" in guide
    assert "(contexts/browser/dom-backed/SKILL.md)" in guide
    assert reference.read_bytes() == packaged.read_bytes()
    launcher = " ".join(LAUNCHER.read_text().split())
    assert "coga launch bootstrap/browser-automation" in launcher
    assert "`browser/build-automation` skill" in launcher
    assert "`browser/playwright` is the separate lower-level browser runner" in launcher
