"""Tests for the tier-2 shim mechanism (`cli-extension-model/move-command-logic`).

Two layers:
  * `_parse_shims` — the `[shims.*]` config schema (Piece 1).
  * `resolve_shim_target` / `run_shim` — the around-hook dispatch (Piece 2),
    one test per launch situation: bare / new / existing / draft-off / tty.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from conftest import seed_direct_body_workflow
from relay.config import ConfigError, Shim, _parse_shims, load_config
from relay.commands.shim import resolve_shim_target, run_shim
from relay.tasks import TaskNotFoundError


# --------------------------------------------------------------------------- #
# Piece 1 — the [shims.*] config schema
# --------------------------------------------------------------------------- #

def test_parse_shims_valid_full() -> None:
    raw = {
        "ticket": {
            "launch": "bootstrap/ticket",
            "draft_if_missing": True,
            "validate_after": True,
            "sync": ["tasks", "contexts", "skills"],
            "require_tty": True,
        }
    }
    assert _parse_shims(raw) == {
        "ticket": Shim(
            name="ticket",
            launch="bootstrap/ticket",
            draft_if_missing=True,
            validate_after=True,
            sync=("tasks", "contexts", "skills"),
            require_tty=True,
        )
    }


def test_parse_shims_defaults_when_only_launch() -> None:
    s = _parse_shims({"x": {"launch": "bootstrap/x"}})["x"]
    assert (s.draft_if_missing, s.validate_after, s.sync, s.require_tty) == (
        False,
        False,
        (),
        False,
    )


def test_parse_shims_none_and_empty() -> None:
    assert _parse_shims(None) == {}
    assert _parse_shims({}) == {}


def test_parse_shims_rejects_unknown_key() -> None:
    with pytest.raises(ConfigError, match="unsupported keys"):
        _parse_shims({"t": {"launch": "x", "if_arg_matches": "y"}})


def test_parse_shims_requires_non_empty_launch() -> None:
    with pytest.raises(ConfigError, match="launch must be a non-empty string"):
        _parse_shims({"t": {"draft_if_missing": True}})
    with pytest.raises(ConfigError, match="launch must be a non-empty string"):
        _parse_shims({"t": {"launch": "  "}})


def test_parse_shims_rejects_bad_sync() -> None:
    with pytest.raises(ConfigError, match="sync must be a list of strings"):
        _parse_shims({"t": {"launch": "x", "sync": "tasks"}})
    with pytest.raises(ConfigError, match="sync must be a list of strings"):
        _parse_shims({"t": {"launch": "x", "sync": ["tasks", 3]}})


def test_parse_shims_rejects_non_bool_flag() -> None:
    with pytest.raises(ConfigError, match="draft_if_missing must be a boolean"):
        _parse_shims({"t": {"launch": "x", "draft_if_missing": "yes"}})


def test_parse_shims_rejects_non_table_entry() -> None:
    with pytest.raises(ConfigError, match=r"\[shims.t\] must be a table"):
        _parse_shims({"t": "bootstrap/t"})


# --------------------------------------------------------------------------- #
# Piece 2 — the around-hook dispatch
# --------------------------------------------------------------------------- #

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [shims.demo]
        launch = "bootstrap/demo"
        draft_if_missing = true

        [shims.strict]
        launch = "bootstrap/demo"
        draft_if_missing = false

        [shims.tty]
        launch = "bootstrap/demo"
        require_tty = true
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "marc"\n')
    _write(
        relay_os / "bootstrap" / "demo" / "ticket.md",
        """
        ---
        title: Demo shim
        mode: interactive
        assignee: claude
        ---

        ## Description

        Demo bootstrap shim for shim-dispatch tests.
        """,
    )
    seed_direct_body_workflow(relay_os)
    monkeypatch.chdir(relay_os)
    return relay_os


def _mock_launch(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the real spawn with a recorder; returns the list of launched targets."""
    launched: list[str] = []
    monkeypatch.setattr(
        "relay.commands.launch.launch",
        lambda task, **kw: launched.append(task),
    )
    return launched


# --- resolve_shim_target: the bare/new/existing decision (no launch) --------- #

def test_resolve_bare_launches_the_shim_target(repo: Path) -> None:
    cfg = load_config()
    res = resolve_shim_target(cfg, cfg.shims["demo"], None)
    assert res.kind == "bare"
    assert res.target == "bootstrap/demo"
    assert res.task_ref is None


def test_resolve_new_creates_a_draft_from_the_arg(repo: Path) -> None:
    cfg = load_config()
    res = resolve_shim_target(cfg, cfg.shims["demo"], "My New Thing")
    assert res.kind == "new"
    assert res.task_ref is not None
    assert (repo / "tasks" / res.task_ref.slug / "ticket.md").exists()
    assert res.target == res.task_ref.id_slug


def test_resolve_existing_does_not_create_a_draft(repo: Path) -> None:
    cfg = load_config()
    created = resolve_shim_target(cfg, cfg.shims["demo"], "Existing Thing")
    slug = created.task_ref.slug

    cfg2 = load_config()
    res = resolve_shim_target(cfg2, cfg2.shims["demo"], slug)
    assert res.kind == "existing"
    assert res.task_ref.slug == slug


def test_resolve_unknown_arg_errors_when_draft_if_missing_off(repo: Path) -> None:
    cfg = load_config()
    with pytest.raises(TaskNotFoundError, match="does not"):
        resolve_shim_target(cfg, cfg.shims["strict"], "nonexistent-thing")


# --- run_shim: the full around-hook, with the spawn mocked ------------------- #

def test_run_shim_bare_launches_the_bootstrap_shim(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = _mock_launch(monkeypatch)
    cfg = load_config()
    code = run_shim(cfg, cfg.shims["demo"], [])
    assert code == 0
    assert launched == ["bootstrap/demo"]


def test_run_shim_new_launches_the_created_draft(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = _mock_launch(monkeypatch)
    cfg = load_config()
    code = run_shim(cfg, cfg.shims["demo"], ["My Thing"])
    assert code == 0
    assert len(launched) == 1
    assert (repo / "tasks" / launched[0] / "ticket.md").exists()


def test_run_shim_require_tty_bails_without_a_terminal(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("relay.commands.shim._has_tty", lambda: False)
    launched = _mock_launch(monkeypatch)
    cfg = load_config()
    code = run_shim(cfg, cfg.shims["tty"], [])
    assert code == 2
    assert launched == []  # bailed before launch
