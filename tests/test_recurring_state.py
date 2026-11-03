"""Recurring definition catalog, selection, and repo state carriers.

Covers `coga.recurring_state` (carrier shape, classification, first-use
initialization) and the effective catalog in `coga.recurring`
(`iter_template_sources`/`resolve_template_source`, `jobs.toml` selection)
through the real scan/create/list/validate seams.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from coga.config import load_config
from coga.paths import LocalOverrideError, packaged_template_path, resolve_skill_path
from coga.recurring import (
    RecurringError,
    create_named,
    iter_template_sources,
    list_templates,
    resolve_template_source,
    scan_due,
)
from coga.recurring_state import (
    CARRIER,
    INCOMPLETE,
    STATE_ONLY,
    RecurringStateError,
    ensure_parent_state,
    inspect_parent_dir,
    parent_state_path,
    render_carrier,
)
from coga.retire_worklist import worklist_for_period_task
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import TaskNotFoundError, resolve_bootstrap
from coga.validate import _check_recurring_templates


NOW = datetime(2026, 4, 22, 10, 0, 0)
BUNDLED = (
    "address-pr-comments", "autoclose-merged", "blocker-reminders", "branch-sweep",
    "dream", "phone-home", "resolve-conflicts", "skill-update", "trim-log",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


LOCAL_JOB = """
---
schedule: "0 9 * * 1"
title: "Local job"
---

## Description

Do the local thing.

<!-- coga:blackboard -->

cursor: 1
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    company = tmp_path / "coga"
    _write(company / "coga.toml", 'version = 1\n[agents.claude]\ncli = "claude"\nfile = "CLAUDE.md"\n')
    _write(company / "coga.local.toml", 'user = "marc"\n')
    return company


def _jobs(repo: Path, body: str) -> None:
    _write(repo / "recurring" / "jobs.toml", body)


def _sources(repo: Path) -> dict:
    return {s.name: s for s in iter_template_sources(load_config(repo))}


def test_without_selection_only_local_definitions_run(repo: Path) -> None:
    """Pre-upgrade repos keep local-only activation; bundled jobs stay off."""
    _write(repo / "recurring" / "local-job" / "ticket.md", LOCAL_JOB)
    sources = _sources(repo)
    assert sources["local-job"].enabled and sources["local-job"].origin == "local"
    for name in BUNDLED:
        assert sources[name].selection == "unselected"
        assert sources[name].origin == "package"
        assert not sources[name].enabled
    scan = scan_due(load_config(repo), now=NOW)
    assert [t.template for t in scan.tasks] == ["local-job"]
    assert scan.errors == []
    # A read-only scan of bundled jobs creates no state.
    assert sorted(p.name for p in (repo / "recurring").iterdir()) == ["local-job"]
    # Status views list the configured job; `recurring list` offers the rest.
    assert [s.name for s in list_templates(load_config(repo), NOW)] == ["local-job"]
    offered = list_templates(load_config(repo), NOW, include_available=True)
    assert {s.name for s in offered} == {"local-job", *BUNDLED}


def test_selected_bundled_job_creates_a_carrier_once_from_the_seed(repo: Path) -> None:
    _jobs(repo, "[jobs]\ndream = true\n")
    cfg = load_config(repo)
    source = resolve_template_source(cfg, "dream")
    assert source.enabled and source.origin == "package"
    assert source.definition_dir == packaged_template_path("recurring", "dream")
    parent = repo / "recurring" / "dream" / "ticket.md"
    assert not parent.exists()

    outcome = create_named(cfg, "dream")
    assert outcome.created
    seed = read_blackboard(packaged_template_path("recurring", "dream", "ticket.md"))
    assert parent.read_text(encoding="utf-8") == render_carrier(seed)
    assert inspect_parent_dir(parent.parent).kind == CARRIER
    # The period froze the packaged body; the carrier holds no instructions.
    assert "Coga's generic ticket cleanup pass" not in parent.read_text(encoding="utf-8")

    # Existing state, even an intentionally empty region, is never reseeded.
    replace_blackboard(parent, "\n")
    assert ensure_parent_state(
        cfg, "dream", seed_ticket=packaged_template_path("recurring", "dream", "ticket.md")
    ) == parent
    assert read_blackboard(parent) == "\n"
    # Still package-backed: a carrier never shadows the definition.
    assert resolve_template_source(load_config(repo), "dream").origin == "package"


def test_local_override_wins_and_owns_its_state(repo: Path) -> None:
    _jobs(repo, "[jobs]\ndream = true\n")
    _write(repo / "recurring" / "dream" / "ticket.md", LOCAL_JOB)
    source = resolve_template_source(load_config(repo), "dream")
    assert source.enabled and source.origin == "local"
    template = source.load(now=NOW)
    assert template.state_path == template.ticket_path == repo / "recurring/dream/ticket.md"


def test_false_disables_local_and_bundled_even_when_forced(repo: Path) -> None:
    _write(repo / "recurring" / "local-job" / "ticket.md", LOCAL_JOB)
    _jobs(repo, "[jobs]\nlocal-job = false\ndream = false\n")
    cfg = load_config(repo)
    for name in ("local-job", "dream"):
        assert resolve_template_source(cfg, name).selection == "disabled"
        with pytest.raises(RecurringError, match=r"jobs\.toml"):
            create_named(cfg, name)
    assert scan_due(cfg, now=NOW, force=True).tasks == []


def test_a_newly_bundled_job_needs_explicit_selection(repo: Path) -> None:
    _jobs(repo, "[jobs]\ndream = true\n")
    cfg = load_config(repo)
    with pytest.raises(RecurringError, match="not selected"):
        create_named(cfg, "skill-update")


def test_parked_jobs_stay_parked_and_keep_their_state(repo: Path) -> None:
    _jobs(repo, "[jobs]\ndream = true\n")
    parked = repo / "recurring" / "_dream" / "ticket.md"
    _write(parked, render_carrier("\nsaved: yes\n"))
    cfg = load_config(repo)
    source = resolve_template_source(cfg, "dream")
    assert source.selection == "parked" and source.origin == "package"
    with pytest.raises(RecurringError, match="parked"):
        create_named(cfg, "dream")
    assert scan_due(cfg, now=NOW, force=True).tasks == []
    assert parent_state_path(cfg, "dream") == parked


def test_ambiguous_active_and_parked_configurations_are_errors(repo: Path) -> None:
    _write(repo / "recurring" / "dream" / "ticket.md", LOCAL_JOB)
    _write(repo / "recurring" / "_dream" / "ticket.md", LOCAL_JOB)
    _write(repo / "recurring" / "phone-home" / "ticket.md", render_carrier("\n"))
    _write(repo / "recurring" / "_phone-home" / "ticket.md", render_carrier("\n"))
    sources = _sources(repo)
    assert "parked" in sources["dream"].error
    assert "reconcile their cursors" in sources["phone-home"].error
    with pytest.raises(RecurringStateError):
        parent_state_path(load_config(repo), "phone-home")


def test_carrier_shape_and_incomplete_forks_fail_visibly(repo: Path) -> None:
    _jobs(repo, "[jobs]\nphone-home = true\nbranch-sweep = true\ndream = true\n")
    # A script beside a carrier is an incomplete fork, never inherited.
    _write(repo / "recurring" / "phone-home" / "ticket.md", render_carrier("\nperiod_state: {}\n"))
    _write(repo / "recurring" / "phone-home" / "ticket.py", "raise SystemExit(0)\n")
    # A marked file carrying definition fields is malformed.
    _write(
        repo / "recurring" / "branch-sweep" / "ticket.md",
        '---\nschedule: "0 7 * * *"\n---\n<!-- coga:recurring-state -->\n\n<!-- coga:blackboard -->\n',
    )
    # Recognized runtime state beside a carrier is fine.
    _write(repo / "recurring" / "dream" / "ticket.md", render_carrier("\n"))
    _write(repo / "recurring" / "dream" / "retires.md", "# Retire follow-ups\n")
    sources = _sources(repo)
    assert "incomplete fork" in sources["phone-home"].error
    assert "state-only carrier" in sources["branch-sweep"].error
    assert sources["dream"].enabled and sources["dream"].origin == "package"
    issues = [i for i in _check_recurring_templates(load_config(repo)) if i.kind == "bad-recurring-template"]
    assert {i.task for i in issues} == {"recurring/phone-home", "recurring/branch-sweep"}
    with pytest.raises(RecurringError, match="incomplete fork"):
        create_named(load_config(repo), "phone-home")


def test_unmarked_ticket_without_schedule_is_not_a_quiet_fallback(repo: Path) -> None:
    _jobs(repo, "[jobs]\ndream = true\n")
    _write(repo / "recurring" / "dream" / "ticket.md", "---\n{}\n---\n\n<!-- coga:blackboard -->\n")
    source = resolve_template_source(load_config(repo), "dream")
    assert source.origin == "local"
    with pytest.raises(RecurringError, match="schedule"):
        create_named(load_config(repo), "dream")


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("[jobs\n", "not valid TOML"),
        ("[jobs]\ndream = 1\n", "true or false"),
        ("[jobs]\n_dream = true\n", "not a recurring job name"),
        ("schedule = 1\n[jobs]\n", "unknown top-level keys"),
        ("[jobs]\nmissing = true\n", "neither a local"),
    ],
)
def test_selection_errors_are_visible(repo: Path, body: str, message: str) -> None:
    _jobs(repo, body)
    errors = [s.error for s in iter_template_sources(load_config(repo)) if s.error]
    assert errors and all(message in e for e in errors), errors
    scan = scan_due(load_config(repo), now=NOW)
    assert scan.tasks == [] and scan.errors


def test_worklist_only_directory_resolves_the_selected_bundled_parent(repo: Path) -> None:
    _jobs(repo, "[jobs]\nautoclose-merged = true\n")
    worklist = repo / "recurring" / "autoclose-merged" / "retires.md"
    _write(worklist, "# Retire follow-ups\n")
    cfg = load_config(repo)
    assert inspect_parent_dir(worklist.parent).kind == STATE_ONLY
    period = repo / "tasks" / "recurring" / "autoclose-merged" / "ticket.md"
    _write(period, "---\ntitle: x\n---\n")
    assert worklist_for_period_task(cfg, period) == worklist
    _jobs(repo, "[jobs]\nautoclose-merged = false\n")
    assert worklist_for_period_task(load_config(repo), period) is None


def test_cache_only_directory_does_not_shadow_the_package(repo: Path) -> None:
    _jobs(repo, "[jobs]\nphone-home = true\n")
    cache = repo / "recurring" / "phone-home" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "ticket.cpython-312.pyc").write_bytes(b"")
    source = resolve_template_source(load_config(repo), "phone-home")
    assert source.enabled and source.origin == "package"


def test_invalid_local_skill_and_bootstrap_overrides_never_select_stock(repo: Path) -> None:
    cfg = load_config(repo)
    (repo / "skills" / "direct" / "body" / "SKILL.md").mkdir(parents=True)
    with pytest.raises(LocalOverrideError):
        resolve_skill_path(cfg, "direct/body")
    _write(repo / "skills" / "code" / "implement" / "seed_local_config.py", "")
    with pytest.raises(LocalOverrideError, match="no SKILL.md"):
        resolve_skill_path(cfg, "code/implement")
    (repo / "bootstrap" / "retire").mkdir(parents=True)
    (repo / "bootstrap" / "retire" / "ticket.md").symlink_to(repo / "missing.md")
    with pytest.raises(TaskNotFoundError, match="link to no regular file"):
        resolve_bootstrap(cfg, "bootstrap/retire")
    # Namespace directories holding only nested refs are not overrides.
    (repo / "skills" / "coga" / "extra").mkdir(parents=True)
    assert resolve_skill_path(cfg, "coga/show") == packaged_template_path(
        "bootstrap", "skills", "coga", "show", "SKILL.md"
    )
