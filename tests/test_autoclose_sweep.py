from __future__ import annotations

import shutil
from datetime import datetime
from types import SimpleNamespace
from pathlib import Path
from textwrap import dedent

from coga import autoclose
from coga.config import load_config
from coga.recurring import Template, create_named
from coga.tasks import list_tasks
from coga.ticket import Ticket


ROOT = Path(__file__).resolve().parents[1]
PACKAGED_COGA_OS = ROOT / "src" / "coga" / "resources" / "templates" / "coga"
PACKAGED_SKILL = (
    PACKAGED_COGA_OS / "bootstrap" / "skills" / "coga" / "autoclose" / "sweep"
)
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8", newline="\n")


def test_autoclose_recipe_calls_shared_sweep_loudly(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    # `repo_root` is all the recipe reads before the sweep (to scope the
    # follow-up report); everything else is exercised through the fake sweep.
    cfg = SimpleNamespace(repo_root=tmp_path)
    calls: list[tuple[object, bool]] = []

    def fake_sweep(
        cfg_arg,
        *,
        quiet: bool,
        result: autoclose.AutocloseResult,
        before_close,
    ) -> autoclose.AutocloseResult:
        calls.append((cfg_arg, quiet))
        assert result.closed == []
        assert callable(before_close)
        return result

    monkeypatch.setattr(autoclose, "sweep_merged", fake_sweep)

    assert autoclose.run_autoclose_recipe(cfg, []) == 0
    assert calls == [(cfg, False)]
    assert "[autoclose] no tickets bumped." in capsys.readouterr().out


def test_autoclose_recipe_surfaces_gh_error(monkeypatch, capsys, tmp_path: Path) -> None:
    def boom(*args, **kwargs):
        raise autoclose.GhError("gh: not authenticated")

    monkeypatch.setattr(autoclose, "sweep_merged", boom)

    assert autoclose.run_autoclose_recipe(SimpleNamespace(repo_root=tmp_path), []) == 2
    assert "gh: not authenticated" in capsys.readouterr().err


def test_autoclose_recurring_template_creates_idempotently(tmp_path: Path) -> None:
    coga_os = tmp_path / "coga"
    _write(
        coga_os / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification.slack]
        enabled = false

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(coga_os / "coga.local.toml", 'user = "marc"\n')
    _write(
        coga_os / "contexts" / "coga" / "period-task" / "SKILL.md",
        """
        ---
        name: coga/period-task
        description: period task context
        ---
        Period task.
        """,
    )
    shutil.copytree(
        PACKAGED_COGA_OS / "recurring" / "autoclose-merged",
        coga_os / "recurring" / "autoclose-merged",
    )
    shutil.copytree(
        PACKAGED_COGA_OS / "bootstrap" / "workflows" / "autoclose-merged",
        coga_os / "workflows" / "autoclose-merged",
    )
    shutil.copytree(
        PACKAGED_SKILL,
        coga_os / "skills" / "coga" / "autoclose" / "sweep",
    )

    cfg = load_config(coga_os)
    now = datetime(2026, 6, 11, 8, 30, 0)
    first = create_named(cfg, "autoclose-merged", now=now)
    second = create_named(cfg, "autoclose-merged", now=now)

    assert first.created is True
    assert second.created is False
    refs = list_tasks(cfg)
    assert [(ref.directory, ref.slug, ref.id_slug) for ref in refs] == [
        ("recurring", "autoclose-merged", "recurring/autoclose-merged")
    ]
    # The serviced period is recorded in the repo-global append-only log, not
    # in the template — a co-writer rewriting the blackboard cannot lose it.
    from coga.recurring import serviced_periods

    assert serviced_periods(cfg).get("recurring/autoclose-merged") == "2026-06-11"

    ticket = Ticket.read(refs[0].path / "ticket.md")
    template = Template.load(coga_os / "recurring" / "autoclose-merged")
    entry = template.script_entry_point
    assert entry == coga_os / "recurring" / "autoclose-merged" / "ticket.py"
    # The template's deterministic half is copied into the period task, which
    # is what makes `coga launch` classify that task as a script run.
    assert (refs[0].path / "ticket.py").read_text(encoding="utf-8") == entry.read_text(encoding="utf-8")
    assert "\nscript:" not in (refs[0].path / "ticket.md").read_text(encoding="utf-8")
    assert "\nrecipe:" not in (refs[0].path / "ticket.md").read_text(encoding="utf-8")
    assert ticket.agent == "claude"
    assert ticket.workflow["name"] == "autoclose-merged/sweep"
    assert ticket.workflow["steps"][0]["skills"] == ["coga/autoclose/sweep"]
    assert "coga/period-task" in ticket.contexts
