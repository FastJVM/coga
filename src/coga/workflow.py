"""Workflow definitions — parsed from markdown files under coga/workflows/."""

from __future__ import annotations

import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from coga.taskfile import body_sections


class WorkflowError(Exception):
    """Raised on invalid workflow definitions."""


class WorkflowNotFoundError(WorkflowError, FileNotFoundError):
    """The definition is absent, rather than invalid or unreadable."""


_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


# Role tokens a workflow step may declare under `assignee:`. This is the whole
# routing vocabulary: the frozen step's role, not a stored nickname, decides who
# holds a ticket (see coga.bump.resolve_operator).
#
# - `owner` is a human handoff, resolving to the ticket's `owner:`.
# - `agent` is the ticket's main-agent choice.
# - `other-agent` is that agent's configured peer, or the only other configured
#   type when exactly one candidate remains. Ambiguity fails loud rather than
#   guessing (see coga.bump.resolve_other_agent).
#
# A step may also omit `assignee:`, which inherits the nearest preceding
# declared role. The retired `human` token is rejected rather than kept as a
# second spelling of `owner`; literal nicknames were never valid.
VALID_ASSIGNEE_ROLES: frozenset[str] = frozenset(
    {"owner", "agent", "other-agent"}
)

# Launch Git modes a workflow may declare under top-level `git:`. Each mode
# maps to the skill ref whose `run.py` launch runs around the whole launch
# (`enter` before classification, `exit` after the chain), or `None` for no
# hook. The kernel only reads the frozen mode and runs the mapped script; every
# Git command lives in that edge script. An omitted field means `main`.
DEFAULT_GIT_MODE = "main"
GIT_MODES: dict[str, str | None] = {
    "main": None,
    "ticket-branch": "git/ticket-branch",
}

@dataclass(frozen=True)
class WorkflowStep:
    name: str
    skills: tuple[str, ...] = ()
    assignee: str | None = None  # role token; see VALID_ASSIGNEE_ROLES
    # Completion gate token (see coga.step_gate). When set, `coga bump` refuses
    # to advance off this step until the named artifact is recorded on the
    # blackboard — e.g. `requires: pr` on the `open-pr` step.
    requires: str | None = None
    run: str | None = None


@dataclass
class Workflow:
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    body: str = ""
    git: str = DEFAULT_GIT_MODE  # launch Git mode; see GIT_MODES
    # step name -> markdown section body (used when step has no skills ref)
    inline_instructions: dict[str, str] = field(default_factory=dict)
    # other `## <heading>` sections; a ticket frozen before a step rename
    # finds its old step's instructions here
    other_sections: dict[str, str] = field(default_factory=dict)

    def instructions_for(self, step_name: str) -> str | None:
        """Inline instructions for a step, including a frozen step whose
        name the current definition no longer declares."""
        if any(step.name == step_name for step in self.steps):
            return self.inline_instructions.get(step_name)
        return self.other_sections.get(step_name)

    # --- io --------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "Workflow":
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise WorkflowError(f"Cannot read workflow {path}: not a regular file")
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            if path.is_symlink():
                raise WorkflowError(f"Cannot read workflow {path}: {exc}") from exc
            raise WorkflowNotFoundError(f"Workflow not found: {path}") from exc
        except (OSError, UnicodeError) as exc:
            raise WorkflowError(f"Cannot read workflow {path}: {exc}") from exc
        match = _FM_RE.match(text)
        if not match:
            raise WorkflowError(f"{path} must begin with YAML frontmatter")
        fm_text, body = match.group(1), match.group(2)
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise WorkflowError(f"{path}: invalid YAML frontmatter: {exc}") from exc
        if not isinstance(fm, dict):
            raise WorkflowError(f"{path}: YAML frontmatter must be a mapping")
        if "name" not in fm:
            raise WorkflowError(f"{path}: missing `name` in frontmatter")
        if not isinstance(fm["name"], str) or not fm["name"].strip():
            raise WorkflowError(f"{path}: `name` must be a non-empty string")
        if "steps" not in fm or not isinstance(fm["steps"], list) or not fm["steps"]:
            raise WorkflowError(f"{path}: `steps` must be a non-empty list")

        git = fm.get("git", DEFAULT_GIT_MODE)
        if not isinstance(git, str) or git not in GIT_MODES:
            raise WorkflowError(
                f"{path}: `git` {git!r} must be one of {sorted(GIT_MODES)}"
            )

        steps = [_parse_step(s, path) for s in fm["steps"]]
        step_names = {s.name for s in steps}
        inline = _parse_inline_sections(body, step_names)
        other = {
            section.heading: body[section.content_start:section.end].strip()
            for section in body_sections(body)
            if section.heading not in step_names
        }

        return cls(
            name=fm["name"],
            description=fm.get("description", ""),
            steps=steps,
            git=git,
            body=body,
            inline_instructions=inline,
            other_sections=other,
        )

    # --- freezing --------------------------------------------------------------

    def freeze(self) -> dict[str, Any]:
        """Snapshot suitable for ticket frontmatter."""
        out: dict[str, Any] = {
            "name": self.name,
        }
        if self.git != DEFAULT_GIT_MODE:
            out["git"] = self.git
        out["steps"] = []
        for step in self.steps:
            entry: dict[str, Any] = {"name": step.name, "skills": list(step.skills)}
            if step.assignee:
                entry["assignee"] = step.assignee
            if step.requires:
                entry["requires"] = step.requires
            if step.run is not None:
                entry["run"] = step.run
            out["steps"].append(entry)
        return out


def git_mode(workflow: Any, cfg: Any) -> str:
    """The launch Git mode a ticket's `workflow:` selects.

    A frozen mapping carries its own `git:` (absent means `main`). A draft's
    string reference loads the definition it would freeze, as
    `launch_script.script_entry_point` does for a draft's first step. A
    missing workflow is `main`. An unknown frozen value raises
    `WorkflowError`; `coga validate` reports it as `bad-shape`.
    """
    if isinstance(workflow, str):
        from coga.paths import resolve_workflow_path

        return Workflow.load(resolve_workflow_path(cfg, workflow)).git
    if not isinstance(workflow, dict):
        return DEFAULT_GIT_MODE
    mode = workflow.get("git", DEFAULT_GIT_MODE)
    if not isinstance(mode, str) or mode not in GIT_MODES:
        raise WorkflowError(
            f"frozen workflow `git` {mode!r} must be one of {sorted(GIT_MODES)}"
        )
    return mode


# --- helpers ------------------------------------------------------------------


def _parse_step(raw: Any, source: Path) -> WorkflowStep:
    if not isinstance(raw, dict) or "name" not in raw:
        raise WorkflowError(
            f"{source}: step must be a mapping with a `name` field, got {raw!r}"
        )
    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise WorkflowError(f"{source}: step `name` must be a non-empty string")
    if "skill" in raw:
        raise WorkflowError(
            f"{source}: step {name!r} uses legacy singular `skill:` — "
            f"rewrite as `skills: [<ref>]` (a list)."
        )
    skills_raw = raw.get("skills", [])
    if not isinstance(skills_raw, list):
        raise WorkflowError(
            f"{source}: step {name!r} `skills:` must be a list, got {skills_raw!r}"
        )
    for s in skills_raw:
        if not isinstance(s, str) or not s:
            raise WorkflowError(
                f"{source}: step {name!r} `skills` entry must be a non-empty string, got {s!r}"
            )
    assignee = raw.get("assignee")
    if assignee is not None and (
        not isinstance(assignee, str) or assignee not in VALID_ASSIGNEE_ROLES
    ):
        hint = (
            " — `human` was renamed to `owner`"
            if assignee == "human"
            else " (role token only — literal nicknames not allowed)"
        )
        raise WorkflowError(
            f"{source}: step {name!r} assignee {assignee!r} must be one of "
            f"{sorted(VALID_ASSIGNEE_ROLES)}{hint}"
        )
    requires = raw.get("requires")
    if requires is not None:
        # Imported lazily to avoid a module-load cycle (step_gate -> autoclose).
        from coga.step_gate import known_gate_tokens

        if not isinstance(requires, str) or requires not in known_gate_tokens():
            raise WorkflowError(
                f"{source}: step {name!r} requires {requires!r} must be one of "
                f"{sorted(known_gate_tokens())} (a registered completion gate)"
            )
    run = raw.get("run")
    if run is not None and (not isinstance(run, str) or not run.strip()):
        raise WorkflowError(f"{source}: step {name!r} run must be a skill ref")
    return WorkflowStep(
        name=name,
        skills=tuple(skills_raw),
        assignee=assignee,
        requires=requires,
        run=run,
    )


def _parse_inline_sections(body: str, step_names: set[str]) -> dict[str, str]:
    """Split the markdown body by `## <heading>` into sections keyed by heading text.

    Only returns sections whose heading matches a step name. Use the shared
    section parser so fenced example headings cannot split or create steps.
    """
    return {
        section.heading: body[section.content_start:section.end].strip()
        for section in body_sections(body)
        if section.heading in step_names
    }


__all__ = [
    "Workflow", "WorkflowStep", "WorkflowError", "WorkflowNotFoundError",
    "VALID_ASSIGNEE_ROLES", "GIT_MODES", "DEFAULT_GIT_MODE", "git_mode",
]
