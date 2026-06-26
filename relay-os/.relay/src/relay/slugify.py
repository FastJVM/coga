"""Turn a human title into a filesystem slug."""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 50) -> str:
    """Lowercase, hyphen-separated, trimmed to max_len."""
    lowered = text.lower()
    slug = _SLUG_RE.sub("-", lowered).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or "task"


__all__ = ["slugify"]
