"""`coga init` — create a new coga repo, or finish setting up a clone of one.

`coga init` writes everything from scratch into `<path>/coga/`. Templates come
from the installed coga package. Init installs no Python packages or skills;
in an interactive terminal it offers (never forces) to install missing
external CLIs such as `gh` and an agent CLI, only after every precondition
has passed. On a repo whose `coga/` already exists it
refuses — unless the gitignored machine-local half
(`coga.local.toml` with a `user`, the agent skill symlinks) is missing, which
is what a fresh clone looks like: then `coga init --user NAME` creates only
that half and commits nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources.abc import Traversable
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import tomlkit
import typer

from coga.agent_cli_setup import offer_agent_cli
from coga.agent_skills import refresh_agent_skill_view
from coga.aliases import ONBOARDING_TASK
from coga.commands.update import (
    _refresh_coga_gitignore,
    copy_fresh_templates,
    ensure_host_gitignore,
    is_git_repo,
    nearest_existing_dir,
    packaged_template_root,
)
from coga.config import (
    Config,
    ConfigError,
    _parse_git,
    load_config,
    resolve_layout_contexts_path,
)
from coga.dependencies import (
    AGENT_CLIS,
    DEPENDENCIES,
    NEEDS_ROOT,
    PACKAGE_MANAGERS,
    Dependency,
    install_hint,
)
from coga.git import GitError, control_branch_present, symbolic_head
from coga.logfile import append_log


LOCAL_TOML_TEMPLATE = """\
# Machine-local config — gitignored. Holds your assignee name and any
# machine-local overrides. Override anything from coga.toml here without
# committing it.
user = ""

# Secrets are declared inline on each ticket's `secrets:` frontmatter
# (`NAME: op://vault/item/field` or `NAME: env:VAR`) — there is no central
# [secrets] catalog here.

# Per-agent permission-skip policy from older installs is removed. Current
# launch rejects those keys as unknown config because Coga no longer has a
# ticket-level unattended execution axis.

# Default agent for `coga ticket` authoring interviews on this machine — e.g.
# switch to codex while a Claude quota is exhausted. COGA_AUTHORING_AGENT wins
# over it; `coga ticket --agent` wins over both.
# [authoring]
# agent = "codex"
"""

_RELOCATED_CONTEXTS_GITIGNORE = """\
# Per-domain scaffolding templates (bare `_template`, `_template.md`).
**/_template/
**/_template.md
"""


def _clean_user_name(raw: str) -> str | None:
    """Strip `raw` and return it if it's a valid `user` value, else None.

    Valid = non-empty after stripping, no `"` or `\\` (both would break the
    `user = "..."` line in `coga.local.toml`). The single source of truth for
    what counts as a usable name, used by the `coga init --user` parameter.
    """
    name = raw.strip()
    if name and '"' not in name and "\\" not in name:
        return name
    return None


def _require_user_name(user: str | None) -> str:
    """Resolve the `--user` value for a direct `coga init`.

    `coga init` takes the operator's name as a parameter rather than prompting,
    so init stays scriptable. `--user NAME` is required and coga never guesses:
    a guessed name (git `user.name`, OS username) can disagree with the `owner`
    tokens written into tickets, so init fails loud when it is omitted rather
    than deriving one. `coga init --user NAME` is the one blessed way to set the
    name, and because init writes `user` before anything reads config it still
    works on a bare clone: an already-initialized repo whose gitignored
    `coga.local.toml` is missing takes the `_setup_initialized_clone` path
    instead of the re-init refusal. An invalid `--user` value is also a hard
    error.
    """
    if user is None:
        typer.secho(
            "`coga init` needs your name: pass `--user NAME` (e.g. `coga init "
            "--user marc`). This is the name tickets you create are owned by "
            "and attributed to; coga does not guess it.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    name = _clean_user_name(user)
    if name is None:
        typer.secho(
            "`--user NAME` must be non-empty and contain no quotes or "
            "backslashes (they would break the `user` line in coga.local.toml).",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return name


def render_local_toml(name: str) -> str:
    """`LOCAL_TOML_TEMPLATE` with the captured name substituted into `user`.

    `name` is the validated `--user` value (via `_require_user_name`), so it
    carries no `"`/`\\` and is safe to interpolate into the quoted TOML value.
    """
    return LOCAL_TOML_TEMPLATE.replace('user = ""', f'user = "{name}"', 1)


# Files/dirs that don't count as pre-existing user content when deciding
# whether a target dir is "empty" — `.git`/`.DS_Store` plus everything init
# itself creates. Anything else present before init runs marks the repo as
# already-filled (a real project), which suppresses onboarding-ticket seeding,
# except the hosting-provider scaffold `_is_hosting_scaffold` recognizes.
_INIT_IGNORE: frozenset[str] = frozenset(
    {".git", ".DS_Store", "coga", "CLAUDE.md", "AGENTS.md", ".claude", ".codex", ".gitignore"}
)

# Stock files a hosting provider's "Initialize this repository with..." option
# writes (GitHub: README, LICENSE, .gitignore, .gitattributes). License files
# and `.gitattributes` are scaffold whatever they hold.
_SCAFFOLD_PREFIXES: tuple[str, ...] = ("license", "licence", "copying")
_SCAFFOLD_NAMES: frozenset[str] = frozenset({".gitattributes"})

# A README counts as scaffold only while it is stub-sized: GitHub's is
# `# <name>` plus an optional description line. Anything larger is a real
# project README and marks the repo filled. The tradeoff is deliberate: a real
# project whose only content is a tiny README gets the (deletable) onboarding
# ticket, rather than a scaffolded repo losing it.
_SCAFFOLD_README_MAX_LINES = 3
_SCAFFOLD_README_MAX_BYTES = 1024


def _is_hosting_scaffold(entry: Path) -> bool:
    """True when `entry` is a stock hosting-provider scaffold file."""
    if not entry.is_file():
        return False
    lower = entry.name.lower()
    if lower in _SCAFFOLD_NAMES or lower.startswith(_SCAFFOLD_PREFIXES):
        return True
    if lower.startswith("readme"):
        try:
            data = entry.read_bytes()
        except OSError:
            return False
        if len(data) >= _SCAFFOLD_README_MAX_BYTES:
            return False
        lines = [ln for ln in data.decode("utf-8", "replace").splitlines() if ln.strip()]
        return len(lines) <= _SCAFFOLD_README_MAX_LINES
    return False


def _repo_is_empty(target: Path) -> bool:
    """True when `target` holds no pre-existing user content.

    Evaluated against the directory's pristine contents — call it before init
    writes any of its own files. A missing dir is empty; otherwise any entry
    outside `_INIT_IGNORE` that is not hosting scaffold means the repo is
    already a real project.
    """
    if not target.exists():
        return True
    return all(
        entry.name in _INIT_IGNORE or _is_hosting_scaffold(entry)
        for entry in target.iterdir()
    )


def _enclosing_coga_root(target: Path) -> Path | None:
    """Nearest dir at/above `target` that holds a `coga.toml`, or None.

    Guards `coga init` against scaffolding a `coga/` inside an existing coga
    OS tree — `find_repo_root` walks up, so the enclosing repo would claim the
    new one's subtree and the layout can't work sanely. Mirrors that discovery:
    at each candidate check both a direct `coga.toml` and a sibling `coga/`
    subdir (the common layout — a git repo whose coga lives at `<repo>/coga/`),
    since `find_repo_root` resolves the target through either. The first `.git`
    boundary stops the walk: an outer coga repo beyond the host repo's boundary
    is a different project and no conflict.
    """
    for candidate in [target, *target.parents]:
        if (candidate / "coga.toml").is_file():
            return candidate
        nested = candidate / "coga"
        if (nested / "coga.toml").is_file():
            return nested
        if (candidate / ".git").exists():
            return None
    return None


def _host_ignores_coga(target: Path) -> bool:
    """True when the host repo's ignore rules would exclude the coga/ dir we're
    about to create at `target`.

    `git add` refuses ignored paths, so if the host repo gitignores the target
    subtree (e.g. `coga init build/ops` where `build/` is ignored) we'd write
    coga/ to disk and then silently skip the commit — the very silent-skip the
    up-front git check exists to prevent. Detected here so `coga init` can fail
    loud before writing anything. `target` may not exist yet, so run
    `git check-ignore` from the nearest existing ancestor.
    """
    return _host_ignores_path(target / "coga")


def _host_ignores_path(path: Path) -> bool:
    """True when the enclosing checkout's ignore rules exclude `path`."""
    probe = nearest_existing_dir(path)
    if probe is None:
        return False
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(probe),
                "check-ignore",
                "-q",
                "--no-index",
                f"{path}{os.sep}",
            ],
            capture_output=True,
        )
    except OSError:
        return False
    return result.returncode == 0


# Delivered onboarding ticket, pruned from the copied tree on a filled repo
# (a real project doesn't want the bootstrap interview seeded for it).
_ONBOARDING_TICKET_DIRS: tuple[str, ...] = (ONBOARDING_TASK,)


def _prune_onboarding_tickets(coga_os: Path) -> list[str]:
    """Remove the delivered onboarding ticket dir(s) from a freshly copied tree.

    Returns the names removed (for the caller's report). Used on filled repos,
    where the bootstrap interview should not be seeded.
    """
    pruned: list[str] = []
    tasks = coga_os / "tasks"
    for name in _ONBOARDING_TICKET_DIRS:
        # A delivered onboarding task may be file-form (`tasks/<name>.md`) or
        # directory-form (`tasks/<name>/`).
        ticket_dir = tasks / name
        ticket_file = tasks / f"{name}.md"
        if ticket_dir.is_dir():
            shutil.rmtree(ticket_dir)
            pruned.append(name)
        elif ticket_file.is_file():
            ticket_file.unlink()
            pruned.append(name)
    return pruned


# Matches an `owner:` line whose value is exactly the `new-user` placeholder.
# `owner` is now the only human field a ticket carries. Deliberately does NOT
# match `replace-with-human-name` (the `_template`/recurring token, owned by
# `create_task`/recurring) — only the placeholder that would otherwise ship as a
# live value.
_NEW_USER_LINE = re.compile(r"^(owner):[ \t]*new-user[ \t]*$", re.M)


def _stamp_user_into_delivered_tickets(coga_os: Path, name: str) -> list[str]:
    """Replace the `new-user` placeholder with `name` in every delivered ticket.

    Rewrites `owner:` lines that read `new-user` across
    every delivered task ticket — both file-form `tasks/<slug>.md` and
    directory-form `tasks/**/ticket.md` — so the placeholder never ships as a
    live owner. Returns the slugs that were stamped.
    """
    stamped: list[str] = []
    # JSON string syntax is valid YAML string syntax. Always quote the captured
    # name so values such as ``yes``, ``Jane: Doe``, and ``Nick #1`` remain the
    # exact string written to coga.local.toml instead of becoming a boolean,
    # invalid YAML, or a value truncated by a YAML comment.
    encoded_name = json.dumps(name, ensure_ascii=False)
    tasks = coga_os / "tasks"
    if not tasks.is_dir():
        return stamped
    # `**/*.md` covers both shapes: a file-form `<slug>.md` and a directory-form
    # `<dir>/ticket.md` (both end in `.md`).
    for ticket in sorted(tasks.glob("**/*.md")):
        text = ticket.read_text()
        new_text, count = _NEW_USER_LINE.subn(
            lambda match: f"{match.group(1)}: {encoded_name}", text
        )
        if count:
            ticket.write_text(new_text)
            stamped.append(
                ticket.parent.name if ticket.name == "ticket.md" else ticket.stem
            )
    return stamped


# Orientation file dropped at the host repo root for agent CLIs that look for
# it there (Claude Code reads CLAUDE.md, Codex reads AGENTS.md, and recent
# Claude Code also picks up AGENTS.md). Identical content in both — three
# similar lines beats a clever symlink that breaks on Windows. Created only
# when missing; a user's hand-edited guide is never overwritten.
AGENT_GUIDE_TEMPLATE = """\
# Agent guide

This repo uses [coga](https://github.com/FastJVM/coga) to coordinate shared
task and context state between humans and agents. Most coordinated files live
under `coga/`; contexts live in the configured contexts directory —
`coga/contexts/` by default, or `[layout] contexts` in `coga/coga.toml`.

## Start here

Run `coga launch bootstrap/orient` to drop into a coga-aware session — the
orient ticket lists the canonical contexts under its own `contexts:`, so they
are composed into that prompt. For ticket-bound work, prefer
`coga launch <slug>`: a ticket loads only the contexts its own `contexts:`
list names, plus its current workflow step.

## Common commands

- `coga status` — triage view of all tasks
- `coga ticket "<title>"` — guided task authoring
- `coga create "<title>"` — raw draft create
- `coga dream` — run the Coga cleanup pass now
- `coga mark active <slug>` — activate a draft without launching it (launch activates inline on its own)
- `coga launch <slug>` — start or resume a task (any unique prefix works)
- `coga show <slug>` — read a task's ticket / blackboard / log
- `coga bump <slug>` — advance one workflow step
- `coga mark done <slug>` — finish active or in-progress work
- `coga mark canceled <slug> --message "<reason>"` — abandon work explicitly
- `coga block --task <slug> --reason "..."` — stop for a concrete answer
- `coga unblock <slug> --answer "..."` — record the answer and resume
- `coga --help` — full CLI surface

## Mental model

Coga's own contexts are package-backed; a repo can override one by adding a
local file at the same ref under `<contexts-dir>/` (by default,
`coga/contexts/`). The orientation set:

- `coga/principles` — the seven non-negotiables
- `coga/architecture` — overview of the primitives, the correction loop, and
  a map of the focused topic refs (tickets, lifecycle, launch, sync, ...)
- `coga/cli` — command index pointing at each command's owning topic

`bootstrap/orient` attaches exactly these three. No context is composed into
every ticket: a launched ticket composes only the refs in its own `contexts:`
list, and a link inside a context never loads the linked page. Attach the
focused topic a task needs rather than a broad overview.

## Don't

- Don't hand-edit `status` / `step` / `workflow` in ticket frontmatter — the
  CLI manages them. Use `coga bump` / `coga block` instead.
- Don't write to the repo-global `coga/log.md` — also CLI-managed.
  Working notes go in the blackboard region of `ticket.md`.
- Don't commit secrets. Use `coga.local.toml` (gitignored) for machine-local
  values, and `env:VAR_NAME` references in `coga.toml` for shared ones.
"""


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _require_init_tools() -> None:
    """Fail loud when a tool `coga init` *requires* is not on PATH.

    Covers the `required_at_init` dependencies in the `coga.dependencies`
    manifest — just `git`. `_do_init` calls it only after the checks that need
    no tool (the `coga/` state, `--user`, an enclosing Coga repo) have passed,
    and before the Git-backed ones that cannot run without it. In an
    interactive terminal a missing required tool is first offered through the
    machine's package manager; nothing installs without a yes, and a
    non-interactive init never prompts. A tool still missing exits 2 with its
    install hint.
    """
    interactive = _interactive()
    manager = _package_manager() if interactive else None
    required = [
        dep
        for dep in DEPENDENCIES
        if dep.required_at_init
        and shutil.which(dep.name) is None
        and not (interactive and _offer_install(dep, manager))
    ]
    if not required:
        return
    lines = [
        "coga needs these external command-line tools, but they are not on "
        "PATH:",
        *(f"  - {dep.name}: install from {dep.install}" for dep in required),
        "Install the missing tool(s), then re-run `coga init`.",
    ]
    typer.secho("\n".join(lines), fg=typer.colors.RED, err=True)
    sys.exit(2)


def _offer_optional_tools() -> None:
    """Offer missing optional CLIs and `gh auth login`; warn on what is left.

    `_do_init` calls it once every precondition has passed, just before the
    first write, so a malformed or redundant invocation never installs or
    authenticates anything. In an interactive terminal each missing optional
    tool with an `offer_install` default (`gh`, `op`) is offered through the
    machine's package manager, printing the exact command first, and `gh` is
    then offered `gh auth login` if its active github.com account is not
    logged in. A tool still missing is only a warning: each is enforced again
    at its point of need. Agent CLIs are not warned about here:
    `_offer_agent_cli` offers them, and the next steps name them.
    """
    interactive = _interactive()
    manager = _package_manager() if interactive else None
    optional = [
        dep
        for dep in DEPENDENCIES
        if not dep.required_at_init
        and dep.offer_install is not None
        and shutil.which(dep.name) is None
        and not (interactive and _offer_install(dep, manager))
    ]
    if interactive and "gh" not in {dep.name for dep in optional}:
        _offer_gh_login()
    if optional:
        typer.secho(
            "\n".join(
                [
                    "Optional tools not on PATH (init continues without them):",
                    *(f"  - {dep.name}: install from {dep.install}" for dep in optional),
                ]
            ),
            fg=typer.colors.YELLOW,
            err=True,
        )


def _package_manager() -> str | None:
    """The first `PACKAGE_MANAGERS` entry this platform supports and has."""
    if sys.platform == "darwin":
        candidates = ["brew"]
    elif sys.platform == "win32":
        candidates = ["winget"]
    else:
        candidates = ["apt-get", "dnf", "pacman", "brew"]
    for name in candidates:
        if shutil.which(name) is not None:
            return name
    return None


def _offer_install(dep: Dependency, manager: str | None) -> bool:
    """Ask to install `dep` with `manager`; True when it is now on PATH."""
    if dep.offer_install is None or manager not in dep.packages:
        return False
    argv = [*PACKAGE_MANAGERS[manager], *dep.packages[manager]]
    if manager in NEEDS_ROOT and hasattr(os, "geteuid") and os.geteuid() != 0:
        if shutil.which("sudo") is None:
            return False
        argv.insert(0, "sudo")
    first_line = dep.purpose.split(" — ")[0].split(". ")[0]
    typer.echo(f"`{dep.name}` is not installed ({first_line}).")
    typer.echo(f"  Will run: {shlex.join(argv)}")
    if not typer.confirm("Install it now?", default=dep.offer_install):
        return False
    result = subprocess.run(argv, check=False)
    if result.returncode != 0:
        typer.secho(
            f"`{shlex.join(argv)}` failed (exit {result.returncode}).",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return False
    if shutil.which(dep.name) is None:
        typer.secho(
            f"Installed `{dep.name}`, but it is not on PATH yet — open a new "
            "shell, then re-run `coga init` if it is required.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        return False
    return True


def _offer_gh_login() -> None:
    """Offer `gh auth login` when `gh` is installed but not logged in."""
    gh = shutil.which("gh")
    if gh is None:
        return
    if _gh_logged_in(gh):
        return
    typer.echo("`gh` is installed but not logged in to GitHub.")
    if typer.confirm("Run `gh auth login` now?", default=True):
        subprocess.run([gh, "auth", "login"], check=False)


def _gh_logged_in(gh: str) -> bool:
    """True when the active github.com account of `gh` is authenticated.

    Plain `gh auth status` tests every known account on every host and exits
    1 if any of them has a problem, so a stale second account would read as
    "logged out". `--active --hostname github.com` checks only the account
    `gh` actually uses there. A `gh` older than 2.40 has no `--active` (and
    holds one account per host), so on an unknown-flag error retry with
    `--hostname` alone.
    """
    argv = [gh, "auth", "status", "--active", "--hostname", "github.com"]
    status = subprocess.run(argv, capture_output=True, text=True, check=False)
    if status.returncode != 0 and "unknown flag" in (status.stderr or ""):
        argv.remove("--active")
        status = subprocess.run(argv, capture_output=True, text=True, check=False)
    return status.returncode == 0


def _offer_agent_cli(default_agent: str | None) -> str | None:
    """Offer to install an agent CLI; the agent to make default, or None.

    Interactive init only, after `_offer_optional_tools`. With no agent CLI on
    PATH the user picks one of `AGENT_CLIS` (or skips) and
    `coga.agent_cli_setup.offer_agent_cli` offers its install and login. When
    exactly one agent CLI is then on PATH and it is not `default_agent` — the
    first-declared agent of the coga.toml init is about to write — init asks
    to make it the default and returns it on a yes. `default_agent` is None
    where init must not edit coga.toml (a clone's machine-local setup), so
    nothing is returned there.
    """
    if not _interactive():
        return None
    installed = [name for name in AGENT_CLIS if shutil.which(name) is not None]
    if len(installed) > 1:
        return None
    if installed:
        chosen = installed[0]
    else:
        typer.echo(
            "No agent CLI is installed — coga launches agents through Claude "
            "Code (`claude`) or Codex (`codex`)."
        )
        choices = [*AGENT_CLIS, "skip"]
        chosen = ""
        while chosen not in choices:
            chosen = typer.prompt(
                f"Install which agent CLI? ({'/'.join(choices)})",
                default=AGENT_CLIS[0],
            ).strip()
        if chosen == "skip" or not offer_agent_cli(chosen):
            return None
    if default_agent is None or chosen == default_agent:
        return None
    if not typer.confirm(
        f"Make `{chosen}` the default agent in coga.toml (instead of "
        f"`{default_agent}`)?",
        default=True,
    ):
        return None
    return chosen


def _template_default_agent(template_root: Traversable) -> str | None:
    """First-declared `[agents.*]` type of the packaged coga.toml, or None."""
    shared = tomllib.loads(template_root.joinpath("coga.toml").read_text())
    agents = shared.get("agents")
    if not isinstance(agents, dict) or not agents:
        return None
    return next(iter(agents))


_AGENT_LABELS = {"claude": "Claude Code", "codex": "Codex"}

_TABLE_HEADER = re.compile(r"^[ \t]*\[\[?[ \t]*([^\]]+?)[ \t]*\]\]?[ \t]*(#.*)?$")


def _make_default_agent(coga_toml: Path, name: str) -> bool:
    """Move `[agents.<name>]` first among the agent tables; True on success.

    `Config.default_agent` is the first-declared agent type, so declaration
    order is the default. The tables swap places as text rather than through a
    TOML round trip, so each keeps its own comments and the comments between
    sections stay put. The rewrite must parse to the same config with `name`
    first, or coga.toml is left untouched and this returns False.
    """
    text = coga_toml.read_text()
    lines = text.splitlines(keepends=True)
    headers = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := _TABLE_HEADER.match(line))
    ]
    spans: list[tuple[int, int, str]] = []
    for position, (start, key) in enumerate(headers):
        parts = key.split(".")
        if len(parts) != 2 or parts[0] != "agents":
            continue
        end = next(
            (
                index
                for index, other in headers[position + 1 :]
                if not other.startswith(f"{key}.")
            ),
            len(lines),
        )
        # Trailing blank and comment lines introduce the next section.
        while end > start + 1 and (
            not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")
        ):
            end -= 1
        spans.append((start, end, parts[1]))
    order = [agent for _, _, agent in spans]
    if name not in order:
        return False
    if order[0] == name:
        return True
    order = [name, *(agent for agent in order if agent != name)]
    blocks = {agent: lines[start:end] for start, end, agent in spans}
    out: list[str] = []
    cursor = 0
    for (start, end, _), agent in zip(spans, order):
        out += lines[cursor:start]
        out += blocks[agent]
        cursor = end
    out += lines[cursor:]
    new_text = "".join(out)
    try:
        before = tomllib.loads(text)
        after = tomllib.loads(new_text)
    except tomllib.TOMLDecodeError:
        return False
    if after != before or list(after.get("agents", {})) != order:
        return False
    coga_toml.write_text(new_text)
    return True


def _stamp_agent_into_delivered_tickets(coga_os: Path, old: str, new: str) -> None:
    """Point delivered tickets that name the old default agent at the new one.

    The onboarding ticket ships `agent: claude`; once init makes another agent
    the default, `coga build` should launch that one.
    """
    pattern = re.compile(rf"^agent:[ \t]*{re.escape(old)}[ \t]*$", re.M)
    tasks = coga_os / "tasks"
    if not tasks.is_dir():
        return
    for ticket in sorted(tasks.glob("**/*.md")):
        text = ticket.read_text()
        new_text, count = pattern.subn(f"agent: {new}", text)
        if count:
            ticket.write_text(new_text)


def _check_git_identity(target: Path) -> None:
    """Fail loud before any writes when git cannot author a commit here.

    On a fresh machine with no `user.email`/`user.name` (every truly new
    machine), the "commit coga/" step at the end of init would fail —
    historically silently, leaving coga/ staged but uncommitted, and the
    user's first `coga create` dying on a raw `fatal: ambiguous argument
    'HEAD'`. Git resolves author and committer identity separately, so probe
    both `git var GIT_AUTHOR_IDENT` and `GIT_COMMITTER_IDENT` up front — after
    the git-repo check, before the slow clone/venv — and fail with the remedy
    if either is unavailable. The probes honor config, their matching GIT_*
    env vars, EMAIL, and git's hostname auto-detection. `target` may not exist
    yet (nested init), so probe from the nearest existing ancestor; repo-local
    `user.email` still counts. A missing or unrunnable git is not this check's
    problem —
    `_require_init_tools` owns that.
    """
    probe = nearest_existing_dir(target)
    if probe is None:
        return
    result: subprocess.CompletedProcess[str] | None = None
    for identity_var in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        try:
            result = subprocess.run(
                ["git", "-C", str(probe), "var", identity_var],
                capture_output=True,
                text=True,
            )
        except OSError:
            return
        if result.returncode != 0:
            break
    if result is None or result.returncode == 0:
        return
    detail = next(
        (line for line in result.stderr.strip().splitlines() if line.strip()),
        "no user.email / user.name configured",
    )
    typer.secho(
        f"git has no identity configured on this machine — coga is git-backed "
        f"and `coga init` commits coga/ into your repo, but git cannot author "
        f"a commit ({detail}).\n"
        f"Tell git who you are, then re-run `coga init`:\n"
        f'    git config --global user.email "you@example.com"\n'
        f'    git config --global user.name "Your Name"',
        fg=typer.colors.RED,
        err=True,
    )
    sys.exit(2)


def init(
    path: Path | None = typer.Argument(
        None,
        help=(
            "Target dir for coga/ (created if missing) — a git repo root or "
            "any subdir inside one (e.g. `coga init tools/ops` in a monorepo). "
            "Defaults to the current dir."
        ),
    ),
    user: str | None = typer.Option(
        None,
        "--user",
        help=(
            "Your name — becomes `user` in coga.local.toml, the name tickets "
            "and agents refer to you by (e.g. marc). On a clone of an "
            "already-initialized repo this is all init writes."
        ),
    ),
) -> None:
    """Create `coga/` from package templates, or set up a clone's machine-local half."""
    _do_init(path or Path("."), user=user)


def _template_contexts_destination(
    template_root: Traversable, coga_os: Path
) -> Path | None:
    """Configured contexts destination embedded in a fresh template tree.

    The normal shipped template leaves `[layout]` unset. Keeping this path
    config-aware prevents a customized or future scaffold that does set it
    from copying local contexts into the default directory while its own
    config points somewhere else.
    """
    shared = tomllib.loads(template_root.joinpath("coga.toml").read_text())
    return resolve_layout_contexts_path(shared.get("layout"), coga_os)


def _relocate_fresh_contexts(
    coga_os: Path, destination: Path | None
) -> tuple[Path | None, tuple[Path, ...]]:
    """Move scaffolded local contexts to `destination`, when configured.

    Returns the moved directory and any parent directories this call created,
    allowing `_do_init` to preserve its all-or-nothing cleanup if a later
    initialization phase raises.
    """
    source = (coga_os / "contexts").resolve(strict=False)
    if destination is None or destination == source:
        return None, ()
    if destination.exists():
        raise FileExistsError(
            f"configured contexts destination already exists: {destination}"
        )
    if not source.is_dir():
        raise FileNotFoundError(
            f"installed templates are missing the contexts directory at {source}"
        )

    created_parents: list[Path] = []
    parent = destination.parent
    while not parent.exists():
        created_parents.append(parent)
        parent = parent.parent
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        source.rename(destination)
        relocated_gitignore = destination / ".gitignore"
        if not relocated_gitignore.exists():
            relocated_gitignore.write_text(_RELOCATED_CONTEXTS_GITIGNORE)
    except BaseException:
        if destination.is_dir():
            shutil.rmtree(destination, ignore_errors=True)
        for created in created_parents:
            try:
                created.rmdir()
            except OSError:
                pass
        raise
    return destination, tuple(created_parents)


# The scaffolded `coga.toml` documents `[git]` in comments only, so the control
# branch comes from the `main` default in `coga.config`. When that default is
# wrong for this checkout, the real table is written just above the aliases
# heading, where the git-sync commentary ends.
_GIT_TABLE_ANCHOR = "# --- Aliases ---"


def _render_git_control_branch_table(branch: str, default: str) -> str:
    """The `[git]` table `coga init` writes when `default` is absent here."""
    return (
        f"# `coga init` found no {default!r} branch in this checkout, so it\n"
        f"# identified {branch!r} as this repository's control branch.\n"
        f"# Change this if the team\n"
        f"# syncs coga state onto a different branch.\n"
        f"[git]\n"
        f'control_branch = "{branch}"\n'
    )


def _scaffolded_git_defaults(coga_os: Path) -> tuple[str, str, bool]:
    """`(control_branch, remote, declared)` for the freshly scaffolded config.

    Deliberately parses only `[git]` rather than going through `load_config`:
    init must not start failing over an unrelated config problem (an
    unresolvable Slack webhook, say) that it never used to read at this point.

    `declared` is True when the scaffold ships a real `[git]` table. The
    packaged template documents that table in comments only, so a scaffold
    that has one made a deliberate choice — and a second table written under
    it would not even parse.
    """
    shared = tomllib.loads((coga_os / "coga.toml").read_text())
    git_table = shared.get("git")
    remote, control_branch, _worktrees_ticket_owned = _parse_git(git_table)
    return control_branch, remote, git_table is not None


def _repository_has_refs(target: Path) -> bool:
    """Whether this checkout has any refs, distinguishing fresh from orphaned."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "for-each-ref",
            "--count=1",
            "--format=%(refname)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise GitError(f"`git for-each-ref` failed: {detail}")
    return bool(result.stdout.strip())


def _git_can_read_repository(target: Path) -> bool:
    """Whether Git recognizes the checkout beyond a synthetic `.git` marker."""
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _cached_remote_default_branch(target: Path, remote: str) -> str | None:
    """The branch named by cached `refs/remotes/<remote>/HEAD`, if present."""
    ref = f"refs/remotes/{remote}/HEAD"
    result = subprocess.run(
        ["git", "-C", str(target), "symbolic-ref", "--quiet", "--short", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise GitError(f"`git symbolic-ref {ref}` failed: {detail}")
    symbolic = result.stdout.strip()
    prefix = f"{remote}/"
    if not symbolic.startswith(prefix) or symbolic == prefix:
        return None
    return symbolic[len(prefix) :]


def _unwritable_control_branch_reason(branch: str) -> str | None:
    """Why `branch` cannot be emitted as a TOML basic string, if any."""
    if '"' in branch or "\\" in branch:
        # Git permits a quote in a ref name; it would not survive the
        # `control_branch = "..."` literal written below.
        return f"branch {branch!r} cannot be written to coga.toml"
    return None


def _detect_control_branch(
    target: Path, *, control_branch: str, remote: str
) -> tuple[str | None, str | None]:
    """What `coga init` should record as the control branch, and why it can't.

    `coga init` must not create the mismatch every later command complains
    about, so the trigger here is the local/cached-ref portion of the predicate
    behind that warning: `git.control_branch_present`. Init deliberately does
    not contact a remote while scaffolding. Returns `(branch, None)` when the
    configured control branch is absent and a safe replacement can be recorded,
    `(None, None)` when the configured value already fits, and `(None, reason)`
    when init cannot make a safe choice.

    Detection is deliberately narrow. A ref-less fresh repo is safe to infer
    from its unborn HEAD. An established repo is pinned only to its confirmed,
    cached remote default; recording its current HEAD could make a disposable
    feature branch the shared control branch.
    """
    try:
        # `symbolic-ref` resolves an unborn HEAD, which `rev-parse` cannot. If
        # it already names the configured branch, the init commit will create
        # that ref; do not write a redundant table or claim the branch is absent.
        branch = symbolic_head(target)
    except (OSError, GitError):
        # The up-front dependency check owns a missing Git executable. Some
        # unit fixtures deliberately supply only an empty `.git/` marker.
        return None, None
    if branch == control_branch:
        return None, None

    try:
        if control_branch_present(
            target, control_branch, remote, probe_remote=False
        ):
            return None, None
    except OSError:
        return None, None
    except GitError as exc:
        if not _git_can_read_repository(target):
            # Preserve init's historical clean skip for synthetic/unreadable
            # `.git/` markers; a real invocation fails an earlier repo/identity
            # gate. Valid repos reach the loud remote-probe diagnostic below.
            return None, None
        return None, (
            f"git could not verify configured control branch "
            f"{control_branch!r} ({exc})"
        )
    if branch is None:
        return None, (
            f"configured control branch {control_branch!r} is absent and this "
            "checkout has a detached HEAD"
        )

    try:
        remote_configured = subprocess.run(
            ["git", "-C", str(target), "remote", "get-url", remote],
            capture_output=True,
            text=True,
            check=False,
        ).returncode == 0
        has_refs = _repository_has_refs(target)
        remote_default = (
            _cached_remote_default_branch(target, remote)
            if remote_configured
            else None
        )
    except (GitError, OSError) as exc:
        return None, f"git could not determine a safe replacement branch ({exc})"

    if not remote_configured and not has_refs:
        reason = _unwritable_control_branch_reason(branch)
        return (None, reason) if reason else (branch, None)

    if remote_default is not None:
        reason = _unwritable_control_branch_reason(remote_default)
        if reason is not None:
            return None, reason
        try:
            if control_branch_present(
                target, remote_default, remote, probe_remote=False
            ):
                return remote_default, None
        except (GitError, OSError) as exc:
            return None, (
                f"git could not verify cached remote default branch "
                f"{remote_default!r} ({exc})"
            )

    if remote_configured:
        detail = (
            f"cached default branch {remote_default!r} is absent"
            if remote_default is not None
            else f"remote {remote!r} has no cached default branch"
        )
    else:
        detail = "there is no configured remote default"
    return None, (
        f"configured control branch {control_branch!r} is absent, but current "
        f"branch {branch!r} belongs to an established repository and {detail} "
        "to confirm the team's control branch"
    )


def _pin_control_branch(coga_os: Path, branch: str, default: str) -> None:
    """Record `[git] control_branch` in the freshly scaffolded `coga.toml`."""
    config_path = coga_os / "coga.toml"
    table = _render_git_control_branch_table(branch, default)
    text = config_path.read_text()
    anchor = f"\n{_GIT_TABLE_ANCHOR}"
    if anchor in text:
        text = text.replace(anchor, f"\n{table}{anchor}", 1)
    else:
        # A customized scaffold without the shipped headings still gets the
        # same table — a trailing one parses identically.
        text = text.rstrip("\n") + "\n\n" + table
    config_path.write_text(text)


def _local_toml_user(local_toml: Path) -> str | None:
    """Return the `user` value `coga.local.toml` currently sets, or None.

    None covers both "file absent" and "file present but `user` missing or
    empty" — the same test `load_config` applies before refusing to act as
    anyone. An unparseable file is a hard error: init will not guess whether a
    broken machine-local file still names someone.
    """
    if not local_toml.is_file():
        return None
    try:
        data = tomllib.loads(local_toml.read_text())
    except (tomllib.TOMLDecodeError, OSError) as exc:
        typer.secho(
            f"{local_toml} could not be read as TOML ({exc}). Fix or remove "
            "it, then re-run `coga init --user NAME`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    user = data.get("user")
    return user if isinstance(user, str) and user else None


def _write_local_user(local_toml: Path, name: str) -> str:
    """Set `user = "<name>"` in `coga.local.toml`, creating the file if absent.

    A missing file gets the full template via `render_local_toml`. An existing
    file is edited as TOML so `user` stays at the root and other machine-local
    overrides and comments survive, including nested keys also named `user`.
    Validate the rendered document with the config reader before writing it.
    Returns "wrote" or "updated" for the caller's report.
    """
    if not local_toml.is_file():
        text = render_local_toml(name)
        verb = "wrote"
    else:
        document = tomlkit.parse(local_toml.read_text())
        document["user"] = name
        text = tomlkit.dumps(document)
        verb = "updated"
    tomllib.loads(text)
    local_toml.write_text(text)
    return verb


def _require_git_work_tree(target: Path) -> None:
    """Both fresh init and clone setup require an enclosing Git work tree."""
    if not is_git_repo(target):
        typer.secho(
            f"{target} is not inside a git repository — coga is git-backed.\n"
            f"Run `git init` in {target} (or an ancestor) first, then re-run "
            f"`coga init`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)


def _setup_initialized_clone(target: Path, coga_os: Path, user: str | None) -> None:
    """`coga init --user NAME` on an already-initialized repo.

    A clone of a Coga repo carries the committed `coga/` but none of what the
    coga-managed `.gitignore` blocks: `coga.local.toml`, the agent skill
    symlinks, and the generated `coga/.agent-skills/` view. This is the
    supported way to create that machine-local half. It writes only gitignored
    state — nothing is staged or committed — and is idempotent: a second run
    finds the same user and takes the ordinary refusal below. The refusals
    that need no tool come first; optional installs are offered only once
    every check has passed.
    """
    local_toml = coga_os / "coga.local.toml"
    if _local_toml_user(local_toml) is not None:
        # The machine-local half is already there, so re-running init was
        # reaching for something else: upgrading the CLI, repairing a broken
        # coga/, or removing Coga. Refuse with that menu.
        typer.secho(
            f"{coga_os} already exists — this repo is already initialized.\n"
            "To upgrade the CLI, use the installer that owns it: "
            "`uv tool upgrade coga` for uv, or run "
            "`pip install --upgrade coga` in its Python environment. "
            "Batteries resolve from the installed package, so no re-init "
            "is needed.\n"
            f"If {coga_os} is broken or partial, fix the cause or remove "
            "the dir, then re-run `coga init`.\n"
            f"To remove Coga from this repo entirely, run `coga uninstall` "
            f"from inside {target}.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    if user is None:
        typer.secho(
            f"{coga_os} is already initialized, but {local_toml} does not set "
            "your name (a clone never carries this gitignored, machine-local "
            "file). Run `coga init --user NAME` (e.g. `coga init --user marc`) "
            "to create it and wire the agent skill links; coga does not guess "
            "the name.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    name = _require_user_name(user)
    _require_init_tools()
    _require_git_work_tree(target)
    _offer_optional_tools()
    # A clone's coga.toml is committed team config; this path writes only
    # gitignored state, so it offers the install but never a new default.
    _offer_agent_cli(None)

    # A saved user is the completed-setup guard on the next invocation. Keep
    # the local config unchanged until every agent link is ready, so failures
    # and interruptions can be retried without hitting the re-init refusal.
    try:
        wired_agents, blocked_agents = _link_skills_for_agents(target, coga_os)
    except OSError as exc:
        typer.secho(
            f"Could not prepare agent skills for {coga_os}: {exc}. "
            "Your name has not been saved. Fix the path or its permissions, "
            "then re-run `coga init --user NAME`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    if blocked_agents:
        for label, path in blocked_agents:
            typer.secho(
                f"Could not wire {label} skills at {path}. Fix this path or "
                "its permissions, then re-run `coga init --user NAME`. "
                "Your name has not been saved.",
                fg=typer.colors.RED,
                err=True,
            )
        sys.exit(2)

    try:
        verb = _write_local_user(local_toml, name)
    except (OSError, tomllib.TOMLDecodeError, tomlkit.exceptions.ParseError) as exc:
        typer.secho(
            f"Could not update {local_toml}: {exc}. Fix the cause, then "
            "re-run `coga init --user NAME`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    typer.echo("")
    typer.echo(f"Set up machine-local Coga state for {coga_os} (already initialized).")
    typer.echo(
        f'{verb.capitalize()} {local_toml} (machine-local config — gitignored) '
        f'with user = "{name}".'
    )
    if wired_agents:
        names = ", ".join(wired_agents)
        typer.echo(f"Wired skill discovery for {names} (symlinked into their skill dirs).")
    typer.echo("Nothing was committed: this path writes only gitignored state.")


def _do_init(path: Path, *, user: str | None = None) -> None:
    target = path.resolve()
    coga_os = target / "coga"

    if coga_os.exists():
        if (coga_os / "coga.toml").is_file():
            # Initialized repo. Either a clone missing its machine-local half
            # (set it up) or a genuine re-init (refuse with the upgrade menu).
            _setup_initialized_clone(target, coga_os, user)
            return
        else:
            message = (
                f"{coga_os} already exists, but it does not look like an "
                "initialized Coga repo (coga.toml is missing).\n"
                "If this is a broken or partial Coga install, fix the cause or "
                "remove the dir, then re-run `coga init`. Otherwise, move or "
                "rename the existing path so Coga does not overwrite it."
            )
        typer.secho(
            message,
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # A coga/ nested inside an existing coga OS tree can't work — discovery
    # walks up and the enclosing repo claims the subtree. Fail loud before
    # anything is written.
    enclosing = _enclosing_coga_root(target)
    if enclosing is not None:
        typer.secho(
            f"{target} is inside an existing coga repo ({enclosing / 'coga.toml'}) "
            f"— a coga/ nested inside another coga/ can't work: discovery walks "
            f"up and resolves the enclosing repo.\n"
            f"Run `coga init` outside {enclosing}, or use that repo directly.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Require the operator's name up front (before the slow clone/venv) so
    # `current_user` is valid from the first moment after init, and a bad
    # invocation leaves nothing on disk.
    name = _require_user_name(user)

    # Every check below runs git, so a missing git is reported (or, in a
    # terminal, offered for install) only now, once the checks that need no
    # tool have passed.
    _require_init_tools()

    # Coga is git-backed: `coga init` commits coga/ into the host repo.
    # If the target isn't inside a git work tree, fail loud (principle 6)
    # instead of writing coga/ and silently skipping the commit further down.
    # The target itself doesn't have to be the git root — `coga init tools/ops`
    # inside a monorepo scaffolds a nested coga/ committed into the host repo.
    # We don't run `git init` ourselves — the user does, which keeps branch
    # naming in their hands. Checked here, before any writes, so a bad
    # invocation leaves nothing behind and we fail before the slow clone/venv.
    _require_git_work_tree(target)

    # The host repo must actually be able to track coga/. If its ignore rules
    # exclude the target, `git add` refuses the path and the commit is silently
    # skipped — same silent-skip the git check above guards against. Fail loud
    # up front (still before any writes) so nothing is left behind.
    if _host_ignores_coga(target):
        typer.secho(
            f"{target / 'coga'} is gitignored by the host repo — coga is "
            f"git-backed and `coga init` must commit coga/ into your repo, but "
            f"git refuses to track an ignored path.\n"
            f"Remove the ignore rule covering {target}, or pick a target the "
            f"repo tracks, then re-run `coga init`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Same fail-before-writes posture for git identity: with no user.email /
    # user.name, the "commit coga/" step at the end would fail and leave
    # coga/ staged but uncommitted. Probe it here so the remedy comes before
    # the slow clone/venv, not after.
    _check_git_identity(target)

    # Decide empty-vs-filled against the pristine dir, before init writes
    # anything of its own — a filled repo skips onboarding-ticket seeding.
    # A target without its own `.git` is a nested init below an established
    # host repo's root: always treat it as filled, even when the subdir itself
    # is empty — the onboarding interview is for genuinely new repos.
    nested = not (target / ".git").exists()
    is_empty = _repo_is_empty(target) and not nested

    template_root = packaged_template_root()
    try:
        contexts_destination = _template_contexts_destination(
            template_root, coga_os
        )
    except (ConfigError, OSError, tomllib.TOMLDecodeError) as exc:
        typer.secho(
            f"Cannot scaffold Coga from the installed templates: {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    default_contexts = (coga_os / "contexts").resolve(strict=False)
    if (
        contexts_destination is not None
        and contexts_destination != default_contexts
        and contexts_destination.exists()
    ):
        typer.secho(
            f"Cannot scaffold configured contexts at {contexts_destination}: "
            "that path already exists, and `coga init` will not merge into or "
            "overwrite a pre-existing directory.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    if (
        contexts_destination is not None
        and contexts_destination != default_contexts
        and _host_ignores_path(contexts_destination)
    ):
        typer.secho(
            f"Cannot scaffold configured contexts at {contexts_destination}: "
            "the host repository ignores that path, so Git could not preserve "
            "the directory in a fresh clone.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Every precondition has passed: only now offer optional installs,
    # `gh auth login`, and an agent CLI, so a doomed invocation never changes
    # the machine. The chosen default agent is written once coga.toml exists.
    _offer_optional_tools()
    template_default_agent = _template_default_agent(template_root)
    default_agent = _offer_agent_cli(template_default_agent)

    target.mkdir(parents=True, exist_ok=True)

    # Init is atomic. The check above guarantees coga/ did not exist before
    # this run, so if any step below fails — template copy, venv build, a
    # Ctrl-C, even a sys.exit — we remove the half-built coga/ and re-raise.
    # A partial init must never survive: it is the dead end where a re-run of
    # `coga init` refuses ("already exists") yet the leftover coga/ has a broken
    # venv / missing user (the re-init wedge).
    relocated_contexts: Path | None = None
    created_context_parent_dirs: tuple[Path, ...] = ()
    try:
        copy_fresh_templates(template_root, coga_os)
        # `.gitignore` shipped verbatim by copytree; wrap it in the
        # coga-managed marker block so the fenced region stays distinct
        # from user additions.
        _refresh_coga_gitignore(template_root, coga_os)
        relocated_contexts, created_context_parent_dirs = (
            _relocate_fresh_contexts(coga_os, contexts_destination)
        )

        # On a filled repo, drop the onboarding ticket(s) the template ships — a
        # real project doesn't want the bootstrap interview seeded for it.
        pruned_onboarding = (
            _prune_onboarding_tickets(coga_os) if not is_empty else []
        )
        # Stamp the captured name over the `new-user` placeholder in whatever
        # tickets remain, so the placeholder never ships as a live owner.
        _stamp_user_into_delivered_tickets(coga_os, name)

        local_toml = coga_os / "coga.local.toml"
        local_toml.write_text(render_local_toml(name))

        # Init must not scaffold the very control-branch mismatch every later
        # command nags about. Infer only when Git makes the repository's intent
        # unambiguous; otherwise keep the configured default and say how to fix
        # it rather than pinning a transient feature branch.
        default_control_branch, default_remote, git_declared = (
            _scaffolded_git_defaults(coga_os)
        )
        pinned_branch, unpinnable_control_branch = _detect_control_branch(
            target, control_branch=default_control_branch, remote=default_remote
        )
        if pinned_branch is not None and git_declared:
            # The scaffold already made its own `[git]` choice. Report the
            # mismatch rather than editing a config that states one.
            unpinnable_control_branch = (
                f"configured control branch {default_control_branch!r} is absent, "
                "and this scaffold's coga.toml already declares its own [git] table"
            )
            pinned_branch = None
        if pinned_branch is not None:
            _pin_control_branch(coga_os, pinned_branch, default_control_branch)

        default_agent_set = default_agent is not None and _make_default_agent(
            coga_os / "coga.toml", default_agent
        )
        if default_agent_set and template_default_agent is not None:
            _stamp_agent_into_delivered_tickets(
                coga_os, template_default_agent, default_agent
            )

        if is_empty:
            # The template cannot know when this repo is initialized. Record
            # the seeded onboarding task through the ordinary audit writer so
            # its creation time is real rather than baked into every install.
            append_log(
                _load_scaffolded_config(coga_os),
                ONBOARDING_TASK,
                "coga:init",
                "created (mode=interactive, status=active)",
            )

        wired_agents, blocked_agents = _link_skills_for_agents(target, coga_os)
        host_gitignore_changed = ensure_host_gitignore(target)
        written_guides = _write_agent_guides(target)
        generated_host_paths = list(written_guides)
        if relocated_contexts is not None:
            try:
                relocated_contexts.relative_to(coga_os)
            except ValueError:
                generated_host_paths.append(
                    os.path.relpath(relocated_contexts, target)
                )
        commit_sha, commit_failure = _git_commit_coga_os(
            target, coga_os, host_gitignore_changed, generated_host_paths
        )
    except BaseException:
        # Roll back the partial coga/ this run created (only this run — a
        # pre-existing one is refused far above and never reaches here), then
        # re-raise so the original error / exit code / Ctrl-C is preserved.
        if relocated_contexts is not None and relocated_contexts.is_dir():
            shutil.rmtree(relocated_contexts, ignore_errors=True)
        for parent in created_context_parent_dirs:
            try:
                parent.rmdir()
            except OSError:
                pass
        if coga_os.exists():
            shutil.rmtree(coga_os, ignore_errors=True)
            typer.secho(
                f"init failed — removed the partial state rooted at {coga_os}; "
                f"fix the cause and re-run `coga init`.",
                fg=typer.colors.YELLOW,
                err=True,
            )
        raise

    typer.echo("")
    typer.echo(f"Initialized coga repo at {coga_os}")
    typer.echo(
        f'Wrote {local_toml} (machine-local config — gitignored) with user = "{name}".'
    )
    if pruned_onboarding:
        typer.echo(
            "Skipped the onboarding ticket (this dir already has a project), "
            "so `coga build` is unavailable here — create tasks with "
            "`coga ticket` when you're ready."
        )
    if wired_agents:
        names = ", ".join(wired_agents)
        typer.echo(f"Wired skill discovery for {names} (symlinked into their skill dirs).")
    for label, path in blocked_agents:
        typer.secho(
            f"Skipped {label} skill wiring — {path} exists but isn't a directory. "
            f"Remove or convert it so skill wiring can complete.",
            fg=typer.colors.YELLOW,
        )
    if pinned_branch is not None:
        typer.echo(
            f'Set [git] control_branch = "{pinned_branch}" in '
            f"{coga_os / 'coga.toml'} — this repo has no "
            f"{default_control_branch!r} branch."
        )
    elif unpinnable_control_branch is not None:
        typer.secho(
            f"[git] coga init could not safely select a control branch: "
            f"{unpinnable_control_branch}. It left the "
            f"{default_control_branch!r} default in {coga_os / 'coga.toml'}; "
            f"verify that branch or set the right one explicitly:\n"
            f"    [git]\n"
            f'    control_branch = "<your-branch>"',
            fg=typer.colors.YELLOW,
        )
    if default_agent_set:
        typer.echo(
            f"Made `{default_agent}` the default agent (declared first under "
            f"[agents] in {coga_os / 'coga.toml'})."
        )
    elif default_agent is not None:
        typer.secho(
            f"Could not make `{default_agent}` the default agent: "
            f"{coga_os / 'coga.toml'} did not reorder cleanly. Move its "
            f"[agents.{default_agent}] table above the other agent tables.",
            fg=typer.colors.YELLOW,
        )
    if host_gitignore_changed:
        typer.echo(f"Updated {target / '.gitignore'} (coga-managed block).")
    if written_guides:
        typer.echo(
            f"Wrote {', '.join(written_guides)} (agent orientation — Claude Code / Codex)."
        )
    external_contexts = False
    if relocated_contexts is not None:
        try:
            relocated_contexts.relative_to(coga_os)
        except ValueError:
            external_contexts = True
    state_label = "Coga state" if external_contexts else "coga/"
    if commit_sha is not None:
        typer.echo(f"Committed {state_label} as {commit_sha[:12]} (push when ready).")
    elif commit_failure is not None:
        # Backstop for commit failures the up-front identity check can't see
        # (failing hooks, odd repo state): coga/ is on disk, so don't roll
        # back — but never let the failure pass silently. Re-stage every path
        # init generated before retrying because the failed phase may have
        # been `git add` itself.
        add_command = shlex.join(
            ["git", "-C", str(target), "add", "--", *commit_failure.paths]
        )
        commit_command = shlex.join(
            [
                "git",
                "-C",
                str(target),
                "commit",
                "-m",
                "Create coga via `coga init`",
                "--",
                *commit_failure.paths,
            ]
        )
        typer.secho(
            f"Warning: {state_label} was written but NOT committed — "
            f"{commit_failure.phase} failed with:\n"
            f"{textwrap.indent(commit_failure.error, '  ')}\n"
            f"Fix the cause, then stage and commit every generated path:\n"
            f"  {add_command}\n"
            f"  {commit_command}",
            fg=typer.colors.YELLOW,
            err=True,
        )

    # Whether the user already has a working `coga` they can run as-is.
    # `shutil.which` honors the executable bit, so a stale non-executable
    # file at `~/.local/bin/coga` won't fool us.
    existing = shutil.which("coga")
    if existing:
        typer.echo(f"`coga` is already on your PATH at {existing}.")

    steps: list[str] = []
    if not existing:
        steps.append(
            "Put `coga` on your PATH — init scaffolds this repo but installs no "
            "software, so the CLI you run is your own:\n"
            "       uv tool install coga"
        )
    steps.append(
        f"Edit {coga_os}/coga.toml — set your agents, notification channels, "
        "and aliases."
    )
    # `coga build` / `coga launch` drive an agent CLI that init deliberately
    # does not require (see `coga.dependencies`) — name the prerequisite here
    # so a fresh user isn't sent into the flow only to hit "not found in PATH".
    steps.append(
        "Install an agent CLI, if you haven't — coga drives Claude Code "
        f"({install_hint('claude')}) or Codex ({install_hint('codex')}). "
        "Launching agents (`coga build`, `coga launch`, `coga ticket`) needs "
        "one installed and authenticated."
    )
    if is_empty:
        build_agent = default_agent or AGENT_CLIS[0]
        other = next(name for name in AGENT_CLIS if name != build_agent)
        steps.append(
            f"Run `coga build` with {_AGENT_LABELS[build_agent]}, or "
            f"`coga build --agent {other}` with {_AGENT_LABELS[other]} "
            "— it launches the coga-build onboarding: one question "
            "about what you want to build, then an agent-led chat that ends in "
            "a short vision you sign off on and a flat batch of starter tickets "
            "you can immediately `coga launch`."
        )
    else:
        steps.append(
            'Run `coga ticket "<title>"` to author your first task — the '
            "guided author turns a one-line title into a ready ticket."
        )
    steps.append("Run `coga --help` to see what's available.")

    typer.echo("")
    typer.echo("Next steps:")
    for i, step in enumerate(steps, 1):
        typer.echo(f"  {i}. {step}")

    _print_notification_state()


def _load_scaffolded_config(coga_os: Path) -> Config:
    """Load the config `coga init` just wrote, for init's own audit write.

    The shipped coga.toml selects no notification channel, so a bare
    `SLACK_WEBHOOK_URL` in the operator's environment plays no part in this
    read — but `load_config` refuses one as a migration guard aimed at the
    user's declared config. Hide the variable for this single call so the
    empty-repo path agrees with the filled path, which never loads config:
    both finish and let `_print_notification_state` say what to declare. The
    guard is untouched for every later command, and the variable is restored
    before init spawns anything.
    """
    saved = os.environ.pop("SLACK_WEBHOOK_URL", None)
    try:
        return load_config(coga_os)
    finally:
        if saved is not None:
            os.environ["SLACK_WEBHOOK_URL"] = saved


def _print_notification_state() -> None:
    """End-of-init line on notifications — optional on first run, Slack opt-in."""
    typer.echo("")
    if os.environ.get("SLACK_WEBHOOK_URL"):
        typer.secho(
            "✓ Notifications: optional on first run — Coga runs without them. "
            "$SLACK_WEBHOOK_URL is already set, so opting in is one step: add "
            'channels = ["slack"] under [notification] and '
            '[notification.slack].webhook = "env:SLACK_WEBHOOK_URL" in coga.toml.',
            fg=typer.colors.GREEN,
        )
        return
    typer.secho(
        "✓ Notifications: optional on first run — bump/slack/block/launch run\n"
        "  without them. To turn on team notifications later, select the Slack\n"
        "  channel and point it at a webhook in coga.toml:\n"
        "      [notification]\n"
        '      channels = ["slack"]\n'
        "      [notification.slack]\n"
        '      webhook = "env:SLACK_WEBHOOK_URL"\n'
        "  then export SLACK_WEBHOOK_URL. Once Slack is selected it is fail-loud.",
        fg=typer.colors.GREEN,
    )


# Agents we wire skill discovery for. Each entry is the project-level dir
# that the agent's CLI scans for skills (e.g. Claude Code reads `.claude/skills/`,
# Codex reads `.codex/skills/`). We symlink `<agent>/skills/coga` ->
# `coga/.agent-skills`, a generated merged view of local skills plus
# bundled bootstrap batteries. Other agents (OpenCode etc.) need manual wiring.
_AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    ("Claude Code", ".claude"),
    ("Codex", ".codex"),
)


def _link_skills_for_agents(
    target: Path, coga_os: Path
) -> tuple[list[str], list[tuple[str, Path]]]:
    """Symlink the generated Coga skill view into known agent skill paths.

    Creates `<target>/<agent-dir>/skills/coga` ->
    `<target>/coga/.agent-skills` for Claude Code and Codex. Idempotent:
    refreshes the generated view and leaves a correct link alone,
    if the agent dir is something we shouldn't touch (e.g. a non-directory
    marker file), or if the OS doesn't support symlinks.

    Returns `(wired, blocked)` where `wired` is the list of human-readable
    agent names that ended up with a working link, and `blocked` is a list
    of `(name, path)` pairs we skipped because something non-directory was
    sitting in the way.
    """
    skills_src = refresh_agent_skill_view(coga_os).view_dir

    wired: list[str] = []
    blocked: list[tuple[str, Path]] = []
    for label, dirname in _AGENT_SKILL_DIRS:
        agent_dir = target / dirname
        # Some agents leave a marker file (e.g. an empty `.codex` sentinel).
        # Don't clobber it — surface it to the caller so the human decides.
        if agent_dir.exists() and not agent_dir.is_dir():
            blocked.append((label, agent_dir))
            continue

        skills_dir = agent_dir / "skills"
        link = skills_dir / "coga"
        try:
            rel_target = Path(os.path.relpath(skills_src, skills_dir))
            if link.is_symlink():
                try:
                    if Path(os.readlink(link)) == rel_target:
                        wired.append(label)
                        continue
                except OSError:
                    blocked.append((label, link))
                    continue
                link.unlink()
            elif link.exists():
                blocked.append((label, link))
                continue

            skills_dir.mkdir(parents=True, exist_ok=True)
            link.symlink_to(rel_target, target_is_directory=True)
        except OSError:
            if (label, link) not in blocked:
                blocked.append((label, link))
            continue
        wired.append(label)
    return wired, blocked


_AGENT_GUIDE_FILES: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")


def _write_agent_guides(target: Path) -> list[str]:
    """Drop CLAUDE.md and AGENTS.md at the host repo root if either is missing.

    Both files get the same content. We never overwrite an existing one — a
    user's hand-edited orientation always wins. Returns the basenames we wrote
    so the caller can echo and stage them.
    """
    written: list[str] = []
    for name in _AGENT_GUIDE_FILES:
        path = target / name
        if path.exists():
            continue
        try:
            path.write_text(AGENT_GUIDE_TEMPLATE)
        except OSError:
            continue
        written.append(name)
    return written


@dataclass(frozen=True)
class GitCommitFailure:
    """A failed phase of init's generated-path commit, with retry context."""

    phase: str
    error: str
    paths: tuple[str, ...]


def _git_commit_coga_os(
    target: Path,
    coga_os: Path,
    include_host_gitignore: bool,
    extra_host_paths: list[str] | None = None,
) -> tuple[str | None, GitCommitFailure | None]:
    """Commit coga/ plus generated host paths when `target` is a git repo.

    Returns `(sha, None)` on success, `(None, None)` on a clean skip (not a
    git repo, or nothing to stage), and `(None, failure)` when a git invocation
    failed. The failure names the phase, carries git's stderr, and preserves
    the exact generated path set so the caller can print a complete recovery
    command instead of the historical silent skip (principle 6). Never raises.
    `target` may sit below the git root (nested init) — `git -C <target>`
    resolves pathspecs relative to `target`, and the commit lands in the host
    repo. The commit is scoped to the staged coga paths, so any unrelated
    changes the user already had staged in the host repo are left staged, not
    swept in.
    """
    if not is_git_repo(target):
        return None, None
    paths = ["coga"]
    if include_host_gitignore and (target / ".gitignore").is_file():
        paths.append(".gitignore")
    for extra in extra_host_paths or []:
        if (target / extra).exists():
            paths.append(extra)
    phase = "git repository check"
    try:
        # `is_git_repo` is a filesystem heuristic (a bare `.git` entry counts);
        # confirm git itself agrees before treating later failures as loud
        # errors. Disagreement is the same "not a git repo" clean skip as
        # above — the real not-a-repo case already failed loud in `_do_init`,
        # and test fixtures fake a repo with an empty `.git` dir.
        probe = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--git-dir"],
            capture_output=True,
        )
        if probe.returncode != 0:
            return None, None
        phase = "git add"
        subprocess.run(
            ["git", "-C", str(target), "add", "--", *paths],
            check=True,
            capture_output=True,
            text=True,
        )
        # Anything actually staged *among our paths*? Scope the check (and the
        # commit below) to `paths`: a nested init runs inside a live host repo
        # where the user may already have unrelated files staged, and an
        # unscoped commit would sweep them into the "Create coga" commit.
        phase = "git staged-change check"
        diff = subprocess.run(
            ["git", "-C", str(target), "diff", "--cached", "--quiet", "--", *paths],
            capture_output=True,
            text=True,
        )
        if diff.returncode == 0:
            return None, None
        if diff.returncode != 1:
            error = diff.stderr.strip() or f"git diff exited {diff.returncode}"
            return None, GitCommitFailure(phase, error, tuple(paths))
        phase = "git commit"
        subprocess.run(
            [
                "git", "-C", str(target),
                "commit", "-m", "Create coga via `coga init`", "--", *paths,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        phase = "git commit verification"
        rev = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return rev.stdout.strip() or None, None
    except FileNotFoundError as exc:
        return None, GitCommitFailure(phase, str(exc), tuple(paths))
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        error = stderr or f"{shlex.join(str(arg) for arg in exc.cmd)} exited {exc.returncode}"
        return None, GitCommitFailure(phase, error, tuple(paths))


def _on_path(directory: Path) -> bool:
    resolved = directory.resolve() if directory.exists() else directory
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False
