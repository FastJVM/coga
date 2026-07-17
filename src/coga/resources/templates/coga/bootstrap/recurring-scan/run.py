from __future__ import annotations

import os
import sys

import typer

from coga.config import ConfigError, load_config
from coga.recurring_runner import run_recurring_scan


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2

    return run_recurring_scan(
        cfg,
        force=_env_flag("COGA_RECURRING_FORCE"),
        interactive=_env_flag("COGA_RECURRING_INTERACTIVE"),
        agent_override=os.environ.get("COGA_RECURRING_AGENT") or None,
        require_fresh_control=_env_flag("COGA_RECURRING_REQUIRE_FRESH_CONTROL"),
    )


def _env_flag(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    sys.exit(main())
