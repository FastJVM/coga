"""Tests for `coga.version_skew` — the stale-binary warning guard.

Exercises the real git path (a tmp checkout with a committed `src/coga/`, in the
spirit of `test_git.py`'s `git_repo`) and monkeypatches only the one
environment-dependent input, `_installed_build_time`, so the source/build time
comparison is deterministic.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from coga import version_skew


# --- helpers -------------------------------------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, capture_output=True, text=True,
    )


def _source_checkout(tmp_path: Path, *, with_src: bool = True) -> Path:
    """A git repo optionally carrying a committed `src/coga/`, returned as root."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Coga Test")
    _git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("repo\n")
    if with_src:
        src = root / "src" / "coga"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("__version__ = '0.0.0'\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    return root


def _src_commit_time(root: Path) -> int:
    latest = version_skew._latest_src_change(root)
    assert latest is not None
    return latest[0]


@pytest.fixture
def frozen_install(tmp_path, monkeypatch):
    """Pin the running package to a real *installed* location (a site-packages
    dir outside any checkout), so the build-time-vs-source decision is what gets
    exercised. Without this the test-runner's own editable coga install would be
    detected as live source and short-circuit the decision under test."""
    pkg = tmp_path / "site-packages" / "coga"
    pkg.mkdir(parents=True)
    monkeypatch.setattr(version_skew, "_installed_package_dir", lambda: pkg)
    return pkg


# --- source-change detection ---------------------------------------------------


def test_latest_src_change_reads_last_commit(tmp_path):
    root = _source_checkout(tmp_path)
    commit_time, short_sha, commit_date = version_skew._latest_src_change(root)
    assert commit_time > version_skew._PLAUSIBLE_BUILD_FLOOR
    assert short_sha
    assert commit_date.count("-") == 2  # YYYY-MM-DD


def test_latest_src_change_none_without_src(tmp_path):
    root = _source_checkout(tmp_path, with_src=False)
    assert version_skew._latest_src_change(root) is None


def test_source_checkout_root_requires_src_coga(tmp_path):
    assert version_skew._source_checkout_root(_source_checkout(tmp_path)) is not None
    assert (
        version_skew._source_checkout_root(
            _source_checkout(tmp_path / "bare", with_src=False)
        )
        is None
    )


def test_source_checkout_root_none_outside_git(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert version_skew._source_checkout_root(plain) is None


# --- the warning decision ------------------------------------------------------


def test_warns_when_binary_predates_source(tmp_path, monkeypatch, frozen_install):
    root = _source_checkout(tmp_path)
    monkeypatch.setattr(
        version_skew, "_installed_build_time", lambda: _src_commit_time(root) - 3600
    )
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is True
    out = stream.getvalue()
    assert "version skew" in out
    assert "src/coga last changed" in out
    assert "uv tool upgrade coga" in out


def test_no_warning_when_binary_newer_than_source(tmp_path, monkeypatch, frozen_install):
    root = _source_checkout(tmp_path)
    monkeypatch.setattr(
        version_skew, "_installed_build_time", lambda: _src_commit_time(root) + 3600
    )
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is False
    assert stream.getvalue() == ""


def test_no_warning_when_build_time_unknown(tmp_path, monkeypatch, frozen_install):
    root = _source_checkout(tmp_path)
    monkeypatch.setattr(version_skew, "_installed_build_time", lambda: None)
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is False
    assert stream.getvalue() == ""


def test_no_warning_outside_source_checkout(tmp_path, monkeypatch):
    root = _source_checkout(tmp_path, with_src=False)
    # Even with a would-be-stale build time, a non-source repo never warns.
    monkeypatch.setattr(version_skew, "_installed_build_time", lambda: 0.0)
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is False
    assert stream.getvalue() == ""


def test_no_warning_when_running_in_tree(tmp_path, monkeypatch):
    """An editable / pythonpath run — the package lives under the repo's `src/` —
    is the source itself, so it can never be stale against it."""
    root = _source_checkout(tmp_path)
    monkeypatch.setattr(
        version_skew, "_installed_package_dir", lambda: root / "src" / "coga"
    )
    monkeypatch.setattr(
        version_skew, "_installed_build_time", lambda: _src_commit_time(root) - 3600
    )
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is False
    assert stream.getvalue() == ""


def test_no_warning_when_editable_source_in_other_checkout(tmp_path, monkeypatch):
    """Editable install from checkout A, operating coga inside checkout B: the
    running package is live source of its OWN checkout, so it is never stale —
    even though it does not live under the *operated* repo's `src/`. (Guards the
    common coga worktree flow: install editable once, operate in many worktrees.)"""
    operated = _source_checkout(tmp_path / "b")
    editable = _source_checkout(tmp_path / "a")
    monkeypatch.setattr(
        version_skew, "_installed_package_dir", lambda: editable / "src" / "coga"
    )
    # A would-be-stale build time relative to the operated repo's latest commit.
    monkeypatch.setattr(
        version_skew, "_installed_build_time", lambda: _src_commit_time(operated) - 3600
    )
    stream = io.StringIO()
    assert (
        version_skew.warn_if_installed_predates_source(operated, stream=stream) is False
    )
    assert stream.getvalue() == ""


def test_warns_for_frozen_venv_copy_inside_source_tree(tmp_path, monkeypatch):
    """A NON-editable install into an in-tree `.venv` is a frozen snapshot that
    merely sits inside the checkout — it is not under `src/`, so it must still be
    caught as skew. The live-source short-circuit must not swallow it."""
    root = _source_checkout(tmp_path)
    frozen = root / ".venv" / "lib" / "coga"
    frozen.mkdir(parents=True)
    monkeypatch.setattr(version_skew, "_installed_package_dir", lambda: frozen)
    monkeypatch.setattr(
        version_skew, "_installed_build_time", lambda: _src_commit_time(root) - 3600
    )
    stream = io.StringIO()
    assert version_skew.warn_if_installed_predates_source(root, stream=stream) is True
    assert "version skew" in stream.getvalue()


def test_build_floor_rejects_reproducible_zeroed_mtime(tmp_path, monkeypatch):
    """A reproducible build zeroes mtimes to a fixed epoch; that must read as
    'unknown' (None), not as an ancient — and therefore always-stale — binary."""
    location = tmp_path / "coga" / "__init__.py"
    location.parent.mkdir(parents=True)
    location.write_text("x\n")
    import os

    os.utime(location, (315_532_800, 315_532_800))  # 1980-01-01, the zip epoch
    monkeypatch.setattr(version_skew.coga, "__file__", str(location))
    assert version_skew._installed_build_time() is None


def test_guard_never_raises(monkeypatch, tmp_path):
    """Any internal failure is swallowed — the guard must not break its caller."""
    def _boom(_root):
        raise RuntimeError("git exploded")

    monkeypatch.setattr(version_skew, "_source_checkout_root", _boom)
    assert version_skew.warn_if_installed_predates_source(tmp_path) is False
