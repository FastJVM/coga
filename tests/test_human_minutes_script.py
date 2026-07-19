from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from zoneinfo import ZoneInfo

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "human_minutes.py"
JULY_FIXTURE = (
    ROOT / "tests" / "fixtures" / "human_minutes" / "july_1_2_megalaunch.log"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("human_minutes_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


human_minutes = _load_module()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _event(minute: int) -> object:
    return human_minutes.Event(
        timestamp=datetime(2026, 7, 1, 9, minute, tzinfo=ZoneInfo("UTC")),
        task="demo",
        source="log",
        action="event",
    )


def _git(
    root: Path, *args: str, when: str = "2026-07-01T09:00:00-07:00"
) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": when,
            "GIT_COMMITTER_DATE": when,
        }
    )
    subprocess.run(
        ["git", *args],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_episode_gap_is_strictly_greater_and_floor_applies() -> None:
    episodes = human_minutes.cluster_events(
        [_event(0), _event(10), _event(21)], gap_minutes=10
    )

    assert [len(episode.events) for episode in episodes] == [2, 1]
    assert human_minutes.episode_total(episodes, floor_minutes=2) == 12
    assert human_minutes.episode_total(episodes, floor_minutes=5) == 15

    short_multi_event = human_minutes.cluster_events(
        [_event(0), _event(1)], gap_minutes=10
    )
    assert human_minutes.episode_total(short_multi_event, floor_minutes=5) == 1

    shared_commit = human_minutes.Event(
        timestamp=datetime(2026, 7, 1, 9, 30, tzinfo=ZoneInfo("UTC")),
        task="first",
        source="git",
        action="shared commit",
        event_id="git:shared",
    )
    duplicate_association = human_minutes.Event(
        timestamp=shared_commit.timestamp,
        task="second",
        source="git",
        action="shared commit",
        event_id="git:shared",
    )
    deduplicated = human_minutes.cluster_events(
        [shared_commit, duplicate_association], gap_minutes=10
    )
    assert human_minutes.episode_total(deduplicated, floor_minutes=2) == 2


def test_july_1_2_log_fixture_has_nine_megalaunch_tasks_in_expected_range() -> None:
    tz = ZoneInfo("America/Los_Angeles")
    log_data = human_minutes.parse_log(JULY_FIXTURE, tz=tz, log_web_url=None)
    since = human_minutes.parse_window_bound(
        "2026-07-01", is_until=False, tz=tz
    )
    until = human_minutes.parse_window_bound("2026-07-02", is_until=True, tz=tz)

    report = human_minutes.build_report(
        log_data=log_data,
        task_infos={},
        external_events=[],
        since=since,
        until=until,
        timezone_name="America/Los_Angeles",
        gap_minutes=10,
        floor_minutes=2,
        prs_read=0,
        identities={"nicktoper"},
        git_enabled=False,
        github_enabled=False,
    )

    assert len({attempt.task for attempt in log_data.attempts}) == 9
    assert len(report["tasks"]) == 9
    assert all(2 <= row["minutes"] <= 12 for row in report["tasks"])
    assert report["days"][0]["blockers_answered"][0]["task"] == "burst/task-03"
    assert report["sensitivity"]["floor_minutes"] == 5
    markdown = human_minutes.format_markdown(report)
    assert "Sensitivity (isolated-event floor = 5 min):" in markdown
    assert "git=omitted, agent commits excluded=omitted, GitHub=omitted" in markdown


def test_recorded_local_branch_attributes_only_human_non_coga_commits(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "nicktoper")
    _git(tmp_path, "config", "user.email", "nick@example.com")
    _write(tmp_path / "tracked.txt", "base\n")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "Base", when="2026-07-01T08:00:00-07:00")
    _git(tmp_path, "switch", "-c", "demo-branch")
    _write(tmp_path / "human.txt", "human\n")
    _git(tmp_path, "add", "human.txt")
    _git(tmp_path, "commit", "-m", "Review outcome")
    _write(tmp_path / "agent.txt", "agent\n")
    _git(tmp_path, "add", "agent.txt")
    _git(
        tmp_path,
        "commit",
        "-m",
        "Agent implementation",
        when="2026-07-01T09:05:00-07:00",
    )
    _write(tmp_path / "auto.txt", "auto\n")
    _git(tmp_path, "add", "auto.txt")
    _git(
        tmp_path,
        "commit",
        "-m",
        "Log: demo",
        when="2026-07-01T09:07:00-07:00",
    )

    tz = ZoneInfo("America/Los_Angeles")
    excluded: set[str] = set()
    events = human_minutes._local_branch_events(
        "demo",
        "demo-branch",
        matcher=human_minutes.IdentityMatcher({"nicktoper"}),
        agent_windows=[
            human_minutes.AgentSessionWindow(
                datetime(2026, 7, 1, 8, 30, tzinfo=tz),
                datetime(2026, 7, 1, 8, 31, tzinfo=tz),
            ),
            human_minutes.AgentSessionWindow(
                datetime(2026, 7, 1, 9, 4, tzinfo=tz),
                datetime(2026, 7, 1, 9, 6, tzinfo=tz),
            ),
        ],
        tz=tz,
        repo_root=tmp_path,
        git_base="main",
        commit_web_root="https://github.com/acme/widgets",
        seen_commits=set(),
        agent_commits_excluded=excluded,
    )

    assert [event.action for event in events] == ["Review outcome"]
    assert len(excluded) == 1
    assert events[0].link is not None
    assert events[0].link.startswith("https://github.com/acme/widgets/commit/")

    with pytest.raises(human_minutes.MetricsError, match="predates schema-2"):
        human_minutes._local_branch_events(
            "demo",
            "demo-branch",
            matcher=human_minutes.IdentityMatcher({"nicktoper"}),
            agent_windows=[],
            tz=tz,
            repo_root=tmp_path,
            git_base="main",
            commit_web_root=None,
            seen_commits=set(),
            agent_commits_excluded=set(),
        )


def test_json_report_merges_log_git_github_and_usage_records(
    tmp_path: Path, capsys
) -> None:
    task = tmp_path / "coga" / "tasks" / "demo.md"
    pr_url = "https://github.com/acme/widgets/pull/7"
    _write(
        task,
        f"""
        ---
        slug: demo
        title: Demo
        status: done
        owner: nicktoper
        human: nicktoper
        ---

        ## Description

        Demo task.

        <!-- coga:blackboard -->

        ## Dev

        pr: {pr_url}
        branch: demo-branch
        """,
    )
    usage_autonomous = {
        "schema": 2,
        "ts": "2026-07-01T16:00:00Z",
        "started_at": "2026-07-01T15:55:00Z",
        "ended_at": "2026-07-01T16:00:00Z",
        "session_id": "autonomous-session",
        "slug": "demo",
        "usage_status": "ok",
        "human_turns": 0,
        "provider": "openai",
        "model": "model-a",
        "input_tokens": 10,
        "cache_creation_input_tokens": 2,
        "cache_read_input_tokens": 3,
        "output_tokens": 4,
    }
    usage_interactive = {
        "schema": 2,
        "ts": "2026-07-01T17:05:00Z",
        "started_at": "2026-07-01T17:01:00Z",
        "ended_at": "2026-07-01T17:05:00Z",
        "session_id": "interactive-session",
        "slug": "demo",
        "usage_status": "ok",
        "human_turns": 2,
        "provider": "anthropic",
        "model": "model-b",
        "input_tokens": 5,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": 0,
        "output_tokens": 6,
    }
    log = tmp_path / "coga" / "log.md"
    _write(
        log,
        "\n".join(
            [
                "2026-07-01 09:00 [demo] [human:nicktoper] unblocked (blocked → active): Keep the change narrow.",
                "2026-07-01 09:04 [demo] [human:nicktoper] advanced to step 2 (review)",
                "2026-07-01 10:00 [demo] [system] "
                + json.dumps(usage_autonomous, separators=(",", ":")),
                "2026-07-01 10:05 [demo] [system] "
                + json.dumps(usage_interactive, separators=(",", ":")),
            ]
        )
        + "\n",
    )
    github_data = tmp_path / "github.json"
    github_data.write_text(
        json.dumps(
            {
                pr_url: {
                    "url": pr_url,
                    "commits": [
                        {
                            "oid": "abc123",
                            "committedDate": "2026-07-01T16:05:00Z",
                            "messageHeadline": "Implement demo",
                            "authors": [
                                {
                                    "login": "nicktoper",
                                    "name": "Nick",
                                    "email": "nick@example.com",
                                }
                            ],
                        },
                        {
                            "oid": "auto456",
                            "committedDate": "2026-07-01T16:06:00Z",
                            "messageHeadline": "Ticket: demo — step 2",
                            "authors": [{"login": "nicktoper"}],
                        },
                        {
                            "oid": "auto-log",
                            "committedDate": "2026-07-01T16:06:30Z",
                            "messageHeadline": "Log: demo",
                            "authors": [{"login": "nicktoper"}],
                        },
                        {
                            "oid": "auto-sync",
                            "committedDate": "2026-07-01T16:06:45Z",
                            "messageHeadline": "Sync coga state",
                            "authors": [{"login": "nicktoper"}],
                        },
                        {
                            "oid": "agent789",
                            "committedDate": "2026-07-01T17:03:00Z",
                            "messageHeadline": "Agent implementation",
                            "authors": [{"login": "nicktoper"}],
                        },
                    ],
                    "reviews": [
                        {
                            "id": "review-1",
                            "submittedAt": "2026-07-01T16:06:00Z",
                            "state": "APPROVED",
                            "author": {"login": "nicktoper", "is_bot": False},
                        }
                    ],
                    "comments": [
                        {
                            "id": "comment-1",
                            "createdAt": "2026-07-01T16:08:00Z",
                            "url": pr_url + "#issuecomment-1",
                            "author": {"login": "nicktoper", "is_bot": False},
                        }
                    ],
                    "reviewComments": [
                        {
                            "id": "inline-1",
                            "created_at": "2026-07-01T16:09:00Z",
                            "html_url": pr_url + "#discussion_r1",
                            "user": {"login": "nicktoper", "type": "User"},
                        },
                        {
                            "id": "inline-bot",
                            "created_at": "2026-07-01T16:10:00Z",
                            "user": {"login": "ci[bot]", "type": "Bot"},
                        },
                    ],
                    "mergedAt": "2026-07-01T16:12:00Z",
                    "mergedBy": {"login": "nicktoper", "is_bot": False},
                }
            }
        )
    )

    result = human_minutes.main(
        [
            "--repo-root",
            str(tmp_path),
            "--github-data",
            str(github_data),
            "--repo-url",
            "https://github.com/acme/widgets",
            "--revision",
            "deadbeef",
            "--since",
            "2026-07-01",
            "--until",
            "2026-07-01",
            "--json",
        ]
    )

    assert result == 0
    report = json.loads(capsys.readouterr().out)
    assert report["sources"] == {
        "agent_commit_events_excluded": 1,
        "git_enabled": True,
        "git_commit_events": 1,
        "github_enabled": True,
        "github_events": 4,
        "github_prs_read": 1,
        "log_enabled": True,
        "log_events": 2,
        "usage_sessions": 2,
    }
    assert report["tasks"] == [
        {
            "artifact": pr_url,
            "episodes": 1,
            "events": 7,
            "minutes": 12.0,
            "task": "demo",
        }
    ]
    assert report["days"][0]["blockers_answered"][0]["link"].endswith(
        "/coga/log.md#L1"
    )
    assert report["days"][0]["tasks_advanced"] == ["demo"]
    assert report["tokens"]["by_mode"]["autonomous"]["total_tokens"] == 19
    assert report["tokens"]["by_mode"]["interactive"]["total_tokens"] == 11
    assert [
        (row["provider"], row["model"])
        for row in report["tokens"]["by_model"]
    ] == [("anthropic", "model-b"), ("openai", "model-a")]


def test_union_log_duplicates_and_free_form_text_do_not_change_ledger(
    tmp_path: Path,
) -> None:
    dependency_pr = "https://github.com/acme/widgets/pull/41"
    task_pr = "https://github.com/acme/widgets/pull/42"
    answer = (
        "Use the dependency PR only as context; preserve this complete blocker "
        "answer in the published human-readable ledger without truncating it."
    )
    human_line = (
        "2026-07-01 09:00 [demo] [human:nicktoper] "
        f"unblocked (blocked → active): {answer} Dependency: {dependency_pr}"
    )
    usage = {
        "schema": 1,
        "ts": "2026-07-01T16:00:00Z",
        "slug": "demo",
        "usage_status": "ok",
        "session_id": "usage-1",
        "input_tokens": 3,
        "output_tokens": 2,
    }
    usage_line = (
        "2026-07-01 09:00 [demo] [system] "
        + json.dumps(usage, separators=(",", ":"))
    )
    log = tmp_path / "coga" / "log.md"
    _write(
        log,
        "\n".join(
            [
                human_line,
                human_line,
                "2026-07-01 09:01 [docs] [agent:claude] blocked: docs/getting-started.md needs a decision",
                "2026-07-01 09:02 [publish] [agent:claude] advanced to step 4 (review) — PR opened & mergeable: "
                f"<{task_pr}|PR #42>",
                usage_line,
                usage_line,
            ]
        )
        + "\n",
    )

    tz = ZoneInfo("America/Los_Angeles")
    log_data = human_minutes.parse_log(log, tz=tz, log_web_url=None)
    report = human_minutes.build_report(
        log_data=log_data,
        task_infos={},
        external_events=[],
        since=human_minutes.parse_window_bound("2026-07-01", is_until=False, tz=tz),
        until=human_minutes.parse_window_bound("2026-07-01", is_until=True, tz=tz),
        timezone_name="America/Los_Angeles",
        gap_minutes=10,
        floor_minutes=2,
        prs_read=0,
        identities={"nicktoper"},
        git_enabled=False,
        github_enabled=False,
    )

    assert len(log_data.events) == 1
    assert len(log_data.blockers) == 1
    assert [item.task for item in log_data.progress] == ["demo", "publish"]
    assert log_data.pr_urls == {"publish": task_pr}
    assert report["tasks"][0]["minutes"] == 2
    assert report["sources"]["usage_sessions"] == 1
    markdown = human_minutes.format_markdown(report)
    assert answer in markdown
    assert dependency_pr in markdown
    assert "…" not in markdown


def test_local_branch_fails_loud_when_git_base_is_missing(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "master")
    _git(tmp_path, "config", "user.name", "nicktoper")
    _git(tmp_path, "config", "user.email", "nick@example.com")
    _write(tmp_path / "tracked.txt", "base\n")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "Base")
    _git(tmp_path, "switch", "-c", "demo-branch")

    with pytest.raises(human_minutes.MetricsError, match="git base 'origin/main'"):
        human_minutes._local_branch_events(
            "demo",
            "demo-branch",
            matcher=human_minutes.IdentityMatcher({"nicktoper"}),
            agent_windows=[],
            tz=ZoneInfo("America/Los_Angeles"),
            repo_root=tmp_path,
            git_base="origin/main",
            commit_web_root=None,
            seen_commits=set(),
            agent_commits_excluded=set(),
        )


def test_github_fixture_missing_record_fails_loud(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / "coga" / "tasks" / "demo.md",
        """
        ---
        slug: demo
        human: nicktoper
        ---
        <!-- coga:blackboard -->
        ## Dev
        pr: https://github.com/acme/widgets/pull/9
        """,
    )
    _write(tmp_path / "coga" / "log.md", "")
    fixture = tmp_path / "github.json"
    fixture.write_text("{}")

    result = human_minutes.main(
        [
            "--repo-root",
            str(tmp_path),
            "--github-data",
            str(fixture),
        ]
    )

    assert result == 2
    assert "has no object for recorded PR" in capsys.readouterr().err
