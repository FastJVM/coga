"""Warn when the running coga binary predates the source checkout it operates on.

A coga developer who installs the CLI once (`uv tool install .`, `pipx`, a plain
`pip install`) and then keeps editing the source tree ends up running a *frozen
snapshot* of the code against a repo whose `src/coga/` has since moved on. The
skew is silent: nothing tells you the binary is stale, so a bug fixed in source
is still live in the binary you actually run. That is not hypothetical — it cost
a manual salvage session (PR #500) when a launch kept losing `log.md` lines
through a fix that was already in source but not in the installed binary.

This guard makes that skew *visible*. It is warn-only — running a slightly stale
coga is usually fine — and it is scoped to coga developers: it fires only inside
a coga source checkout (a repo with `src/coga/`) and stays completely silent for
normal users, who never have that tree.

Detection is a build-time-vs-source-time comparison:

  - The running package's install time is `mtime(coga.__file__)`. A `uv tool` /
    `pipx` / `pip` install writes the package files at install time, so that
    mtime is a reliable "built/installed at" stamp. (A reproducible build could
    zero it; an implausibly old stamp is treated as unknown and skipped.)
  - The source side is `git log -1 --format=%ct -- src/coga` of the operated-on
    repo — the last commit that touched the CLI source.
  - When the source commit is newer than the install, the binary predates the
    tree and we warn, naming both sides and the reinstall remedy.

Every degradation is silent: not a git repo, not a coga source checkout, an
editable / in-tree run (the running code *is* the source, so no skew is
possible), or an unreadable build time. The whole entry point is wrapped so a
git hiccup or a surprising filesystem can never turn this diagnostic into a
crash of the command it precedes.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import TextIO

import coga

# Below this, a build-time mtime is treated as "unknown" rather than real:
# reproducible builds zero file mtimes to a fixed epoch (the 1980 zip epoch,
# or a pinned SOURCE_DATE_EPOCH), which would otherwise read as "ancient" and
# make the guard warn on every run. 2020-01-01 UTC comfortably clears those.
_PLAUSIBLE_BUILD_FLOOR = 1_577_836_800.0


def warn_if_installed_predates_source(
    repo_root: Path, *, stream: TextIO = sys.stderr
) -> bool:
    """Print a stderr warning when the running coga predates the repo's source.

    `repo_root` is the coga OS dir of the repo being operated on (`cfg.repo_root`);
    the git toplevel is resolved from it. Returns True iff a warning was printed,
    for callers that want to know (and for tests). Never raises — any failure to
    determine the answer is a silent no-op, because this is a diagnostic that
    must never break the command it precedes.
    """
    try:
        git_root = _source_checkout_root(repo_root)
        if git_root is None:
            return False

        package_dir = _installed_package_dir()
        if package_dir is not None and _is_within(package_dir, git_root / "src"):
            # Editable / pythonpath dev run: the running code *is* the source
            # tree, so there is nothing to be stale against.
            return False

        build_time = _installed_build_time()
        if build_time is None:
            return False

        latest = _latest_src_change(git_root)
        if latest is None:
            return False
        src_commit_time, short_sha, commit_date = latest

        if src_commit_time <= build_time:
            return False

        stream.write(
            _format_warning(
                version=_running_version(),
                build_time=build_time,
                short_sha=short_sha,
                commit_date=commit_date,
            )
        )
        return True
    except Exception:
        # A guard that can crash the command is worse than no guard.
        return False


def _source_checkout_root(repo_root: Path) -> Path | None:
    """Git toplevel containing `repo_root`, but only if it is a coga source tree.

    Returns the toplevel path when the repo is a git checkout that carries
    `src/coga/` (the marker of a coga source tree), else None. Normal users'
    repos lack `src/coga/`, so this short-circuits them without any further work.
    """
    start = repo_root if repo_root.is_dir() else repo_root.parent
    out = _run_git(start, "rev-parse", "--show-toplevel")
    if out is None:
        return None
    top = Path(out.strip())
    if not (top / "src" / "coga").is_dir():
        return None
    return top


def _latest_src_change(git_root: Path) -> tuple[int, str, str] | None:
    """(commit_time, short_sha, date) of the last commit touching `src/coga/`.

    `commit_time` is the committer date as a Unix timestamp; `date` is its
    `YYYY-MM-DD` short form for the message. None when the path has no history
    (or git is unavailable).
    """
    out = _run_git(
        git_root, "log", "-1", "--format=%ct%x00%h%x00%cs", "--", "src/coga"
    )
    if not out or not out.strip():
        return None
    parts = out.strip().split("\x00")
    if len(parts) < 3:
        return None
    try:
        commit_time = int(parts[0])
    except ValueError:
        return None
    return commit_time, parts[1], parts[2]


def _installed_package_dir() -> Path | None:
    """Directory the running `coga` package is imported from, or None."""
    location = getattr(coga, "__file__", None)
    if not location:
        return None
    try:
        return Path(location).resolve().parent
    except OSError:
        return None


def _installed_build_time() -> float | None:
    """Install/build time of the running package as a Unix timestamp, or None.

    Uses the mtime of the package's `__init__.py`, which `uv tool` / `pipx` /
    `pip` write at install time. An implausibly old stamp (see the floor) is
    reported as None so a reproducible build can't make the guard cry wolf.
    """
    location = getattr(coga, "__file__", None)
    if not location:
        return None
    try:
        mtime = Path(location).stat().st_mtime
    except OSError:
        return None
    if mtime < _PLAUSIBLE_BUILD_FLOOR:
        return None
    return mtime


def _running_version() -> str:
    try:
        return _pkg_version("coga")
    except PackageNotFoundError:
        return getattr(coga, "__version__", "unknown")


def _is_within(path: Path, ancestor: Path) -> bool:
    """True when `path` is `ancestor` or lives underneath it."""
    try:
        path.relative_to(ancestor)
        return True
    except ValueError:
        return False


def _format_warning(
    *, version: str, build_time: float, short_sha: str, commit_date: str
) -> str:
    built = datetime.fromtimestamp(build_time).strftime("%Y-%m-%d %H:%M")
    return (
        "\n"
        "⚠  coga version skew — the running binary predates this checkout's source.\n"
        f"     running:  coga {version}, built/installed {built}\n"
        f"     source:   src/coga last changed {commit_date} ({short_sha}), which is newer\n"
        "   You are likely running stale code. Reinstall to pick up the latest src/coga:\n"
        "       uv tool upgrade coga                     # if installed via `uv tool`\n"
        "       uv tool install --force --from . coga    # or reinstall from this checkout\n"
        "   (Warning only — coga will continue.)\n"
    )


def _run_git(root: Path, *args: str) -> str | None:
    """Run a git subcommand, returning stdout or None on any failure.

    Deliberately non-raising (unlike `coga.git._run_git`): this guard swallows
    every error, so a missing git binary or a non-zero exit is just "unknown".
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


__all__ = ["warn_if_installed_predates_source"]
