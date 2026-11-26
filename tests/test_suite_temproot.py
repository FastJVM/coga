"""The conftest guard that keeps the suite's tmp trees outside every checkout.

`coga launch` points `TMPDIR` inside the Git work tree. On 2026-11-23 a run
under that `TMPDIR` let `test_uninstall_outside_repo_errors` discover the live
checkout from its "empty" tmp dir and run `coga uninstall --yes` against it,
deleting tracked files. `conftest.py::pytest_configure` moves such a temp root
to the system temp; these tests prove it from a child `pytest` that inherits an
in-checkout `TMPDIR`, the only way to exercise a session-start hook.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import enclosing_checkout

_REPO_ROOT = Path(__file__).resolve().parents[1]

_PROBE_TEST = "tests/test_suite_temproot.py::test_tmp_path_is_outside_every_checkout"
_UNINSTALL_TEST = "tests/test_uninstall.py::test_uninstall_outside_repo_errors"


def test_tmp_path_is_outside_every_checkout(tmp_path: Path) -> None:
    assert enclosing_checkout(tmp_path) is None


def test_enclosing_checkout_recognizes_each_marker(tmp_path: Path) -> None:
    git = tmp_path / "git"
    (git / ".git").mkdir(parents=True)
    (git / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    empty_git = tmp_path / "empty-git"
    (empty_git / ".git").mkdir(parents=True)
    root_layout = tmp_path / "root"
    root_layout.mkdir()
    (root_layout / "coga.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "nested"
    (nested / "coga").mkdir(parents=True)
    (nested / "coga" / "coga.toml").write_text("", encoding="utf-8")

    assert enclosing_checkout(git / "a" / "b") == git
    assert enclosing_checkout(worktree / "a") == worktree
    assert enclosing_checkout(empty_git / "a") is None
    assert enclosing_checkout(root_layout / "a") == root_layout
    assert enclosing_checkout(nested / "coga" / ".coga" / "tmp" / "x") == nested / "coga"
    assert enclosing_checkout(tmp_path / "plain") is None


def _seed_host(tmp_path: Path) -> tuple[Path, Path]:
    """A stand-in checkout in the launch layout, plus its in-repo TMPDIR."""
    host = tmp_path / "host"
    (host / ".git").mkdir(parents=True)
    (host / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (host / "coga").mkdir()
    (host / "coga" / "coga.toml").write_text("[repo]\n", encoding="utf-8")
    (host / "docs" / "contexts").mkdir(parents=True)
    (host / "docs" / "contexts" / "keep.md").write_text("keep\n", encoding="utf-8")
    launch_tmp = host / "coga" / ".coga" / "tmp" / "launch"
    launch_tmp.mkdir(parents=True)
    return host, launch_tmp


def _child_pytest(
    tmp_path: Path, launch_tmp: Path, *args: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    system_tmp = tmp_path / "system"
    system_tmp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTEST_DEBUG_TEMPROOT", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in ("TMPDIR", "TMP", "TEMP"):
        env[name] = str(launch_tmp)
    env["COGA_SYSTEM_TMPDIR"] = str(system_tmp)
    src = str(_REPO_ROOT / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=_REPO_ROOT,
    )
    return result, system_tmp


def _host_files(host: Path) -> list[str]:
    return sorted(
        path.relative_to(host).as_posix()
        for path in host.rglob("*")
        if path.is_file() and ".coga" not in path.relative_to(host).parts
    )


def test_in_checkout_tmpdir_is_redirected_to_system_temp(tmp_path: Path) -> None:
    host, launch_tmp = _seed_host(tmp_path)
    before = _host_files(host)

    result, system_tmp = _child_pytest(tmp_path, launch_tmp, _PROBE_TEST, _UNINSTALL_TEST)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _host_files(host) == before
    assert list(system_tmp.glob("pytest-of-*"))
    assert not any(launch_tmp.glob("pytest-of-*"))


def test_in_checkout_basetemp_is_refused(tmp_path: Path) -> None:
    host, launch_tmp = _seed_host(tmp_path)
    before = _host_files(host)

    result, _ = _child_pytest(
        tmp_path, launch_tmp, "--basetemp", str(launch_tmp / "bt"), _PROBE_TEST
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert "inside the checkout" in result.stdout + result.stderr
    assert _host_files(host) == before
    assert not (launch_tmp / "bt").exists()


def test_basetemp_containing_checkout_under_test_is_refused(tmp_path: Path) -> None:
    parent = tmp_path / "checkout-parent"
    host, launch_tmp = _seed_host(parent)
    test_dir = host / "tests"
    test_dir.mkdir()
    shutil.copyfile(_REPO_ROOT / "tests" / "conftest.py", test_dir / "conftest.py")
    probe = test_dir / "test_probe.py"
    probe.write_text(
        "def test_probe(tmp_path):\n    assert tmp_path.is_dir()\n",
        encoding="utf-8",
    )
    before = _host_files(host)

    # Run from outside the stand-in checkout so pytest's cwd check allows
    # the argument and our own guard must catch it.
    result, _ = _child_pytest(tmp_path, launch_tmp, "--basetemp", str(parent), str(probe))

    assert result.returncode == 4, result.stdout + result.stderr
    assert "contains the checkout under test" in result.stdout + result.stderr
    assert _host_files(host) == before
