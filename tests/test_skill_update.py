from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.tasks import list_tasks

SKILL_UPDATE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coga"
    / "resources"
    / "templates"
    / "coga-os"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "skill-update"
)


def _load_skill_update_module():
    spec = importlib.util.spec_from_file_location(
        "skill_update_skill", SKILL_UPDATE / "run.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


skill_update = _load_skill_update_module()

SkillUpdate = skill_update.SkillUpdate
classify_status = skill_update.classify_status
parse_results = skill_update.parse_results
render_blackboard_report = skill_update.render_blackboard_report
build_update_command = skill_update.build_update_command
has_followups = skill_update.has_followups
GROUP_UPDATED = skill_update.GROUP_UPDATED
GROUP_FOLLOWUP = skill_update.GROUP_FOLLOWUP
GROUP_SKIPPED = skill_update.GROUP_SKIPPED


def _result(name: str, status: str, *, source_type: str = "url", changed: bool = False):
    return SkillUpdate(
        name=name,
        source_type=source_type,
        status=status,
        message=f"{status} message",
        changed=changed,
    )


def test_classify_status_buckets_known_statuses() -> None:
    assert classify_status("updated") == GROUP_UPDATED
    assert classify_status("delegated") == GROUP_UPDATED
    assert classify_status("skipped-bundled") == GROUP_SKIPPED
    assert classify_status("unchanged") == GROUP_SKIPPED
    assert classify_status("skipped-local-adaptation") == GROUP_FOLLOWUP
    assert classify_status("failed") == GROUP_FOLLOWUP


def test_classify_status_routes_conflict_and_unknown_to_followup() -> None:
    # The sibling ticket's future `conflict` status — and any status the
    # updater grows that this worker has not enumerated — must surface as
    # follow-up, never be silently dropped under a benign heading.
    assert classify_status("conflict") == GROUP_FOLLOWUP
    assert classify_status("some-brand-new-status") == GROUP_FOLLOWUP


def test_has_followups_detects_human_needed_statuses() -> None:
    assert has_followups([_result("a/clean", "updated")]) is False
    assert (
        has_followups(
            [
                _result("a/clean", "updated"),
                _result("b/adapted", "skipped-local-adaptation"),
            ]
        )
        is True
    )


def test_build_update_command_toggles_pr() -> None:
    with_pr = build_update_command(pr=True, pr_title="T")
    assert with_pr[-4:] == ["--json", "--pr", "--pr-title", "T"]
    no_pr = build_update_command(pr=False, pr_title="T")
    assert "--pr" not in no_pr
    assert no_pr[-1] == "--json"


def test_parse_results_reads_json_payload() -> None:
    payload = {
        "results": [
            {
                "name": "tools/example",
                "source_type": "url",
                "status": "updated",
                "message": "updated from URL source",
                "changed": True,
            },
            "not-a-dict",
        ]
    }
    results = parse_results(payload)
    assert len(results) == 1
    assert results[0].name == "tools/example"
    assert results[0].changed is True


def test_render_buckets_conflict_separately_from_skipped_local_adaptation() -> None:
    results = [
        _result("a/clean", "updated", changed=True),
        _result("b/adapted", "skipped-local-adaptation"),
        _result("c/conflicted", "conflict"),
        _result("d/bundled", "skipped-bundled", source_type="bundled"),
    ]
    report = render_blackboard_report(
        results,
        generated_at="2026-06-09T00:00:00+00:00",
        command=["coga", "skill", "update", "--all", "--pr", "--json"],
        pr_url="https://example.com/pr/1",
        pr_requested=True,
        task_slug="skill-update",
    )

    assert "## Skill Update" in report
    assert "Task: `skill-update`" in report
    assert "Result: 4 skill(s): 1 updated, 2 need follow-up, 1 skipped." in report
    assert "PR: https://example.com/pr/1" in report
    # The two follow-up statuses keep their own distinct lines under the
    # follow-up heading — `conflict` is never merged with
    # `skipped-local-adaptation`.
    assert "### Needs follow-up" in report
    assert "`b/adapted`: `skipped-local-adaptation`" in report
    assert "`c/conflicted`: `conflict`" in report
    assert "### Updated" in report
    assert "`a/clean`: `updated`" in report
    assert "### Skipped" in report
    assert "`d/bundled`: `skipped-bundled`" in report


def test_render_reports_no_pr_when_no_updates() -> None:
    report = render_blackboard_report(
        [_result("d/bundled", "skipped-bundled", source_type="bundled")],
        generated_at="2026-06-09T00:00:00+00:00",
        command=["coga", "skill", "update", "--all", "--pr", "--json"],
        pr_url=None,
        pr_requested=True,
        task_slug="skill-update",
    )
    assert "PR: none opened — no clean skill updates to commit." in report


def test_render_handles_empty_results() -> None:
    report = render_blackboard_report(
        [],
        generated_at="2026-06-09T00:00:00+00:00",
        command=["coga", "skill", "update", "--all", "--pr", "--json"],
        pr_url=None,
        pr_requested=True,
        task_slug="skill-update",
    )
    assert "Result: no installed skills to update." in report
    assert "PR: none opened" in report


def test_skill_update_skill_declares_contract() -> None:
    text = (SKILL_UPDATE / "SKILL.md").read_text()
    norm = " ".join(text.split())

    assert "name: bootstrap/skill-update" in text
    assert "## Known Skill Contract" in text
    assert "- Purpose: update clean imported skills" in text
    assert "- Action: `pr-required`" in text
    assert "coga skill update --all --pr" in text
    assert "`coga/skill-update` branch" in norm
    assert "never the caller's branch" in norm
    assert "Bundled (package-backed) skills are not updated here" in norm
    assert "- Output: append `## Skill Update`" in text
    assert "COGA_TASK_BLACKBOARD" in text
    assert "--blackboard" not in text


def test_skill_update_ships_as_a_recurring_template() -> None:
    """The skill updater is a standalone recurring task, not a Dream phase.
    The packaged template wires a weekly `autonomy: auto` ticket to the
    `skill-update/run` workflow, whose one step runs `bootstrap/skill-update`;
    that script-backed step is what makes it run as a script (deduced at
    launch), so no `mode: script` is declared anymore."""
    coga_os = SKILL_UPDATE.parents[3]
    ticket = (coga_os / "recurring" / "skill-update" / "ticket.md").read_text()
    workflow = (coga_os / "workflows" / "skill-update" / "run.md").read_text()

    assert ticket.startswith("---\n")
    assert "schedule:" in ticket
    assert 'title: "Skill update"' in ticket
    assert "autonomy: auto" in ticket
    assert "workflow: skill-update/run" in ticket
    assert "coga skill update --all --pr" in ticket

    assert "name: skill-update/run" in workflow
    assert "- bootstrap/skill-update" in workflow


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga-os"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    (coga_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(coga_os)
    return coga_os


def test_skill_update_runs_as_script_skill_and_reports_no_op(repo: Path) -> None:
    # No imported skills under `skills/`: `coga skill update --all --pr` finds
    # nothing clean to update, so it commits nothing and opens no PR (never
    # touching git), and the skill reports a clean no-op on the task
    # blackboard. Install into the bundled bootstrap root rather than the
    # project-local `skills/` tree so the skill being tested does not look
    # like an imported, gh-backed local skill.
    shutil.copytree(
        SKILL_UPDATE, repo / "bootstrap" / "skills" / "bootstrap" / "skill-update"
    )
    _write(
        repo / "workflows" / "skill-update" / "run.md",
        """
        ---
        name: skill-update/run
        description: script worker.
        steps:
          - name: update
            skills:
              - bootstrap/skill-update
        ---
        """,
    )
    cfg = load_config(repo)
    create_task(
        cfg=cfg,
        title="Skill Update",
        workflow_name="skill-update/run",
        contexts=[],
        autonomy="interactive",
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    result = CliRunner().invoke(app, ["launch", "skill-update"])

    assert result.exit_code == 0, result.output
    ref = list_tasks(cfg)[0]
    # Single-file format: a script worker's COGA_TASK_BLACKBOARD is its own
    # ticket.md, so its report lands in that ticket's blackboard region.
    from coga.taskfile import read_blackboard

    blackboard = read_blackboard(ref.ticket_path)
    assert "## Skill Update" in blackboard
    assert "Task: `skill-update`" in blackboard
    assert "PR: none opened" in blackboard


def test_skill_update_followup_without_pr_exits_nonzero_and_keeps_report(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blackboard = repo / "tasks" / "skill-update" / "blackboard.md"
    blackboard.parent.mkdir(parents=True)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))
    monkeypatch.setenv("COGA_TASK_SLUG", "skill-update")

    def fake_run_update_json(*, cwd: Path | None, pr: bool, pr_title: str):
        assert pr is True
        return (
            {
                "results": [
                    {
                        "name": "b/adapted",
                        "source_type": "url",
                        "status": "skipped-local-adaptation",
                        "message": "local changes detected",
                        "changed": False,
                    }
                ],
                "pr_url": "",
            },
            ["coga", "skill", "update", "--all", "--pr", "--json"],
        )

    monkeypatch.setattr(skill_update, "run_update_json", fake_run_update_json)

    assert skill_update.main([]) == 1
    text = blackboard.read_text()
    assert "## Skill Update" in text
    assert "Task: `skill-update`" in text
    assert "### Needs follow-up" in text
    assert "`b/adapted`: `skipped-local-adaptation`" in text
    assert "PR: none opened" in text
