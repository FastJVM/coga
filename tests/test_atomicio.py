"""Tests for atomic state-file writes (relay.atomicio + its call sites)."""

from __future__ import annotations

import os
import stat

import pytest

from relay.atomicio import atomic_write_text
from relay.ticket import Ticket


def test_atomic_write_replaces_content(tmp_path) -> None:
    target = tmp_path / "state.txt"
    atomic_write_text(target, "first")
    atomic_write_text(target, "second")
    assert target.read_text() == "second"


def test_atomic_write_preserves_existing_mode(tmp_path) -> None:
    target = tmp_path / "state.txt"
    target.write_text("old")
    target.chmod(0o640)

    atomic_write_text(target, "new")

    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_atomic_write_uses_umask_mode_for_new_file(tmp_path) -> None:
    target = tmp_path / "state.txt"
    old_umask = os.umask(0o027)
    try:
        atomic_write_text(target, "payload")
    finally:
        os.umask(old_umask)

    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_atomic_write_leaves_no_temp_files(tmp_path) -> None:
    target = tmp_path / "state.txt"
    atomic_write_text(target, "payload")
    # The same-directory temp must be renamed away, not left behind.
    assert [p.name for p in tmp_path.iterdir()] == ["state.txt"]


def test_interrupted_write_preserves_prior_content(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash in the rename window must leave the *old* file fully intact —
    the truncated-ticket footgun this work exists to close."""
    target = tmp_path / "ticket.md"
    atomic_write_text(target, "original complete content\n")

    real_replace = os.replace

    def boom(src, dst):  # simulate the process dying at the rename
        raise OSError("simulated crash before rename completes")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(target, "NEW PARTIAL DATA THAT MUST NOT SURVIVE")
    monkeypatch.setattr(os, "replace", real_replace)

    # Reader sees the old, complete file — never a truncated mix.
    assert target.read_text() == "original complete content\n"
    # And the aborted write left no debris in the directory.
    assert [p.name for p in tmp_path.iterdir()] == ["ticket.md"]


def test_ticket_write_survives_interrupted_write(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Ticket.write` is atomic: an interrupted rewrite leaves the prior
    ticket.md parseable rather than truncated for the next `relay validate`."""
    path = tmp_path / "ticket.md"
    Ticket.parse(
        "---\ntitle: First\nstatus: active\n---\n\nbody\n"
    ).write(path)

    def boom(src, dst):
        raise OSError("crash mid-write")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        Ticket.parse(
            "---\ntitle: Second\nstatus: in_progress\n---\n\nnew body\n"
        ).write(path)
    monkeypatch.undo()

    survivor = Ticket.read(path)
    assert survivor.title == "First"
    assert survivor.status == "active"
