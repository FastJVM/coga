"""Period keys for schedules that fire more than once per month/week/day bucket."""
import shutil
from datetime import datetime
from pathlib import Path

from coga.config import load_config
from coga.recurring import _period_key, scan_due
from coga.ticket import Ticket

from tests.test_recurring import _write_recurring, repo  # noqa: F401


def test_weekday_firings_get_their_own_periods() -> None:
    mon = _period_key("0 9 * * 1-5", datetime(2026, 4, 20, 9))
    tue = _period_key("0 9 * * 1-5", datetime(2026, 4, 21, 9))
    assert (mon, tue) == ("2026-04-20", "2026-04-21")


def test_twice_monthly_firings_get_their_own_periods() -> None:
    assert _period_key("0 9 1,15 * *", datetime(2026, 4, 1, 9)) == "2026-04-01"
    assert _period_key("0 9 1,15 * *", datetime(2026, 4, 15, 9)) == "2026-04-15"


def test_once_per_bucket_schedules_keep_their_keys() -> None:
    assert _period_key("0 9 * * 1", datetime(2026, 4, 20, 9)) == "2026-W17"
    assert _period_key("0 9 1 * *", datetime(2026, 4, 1, 9)) == "2026-04"
    assert _period_key("0 9 * * *", datetime(2026, 4, 20, 9)) == "2026-04-20"


def test_sub_hourly_schedules_keep_one_period_per_hour() -> None:
    assert _period_key("* * * * *", datetime(2026, 4, 20, 9, 7)) == "2026-04-20-09"
    assert _period_key("*/15 * * * *", datetime(2026, 4, 20, 9, 30)) == "2026-04-20-09"


def _finish(ref) -> None:
    ticket = Ticket.read(ref.path / "ticket.md")
    ticket.frontmatter["status"] = "done"
    ticket.write(ref.path / "ticket.md")
    shutil.rmtree(ref.path)


def test_weekday_schedule_runs_every_weekday(repo: Path) -> None:  # noqa: F811
    _write_recurring(
        repo,
        "weekly-check",
        """
        ---
        schedule: "0 9 * * 1-5"
        title: "Weekday standup digest"
        owner: marc
        ---

        ## Description

        Post the standup digest.
        """,
    )
    cfg = load_config(repo)
    created = []
    for day in range(20, 25):  # Mon 20 .. Fri 24 Apr 2026, one sweep a day at 10:00
        task = scan_due(cfg, now=datetime(2026, 4, day, 10, 0, 0)).tasks[0]
        created.append(task.created)
        if task.created:
            _finish(task.ref)
    assert created == [True] * 5
