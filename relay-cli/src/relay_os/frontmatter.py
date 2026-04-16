"""YAML frontmatter parsing and writing for ticket.md / SKILL.md / etc.

Almost every CLI command uses this. `relay create` writes ticket
frontmatter, `relay step` updates the step field, `relay launch` reads
fields, `relay status` reads fields across many tickets. Getting it
wrong (mangled YAML, lost body, trailing-whitespace drift) breaks
downstream commands silently.

Design choices:

1. **Class-based API.** `Document.read(path)` returns a Document that
   exposes `.frontmatter`, `.body`, `.get(key)`, `.update(**kwargs)`,
   and `.save()`. We need state (the original raw frontmatter text) to
   make no-op round-trips byte-identical.

2. **Lazy writes.** If `update()` is never called, `save()` writes the
   original frontmatter back verbatim. Only when fields actually change
   do we re-emit via `yaml.safe_dump(sort_keys=False)` — which respects
   dict insertion order in Python 3.7+ so explicitly-modified fields
   keep their original position.

3. **Body is bytes.** The body is captured exactly between the closing
   `---` and EOF. No trim, no normalization, no trailing-newline policy.
   What you read is what you write back.

4. **Missing frontmatter is OK.** A file without `---` delimiters is
   treated as body-only; `Document.frontmatter` is `{}`.

5. **No external dependencies beyond PyYAML.** We don't pull in
   `ruamel.yaml`. The lazy-write strategy gives us byte-identical
   round-trips for the common case (read, then save without updates),
   and `safe_dump` is good enough for the modify case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "error: relay-os requires PyYAML. Install with: pip install pyyaml"
    ) from e


# Matches `---\n<frontmatter>\n---\n<body>` with optional CRs and
# optional trailing newline after the closing delimiter. Non-greedy on
# the frontmatter capture so the FIRST `---` after the opener wins —
# `---` lines in the body are not treated as delimiters.
FRONTMATTER_RE = re.compile(
    r"^---\r?\n(.*?)---\r?\n?(.*)\Z",
    re.DOTALL,
)


# Matches `N (step-name)` — what the spec uses for the `step` field.
_STEP_FIELD_RE = re.compile(r"^\s*(\d+)\s*\((.+)\)\s*$")


class FrontmatterError(Exception):
    """Raised on parse failures, malformed YAML, or non-mapping
    frontmatter. The CLI surface translates these into non-zero exits
    with a user-readable message."""


@dataclass
class Document:
    """A markdown file with YAML frontmatter.

    Read with `Document.read(path)`, mutate via `update()`, write back
    with `save()`. Mutations are tracked so `save()` can reuse the
    original raw frontmatter text when nothing changed (giving a
    byte-identical round-trip).
    """

    path: Path
    frontmatter: dict
    body: str
    _raw_frontmatter: str | None = None
    _had_frontmatter: bool = True
    _dirty: bool = False

    # ----- I/O -----

    @classmethod
    def read(cls, path: Path) -> "Document":
        path = Path(path)
        text = path.read_text()
        return cls._parse(path, text)

    @classmethod
    def parse(cls, text: str, path: Path | None = None) -> "Document":
        """Parse from a string instead of a file. Useful for tests and
        for callers that already have the bytes in memory."""
        return cls._parse(path or Path("<string>"), text)

    @classmethod
    def _parse(cls, path: Path, text: str) -> "Document":
        m = FRONTMATTER_RE.match(text)
        if not m:
            # No frontmatter — entire file is body.
            return cls(
                path=path,
                frontmatter={},
                body=text,
                _raw_frontmatter=None,
                _had_frontmatter=False,
            )

        raw_fm = m.group(1)
        body = m.group(2)

        try:
            parsed = yaml.safe_load(raw_fm)
        except yaml.YAMLError as e:
            raise FrontmatterError(f"{path}: invalid YAML in frontmatter: {e}") from e

        if parsed is None:
            parsed = {}
        elif not isinstance(parsed, dict):
            raise FrontmatterError(
                f"{path}: frontmatter must be a YAML mapping, got "
                f"{type(parsed).__name__}"
            )

        return cls(
            path=path,
            frontmatter=parsed,
            body=body,
            _raw_frontmatter=raw_fm,
            _had_frontmatter=True,
        )

    def save(self, path: Path | None = None) -> None:
        """Write the document back. If `update()` was never called,
        the original frontmatter text is reused verbatim — making the
        on-disk file byte-identical to what was read."""
        target = Path(path) if path else self.path
        target.write_text(self._render())

    def _render(self) -> str:
        if not self._dirty and self._raw_frontmatter is not None:
            return f"---\n{self._raw_frontmatter}---\n{self.body}"
        if not self._had_frontmatter and not self.frontmatter:
            return self.body
        if not self.frontmatter:
            # Started with frontmatter, all fields removed — emit empty fm.
            return f"---\n---\n{self.body}"
        fm_text = yaml.safe_dump(
            self.frontmatter,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=1_000_000,  # don't wrap long strings
        )
        # safe_dump always ends with a newline — we want exactly one
        # before the closing `---`.
        if not fm_text.endswith("\n"):
            fm_text += "\n"
        return f"---\n{fm_text}---\n{self.body}"

    # ----- Accessors -----

    def get(self, key: str, default: Any = None) -> Any:
        return self.frontmatter.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.frontmatter

    # ----- Mutation -----

    def update(self, **kwargs: Any) -> None:
        """Update one or more frontmatter fields. Existing keys keep
        their position; new keys are appended in call order.

        Marks the document dirty so `save()` will re-emit the
        frontmatter rather than reusing the raw original."""
        if not kwargs:
            return
        for k, v in kwargs.items():
            self.frontmatter[k] = v
        self._dirty = True
        self._had_frontmatter = True

    def set(self, key: str, value: Any) -> None:
        """Single-key convenience for callers that prefer it over
        `update(**{key: value})`."""
        self.update(**{key: value})

    def remove(self, key: str) -> None:
        """Delete a field if present. No-op if the key isn't there."""
        if key in self.frontmatter:
            del self.frontmatter[key]
            self._dirty = True


# ----- Step field helpers -----


def parse_step_field(s: str | None) -> tuple[int | None, str | None]:
    """Parse the `step` field format `N (step-name)`.

    Returns `(None, None)` if the field is None, empty, or doesn't
    match the format. Step numbers are 1-indexed per spec.
    """
    if not s:
        return None, None
    m = _STEP_FIELD_RE.match(s)
    if not m:
        return None, None
    return int(m.group(1)), m.group(2)


def format_step_field(n: int, name: str) -> str:
    """Inverse of `parse_step_field`. Use when writing the step field
    so format stays consistent across the codebase."""
    return f"{n} ({name})"
