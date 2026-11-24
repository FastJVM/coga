"""ticket.md — YAML frontmatter + markdown body."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from coga.atomicio import atomic_write_text


class TicketError(Exception):
    """Raised on malformed ticket files."""


class TicketNotFoundError(TicketError, FileNotFoundError):
    """Raised when a ticket file is missing from disk.

    Subclasses both so callers guarding reads with `except TicketError` and
    pre-existing `except FileNotFoundError` handlers each keep catching it.
    """


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

# libyaml's safe loader parses frontmatter ~8x faster than the pure-Python one
# and builds the same values (same SafeConstructor); fall back when the C
# extension isn't compiled in.
_SafeLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


# Canonical ticket frontmatter key set. Anything outside this is a repo
# extension (declared via `[ticket.fields.<name>]` in `coga.toml`) and is
# rendered below the `# --- extensions ---` marker. Kept here so renderer and
# validator share the same source of truth.
CANONICAL_TICKET_KEYS: frozenset[str] = frozenset({
    "title",
    "status",
    "owner",
    "agent",
    "workflow",
    "step",
    "contexts",
    "skills",
    "delegate",
    "secrets",
})

# Metadata the simplified format removed outright. These are not ordinary
# orphan extensions: each one used to carry routing or notification meaning, so
# leaving a stale copy on disk would look authoritative while nothing reads it.
# `coga validate` reports them by name as errors, which makes every Coga writer
# (each calls `assert_task_valid` before or after its write) refuse a ticket
# that still carries one instead of perpetuating it. `config.py` also keeps
# these names reserved against `[ticket.fields.*]` so a repo extension cannot
# quietly restore independent assignment.
#
# - `slug` duplicated the task's path-derived `TaskRef.id_slug`.
# - `human` always equalled `owner` in practice; `owner` is the human of record.
# - `assignee` cached a routing result now derived from the frozen workflow
#   step's role (see `coga.bump.resolve_operator`).
# - `watchers` cc'd Slack notifications and was never populated.
REJECTED_TICKET_KEYS: frozenset[str] = frozenset({
    "slug",
    "human",
    "assignee",
    "watchers",
})

EXTENSION_MARKER = "# --- extensions ---"

@dataclass
class Ticket:
    frontmatter: dict[str, Any]
    body: str

    # --- parsing / rendering ---------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Ticket":
        match = _FM_RE.match(text)
        if not match:
            raise TicketError("ticket.md must begin with YAML frontmatter between --- lines")
        fm_text, body = match.group(1), match.group(2)
        try:
            fm = yaml.load(fm_text, Loader=_SafeLoader) or {}
        except yaml.YAMLError as exc:
            raise TicketError(f"Invalid YAML frontmatter: {exc}") from exc
        if not isinstance(fm, dict):
            raise TicketError("Frontmatter must be a YAML mapping")
        return cls(frontmatter=fm, body=body)

    def render(self) -> str:
        canonical: dict[str, Any] = {}
        extensions: dict[str, Any] = {}
        for key, value in self.frontmatter.items():
            if _omit_empty_optional(key, value):
                continue
            if key in CANONICAL_TICKET_KEYS:
                canonical[key] = value
            else:
                extensions[key] = value

        fm_text = yaml.safe_dump(
            canonical,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).rstrip()
        if extensions:
            ext_text = yaml.safe_dump(
                extensions,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).rstrip()
            fm_text = f"{fm_text}\n{EXTENSION_MARKER}\n{ext_text}"

        body = self.body.lstrip("\n")
        return f"---\n{fm_text}\n---\n\n{body}" if body else f"---\n{fm_text}\n---\n"

    # --- io --------------------------------------------------------------------

    @classmethod
    def read(cls, path: Path) -> "Ticket":
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise TicketNotFoundError(f"ticket file missing: {path}") from exc
        return cls.parse(text)

    def write(self, path: Path) -> None:
        # Atomic so a crash mid-write can't leave a truncated ticket.md for the
        # next `coga validate` to trip on (see coga.atomicio).
        atomic_write_text(path, self.render())

    # --- helpers ---------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.frontmatter.get("title", "")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "")

    @property
    def owner(self) -> str | None:
        return self.frontmatter.get("owner")

    @property
    def agent(self) -> str | None:
        """This ticket's optional main-agent choice, exactly as stored.

        Deliberately raw: it is *not* the current operator (a workflow step may
        route to the owner or to the main agent's peer), and it is not resolved
        against `[agents.*]` here. `coga.bump.resolve_main_agent` owns the
        configured-agent check, and `coga.bump.resolve_operator` owns routing,
        so an accessor never loads config or writes a file.
        """
        return self.frontmatter.get("agent")

    @property
    def contexts(self) -> list[str]:
        value = self.frontmatter.get("contexts") or []
        return list(value)

    @property
    def skills(self) -> list[str]:
        """Ticket-level skill refs (plural). Used by bootstrap tickets that
        aren't workflow-bound and by normal tickets that want extra process
        instructions on top of the current workflow step."""
        value = self.frontmatter.get("skills") or []
        return list(value)

    @property
    def delegate(self) -> str | None:
        """Frozen recurring bootstrap target, absent on ordinary tasks."""
        value = self.frontmatter.get("delegate")
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip()

    @property
    def secrets(self) -> Any:
        """Raw `secrets:` frontmatter value.

        Absent, explicit null, and explicit empty all mean "no secrets
        declared" — see `coga.config.parse_inline_secrets` /
        `select_launch_secrets`, which treat the three alike — so the renderer
        omits every one of them. A non-empty list declares least-privilege
        inline references (`op://…`, `env:VAR`). Kept raw rather than
        normalized with `or []` so `coga validate` can still report a malformed
        non-list value instead of seeing it erased.
        """
        return self.frontmatter.get("secrets")

    @property
    def workflow(self) -> dict[str, Any] | str | None:
        # Frozen as a dict post-launch; can be a bare string ref on
        # hand-authored / draft tickets that haven't been launched yet.
        return self.frontmatter.get("workflow")

    @property
    def step(self) -> str | None:
        return self.frontmatter.get("step")

    def step_index(self) -> int | None:
        """Return 1-indexed step number, or None if no workflow."""
        step = self.step
        if not step:
            return None
        # Format: "N (step-name)"
        match = re.match(r"(\d+)\s*\(", step)
        return int(match.group(1)) if match else None

    def current_step(self) -> dict[str, Any] | None:
        """Return the current workflow step dict, or None."""
        wf = self.workflow
        idx = self.step_index()
        if not isinstance(wf, dict) or idx is None:
            return None
        steps = wf.get("steps", [])
        if 1 <= idx <= len(steps):
            return steps[idx - 1]
        return None


def _omit_empty_optional(key: str, value: Any) -> bool:
    """Whether an optional declaration is empty and should not be rendered.

    Absence *is* empty for `contexts` / `skills` / `secrets`, so a rendered
    ticket stops carrying rows that say nothing. Only genuinely empty values
    disappear: an explicit null `contexts:`/`skills:` and any malformed falsy
    value (`""`, `0`, `False`, `{}`) stays on disk so `coga validate` can name
    it rather than silently erasing a typo as though it were an empty list.
    """
    if key in ("contexts", "skills"):
        return isinstance(value, list) and not value
    if key == "secrets":
        return value is None or (isinstance(value, list) and not value)
    return False


__all__ = [
    "CANONICAL_TICKET_KEYS",
    "REJECTED_TICKET_KEYS",
    "Ticket",
    "TicketError",
    "TicketNotFoundError",
]
