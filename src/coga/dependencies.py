"""Coga's external command-line dependencies — the single source of truth.

Coga shells out to a few human-installed CLIs. This manifest names each, why
coga needs it, where to install it, and whether it is required at `coga init`
(a hard crash up front) or only when a specific feature is actually used (a
softer, deferred failure at the point of need).

`coga init` reads `required_at_init` to decide what to enforce before doing
anything; the README's "Getting Started" section describes the same set for
humans. Keeping the list here means the init check and the docs can't drift.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    """One external CLI coga depends on.

    `name` is the binary as found on PATH; `purpose` is why coga needs it;
    `install` is an install URL/hint; `required_at_init` is True when a missing
    binary must crash `coga init` (vs. being enforced later, when first used).
    """

    name: str
    purpose: str
    install: str
    required_at_init: bool


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        name="git",
        purpose=(
            "Coga stores all task state in git and vendors its CLI via a "
            "clone — nothing works without it."
        ),
        install="https://git-scm.com/downloads",
        required_at_init=True,
    ),
    Dependency(
        name="gh",
        purpose=(
            "GitHub PR workflows — opening PRs, the merged-ticket autoclose "
            "sweep, and `gh skill`-backed managed skill installs. Run "
            "`gh auth login` once installed. Not required at init: every "
            "consumer enforces it at the point of need — managed skill "
            "installs degrade to a warn-with-hint skip, the open-pr step and "
            "autoclose sweep fail loud with setup hints, and "
            "`coga validate --check-github` probes install/auth proactively — "
            "so init works on a machine that never opens PRs."
        ),
        install="https://cli.github.com",
        required_at_init=False,
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
    ),
    Dependency(
        name="claude",
        purpose=(
            "Claude Code — an agent CLI coga drives for `coga launch`, "
            "`coga ticket`, and `coga build`. Not required at init: which "
            "binary a launch needs comes from the launched agent's `cli` in "
            "coga.toml, and the launch fails loud at the point of need. "
            "Install and authenticate it before launching agents."
        ),
        install="https://claude.com/claude-code",
        required_at_init=False,
    ),
    Dependency(
        name="codex",
        purpose=(
            "Codex — an agent CLI coga drives for `coga launch`, "
            "`coga ticket`, and `coga build`. Not required at init: which "
            "binary a launch needs comes from the launched agent's `cli` in "
            "coga.toml, and the launch fails loud at the point of need. "
            "Install and authenticate it before launching agents."
        ),
        install="https://github.com/openai/codex",
        required_at_init=False,
    ),
)


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
