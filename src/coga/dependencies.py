"""Coga's external command-line dependency handling.

Coga shells out to supporting tools and agent CLIs. `DEPENDENCIES` names the
supporting tools, why Coga needs them, where to install them, and whether they
are required at `coga init` (a hard crash up front) or only when a specific
feature is used (a softer, deferred failure at the point of need).

`coga init` reads `required_at_init` to decide what to enforce before doing
anything, and `offer_install` / `packages` to offer installing a missing tool
through the machine's package manager. Agent CLIs are separate: `AGENT_CLIS`
holds one `AgentCLI` record per supported agent in scan order, and Coga
resolves the configured `cli` only at the point of need. Coga never installs
an agent CLI or names an agent installer; a missing one is a `coga.toml` fix.
The `coga/init` topic summarizes the same set for humans and points here.
Keeping the list here means the init check and the docs can't drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dependency:
    """One external CLI coga depends on.

    `name` is the binary as found on PATH; `purpose` is why coga needs it;
    `install` is an install URL/hint; `required_at_init` is True when a missing
    binary must crash `coga init` (vs. being enforced later, when first used).
    `offer_install` is the default answer when an interactive `coga init`
    offers to install the missing binary, or None to never offer; `packages`
    maps a package manager (see `PACKAGE_MANAGERS`) to the argv tail that
    installs the binary with it. A manager absent from `packages` falls back
    to the `install` URL.
    """

    name: str
    purpose: str
    install: str
    required_at_init: bool
    offer_install: bool | None = None
    packages: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentCLI:
    """One agent CLI Coga knows how to drive.

    `name` is both the binary Coga scans PATH for and the `[agents.<name>]`
    type the shipped `coga.toml` declares — one string, because the packaged
    template's `[agents.claude]` sets `cli = "claude"` and `[agents.codex]`
    sets `cli = "codex"`, so the two are equal for every agent Coga ships.
    Split them when a supported agent's binary first differs from its table
    name. `label` is the vendor's display name; `display` falls back to `name`,
    which is what keeps a label-less entry total by construction — no caller
    repeats a `.get`.

    The record carries no install URL and no `packages`: Coga installs no
    agent CLI, so there is nothing here that could install anything.
    """

    name: str
    label: str = ""

    @property
    def display(self) -> str:
        return self.label or self.name


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        name="git",
        purpose=(
            "Coga stores all task state in git and vendors its CLI via a "
            "clone — nothing works without it."
        ),
        install="https://git-scm.com/downloads",
        required_at_init=True,
        offer_install=True,
        packages={
            "brew": ("git",),
            "apt-get": ("git",),
            "dnf": ("git",),
            "pacman": ("git",),
            "winget": ("--id", "Git.Git", "-e"),
        },
    ),
    Dependency(
        name="gh",
        purpose=(
            "GitHub PR workflows — opening PRs, the merged-ticket autoclose "
            "sweep, and the explicit `gh skill`-backed `coga skill install` / "
            "`update`. Run `gh auth login` once installed. Not required at "
            "init: init installs no skills, and every consumer enforces `gh` "
            "at the point of need — `coga skill install`, the open-pr step, "
            "and the autoclose sweep fail loud with setup hints, and "
            "`coga validate --check-github` probes install/auth proactively — "
            "so init works on a machine that never opens PRs."
        ),
        install="https://cli.github.com",
        required_at_init=False,
        offer_install=True,
        packages={
            "brew": ("gh",),
            "apt-get": ("gh",),
            "dnf": ("gh",),
            "pacman": ("github-cli",),
            "winget": ("--id", "GitHub.cli", "-e"),
        },
    ),
    Dependency(
        name="op",
        purpose=(
            "1Password CLI — needed only when a ticket declares an "
            "`op://vault/item/field` secret, which coga resolves live with "
            "`op read` at launch (run `op signin`). Tickets that use only "
            "`env:VAR` secrets never invoke it, so it is not required at init; "
            "a launch that needs it fails loud if it is missing."
        ),
        install="https://developer.1password.com/docs/cli/get-started/",
        required_at_init=False,
        # Never offered (and so no `packages`): a secrets manager is the
        # user's own choice, and init installing 1Password would read as coga
        # picking one for them. A missing `op` gets its own note instead
        # (`init._note_missing_op`), naming what needs it.
        offer_install=None,
    ),
)


# Package managers coga knows how to drive, each mapped to the argv head that
# installs a package non-interactively. Linux managers need root; init
# prefixes `sudo` when it is not already root.
PACKAGE_MANAGERS: dict[str, tuple[str, ...]] = {
    "brew": ("brew", "install"),
    "winget": ("winget", "install"),
    "apt-get": ("apt-get", "install", "-y"),
    "dnf": ("dnf", "install", "-y"),
    "pacman": ("pacman", "-S", "--noconfirm"),
}
NEEDS_ROOT = frozenset({"apt-get", "dnf", "pacman"})

# Agent CLIs Coga knows how to drive, in stable scan order; the first is the
# shipped `coga.toml`'s default agent. One record per agent feeds both the
# init scan and init's next-steps labels, so a fourth agent is one edit here
# rather than one per reader. There is deliberately no derived
# `tuple[str, ...]` alias: two public names for one list is the split these
# records exist to close.
AGENT_CLIS: tuple[AgentCLI, ...] = (
    AgentCLI("claude", "Claude Code"),
    AgentCLI("codex", "Codex"),
)


def agent_label(name: str) -> str:
    """The display name for agent type `name`, or `name` itself.

    Takes a plain string rather than a record because callers hold an agent
    type that may not be in the registry at all: a repo's `default_agent` can
    name any agent its `coga.toml` declares. An unregistered type reads under
    its own name instead of raising.
    """
    for agent in AGENT_CLIS:
        if agent.name == name:
            return agent.display
    return name


def agent_cli_missing_message(name: str, cli: str) -> str:
    """Error text for a configured agent CLI Coga could not resolve.

    `name` is the `[agents.<name>]` table that declared the agent and `cli` is
    its `cli` value, so the message can point at the one line to change. Coga
    never installs an agent CLI: the remedy is always a `coga.toml` edit. `cli`
    may be a bare binary name or a full path, which `shutil.which` resolves
    either way, so the message names the config rather than the lookup.
    """
    return (
        f"Agent CLI {cli!r} not found. Set `cli` in [agents.{name}] in "
        "coga.toml to your agent CLI."
    )
