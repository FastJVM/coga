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


@pytest.mark.parametrize("width", [80, 120])
def test_listing_keeps_names_and_schedules_visible_with_disabled_reasons(
    repo: Path, width: int,
) -> None:
    from io import StringIO
    from rich.console import Console
    from coga.commands.recurring import _print_templates_table

    _jobs(repo, "[jobs]\nbranch-sweep = true\nphone-home = true\ndream = false\nskill-update = true\n")
    _write(repo / "recurring/_skill-update/ticket.md", render_carrier("cursor: 1\n"))
    output = StringIO()
    _print_templates_table(
        Console(file=output, width=width, color_system=None),
        list_templates(load_config(repo), NOW, include_available=True), NOW,
    )
    text = output.getvalue()
    table = text.split("Recurring templates", 1)[1].split("dream:", 1)[0]
    for name in ("branch-sweep", "phone-home", "dream", "skill-update"):
        assert name in table
    assert "0 7 * * 1" in table
    assert "disabled" in table and "parked" in table
    assert "…" not in table
    # The note names an absolute tmp path, which Rich may wrap mid-word.
    flat = text.replace("\n", "")
    assert "jobs.toml" in flat and "_skill-update" in flat


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
    listed = {s.name: s for s in list_templates(cfg, NOW, include_available=True)}
    assert listed["dream"].selection == "parked"
    assert str(parked.parent) in listed["dream"].reason


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


def test_dangling_selection_never_restores_local_only_activation(repo: Path) -> None:
    _write(repo / "recurring/local-job/ticket.md", LOCAL_JOB)
    selection = repo / "recurring/jobs.toml"
    selection.symlink_to(repo / "missing-selection.toml")
    cfg = load_config(repo)
    sources = iter_template_sources(cfg)
    assert all(s.error and "symlink target is missing" in s.error for s in sources)
    scan = scan_due(cfg, now=NOW, force=True)
    assert scan.tasks == [] and scan.errors
    with pytest.raises(RecurringError, match="symlink target is missing"):
        create_named(cfg, "local-job", now=NOW)
    assert not (repo / "tasks/recurring/local-job").exists()


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


def test_unreadable_override_does_not_hide_healthy_jobs(repo, monkeypatch):
    _jobs(repo, "[jobs]\ndream = true\nphone-home = true\n")
    bad = repo / "recurring/dream"
    bad.mkdir()
    original = Path.iterdir
    def denied(path):
        if path == bad:
            raise PermissionError("unreadable parent")
        return original(path)
    monkeypatch.setattr(Path, "iterdir", denied)
    sources = _sources(repo)
    assert "unreadable parent" in sources["dream"].error
    assert sources["phone-home"].enabled


def test_direct_phone_home_refuses_malformed_carrier_before_writing(repo, monkeypatch):
    from coga_edge import phone_home

    seed = read_blackboard(packaged_template_path("recurring", "phone-home", "ticket.md"))
    parent = repo / "recurring/phone-home/ticket.md"
    _write(parent, render_carrier(seed).replace("{}", "schedule: invalid", 1))
    before = parent.read_bytes()
    monkeypatch.setattr(phone_home, "_admitted", lambda cfg: False)
    with pytest.raises(RecurringStateError, match="state-only carrier"):
        phone_home.run_phone_home(load_config(repo), [])
    assert parent.read_bytes() == before


@pytest.mark.parametrize("parked", [False, True])
def test_direct_phone_home_preserves_disabled_or_parked_state(repo, monkeypatch, parked):
    from coga_edge import phone_home

    _jobs(repo, "[jobs]\nphone-home = false\n")
    name = "_phone-home" if parked else "phone-home"
    parent = repo / "recurring" / name / "ticket.md"
    seed = read_blackboard(packaged_template_path("recurring", "phone-home", "ticket.md"))
    _write(parent, render_carrier(seed + "\nother: keep\n"))
    monkeypatch.setattr(phone_home, "_admitted", lambda cfg: False)
    for _ in range(2):
        assert phone_home.run_phone_home(load_config(repo), []) == 0
    assert phone_home._state(read_blackboard(parent))[0]["run"] == 2
    assert "other: keep" in read_blackboard(parent)
    if parked:
        assert not (repo / "recurring/phone-home/ticket.md").exists()


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


@pytest.mark.parametrize("feature", [False, True])
def test_first_package_period_publishes_carrier_and_ledger_together(git_repo, feature):
    from coga.recurring_runner import _sync_recurring_create
    from coga_edge import phone_home

    _jobs(git_repo.coga_os, "[jobs]\nphone-home = true\n")
    git_repo.git("add", "coga/recurring/jobs.toml")
    git_repo.git("commit", "-m", "select packaged phone-home")
    git_repo.git("push", "origin", "main")
    if feature:
        git_repo.checkout_branch("feature/test")
    cfg = load_config(git_repo.coga_os)
    outcome = create_named(cfg, "phone-home", now=NOW)
    failures = []
    assert _sync_recurring_create(cfg, "phone-home", outcome.ref, sync_failures=failures)
    assert not failures
    parent_rel = "coga/recurring/phone-home/ticket.md"
    assert git_repo.origin_tracks(parent_rel)
    assert git_repo.origin_tracks("coga/tasks/recurring/phone-home/.state-snapshot.json")
    assert git_repo.origin_tracks("coga/tasks/recurring/phone-home/ticket.py")
    assert "created recurring/phone-home" in git_repo.git("show", "main:coga/log.md", cwd=git_repo.origin)
    assert "period_state:" in git_repo.git("show", f"main:{parent_rel}", cwd=git_repo.origin)
    assert phone_home.run_phone_home(cfg, []) == 0
    assert phone_home._state(read_blackboard(git_repo.coga_os / "recurring/phone-home/ticket.md"))[0]["run"] == 1


def test_package_create_adopts_a_racing_parent_without_resetting_state(git_repo, monkeypatch):
    from coga import git
    from coga.recurring_runner import _sync_recurring_create

    _jobs(git_repo.coga_os, "[jobs]\nphone-home = true\n")
    git_repo.git("add", "coga/recurring/jobs.toml")
    git_repo.git("commit", "-m", "select packaged phone-home")
    git_repo.git("push", "origin", "main")
    cfg = load_config(git_repo.coga_os)
    outcome = create_named(cfg, "phone-home", now=NOW)
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    peer = parent.read_text(encoding="utf-8").replace('"run":0', '"run":9') + "\nother: peer\n"
    original = git._push
    raced = False
    def create_parent(root, remote, refspec):
        nonlocal raced
        if not raced:
            raced = True
            git_repo.push_competing_commit("coga/recurring/phone-home/ticket.md", peer)
        return original(root, remote, refspec)
    monkeypatch.setattr(git, "_push", create_parent)
    failures = []
    assert _sync_recurring_create(cfg, "phone-home", outcome.ref, sync_failures=failures)
    assert raced and not failures
    assert parent.read_text(encoding="utf-8") == peer
    assert git_repo.git("show", "main:coga/recurring/phone-home/ticket.md", cwd=git_repo.origin) == peer


def test_stale_package_create_adopts_the_existing_period_and_carrier(git_repo):
    from coga.recurring_runner import _sync_recurring_create

    _jobs(git_repo.coga_os, "[jobs]\nphone-home = true\n")
    git_repo.git("add", "coga/recurring/jobs.toml")
    git_repo.git("commit", "-m", "select packaged phone-home")
    git_repo.git("push", "origin", "main")
    start = git_repo.git("rev-parse", "HEAD").strip()
    cfg = load_config(git_repo.coga_os)
    first = create_named(cfg, "phone-home", now=NOW)
    assert _sync_recurring_create(cfg, "phone-home", first.ref)
    expected_task = first.ref.ticket_path.read_bytes()
    expected_snapshot = (first.ref.path / ".state-snapshot.json").read_bytes()
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    expected_parent = parent.read_bytes()
    git_repo.git("reset", "--hard", start)
    stale = create_named(cfg, "phone-home", now=NOW)
    assert stale.ref.ticket_path.read_bytes() != expected_task
    assert not _sync_recurring_create(cfg, "phone-home", stale.ref)
    assert stale.ref.ticket_path.read_bytes() == expected_task
    assert (stale.ref.path / ".state-snapshot.json").read_bytes() == expected_snapshot
    assert parent.read_bytes() == expected_parent
