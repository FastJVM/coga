"""Bootstrap helpers used by `coga init`.

Copies coga templates from the installed package resources and stands up the
self-contained venv the vendored CLI runs out of. The venv's coga comes from
the running distribution — the release version for wheel installs, the source
checkout for editable installs — never from a fresh upstream clone, so the
vendored copy is exactly the CLI that ran init. No Typer commands live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import (
    PackageNotFoundError,
    metadata as _pkg_metadata,
    version as _pkg_version,
)
from importlib.resources import files
from importlib.resources.abc import Traversable
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import typer

import coga
from coga.github_source import pip_git_source, redacted_git_source


COGA_REPO_URL = "https://github.com/FastJVM/coga"
COGA_REPO_URL_ENV = "COGA_REPO_URL"
TEMPLATE_RESOURCE_PACKAGE = "coga.resources"
TEMPLATE_RESOURCE_PATH = ("templates", "coga")

_LEGACY_COGA_GITIGNORE_ENTRIES: set[str] = {
    "skills/bootstrap",
    "skills/retro",
    "skills/coga",
    "contexts/coga/architecture",
    "contexts/coga/principles",
    "contexts/coga/cli",
}


@dataclass(frozen=True)
class InstallSource:
    """Where `install_venv` gets the coga package it puts in the vendored venv.

    `pip_spec` is the literal requirement handed to `pip install`. `display`
    is the redacted, human-readable provenance recorded in COGA_PIN and echoed
    to the operator (never credential-bearing). `requires_python` is the
    source's requires-python spec when it is knowable before installing;
    None skips the pre-install interpreter check and leaves it to pip.
    """

    kind: str  # "release" | "checkout" | "url"
    pip_spec: str
    display: str
    requires_python: str | None = None


def resolve_install_source() -> InstallSource:
    """Decide where the vendored venv's coga comes from.

    In order: the `COGA_REPO_URL` override — a local checkout path (the
    sanctioned source-install path) or a git URL pip can install from; the
    source checkout the running package is imported from (editable installs);
    else the running package's own release from PyPI (`pip install
    coga==<running version>`). The vendored copy is therefore always the CLI
    that ran init — never upstream main. Exits loud when the override doesn't
    name a usable source or the running version can't be determined.
    """
    override = os.environ.get(COGA_REPO_URL_ENV, "").strip()
    if override:
        path = Path(override).expanduser()
        if path.is_dir():
            return _checkout_install_source(
                path.resolve(), origin=f"{COGA_REPO_URL_ENV} override"
            )
        return InstallSource(
            kind="url",
            pip_spec=pip_git_source(override),
            display=redacted_git_source(override),
        )
    checkout = _running_checkout_root()
    if checkout is not None:
        return _checkout_install_source(checkout, origin="running source checkout")
    try:
        version = _pkg_version("coga")
    except PackageNotFoundError:
        version = None
    if not version:
        typer.secho(
            "Cannot determine which coga to vendor: no installed `coga` "
            "distribution and not running from a source checkout.\n"
            f"Set {COGA_REPO_URL_ENV} to a coga checkout path or git URL and "
            "re-run.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return InstallSource(
        kind="release",
        pip_spec=f"coga=={version}",
        display=f"coga=={version} (PyPI)",
        requires_python=_running_requires_python(),
    )


def _running_checkout_root() -> Path | None:
    """Root of the source checkout the running coga is imported from, or None.

    An editable / in-tree run imports the package straight from a checkout's
    `src/coga/`, under a root whose `pyproject.toml` declares the `coga`
    project. A wheel install (site-packages) never has that shape.
    """
    location = getattr(coga, "__file__", None)
    if not location:
        return None
    pkg_dir = Path(location).resolve().parent
    if pkg_dir.name != "coga" or pkg_dir.parent.name != "src":
        return None
    root = pkg_dir.parents[1]
    if _pyproject_project_name(root / "pyproject.toml") != "coga":
        return None
    return root


def _checkout_install_source(root: Path, *, origin: str) -> InstallSource:
    """An InstallSource for a coga source checkout at `root`. Exits if it isn't one."""
    pyproject = root / "pyproject.toml"
    if _pyproject_project_name(pyproject) != "coga":
        typer.secho(
            f"{root} ({origin}) is not a coga source checkout — {pyproject} "
            "is missing or doesn't declare project name `coga`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return InstallSource(
        kind="checkout",
        pip_spec=str(root),
        display=str(root),
        requires_python=_requires_python_spec(pyproject),
    )


def _pyproject_project_name(pyproject: Path) -> str | None:
    """`project.name` from a pyproject.toml, or None if absent/unreadable."""
    try:
        data = tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None
    name = data.get("project", {}).get("name")
    return name if isinstance(name, str) and name.strip() else None


def _running_requires_python() -> str | None:
    """Requires-Python of the running coga distribution, or None."""
    try:
        return _pkg_metadata("coga").get("Requires-Python") or None
    except PackageNotFoundError:
        return None


def vendored_cli_version(venv_dir: Path) -> str | None:
    """The coga version pip actually installed into `venv_dir`, or None."""
    venv_python = venv_dir / "bin" / "python"
    try:
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                "from importlib.metadata import version; print(version('coga'))",
            ],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def write_pin(
    coga_os: Path,
    source: InstallSource,
    version: str | None,
) -> Path | None:
    """Record what `coga/.coga/` was vendored from: install source + version.

    Skips the write if `version` is None (stubbed venv in tests, mostly).
    Returns the pin path on success.
    """
    if version is None:
        return None
    pin = coga_os / ".coga" / "COGA_PIN"
    pin.parent.mkdir(parents=True, exist_ok=True)
    pin.write_text(f"{source.display}\n{version}\n")
    return pin


def read_pin_source(coga_os: Path) -> str | None:
    """Return the install source recorded in `.coga/COGA_PIN`, or None."""
    pin = coga_os / ".coga" / "COGA_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[0]


def read_pin(coga_os: Path) -> str | None:
    """Return the pinned vendored version from `.coga/COGA_PIN`, or None.

    Pre-PyPI pins recorded an upstream commit SHA on this line instead of a
    package version; both are reported as-is.
    """
    pin = coga_os / ".coga" / "COGA_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[1]


def packaged_template_root() -> Traversable:
    """Return the coga template tree embedded in the installed package."""
    root = files(TEMPLATE_RESOURCE_PACKAGE).joinpath(*TEMPLATE_RESOURCE_PATH)
    if not root.is_dir():
        typer.secho(
            "Installed coga package is missing templates/coga resources.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return root


def packaged_bootstrap_skills_dir() -> Path:
    """Return the bundled package skill root."""
    return Path(
        files(TEMPLATE_RESOURCE_PACKAGE).joinpath(
            *TEMPLATE_RESOURCE_PATH, "bootstrap", "skills"
        )
    )


def copy_fresh_templates(src_root: Traversable, coga_os: Path) -> None:
    """Copy the full packaged coga template tree into a fresh repo."""
    _copy_resource_tree(src_root, coga_os, skip_top={"bootstrap"})
    _chmod_packaged_executables(coga_os)


def nearest_existing_dir(target: Path) -> Path | None:
    """The nearest dir at/above `target` that exists on disk, or None.

    `coga init`'s target may not exist yet (`coga init tools/ops` creates the
    subdir), but `git -C` needs a real directory to run from; both `is_git_repo`
    and init's `_host_ignores_coga` probe git from this ancestor, so they share
    the walk.
    """
    return next((p for p in [target, *target.parents] if p.is_dir()), None)


def is_git_repo(target: Path) -> bool:
    """True when `target` is a git repo root or sits inside a git work tree.

    `.git` may be a directory (normal repo) or a file (worktree/submodule), so
    test existence rather than dir-ness; that also keeps the common repo-root
    case a pure filesystem check. A target *without* its own `.git` may still
    be a subdir of a host repo (monorepo `coga init tools/ops`), so fall back
    to asking git from the nearest existing ancestor — `target` itself may not
    exist yet. `coga init` requires this up front, `_git_commit_coga_os` reuses
    it to decide whether to commit, and `ensure_host_gitignore` to decide
    whether a host `.gitignore` is meaningful — the three must agree, so they
    share this predicate.
    """
    if (target / ".git").exists():
        return True
    probe = nearest_existing_dir(target)
    if probe is None:
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


HOST_GITIGNORE_BEGIN = "# >>> coga-managed >>>"
HOST_GITIGNORE_END = "# <<< coga-managed <<<"
_HOST_GITIGNORE_BODY = (
    f"{HOST_GITIGNORE_BEGIN}\n"
    "# Managed by `coga init`. Don't edit between these markers —\n"
    "# they will be overwritten. Symlinks below are created by `coga init` so\n"
    "# agent CLIs (Claude Code, Codex) can discover Coga's generated skill view.\n"
    ".claude/skills/coga\n"
    ".codex/skills/coga\n"
    "# coga-local state: vendored CLI/venv (`.coga/bin`, `.coga/.venv`).\n"
    ".coga/\n"
    f"{HOST_GITIGNORE_END}\n"
)


def ensure_host_gitignore(target: Path) -> bool:
    """Insert/refresh the coga-managed block in `<target>/.gitignore`.

    Idempotent: leaves the file alone when the existing block already matches.
    Only runs inside a git work tree — outside one a host `.gitignore` is moot.
    For a nested init (`target` below the git root) the block still lands at
    `<target>/.gitignore`: git scopes a nested ignore file's patterns to its
    own directory, which is exactly where the symlinks and `.coga/` live.
    Returns True iff the file was modified.
    """
    if not is_git_repo(target):
        return False

    gi = target / ".gitignore"
    existing = gi.read_text() if gi.is_file() else ""

    begin = existing.find(HOST_GITIGNORE_BEGIN)
    if begin == -1:
        prefix = existing
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix:
            prefix += "\n"
        new = prefix + _HOST_GITIGNORE_BODY
    else:
        end = existing.find(HOST_GITIGNORE_END, begin)
        if end == -1:
            new = existing[:begin] + _HOST_GITIGNORE_BODY
        else:
            end += len(HOST_GITIGNORE_END)
            if end < len(existing) and existing[end] == "\n":
                end += 1
            new = existing[:begin] + _HOST_GITIGNORE_BODY + existing[end:]

    if new == existing:
        return False
    gi.write_text(new)
    return True


def remove_host_gitignore(target: Path) -> bool:
    """Strip the coga-managed block from `<target>/.gitignore`. Inverse of
    `ensure_host_gitignore`.

    Removes only the marker-fenced region (and a single trailing blank line left
    behind), leaving every user-authored line intact. Idempotent: returns False
    when there's no `.gitignore` or no managed block to remove. Never raises.
    """
    gi = target / ".gitignore"
    if not gi.is_file():
        return False
    existing = gi.read_text()

    begin = existing.find(HOST_GITIGNORE_BEGIN)
    if begin == -1:
        return False
    end = existing.find(HOST_GITIGNORE_END, begin)
    if end == -1:
        # Truncated block (no end marker) — drop from the begin marker on.
        new = existing[:begin]
    else:
        end += len(HOST_GITIGNORE_END)
        if end < len(existing) and existing[end] == "\n":
            end += 1
        new = existing[:begin] + existing[end:]

    # Collapse the blank-line gap `ensure_host_gitignore` inserted before the
    # block so removing it doesn't leave a trailing run of newlines.
    new = new.rstrip("\n")
    if new:
        new += "\n"

    if new == existing:
        return False
    gi.write_text(new)
    return True


def write_bin_wrapper(bin_dir: Path) -> None:
    """Drop `bin/coga` — a relative symlink to the venv's `coga` console script.

    Resolved chain at runtime: `<.coga>/bin/coga` → `<.coga>/.venv/bin/coga`,
    whose pip-generated shebang points at `<.coga>/.venv/bin/python`. Works even
    when `bin/coga` itself is reached via another symlink (e.g. `~/.local/bin`).
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "coga"
    if wrapper.exists() or wrapper.is_symlink():
        wrapper.unlink()
    wrapper.symlink_to(Path("..") / ".venv" / "bin" / "coga")


COGA_PYTHON_ENV = "COGA_PYTHON"


def resolve_venv_python() -> str:
    """Pick the interpreter that builds `.coga/.venv`. The rule, in order:

    1. `$COGA_PYTHON` — explicit operator override; a path or a PATH name
       (`COGA_PYTHON=python3.11 coga init …`). The escape hatch when the
       CLI's own interpreter is one the vendored build chokes on. Exits if
       it doesn't resolve to an executable — an explicit choice that can't
       be honored must never silently fall back to a different Python.
    2. `sys.executable` — the interpreter running the coga CLI. Whatever
       installed coga (pipx, uv tool, pip) already imports it under this
       Python, and `python -m venv` derives the venv from this
       interpreter's base, so the venv gets the version validated here.

    `install_venv` validates the choice against the vendored copy's
    `requires-python` before building anything.
    """
    override = os.environ.get(COGA_PYTHON_ENV, "").strip()
    if not override:
        return sys.executable
    resolved = shutil.which(override)
    if not resolved:
        typer.secho(
            f"{COGA_PYTHON_ENV}={override} does not resolve to an executable"
            " Python — fix or unset it.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return resolved


def _python_version(python: str) -> tuple[int, int, int] | None:
    """(major, minor, micro) of `python`, or None if it can't be run/parsed."""
    if python == sys.executable:
        return (sys.version_info[0], sys.version_info[1], sys.version_info[2])
    try:
        result = subprocess.run(
            [python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    return None


def _python_executable(python: str) -> Path | None:
    """Resolved executable identity reported by `python`, or None on failure."""
    if python == sys.executable:
        return Path(sys.executable).resolve()
    try:
        result = subprocess.run(
            [python, "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    executable = result.stdout.strip()
    if result.returncode != 0 or not executable:
        return None
    return Path(executable).resolve()


def _requires_python_spec(pyproject: Path) -> str | None:
    """`project.requires-python` from a pyproject.toml, or None if absent/unreadable."""
    try:
        data = tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None
    spec = data.get("project", {}).get("requires-python")
    if isinstance(spec, str) and spec.strip():
        return spec.strip()
    return None


_SPEC_CLAUSE_RE = re.compile(r"^(>=|<=|==|!=|~=|>|<)\s*([0-9]+(?:\.[0-9]+)*(?:\.\*)?)$")


def _version_satisfies(version: tuple[int, int, int], spec: str) -> bool:
    """Check a Python version against a `requires-python` specifier.

    Covers the PEP 440 subset that shows up in real requires-python fields:
    comma-joined `>= > <= < == != ~=` clauses plus `.*` wildcards on ==/!=.
    Clauses it can't parse count as satisfied — an exotic spec must not
    brick the bootstrap; pip re-checks the full spec at install time.
    """
    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = _SPEC_CLAUSE_RE.match(clause)
        if not match:
            continue
        if not _spec_clause_holds(version, match.group(1), match.group(2)):
            return False
    return True


def _spec_clause_holds(version: tuple[int, int, int], op: str, want: str) -> bool:
    wildcard = want.endswith(".*")
    if wildcard:
        want = want[:-2]
    want_parts = tuple(int(p) for p in want.split("."))
    if wildcard and op in ("==", "!="):
        matches = version[: len(want_parts)] == want_parts
        return matches if op == "==" else not matches
    padded = (want_parts + (0, 0, 0))[:3]
    if op == ">=":
        return version >= padded
    if op == ">":
        return version > padded
    if op == "<=":
        return version <= padded
    if op == "<":
        return version < padded
    if op == "==":
        return version == padded
    if op == "!=":
        return version != padded
    if op == "~=":
        # ~=X.Y means >=X.Y and matching all but the last given component.
        if len(want_parts) < 2:
            return True
        return version >= padded and version[: len(want_parts) - 1] == want_parts[:-1]
    return True


_HASH_MODE_MARKERS = (
    "--require-hashes",
    "can't verify hashes",
    "requiring hashes",
    "hashes are required",
)


def hash_checking_hint(stderr: str) -> str:
    """Remediation to append when pip failed because of hash-checking mode.

    Managed machines commonly force pip's hash-checking mode globally
    (`PIP_REQUIRE_HASHES=1` or `require-hashes` in pip config). Local
    directories and requirement files without pinned hashes can't satisfy it,
    so every pip call coga makes fails with a raw pip error that doesn't name
    the setting. Returns "" when stderr doesn't look like that failure.
    """
    lowered = stderr.lower()
    if not any(marker in lowered for marker in _HASH_MODE_MARKERS):
        return ""
    return (
        "\npip is running in hash-checking mode (PIP_REQUIRE_HASHES=1 or "
        "require-hashes in pip config — common on managed machines), which "
        "rejects installs that don't ship pinned hashes, including coga's "
        "own venv bootstrap.\n"
        "Re-run the same coga command with hash checking disabled for it, "
        "e.g.:\n"
        "  PIP_REQUIRE_HASHES=0 coga init …"
    )


def install_venv(coga_os: Path, source: InstallSource | None = None) -> Path:
    """Create `.coga/.venv/` and `pip install` coga into it from `source`.

    `source` defaults to `resolve_install_source()` — the running release for
    wheel installs, the running source checkout for editable installs, or the
    `COGA_REPO_URL` override.

    The venv's interpreter comes from `resolve_venv_python()` ($COGA_PYTHON,
    else the Python running this CLI) and is validated against the source's
    `requires-python` before anything is built, so an interpreter the
    install method tolerated but the vendored build can't use fails here with
    remediation instead of half-way through a broken bootstrap.

    Idempotent: re-running upgrades the venv in place. If the existing venv was
    built against a different Python X.Y, or an explicit `COGA_PYTHON` resolves
    to a different base executable, it gets rebuilt from scratch (pip-installed
    packages from another interpreter aren't portable, and a host Python upgrade
    can leave a broken interpreter symlink).
    Returns the venv path. Exits with a clear error if Python venv/pip aren't usable.
    """
    venv_dir = coga_os / ".coga" / ".venv"
    if source is None:
        source = resolve_install_source()

    python = resolve_venv_python()
    python_version = _python_version(python)
    if python_version is None:
        typer.secho(
            f"Cannot determine the Python version of {python} — it doesn't run.\n"
            f"Set {COGA_PYTHON_ENV} to a working Python 3 interpreter and re-run.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    spec = source.requires_python
    if spec is not None and not _version_satisfies(python_version, spec):
        version_str = ".".join(str(p) for p in python_version)
        typer.secho(
            f"Python {version_str} ({python}) does not satisfy coga's "
            f"requires-python ({spec}).\n"
            f"Re-run with a suitable interpreter, e.g. "
            f"{COGA_PYTHON_ENV}=python3.11 coga init …",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    target_version = python_version[:2]
    venv_version = _venv_python_version(venv_dir)
    venv_python = venv_dir / "bin" / "python"
    override_requested = bool(os.environ.get(COGA_PYTHON_ENV, "").strip())
    selected_executable = (
        _python_executable(python)
        if override_requested and venv_dir.exists()
        else None
    )
    venv_executable = (
        _venv_python_executable(venv_dir) if override_requested else None
    )
    override_mismatch = override_requested and venv_dir.exists() and (
        selected_executable is None
        or venv_executable is None
        or selected_executable != venv_executable
    )
    if venv_dir.exists() and (
        not venv_python.is_file()
        or (venv_version is not None and venv_version != target_version)
        or override_mismatch
    ):
        if venv_version is not None and venv_version != target_version:
            typer.echo(
                f"Recreating venv (was Python {venv_version[0]}.{venv_version[1]}, "
                f"now {target_version[0]}.{target_version[1]})…"
            )
        elif override_mismatch:
            old = str(venv_executable) if venv_executable is not None else "unknown"
            new = str(selected_executable) if selected_executable is not None else python
            typer.echo(
                f"Recreating venv ({COGA_PYTHON_ENV} selects {new}, was {old})…"
            )
        shutil.rmtree(venv_dir)

    if not venv_python.is_file():
        typer.echo(f"Creating venv at {venv_dir}…")
        result = subprocess.run(
            [python, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = f"venv creation failed:\n{result.stderr}"
            if "ensurepip" in result.stderr:
                message += (
                    f"\n{python} is missing the venv/ensurepip modules "
                    "(Debian/Ubuntu ship them separately). Fix:\n"
                    f"  sudo apt install python{target_version[0]}."
                    f"{target_version[1]}-venv\n"
                    f"or set {COGA_PYTHON_ENV} to a Python with venv support."
                )
            typer.secho(message, fg=typer.colors.RED, err=True)
            sys.exit(2)

    typer.echo(f"Installing vendored CLI into venv (pip install {source.display})…")
    result = subprocess.run(
        [
            str(venv_dir / "bin" / "python"),
            "-m", "pip", "install",
            "--quiet", "--upgrade",
            source.pip_spec,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # A `url` source's pip spec may carry credentials — never echo it raw.
        stderr = result.stderr.replace(source.pip_spec, source.display)
        typer.secho(
            f"pip install failed:\n{stderr}"
            f"{hash_checking_hint(stderr)}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    install_skill_requirements(coga_os, venv_dir)
    return venv_dir


def install_skill_requirements(coga_os: Path, venv_dir: Path) -> list[Path]:
    """pip-install every skill's `requirements.txt` into the venv.

    A skill declares its own Python dependencies in a top-level
    `requirements.txt`; this pass is what actually puts those deps in the venv
    the skills run under, so a packaged skill brings its own deps with it
    (there is no other per-skill install hook). Scans both skill roots:
    project-local `coga/skills/` and packaged bundled skills.
    Called at the tail of `install_venv`, so `coga init` picks up the
    skill requirements present at init time.

    Idempotent — pip skips already-satisfied requirements. Exits with a clear
    error on a failed install, matching `install_venv`'s fail-loud contract.
    Returns the requirement files that were installed (sorted), for callers
    and tests.
    """
    roots = [
        coga_os / "skills",
        packaged_bootstrap_skills_dir(),
    ]
    req_files = sorted(
        req
        for root in roots
        if root.is_dir()
        for req in root.rglob("requirements.txt")
    )
    if not req_files:
        return []
    venv_python = venv_dir / "bin" / "python"
    for req in req_files:
        try:
            label = req.relative_to(coga_os)
        except ValueError:
            label = req
        typer.echo(f"Installing skill deps from {label}…")
        result = subprocess.run(
            [
                str(venv_python),
                "-m", "pip", "install",
                "--quiet", "-r", str(req),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            typer.secho(
                f"pip install -r {req} failed:\n{result.stderr}"
                f"{hash_checking_hint(result.stderr)}",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)
    return req_files


# pipx tracks installs by the package distribution name from `pyproject.toml`.
# The distribution and the entry-point binary are both `coga`, so this is just
# the dist name passed to `pipx`.
COGA_PIPX_PACKAGE = "coga"


def running_cli_location(coga_os: Path) -> tuple[str, Path]:
    """Identify which install of `coga` is currently executing.

    Returns `(kind, venv_root)`:
      - `("vendored", <coga_os>/.coga/.venv)` — running the vendored copy
        `coga init` installed into this repo.
      - `("pipx", <pipx-venv>)` — installed via pipx; we can offer to upgrade.
      - `("other", <venv_root>)` — pip / system python / something else; the
        caller should print a manual-upgrade hint.

    Detection uses the *unresolved* `sys.executable` parent venv. A pipx
    venv's `bin/python` is a symlink to the host Python (Homebrew, pyenv,
    system). Resolving the symlink lands in the host's framework dir and
    misses the `pipx_metadata.json` marker that lives in the venv root.
    Same trap for vendored — `.venv/bin/python` symlinks to the host too,
    so resolving makes vendored and pipx and other all collapse onto the
    same host-python directory and detection silently breaks.
    """
    venv = Path(sys.executable).absolute().parent.parent
    vendored = (coga_os / ".coga" / ".venv").absolute()
    if venv == vendored:
        return ("vendored", venv)
    if (venv / "pipx_metadata.json").is_file():
        return ("pipx", venv)
    return ("other", venv)


def _venv_python_version(venv_dir: Path) -> tuple[int, int] | None:
    """Read `pyvenv.cfg` and return the (major, minor) Python the venv was built with."""
    cfg = venv_dir / "pyvenv.cfg"
    if not cfg.is_file():
        return None
    for line in cfg.read_text().splitlines():
        key, sep, value = line.partition("=")
        if not sep or key.strip() != "version":
            continue
        parts = value.strip().split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    return None


def _venv_python_executable(venv_dir: Path) -> Path | None:
    """Resolved base executable recorded in `pyvenv.cfg`, or None."""
    cfg = venv_dir / "pyvenv.cfg"
    if not cfg.is_file():
        return None
    for line in cfg.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "executable" and value.strip():
            return Path(value.strip()).resolve()
    return None


COGA_GITIGNORE_BEGIN = "# >>> coga-managed >>>"
COGA_GITIGNORE_END = "# <<< coga-managed <<<"
_COGA_GITIGNORE_HEADER = (
    "# Managed by `coga init`. Don't edit between these markers —\n"
    "# they will be overwritten. Add your own ignore rules below the\n"
    "# end marker.\n"
)


def _refresh_coga_gitignore(src_root: Traversable, dst_root: Path) -> bool:
    """Insert/refresh the coga-managed block in `coga/.gitignore`.

    Pattern mirrors `ensure_host_gitignore`: the block is fenced by markers
    and replaced wholesale on each update; lines outside the markers are
    user-owned and preserved. Lines outside the block that exactly match a
    managed entry are dropped — handles repos that predate the marker
    convention or had the upstream content copied in directly.

    Returns True iff the file was modified.
    """
    src = _resource_join(src_root, Path(".gitignore"))
    if not src.is_file():
        return False

    body = _render_coga_gitignore_body(src_root)
    block = f"{COGA_GITIGNORE_BEGIN}\n{body}{COGA_GITIGNORE_END}\n"

    dst = dst_root / ".gitignore"
    existing = dst.read_text() if dst.is_file() else ""

    begin = existing.find(COGA_GITIGNORE_BEGIN)
    if begin == -1:
        # Pre-marker file (or fresh repo). Treat the whole thing as user
        # content, dedupe against managed entries, and prepend the block.
        managed_entries = _parse_gitignore_entries(body)
        managed_entries.update(_LEGACY_COGA_GITIGNORE_ENTRIES)
        deduped = _drop_matching_lines(existing, managed_entries)
        if deduped and not deduped.endswith("\n"):
            deduped += "\n"
        new = block + (("\n" + deduped) if deduped else "")
    else:
        end = existing.find(COGA_GITIGNORE_END, begin)
        if end == -1:
            new = existing[:begin] + block
        else:
            end += len(COGA_GITIGNORE_END)
            if end < len(existing) and existing[end] == "\n":
                end += 1
            new = existing[:begin] + block + existing[end:]

    if new == existing:
        return False
    dst.write_text(new)
    return True


def _render_coga_gitignore_body(src_root: Traversable) -> str:
    src = _resource_join(src_root, Path(".gitignore"))
    upstream_text = src.read_text().rstrip()
    body = _COGA_GITIGNORE_HEADER
    if upstream_text:
        body += upstream_text + "\n"
    return body


def _parse_gitignore_entries(text: str) -> set[str]:
    """Return the set of non-comment, non-blank lines in a gitignore body."""
    return {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _drop_matching_lines(text: str, drop: set[str]) -> str:
    """Remove lines whose stripped form is in `drop`. Preserves other content."""
    kept = [
        line
        for line in text.splitlines(keepends=True)
        if line.strip() not in drop
    ]
    return "".join(kept)


def _resource_join(root: Traversable, rel: Path) -> Traversable:
    node = root
    for part in rel.parts:
        node = node.joinpath(part)
    return node


def _copy_resource_tree(
    src: Traversable, dst: Path, *, skip_top: set[str] | None = None
) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    skip_top = skip_top or set()
    for child in src.iterdir():
        if child.name in skip_top:
            continue
        child_dst = dst / child.name
        if child.is_dir():
            _copy_resource_tree(child, child_dst)
        elif child.is_file():
            _copy_resource_file(child, child_dst)


def _copy_resource_file(src: Traversable, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as source, dst.open("wb") as target:
        shutil.copyfileobj(source, target)


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _chmod_packaged_executables(coga_os: Path) -> None:
    scripts_dir = coga_os / "scripts"
    if scripts_dir.is_dir():
        for script in scripts_dir.glob("*.sh"):
            _chmod_executable(script)


def _chmod_executable(path: Path) -> None:
    try:
        path.chmod(0o755)
    except OSError:
        pass
