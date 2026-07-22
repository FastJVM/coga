"""Task directory creating — write a fresh ticket directory to disk."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from coga.blackboard import render_blackboard
from coga.bump import AssigneeResolutionError, resolve_other_agent
from coga.config import Config
from coga.lifecycle import TERMINAL_STATUSES
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
    assignee: str | None,
    watchers: list[str],
    status: str | None,
    human: str | None = None,
    agent: str | None = None,
    skills: list[str] | None = None,
    slug_override: str | None = None,
    directory: str | None = None,
    description: str | None = None,
    body: str | None = None,
    secrets: Any = None,
    script: Any = None,
    force_directory: bool = False,
    created_by: str = "human",
) -> dict[str, Any]:
    """Create a task directory. Returns dict with {slug, path}.

    Pass `description` for the common case — the body is built as the canonical
    `## Description` / `## Context` skeleton. Pass `body` instead to write a
    full ticket body verbatim (recurring creating does this so template
    sections like `## Script config` survive); a `## Context` section is
    appended when the verbatim body lacks one. `body` takes precedence over
    `description`.

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
    human = human or owner
    agent = agent or _default_agent_for(cfg, assignee)
    if not agent:
        raise ValueError(
            "No default agent configured; declare at least one `[agents.*]` "
            "table in coga.toml (e.g. `[agents.claude]`)."
        )

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

    # Initial assignee: if step 1 declares a role, resolve against the
    # ticket's role fields (or, for `other-agent`, the peer agent from
    # config). Otherwise honor the explicit `assignee` arg or fall back to
    # the owner.
    role_fields = {"owner": owner, "human": human, "agent": agent}
    if wf and wf.steps[0].assignee:
        role = wf.steps[0].assignee
        if role == "other-agent":
            try:
                assignee = resolve_other_agent(cfg, agent)
            except AssigneeResolutionError as exc:
                raise ValueError(
                    f"Workflow {workflow_name!r} step 1 assignee='other-agent': {exc}"
                ) from exc
        else:
            resolved = role_fields.get(role)
            if not resolved:
                raise ValueError(
                    f"Workflow {workflow_name!r} step 1 assignee={role!r} but no `{role}` "
                    f"set on the new ticket."
                )
            assignee = resolved
    else:
        assignee = assignee or owner

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

    # A task is a single `tasks/<slug>.md` file unless it needs a companion
    # directory: a deferred `script: <file>` sibling, or a caller that keeps
    # siblings (recurring period tasks carry a `.state-snapshot.json`). An
    # inline script lives in the body, so it stays file-form.
    needs_dir = force_directory or (
        isinstance(script, str) and bool(script) and script != "inline"
    )
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

    # The TaskRef discovery will report for this new task — its `id_slug` is the
    # canonical task reference, recorded on the ticket as `slug:` so the file is
    # self-describing. A sub-directory create qualifies the slug with it.
    qualified_slug = slug if directory is None else f"{directory}/{slug}"
    created_ref = _task_ref_for_created(qualified_slug, result_path, file_form=file_form)

    # Canonical frontmatter order. Every key is always present so tasks have
    # a single legible shape on disk, even when contexts / skills / workflow
    # are empty.
    fm: dict[str, Any] = {
        "slug": created_ref.id_slug,
        "title": title,
        "status": status,
        "owner": owner,
        "human": human,
        "agent": agent,
        "assignee": assignee,
        "contexts": list(contexts),
        "skills": list(skills),
        "workflow": wf.freeze() if wf else None,
        "secrets": secrets,
        "script": script,
    }
    if wf and status not in TERMINAL_STATUSES:
        first_step = wf.steps[0].name
        fm["step"] = f"1 ({first_step})"
    if watchers:
        fm["watchers"] = list(watchers)

    # Repo-declared extension fields (`[ticket.fields.<name>]`). Seeded
    # with the declared default (or "" if none). Required-but-empty is fine
    # at draft time; `coga mark active` enforces required values at
    # activation time.
    for field_name, spec in cfg.ticket_fields.items():
        fm[field_name] = spec.default

    if body is not None:
        # Recurring creating passes the template body verbatim so sections
        # beyond `## Description` survive into the period task — notably
        # `## Script config`, which configures a script step's run. Ensure
        # the canonical `## Context` section exists so the body shape stays
        # uniform and compose can read inline task context. A template body may
        # itself carry a blackboard fence + region; strip it so the period task
        # starts from a fresh blackboard (the template's working state stays on
        # the template, not copied into each run).
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
    Ticket(frontmatter=fm, body=full_body).write(ticket_path)

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


def _default_agent_for(cfg: Config, assignee: str | None) -> str | None:
    """Best-effort default for the new ticket's `agent:` field.

    If the explicit `assignee` arg names a known agent type, use it. Else
    use the first-declared agent type in `[agents]`. TOML preserves
    declaration order, so the team's default agent is whichever block
    appears first.

    Returns None when no agent types are declared; the caller rejects that
    before writing invalid canonical frontmatter.
    """
    if assignee and assignee in cfg.agents:
        return assignee
    default = cfg.default_agent()
    return default.name if default else None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


__all__ = ["create_task"]
