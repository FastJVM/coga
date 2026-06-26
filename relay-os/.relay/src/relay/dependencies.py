"""Relay's external command-line dependencies — the single source of truth.

Relay shells out to a few human-installed CLIs. This manifest names each, why
relay needs it, where to install it, and whether it is required at `relay init`
(a hard crash up front) or only when a specific feature is actually used (a
softer, deferred failure at the point of need).

`relay init` reads `required_at_init` to decide what to enforce before doing
anything; the README's "External CLI Tools" section describes the same set for
humans. Keeping the list here means the init check and the docs can't drift.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    """One external CLI relay depends on.

    `name` is the binary as found on PATH; `purpose` is why relay needs it;
    `install` is an install URL/hint; `required_at_init` is True when a missing
    binary must crash `relay init` (vs. being enforced later, when first used).
    """

    name: str
    purpose: str
    install: str
    required_at_init: bool


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        name="git",
        purpose=(
            "Relay stores all task state in git and vendors its CLI via a "
            "clone — nothing works without it."
        ),
        install="https://git-scm.com/downloads",
        required_at_init=True,
    ),
    Dependency(
        name="gh",
        purpose=(
            "GitHub PR workflows — opening PRs and the merged-ticket autoclose "
            "sweep. Run `gh auth login` once installed."
        ),
        install="https://cli.github.com",
        required_at_init=True,
    ),
    Dependency(
        name="op",
        purpose=(
            "1Password CLI — needed only when a ticket declares an "
            "`op://vault/item/field` secret, which relay resolves live with "
            "`op read` at launch (run `op signin`). Tickets that use only "
            "`env:VAR` secrets never invoke it, so it is not required at init; "
            "a launch that needs it fails loud if it is missing."
        ),
        install="https://developer.1password.com/docs/cli/get-started/",
        required_at_init=False,
    ),
)
