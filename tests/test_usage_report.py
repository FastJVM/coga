"""The weekly agent-usage report beside `coga/recurring/usage-report/`.

The report is ticket-owned deterministic work at the edge, not a packaged
template, so unlike `test_recurring_shims.py` this suite reads the *live*
`coga/recurring/usage-report/` directory: it is the only copy. The end-to-end
run still happens against a copy of the seeded `example/` repo.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent
from types import ModuleType

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.launch_script import SCRIPT_ENTRY_POINT
from coga.recurring import create_named
from coga.tasks import read_ticket
from coga.usage import UsageRecord, append_record


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "example"
TEMPLATE = REPO_ROOT / "coga" / "recurring" / "usage-report"
WORKFLOW = REPO_ROOT / "coga" / "workflows" / "usage-report" / "post.md"
SKILL = REPO_ROOT / "coga" / "skills" / "coga" / "usage-report" / "post" / "SKILL.md"


def _load_report() -> ModuleType:
    """Import `report.py` by path: its directory name is not an identifier."""
    spec = importlib.util.spec_from_file_location(
        "usage_report", TEMPLATE / "report.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: a dataclass resolves its postponed annotations
    # through `sys.modules[cls.__module__]`.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


report = _load_report()


def _record(
    ts: str,
    *,
    model: str | None = "claude-opus-5",
    tokens: tuple[int, int, int, int] | None = (1, 2, 3, 4),
) -> UsageRecord:
    """A usage record ending at `ts`; `tokens=None` is a `usage_status: unknown` session."""
    input_tokens, cache_write, cache_read, output = tokens or (None,) * 4
    return UsageRecord(
        ts=ts,
        title="Work",
        slug="work",
        step="implement",
        agent="claude",
        cli="claude",
        provider="anthropic",
        model=model,
        session_id="abc",
        input_tokens=input_tokens,
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cache_read,
        output_tokens=output,
        usage_status="ok" if tokens else "unknown",
    )


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        # Monday: the week that ended at 00:00 today.
        (date(2026, 9, 21), (date(2026, 9, 14), date(2026, 9, 21))),
        # Mid-week and Sunday both still report the previous Mon–Sun week.
        (date(2026, 9, 16), (date(2026, 9, 7), date(2026, 9, 14))),
        (date(2026, 9, 20), (date(2026, 9, 7), date(2026, 9, 14))),
    ],
)
def test_default_window_is_the_last_completed_iso_week(
    today: date, expected: tuple[date, date]
) -> None:
    assert report.default_window(today) == expected


def test_window_is_half_open_in_utc() -> None:
    """`since` 00:00 is in; `until` 00:00 is out; the instant before it is in."""
    since, until = date(2026, 8, 31), date(2026, 9, 7)
    records = [
        _record("2026-08-30T23:59:59Z"),
        _record("2026-08-31T00:00:00Z"),
        _record("2026-09-06T23:59:59.999999Z"),
        _record("2026-09-07T00:00:00Z"),
    ]

    result = report.build_report(records, since, until)

    assert result.sessions == 2
    assert result.total_tokens == 20


def test_build_report_refuses_an_inverted_window() -> None:
    with pytest.raises(ValueError):
        report.build_report([], date(2026, 9, 7), date(2026, 9, 7))


def test_render_keeps_every_model_bucket_and_states_the_floor() -> None:
    records = [
        _record("2026-09-01T10:00:00Z", tokens=(1_100_000, 2_000_000, 300_000_000, 9_100_000)),
        _record("2026-09-02T10:00:00Z", model="gpt-5.6-sol", tokens=(0, 0, 140_200_000, 0)),
        _record("2026-09-03T10:00:00Z", model="<synthetic>", tokens=(0, 0, 500, 0)),
        _record("2026-09-04T10:00:00Z", model=None, tokens=None),
        _record("2026-09-05T10:00:00Z", model=None, tokens=None),
    ]

    result = report.build_report(records, date(2026, 8, 31), date(2026, 9, 7))

    assert result.unknown_sessions == 2
    # Largest first; the null-model and synthetic buckets are rows, not drops.
    assert result.models == (
        ("claude-opus-5", 312_200_000),
        ("gpt-5.6-sol", 140_200_000),
        ("<synthetic>", 500),
        ("(unknown)", 0),
    )
    assert report.render(result) == dedent(
        """\
        Agent usage — week of 2026-08-31 (Mon–Sun)
        452.4M tokens across 5 sessions (2 sessions have unknown counts, so this is a floor)
          input 1.1M · cache write 2.0M · cache read 440.2M · output 9.1M
          claude-opus-5  312.2M
          gpt-5.6-sol    140.2M
          <synthetic>       500
          (unknown)           0"""
    )


def test_render_omits_the_floor_caveat_when_every_session_is_counted() -> None:
    result = report.build_report(
        [_record("2026-09-01T10:00:00Z")], date(2026, 8, 31), date(2026, 9, 7)
    )

    assert report.render(result).splitlines()[1] == "10 tokens across 1 session"


def test_render_names_a_window_that_is_not_a_calendar_week() -> None:
    result = report.build_report(
        [_record("2026-09-01T10:00:00Z")], date(2026, 9, 1), date(2026, 9, 3)
    )

    assert report.render(result).splitlines()[0] == (
        "Agent usage — 2026-09-01 to 2026-09-03 (UTC, end exclusive)"
    )


def test_empty_window_still_renders_and_says_so() -> None:
    result = report.build_report([], date(2026, 8, 31), date(2026, 9, 7))

    assert result.sessions == 0
    assert report.render(result) == (
        "Agent usage — week of 2026-08-31 (Mon–Sun)\n"
        "No Coga-launched sessions recorded in this window."
    )


@pytest.fixture
def coga_os(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal Coga OS root holding two usage records a week apart."""
    root = tmp_path / "coga"
    root.mkdir()
    (root / "coga.toml").write_text(
        'version = 1\n[agents.claude]\ncli = "claude"\nfile = "CLAUDE.md"\n'
    )
    (root / "coga.local.toml").write_text('user = "marc"\n')
    cfg = load_config(root)
    append_record(cfg, _record("2026-09-01T10:00:00Z"))
    append_record(cfg, _record("2026-09-08T10:00:00Z"))
    monkeypatch.chdir(root)
    return root


def test_main_prints_the_window_and_writes_nothing(
    coga_os: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (coga_os / "log.md").read_bytes()

    code = report.main(["--since", "2026-08-31", "--until", "2026-09-07"])

    assert code == 0
    assert capsys.readouterr().out.splitlines()[1] == "10 tokens across 1 session"
    assert (coga_os / "log.md").read_bytes() == before


def test_main_json_carries_the_report_fields(
    coga_os: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = report.main(["--since", "2026-08-31", "--until", "2026-09-14", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["since"] == "2026-08-31"
    assert payload["until"] == "2026-09-14"
    assert payload["sessions"] == 2
    assert payload["total_tokens"] == 20
    assert payload["models"] == [{"model": "claude-opus-5", "total_tokens": 20}]


def test_main_renders_without_a_local_user(
    coga_os: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ad hoc rendering is read-only, so like `coga usage` it must work in a
    fresh clone that has no `coga.local.toml` user yet."""
    (coga_os / "coga.local.toml").unlink()

    code = report.main(["--since", "2026-08-31", "--until", "2026-09-07"])

    assert code == 0
    assert capsys.readouterr().out.splitlines()[1] == "10 tokens across 1 session"


def test_main_rejects_an_inverted_window(coga_os: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        report.main(["--since", "2026-09-07", "--until", "2026-09-07"])

    assert excinfo.value.code == 2


def test_shim_posts_once_on_the_important_route_and_bumps_through_the_cli() -> None:
    """The shim's contract, read structurally so reformatting cannot retire it.

    It reaches `report.py` through `COGA_COGA_OS_ROOT` (only `ticket.py` is
    copied into the period task), posts exactly once with `important=True` and
    `fatal=False`, and completes the step by subprocessing the CLI — calling
    the Typer command in-process would pass `OptionInfo` sentinels.
    """
    script = TEMPLATE / SCRIPT_ENTRY_POINT
    tree = ast.parse(script.read_text(), filename=str(script))

    imported: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module != "__future__":
            assert node.module is not None
            for alias in node.names:
                imported[alias.asname or alias.name] = node.module
    assert imported == {
        "load_config": "coga.config",
        "post": "coga.notification",
        "Path": "pathlib",
        "datetime": "datetime",
        "timezone": "datetime",
    }
    assert "COGA_COGA_OS_ROOT" in script.read_text()

    posts = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "post"
    ]
    (call,) = posts
    keywords = {kw.arg: kw.value for kw in call.keywords}
    assert isinstance(keywords["important"], ast.Constant) and keywords["important"].value is True
    assert isinstance(keywords["fatal"], ast.Constant) and keywords["fatal"].value is False

    runs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    (call,) = runs
    (argv,) = call.args
    assert isinstance(argv, ast.List)
    assert [
        element.value for element in argv.elts[1:4] if isinstance(element, ast.Constant)
    ] == ["-m", "coga.cli", "bump"]
    slug = argv.elts[4]
    assert isinstance(slug, ast.Subscript) and isinstance(slug.slice, ast.Constant)
    assert slug.slice.value == "COGA_TASK_SLUG"


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the seeded example repo (see `test_recurring_shims`)."""
    dest = tmp_path / "example"
    shutil.copytree(
        EXAMPLE,
        dest,
        ignore=shutil.ignore_patterns(".claude", ".codex", ".git", ".venv*", "venv"),
        ignore_dangling_symlinks=True,
    )
    monkeypatch.chdir(dest / "coga")
    return dest / "coga"


def test_period_task_renders_last_week_from_the_template_and_closes_its_step(
    seeded: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """End-to-end: materialize the period task from the live template and launch.

    `_create_at_slug` copies only `ticket.py`, so the run proves the shim finds
    `report.py` through `COGA_COGA_OS_ROOT` rather than beside itself. The
    seeded repo selects no notification channel, which is the stub: `post`
    echoes the message it would have sent to stderr, where `capfd` reads it
    from the subprocess, and the shim's own `coga bump` closes the step.
    """
    shutil.copytree(TEMPLATE, seeded / "recurring" / "usage-report")
    shutil.copy(WORKFLOW, _mkdir(seeded / "workflows" / "usage-report") / "post.md")
    # Period creation resolves the step's skill, so the live skill rides along.
    shutil.copy(SKILL, _mkdir(seeded / "skills" / "coga" / "usage-report" / "post") / "SKILL.md")

    cfg = load_config(seeded)
    since, until = report.default_window(datetime.now(timezone.utc).date())
    inside = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
    stamp = lambda dt: dt.isoformat().replace("+00:00", "Z")  # noqa: E731
    records = [
        _record(stamp(inside + timedelta(days=2)), tokens=(10, 20, 30, 40)),
        _record(stamp(inside + timedelta(days=3)), model=None, tokens=None),
        # The next week's first instant: outside the half-open window.
        _record(stamp(inside + timedelta(days=7))),
    ]
    for record in records:
        append_record(cfg, record)
    expected = report.render(report.build_report(records, since, until))
    assert expected.splitlines()[1] == (
        "100 tokens across 2 sessions (1 session has unknown counts, so this is a floor)"
    )

    outcome = create_named(cfg, "usage-report")
    ref = outcome.ref
    assert outcome.created is True
    assert sorted(path.name for path in ref.task_dir.iterdir()) == sorted(
        ("ticket.md", SCRIPT_ENTRY_POINT)
    )

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    assert read_ticket(ref).status == "done"
    stderr = capfd.readouterr().err
    assert stderr.count(expected) == 1
    assert "no channels configured: " + expected.splitlines()[0] in stderr


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
