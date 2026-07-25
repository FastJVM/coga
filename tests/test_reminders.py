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
import json
import re
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
# ack. No window, no ack; fire = the query returns work. Both post to the
# *normal* channel.
#
# These sweeps parse raw /v3/accounting/records records, so the tests feed them
# real ones: `recorded/brex/record-shape.json` is a genuine record captured
# 2026-07-25, and the recorded runs supply real dates, amounts and counts (names
# and ids aliased — see that directory's README). The Brex query itself is never
# touched; `fetch` is injected.

brex_receipts = _load(
    "brex_receipts", FIXTURES / "admin" / "brex_missing_receipts_sweep.py"
)
brex_gl = _load("brex_gl", FIXTURES / "admin" / "brex_missing_gl_sweep.py")

RECORDED_BREX = FIXTURES / "recorded" / "brex"


def _recorded(name: str):
    return json.loads((RECORDED_BREX / name).read_text(encoding="utf-8"))


def _record(
    *,
    posted_at="2026-07-02T12:00:00.000Z",
    amount=100.0,
    currency="USD",
    vendor="Vendor A",
    cardholder="Cardholder One",
    type="CARD_EXPENSE_POST",
    receipts=(),
    gl_set=True,
    line_items=None,
    source_id="expense_000000000000000000000001",
):
    """A Brex accounting record in the real v3 shape.

    Built from the same structure as `record-shape.json` so a test record and a
    recorded one exercise identical parsing paths.
    """
    if line_items is None:
        gl_value = "efo_0000000000000000000001" if gl_set else None
        line_items = [
            {
                "id": "accrli_000000000000000000000001",
                "type": "DEBIT",
                "amount": {"amount": amount, "currency": currency},
                "accounting_field_values": [
                    {
                        "brex_field_id": "extended_field_00000000000000000001",
                        "remote_field_id": "GL_ACCOUNT",
                        "field_name": "GL Account",
                        "brex_field_value_id": gl_value,
                        "field_value_name": "7500 Other G&A" if gl_set else None,
                        "type": "IDENTIFIER",
                    }
                ],
            },
            {
                "id": "accrli_000000000000000000000002",
                "type": "CREDIT",
                "amount": {"amount": amount, "currency": currency},
                "accounting_field_values": [],
            },
        ]
    return {
        "id": "accr_000000000000000000000001",
        "source_id": source_id,
        "type": type,
        "posted_at": posted_at,
        "amount": {"amount": amount, "currency": currency},
        "receipts": list(receipts),
        "review_status": "PREPARE",
        # Trailing whitespace is a real Brex quirk; the sweeps must collapse it.
        "user": {"first_name": cardholder.split()[0] + " ", "last_name": cardholder.split()[1] + " "},
        "vendor": {"name": vendor},
        "line_items": line_items,
    }


def _brex_ticket_dir(base: Path, slug: str, ack: str | None = None) -> Path:
    tasks = base / "tasks"
    ticket = tasks / slug / "ticket.md"
    ticket.parent.mkdir(parents=True)
    body = f"---\nslug: {slug}\n---\n\n## Description\nx\n\n<!-- coga:blackboard -->\n"
    if ack is not None:
        body += f"\nAcked: {ack}\n"
    ticket.write_text(body, encoding="utf-8")
    return tasks


def _recorded_amount(row: dict) -> float:
    """The row's amount as a float.

    The two recorded runs render amounts differently — the GL run as
    `$74.99 USD`, the receipts run as `USD 200.00` — because they come from two
    scripts with separate formatters. Pull the number out of either.
    """
    if "amount_value" in row:
        return float(row["amount_value"])
    match = re.search(r"[\d,]+\.\d{2}", row["amount"])
    assert match, f"no amount in {row['amount']!r}"
    return float(match.group().replace(",", ""))


def _records_from_recorded(rows: list[dict], *, gl_set=True, receipts=()) -> list[dict]:
    """Recorded rows re-expressed as raw records the sweeps can parse."""
    return [
        _record(
            posted_at=r["posted_at"],
            amount=_recorded_amount(r),
            vendor=r["vendor"],
            cardholder=r["user"],
            source_id=r["source_id"],
            gl_set=gl_set,
            receipts=receipts,
        )
        for r in rows
    ]


# --- the recorded contract ---------------------------------------------------
#
# The bug these guard against: an earlier draft filtered on an `incurred` field
# that /v3/accounting/records does not return, and the stubbed query meant no
# test could catch it.


def test_recorded_record_carries_no_purchase_date():
    """v3 accounting records have no purchase date — only settlement dates.

    If Brex ever adds one, this fails and the high-water ack should be revisited
    (posted_at lags the purchase, which is why late-month charges roll forward).
    """
    record = _recorded("record-shape.json")
    date_fields = {k for k, v in record.items() if isinstance(v, str) and _looks_iso(v)}
    # All three are settlement/bookkeeping stamps. None records when the card
    # was actually swiped, which is why the high-water ack keys on posted_at.
    assert date_fields == {"posted_at", "updated_at", "erp_posting_date"}, date_fields
    assert "incurred" not in record
    assert "purchased_at" not in record


def _looks_iso(value: str) -> bool:
    return len(value) >= 20 and value[4] == "-" and value[7] == "-" and "T" in value


def test_recorded_record_has_gl_set_on_the_debit_line():
    """The recorded record has a GL assigned, so the probe must not flag it."""
    record = _recorded("record-shape.json")
    assert brex_gl.is_missing_gl(record) is False
    debit = next(li for li in record["line_items"] if li["type"] == "DEBIT")
    gl = next(f for f in debit["accounting_field_values"] if f["remote_field_id"] == "GL_ACCOUNT")
    assert gl["brex_field_value_id"] is not None
    # The CREDIT line is the card-liability account and carries no GL fields.
    credit = next(li for li in record["line_items"] if li["type"] == "CREDIT")
    assert credit["accounting_field_values"] == []


def test_recorded_receipts_run_reproduces_its_pile(tmp_path):
    """The 14 expenses the live 2026 run found all surface with no ack."""
    rows = _recorded("receipts-missing.json")
    assert len(rows) == 14
    sweep = brex_receipts.build_sweep(fetch=lambda: _records_from_recorded(rows))
    result = sweep(date(2026, 7, 25), tmp_path)
    assert "14 expense(s) missing a receipt total." in result.report
    assert result.alerts and "14 Brex expense(s)" in result.alerts[0]
    # Oldest in the recorded pile is 2026-01-09.
    assert "2026-01-09" in result.alerts[0]


def test_recorded_receipts_run_high_water_ack_splits_the_real_pile(tmp_path):
    """Acking through the real pile's midpoint mutes exactly the older half."""
    rows = _recorded("receipts-missing.json")
    tasks = _brex_ticket_dir(tmp_path, "brex-missing-receipts", ack="2026-03-31")
    sweep = brex_receipts.build_sweep(fetch=lambda: _records_from_recorded(rows))
    result = sweep(date(2026, 7, 25), tasks)
    expected = sum(1 for r in rows if r["posted_at"][:10] > "2026-03-31")
    assert 0 < expected < len(rows)  # the recorded pile really does straddle it
    assert f"{expected} to act on:" in result.report
    assert f"{len(rows) - expected} acknowledged through 2026-03-31." in result.report


def test_recorded_gl_run_reproduces_its_pile(tmp_path):
    """The 11 charges the live GL run found all surface with no ack."""
    rows = _recorded("gl-missing.json")
    assert len(rows) == 11
    records = _records_from_recorded(rows, gl_set=False)
    sweep = brex_gl.build_sweep(fetch=lambda: records)
    result = sweep(date(2026, 7, 25), tmp_path)
    assert "11 expense(s) missing a GL code total." in result.report
    assert result.alerts and "11 Brex expense(s)" in result.alerts[0]


# --- the query contract: what counts as owing a receipt / a GL code ----------


def test_receipts_threshold_excludes_forty_and_under(tmp_path):
    """Manycore policy: $40 and under needs no receipt. The boundary is exact."""
    sweep = brex_receipts.build_sweep(
        fetch=lambda: [_record(amount=40.0), _record(amount=40.01)]
    )
    assert "1 expense(s) missing a receipt total." in sweep(date(2026, 7, 25), tmp_path).report


def test_receipts_only_posted_purchases_need_one(tmp_path):
    """Refunds and adjustments are not purchases."""
    sweep = brex_receipts.build_sweep(
        fetch=lambda: [_record(type="CARD_EXPENSE_REFUND"), _record(type="CARD_EXPENSE_POST")]
    )
    assert "1 expense(s) missing a receipt total." in sweep(date(2026, 7, 25), tmp_path).report


def test_receipts_attached_receipt_clears_the_record(tmp_path):
    sweep = brex_receipts.build_sweep(
        fetch=lambda: [_record(receipts=[{"download_uris": ["https://example.invalid/r"]}])]
    )
    assert sweep(date(2026, 7, 25), tmp_path).alerts == []


def test_gl_probe_flags_unset_debit_gl(tmp_path):
    sweep = brex_gl.build_sweep(fetch=lambda: [_record(gl_set=False), _record(gl_set=True)])
    assert "1 expense(s) missing a GL code total." in sweep(date(2026, 7, 25), tmp_path).report


@pytest.mark.parametrize(
    "line_items",
    [
        pytest.param([], id="no-line-items"),
        pytest.param([{"type": "CREDIT", "accounting_field_values": []}], id="no-debit-line"),
        pytest.param([{"type": "DEBIT", "accounting_field_values": []}], id="no-accounting-fields"),
        pytest.param(
            [{"type": "DEBIT", "accounting_field_values": [{"remote_field_id": "DEPARTMENT"}]}],
            id="no-gl-field",
        ),
    ],
)
def test_gl_probe_fails_safe_on_malformed_records(line_items):
    """A record the probe cannot read is surfaced, never silently dropped."""
    assert brex_gl.is_missing_gl(_record(line_items=line_items)) is True


def test_gl_horizon_excludes_closed_fiscal_years(tmp_path):
    """Missing GL on a closed year is not actionable — it would reopen the books."""
    sweep = brex_gl.build_sweep(
        fetch=lambda: [
            _record(posted_at="2025-12-31T23:00:00.000Z", gl_set=False),  # closed year
            _record(posted_at="2026-06-01T12:00:00.000Z", gl_set=False),  # open year
        ]
    )
    assert "1 expense(s) missing a GL code total." in sweep(date(2026, 7, 25), tmp_path).report


def test_gl_horizon_is_company_local_new_year(tmp_path):
    """The cutoff is Jan 1 in America/Los_Angeles, not UTC.

    A charge settling 2026-01-01T04:00Z is 2025-12-31 20:00 in LA — still the
    closed year — so it must not surface.
    """
    cutoff = brex_gl.fiscal_year_cutoff(date(2026, 7, 25))
    assert cutoff == "2026-01-01T08:00:00Z"
    sweep = brex_gl.build_sweep(
        fetch=lambda: [_record(posted_at="2026-01-01T04:00:00.000Z", gl_set=False)]
    )
    assert sweep(date(2026, 7, 25), tmp_path).alerts == []


def test_gl_horizon_follows_today_not_import_time(tmp_path):
    """--today drives the horizon, so a dated run is reproducible."""
    assert brex_gl.fiscal_year_cutoff(date(2025, 3, 1)) == "2025-01-01T08:00:00Z"
    assert brex_gl.fiscal_year_cutoff(date(2026, 3, 1)) == "2026-01-01T08:00:00Z"


def test_cardholder_name_collapses_brex_trailing_whitespace():
    record = _recorded("record-shape.json")
    name = brex_receipts.cardholder_name(record)
    assert name == name.strip() and "  " not in name


def test_brex_receipts_fires_when_source_reports_missing(tmp_path):
    sweep = brex_receipts.build_sweep(fetch=lambda: [_record()])
    result = sweep(date(2026, 7, 15), tmp_path)
    assert result.alerts and "missing a receipt" in result.alerts[0]


def test_brex_receipts_quiet_when_source_is_clean(tmp_path):
    sweep = brex_receipts.build_sweep(fetch=lambda: [])
    assert sweep(date(2026, 7, 15), tmp_path).alerts == []


def test_brex_receipts_one_summary_alert_not_per_expense(tmp_path):
    many = [_record(posted_at=f"2026-07-0{i}T12:00:00.000Z") for i in (1, 2, 3)]
    sweep = brex_receipts.build_sweep(fetch=lambda: many)
    alerts = sweep(date(2026, 7, 15), tmp_path).alerts
    assert len(alerts) == 1 and "3 Brex expense(s)" in alerts[0]


def test_brex_receipts_posts_to_normal_channel_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(brex_receipts, "fetch_card_records", lambda: [_record()])
    posted: list[dict] = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(k) or 0)
    rc = brex_receipts.main(
        ["--today", "2026-07-15", "--tasks-dir", str(tmp_path), "--notify"]
    )
    assert rc == 0
    assert len(posted) == 1 and posted[0].get("important") is False


def test_brex_gl_fires_when_source_reports_missing(tmp_path):
    sweep = brex_gl.build_sweep(fetch=lambda: [_record(gl_set=False)])
    result = sweep(date(2026, 7, 15), tmp_path)
    assert result.alerts and "GL code" in result.alerts[0]


def test_brex_gl_quiet_when_source_is_clean(tmp_path):
    assert brex_gl.build_sweep(fetch=lambda: [])(date(2026, 7, 15), tmp_path).alerts == []


def test_brex_gl_posts_to_normal_channel_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(brex_gl, "fetch_card_records", lambda: [_record(gl_set=False)])
    posted: list[dict] = []
    monkeypatch.setattr(reminders, "notify", lambda task, msg, **k: posted.append(k) or 0)
    rc = brex_gl.main(["--today", "2026-07-15", "--tasks-dir", str(tmp_path), "--notify"])
    assert rc == 0
    assert len(posted) == 1 and posted[0].get("important") is False


# --- high-water ack: acknowledge the backlog, alert only on newer gaps --------
#
# Missing receipts/GL are a running pile, not a per-period obligation, so the ack
# is a date high-water mark (Acked: YYYY-MM-DD): the sweep flags only records
# posted *after* it. Cadence-independent — the monthly run just shows what's new
# since the last ack. No ack -> the whole pile; addressing everything -> quiet.


def test_brex_receipts_ack_mutes_old_pile_but_new_fires(tmp_path):
    tasks = _brex_ticket_dir(tmp_path, "brex-missing-receipts", ack="2026-07-10")
    old = _record(posted_at="2026-06-15T12:00:00.000Z")  # <= ack -> muted
    new = _record(posted_at="2026-07-20T12:00:00.000Z")  # >  ack -> flagged
    alerts = brex_receipts.build_sweep(fetch=lambda: [old, new])(date(2026, 8, 1), tasks).alerts
    assert len(alerts) == 1 and "1 Brex expense(s)" in alerts[0]


def test_brex_receipts_ack_through_whole_pile_goes_quiet(tmp_path):
    tasks = _brex_ticket_dir(tmp_path, "brex-missing-receipts", ack="2026-07-31")
    pile = [_record(posted_at=f"2026-07-0{i}T12:00:00.000Z") for i in (1, 2, 3)]
    assert brex_receipts.build_sweep(fetch=lambda: pile)(date(2026, 8, 1), tasks).alerts == []


def test_brex_receipts_ack_roundtrip(tmp_path):
    tasks = _brex_ticket_dir(tmp_path, "brex-missing-receipts", ack=None)
    ticket = tasks / "brex-missing-receipts" / "ticket.md"
    pile = [_record(posted_at="2026-07-02T12:00:00.000Z")]
    fires = brex_receipts.build_sweep(fetch=lambda: pile)
    assert fires(date(2026, 7, 15), tasks).alerts           # backlog fires
    reminders.record_ack(ticket, "2026-07-15")              # draw the line at today
    assert fires(date(2026, 7, 16), tasks).alerts == []     # backlog now muted
    later = pile + [_record(posted_at="2026-07-20T12:00:00.000Z")]
    assert brex_receipts.build_sweep(fetch=lambda: later)(date(2026, 8, 1), tasks).alerts  # new gap fires


def test_brex_gl_self_clears_without_ack_but_ack_is_available(tmp_path):
    # Usually GL just self-clears when the pile empties — no ack needed:
    clean = _brex_ticket_dir(tmp_path / "clean", "brex-missing-gl", ack=None)
    assert brex_gl.build_sweep(fetch=lambda: [])(date(2026, 8, 1), clean).alerts == []
    # ...but the same ack escape hatch is there for a deferred batch:
    acked = _brex_ticket_dir(tmp_path / "acked", "brex-missing-gl", ack="2026-07-31")
    pile = [_record(posted_at="2026-07-05T12:00:00.000Z", gl_set=False)]
    assert brex_gl.build_sweep(fetch=lambda: pile)(date(2026, 8, 1), acked).alerts == []
