"""`coga init` — create a new coga repo, or finish setting up a clone of one.

`coga init` writes everything from scratch into `<path>/coga/`. Templates come
from the installed coga package. Init installs no Python packages, skills, or
agent CLIs; in an interactive terminal it offers (never forces) to install
missing supporting CLIs such as `gh`, only after every precondition has
passed. On a repo whose `coga/` already exists it
refuses — unless the gitignored machine-local half
(`coga.local.toml` with a `user`, the agent skill symlinks) is missing, which
is what a fresh clone looks like: then `coga init --user NAME` creates only
that half and commits nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.resources.abc import Traversable
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import tomlkit
import typer

from coga.agent_skills import refresh_agent_skill_view
from coga.paths import LocalOverrideError
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
    load_config,
    resolve_layout_contexts_path,
)
from coga.dependencies import (
    AGENT_CLIS,
    DEPENDENCIES,
    NEEDS_ROOT,
    PACKAGE_MANAGERS,
    Dependency,
    agent_label,
)
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
        text = ticket.read_text(encoding="utf-8")
        new_text, count = _NEW_USER_LINE.subn(
            lambda match: f"{match.group(1)}: {encoded_name}", text
        )
        if count:
            ticket.write_text(new_text, encoding="utf-8", newline="\n")
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

- `coga/architecture` — overview of the primitives, the correction loop, and
  a map of the focused topic refs (tickets, lifecycle, launch, sync, ...)
- `coga/cli` — command index pointing at each command's owning topic

`bootstrap/orient` attaches these contexts. No context is composed into
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


def _offer_optional_tools() -> None:
    """Offer missing optional CLIs and `gh auth login`; warn on what is left.

    `_do_init` calls it once every precondition has passed, just before the
    first write, so a malformed or redundant invocation never installs or
    authenticates anything. In an interactive terminal each missing optional
    tool with an `offer_install` default (`gh`) is offered through the
    machine's package manager, printing the exact command first, and `gh` is
    then offered `gh auth login` if its active github.com account is not
    logged in. A tool still missing is only a warning: each is enforced again
    at its point of need. `op` is deliberately not in that set — it carries
    `offer_install=None`, so it is never offered and never listed as a tool
    init handles; `_note_missing_op` notes it on its own instead. Agent CLIs
    are not warned about here either: init installs none, and the next steps
    name the prerequisite when neither one resolves.
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
    _note_missing_op()


def _note_missing_op() -> None:
    """Note a missing `op` without offering it, in interactive mode or not.

    Which secrets manager a user runs is their choice, so init never installs
    1Password — `op`'s `offer_install=None` keeps it out of both the install
    offer and the `_offer_optional_tools` warning list, which would otherwise
    read as a tool init handles. That leaves nothing saying `op` exists, so
    this prints one note naming what actually needs it, sourced from the
    manifest `purpose` rather than restating it. A user with another manager
    reads it and skips it knowing nothing is broken.
    """
    op = next((dep for dep in DEPENDENCIES if dep.name == "op"), None)
    if op is None or shutil.which(op.name) is not None:
        return
    label, _, condition = op.purpose.partition(" — ")
    typer.secho(
        "\n".join(
            [
                f"`op` ({label}) is not on PATH, and init does not install it:",
                f"  {condition.split('. ')[0]}.",
                f"  Install it from {op.install} only if you need it.",
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


def _installed_agent_clis() -> list[str]:
    """The `AGENT_CLIS` that resolve to a runnable binary, in supported order.

    A machine scan rather than a config read, and deliberately so: init is the
    command that creates the `coga.toml` a point-of-need lookup reads, and
    `print_agent_scan` prints before anything is written, so there is no
    config to consult yet. "What can this machine run" and "what does this
    repo use" are different questions; this answers the first. Nothing here
    states a requirement — which binary a launch needs comes from that agent's
    `cli` in `coga.toml`.
    """
    return [agent.name for agent in AGENT_CLIS if shutil.which(agent.name) is not None]


def print_agent_scan() -> list[str]:
    """Print every supported agent CLI and whether its binary is on PATH.

    Returns the agents it found, so init configures `coga.toml` from the very
    rows the user just read instead of walking PATH a second time that could
    disagree with the first. Still argument-free, so a later `coga check` calls
    it the same way and ignores the return; it holds no interactivity check of
    its own either, so such a command can print unconditionally while init
    prints only on a tty. Rows come from `AGENT_CLIS`, so an agent added there
    renders with no edit here, and `AgentCLI.display` reads a label-less entry
    under its slug rather than raising. The binary rides in parens inside the
    label, so no row needs column alignment.

    The leading blank line is load-bearing: on a fresh VM the heading ran
    straight on from the `op` note above it and read as another line of that
    block. Found is green; not found is left uncoloured rather than given a
    warning colour, because having exactly one agent is the normal case. An
    empty registry prints nothing at all rather than a heading with nothing
    under it. Asks nothing and writes nothing.
    """
    if not AGENT_CLIS:
        return []
    installed = _installed_agent_clis()
    typer.echo("")
    typer.echo("Checking for agent CLIs...")
    typer.echo("")
    typer.echo("Agent CLIs coga can drive")
    for position, agent in enumerate(AGENT_CLIS, start=1):
        last = position == len(AGENT_CLIS)
        found = agent.name in installed
        typer.secho(
            f"{'└──' if last else '├──'} {'●' if found else '○'} "
            f"{agent.display} ({agent.name}) — "
            f"{'found' if found else 'not found'}",
            fg=typer.colors.GREEN if found else None,
        )
    return installed


def _template_default_agent(template_root: Traversable) -> str | None:
    """The default agent type of the packaged coga.toml, or None.

    Mirrors `Config.default_agent`: a top-level `default_agent` naming a
    declared type wins, else the first-declared `[agents.*]` table.
    """
    shared = tomllib.loads(template_root.joinpath("coga.toml").read_text(encoding="utf-8"))
    agents = shared.get("agents")
    if not isinstance(agents, dict) or not agents:
        return None
    named = shared.get("default_agent")
    if isinstance(named, str) and named.strip() in agents:
        return named.strip()
    return next(iter(agents))


_TABLE_START = re.compile(r"^[ \t]*\[")


def _agent_table_start(name: str) -> re.Pattern[str]:
    """The live `[agents.<name>]` header line, commented headers excluded."""
    return re.compile(rf"^[ \t]*\[agents\.{re.escape(name)}\][ \t]*$")


_COMMENTED_AGENT_TABLE = re.compile(
    r"^[ \t]*#[ \t]*\[agents\.([^\]\s]+)\][ \t]*$", re.M
)


def _agent_table_state(coga_toml: Path) -> tuple[list[str], list[str]]:
    """What coga.toml declares, and which registry tables sit commented out.

    Read back off disk instead of inferred from the scan, so init reports the
    file the user actually has: a configuration that bailed leaves the packaged
    template, where every table is live and none is commented out, and both
    lists say so. Declared names keep the file's own order, which is the
    order `Config.default_agent` resolves the default from. The commented list
    is filtered through `AGENT_CLIS`, so a hand-commented table for some other
    agent type is not reported as init's work. Returns two empty lists for an
    unreadable or unparseable file, which the caller treats as nothing to say.
    """
    try:
        text = coga_toml.read_text(encoding="utf-8")
        parsed = tomllib.loads(text)
    except (OSError, tomllib.TOMLDecodeError):
        return [], []
    agents = parsed.get("agents")
    declared = list(agents) if isinstance(agents, dict) else []
    commented = set(_COMMENTED_AGENT_TABLE.findall(text))
    return declared, [a.name for a in AGENT_CLIS if a.name in commented]


def _configure_agent_tables(
    coga_toml: Path, found: Sequence[str]
) -> list[str] | None:
    """Comment out the not-found agents' tables; the names still declared.

    The scan's PATH read is the input and this file is the output, so what the
    machine has decides what the repo declares. Every registry agent absent
    from `found` gets its `[agents.<name>]` table commented out rather than
    deleted, which makes enabling it later an uncomment rather than an edit
    the user has to compose. An empty `found` is the exception: with no agent
    to choose, the packaged file stands untouched and keeps declaring every
    supported agent, so installing any one CLI is the whole remedy and no
    first step is a `coga.toml` edit. Returns the names the file now declares, in
    declaration order, which is the first-is-default order
    `Config.default_agent` reads; returns None, leaving coga.toml untouched, on
    any failure.

    Callers must read the returned list rather than `found`: a registry agent
    the packaged template never declared has no table to comment out and is
    skipped, so it is found yet undeclared, and treating it as the default
    would stamp an `agent:` that `coga validate` reports as unknown.

    Two traps shape the rewrite. Commenting "every line to the next table
    header" would swallow the eighty-line unattended-runs block, because
    `[recurring]` and `[launch]` ship commented out and so are not headers
    `_TABLE_START` can see; this comments only live lines, which stops at the
    table's own last key. And a direct write that failed partway would leave a
    truncated coga.toml for init to commit, so the new text lands through a
    sibling temporary file and `os.replace`. Raises nothing: a failure here
    must not trigger init's rollback of an otherwise good repo.
    """
    try:
        text = coga_toml.read_text(encoding="utf-8")
        before = tomllib.loads(text)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    declared = before.get("agents")
    if not isinstance(declared, dict):
        declared = {}
    if not found:
        return [agent.name for agent in AGENT_CLIS if agent.name in declared]
    expected = [
        agent.name
        for agent in AGENT_CLIS
        if agent.name in found and agent.name in declared
    ]

    lines = text.splitlines(keepends=True)
    for agent in AGENT_CLIS:
        if agent.name in found or agent.name not in declared:
            continue
        header = _agent_table_start(agent.name)
        start = next(
            (i for i, line in enumerate(lines) if header.match(line)), None
        )
        if start is None:
            continue
        for i in range(start, len(lines)):
            stripped = lines[i].strip()
            if i > start and _TABLE_START.match(lines[i]):
                break
            if not stripped or stripped.startswith("#"):
                continue
            lines[i] = f"# {lines[i]}"
    new_text = "".join(lines)

    try:
        after = tomllib.loads(new_text)
    except tomllib.TOMLDecodeError:
        return None
    if list(after.get("agents", {})) != expected:
        return None
    if {k: v for k, v in after.items() if k != "agents"} != {
        k: v for k, v in before.items() if k != "agents"
    }:
        return None

    if new_text == text:
        # Every declared agent was found: nothing to comment out, so leave the
        # packaged bytes exactly as they shipped rather than rewriting them.
        return expected

    tmp = coga_toml.with_name(f"{coga_toml.name}.coga-tmp")
    try:
        tmp.write_text(new_text, encoding="utf-8", newline="\n")
        os.replace(tmp, coga_toml)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return expected


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
        text = ticket.read_text(encoding="utf-8")
        new_text, count = pattern.subn(f"agent: {new}", text)
        if count:
            ticket.write_text(new_text, encoding="utf-8", newline="\n")


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
    shared = tomllib.loads(template_root.joinpath("coga.toml").read_text(encoding="utf-8"))
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
            relocated_gitignore.write_text(_RELOCATED_CONTEXTS_GITIGNORE, encoding="utf-8", newline="\n")
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
        data = tomllib.loads(local_toml.read_text(encoding="utf-8"))
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
        document = tomlkit.parse(local_toml.read_text(encoding="utf-8"))
        document["user"] = name
        text = tomlkit.dumps(document)
        verb = "updated"
    tomllib.loads(text)
    local_toml.write_text(text, encoding="utf-8", newline="\n")
    return verb


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
    _offer_optional_tools()

    # A saved user is the completed-setup guard on the next invocation. Keep
    # the local config unchanged until every agent link is ready, so failures
    # and interruptions can be retried without hitting the re-init refusal.
    try:
        wired_agents, blocked_agents = _link_skills_for_agents(target, coga_os)
    except (OSError, LocalOverrideError) as exc:
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

    nested = not (target / ".git").exists() and is_git_repo(target)
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
    # Every precondition has passed: only now offer optional supporting-tool
    # installs and `gh auth login`, then show what this machine can drive, so
    # a doomed invocation never changes the machine.
    #
    # This is the one PATH read for agents, and it is here for three reasons:
    # it is in no early-returning branch, so every interactive fresh init
    # prints it; it is before `target.mkdir()`, so it is outside the rollback
    # and writes nothing; and it is after the `op` note, so the scan's leading
    # blank line is what separates them. Its result configures coga.toml once
    # that file exists, which is why the snapshot is kept rather than re-read:
    # the rows the user just read are the agents the repo ends up declaring.
    # `None` means non-interactive, which is distinct from `[]`, found nothing.
    # The clone path gets no call: a clone's coga.toml is committed team config
    # and the scan is about this machine.
    _offer_optional_tools()
    found_agent_clis = print_agent_scan() if _interactive() else None
    template_default_agent = _template_default_agent(template_root)

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
        local_toml.write_text(render_local_toml(name), encoding="utf-8", newline="\n")

        # Write the scan's answer into the config every later command reads.
        # Non-interactive init (`found_agent_clis is None`) never touches the
        # file: a scripted run saw no scan to act on, so the packaged template
        # declaring every supported agent stands.
        configured_agents = (
            None
            if found_agent_clis is None
            else _configure_agent_tables(coga_os / "coga.toml", found_agent_clis)
        )
        # Point the delivered tickets' `agent:` at the first agent the file
        # still declares — not the first found, which may be a registry entry
        # the template never declared a table for.
        if (
            configured_agents
            and template_default_agent is not None
            and configured_agents[0] != template_default_agent
        ):
            _stamp_agent_into_delivered_tickets(
                coga_os, template_default_agent, configured_agents[0]
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
    # Read the outcome back off disk rather than inferring it from the scan:
    # after a failed rewrite the packaged file is still there declaring
    # everything, and a message built from `found_agent_clis` would describe a
    # file the user does not have. Every line below reads these two lists.
    declared_agents, commented_out_agents = _agent_table_state(
        coga_os / "coga.toml"
    )
    # Init comments a table out only beside one it kept, so a file with every
    # table commented out is a scaffold's choice, which the agent step below
    # reports, not something this run did.
    if commented_out_agents and declared_agents:
        tables = ", ".join(f"[agents.{name}]" for name in commented_out_agents)
        missing = ", ".join(f"`{name}`" for name in commented_out_agents)
        kept = ", ".join(agent_label(name) for name in declared_agents)
        typer.echo(
            f"Declared {kept} in {coga_os / 'coga.toml'}; commented out "
            f"{tables} ({missing} not on PATH) — uncomment once installed."
        )
    if found_agent_clis is not None and configured_agents is None:
        typer.secho(
            f"Could not configure the agent tables in {coga_os / 'coga.toml'}: "
            f"it was left exactly as packaged, so it declares every supported "
            f"agent. Comment out the [agents.*] table of any agent you have "
            f"not installed.",
            fg=typer.colors.YELLOW,
        )
    if host_gitignore_changed:
        typer.echo(f"Updated {target / '.gitignore'} (coga-managed block).")
    if written_guides:
        typer.echo(
            f"Wrote {', '.join(written_guides)} (agent orientation — Claude Code / Codex)."
        )
    typer.echo("Commit `coga/` when ready.")
    if relocated_contexts is not None and not relocated_contexts.is_relative_to(coga_os):
        typer.echo(f"Include the relocated contexts at {relocated_contexts}.")

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
            "       uv tool install --python 3.11 coga"
        )
    # `coga build` / `coga launch` drive an agent CLI that init deliberately
    # neither requires nor installs (see `coga.dependencies`) — name the
    # prerequisite here, and only for the user the scan shows has none, so a
    # fresh user isn't sent into the flow only to hit "not found".
    #
    # Init leaves every table live when it finds no agent CLI, so installing
    # the binary is the whole remedy and the step names no `.toml`. Only a
    # coga.toml that declares no agent at all (a scaffold shipping its tables
    # commented out) sends the reader to the file, because there installing is
    # half the remedy and the other half is an uncomment.
    if not (found_agent_clis if found_agent_clis is not None else _installed_agent_clis()):
        drivable = " or ".join(f"{agent.display} (`{agent.name}`)" for agent in AGENT_CLIS)
        remedy = (
            "Install one, then uncomment its [agents.*] table in "
            f"{coga_os / 'coga.toml'}. "
            if not declared_agents
            else ""
        )
        steps.append(
            f"No agent CLI was found — coga drives {drivable}. {remedy}"
            "Agent-backed commands (`coga build`, `coga launch`, "
            "`coga ticket`) need one."
        )
    if is_empty:
        # Advertise only what coga.toml declares: a one-agent repo has no
        # `--agent` alternative to offer. With nothing declared, the delivered
        # ticket still names the template default, and the prerequisite line
        # above has already said what to do first.
        build_agent = (
            declared_agents[0] if declared_agents else template_default_agent
        ) or AGENT_CLIS[0].name
        alternatives = "".join(
            f", or `coga build --agent {name}` with {agent_label(name)}"
            for name in declared_agents
            if name != build_agent
        )
        steps.append(
            f"Run `coga build` with {agent_label(build_agent)}{alternatives} "
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
            path.write_text(AGENT_GUIDE_TEMPLATE, encoding="utf-8", newline="\n")
        except OSError:
            continue
        written.append(name)
    return written


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
