"""Bootstrap helpers used by `coga init`.

Copies coga templates from the installed package resources into a repo and
manages the coga-owned `.gitignore` blocks. `coga init` scaffolds the markdown
OS; it does not install software. The operator's own `coga` — `uv tool install
coga`, pipx, or a pip install — is the one CLI that runs, in every repo. No
Typer commands live here.
"""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
import shutil
import subprocess
import sys
from pathlib import Path

import typer


COGA_REPO_URL = "https://github.com/FastJVM/coga"
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
    "# Machine-local Coga state: run records, megalaunch selection.\n"
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


COGA_PIPX_PACKAGE = "coga"


def running_cli_location() -> tuple[str, Path]:
    """Identify which install of `coga` is currently executing.

    Returns `(kind, venv_root)`:
      - `("pipx", <pipx-venv>)` — installed via pipx; we can offer to upgrade.
      - `("other", <venv_root>)` — pip / uv tool / system python; the caller
        should print a manual-upgrade hint.

    Detection uses the *unresolved* `sys.executable` parent venv. A pipx
    venv's `bin/python` is a symlink to the host Python (Homebrew, pyenv,
    system). Resolving the symlink lands in the host's framework dir and
    misses the `pipx_metadata.json` marker that lives in the venv root, which
    would collapse pipx and other onto the same directory.
    """
    venv = Path(sys.executable).absolute().parent.parent
    if (venv / "pipx_metadata.json").is_file():
        return ("pipx", venv)
    return ("other", venv)


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
