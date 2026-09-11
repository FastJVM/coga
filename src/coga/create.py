"""Task directory creating — write a fresh ticket directory to disk."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from coga import git
from coga.blackboard import render_blackboard
from coga.bump import OperatorResolutionError, resolve_main_agent, resolve_operator
from coga.config import Config
from coga.lifecycle import MAIN_AGENT_REQUIRED_STATUSES, TERMINAL_STATUSES
from coga.logfile import append_log
from coga.paths import (
    missing_skill_message,
    resolve_context_path,
    resolve_skill_path,
    resolve_workflow_path,
    tasks_dir,
)
from coga.slugify import slugify
from coga.taskfile import join_task_body, split_body
from coga.tasks import TaskRef, list_tasks
from coga.ticket import Ticket
from coga.workflow import Workflow

# Shape of one `tasks/` sub-directory path component: slug-like, the kind of
# name you'd `mkdir`. Anything else — spaces, parentheses, other punctuation —
# is almost certainly a title containing a literal '/' that the `coga create`
# positional split misread as a directory prefix.
_DIR_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def create_task(
    *,
    cfg: Config,
    title: str,
    workflow_name: str | None,
    contexts: list[str],
    owner: str | None,
    status: str | None,
    agent: str | None = None,
    skills: list[str] | None = None,
    delegate: str | None = None,
    period_generation: str | None = None,
    slug_override: str | None = None,
    directory: str | None = None,
    description: str | None = None,
    body: str | None = None,
    secrets: Any = None,
    force_directory: bool = False,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {slug, path}.

    Pass `description` for the common case — the body is built as the canonical
    `## Description` / `## Context` skeleton. Pass `body` instead to write a
    full ticket body verbatim (recurring creating does this so template
    sections beyond `## Description` survive); a `## Context` section is
    appended when the verbatim body lacks one. `body` takes precedence over
    `description`.

    `agent` is the optional main-agent choice, not the current operator: who
    holds the task is derived from its frozen workflow step (see
    `coga.bump.resolve_operator`). An explicit choice is validated against
    `[agents.*]` and kept. Left absent, it stays absent on a draft and is filled
    in with the configured default when a caller creates straight into a live
    status — the same selection `coga mark active` performs, so a task that is
    already routable always names the agent it routes to.

    `directory` lands the task in a sub-directory under `tasks/` (`v2`,
    `marketing/social`); the default (None) is the top level. The sub-directory
    is created if missing, and slug uniqueness becomes per-directory — a leaf
    may repeat across directories. (`slug_override` carrying its own path, as
    the recurring creator passes, is the orthogonal way to land a fixed nested
    slug.)
    """
    from coga.validate import assert_task_valid

    owner = owner or cfg.current_user
    status = status or cfg.default_status
    try:
        agent = _select_main_agent(cfg, agent, status=status)
    except OperatorResolutionError as exc:
        raise ValueError(str(exc)) from exc

    contexts = _dedupe(contexts)
    missing_ctx = [c for c in contexts if resolve_context_path(cfg, c) is None]
    if missing_ctx:
        raise ValueError(f"Unknown contexts: {missing_ctx}")

    skills = _dedupe(list(skills or []))
    missing_skills_top = [s for s in skills if resolve_skill_path(cfg, s) is None]
    if missing_skills_top:
        raise ValueError(f"Unknown skills: {missing_skills_top}")

    wf: Workflow | None = None
    if workflow_name:
        wf = Workflow.load(resolve_workflow_path(cfg, workflow_name))
        missing_step_skills: list[str] = []
        for s in wf.steps:
            for ref in s.skills:
                if resolve_skill_path(cfg, ref) is None:
                    missing_step_skills.append(ref)
        if missing_step_skills:
            details = "; ".join(
                missing_skill_message(
                    cfg, ref, source=f"Workflow {workflow_name!r}"
                )
                for ref in missing_step_skills
            )
            raise ValueError(details)

    directory = _normalize_create_dir(cfg, directory)
    base_slug = slug_override or slugify(title)
    # Creates land at the top level by default (`tasks/<slug>.md` or
    # `tasks/<slug>/`), or under `tasks/<directory>/` when a sub-directory is
    # given (the `<dir>/<leaf>` positional path). Slug uniqueness is
    # per-directory — a task in a different sub-directory (or the top level)
    # may reuse the leaf, so only clear slugs already living in the SAME
    # directory.
    existing_slugs = {t.slug for t in list_tasks(cfg) if t.directory == directory}
    slug = base_slug
    n = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{n}"
        n += 1

    base_dir = tasks_dir(cfg) if directory is None else tasks_dir(cfg) / directory

    # A task is a single `tasks/<slug>.md` file unless a caller explicitly
    # needs siblings (recurring period tasks carry a `.state-snapshot.json`).
    needs_dir = force_directory
    file_form = not needs_dir
    if needs_dir:
        task_dir = base_dir / slug
        if task_dir.exists():
            raise ValueError(f"Task directory already exists: {task_dir}")
        task_dir.mkdir(parents=True)
        ticket_path = task_dir / "ticket.md"
        result_path = task_dir
    else:
        ticket_path = base_dir / f"{slug}.md"
        if ticket_path.exists() or (base_dir / slug).is_dir():
            raise ValueError(f"Task already exists: {ticket_path}")
        ticket_path.parent.mkdir(parents=True, exist_ok=True)
        result_path = ticket_path

    # The TaskRef discovery will report for this new task. Its `id_slug` is the
    # canonical task reference; the path is the only identity, so nothing is
    # copied into frontmatter to drift from it. A sub-directory create qualifies
    # the slug with it.
    qualified_slug = slug if directory is None else f"{directory}/{slug}"
    created_ref = _task_ref_for_created(qualified_slug, result_path, file_form=file_form)

    # Canonical frontmatter order. Optional declarations are written only when
    # they say something: an empty `contexts`/`skills`/`secrets` list is
    # indistinguishable from an absent one, so the minimal draft is four lines
    # plus its workflow rather than a screen of empty scaffolding.
    fm: dict[str, Any] = {
        "title": title,
        "status": status,
        "owner": owner,
    }
    if agent is not None:
        fm["agent"] = agent
    if contexts:
        fm["contexts"] = list(contexts)
    if skills:
        fm["skills"] = list(skills)
    if delegate is not None:
        fm["delegate"] = delegate
    if period_generation is not None:
        fm["period_generation"] = period_generation
    fm["workflow"] = wf.freeze() if wf else None
    if secrets:
        fm["secrets"] = secrets
    if wf and status not in TERMINAL_STATUSES:
        first_step = wf.steps[0].name
        fm["step"] = f"1 ({first_step})"

    # Fail loud here if step 1's role cannot resolve against this machine's
    # `[agents.*]` — an ambiguous `other-agent` is a config fact the new ticket
    # cannot fix, and deferring it would hand the operator a task that refuses
    # at launch instead. Nothing is persisted: the answer is discarded, and
    # every later read derives it again from the frozen snapshot.
    if wf and status not in TERMINAL_STATUSES:
        try:
            resolve_operator(
                cfg,
                created_ref,
                Ticket(frontmatter=fm, body=""),
                step_index=1,
                allow_prospective_default=True,
            )
        except OperatorResolutionError as exc:
            raise ValueError(
                f"Workflow {workflow_name!r} step 1: {exc}"
            ) from exc

    # Repo-declared extension fields (`[ticket.fields.<name>]`). Seeded
    # with the declared default (or "" if none). Required-but-empty is fine
    # at draft time; `coga mark active` enforces required values at
    # activation time.
    for field_name, spec in cfg.ticket_fields.items():
        fm[field_name] = spec.default

    if body is not None:
        # Recurring creating passes the template body verbatim so sections
        # beyond `## Description` survive into the period task. Ensure the
        # canonical `## Context` section exists so the body shape stays uniform
        # and compose can read inline task context. A template body may itself
        # carry a blackboard fence + region; strip it so the period task starts
        # from a fresh blackboard (the template's working state stays on the
        # template, not copied into each run).
        above, _ = split_body(body, blackboard_required=False)
        ticket_body = above.rstrip() + "\n"
        if not re.search(r"(?m)^##\s+Context\s*$", ticket_body):
            ticket_body += "\n## Context\n\n"
    else:
        desc_body = (description or "").strip()
        ticket_body = f"## Description\n\n{desc_body}\n\n## Context\n\n"
    # One file per task: body + fence + blackboard, no sibling blackboard.md /
    # log.md. The append-only history goes to the repo-global log.
    full_body = join_task_body(ticket_body, render_blackboard(title))
    git.write_ticket_under_barrier(
        cfg,
        Ticket(frontmatter=fm, body=full_body),
        ticket_path,
    )

    actor = f"{created_by}:{cfg.current_user}" if created_by == "human" else created_by
    append_log(cfg, created_ref.id_slug, actor, f"created (status={status})")

    assert_task_valid(cfg, created_ref, action="create")

    return {"slug": created_ref.id_slug, "path": result_path}


def _normalize_create_dir(cfg: Config, directory: str | None) -> str | None:
    """Validate a sub-directory target into a clean relative path under `tasks/`.

    Returns None for the top level (no sub-directory), or a slash-joined
    relative path (`v2`, `marketing/social`). Fails loud (principle 6) on a
    path that would escape `tasks/`, name a discovery-skipped (`_`-prefixed)
    segment, or nest the new task inside an existing task directory — discovery
    never recurses into a task dir, so a task placed there would be
    undiscoverable.
    """
    if directory is None:
        return None
    raw = directory.strip().strip("/")
    if not raw:
        return None
    parts = raw.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise ValueError(
                f"Invalid sub-directory {directory!r}: path components cannot be "
                f"empty, '.', or '..' — the directory must stay under tasks/."
            )
        if part.startswith("_"):
            raise ValueError(
                f"Invalid sub-directory {directory!r}: component '{part}' starts "
                f"with '_', which task discovery treats as a template and skips."
            )
        if not _DIR_SEGMENT_RE.match(part):
            # A prose component ("Populate the base repo context stub (coga")
            # almost always means the *title* contained a literal '/', which
            # `coga create` reads as a sub-directory split — creating a mangled
            # directory tree instead of one ticket. Fail loud with both ways
            # out rather than landing junk on disk.
            raise ValueError(
                f"Invalid sub-directory {directory!r}: component {part!r} is "
                "not slug-like (letters, digits, '.', '-', '_' only — no "
                "spaces or other punctuation). If the title contains a "
                "literal '/', drop the slash and create the task at the top "
                "level (then `mv` it into a directory if needed), or pass a "
                "slug-like directory prefix like 'v2/' or 'marketing/social/'."
            )
    normalized = "/".join(parts)
    probe = tasks_dir(cfg)
    for part in parts:
        probe = probe / part
        if (probe / "ticket.md").is_file():
            rel = probe.relative_to(tasks_dir(cfg)).as_posix()
            raise ValueError(
                f"Cannot create under {normalized!r}: {rel!r} is itself a task "
                f"directory — a task can't live inside another task. Pick a "
                f"plain sub-directory instead."
            )
    return normalized


def _task_ref_for_created(slug: str, path: Path, *, file_form: bool) -> TaskRef:
    """Build the same TaskRef that discovery will report for a new task.

    `path` is the `.md` file for a file-form task, or the task directory for a
    directory-form one.
    """
    head, sep, leaf = slug.rpartition("/")
    if sep and head:
        return TaskRef(slug=leaf, path=path, directory=head, file_form=file_form)
    return TaskRef(slug=slug, path=path, file_form=file_form)


def _select_main_agent(cfg: Config, agent: str | None, *, status: str) -> str | None:
    """The `agent:` value a newly created ticket should carry, or None.

    An explicit choice is validated against `[agents.*]` and kept — including a
    choice that happens to equal today's default, which is a decision, not a
    coincidence. Without one, a draft keeps the field absent and defers the
    decision to activation, while a create straight into a live status performs
    that same selection now: `Config.default_agent()` is the first agent
    declared in the effective merged configuration (TOML preserves declaration
    order), so the team's default is whichever block appears first.

    Raises `OperatorResolutionError` for an unconfigured explicit choice, or
    when a live create finds no agents declared at all.
    """
    if agent is not None:
        return resolve_main_agent(cfg, agent)
    if status not in MAIN_AGENT_REQUIRED_STATUSES:
        return None
    return resolve_main_agent(cfg, None, allow_prospective_default=True)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


__all__ = ["create_task"]
