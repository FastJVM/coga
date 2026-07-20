"""Shared validation and defaults for Coga CLI aliases."""

from __future__ import annotations

import shlex
import sys

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
        "open-pr",
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
        "project",
        "validate",
        "secret",
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
# interactive megalaunch picker.
DEFAULT_ALIASES: dict[str, str] = {
    "chat": "launch bootstrap/orient",
    "dream": "recurring launch dream",
    "build": "launch coga-build",
    "skill-update": "recurring launch skill-update",
    "autoclose": "recurring launch autoclose-merged",
    "pick": "megalaunch --pick",
}


LEGACY_ALIASES: dict[str, str] = {
    "create": "launch bootstrap/ticket",
}


def validate_aliases(
    aliases: dict[str, str], *, warn_legacy: bool = True
) -> None:
    """Reject aliases that collide with or target unknown built-in commands.

    The exact legacy ``create`` alias is removed rather than rejected. CLI
    startup warns about that migration; read-only preflight callers can disable
    the duplicate notice while applying the same validation semantics.
    """
    for name in list(aliases):
        expansion = aliases[name]
        if LEGACY_ALIASES.get(name) == expansion:
            if warn_legacy:
                print(
                    f"coga: dropping legacy alias {name!r} from coga.toml "
                    f"({name!r} is now a built-in command — remove the line "
                    f"under [aliases]).",
                    file=sys.stderr,
                )
            del aliases[name]
            continue
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
