from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from coga.config import Config
from coga.recurring_activity import check_activity, is_machine_commit


MACHINE_SUBJECTS = [
    "Log: recurring/dream", "Sync coga state", "Dream findings (#10)",
    "Ticket: recurring/digest — recurring create", "Autofix: fix — created",
    "Ticket: autofix/fix — active", "Update Coga-managed skills (#12)",
    "Ticket: human — blocker reminder",
    *[f"Merge pull request #12 from owner/{branch}" for branch in (
        "claude/dream-w39-fix", "coga/dream-fix", "dream/fix", "coga/skill-update",
    )],
]


def _git(repo: Path, *args: str, **kwargs) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, **kwargs,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "user.email", "test@example.com")
    return tmp_path


def _commit(repo: Path, subject: str, day: str) -> str:
    stamp = f"{day}T12:00:00+00:00"
    _git(repo, "commit", "--allow-empty", "-m", subject,
         env={**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})
    return _git(repo, "rev-parse", "HEAD")


def _cfg(repo: Path, **kwargs) -> Config:
    return Config(repo_root=repo, current_user="test", default_status="draft",
                  agents={}, slack_webhook=None, slack_enabled=False, **kwargs)


@pytest.mark.parametrize("subject", MACHINE_SUBJECTS)
def test_machine_only_history(repo: Path, subject: str) -> None:
    assert is_machine_commit(subject)
    _commit(repo, subject, "2026-09-25")
    activity = check_activity(_cfg(repo), date(2026, 9, 25))
    assert activity.inactive
    assert activity.last_human is None
    assert activity.error is None


@pytest.mark.parametrize("subject", [
    "Implement feature", "Ticket: human — active", "Log: bootstrap/orient",
    "Merge pull request #13 from owner/feature", "Ticket: follow-up — created",
])
def test_human_history(repo: Path, subject: str) -> None:
    assert not is_machine_commit(subject)
    _commit(repo, subject, "2026-09-12")
    assert not check_activity(_cfg(repo), date(2026, 9, 25)).inactive
    assert check_activity(_cfg(repo), date(2026, 9, 26)).inactive


def test_newest_timestamp_across_refs_and_clock_skew(repo: Path) -> None:
    newest = _commit(repo, "Human latest", "2026-09-24")
    _commit(repo, "Human skewed", "2026-09-04")
    _git(repo, "update-ref", "refs/remotes/origin/main", newest)
    _commit(repo, "Dream output", "2026-09-25")
    result = check_activity(_cfg(repo), date(2026, 9, 25))
    assert result.last_human == date(2026, 9, 24)
    assert not result.inactive


@pytest.mark.parametrize("remote_only", [False, True])
def test_single_resolving_ref(repo: Path, remote_only: bool) -> None:
    sha = _commit(repo, "Human", "2026-09-04")
    if remote_only:
        _git(repo, "update-ref", "refs/remotes/origin/main", sha)
        _git(repo, "update-ref", "-d", "refs/heads/main")
    result = check_activity(_cfg(repo), date(2026, 9, 25))
    assert result.inactive
    assert result.last_human == date(2026, 9, 4)


def test_no_refs_fails_open(repo: Path) -> None:
    result = check_activity(_cfg(repo), date(2026, 9, 25))
    assert not result.inactive
    assert result.error


def test_git_failure_fails_open(tmp_path: Path) -> None:
    result = check_activity(_cfg(tmp_path), date(2026, 9, 25))
    assert not result.inactive
    assert result.error


@pytest.mark.parametrize("kwargs", [{"git_enabled": False}, {"recurring_idle_days": 0}])
def test_disabled_never_calls_git(tmp_path: Path, monkeypatch, kwargs) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("called git"))
    result = check_activity(_cfg(tmp_path, **kwargs), date(2026, 9, 25))
    assert not result.inactive
    assert result.error is None


@pytest.mark.parametrize("machine_merge", [True, False])
def test_first_parent_merge_activity(repo: Path, machine_merge: bool) -> None:
    _commit(repo, "Human baseline", "2026-09-04")
    _git(repo, "switch", "-c", "feature")
    _commit(repo, "Feature work invisible until merge", "2026-09-25")
    _git(repo, "switch", "main")
    _commit(repo, "Dream daily", "2026-09-25")
    assert check_activity(_cfg(repo), date(2026, 9, 25)).inactive
    branch = "claude/dream-w39-fix" if machine_merge else "feature"
    stamp = "2026-09-25T12:00:00+00:00"
    _git(repo, "merge", "--no-ff", "feature", "-m",
         f"Merge pull request #15 from owner/{branch}",
         env={**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})
    result = check_activity(_cfg(repo), date(2026, 9, 25))
    assert result.inactive == machine_merge
    assert result.last_human == date(2026, 9, 4 if machine_merge else 25)


def test_classifier_tracks_machine_subject_writers() -> None:
    """Read writer expressions so changes to emitted subjects break this pin."""
    import ast
    root = Path(__file__).resolve().parents[1] / "src/coga"
    git_tree = ast.parse((root / "git.py").read_text())
    writer = next(n for n in git_tree.body if isinstance(n, ast.FunctionDef) and n.name == "sync_coga_state")
    default = writer.args.kw_defaults[0]
    assert isinstance(default, ast.Constant)
    assert is_machine_commit(default.value)
    cases = [
        ("commands/launch.py", "Log: ", "recurring/dream"),
        ("launch_script.py", "Log: ", "recurring/dream"),
        ("recurring_runner.py", "Log: ", "recurring/dream"),
        ("recurring_runner.py", " — recurring create", "recurring/digest"),
        ("recurring_autofix.py", " — created", "autofix/test"),
        ("blocker_reminders.py", " — blocker reminder", "human"),
    ]
    for filename, fragment, slug in cases:
        tree = ast.parse((root / filename).read_text())
        subjects = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.keyword) or node.arg != "message":
                continue
            value = node.value
            if isinstance(value, ast.JoinedStr):
                subject = "".join(part.value if isinstance(part, ast.Constant) else slug
                                  for part in value.values)
                if fragment in subject:
                    subjects.append(subject)
        # The recurring create writer first assigns its message to a local.
        if filename == "recurring_runner.py" and fragment == " — recurring create":
            subjects = ["".join(part.value if isinstance(part, ast.Constant) else slug
                                for part in node.values)
                        for node in ast.walk(tree) if isinstance(node, ast.JoinedStr)
                        and any(isinstance(part, ast.Constant) and part.value == fragment
                                for part in node.values)]
        assert subjects, (filename, fragment)
        assert all(is_machine_commit(subject) for subject in subjects), subjects
    for filename in ("skill_manager.py", "commands/skill.py"):
        constants = [n.value for n in ast.walk(ast.parse((root / filename).read_text()))
                     if isinstance(n, ast.Constant)]
        assert "Update Coga-managed skills" in constants
        assert is_machine_commit("Update Coga-managed skills")
    assert not is_machine_commit("Ticket: human — active")


@pytest.mark.parametrize("remote_newer", [False, True])
def test_divergent_refs_choose_newest_human(repo: Path, remote_newer: bool) -> None:
    base = _commit(repo, "Human baseline", "2026-09-01")
    _git(repo, "switch", "-c", "remote-history")
    remote = _commit(repo, "Remote human", "2026-09-24" if remote_newer else "2026-09-04")
    _git(repo, "update-ref", "refs/remotes/origin/main", remote)
    _git(repo, "switch", "main")
    assert _git(repo, "rev-parse", "HEAD") == base
    _commit(repo, "Local human", "2026-09-04" if remote_newer else "2026-09-24")
    assert check_activity(_cfg(repo), date(2026, 9, 25)).last_human == date(2026, 9, 24)


def test_log_failure_fails_open(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _commit(repo, "Human", "2026-09-04")
    run = subprocess.run

    def fail_log(argv, **kwargs):
        if argv[:2] == ["git", "log"]:
            raise subprocess.CalledProcessError(128, argv)
        return run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_log)
    result = check_activity(_cfg(repo), date(2026, 9, 25))
    assert not result.inactive and result.error
