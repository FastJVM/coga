"""Coga's external command-line dependencies — the single source of truth.

Coga shells out to a few human-installed CLIs. This manifest names each, why
coga needs it, where to install it, and whether it is required at `coga init`
(a hard crash up front) or only when a specific feature is actually used (a
softer, deferred failure at the point of need).

`coga init` reads `required_at_init` to decide what to enforce before doing
anything, and `offer_install` / `packages` to offer installing a missing tool
through the machine's package manager. Agent CLIs (`AGENT_CLIS`) carry
`packages` and `login` for `coga.agent_cli_setup` instead, which offers them
through brew or npm rather than the system package manager. The README's "Getting Started" section
describes the same set for humans. Keeping the list here means the init check
and the docs can't drift.
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
    to the `install` URL. `login` is the argv tail that logs the installed
    binary in (empty runs the bare binary), or None when coga offers no login.
    """

    name: str
    purpose: str
    install: str
    required_at_init: bool
    offer_install: bool | None = None
    packages: dict[str, tuple[str, ...]] = field(default_factory=dict)
    login: tuple[str, ...] | None = None


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
        # Most repos never declare an `op://` secret: offered, default no.
        # Linux distros need 1Password's own repo, so only brew/winget.
        offer_install=False,
        packages={
            "brew": ("--cask", "1password-cli"),
            "winget": ("--id", "AgileBits.1Password.CLI", "-e"),
        },
    ),
    Dependency(
        name="claude",
        purpose=(
            "Claude Code — an agent CLI coga drives for `coga launch`, "
            "`coga ticket`, and `coga build`. Not required at init: which "
            "binary a launch needs comes from the launched agent's `cli` in "
            "coga.toml, and the launch fails loud at the point of need. "
            "Interactive `coga init` and `coga build` offer to install and "
            "log it in."
        ),
        install="https://claude.com/claude-code",
        required_at_init=False,
        packages={
            "brew": ("--cask", "claude-code"),
            "npm": ("@anthropic-ai/claude-code",),
        },
        login=(),
    ),
    Dependency(
        name="codex",
        purpose=(
            "Codex — an agent CLI coga drives for `coga launch`, "
            "`coga ticket`, and `coga build`. Not required at init: which "
            "binary a launch needs comes from the launched agent's `cli` in "
            "coga.toml, and the launch fails loud at the point of need. "
            "Interactive `coga init` and `coga build` offer to install and "
            "log it in."
        ),
        install="https://github.com/openai/codex",
        required_at_init=False,
        packages={
            "brew": ("--cask", "codex"),
            "npm": ("@openai/codex",),
        },
        login=("login",),
    ),
)


# Package managers coga knows how to drive, each mapped to the argv head that
# installs a package non-interactively. Linux managers need root; init
# prefixes `sudo` when it is not already root. `npm` serves only agent CLIs
# (`coga.agent_cli_setup`); init's system-manager detection never picks it.
PACKAGE_MANAGERS: dict[str, tuple[str, ...]] = {
    "brew": ("brew", "install"),
    "winget": ("winget", "install"),
    "apt-get": ("apt-get", "install", "-y"),
    "dnf": ("dnf", "install", "-y"),
    "pacman": ("pacman", "-S", "--noconfirm"),
    "npm": ("npm", "install", "-g"),
}
NEEDS_ROOT = frozenset({"apt-get", "dnf", "pacman"})

# Agent CLIs coga knows how to offer, in the order a picker lists them; the
# first is the shipped `coga.toml`'s default agent.
AGENT_CLIS: tuple[str, ...] = ("claude", "codex")


def install_hint(name: str) -> str | None:
    """The manifest's install URL for the binary `name`, or None if unlisted.

    Lets point-of-need "not found in PATH" errors carry the same install hint
    the init check prints, without each call site re-embedding URLs.
    """
    for dep in DEPENDENCIES:
        if dep.name == name:
            return dep.install
    return None


def agent_cli_missing_message(cli: str) -> str:
    """Error text for an agent CLI missing from PATH.

    `cli` is the launched agent's `cli` value from coga.toml — usually
    `claude` or `codex`, but any binary a repo configures. When the manifest
    knows the binary, the message carries its install hint; an unlisted one
    still fails loud, just without a URL.
    """
    message = f"Agent CLI {cli!r} not found in PATH."
    hint = install_hint(cli)
    if hint is not None:
        message += f" Install it from {hint} and authenticate, then re-run."
    return message
