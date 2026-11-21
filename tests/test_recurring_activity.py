from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from coga.config import Config
from coga.recurring_activity import check_activity


def _cfg(repo: Path, **kwargs) -> Config:
    return Config(repo_root=repo, current_user="test", default_status="draft",
                  agents={}, slack_webhook=None, slack_enabled=False, **kwargs)


@pytest.mark.parametrize("day,inactive", [(25, False), (26, True)])
def test_recent_activity_uses_the_local_audit_log(tmp_path: Path, day: int, inactive: bool) -> None:
    (tmp_path / "log.md").write_text(
        "2026-09-12 12:00 [work] [human:test] created (status=draft)\n"
        "2026-09-25 12:00 [recurring/job] [system] ran\n"
        "2026-09-25 12:00 [autofix/job] [system] reported findings\n",
        encoding="utf-8",
    )
    result = check_activity(_cfg(tmp_path), date(2026, 9, day))
    assert result.last_human == date(2026, 9, 12)
    assert result.inactive is inactive
    assert result.error is None


def test_empty_workspace_can_run_recurring_jobs(tmp_path: Path) -> None:
    result = check_activity(_cfg(tmp_path), date(2026, 9, 25))
    assert result.last_human is None
    assert not result.inactive


def test_zero_idle_days_disables_the_activity_gate(tmp_path: Path) -> None:
    (tmp_path / "log.md").write_text(
        "2026-09-01 12:00 [work] [human:test] created (status=draft)\n", encoding="utf-8",
    )
    result = check_activity(_cfg(tmp_path, recurring_idle_days=0), date(2026, 9, 25))
    assert not result.inactive
