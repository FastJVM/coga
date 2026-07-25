"""Tests for the shared recurring-reminder / sweep engine (`coga.reminders`).

Two halves:

- **Engine unit tests** — the shared primitives (date math, the in-window
  kernel, frontmatter reading, ack helpers, notify, the CLI harness).
- **Parity** — the reason the engine exists. Two already-shipped patents
  sweeps are vendored under `fixtures/reminders/`: the standalone originals
  (`golden/`, the oracle) and engine-backed retrofits (`retrofit/`). For the
  same `--today` / `--tasks-dir` the retrofit's stdout must match the golden's
  byte-for-byte, plus a frozen snapshot of each sweep's recorded sample run.
  The sweeps are deliberately diverse: maintenance exercises the auto-detect
  path (`patent_maintenance_paid == N`), candidate the time-window path.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from coga import reminders


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reminders"
MAINTENANCE_TASKS = FIXTURES / "tasks" / "maintenance"
CANDIDATE_TASKS = FIXTURES / "tasks" / "candidate"
RECORDED = FIXTURES / "recorded"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


golden_maintenance = _load(
    "golden_maintenance", FIXTURES / "golden" / "maintenance_fee_sweep.py"
)
retrofit_maintenance = _load(
    "retrofit_maintenance", FIXTURES / "retrofit" / "maintenance_fee_sweep.py"
)
golden_candidate = _load(
    "golden_candidate", FIXTURES / "golden" / "candidate_sweep.py"
)
retrofit_candidate = _load(
    "retrofit_candidate", FIXTURES / "retrofit" / "candidate_sweep.py"
)


# ==========================================================================
# Engine unit tests
# ==========================================================================

# --- date arithmetic -------------------------------------------------------


def test_add_years_basic():
    assert reminders.add_years(date(2020, 1, 31), 3) == date(2023, 1, 31)


def test_add_years_leap_day_clamps_in_non_leap_year():
    assert reminders.add_years(date(2020, 2, 29), 1) == date(2021, 2, 28)


def test_add_years_leap_day_preserved_in_leap_year():
    assert reminders.add_years(date(2020, 2, 29), 4) == date(2024, 2, 29)


def test_add_months_basic():
    assert reminders.add_months(date(2026, 1, 19), 14) == date(2027, 3, 19)


def test_add_months_wraps_year():
    assert reminders.add_months(date(2025, 5, 30), 12) == date(2026, 5, 30)


def test_add_months_clamps_short_month():
    assert reminders.add_months(date(2025, 12, 31), 14) == date(2027, 2, 28)


def test_add_months_clamps_to_leap_feb29():
    assert reminders.add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_parse_date():
    assert reminders.parse_date("2026-01-19") == date(2026, 1, 19)
    assert reminders.parse_date("") is None
    assert reminders.parse_date("  ") is None
    assert reminders.parse_date("not-a-date") is None
    assert reminders.parse_date("2026-13-99") is None


# --- in-window kernel ------------------------------------------------------


def test_in_window_open_is_inclusive():
    assert reminders.in_window(date(2026, 1, 1), date(2026, 1, 1), date(2026, 2, 1))


def test_in_window_close_is_exclusive():
    assert not reminders.in_window(date(2026, 2, 1), date(2026, 1, 1), date(2026, 2, 1))


def test_in_window_before_open_is_false():
    assert not reminders.in_window(date(2025, 12, 31), date(2026, 1, 1), date(2026, 2, 1))


def test_in_window_past_deadline_fires_ignores_close():
    # A money obligation keeps firing after its deadline until satisfied.
    opens, closes = date(2026, 1, 1), date(2026, 2, 1)
    assert reminders.in_window(date(2030, 6, 1), opens, closes, past_deadline_fires=True)
    # …but still does not fire before it opens.
    assert not reminders.in_window(
        date(2025, 12, 31), opens, closes, past_deadline_fires=True
    )


# --- frontmatter reading ---------------------------------------------------


def test_read_frontmatter_scalar_fields(tmp_path):
    p = tmp_path / "t.md"
    p.write_text(
        "---\n"
        "slug: patent-x\n"
        "patent_number: '123'\n"
        "  indented: ignored\n"
        "# comment: ignored\n"
        "contexts:\n"
        "  - a/b\n"
        "---\n\n## Description\nbody\n",
        encoding="utf-8",
    )
    fm = reminders.read_frontmatter(p)
    # A column-0 `contexts:` key keeps its (empty) value; its indented list items
    # are skipped. Callers `.get()` the scalar keys they need, so the empty
    # `contexts` entry is harmless — this mirrors the golden sweeps verbatim.
    assert fm == {"slug": "patent-x", "patent_number": "123", "contexts": ""}


def test_read_frontmatter_no_frontmatter(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("no frontmatter here\n", encoding="utf-8")
    assert reminders.read_frontmatter(p) == {}


def test_read_frontmatter_missing_file(tmp_path):
    assert reminders.read_frontmatter(tmp_path / "nope.md") == {}


# --- default tasks dir -----------------------------------------------------


def test_default_tasks_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("COGA_COGA_OS_ROOT", str(tmp_path))
    assert reminders.default_tasks_dir() == tmp_path / "tasks"


def test_default_tasks_dir_unset_returns_none(monkeypatch):
    monkeypatch.delenv("COGA_COGA_OS_ROOT", raising=False)
    assert reminders.default_tasks_dir() is None


# --- ack helper ------------------------------------------------------------


def test_read_ack_absent(tmp_path):
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        "---\nslug: example\n---\n\nBody\n\n<!-- coga:blackboard -->\n\nsome notes\n",
        encoding="utf-8",
    )
    assert reminders.read_ack(ticket) is None


def test_record_then_read_ack(tmp_path):
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        "---\nslug: example\n---\n\nBody\n\n<!-- coga:blackboard -->\n\nsome notes\n",
        encoding="utf-8",
    )
    reminders.record_ack(ticket, "2026-07")
    assert reminders.read_ack(ticket) == "2026-07"
    assert "some notes" in ticket.read_text()


def test_record_ack_replaces_prior(tmp_path):
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        "---\nslug: example\n---\n\nBody\n\n<!-- coga:blackboard -->"
        "\n\nnotes\nAcked: 2026-06\nmore\n",
        encoding="utf-8",
    )
    reminders.record_ack(ticket, "2026-07")
    assert reminders.read_ack(ticket) == "2026-07"
    # Exactly one Acked line survives.
    assert ticket.read_text().count("Acked:") == 1


def test_ack_ignores_body_examples_and_preserves_body(tmp_path):
    ticket = tmp_path / "ticket.md"
    before_fence = (
        "---\nslug: example\n---\n\n"
        "Example syntax: `Acked: YYYY-MM`.\n\n"
        "Acked: not-live-state\n\n"
        "<!-- coga:blackboard -->"
    )
    ticket.write_text(before_fence + "\n\nAcked: 2026-06\n", encoding="utf-8")

    assert reminders.read_ack(ticket) == "2026-06"
    reminders.record_ack(ticket, "2026-07")

    updated = ticket.read_text(encoding="utf-8")
    assert (
        updated.partition("<!-- coga:blackboard -->")[0]
        + "<!-- coga:blackboard -->"
        == before_fence
    )
    assert reminders.read_ack(ticket) == "2026-07"
    assert "Acked: not-live-state" in updated


# --- notify ----------------------------------------------------------------


def test_notify_important_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reminders.subprocess,
        "run",
        lambda cmd, *a, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0),
    )
    rc = reminders.notify("repo/x", "hello")
    assert rc == 0
    assert calls == [["coga", "slack", "--task", "repo/x", "--message", "hello", "--important"]]


def test_notify_can_drop_important(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reminders.subprocess,
        "run",
        lambda cmd, *a, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 7),
    )
    rc = reminders.notify("repo/x", "hi", important=False)
    assert rc == 7
    assert "--important" not in calls[0]


# --- run() harness ---------------------------------------------------------


def _ok_sweep(report="R", alerts=None):
    return lambda today, tasks_dir: reminders.SweepResult(report=report, alerts=alerts or [])


def test_run_prints_report_and_returns_zero(tmp_path, capsys):
    rc = reminders.run(
        _ok_sweep("the report"),
        task_slug="repo/x",
        argv=["--today", "2026-07-13", "--tasks-dir", str(tmp_path)],
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "the report"


def test_run_missing_tasks_dir_returns_one(tmp_path, capsys):
    missing = tmp_path / "nope"
    rc = reminders.run(
        _ok_sweep(), task_slug="repo/x", argv=["--tasks-dir", str(missing)]
    )
    assert rc == 1
    assert "tasks directory not found" in capsys.readouterr().err


def test_run_bare_is_print_only(tmp_path, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(reminders, "notify", lambda *a, **k: posted.append(a) or 0)
    rc = reminders.run(
        _ok_sweep("R", ["alert-1"]),
        task_slug="repo/x",
        argv=["--tasks-dir", str(tmp_path)],  # no --notify
    )
    assert rc == 0 and posted == []


def test_run_notify_posts_each_alert(tmp_path, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(
        reminders, "notify", lambda task, msg, **k: posted.append((task, msg, k)) or 0
    )
    rc = reminders.run(
        _ok_sweep("R", ["alert-1", "alert-2"]),
        task_slug="repo/x",
        argv=["--tasks-dir", str(tmp_path), "--notify"],
    )
    assert rc == 0
    assert [m for _, m, _ in posted] == ["alert-1", "alert-2"]
    assert all(k.get("important") is True for _, _, k in posted)


def test_run_notify_uses_env_task_slug(tmp_path, monkeypatch):
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/from-env")
    posted = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(task) or 0)
    reminders.run(
        _ok_sweep("R", ["a"]),
        task_slug="repo/fallback",
        argv=["--tasks-dir", str(tmp_path), "--notify"],
    )
    assert posted == ["recurring/from-env"]


def test_run_notify_failure_returns_one(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "notify", lambda *a, **k: 1)
    rc = reminders.run(
        _ok_sweep("R", ["a"]),
        task_slug="repo/x",
        argv=["--tasks-dir", str(tmp_path), "--notify"],
    )
    assert rc == 1


# ==========================================================================
# Parity — retrofit stdout must match the golden oracle byte-for-byte
# ==========================================================================

MAINTENANCE_DATES = [
    "2025-06-01",  # between windows -> nothing flagged
    "2026-01-15",  # entering windows
    "2026-07-13",  # recorded sample run: 2 flagged, 1 suppressed
    "2027-02-01",  # windows closing
    "2030-06-01",  # all aged out
]

CANDIDATE_DATES = [
    "2026-07-13",  # before the in-window candidate reaches 14mo
    "2027-03-18",  # one day before the window opens
    "2027-03-19",  # window opens (recorded sample run): 1 flagged
    "2027-04-01",  # mid-window
    "2027-04-19",  # window closes (exclusive) -> aged out
    "2028-01-01",  # long aged out
]


def _capture(module, argv, capsys, monkeypatch):
    """Run a sweep's main() against the fixtures, returning stdout only.

    The golden maintenance sweep always posts (no --notify gate), so stub
    subprocess.run to keep the oracle offline; stdout is the parity surface.
    """
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 0)
    )
    capsys.readouterr()  # clear
    module.main(argv)
    return capsys.readouterr().out


@pytest.mark.parametrize("today", MAINTENANCE_DATES)
def test_maintenance_retrofit_matches_golden(today, capsys, monkeypatch):
    argv = ["--today", today, "--tasks-dir", str(MAINTENANCE_TASKS)]
    golden = _capture(golden_maintenance, argv, capsys, monkeypatch)
    actual = _capture(retrofit_maintenance, argv, capsys, monkeypatch)
    assert actual == golden


@pytest.mark.parametrize("today", CANDIDATE_DATES)
def test_candidate_retrofit_matches_golden(today, capsys, monkeypatch):
    argv = ["--today", today, "--tasks-dir", str(CANDIDATE_TASKS)]
    golden = _capture(golden_candidate, argv, capsys, monkeypatch)
    actual = _capture(retrofit_candidate, argv, capsys, monkeypatch)
    assert actual == golden


# ==========================================================================
# Recorded sample runs — frozen golden snapshots (format-stability lock)
# ==========================================================================

def test_maintenance_recorded_sample_run(capsys, monkeypatch):
    tasks = RECORDED / "maintenance"
    expected = (RECORDED / "maintenance-output.txt").read_text(encoding="utf-8")
    argv = ["--today", "2026-07-13", "--tasks-dir", str(tasks)]
    golden = _capture(golden_maintenance, argv, capsys, monkeypatch)
    actual = _capture(retrofit_maintenance, argv, capsys, monkeypatch)
    assert actual == golden == expected


def test_candidate_recorded_sample_run(capsys, monkeypatch):
    tasks = RECORDED / "candidate"
    expected = (RECORDED / "candidate-output.txt").read_text(encoding="utf-8")
    argv = ["--today", "2026-07-21", "--tasks-dir", str(tasks)]
    golden = _capture(golden_candidate, argv, capsys, monkeypatch)
    actual = _capture(retrofit_candidate, argv, capsys, monkeypatch)
    assert actual == golden == expected
