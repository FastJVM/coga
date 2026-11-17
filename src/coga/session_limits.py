"""Liveness limit resolution shared by recurring and queue callers."""
from __future__ import annotations

import math
import os

from coga.config import Config


def _env_seconds(name: str) -> tuple[bool, float | None]:
    """Read a seconds value from env var `name`.

    Returns `(present, value)`: `present` is False when the var is unset (so
    the caller falls back to config/default); when set, `value` is the parsed
    seconds or None for a `<= 0`, non-finite, or unparseable value (an explicit
    "disarm this backstop"). The env override always wins over config when set —
    even to disarm — so a machine can turn a committed default off locally.
    """
    raw = os.environ.get(name)
    if raw is None:
        return False, None
    try:
        seconds = float(raw)
    except ValueError:
        return True, None
    if not math.isfinite(seconds) or seconds <= 0:
        return True, None
    return True, seconds


def resolve_idle_timeout(cfg: Config, *, default: float | None) -> float | None:
    """Resolve env > explicit config > the caller's idle default."""
    present, value = _env_seconds("COGA_REPL_IDLE_TIMEOUT")
    if present:
        return value
    if cfg.launch_idle_timeout_present:
        return cfg.launch_idle_timeout
    return default


def resolve_max_session(cfg: Config) -> float | None:
    """Resolve env > config; no caller arms an implicit wall-clock cap."""
    present, value = _env_seconds("COGA_REPL_MAX_SESSION")
    return value if present else cfg.launch_max_session
