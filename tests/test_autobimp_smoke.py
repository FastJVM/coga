"""Self-contained smoke test carried by the `test-autobimp` ticket.

Exists to give the auto-relaunch supervisor a real, green diff to chain
through `implement → self-qa → pr`. It asserts stable, pure `slugify`
behaviors not already covered by `test_primitives.py` — no source change,
nothing env- or timing-dependent, so it can't flake and muddy the signal.
"""

from __future__ import annotations

from relay.slugify import slugify


def test_slugify_empty_string_falls_back_to_task() -> None:
    assert slugify("") == "task"


def test_slugify_collapses_separator_runs() -> None:
    assert slugify("Hello,   World!!!") == "hello-world"


def test_slugify_trims_surrounding_whitespace() -> None:
    assert slugify("  Leading and Trailing  ") == "leading-and-trailing"
