"""Bootstrap helpers used by `relay init` (with or without --update).

Pulls upstream into `relay-os/.relay/` and stands up the self-contained venv
the vendored CLI runs out of. No Typer commands live here.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer


RELAY_REPO_URL = "https://github.com/FastJVM/relay"
TEMPLATE_SUBPATH = Path("src/relay/resources/templates/relay-os")
CLI_SRC_SUBPATH = Path("src/relay")

# Paths (relative to relay-os/) that earlier upstreams shipped but no longer do.
# `init --update` prunes these from existing repos so removed scaffolding doesn't
# linger after a migration. Keep entries narrow — only files we know we shipped
# and now want gone, never user-owned paths.
OBSOLETE_PATHS: tuple[str, ...] = (
    "counter",  # numeric task ID counter, dropped in the slug-only migration
    "meta",  # renamed to bootstrap/ — pre-bootstrap upstreams shipped meta/
    "skills/bootstrap/create",  # renamed to bootstrap/ticket in 350c4ed
)


def clone_upstream(into: Path) -> Path:
    """Shallow-clone the relay repo into `into`. Exit on failure. Return the path."""
    typer.echo(f"Cloning {RELAY_REPO_URL} (shallow)…")
    result = subprocess.run(
        ["git", "clone", "--depth=1", RELAY_REPO_URL, str(into)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        typer.secho(
            f"git clone failed:\n{result.stderr}",
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


def write_pin(relay_os: Path, sha: str | None) -> Path | None:
    """Record the upstream commit `relay-os/.relay/` was vendored from.

    Skips the write if `sha` is None (clone-without-git in tests, mostly).
    Returns the pin path on success.
    """
    if sha is None:
        return None
    pin = relay_os / ".relay" / "RELAY_PIN"
    pin.parent.mkdir(parents=True, exist_ok=True)
    pin.write_text(f"{RELAY_REPO_URL}\n{sha}\n")
    return pin


def read_pin(relay_os: Path) -> str | None:
    """Return the pinned upstream SHA from `.relay/RELAY_PIN`, or None if absent/garbled."""
    pin = relay_os / ".relay" / "RELAY_PIN"
    if not pin.is_file():
        return None
    lines = [line.strip() for line in pin.read_text().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    return lines[1]


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


def refresh_templates(clone_dir: Path, relay_os: Path) -> tuple[list[str], list[str]]:
    """Refresh relay-owned scaffolds under `relay_os/` from the clone.

    Four things are treated as upstream-owned (always overwritten on update):
      - `_*` template scaffolds (`_template/` etc.)
      - `bootstrap/` shims and the `skills/bootstrap/` skills they reference —
        relay-owned infra, not user content. Mirrored as a unit by
        `_copy_bootstrap`.
      - `skills/retro/` — shipped prompt-only retro skills. Mirrored by
        `_copy_retro_skills`.
      - `contexts/relay/{architecture,principles,cli}/` — the canonical
        relay-the-tool contexts that ship with relay. Mirrored by
        `_copy_relay_contexts`.
      - `.gitignore` — must track upstream so new ignore entries land in
        existing repos without manual edits.

    Returns `(copied, pruned)`: `pruned` lists `_*` scaffolds removed because
    upstream no longer ships them (renames, deletions).
    """
    src_root = clone_dir / TEMPLATE_SUBPATH
    if not src_root.is_dir():
        typer.secho(
            f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    copied = _copy_templates(src_root, relay_os)
    copied.extend(_copy_bootstrap(src_root, relay_os))
    copied.extend(_copy_retro_skills(src_root, relay_os))
    copied.extend(_copy_relay_contexts(src_root, relay_os))
    copied.extend(_copy_relay_hooks(src_root, relay_os))
    copied.extend(_copy_upstream_files(src_root, relay_os))
    pruned = _prune_removed_templates(src_root, relay_os)
    return copied, pruned


def prune_obsolete(relay_os: Path) -> list[str]:
    """Remove paths upstream once shipped but no longer does. Returns relative paths pruned."""
    pruned: list[str] = []
    for rel in OBSOLETE_PATHS:
        target = relay_os / rel
        if target.is_symlink() or target.is_file():
            target.unlink()
            pruned.append(rel)
        elif target.is_dir():
            shutil.rmtree(target)
            pruned.append(rel)
    return pruned


HOST_GITIGNORE_BEGIN = "# >>> relay-managed >>>"
HOST_GITIGNORE_END = "# <<< relay-managed <<<"
_HOST_GITIGNORE_BODY = (
    f"{HOST_GITIGNORE_BEGIN}\n"
    "# Managed by `relay init [--update]`. Don't edit between these markers —\n"
    "# they will be overwritten. Symlinks below are created by `relay init` so\n"
    "# agent CLIs (Claude Code, Codex) can discover relay-os/skills/.\n"
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
    return venv_dir


def running_cli_location(relay_os: Path) -> tuple[str, Path]:
    """Identify which install of `relay` is currently executing.

    Returns `(kind, venv_root)`:
      - `("vendored", <relay_os>/.relay/.venv)` — running the vendored copy
        the just-completed `init --update` already refreshed.
      - `("pipx", <pipx-venv>)` — installed via pipx; we can offer to upgrade.
      - `("other", <venv_root>)` — pip / system python / something else; the
        caller should print a manual-upgrade hint.

    Detection uses `sys.executable`'s parent venv. pipx leaves a
    `pipx_metadata.json` at every managed venv's root — that's the canonical
    marker, and what `pipx upgrade` itself relies on.
    """
    venv = Path(sys.executable).resolve().parent.parent
    try:
        vendored = (relay_os / ".relay" / ".venv").resolve()
    except OSError:
        vendored = relay_os / ".relay" / ".venv"
    if venv == vendored:
        return ("vendored", venv)
    if (venv / "pipx_metadata.json").is_file():
        return ("pipx", venv)
    return ("other", venv)


def upgrade_global_cli(kind: str) -> tuple[str, str | None]:
    """Best-effort upgrade of the running `relay` install. Never raises.

    Returns `(status, detail)`:
      - `("vendored", None)` — running the vendored copy; no-op.
      - `("pipx-upgraded", stdout)` — `pipx upgrade relay` succeeded.
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
    typer.echo("Upgrading your global `relay` (pipx)…")
    result = subprocess.run(
        [pipx, "upgrade", "relay"],
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


def _copy_templates(src_root: Path, dst_root: Path) -> list[str]:
    """Copy every `_*` scaffold under `src_root` into `dst_root`.

    Always overwrites; matches nested under another `_*` ancestor are skipped
    so each scaffold is processed once.
    """
    copied: list[str] = []
    for src in src_root.rglob("_*"):
        rel = src.relative_to(src_root)
        if any(part.startswith("_") for part in rel.parts[:-1]):
            continue

        dst = dst_root / rel
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            for f in src.rglob("*"):
                if f.is_file():
                    copied.append(str(f.relative_to(src_root)))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(str(rel))

    return copied


def _prune_removed_templates(src_root: Path, dst_root: Path) -> list[str]:
    """Remove top-level `_*` scaffolds in `dst_root` that upstream no longer ships.

    Catches renames and deletions: a `_template/` removed upstream stays in user
    repos forever otherwise, since `_copy_templates` is purely additive. Only
    inspects top-level `_*` matches (same convention as `_copy_templates`) so
    nested entries inside a scaffold are owned by their parent. Skips trees that
    are managed by a different mechanism — `.relay/` is vendored wholesale by
    `refresh_cli` and ships its own template fixtures, and `bootstrap/` is
    mirrored as a unit by `_copy_bootstrap`.
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
        if (src_root / rel).exists():
            continue
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
        pruned.append(str(rel))
    return pruned


RELAY_GITIGNORE_BEGIN = "# >>> relay-managed >>>"
RELAY_GITIGNORE_END = "# <<< relay-managed <<<"
_RELAY_GITIGNORE_HEADER = (
    "# Managed by `relay init [--update]`. Don't edit between these markers —\n"
    "# they will be overwritten on update. Add your own ignore rules below the\n"
    "# end marker.\n"
)


def _copy_upstream_files(src_root: Path, dst_root: Path) -> list[str]:
    """Refresh upstream-managed root files inside `dst_root`.

    Currently just `.gitignore`, which is merged into a relay-managed marker
    block — preserving any user-added entries outside the block and deduping
    entries the user may have copied in before the block existed.
    """
    if _refresh_relay_gitignore(src_root, dst_root):
        return [".gitignore"]
    return []


def _refresh_relay_gitignore(src_root: Path, dst_root: Path) -> bool:
    """Insert/refresh the relay-managed block in `relay-os/.gitignore`.

    Pattern mirrors `ensure_host_gitignore`: the block is fenced by markers
    and replaced wholesale on each update; lines outside the markers are
    user-owned and preserved. Lines outside the block that exactly match a
    managed entry are dropped — handles repos that predate the marker
    convention or had the upstream content copied in directly.

    Returns True iff the file was modified.
    """
    src = src_root / ".gitignore"
    if not src.is_file():
        return False

    upstream_text = src.read_text()
    body = _RELAY_GITIGNORE_HEADER + upstream_text
    if not body.endswith("\n"):
        body += "\n"
    block = f"{RELAY_GITIGNORE_BEGIN}\n{body}{RELAY_GITIGNORE_END}\n"

    dst = dst_root / ".gitignore"
    existing = dst.read_text() if dst.is_file() else ""

    begin = existing.find(RELAY_GITIGNORE_BEGIN)
    if begin == -1:
        # Pre-marker file (or fresh repo). Treat the whole thing as user
        # content, dedupe against managed entries, and prepend the block.
        managed_entries = _parse_gitignore_entries(upstream_text)
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


def _copy_bootstrap(src_root: Path, dst_root: Path) -> list[str]:
    """Mirror the `bootstrap/`-namespace tree from upstream — wipe, copy fresh.

    Covers two paths, both relay-owned infra (not user content):
      - `bootstrap/` — launch shims for relay-owned skills.
      - `skills/bootstrap/` — the skills those shims reference.

    Each is wholesale-replaced on update so renames and removals propagate
    cleanly. Don't put custom shims or custom skills under `bootstrap/`
    namespaces — they'll be pruned. Custom skills go elsewhere under
    `skills/` (e.g. `skills/code/...`).
    """
    return _wholesale_mirror(src_root, dst_root, ("bootstrap", "skills/bootstrap"))


def _copy_retro_skills(src_root: Path, dst_root: Path) -> list[str]:
    """Mirror Relay-owned retro prompt skills."""
    return _wholesale_mirror(src_root, dst_root, ("skills/retro",))


# Canonical relay-the-tool contexts: same content shipped to every relay-os/.
# Other namespaces under `contexts/` are user-owned and never touched here.
_RELAY_OWNED_CONTEXTS: tuple[str, ...] = (
    "contexts/relay/architecture",
    "contexts/relay/principles",
    "contexts/relay/cli",
)


def _copy_relay_contexts(src_root: Path, dst_root: Path) -> list[str]:
    """Mirror the canonical `contexts/relay/*` contexts from upstream.

    These describe relay-the-tool (mental model, principles, CLI surface) and
    ship as-is to every relay-os/ so the `bootstrap/orient` shim's references
    resolve. User-authored contexts under other `contexts/<namespace>/` paths
    are untouched.
    """
    return _wholesale_mirror(src_root, dst_root, _RELAY_OWNED_CONTEXTS)


def _copy_relay_hooks(src_root: Path, dst_root: Path) -> list[str]:
    """Mirror `hooks/` from upstream — the git-hook scripts relay installs.

    Currently just `post-merge` (auto-bumps tickets whose PR has merged).
    Symlinked into `.git/hooks/` by `relay init`; the file lives here so it
    travels with the repo and updates land via `init --update`.
    """
    copied = _wholesale_mirror(src_root, dst_root, ("hooks",))
    # `_wholesale_mirror` uses `shutil.copytree` whose default `copy2` honors
    # mode bits, but be defensive: hooks are useless if not executable.
    hooks_dir = dst_root / "hooks"
    if hooks_dir.is_dir():
        for hook in hooks_dir.iterdir():
            if hook.is_file():
                try:
                    hook.chmod(0o755)
                except OSError:
                    pass
    return copied


def _wholesale_mirror(
    src_root: Path, dst_root: Path, rels: tuple[str, ...]
) -> list[str]:
    """Wipe-and-copy each `rel` from `src_root` into `dst_root`. Skip missing srcs."""
    copied: list[str] = []
    for rel in rels:
        src = src_root / rel
        if not src.is_dir():
            continue
        dst = dst_root / rel
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        copied.extend(
            str(f.relative_to(src_root))
            for f in src.rglob("*")
            if f.is_file()
        )
    return copied
