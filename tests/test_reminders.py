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


def test_notify_defaults_to_normal_channel(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reminders.subprocess,
        "run",
        lambda cmd, *a, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0),
    )
    rc = reminders.notify("repo/x", "hello")
    assert rc == 0
    assert calls == [["coga", "slack", "--task", "repo/x", "--message", "hello"]]
    assert "--important" not in calls[0]


def test_notify_can_opt_into_important(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reminders.subprocess,
        "run",
        lambda cmd, *a, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 7),
    )
    rc = reminders.notify("repo/x", "hi", important=True)
    assert rc == 7
    assert calls[0][-1] == "--important"


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
    # Quiet channel by default now — a sweep opts into important when it matters.
    assert all(k.get("important") is False for _, _, k in posted)


def test_run_notify_important_opt_in_propagates(tmp_path, monkeypatch):
    posted = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(k) or 0)
    reminders.run(
        _ok_sweep("R", ["a"]),
        task_slug="repo/x",
        important=True,
        argv=["--tasks-dir", str(tmp_path), "--notify"],
    )
    assert posted and posted[0].get("important") is True


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


# ==========================================================================
# Admin ack sweep — the monthly Xero-reconcile ack shape
# ==========================================================================
#
# The first ack-based admin reminder to adopt the engine. It is engine-native
# (no golden oracle), so it is verified behaviourally. These tests are what pin
# the deferred period/ack shape: the period is the *prior* calendar month as
# ``YYYY-MM``, and the reminder goes quiet once ``Acked: <period>`` is recorded.

xero_reconcile = _load(
    "xero_reconcile", FIXTURES / "admin" / "xero_reconcile_sweep.py"
)


def _reconcile_tasks_dir(tmp_path, ack: str | None = None) -> Path:
    """A tmp tasks dir holding the single reconcile ticket, optionally pre-acked."""
    tasks = tmp_path / "tasks"
    ticket = tasks / "xero-reconciliation" / "ticket.md"
    ticket.parent.mkdir(parents=True)
    body = (
        "---\nslug: xero-reconciliation\ntitle: Monthly Xero reconciliation\n---\n\n"
        "## Description\nReconcile last month's Xero books, then record the ack.\n\n"
        "<!-- coga:blackboard -->\n"
    )
    if ack is not None:
        body += f"\nAcked: {ack}\n"
    ticket.write_text(body, encoding="utf-8")
    return tasks


def _fires(tasks_dir: Path, today: str) -> bool:
    return bool(xero_reconcile._sweep(date.fromisoformat(today), tasks_dir).alerts)


def test_xero_period_is_prior_month():
    assert xero_reconcile.period_for(date(2026, 8, 1)) == "2026-07"
    assert xero_reconcile.period_for(date(2026, 8, 31)) == "2026-07"
    assert xero_reconcile.period_for(date(2026, 1, 15)) == "2025-12"  # year rollover


def test_xero_unacked_month_fires(tmp_path):
    tasks = _reconcile_tasks_dir(tmp_path, ack=None)
    assert _fires(tasks, "2026-08-15")  # July not acked -> due


def test_xero_ack_of_current_period_suppresses(tmp_path):
    tasks = _reconcile_tasks_dir(tmp_path, ack="2026-07")
    assert not _fires(tasks, "2026-08-15")  # July acked -> quiet


def test_xero_stale_ack_still_fires(tmp_path):
    tasks = _reconcile_tasks_dir(tmp_path, ack="2026-06")  # last month's ack
    assert _fires(tasks, "2026-08-15")  # period is 2026-07, not 2026-06 -> due


def test_xero_ack_roundtrip_defines_the_shape(tmp_path):
    """record_ack(period_for(today)) must silence the very next run.

    The write side (period_for) and the read side (satisfied) producing the same
    string for the same day *is* the shape being correct.
    """
    tasks = _reconcile_tasks_dir(tmp_path, ack=None)
    ticket = tasks / "xero-reconciliation" / "ticket.md"
    today = date(2026, 8, 15)
    assert xero_reconcile._sweep(today, tasks).alerts  # fires first
    reminders.record_ack(ticket, xero_reconcile.period_for(today))
    assert not xero_reconcile._sweep(today, tasks).alerts  # now quiet
    assert reminders.read_ack(ticket) == "2026-07"


def test_xero_quiet_at_rollover_even_if_a_month_was_missed(tmp_path):
    """A skipped month goes quiet at rollover; the new month is what now fires."""
    tasks = _reconcile_tasks_dir(tmp_path, ack=None)  # July never acked
    assert xero_reconcile.period_for(date(2026, 9, 10)) == "2026-08"
    assert _fires(tasks, "2026-09-10")  # asks about August, not the missed July
    reminders.record_ack(tasks / "xero-reconciliation" / "ticket.md", "2026-08")
    assert not _fires(tasks, "2026-09-10")  # acking August silences it


def test_xero_runs_through_the_harness(tmp_path, monkeypatch):
    """End-to-end via run(): --notify posts one alert, to the *normal* channel."""
    tasks = _reconcile_tasks_dir(tmp_path, ack=None)
    posted: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        reminders, "notify", lambda task, msg, **k: posted.append((msg, k)) or 0
    )
    rc = xero_reconcile.main(
        ["--today", "2026-08-15", "--tasks-dir", str(tasks), "--notify"]
    )
    assert rc == 0
    assert len(posted) == 1
    msg, kwargs = posted[0]
    assert "2026-07" in msg
    assert kwargs.get("important") is False  # a routine reconcile stays off coga-important


# ==========================================================================
# Admin query sweeps — the live-source shape (Brex missing receipts / GL)
# ==========================================================================
#
# The query path: satisfied() is a live source query, not a ticket field or an
# ack. Engine-native, so verified behaviourally with an injected fetch (the real
# Brex query is never touched). No window, no ack; fire = the query returns work.
# Both post to the *normal* channel.

brex_receipts = _load(
    "brex_receipts", FIXTURES / "admin" / "brex_missing_receipts_sweep.py"
)
brex_gl = _load("brex_gl", FIXTURES / "admin" / "brex_missing_gl_sweep.py")


def _receipt(module, id="e1", incurred="2026-07-02"):
    return module.Expense(id=id, merchant="Acme", amount="$10.00", incurred=incurred)


def test_brex_receipts_fires_when_source_reports_missing(tmp_path):
    sweep = brex_receipts.build_sweep(fetch=lambda: [_receipt(brex_receipts)])
    result = sweep(date(2026, 7, 15), tmp_path)
    assert result.alerts and "missing a receipt" in result.alerts[0]


def test_brex_receipts_quiet_when_source_is_clean(tmp_path):
    sweep = brex_receipts.build_sweep(fetch=lambda: [])
    assert sweep(date(2026, 7, 15), tmp_path).alerts == []


def test_brex_receipts_one_summary_alert_not_per_expense(tmp_path):
    many = [_receipt(brex_receipts, id=f"e{i}", incurred=f"2026-07-0{i}") for i in (1, 2, 3)]
    sweep = brex_receipts.build_sweep(fetch=lambda: many)
    alerts = sweep(date(2026, 7, 15), tmp_path).alerts
    assert len(alerts) == 1 and "3 Brex expense(s)" in alerts[0]


def test_brex_receipts_posts_to_normal_channel_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(
        brex_receipts, "fetch_missing_receipts", lambda: [_receipt(brex_receipts)]
    )
    posted: list[dict] = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(k) or 0)
    rc = brex_receipts.main(
        ["--today", "2026-07-15", "--tasks-dir", str(tmp_path), "--notify"]
    )
    assert rc == 0
    assert len(posted) == 1 and posted[0].get("important") is False


def test_brex_gl_fires_when_source_reports_missing(tmp_path):
    sweep = brex_gl.build_sweep(fetch=lambda: [_receipt(brex_gl)])
    result = sweep(date(2026, 7, 15), tmp_path)
    assert result.alerts and "GL code" in result.alerts[0]


def test_brex_gl_quiet_when_source_is_clean(tmp_path):
    assert brex_gl.build_sweep(fetch=lambda: [])(date(2026, 7, 15), tmp_path).alerts == []


def test_brex_gl_posts_to_normal_channel_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(brex_gl, "fetch_missing_gl", lambda: [_receipt(brex_gl)])
    posted: list[dict] = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(k) or 0)
    rc = brex_gl.main(["--today", "2026-07-15", "--tasks-dir", str(tmp_path), "--notify"])
    assert rc == 0
    assert len(posted) == 1 and posted[0].get("important") is False
