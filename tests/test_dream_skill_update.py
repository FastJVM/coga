from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL_UPDATE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "relay"
    / "resources"
    / "templates"
    / "relay-os"
    / "bootstrap"
    / "skills"
    / "bootstrap"
    / "dream"
    / "tasks"
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
        command=["relay", "skill", "update", "--all", "--pr", "--json"],
        pr_url="https://example.com/pr/1",
        pr_requested=True,
        task_slug="skill-update",
    )

    assert "## Dream Skill: skill-update" in report
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
        command=["relay", "skill", "update", "--all", "--pr", "--json"],
        pr_url=None,
        pr_requested=True,
        task_slug="skill-update",
    )
    assert "PR: none opened — no clean skill updates to commit." in report


def test_render_handles_empty_results() -> None:
    report = render_blackboard_report(
        [],
        generated_at="2026-06-09T00:00:00+00:00",
        command=["relay", "skill", "update", "--all", "--pr", "--json"],
        pr_url=None,
        pr_requested=True,
        task_slug="skill-update",
    )
    assert "Result: no installed skills to update." in report
    assert "PR: none opened" in report
