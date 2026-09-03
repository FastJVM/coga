from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from coga import skill_update
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
    / "coga"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "skill-update"
)
SkillUpdate = skill_update.SkillUpdate
classify_status = skill_update.classify_status
parse_results = skill_update.parse_results
render_blackboard_report = skill_update.render_blackboard_report
render_failure_report = skill_update.render_failure_report
build_update_command = skill_update.build_update_command
has_followups = skill_update.has_followups
render_result_line = skill_update.render_result_line
SkillUpdateReport = skill_update.SkillUpdateReport
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


def test_render_result_line_is_the_reports_own_result_sentence() -> None:
    # One renderer, so a caller summarizing a run states the same counts the
    # blackboard report does instead of parsing `Result:` back out of it.
    results = [
        _result("a/updated", "updated", changed=True),
        _result("b/adapted", "skipped-local-adaptation"),
        _result("c/bundled", "skipped-bundled", source_type="bundled"),
    ]
    line = render_result_line(results)
    assert line == "3 skill(s): 1 updated, 1 need follow-up, 1 skipped."

    report = render_blackboard_report(
        results,
        generated_at="2026-06-09T00:00:00+00:00",
        command=["coga", "skill", "update", "--all", "--pr", "--json"],
        pr_url=None,
        pr_requested=True,
        task_slug="skill-update",
    )
    assert f"Result: {line}" in report


def test_render_result_line_handles_empty_results() -> None:
    assert render_result_line([]) == "no installed skills to update."


def test_recipe_hands_back_the_results_it_already_holds(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blackboard = repo / "tasks" / "skill-update" / "blackboard.md"
    blackboard.parent.mkdir(parents=True)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))
    monkeypatch.setenv("COGA_TASK_SLUG", "skill-update")

    def fake_run_update_json(*, cwd: Path | None, pr: bool, pr_title: str):
        return (
            {
                "results": [
                    {
                        "name": "a/updated",
                        "source_type": "url",
                        "status": "updated",
                        "message": "updated to v2",
                        "changed": True,
                    }
                ],
                "pr_url": "https://github.com/o/r/pull/7",
            },
            ["coga", "skill", "update", "--all", "--pr", "--json"],
        )

    monkeypatch.setattr(skill_update, "run_update_json", fake_run_update_json)

    report = SkillUpdateReport()
    assert skill_update.run_skill_update_recipe(load_config(repo), [], result=report) == 0

    assert [item.name for item in report.results] == ["a/updated"]
    assert report.pr_url == "https://github.com/o/r/pull/7"
    assert report.pr_requested is True
    assert report.command == build_update_command(
        pr=True, pr_title="Update Coga-managed skills"
    )
    assert report.report == blackboard.read_text()
    assert render_result_line(report.results) == "1 skill(s): 1 updated, 0 need follow-up, 0 skipped."


def test_recipe_result_is_populated_on_the_followup_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Exit 1 is the outcome most worth naming, so the collected detail has to
    # survive it.
    blackboard = repo / "tasks" / "skill-update" / "blackboard.md"
    blackboard.parent.mkdir(parents=True)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))
    monkeypatch.setenv("COGA_TASK_SLUG", "skill-update")

    def fake_run_update_json(*, cwd: Path | None, pr: bool, pr_title: str):
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

    report = SkillUpdateReport()
    assert skill_update.run_skill_update_recipe(load_config(repo), [], result=report) == 1

    assert [item.name for item in report.results] == ["b/adapted"]
    assert report.pr_url is None
    assert "### Needs follow-up" in report.report


def test_recipe_result_names_the_command_a_failed_run_attempted(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `run_update_json` raises only *after* the subprocess ran — a non-zero
    # exit, or output that is not valid JSON. So the exit-2 path is a run that
    # happened and failed, and it has to name the command it attempted rather
    # than look like one that never started.
    def boom(*, cwd: Path | None, pr: bool, pr_title: str):
        raise RuntimeError("coga skill update failed")

    monkeypatch.setattr(skill_update, "run_update_json", boom)

    report = SkillUpdateReport()
    assert (
        skill_update.run_skill_update_recipe(load_config(repo), ["--no-pr"], result=report)
        == 2
    )

    assert report.command == build_update_command(
        pr=False, pr_title="Update Coga-managed skills"
    )
    assert report.pr_requested is False
    # Nothing was *classified*: the run failed before returning a payload. The
    # rendered report is the failure itself, not a tally.
    assert report.results == []
    assert "## Skill Update" in report.report
    assert "coga skill update failed" in report.report


def test_recipe_writes_a_failure_report_to_the_blackboard_on_the_hard_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The recurring sweep discards a task's stderr, so an exit-2 run that only
    # wrote its diagnostic there showed up in the run record as a failed task
    # with a blank blackboard and no reason. The failure has to land on the
    # blackboard like every other outcome.
    blackboard = repo / "tasks" / "skill-update" / "blackboard.md"
    blackboard.parent.mkdir(parents=True)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))
    monkeypatch.setenv("COGA_TASK_SLUG", "skill-update")

    def boom(*, cwd: Path | None, pr: bool, pr_title: str):
        raise RuntimeError(
            "`coga skill update --all --pr --json` failed with exit 1: "
            "! [rejected] coga/skill-update -> coga/skill-update (stale info)"
        )

    monkeypatch.setattr(skill_update, "run_update_json", boom)

    report = SkillUpdateReport()
    assert skill_update.run_skill_update_recipe(load_config(repo), [], result=report) == 2

    written = blackboard.read_text()
    assert "## Skill Update" in written
    assert "Task: `skill-update`" in written
    assert "### Failed" in written
    assert "(stale info)" in written
    # Not "PR: none opened": the update raises only after the child ran, and the
    # push precedes the `gh` calls, so a real PR or branch update may exist.
    assert "PR: not confirmed" in written
    assert "none opened" not in written
    assert report.report == written


def test_recipe_survives_an_unwritable_blackboard_on_the_hard_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A blackboard that cannot be written must not replace the original
    # diagnostic with a traceback: the exit code stays 2.
    blackboard = repo / "tasks" / "missing" / "blackboard.md"
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))

    def boom(*, cwd: Path | None, pr: bool, pr_title: str):
        raise RuntimeError("coga skill update failed")

    monkeypatch.setattr(skill_update, "run_update_json", boom)

    assert skill_update.run_skill_update_recipe(load_config(repo), []) == 2


def test_render_failure_report_names_the_command_and_the_detail() -> None:
    report = render_failure_report(
        "`coga skill update --all --json` failed with exit 2: boom",
        generated_at="2026-09-01T00:00:00+00:00",
        command=["coga", "skill", "update", "--all", "--json"],
        pr_requested=False,
        task_slug="recurring/skill-update",
    )

    assert report.startswith("## Skill Update\n")
    assert "Command: `coga skill update --all --json`" in report
    assert "Task: `recurring/skill-update`" in report
    assert "Result: the update failed; no skills were classified." in report
    assert "PR: none opened (--no-pr)." in report
    assert "### Failed" in report
    assert "failed with exit 2: boom" in report
    assert report.endswith("```\n")


def test_recipe_keeps_the_success_report_when_the_blackboard_write_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `append_report` raises RuntimeError on a missing blackboard parent — the
    # same exception type a failed update raises. If the success-path write sits
    # inside the update's `try`, a clean run gets filed as "the update failed;
    # no skills were classified" while `results` still holds the classification.
    blackboard = repo / "tasks" / "missing" / "blackboard.md"
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))

    def clean_run(*, cwd: Path | None, pr: bool, pr_title: str):
        payload = {
            "results": [
                {
                    "name": "code/open-pr",
                    "source_type": "url",
                    "status": "updated",
                    "message": "",
                    "changed": True,
                }
            ],
            "pr_url": "https://github.com/FastJVM/coga/pull/9",
        }
        return payload, ["coga", "skill", "update", "--all", "--pr"]

    monkeypatch.setattr(skill_update, "run_update_json", clean_run)

    report = SkillUpdateReport()
    with pytest.raises(RuntimeError, match="Blackboard parent does not exist"):
        skill_update.run_skill_update_recipe(load_config(repo), [], result=report)

    # The run succeeded; the report it produced must describe that, not a failure.
    assert [result.name for result in report.results] == ["code/open-pr"]
    assert report.pr_url == "https://github.com/FastJVM/coga/pull/9"
    assert "the update failed" not in report.report


def test_recipe_survives_a_permission_error_on_the_hard_exit(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The realistic unwritable-blackboard failure is OSError, not RuntimeError:
    # `append_report` only converts a missing parent into the latter, while the
    # write itself raises PermissionError on a read-only checkout or full disk.
    blackboard = repo / "tasks" / "skill-update" / "blackboard.md"
    blackboard.parent.mkdir(parents=True)
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(blackboard))

    def boom(*, cwd: Path | None, pr: bool, pr_title: str):
        raise RuntimeError("coga skill update failed")

    def unwritable(self, *args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(skill_update, "run_update_json", boom)
    monkeypatch.setattr(Path, "write_text", unwritable)

    assert skill_update.run_skill_update_recipe(load_config(repo), []) == 2


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
    assert "`gh skill`'s own metadata for GitHub-backed installs" in norm
    assert "Coga `.coga-source.json` provenance for URL-backed installs" in norm
    assert "delegated GitHub path does not promise to preserve local edits" in norm
    assert "Do not keep local adaptations in GitHub-backed directories" in norm
    assert "- Output: append `## Skill Update`" in text
    assert "COGA_TASK_BLACKBOARD" in text
    assert "--blackboard" not in text


def test_skill_update_ships_as_a_recurring_template() -> None:
    """The skill updater is a standalone recurring task, not a Dream phase.
    The packaged template pairs a weekly ticket with the reserved `ticket.py`
    deterministic half and keeps a one-step workflow for ordinary task
    lifecycle. No declaration field selects that mode — the file does."""
    coga_os = SKILL_UPDATE.parents[3]
    template_dir = coga_os / "recurring" / "skill-update"
    ticket = (template_dir / "ticket.md").read_text()
    script = (template_dir / "ticket.py").read_text()
    workflow = (coga_os / "workflows" / "skill-update" / "run.md").read_text()

    assert ticket.startswith("---\n")
    assert "schedule:" in ticket
    assert 'title: "Skill update"' in ticket
    assert "mode:" not in ticket
    assert "recipe:" not in ticket
    assert "workflow: skill-update/run" in ticket
    assert "coga skill update --all --pr" in ticket

    assert "from coga.skill_update import run_skill_update_recipe" in script
    assert "run_skill_update_recipe(load_config(), [])" in script

    assert "name: skill-update/run" in workflow
    assert "- bootstrap/skill-update" in workflow


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    (coga_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(coga_os)
    return coga_os


def test_skill_update_runs_through_generic_recipe_and_reports_no_op(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No imported skills under `skills/`: `coga skill update --all --pr` finds
    # nothing clean to update, so it commits nothing and opens no PR (never
    # touching git), and the registered recipe reports a clean no-op
    # on the task blackboard.
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH")
    pythonpath = (
        src_path
        if not existing_pythonpath
        else src_path + os.pathsep + existing_pythonpath
    )
    monkeypatch.setenv(
        "PYTHONPATH",
        pythonpath,
    )
    _write(
        repo / "workflows" / "skill-update" / "run.md",
        """
        ---
        name: skill-update/run
        description: recipe-backed task lifecycle.
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
        owner="marc",
        assignee="claude",
        watchers=[],
        status="active",
    )

    ref = list_tasks(cfg)[0]
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(ref.ticket_path.resolve()))
    monkeypatch.setenv("COGA_TASK_SLUG", ref.id_slug)

    result = CliRunner().invoke(app, ["run", "skill-update"])

    assert result.exit_code == 0, result.output
    # The inherited task context points at the single ticket file, so the
    # report lands in its blackboard region.
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

    assert skill_update.run_skill_update_recipe(load_config(repo), []) == 1
    text = blackboard.read_text()
    assert "## Skill Update" in text
    assert "Task: `skill-update`" in text
    assert "### Needs follow-up" in text
    assert "`b/adapted`: `skipped-local-adaptation`" in text
    assert "PR: none opened" in text
