"""Unit tests for the `[shims.*]` config schema (tier-2 shim, Pass 2).

These exercise `_parse_shims` directly — the schema is the isolated first
piece of the tier-2 shim mechanism (`cli-extension-model/move-command-logic`).
The strict key-check is what enforces the "no worse Typer" guardrail.
"""

from __future__ import annotations

import pytest

from relay.config import ConfigError, Shim, _parse_shims


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
    assert s.draft_if_missing is False
    assert s.validate_after is False
    assert s.sync == ()
    assert s.require_tty is False


def test_parse_shims_none_and_empty() -> None:
    assert _parse_shims(None) == {}
    assert _parse_shims({}) == {}


def test_parse_shims_rejects_unknown_key() -> None:
    # An if-this/else-that key is exactly the "worse Typer" the guardrail forbids.
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
