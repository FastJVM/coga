from __future__ import annotations

import importlib.util
import shutil
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from relay.config import load_config
from relay.recurring import scaffold_named
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


def test_autoclose_live_and_packaged_copies_stay_in_sync() -> None:
    pairs = [
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "ticket.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "ticket.md",
        ),
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "blackboard.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "blackboard.md",
        ),
        (
            LIVE_RELAY_OS / "recurring" / "autoclose-merged" / "log.md",
            PACKAGED_RELAY_OS / "recurring" / "autoclose-merged" / "log.md",
        ),
        (
            LIVE_RELAY_OS / "workflows" / "autoclose-merged" / "sweep.md",
            PACKAGED_RELAY_OS / "workflows" / "autoclose-merged" / "sweep.md",
        ),
        (
            LIVE_RELAY_OS / "skills" / "relay" / "autoclose" / "sweep" / "SKILL.md",
            PACKAGED_SKILL / "SKILL.md",
        ),
        (
            LIVE_RELAY_OS / "skills" / "relay" / "autoclose" / "sweep" / "run.py",
            PACKAGED_SKILL / "run.py",
        ),
    ]

    for live, packaged in pairs:
        assert live.read_text() == packaged.read_text()


def test_autoclose_recurring_template_scaffolds_idempotently(tmp_path: Path) -> None:
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
    first = scaffold_named(cfg, "autoclose-merged", now=now)
    second = scaffold_named(cfg, "autoclose-merged", now=now)

    assert first.created is True
    assert second.created is False
    refs = list_tasks(cfg)
    assert [ref.slug for ref in refs] == ["recurring-autoclose-merged-2026-06-11"]

    ticket = Ticket.read(refs[0].path / "ticket.md")
    assert ticket.mode == "script"
    assert ticket.assignee == "claude"
    assert ticket.workflow["name"] == "autoclose-merged/sweep"
    assert ticket.workflow["steps"][0]["skills"] == ["relay/autoclose/sweep"]
    assert "relay/period-task" in ticket.contexts
