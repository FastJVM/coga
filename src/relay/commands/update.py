"""Bootstrap helpers used by `relay init` (with or without --update).

Pulls upstream CLI source into `relay-os/.relay/`, refreshes relay templates
from the installed package resources, and stands up the self-contained venv
the vendored CLI runs out of. No Typer commands live here.
"""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import typer

from relay.github_source import (
    git_clone_source,
    is_ssh_git_source,
    pip_git_source,
    redacted_git_source,
    same_github_repo,
)


RELAY_REPO_URL = "https://github.com/FastJVM/relay"
RELAY_REPO_URL_ENV = "RELAY_REPO_URL"
RELAY_REMOTE_NAMES = ("upstream", "origin")
TEMPLATE_SUBPATH = Path("src/relay/resources/templates/relay-os")
CLI_SRC_SUBPATH = Path("src/relay")
TEMPLATE_RESOURCE_PACKAGE = "relay.resources"
TEMPLATE_RESOURCE_PATH = ("templates", "relay-os")

# Paths (relative to relay-os/) that earlier upstreams shipped but no longer do.
# `init --update` prunes these from existing repos so removed creating doesn't
# linger after a migration. Keep entries narrow — only files we know we shipped
# and now want gone, never user-owned paths.
#
# Note on the bootstrap-consolidation entries below: those paths used to be
# shipped directly at the relay-os/ root and are now package-backed batteries
# under `bootstrap/`. Existing repos need those narrow, known Relay-owned paths
# pruned so local-first resolution can fall through to bootstrap. Do not add
# broad namespace entries here; user-owned `skills/<namespace>` and
# `contexts/<namespace>` directories must be preserved.
OBSOLETE_PATHS: tuple[str, ...] = (
    "counter",  # numeric task ID counter, dropped in the slug-only migration
    "meta",  # renamed to bootstrap/ — pre-bootstrap upstreams shipped meta/
    "skills/bootstrap/create",  # renamed to bootstrap/ticket in 350c4ed
    "skills/bootstrap/ticket",  # consolidated under bootstrap/skills/bootstrap/ticket
    "skills/bootstrap/dream/tasks/validate-drift",  # consolidated under bootstrap/skills
    "skills/bootstrap/dream/tasks/cleanup-orphan-markers",  # consolidated under bootstrap/skills
    "skills/retro/done-ticket",  # consolidated under bootstrap/skills/retro/done-ticket
    "contexts/relay/architecture",  # consolidated under bootstrap/contexts/relay/architecture
    "contexts/relay/principles",  # consolidated under bootstrap/contexts/relay/principles
    "contexts/relay/cli",  # consolidated under bootstrap/contexts/relay/cli
    "contexts/relay/sync",  # consolidated under bootstrap/contexts/relay/sync
    "contexts/dev/code",  # consolidated under bootstrap/contexts/dev/code
    "hooks",  # legacy pre-bootstrap post-merge hook dir, now removed
    "tasks/relay-setup",  # `relay setup` retired; replaced by `relay build` (tasks/relay-build)
    "workflows/init",  # init/setup workflow retired; replaced by build/onboarding (dir entry so no empty init/ is left)
)

# Recurring-template files Relay vendors and keeps fresh on every `--update`.
# Unlike `_*` sample creates and user-authored repo-specific loops (REM),
# these are live Relay batteries such as `recurring/dream/` and
# `recurring/skill-update/`; their bodies are upstream-managed, not per-repo.
# They carry no `_` prefix (used as-is, not copied-and-renamed) and don't live under
# `bootstrap/`, so neither `_copy_templates` nor `_copy_vendored_bootstrap`
# would otherwise refresh them — leaving repos that predate a template, or lost
# them, permanently broken (`relay dream` or the skill updater has nothing to
# create).
#
# A recurring task is a ticket-format directory; only the upstream-managed
# `ticket.md` is refreshed. The sibling `blackboard.md` (last-run state) and
# `log.md` (run history) are per-repo and deliberately left untouched.
VENDORED_RECURRING_TEMPLATES: tuple[str, ...] = (
    "recurring/autoclose-merged/ticket.md",
    "recurring/digest/ticket.md",
    "recurring/dream/ticket.md",
    "recurring/skill-update/ticket.md",
)

# Narrow set of upstream-owned workflows that must be present in existing repos
# because a vendored recurring template references them. Do not broad-copy
# workflows: most named workflows are repo-owned playbooks.
VENDORED_WORKFLOW_TEMPLATES: tuple[str, ...] = (
    "workflows/autoclose-merged/sweep.md",
    "workflows/direct/body.md",
    "workflows/skill-update/run.md",
)

# Narrow set of upstream-owned skills that vendored workflows require. Most
# skills remain user-owned or managed through `managed-skills.toml`; these files
# are copied because core Relay batteries call them unconditionally.
VENDORED_SKILL_TEMPLATES: tuple[str, ...] = (
    "skills/direct/body/SKILL.md",
)

_LEGACY_RELAY_GITIGNORE_ENTRIES: set[str] = {
    "skills/bootstrap",
    "skills/retro",
    "skills/relay",
    "contexts/relay/architecture",
    "contexts/relay/principles",
    "contexts/relay/cli",
}


def resolve_relay_repo_url(
    *,
    relay_os: Path | None = None,
    cwd: Path | None = None,
) -> str:
    """Return the Relay upstream URL respecting the operator's git transport."""
    env_url = os.environ.get(RELAY_REPO_URL_ENV, "").strip()
    if env_url:
        return git_clone_source(env_url)
    remote_url = _detect_matching_relay_remote(cwd or Path.cwd())
    if remote_url:
        return remote_url
    pinned_url = read_pin_url(relay_os) if relay_os is not None else None
    return git_clone_source(pinned_url) if pinned_url else RELAY_REPO_URL


def clone_upstream(into: Path, *, repo_url: str | None = None) -> Path:
    """Shallow-clone the relay repo into `into`. Exit on failure. Return the path."""
    url = git_clone_source(repo_url or resolve_relay_repo_url())
    safe_url = redacted_git_source(url)
    typer.echo(f"Cloning {safe_url} (shallow)…")
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, str(into)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.replace(url, safe_url)
        typer.secho(
            f"git clone failed:\n{stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return into


def upstream_sha(clone_dir: Path) -> str | None:
    """Return the HEAD SHA of `clone_dir`, or None if `git rev-parse` fails."""
    result = subprocess.run(
        ["git", "-C", str(clone_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def write_pin(
    relay_os: Path,
    sha: str | None,
    *,
    repo_url: str | None = None,
) -> Path | None:
    """Record the upstream commit `relay-os/.relay/` was vendored from.

    Skips the write if `sha` is None (clone-without-git in tests, mostly).
    Returns the pin path on success.
    """
    if sha is None:
        return None
    pin = relay_os / ".relay" / "RELAY_PIN"
    pin.parent.mkdir(parents=True, exist_ok=True)
    url = repo_url or resolve_relay_repo_url(relay_os=relay_os)
    pin.write_text(f"{redacted_git_source(url)}\n{sha}\n")
    return pin


def read_pin_url(relay_os: Path) -> str | None:
    """Return the pinned upstream URL from `.relay/RELAY_PIN`, or None."""
    pin = relay_os / ".relay" / "RELAY_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[0]


def read_pin(relay_os: Path) -> str | None:
    """Return the pinned upstream SHA from `.relay/RELAY_PIN`, or None if absent/garbled."""
    pin = relay_os / ".relay" / "RELAY_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[1]


def _detect_matching_relay_remote(cwd: Path) -> str | None:
    matches: list[str] = []
    for remote in RELAY_REMOTE_NAMES:
        url = _git_remote_url(cwd, remote)
        if url and same_github_repo(url, RELAY_REPO_URL):
            matches.append(url)
    for url in matches:
        if is_ssh_git_source(url):
            return url
    return matches[0] if matches else None


def _git_remote_url(cwd: Path, remote: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", remote],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def relay_pip_git_source(*, relay_os: Path | None = None) -> str:
    return pip_git_source(
        redacted_git_source(resolve_relay_repo_url(relay_os=relay_os))
    )


def refresh_cli(clone_dir: Path, relay_os: Path) -> None:
    """Replace `relay-os/.relay/src/relay/` (+ pyproject + requirements) from the clone."""
    src = clone_dir / CLI_SRC_SUBPATH
    if not src.is_dir():
        typer.secho(
            f"Upstream layout changed — {CLI_SRC_SUBPATH} not found in clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    dst_relay = relay_os / ".relay"
    dst_src = dst_relay / "src" / "relay"
    if dst_src.exists():
        shutil.rmtree(dst_src)
    dst_src.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst_src)

    for fname in ("pyproject.toml", "requirements.txt"):
        upstream_file = clone_dir / fname
        if upstream_file.is_file():
            shutil.copy2(upstream_file, dst_relay / fname)


def packaged_template_root() -> Traversable:
    """Return the relay-os template tree embedded in the installed package."""
    root = files(TEMPLATE_RESOURCE_PACKAGE).joinpath(*TEMPLATE_RESOURCE_PATH)
    if not root.is_dir():
        typer.secho(
            "Installed relay package is missing templates/relay-os resources.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return root


def copy_fresh_templates(src_root: Traversable, relay_os: Path) -> None:
    """Copy the full packaged relay-os template tree into a fresh repo."""
    _copy_resource_tree(src_root, relay_os)
    _chmod_packaged_executables(relay_os)


def refresh_templates(
    relay_os: Path, src_root: Traversable | None = None
) -> tuple[list[str], list[str]]:
    """Refresh relay-owned creates under `relay_os` from package resources.

    Five things are treated as upstream-owned (always overwritten on update):
      - `_*` template creates (`_template/` etc.)
      - `bootstrap/` — the relay-vendored umbrella. Holds launch targets plus
        package-backed core skills and contexts
        (`bootstrap/skills/`, `bootstrap/contexts/*`). Optional domain skills
        are installed into `skills/` through the managed-skill manifest instead
        of being mirrored from templates. `_copy_vendored_bootstrap` mirrors
        the package-backed bootstrap tree as one unit. Runtime resolvers read
        local user roots first and this bundled root second.
      - `VENDORED_RECURRING_TEMPLATES` — named relay-owned recurring batteries
        (for example `recurring/dream/ticket.md`) that sit outside `bootstrap/` and carry
        no `_` prefix, refreshed by `_copy_vendored_recurring`. The sibling
        `blackboard.md`/`log.md` files are per-repo and left untouched.
      - `VENDORED_WORKFLOW_TEMPLATES` — named relay-owned workflows referenced
        by those batteries, refreshed by `_copy_vendored_workflows`.
      - `VENDORED_SKILL_TEMPLATES` — named relay-owned skills required by
        those workflows, refreshed by `_copy_vendored_skills`.
      - `.gitignore` — must track upstream so new ignore entries land in
        existing repos without manual edits.

    Returns `(copied, pruned)`: `pruned` lists `_*` creates removed because
    upstream no longer ships them (renames, deletions).
    """
    src_root = src_root or packaged_template_root()
    copied = _copy_templates(src_root, relay_os)
    copied.extend(refresh_gitignored_mirrors(relay_os, src_root))
    copied.extend(_copy_vendored_workflows(src_root, relay_os))
    copied.extend(_copy_vendored_skills(src_root, relay_os))
    copied.extend(_copy_upstream_files(src_root, relay_os))
    pruned = _prune_removed_templates(src_root, relay_os)
    return copied, pruned


def refresh_gitignored_mirrors(
    relay_os: Path, src_root: Traversable | None = None
) -> list[str]:
    """Refresh the package-backed mirrors that don't collide with the Relay
    source checkout's git-tracked fixtures.

    `bootstrap/` and the `VENDORED_RECURRING_TEMPLATES` are gitignored under
    `relay-os/` in Relay's own repo — their source of truth lives in
    `src/relay/resources/templates/relay-os/`. They still need to be
    materialized into `relay-os/` for runtime resolution; without them
    `relay launch bootstrap/orient` (i.e. `relay chat`) and `relay dream`
    have nothing to find in a fresh source clone.

    `refresh_templates` calls this alongside the tracked-fixture work; the
    source-checkout path in `init._refresh_one` calls it on its own.
    """
    src_root = src_root or packaged_template_root()
    copied = _copy_vendored_bootstrap(src_root, relay_os)
    copied.extend(_copy_vendored_recurring(src_root, relay_os))
    return copied


def prune_obsolete(relay_os: Path) -> list[str]:
    """Remove paths upstream once shipped but no longer does. Returns relative paths pruned."""
    pruned: list[str] = []
    rels = list(OBSOLETE_PATHS)
    rels.extend(_bootstrap_symlink_paths(relay_os))
    for rel in dict.fromkeys(rels):
        target = relay_os / rel
        if target.is_symlink() or target.is_file():
            target.unlink()
            pruned.append(rel)
        elif target.is_dir():
            shutil.rmtree(target)
            pruned.append(rel)
    return pruned


def _bootstrap_symlink_paths(relay_os: Path) -> list[str]:
    """Existing generated bootstrap exposure links are obsolete; real dirs are not."""
    out: list[str] = []
    for root_name, bootstrap_name in (("skills", "skills"), ("contexts", "contexts")):
        root = relay_os / root_name
        bootstrap_root = (relay_os / "bootstrap" / bootstrap_name).resolve()
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_symlink():
                continue
            try:
                target = child.resolve(strict=False)
            except OSError:
                continue
            try:
                target.relative_to(bootstrap_root)
            except ValueError:
                continue
            out.append(child.relative_to(relay_os).as_posix())
    return sorted(out)


def is_relay_source_checkout(relay_os: Path) -> bool:
    """Return True when `relay_os` belongs to Relay's own source checkout.

    `relay init --update` is also the installer refresh command developers run
    from this repo. In installed repos, obsolete upstream-managed paths should
    be pruned and replaced by bootstrap/ compat symlinks. In the Relay source
    repo, those same paths are source fixtures tracked by git, so pruning them
    damages the checkout.
    """
    root = relay_os.parent
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False

    try:
        data = tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return False

    project = data.get("project")
    if not isinstance(project, dict) or project.get("name") != "relay-os":
        return False

    return (
        (root / "src" / "relay" / "commands" / "init.py").is_file()
        and (root / "src" / "relay" / "commands" / "update.py").is_file()
        and (root / "src" / "relay" / "resources" / "templates" / "relay-os").is_dir()
    )


HOST_GITIGNORE_BEGIN = "# >>> relay-managed >>>"
HOST_GITIGNORE_END = "# <<< relay-managed <<<"
_HOST_GITIGNORE_BODY = (
    f"{HOST_GITIGNORE_BEGIN}\n"
    "# Managed by `relay init [--update]`. Don't edit between these markers —\n"
    "# they will be overwritten. Symlinks below are created by `relay init` so\n"
    "# agent CLIs (Claude Code, Codex) can discover Relay's generated skill view.\n"
    ".claude/skills/relay\n"
    ".codex/skills/relay\n"
    f"{HOST_GITIGNORE_END}\n"
)


def ensure_host_gitignore(target: Path) -> bool:
    """Insert/refresh the relay-managed block in `<target>/.gitignore`.

    Idempotent: leaves the file alone when the existing block already matches.
    Only runs inside a git repo — outside one a host `.gitignore` is moot.
    Returns True iff the file was modified.
    """
    if not (target / ".git").exists():
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
    """Strip the relay-managed block from `<target>/.gitignore`. Inverse of
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
    """Drop `bin/relay` — a relative symlink to the venv's `relay` console script.

    Resolved chain at runtime: `<.relay>/bin/relay` → `<.relay>/.venv/bin/relay`,
    whose pip-generated shebang points at `<.relay>/.venv/bin/python`. Works even
    when `bin/relay` itself is reached via another symlink (e.g. `~/.local/bin`).
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "relay"
    if wrapper.exists() or wrapper.is_symlink():
        wrapper.unlink()
    wrapper.symlink_to(Path("..") / ".venv" / "bin" / "relay")


def install_venv(relay_os: Path) -> Path:
    """Create `.relay/.venv/` and `pip install` the vendored relay package into it.

    Idempotent: re-running upgrades the venv in place. If the existing venv was
    built against a different Python X.Y than the current interpreter, it gets
    rebuilt from scratch (pip-installed packages from the old version aren't
    portable, and a host Python upgrade can leave a broken interpreter symlink).
    Returns the venv path. Exits with a clear error if Python venv/pip aren't usable.
    """
    dst_relay = relay_os / ".relay"
    venv_dir = dst_relay / ".venv"
    pyproject = dst_relay / "pyproject.toml"
    if not pyproject.is_file():
        typer.secho(
            f"Cannot bootstrap venv: missing {pyproject}.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    host_version = sys.version_info[:2]
    venv_version = _venv_python_version(venv_dir)
    venv_python = venv_dir / "bin" / "python"
    if venv_dir.exists() and (
        not venv_python.is_file()
        or (venv_version is not None and venv_version != host_version)
    ):
        if venv_version is not None and venv_version != host_version:
            typer.echo(
                f"Recreating venv (was Python {venv_version[0]}.{venv_version[1]}, "
                f"now {host_version[0]}.{host_version[1]})…"
            )
        shutil.rmtree(venv_dir)

    if not venv_python.is_file():
        typer.echo(f"Creating venv at {venv_dir}…")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            typer.secho(
                f"venv creation failed:\n{result.stderr}",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)

    typer.echo("Installing vendored CLI into venv (pip install)…")
    result = subprocess.run(
        [
            str(venv_dir / "bin" / "python"),
            "-m", "pip", "install",
            "--quiet", "--upgrade",
            str(dst_relay),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.secho(
            f"pip install failed:\n{result.stderr}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    install_skill_requirements(relay_os, venv_dir)
    return venv_dir


def install_skill_requirements(relay_os: Path, venv_dir: Path) -> list[Path]:
    """pip-install every skill's `requirements.txt` into the venv.

    A skill declares its own Python dependencies in a top-level
    `requirements.txt`; this pass is what actually puts those deps in the venv
    the skills run under, so a *bootstrapped* skill brings its own deps with it
    (there is no other per-skill install hook). Scans both skill roots:
    project-local `relay-os/skills/` and bundled `relay-os/bootstrap/skills/`.
    Called at the tail of `install_venv`, so both `relay init` (fresh) and
    `relay init --update` pick up newly added skill requirements.

    Idempotent — pip skips already-satisfied requirements. Exits with a clear
    error on a failed install, matching `install_venv`'s fail-loud contract.
    Returns the requirement files that were installed (sorted), for callers
    and tests.
    """
    roots = [relay_os / "skills", relay_os / "bootstrap" / "skills"]
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
        typer.echo(f"Installing skill deps from {req.relative_to(relay_os)}…")
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
                f"pip install -r {req} failed:\n{result.stderr}",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)
    return req_files


# pipx tracks installs by the package distribution name from `pyproject.toml`,
# not the entry-point binary name. Our binary is `relay`, our package is
# `relay-os`. Confusingly: `pipx upgrade relay` errors with "Package is not
# installed" even when the user definitely has it via pipx — they installed
# `relay-os`. Always pass the distribution name to `pipx`.
RELAY_PIPX_PACKAGE = "relay-os"


def running_cli_location(relay_os: Path) -> tuple[str, Path]:
    """Identify which install of `relay` is currently executing.

    Returns `(kind, venv_root)`:
      - `("vendored", <relay_os>/.relay/.venv)` — running the vendored copy
        the just-completed `init --update` already refreshed.
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
    vendored = (relay_os / ".relay" / ".venv").absolute()
    if venv == vendored:
        return ("vendored", venv)
    if (venv / "pipx_metadata.json").is_file():
        return ("pipx", venv)
    return ("other", venv)


def upgrade_global_cli(kind: str) -> tuple[str, str | None]:
    """Best-effort upgrade of the running `relay` install. Never raises.

    Returns `(status, detail)`:
      - `("vendored", None)` — running the vendored copy; no-op.
      - `("pipx-upgraded", stdout)` — `pipx upgrade relay-os` succeeded.
      - `("pipx-failed", stderr)` — pipx ran but returned non-zero.
      - `("pipx-missing", None)` — looked like pipx but `pipx` isn't on PATH.
      - `("other", None)` — caller prints manual instructions.
    """
    if kind == "vendored":
        return ("vendored", None)
    if kind == "other":
        return ("other", None)
    pipx = shutil.which("pipx")
    if pipx is None:
        return ("pipx-missing", None)
    typer.echo(f"Upgrading your global `relay` (pipx upgrade {RELAY_PIPX_PACKAGE})…")
    result = subprocess.run(
        [pipx, "upgrade", RELAY_PIPX_PACKAGE],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ("pipx-failed", (result.stderr or result.stdout).strip() or None)
    return ("pipx-upgraded", result.stdout.strip() or None)


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


def _copy_templates(src_root: Traversable, dst_root: Path) -> list[str]:
    """Copy every `_*` create under `src_root` into `dst_root`.

    Always overwrites; matches nested under another `_*` ancestor are skipped
    so each create is processed once.
    """
    copied: list[str] = []
    for rel, src in _walk_resources(src_root):
        if not rel.name.startswith("_"):
            continue
        if any(part.startswith("_") for part in rel.parts[:-1]):
            continue

        dst = dst_root / rel
        if src.is_dir():
            _remove_existing(dst)
            _copy_resource_tree(src, dst)
            copied.extend(str(file_rel) for file_rel, _ in _walk_resource_files(src, rel))
        else:
            _copy_resource_file(src, dst)
            copied.append(str(rel))

    return copied


def _prune_removed_templates(src_root: Traversable, dst_root: Path) -> list[str]:
    """Remove top-level `_*` creates in `dst_root` that upstream no longer ships.

    Catches renames and deletions: a `_template/` removed from package resources
    stays in user repos forever otherwise, since `_copy_templates` is purely
    additive. Only inspects top-level `_*` matches (same convention as
    `_copy_templates`) so nested entries inside a create are owned by their
    parent. Skips trees that are managed by a different mechanism — `.relay/` is
    vendored wholesale by `refresh_cli` and ships its own template fixtures, and
    `bootstrap/` is mirrored as a unit by `_copy_bootstrap`.
    """
    if not dst_root.is_dir():
        return []
    candidates: list[Path] = []
    for dst in dst_root.rglob("_*"):
        rel = dst.relative_to(dst_root)
        if any(part.startswith("_") for part in rel.parts[:-1]):
            continue
        if rel.parts and rel.parts[0] in (".relay", "bootstrap"):
            continue
        candidates.append(dst)

    pruned: list[str] = []
    for dst in candidates:
        rel = dst.relative_to(dst_root)
        if _resource_exists(src_root, rel):
            continue
        _remove_existing(dst)
        pruned.append(str(rel))
    return pruned


RELAY_GITIGNORE_BEGIN = "# >>> relay-managed >>>"
RELAY_GITIGNORE_END = "# <<< relay-managed <<<"
_RELAY_GITIGNORE_HEADER = (
    "# Managed by `relay init [--update]`. Don't edit between these markers —\n"
    "# they will be overwritten on update. Add your own ignore rules below the\n"
    "# end marker.\n"
)


def _copy_upstream_files(src_root: Traversable, dst_root: Path) -> list[str]:
    """Refresh upstream-managed root files inside `dst_root`.

    Currently just `.gitignore`, which is merged into a relay-managed marker
    block — preserving any user-added entries outside the block and deduping
    entries the user may have copied in before the block existed.
    """
    if _refresh_relay_gitignore(src_root, dst_root):
        return [".gitignore"]
    return []


def _refresh_relay_gitignore(src_root: Traversable, dst_root: Path) -> bool:
    """Insert/refresh the relay-managed block in `relay-os/.gitignore`.

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

    body = _render_relay_gitignore_body(src_root)
    block = f"{RELAY_GITIGNORE_BEGIN}\n{body}{RELAY_GITIGNORE_END}\n"

    dst = dst_root / ".gitignore"
    existing = dst.read_text() if dst.is_file() else ""

    begin = existing.find(RELAY_GITIGNORE_BEGIN)
    if begin == -1:
        # Pre-marker file (or fresh repo). Treat the whole thing as user
        # content, dedupe against managed entries, and prepend the block.
        managed_entries = _parse_gitignore_entries(body)
        managed_entries.update(_LEGACY_RELAY_GITIGNORE_ENTRIES)
        deduped = _drop_matching_lines(existing, managed_entries)
        if deduped and not deduped.endswith("\n"):
            deduped += "\n"
        new = block + (("\n" + deduped) if deduped else "")
    else:
        end = existing.find(RELAY_GITIGNORE_END, begin)
        if end == -1:
            new = existing[:begin] + block
        else:
            end += len(RELAY_GITIGNORE_END)
            if end < len(existing) and existing[end] == "\n":
                end += 1
            new = existing[:begin] + block + existing[end:]

    if new == existing:
        return False
    dst.write_text(new)
    return True


def _render_relay_gitignore_body(src_root: Traversable) -> str:
    src = _resource_join(src_root, Path(".gitignore"))
    upstream_text = src.read_text().rstrip()
    body = _RELAY_GITIGNORE_HEADER
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


def _copy_vendored_bootstrap(src_root: Traversable, dst_root: Path) -> list[str]:
    """Mirror the `bootstrap/` umbrella — wipe, copy fresh.

    `bootstrap/` is the single home for package-backed control-plane batteries
    Relay vendors and updates wholesale: launch targets
    (`bootstrap/<name>/ticket.md`), the core skills they reference
    (`bootstrap/skills/`), and canonical contexts (`bootstrap/contexts/*`).
    Optional domain skills are installed into `skills/` by the managed-skill
    manifest and updater, not copied through this mirror.
    Runtime resolution reads local roots first, then this package-backed tree.

    Wholesale replacement means renames and removals propagate cleanly. Don't
    put custom content under `bootstrap/` — it'll be wiped. Custom skills
    belong in `skills/<your-ns>/`, custom contexts in `contexts/<your-ns>/`.
    """
    copied = _wholesale_mirror(src_root, dst_root, ("bootstrap",))
    _chmod_packaged_executables(dst_root)
    return copied


def _copy_vendored_recurring(src_root: Traversable, dst_root: Path) -> list[str]:
    """Refresh the named relay-owned recurring templates listed in
    `VENDORED_RECURRING_TEMPLATES`.

    These are live Relay
    batteries, not `_*` samples and not under `bootstrap/`, so the other
    refresh passes skip them. Overwrite wholesale: the file is upstream-managed
    (e.g. Dream's known-skill list), not per-repo customizable — REM is the
    repo-specific recurring loop. This also restores the file in repos that
    predate it. Only `ticket.md` is listed, so a recurring task's per-repo
    `blackboard.md`/`log.md` siblings survive the refresh untouched.

    Missing srcs are skipped — a template the package no longer ships isn't an
    error here.
    """
    copied: list[str] = []
    for rel in VENDORED_RECURRING_TEMPLATES:
        src = _resource_join(src_root, Path(rel))
        if not src.is_file():
            continue
        _copy_resource_file(src, dst_root / rel)
        copied.append(rel)
    return copied


def _copy_vendored_workflows(src_root: Traversable, dst_root: Path) -> list[str]:
    """Refresh the named relay-owned workflows listed in
    `VENDORED_WORKFLOW_TEMPLATES`.

    These are workflow files that a vendored recurring template needs in order
    to launch. Missing srcs are skipped so older package resources remain
    tolerable during development.
    """
    copied: list[str] = []
    for rel in VENDORED_WORKFLOW_TEMPLATES:
        src = _resource_join(src_root, Path(rel))
        if not src.is_file():
            continue
        _copy_resource_file(src, dst_root / rel)
        copied.append(rel)
    return copied


def _copy_vendored_skills(src_root: Traversable, dst_root: Path) -> list[str]:
    """Refresh the named relay-owned skills listed in
    `VENDORED_SKILL_TEMPLATES`.

    These are skill files that vendored workflows need in order to launch.
    Missing srcs are skipped so older package resources remain tolerable during
    development.
    """
    copied: list[str] = []
    for rel in VENDORED_SKILL_TEMPLATES:
        src = _resource_join(src_root, Path(rel))
        if not src.is_file():
            continue
        _copy_resource_file(src, dst_root / rel)
        copied.append(rel)
    return copied


def _wholesale_mirror(
    src_root: Traversable, dst_root: Path, rels: tuple[str, ...]
) -> list[str]:
    """Wipe-and-copy each `rel` from `src_root` into `dst_root`. Skip missing srcs."""
    copied: list[str] = []
    for rel in rels:
        src = _resource_join(src_root, Path(rel))
        if not src.is_dir():
            continue
        dst = dst_root / rel
        _remove_existing(dst)
        _copy_resource_tree(src, dst)
        copied.extend(str(file_rel) for file_rel, _ in _walk_resource_files(src, Path(rel)))
    return copied


def _resource_join(root: Traversable, rel: Path) -> Traversable:
    node = root
    for part in rel.parts:
        node = node.joinpath(part)
    return node


def _resource_exists(root: Traversable, rel: Path) -> bool:
    node = _resource_join(root, rel)
    return node.is_dir() or node.is_file()


def _walk_resources(
    root: Traversable, base: Path = Path()
) -> list[tuple[Path, Traversable]]:
    found: list[tuple[Path, Traversable]] = []
    for child in root.iterdir():
        rel = base / child.name
        found.append((rel, child))
        if child.is_dir():
            found.extend(_walk_resources(child, rel))
    return found


def _walk_resource_files(
    root: Traversable, base: Path = Path()
) -> list[tuple[Path, Traversable]]:
    return [(rel, node) for rel, node in _walk_resources(root, base) if node.is_file()]


def _copy_resource_tree(src: Traversable, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
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


def _chmod_packaged_executables(relay_os: Path) -> None:
    scripts_dir = relay_os / "scripts"
    if scripts_dir.is_dir():
        for script in scripts_dir.glob("*.sh"):
            _chmod_executable(script)


def _chmod_executable(path: Path) -> None:
    try:
        path.chmod(0o755)
    except OSError:
        pass
