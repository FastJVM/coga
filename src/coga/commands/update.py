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


# The reviewed scaffold allowlist: the only package paths `coga init` copies
# into a fresh repo, each for a concrete reason (`coga/init`, "Fresh repo").
# Reusable definitions (contexts, skills, workflows, bootstrap tickets,
# recurring jobs and their scripts/runbooks) are never on it: they resolve from
# the installed package, so an upgrade changes them without copying.
FRESH_SCAFFOLDS: tuple[str, ...] = (
    "coga.toml",               # the repo's own configuration seed
    "context.md",              # the repo context seed
    "log.md",                  # real, initially empty audit history
    ".gitattributes",          # physical merge attributes Git requires
    ".gitignore",              # physical ignore rules (managed block)
    "contexts/.gitignore",     # keeps an empty (relocatable) contexts root tracked
    "contexts/_template",      # ignored authoring starter
    "skills/_template",        # ignored authoring starter
    "workflows/_template.md",  # ignored authoring starter
    "tasks/coga-build.md",     # mutable onboarding task (pruned on filled repos)
)

# Bundled recurring jobs a fresh repo selects explicitly (`recurring/jobs.toml`).
# Written once by init; upgrades never refresh it, so a job bundled later stays
# disabled until a repo selects it. Owner review decides this default list.
FRESH_RECURRING_SELECTION: tuple[str, ...] = (
    "address-pr-comments",
    "blackboard-size",
    "blocker-reminders",
    "dream",
    "phone-home",
    "resolve-conflicts",
    "skill-update",
    "trim-log",
)


def copy_fresh_templates(src_root: Traversable, coga_os: Path) -> None:
    """Copy the reviewed scaffolds (not reusable definitions) into a fresh repo."""
    coga_os.mkdir(parents=True, exist_ok=True)
    for rel in FRESH_SCAFFOLDS:
        src = src_root.joinpath(*rel.split("/"))
        dst = coga_os.joinpath(*rel.split("/"))
        if src.is_dir():
            _copy_resource_tree(src, dst)
        elif src.is_file():
            _copy_resource_file(src, dst)
    _write_fresh_job_selection(coga_os)
    _chmod_packaged_executables(coga_os)


def _write_fresh_job_selection(coga_os: Path) -> None:
    from coga.recurring import JOBS_FILE, render_job_selection

    path = coga_os / "recurring" / JOBS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_job_selection({name: True for name in FRESH_RECURRING_SELECTION}),
        encoding="utf-8", newline="\n",
    )


def nearest_existing_dir(target: Path) -> Path | None:
    """The nearest dir at/above `target` that exists on disk, or None.

    `coga init`'s target may not exist yet (`coga init tools/ops` creates the
    subdir), but `git -C` needs a real directory to run from; both `is_git_repo`
    and init's `_host_ignores_coga` probe git from this ancestor, so they share
    the walk.
    """
    return next((p for p in [target, *target.parents] if p.is_dir()), None)


def is_git_repo(target: Path) -> bool:
    """Check for a repository, worktree, or submodule marker in the ancestry."""
    from coga.config import find_checkout_root

    return (target / ".git").exists() or find_checkout_root(target) is not None


HOST_GITIGNORE_BEGIN = "# >>> coga-managed >>>"
HOST_GITIGNORE_END = "# <<< coga-managed <<<"
_HOST_GITIGNORE_BODY = (
    f"{HOST_GITIGNORE_BEGIN}\n"
    "# Managed by `coga init`. Don't edit between these markers —\n"
    "# they will be overwritten. Symlinks below are created by `coga init` so\n"
    "# agent CLIs (Claude Code, Codex) can discover Coga's generated skill view.\n"
    ".claude/skills/coga\n"
    ".codex/skills/coga\n"
    "# Machine-local Coga state: run records, megalaunch selection, durable\n"
    "# agent state (`.coga/data/`) and per-launch temporaries (`.coga/tmp/`,\n"
    "# purged when each launch ends).\n"
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
    existing = gi.read_text(encoding="utf-8") if gi.is_file() else ""

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
    gi.write_text(new, encoding="utf-8", newline="\n")
    return True


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
    existing = dst.read_text(encoding="utf-8") if dst.is_file() else ""

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
    dst.write_text(new, encoding="utf-8", newline="\n")
    return True


def _render_coga_gitignore_body(src_root: Traversable) -> str:
    src = _resource_join(src_root, Path(".gitignore"))
    upstream_text = src.read_text(encoding="utf-8").rstrip()
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
