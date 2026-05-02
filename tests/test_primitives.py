from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay.blackboard import render_blackboard
from relay.lock import LockHeldError, TaskLock
from relay.logfile import append_log
from relay.slugify import slugify
from relay.ticket import Ticket, TicketError
from relay.workflow import Workflow, WorkflowError


# --- slugify ------------------------------------------------------------------


def test_slugify_basic() -> None:
    assert slugify("Fix retry logic") == "fix-retry-logic"


def test_slugify_truncates() -> None:
    out = slugify("a" * 100, max_len=10)
    assert out == "a" * 10


def test_slugify_empty() -> None:
    assert slugify("!!!") == "task"


# --- lock ---------------------------------------------------------------------


def test_lock_acquire_release(tmp_path: Path) -> None:
    lock = TaskLock(tmp_path)
    info = lock.acquire("claude1")
    assert lock.path.exists()
    assert lock.read().holder == "claude1"
    lock.release()
    assert not lock.path.exists()


def test_lock_held_raises(tmp_path: Path) -> None:
    lock = TaskLock(tmp_path)
    lock.acquire("claude1")
    with pytest.raises(LockHeldError):
        lock.acquire("claude2")


def test_lock_force_overrides(tmp_path: Path) -> None:
    lock = TaskLock(tmp_path)
    lock.acquire("claude1")
    info = lock.acquire("claude2", force=True)
    assert info.holder == "claude2"


def test_lock_context_manager_releases(tmp_path: Path) -> None:
    lock = TaskLock(tmp_path)
    with lock.held("claude1"):
        assert lock.path.exists()
    assert not lock.path.exists()


def test_lock_context_manager_releases_on_error(tmp_path: Path) -> None:
    lock = TaskLock(tmp_path)
    with pytest.raises(ValueError):
        with lock.held("claude1"):
            raise ValueError("boom")
    assert not lock.path.exists()


# --- ticket -------------------------------------------------------------------


TICKET_EXAMPLE = dedent(
    """
    ---
    title: Fix retry logic
    status: active
    mode: interactive
    owner: marc
    assignee: claude1
    workflow:
      name: code/with-review
      steps:
        - name: implement
          skill: infra/testing-conventions
        - name: pr
        - name: approve
          skill: process/approve
        - name: merge
    step: 1 (implement)
    contexts:
      - email/payment-flow
    ---

    ## Description

    Stripe webhook retries are silently failing.
    """
).lstrip()


def test_ticket_roundtrip(tmp_path: Path) -> None:
    t = Ticket.parse(TICKET_EXAMPLE)
    assert t.title == "Fix retry logic"
    assert t.mode == "interactive"
    assert t.contexts == ["email/payment-flow"]
    assert t.step_index() == 1
    assert t.current_step() == {"name": "implement", "skill": "infra/testing-conventions"}
    path = tmp_path / "ticket.md"
    t.write(path)
    again = Ticket.read(path)
    assert again.title == "Fix retry logic"
    assert again.workflow == t.workflow


def test_ticket_without_workflow() -> None:
    text = "---\ntitle: X\nstatus: draft\n---\n\n## Description\n\nfoo\n"
    t = Ticket.parse(text)
    assert t.workflow is None
    assert t.step_index() is None
    assert t.current_step() is None


def test_ticket_rejects_non_mapping() -> None:
    with pytest.raises(TicketError):
        Ticket.parse("---\n- a\n- b\n---\n\nbody\n")


def test_ticket_rejects_missing_frontmatter() -> None:
    with pytest.raises(TicketError):
        Ticket.parse("no frontmatter here\n")


# --- workflow -----------------------------------------------------------------


def test_workflow_step_assignee_role_token_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "wf.md"
    path.write_text(dedent(
        """
        ---
        name: wf
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: human
        ---
        """
    ).lstrip())
    wf = Workflow.load(path)
    assert wf.steps[0].assignee == "agent"
    frozen = wf.freeze()
    assert frozen["steps"][0] == {"name": "implement", "assignee": "agent"}
    assert frozen["steps"][1] == {"name": "review", "assignee": "human"}


def test_workflow_rejects_non_role_token_assignee(tmp_path: Path) -> None:
    path = tmp_path / "wf.md"
    path.write_text(dedent(
        """
        ---
        name: wf
        steps:
          - name: implement
            assignee: claude1
        ---
        """
    ).lstrip())
    with pytest.raises(WorkflowError, match="role token"):
        Workflow.load(path)


# --- log ----------------------------------------------------------------------


def test_append_log(tmp_path: Path) -> None:
    append_log(tmp_path, "agent:claude1", "advanced to step 2 (pr)")
    append_log(tmp_path, "human:marc", "approved")
    log = (tmp_path / "log.md").read_text()
    assert "[agent:claude1] advanced to step 2 (pr)" in log
    assert "[human:marc] approved" in log
    assert len(log.strip().splitlines()) == 2


# --- blackboard ---------------------------------------------------------------


def test_render_blackboard() -> None:
    out = render_blackboard("Fix retry logic")
    assert out  # Template body is rendered.
