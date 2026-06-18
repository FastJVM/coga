"""Deterministic repo validation — the engine behind the dream/drift skill.

Exposed as `relay validate` (see `relay.commands.validate`); also runnable
directly as a module:

    relay validate [--json] [--task <slug>] [--fix] [--max-blackboard-kb N] [--check-slack] [--check-github]
    python -m relay.validate [--json] [--task <slug>] [--fix] [--max-blackboard-kb N] [--check-slack] [--check-github]

Two entry points:
- `run(cfg, ...)` — whole-repo sweep (every task under `relay-os/tasks/`).
- `validate_task(cfg, slug, ...)` — single task. Used by the `--task` flag
  and by every Relay-owned command that mutates a task file.

Per-task primitives:
- `validate_task_dir(cfg, ref)` — file presence + frontmatter schema check.
- `validate_ticket_frontmatter(cfg, task_label, ticket)` — schema only.

Checks (whole-repo):
- Task dirs have ticket.md, blackboard.md, log.md.
- ticket.md parses as YAML frontmatter + body.
- Frontmatter has the canonical key set with the right shapes.
- contexts / skills / workflow step skills resolve to real files.
- step is consistent with workflow shape and status.
- Blackboard files are not large enough to bloat composed prompts.
- Tasks stuck in `in_progress` with no recent log activity.
- Assignees referenced in tickets exist in relay.toml.
- (Opt-in) Slack webhook reachability via an empty-text probe.
- (Opt-in) Git/GitHub auth readiness via `git`/`gh` preflight probes.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

from relay.blackboard import BLACKBOARD_WARN_BYTES, blackboard_size_warning, render_blackboard
from relay.config import Config, ConfigError, load_config
from relay.period_state import read_snapshot, stale_keys
from relay.paths import (
    context_resolution_paths,
    resolve_context_path,
    resolve_skill_path,
    skill_resolution_paths,
)
from relay.slack_response import classify_slack_response
from relay.tasks import (
    DuplicateTaskSlugError,
    TaskNotFoundError,
    TaskRef,
    list_tasks,
    resolve_task,
)
from relay.ticket import Ticket, TicketError
from relay.workflow import VALID_ASSIGNEE_ROLES

VALID_STATUSES = {"draft", "active", "in_progress", "paused", "done"}
VALID_MODES = {"interactive", "auto", "script"}

# Canonical ticket frontmatter schema.
REQUIRED_TASK_KEYS: tuple[str, ...] = (
    "title",
    "status",
    "mode",
    "owner",
    "human",
    "agent",
    "assignee",
    "contexts",
    "skills",
    "workflow",
)
# Optional keys that may appear in addition to the required set.
OPTIONAL_TASK_KEYS: frozenset[str] = frozenset({"step", "watchers", "secrets"})
_NON_EMPTY_STRING_KEYS: tuple[str, ...] = (
    "title",
    "owner",
    "human",
    "agent",
    "assignee",
)


@dataclass
class Issue:
    kind: str            # "missing-file", "broken-ref", ...
    task: str            # "id-slug"
    message: str
    severity: str = "warn"  # "warn" | "error"


@dataclass
class Fix:
    kind: str
    task: str
    message: str
    path: str


@dataclass
class Report:
    generated_at: str
    issues: list[Issue] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    ok_count: int = 0


# --- engine -------------------------------------------------------------------


def _duplicate_slug_issue(exc: DuplicateTaskSlugError) -> Issue:
    """Render a discovery-breaking slug collision as a report issue.

    Discovery raises on duplicate leaf names (every command needs unambiguous
    bare-slug resolution); validate is the one consumer that catches the error
    so it can report the colliding paths legibly instead of crashing.
    """
    paths = ", ".join(str(p) for p in exc.paths)
    return Issue(
        kind="duplicate-slug",
        task=exc.slug,
        message=f"duplicate task slug across {paths} — rename one directory",
        severity="error",
    )


def run(
    cfg: Config,
    idle_hours: float = 72.0,
    max_blackboard_bytes: int = BLACKBOARD_WARN_BYTES,
    check_slack: bool = False,
    check_github: bool = False,
    fix: bool = False,
) -> Report:
    report = Report(generated_at=_now_iso())
    try:
        refs = list_tasks(cfg)
    except DuplicateTaskSlugError as exc:
        report.issues.append(_duplicate_slug_issue(exc))
        return report

    if fix:
        report.fixes.extend(apply_safe_fixes(cfg, only=refs))

    if check_slack:
        report.issues.extend(_notification_issues(cfg))

    if check_github:
        report.issues.extend(_github_issues(cfg))

    valid_assignees = _valid_assignee_set(cfg)
    now = datetime.now(timezone.utc)

    for ref in refs:
        report.issues.extend(
            _check_one_task(
                cfg,
                ref,
                valid_assignees=valid_assignees,
                max_blackboard_bytes=max_blackboard_bytes,
                idle_hours=idle_hours,
                now=now,
            )
        )

    report.ok_count = _ok_count(refs, report.issues)
    return report


def validate_task(
    cfg: Config,
    slug: str,
    *,
    fix: bool = False,
    max_blackboard_bytes: int = BLACKBOARD_WARN_BYTES,
    idle_hours: float = 72.0,
) -> Report:
    """Validate exactly one task directory. Used by `relay validate --task`
    and by every Relay-owned command that mutates a task file."""
    report = Report(generated_at=_now_iso())
    try:
        ref = resolve_task(cfg, slug)
    except DuplicateTaskSlugError as exc:
        report.issues.append(_duplicate_slug_issue(exc))
        return report
    except TaskNotFoundError as exc:
        report.issues.append(Issue(
            kind="unknown-task",
            task=slug,
            message=str(exc),
            severity="error",
        ))
        return report

    if fix:
        report.fixes.extend(apply_safe_fixes(cfg, only=[ref]))

    valid_assignees = _valid_assignee_set(cfg)
    report.issues.extend(
        _check_one_task(
            cfg,
            ref,
            valid_assignees=valid_assignees,
            max_blackboard_bytes=max_blackboard_bytes,
            idle_hours=idle_hours,
            now=datetime.now(timezone.utc),
        )
    )
    report.ok_count = _ok_count([ref], report.issues)
    return report


def validate_task_dir(cfg: Config, ref: TaskRef) -> list[Issue]:
    """File-presence + frontmatter schema check for one task directory.

    Skips the idle-time `stuck-in-progress` heuristic — that's a sweep-only
    signal, not something to gate every edit on.
    """
    return _check_one_task(
        cfg,
        ref,
        valid_assignees=_valid_assignee_set(cfg),
        max_blackboard_bytes=BLACKBOARD_WARN_BYTES,
        idle_hours=float("inf"),
        now=datetime.now(timezone.utc),
    )


def validate_ticket_frontmatter(
    cfg: Config, task_label: str, ticket: Ticket
) -> list[Issue]:
    """Strict canonical-schema check for one ticket's frontmatter only."""
    return list(_check_frontmatter_schema(cfg, task_label, ticket))


def format_task_issues(issues: Iterable[Issue]) -> str:
    """Render issues for stderr / exception messages."""
    return "\n".join(
        f"[{i.severity.upper()}] {i.task}: {i.kind} — {i.message}" for i in issues
    )


class TaskValidationError(RuntimeError):
    """Raised by `assert_task_valid` when a post-edit check finds errors."""

    def __init__(self, issues: list[Issue], *, action: str):
        self.issues = issues
        self.action = action
        super().__init__(
            f"task validation failed after {action}:\n{format_task_issues(issues)}"
        )


def assert_task_valid(cfg: Config, ref: TaskRef, *, action: str) -> None:
    """Re-validate a task after an edit. Raise TaskValidationError on errors.

    Called by every Relay-owned command that mutates a task file, so a bad
    write is surfaced at the edge of the edit instead of later at launch /
    Dream time. Warnings are not fatal.
    """
    issues = validate_task_dir(cfg, ref)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise TaskValidationError(errors, action=action)


# --- per-task checks ----------------------------------------------------------


def _check_one_task(
    cfg: Config,
    ref: TaskRef,
    *,
    valid_assignees: set[str],
    max_blackboard_bytes: int,
    idle_hours: float,
    now: datetime,
) -> list[Issue]:
    out: list[Issue] = []
    task_label = ref.id_slug

    # Required files
    for fname in ("ticket.md", "blackboard.md", "log.md"):
        if not (ref.path / fname).is_file():
            out.append(Issue(
                kind="missing-file",
                task=task_label,
                message=f"missing {fname}",
                severity="error",
            ))

    warning = blackboard_size_warning(
        ref.path / "blackboard.md",
        max_bytes=max_blackboard_bytes,
    )
    if warning:
        out.append(Issue(
            kind="large-blackboard",
            task=task_label,
            message=warning,
            severity="warn",
        ))

    if not (ref.path / "ticket.md").is_file():
        return out

    try:
        ticket = Ticket.read(ref.path / "ticket.md")
    except TicketError as exc:
        out.append(Issue(
            kind="bad-frontmatter",
            task=task_label,
            message=str(exc),
            severity="error",
        ))
        return out

    out.extend(_check_frontmatter_schema(cfg, task_label, ticket))
    out.extend(_check_secrets(cfg, task_label, ticket))

    # Valid assignees: known agent types OR one of this ticket's role-field
    # values (owner / human / agent). The role rotation puts whichever of
    # those is current into `assignee:`.
    role_values = {
        v for v in (ticket.owner, ticket.frontmatter.get("human"), ticket.frontmatter.get("agent"))
        if isinstance(v, str) and v
    }
    if ticket.assignee and ticket.assignee not in valid_assignees and ticket.assignee not in role_values:
        out.append(Issue(
            kind="unknown-assignee",
            task=task_label,
            message=f"assignee {ticket.assignee!r} is neither a known agent type nor one of this ticket's role-field values",
            severity="warn",
        ))

    out.extend(_check_refs(cfg, task_label, ticket))
    out.extend(_check_workflow_shape(task_label, ticket))

    if idle_hours != float("inf") and ticket.status == "in_progress":
        log_path = ref.path / "log.md"
        if log_path.is_file():
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=timezone.utc)
            idle = now - mtime
            if idle > timedelta(hours=idle_hours):
                out.append(Issue(
                    kind="stuck-in-progress",
                    task=task_label,
                    message=f"in_progress but idle for {idle.total_seconds() / 3600:.1f}h",
                    severity="warn",
                ))

    # A `done` period task whose declared state keys still match their
    # create-time snapshot finished without advancing its cursor — the next
    # firing will redo the same range. Surface it here so a stuck cursor is
    # visible without waiting for that duplicate run. Only `done` tasks qualify:
    # an unfinished run legitimately hasn't recorded state yet.
    if ticket.status == "done":
        snapshot = read_snapshot(ref.path)
        if snapshot is not None:
            stale = stale_keys(cfg, snapshot)
            if stale:
                out.append(Issue(
                    kind="recurring-state-stuck",
                    task=task_label,
                    message=(
                        f"finished without advancing declared state key(s) "
                        f"{', '.join(stale)} in {snapshot.parent}'s blackboard"
                    ),
                    severity="warn",
                ))

    return out


def _check_frontmatter_schema(
    cfg: Config, task_label: str, ticket: Ticket
) -> list[Issue]:
    out: list[Issue] = []
    fm = ticket.frontmatter

    for key in REQUIRED_TASK_KEYS:
        if key not in fm:
            out.append(Issue(
                kind="missing-key",
                task=task_label,
                message=f"frontmatter missing required key {key!r}",
                severity="error",
            ))

    extension_keys = set(cfg.ticket_fields)
    extra = (
        set(fm) - set(REQUIRED_TASK_KEYS) - OPTIONAL_TASK_KEYS - extension_keys
    )
    for key in sorted(extra):
        out.append(Issue(
            kind="orphan-extension",
            task=task_label,
            message=(
                f"frontmatter key {key!r} is not in the canonical schema and "
                "is not declared in `[ticket.fields]` — likely orphaned by a "
                "removed declaration; delete it from this ticket or restore "
                "the `[ticket.fields]` entry"
            ),
            severity="warn",
        ))

    for field_name, spec in cfg.ticket_fields.items():
        if field_name not in fm:
            out.append(Issue(
                kind="missing-extension",
                task=task_label,
                message=(
                    f"frontmatter missing extension field {field_name!r} "
                    f"declared in `[ticket.fields.{field_name}]`"
                ),
                severity="error",
            ))
            continue
        value = fm[field_name]
        if not isinstance(value, str):
            out.append(Issue(
                kind="bad-shape",
                task=task_label,
                message=(
                    f"extension field {field_name!r} must be a string, "
                    f"got {value!r}"
                ),
                severity="error",
            ))
            continue
        # Empty values are allowed at validate time (draft tickets carry
        # them until the human or `bootstrap/ticket` fills them in). Enum
        # constraints only apply to non-empty values; `relay mark active`
        # enforces required-non-empty.
        if spec.values is not None and value != "" and value not in spec.values:
            out.append(Issue(
                kind="bad-extension-value",
                task=task_label,
                message=(
                    f"extension field {field_name!r} value {value!r} is not "
                    f"in declared values {list(spec.values)}"
                ),
                severity="error",
            ))

    for key in _NON_EMPTY_STRING_KEYS:
        if key in fm:
            value = fm[key]
            if not isinstance(value, str) or not value.strip():
                out.append(Issue(
                    kind="bad-shape",
                    task=task_label,
                    message=f"{key!r} must be a non-empty string, got {value!r}",
                    severity="error",
                ))

    if "status" in fm:
        status = fm["status"]
        if not isinstance(status, str) or status not in VALID_STATUSES:
            out.append(Issue(
                kind="invalid-status",
                task=task_label,
                message=f"status {status!r} not in {sorted(VALID_STATUSES)}",
                severity="error",
            ))

    if "mode" in fm:
        mode = fm["mode"]
        if not isinstance(mode, str) or mode not in VALID_MODES:
            out.append(Issue(
                kind="invalid-mode",
                task=task_label,
                message=f"mode {mode!r} not in {sorted(VALID_MODES)}",
                severity="error",
            ))

    if "contexts" in fm and not _is_string_list(fm["contexts"]):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=f"contexts must be a list of strings, got {fm['contexts']!r}",
            severity="error",
        ))

    if "skills" in fm and not _is_string_list(fm["skills"]):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=f"skills must be a list of strings, got {fm['skills']!r}",
            severity="error",
        ))

    if "workflow" in fm:
        wf = fm["workflow"]
        if wf is not None and not isinstance(wf, (dict, str)):
            out.append(Issue(
                kind="bad-shape",
                task=task_label,
                message=(
                    "workflow must be `null`, a workflow-name string, or a "
                    f"frozen mapping with `name` and `steps`, got {wf!r}"
                ),
                severity="error",
            ))
        elif isinstance(wf, dict):
            if "name" not in wf or not isinstance(wf.get("name"), str):
                out.append(Issue(
                    kind="bad-shape",
                    task=task_label,
                    message="workflow.name missing or not a string",
                    severity="error",
                ))
            steps = wf.get("steps")
            if not isinstance(steps, list) or not steps:
                out.append(Issue(
                    kind="bad-shape",
                    task=task_label,
                    message="workflow.steps must be a non-empty list",
                    severity="error",
                ))
            else:
                for i, step in enumerate(steps, start=1):
                    out.extend(_check_step_shape(task_label, i, step))

    return out


def _check_secrets(cfg: Config, task_label: str, ticket: Ticket) -> list[Issue]:
    """Validate a ticket's `secrets:` declaration.

    Shape is an error (the field is otherwise free-form): `secrets:` must be
    `null` or a list of strings. Env presence is a warning, not an error, since
    which env vars are exported is per-shell: a declared key absent from
    `[secrets]`, or one whose `env:VAR` is unset in this environment, warns so
    a launch-time fail-loud isn't a surprise.

    An `op://` reference is intentionally **not** probed here: validate never
    requires a real 1Password account, so it does no live `op read` (that
    belongs to explicit launch / `relay secret get`). An op secret is neither
    undeclared nor env-unset (`missing` is env-only), so it produces no issue.
    """
    out: list[Issue] = []
    fm = ticket.frontmatter
    if "secrets" not in fm:
        return out
    declared = fm["secrets"]
    if declared is None:
        return out
    if not _is_string_list(declared):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=f"secrets must be `null` or a list of strings, got {declared!r}",
            severity="error",
        ))
        return out
    for key in declared:
        sv = cfg.secrets.get(key)
        if sv is None:
            out.append(Issue(
                kind="undeclared-secret",
                task=task_label,
                message=(
                    f"declares secret {key!r} but it is not defined in "
                    "[secrets] in relay.local.toml"
                ),
                severity="warn",
            ))
        elif sv.missing:
            out.append(Issue(
                kind="unset-secret-env",
                task=task_label,
                message=(
                    f"declared secret {key!r} points at env var "
                    f"{sv.env_var!r}, which is unset in this environment"
                ),
                severity="warn",
            ))
    return out


def _check_step_shape(task_label: str, idx: int, step: Any) -> list[Issue]:
    out: list[Issue] = []
    if not isinstance(step, dict):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=f"workflow step #{idx} must be a mapping, got {step!r}",
            severity="error",
        ))
        return out
    if "skill" in step:
        out.append(Issue(
            kind="legacy-step-skill",
            task=task_label,
            message=(
                f"workflow step #{idx} uses legacy singular `skill:` — "
                "rewrite as `skills: [<ref>]` (list)"
            ),
            severity="error",
        ))
    if not isinstance(step.get("name"), str) or not step["name"].strip():
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=f"workflow step #{idx} missing non-empty `name`",
            severity="error",
        ))
    skills = step.get("skills", [])
    if not _is_string_list(skills):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=(
                f"workflow step #{idx} `skills` must be a list of strings, "
                f"got {skills!r}"
            ),
            severity="error",
        ))
    assignee = step.get("assignee")
    if assignee is not None and assignee not in VALID_ASSIGNEE_ROLES:
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=(
                f"workflow step #{idx} assignee {assignee!r} must be one of "
                f"{sorted(VALID_ASSIGNEE_ROLES)}"
            ),
            severity="error",
        ))
    return out


def _check_refs(cfg: Config, task_label: str, ticket: Ticket) -> list[Issue]:
    out: list[Issue] = []

    if _is_string_list(ticket.frontmatter.get("contexts", [])):
        for ref_name in ticket.contexts:
            if resolve_context_path(cfg, ref_name) is None:
                out.append(Issue(
                    kind="broken-context",
                    task=task_label,
                    message=(
                        f"context {ref_name!r} does not exist "
                        f"(checked: {_format_paths(context_resolution_paths(cfg, ref_name))})"
                    ),
                    severity="error",
                ))

    if _is_string_list(ticket.frontmatter.get("skills", [])):
        for ref_name in ticket.skills:
            if resolve_skill_path(cfg, ref_name) is None:
                out.append(Issue(
                    kind="broken-skill",
                    task=task_label,
                    message=(
                        f"skill {ref_name!r} does not exist "
                        f"(checked: {_format_paths(skill_resolution_paths(cfg, ref_name))})"
                    ),
                    severity="error",
                ))

    wf = ticket.workflow
    if isinstance(wf, dict):
        for step in wf.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            for ref_name in step.get("skills", []) or []:
                if not isinstance(ref_name, str):
                    continue
                if resolve_skill_path(cfg, ref_name) is None:
                    out.append(Issue(
                        kind="broken-skill",
                        task=task_label,
                        message=(
                            f"step {step.get('name', '?')!r} skill {ref_name!r} "
                            f"does not exist "
                            f"(checked: {_format_paths(skill_resolution_paths(cfg, ref_name))})"
                        ),
                        severity="error",
                    ))
    elif isinstance(wf, str):
        out.append(Issue(
            kind="unfrozen-workflow",
            task=task_label,
            message=(
                f"workflow {wf!r} is not a frozen dict — likely a hand-authored "
                "ticket awaiting first launch"
            ),
            severity="warn",
        ))

    return out


def _format_paths(paths: tuple[Path, ...] | tuple[Path, Path]) -> str:
    return ", ".join(str(path) for path in paths)


def _check_workflow_shape(task_label: str, ticket: Ticket) -> list[Issue]:
    out: list[Issue] = []
    wf = ticket.workflow
    step = ticket.step

    if wf is None:
        if step is not None:
            out.append(Issue(
                kind="bad-shape",
                task=task_label,
                message="`step:` set but `workflow:` is null",
                severity="error",
            ))
        # The governing rule: a workflow is mandatory everywhere EXCEPT while a
        # ticket is a `draft`. `draft` is the authoring grace period — a
        # workflow-less draft (concept-capture: stash an idea before its shape
        # settles) is valid and intentional, so it is NOT flagged. Once a
        # ticket is `active`/`in_progress`/`paused`, a missing workflow means it
        # can never be bumped — structurally stuck — so that is an error. (`done`
        # is left alone: a finished workflow-less task is harmless and flagging
        # it would only nag immutable history.) Machine-authored tasks that
        # used to be workflow-less here — recurring/Dream and retire — now
        # create with the `direct/body` workflow, so no whitelist is needed.
        if ticket.status in {"active", "in_progress", "paused"}:
            out.append(Issue(
                kind="active-no-workflow",
                task=task_label,
                message=(
                    f"{ticket.status} ticket has no `workflow:` — it can never "
                    "be advanced (`relay bump` has no step to move). A workflow "
                    "is required once a ticket leaves `draft`. Set "
                    "`workflow: <name>` (e.g. `direct/body` to run the body "
                    "directly) or rewind it to `draft`."
                ),
                severity="error",
            ))
        return out

    if not isinstance(wf, dict):
        return out  # already reported by shape/ref checks

    status = ticket.status
    if status == "done":
        if step is not None:
            out.append(Issue(
                kind="bad-shape",
                task=task_label,
                message="`step:` must be absent when status is `done`",
                severity="error",
            ))
        return out

    if step is None:
        out.append(Issue(
            kind="missing-step",
            task=task_label,
            message="`workflow:` is set but `step:` is missing",
            severity="error",
        ))
        return out

    idx = ticket.step_index()
    steps = wf.get("steps") or []
    if idx is None or not (1 <= idx <= len(steps)):
        out.append(Issue(
            kind="bad-shape",
            task=task_label,
            message=(
                f"step {step!r} does not point at a valid workflow step "
                f"(1..{len(steps)})"
            ),
            severity="error",
        ))
    return out


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _valid_assignee_set(cfg: Config) -> set[str]:
    """Names a ticket's `assignee:` may take.

    The canonical model is that `assignee:` rotates between role-field
    values (`owner` / `human` / `agent`) so anything that names a known
    agent type is valid. Human names aren't enumerated in config — they
    only have to match the ticket's own `owner:` / `human:` fields, which
    is checked elsewhere — so the warn-level "unknown assignee" check
    just verifies agent-typed assignees resolve.
    """
    return set(cfg.agents)


def _ok_count(refs: list[TaskRef], issues: list[Issue]) -> int:
    synthetic = {"(slack)", "(github)"}
    bad = {i.task for i in issues if i.severity == "error" and i.task not in synthetic}
    return len(refs) - len(bad)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _notification_issues(cfg: Config) -> list[Issue]:
    issues = [
        Issue(
            kind="notification-deprecated-config",
            task="(notification)",
            message=note,
            severity="warn",
        )
        for note in cfg.notification_deprecation_notes
    ]
    if "slack" not in cfg.notification_channels:
        return issues
    if not cfg.slack_enabled:
        return issues
    if not cfg.slack_webhook:
        issues.append(
            Issue(
                kind="slack-misconfigured",
                task="(slack)",
                message=(
                    "no Slack webhook configured — set "
                    "[notification.slack].webhook (Relay requires it unless "
                    "[notification.slack].enabled = false)"
                ),
                severity="error",
            )
        )
        return issues
    status, detail = probe_slack(cfg.slack_webhook)
    if status == "live":
        return issues
    if status == "revoked":
        issues.append(
            Issue(
                kind="slack-revoked",
                task="(slack)",
                message=f"webhook URL not recognized by Slack: {detail}",
                severity="error",
            )
        )
        return issues
    issues.append(
        Issue(
            kind="slack-unreachable",
            task="(slack)",
            message=f"could not reach Slack: {detail}",
            severity="error",
        )
    )
    return issues


def _github_issues(cfg: Config) -> list[Issue]:
    """Map the git/GitHub preflight probes into report issues.

    Opt-in only (gated by `--check-github`): this is the single call site that
    shells out to `git`/`gh`, so the default read-only validate path never hits
    the network. Every failed probe is an `error` — the operator explicitly
    asked "is my setup ready?", and a clear no (with an actionable hint and a
    non-zero exit) is the useful answer, including when the machine is offline.
    """
    from relay.github_preflight import run_preflight

    issues: list[Issue] = []
    for result in run_preflight(cfg.git_remote):
        if not result.ok:
            issues.append(
                Issue(
                    kind=f"github-{result.name}",
                    task="(github)",
                    message=result.detail,
                    severity="error",
                )
            )
    return issues


def apply_safe_fixes(cfg: Config, only: list[TaskRef] | None = None) -> list[Fix]:
    """Apply deterministic repairs that do not change task state.

    Current safe set:
      - create missing `blackboard.md` from the default template
      - create missing `log.md` as an empty append-only file

    Existing files are never rewritten, and `ticket.md` is never
    reconstructed from inference.
    """
    fixes: list[Fix] = []
    targets = list(only) if only is not None else list_tasks(cfg)
    for ref in targets:
        blackboard_path = ref.path / "blackboard.md"
        if not blackboard_path.is_file():
            title = ref.id_slug
            try:
                title = Ticket.read(ref.path / "ticket.md").title or ref.id_slug
            except (TicketError, FileNotFoundError):
                pass
            blackboard_path.write_text(render_blackboard(title))
            fixes.append(
                Fix(
                    kind="missing-file",
                    task=ref.id_slug,
                    message="created blackboard.md",
                    path=str(blackboard_path),
                )
            )

        log_path = ref.path / "log.md"
        if not log_path.is_file():
            log_path.write_text("")
            fixes.append(
                Fix(
                    kind="missing-file",
                    task=ref.id_slug,
                    message="created log.md",
                    path=str(log_path),
                )
            )

    return fixes


# --- slack probe -------------------------------------------------------------


def probe_slack(webhook_url: str) -> tuple[str, str]:
    """POST an empty-text payload to a Slack webhook and classify the response.

    Returns (status, detail) where status is one of:
      "live"        — Slack received the request (any 2xx/4xx that isn't a 404
                      or a `no_service` body)
      "revoked"     — webhook URL not recognized (HTTP 404 or `no_service`)
      "unreachable" — network-level failure or 5xx

    Slack's incoming-webhook wire format isn't pinned by contract; the
    implementation matches by `in` rather than equality so minor body changes
    don't break things.
    """
    try:
        resp = requests.post(webhook_url, json={"text": ""}, timeout=5)
    except requests.RequestException as exc:
        return "unreachable", f"{type(exc).__name__}: {exc}"

    return classify_slack_response(resp.status_code, resp.text)


# --- CLI entry ----------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relay repo validator")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Validate exactly one task slug.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply conservative safe repairs before reporting.",
    )
    parser.add_argument("--idle-hours", type=float, default=72.0)
    parser.add_argument(
        "--max-blackboard-kb",
        type=float,
        default=BLACKBOARD_WARN_BYTES / 1024,
        help="Blackboard size above which to warn about prompt bloat.",
    )
    parser.add_argument(
        "--check-slack",
        action="store_true",
        help="Also probe the Slack webhook with an empty-text payload (network call).",
    )
    parser.add_argument(
        "--check-github",
        action="store_true",
        help="Also probe git/GitHub auth readiness via git/gh (network call).",
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    if args.task is not None:
        if args.check_slack:
            sys.stderr.write("--check-slack is not supported with --task\n")
            return 2
        if args.check_github:
            sys.stderr.write("--check-github is not supported with --task\n")
            return 2
        report = validate_task(
            cfg,
            args.task,
            fix=args.fix,
            max_blackboard_bytes=int(args.max_blackboard_kb * 1024),
            idle_hours=args.idle_hours,
        )
    else:
        report = run(
            cfg,
            idle_hours=args.idle_hours,
            max_blackboard_bytes=int(args.max_blackboard_kb * 1024),
            check_slack=args.check_slack,
            check_github=args.check_github,
            fix=args.fix,
        )

    if args.json:
        payload: dict[str, Any] = {
            "generated_at": report.generated_at,
            "ok_count": report.ok_count,
            "fixes": [asdict(f) for f in report.fixes],
            "issues": [asdict(i) for i in report.issues],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not report.issues:
            for fix_item in report.fixes:
                print(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            print(f"All good ({report.ok_count} tasks checked).")
        else:
            for fix_item in report.fixes:
                print(f"[FIX] {fix_item.task}: {fix_item.kind} — {fix_item.message}")
            for issue in report.issues:
                sev = issue.severity.upper()
                print(f"[{sev}] {issue.task}: {issue.kind} — {issue.message}")

    # Exit code: 0 if no errors, 1 if errors, 2 on tool failure.
    return 1 if any(i.severity == "error" for i in report.issues) else 0


if __name__ == "__main__":
    sys.exit(_main())
