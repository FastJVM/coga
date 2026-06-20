from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from relay.config import load_config
from relay.recurring import create_named
from relay.tasks import list_tasks
from relay.ticket import Ticket


ROOT = Path(__file__).resolve().parents[1]
LIVE_RELAY_OS = ROOT / "relay-os"
PACKAGED_RELAY_OS = ROOT / "src" / "relay" / "resources" / "templates" / "relay-os"
PACKAGED_SKILL = (
    PACKAGED_RELAY_OS / "bootstrap" / "skills" / "relay" / "autoclose" / "sweep"
)


def _load_autoclose_module():
    spec = importlib.util.spec_from_file_location(
        "autoclose_sweep_skill", PACKAGED_SKILL / "run.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


autoclose = _load_autoclose_module()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def test_autoclose_script_calls_shared_sweep_loudly(monkeypatch, capsys) -> None:
    cfg = object()
    calls: list[tuple[object, bool]] = []

    monkeypatch.setattr(autoclose, "load_config", lambda: cfg)

    def fake_sweep(cfg_arg, *, quiet: bool) -> int:
        calls.append((cfg_arg, quiet))
        return 0

    monkeypatch.setattr(autoclose, "auto_bump_merged", fake_sweep)

    assert autoclose.main() == 0
    assert calls == [(cfg, False)]
    assert "[autoclose] no tickets bumped." in capsys.readouterr().out


def test_autoclose_script_surfaces_gh_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(autoclose, "load_config", lambda: object())

    def boom(*args, **kwargs):
        raise autoclose.GhError("gh: not authenticated")

    monkeypatch.setattr(autoclose, "auto_bump_merged", boom)

    assert autoclose.main() == 2
    assert "gh: not authenticated" in capsys.readouterr().err


def _strip_runtime_state(text: str) -> str:
    """Drop the lines a real recurring run mutates into the live copy.

    This repo dogfoods relay, so the live `autoclose-merged` template — which
    doubles as the canonical source mirrored into the packaged templates — gets
    serviced by real `relay recurring` runs. `sync_task_state` then commits that
    runtime state: a `last_serviced_period:` line in the blackboard and
    timestamped `[system] ...` entries in the log. Those are legitimate run
    artifacts, not template drift, so strip them before comparing — what must
    stay in sync is the static template content.
    """
    out = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("last_serviced_period:"):
            continue
        if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} \[", stripped):
            continue
        out.append(line)
    return "".join(out).rstrip("\n")


def test_autoclose_live_and_packaged_copies_stay_in_sync() -> None:
    # (live, packaged, tolerant): tolerant pairs are the files a real recurring
    # run mutates (blackboard's serviced-period line, the log's entries); only
    # their static template content is compared. Everything else is byte-exact.
    pairs = [
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "ticket.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "ticket.md",
            False,
        ),
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "blackboard.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "blackboard.md",
            True,
        ),
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "log.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "log.md",
            True,
        ),
        (
            LIVE_RELAY_OS / "workflows" / "autoclose-merged" / "sweep.md",
            PACKAGED_RELAY_OS / "workflows" / "autoclose-merged" / "sweep.md",
            False,
        ),
        (
            LIVE_RELAY_OS / "skills" / "relay" / "autoclose" / "sweep" / "SKILL.md",
            PACKAGED_SKILL / "SKILL.md",
            False,
        ),
        (
            LIVE_RELAY_OS / "skills" / "relay" / "autoclose" / "sweep" / "run.py",
            PACKAGED_SKILL / "run.py",
            False,
        ),
    ]

    for live, packaged, tolerant in pairs:
        live_text, packaged_text = live.read_text(), packaged.read_text()
        if tolerant:
            live_text = _strip_runtime_state(live_text)
            packaged_text = _strip_runtime_state(packaged_text)
        assert live_text == packaged_text, live


def test_autoclose_recurring_template_creates_idempotently(tmp_path: Path) -> None:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    _write(
        relay_os / "contexts" / "relay" / "period-task" / "SKILL.md",
        """
        ---
        name: relay/period-task
        description: period task context
        ---
        Period task.
        """,
    )
    shutil.copytree(
        LIVE_RELAY_OS / "recurring" / "autoclose-merged",
        relay_os / "recurring" / "autoclose-merged",
    )
    # The live template doubles as the canonical source but is serviced by real
    # `relay recurring` runs in this repo, so its committed blackboard may carry
    # a stale `last_serviced_period:`. Strip it so this test controls its own
    # starting period regardless of dogfooding drift.
    copied_bb = relay_os / "recurring" / "autoclose-merged" / "blackboard.md"
    copied_bb.write_text(_strip_runtime_state(copied_bb.read_text()) + "\n")
    shutil.copytree(
        LIVE_RELAY_OS / "workflows" / "autoclose-merged",
        relay_os / "workflows" / "autoclose-merged",
    )
    shutil.copytree(
        LIVE_RELAY_OS / "skills" / "relay" / "autoclose" / "sweep",
        relay_os / "skills" / "relay" / "autoclose" / "sweep",
    )

    cfg = load_config(relay_os)
    now = datetime(2026, 6, 11, 8, 30, 0)
    first = create_named(cfg, "autoclose-merged", now=now)
    second = create_named(cfg, "autoclose-merged", now=now)

    assert first.created is True
    assert second.created is False
    refs = list_tasks(cfg)
    assert [(ref.directory, ref.slug, ref.id_slug) for ref in refs] == [
        ("recurring", "autoclose-merged", "recurring/autoclose-merged")
    ]
    assert (
        relay_os / "recurring" / "autoclose-merged" / "blackboard.md"
    ).read_text().endswith("last_serviced_period: 2026-06-11\n")

    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.mode == "script"
    assert ticket.assignee == "claude"
    assert ticket.workflow["name"] == "autoclose-merged/sweep"
    assert ticket.workflow["steps"][0]["skills"] == ["relay/autoclose/sweep"]
    assert "relay/period-task" in ticket.contexts
