"""Shared validation and defaults for Coga CLI aliases."""

from __future__ import annotations

import shlex

from coga.config import ConfigError


# Names registered by ``coga.cli``. Alias validation uses this set without
# importing the command head, which keeps reusable config checks below the CLI
# layer. ``tests/test_aliases.py`` verifies that it matches Typer's registry.
BUILTIN_COMMANDS: frozenset[str] = frozenset(
    {
        "init",
        "uninstall",
        "create",
        "launch",
        "megalaunch",
        "status",
        "show",
        "bump",
        "block",
        "unblock",
        "delete",
        "retire",
        "slack",
        "digest",
        "usage",
        "skill",
        "mark",
        "recurring",
        "ticket",
        "validate",
        "secret",
        "run",
    }
)


# Aliases registered for every user, regardless of whether their ``coga.toml``
# has an ``[aliases]`` section. User aliases override matching defaults. This
# keeps ``coga chat`` discoverable and dispatchable in repos initialized before
# the defaults convention, or where the user dropped the section.
#
# ``dream`` is a default alias rather than a built-in command: a Dream run is an
# ordinary recurring task, and ``coga dream`` takes the same path as ``coga
# recurring launch dream``. ``build`` is similarly the first-run alias for
# ``launch coga-build``. ``skill-update`` and ``autoclose`` launch ordinary
# recurring tasks on demand, while ``pick`` is the short spelling for the
# interactive megalaunch picker. ``open-pr`` is the short spelling for the
# registered ``open-pr`` recipe — the argv rewrite hands the task ref to the
# generic runner as ordinary argv (``coga open-pr <slug>`` → ``run open-pr
# <slug>``). ``resolve-conflicts`` fronts an agent-backed command ticket; its
# optional PR selector reaches the appended launch-argument prompt block
# through the same argv rewrite.
DEFAULT_ALIASES: dict[str, str] = {
    "chat": "launch bootstrap/orient",
    "dream": "recurring launch dream",
    "build": "launch coga-build",
    "skill-update": "recurring launch skill-update",
    "autoclose": "recurring launch autoclose-merged",
    "pick": "megalaunch --pick",
    "open-pr": "run open-pr",
    "resolve-conflicts": "launch bootstrap/resolve-conflicts",
}


def validate_aliases(aliases: dict[str, str]) -> None:
    """Reject aliases that collide with or target unknown built-in commands."""
    for name, expansion in aliases.items():
        if name in BUILTIN_COMMANDS:
            raise ConfigError(
                f"alias {name!r} collides with built-in command — rename it."
            )
        tokens = shlex.split(expansion)
        if not tokens:
            raise ConfigError(f"alias {name!r} expands to empty command")
        target = tokens[0]
        if target not in BUILTIN_COMMANDS:
            raise ConfigError(
                f"alias {name!r} expands to unknown command {target!r} "
                f"(known: {sorted(BUILTIN_COMMANDS)})"
            )
