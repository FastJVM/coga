---
name: coga/tickets
description: The ticket file contract — task discovery and refs, file versus directory form, canonical and extension frontmatter keys, who may write which part, the body regions that compose, and creating, authoring and showing tickets.
---

# Tickets

A ticket is one durable unit of work: YAML frontmatter, a body, the fence
line `<!-- coga:blackboard -->`, then the blackboard region. The blackboard
writer's contract is [coga/blackboard](../blackboard/SKILL.md); status and
step movement are [coga/lifecycle](../lifecycle/SKILL.md).

## Where tasks live and how they are named

`src/coga/tasks.py` `list_tasks` walks `coga/tasks/` at any depth:

- **Directory form**: a directory holding `ticket.md`, plus any attachments.
  A task directory is never recursed into (no task inside a task).
- **File form**: a bare `tasks/<slug>.md`, for a self-contained task with no
  siblings. Promote with `mkdir <slug>/ && mv <slug>.md <slug>/ticket.md`.
- `<slug>.md` and `<slug>/` must not both exist (`DuplicateTaskSlugError`).
- `README.md` is never a task; it documents its directory. Names starting
  with `_` are skipped at every level.
- Other directories are plain folders managed with `mkdir`/`mv`/`rm`; Coga
  has no command for them.

A task's identity is its **path under `tasks/`**: the bare leaf at top level,
otherwise the relative path (`marketing/social/relaunch`). `resolve_task`
accepts an exact ref or a unique prefix; a nested task's bare leaf does not
resolve, and ambiguous prefixes fail listing the matches. Agents use the exact
task directory printed in the composed prompt header rather than rebuilding it
from the ref. Log lines are tagged with the ref and never rewritten, so moving
a task orphans its history under the old tag: record the prior ref in the body
and grep for it.

A directory-form task may reserve the exact sibling `ticket.py` as its
deterministic phase ([coga/script-tickets](../script-tickets/SKILL.md)); no
other attachment changes dispatch. Attachments are never composed.

## Frontmatter

`src/coga/ticket.py` `CANONICAL_TICKET_KEYS` is the reserved set: `title`,
`status`, `owner`, `agent`, `workflow`, `step`, `contexts`, `skills`,
`delegate`, `period_generation`, `launch_generation`, `secrets`.
`validate.REQUIRED_TASK_KEYS` is `title`, `status`, `owner`, `workflow`; a new
draft is exactly those four (`status: draft`, `workflow: null`) plus a body.

- `owner` is the human of record. `agent` is the optional **main-agent
  choice**, not the current operator: absent on drafts, filled once with
  `Config.default_agent()` (first agent in merged config) at first activation,
  then kept through pause, unblock, bump, peer review and terminal moves. A
  present value must name a configured agent; null, blank, unknown or
  since-removed agents fail loud. An activated task missing it is a validation
  error.
- The operator is never stored; it is derived from the frozen step role
  ([coga/workflows](../workflows/SKILL.md)).
- `contexts`, `skills`, `secrets`: absence is empty and an empty list is not
  written. A malformed falsy value (`contexts:` null, `""`, `0`) stays on disk
  so validation names it. `secrets` syntax is owned by
  [coga/secrets](../secrets/SKILL.md).
- `delegate` and `period_generation` are system-written and legal only on a
  materialized task directly under `tasks/recurring/`
  ([coga/recurring](../recurring/SKILL.md)); `launch_generation` is
  megalaunch's claim token ([coga/megalaunch](../megalaunch/SKILL.md)).
- **Removed keys are errors**: `slug`, `human`, `assignee`, `watchers`
  (`REJECTED_TICKET_KEYS`, validate kind `removed-ticket-field`). Every writer
  refuses such a ticket; there is no compatibility reader. Recurring templates
  reject them at load.

**Extensions.** A repo declares fields under `[ticket.fields.<name>]` in
`coga.toml` with only `description` (required), `values` (enum), `default`,
and `required`; strings only, no nesting, no canonical-name collisions
(`config._RESERVED_TICKET_FIELD_NAMES`). `coga create`/`coga ticket` write
each declared field below the `# --- extensions ---` marker, seeded with its
default or `""`. `coga validate` fails on a missing declared field or enum
violation and only warns on an undeclared orphan key. `coga mark active`
refuses empty `required` fields. Extensions reach prompts only as part of the
ticket, not as a separate layer.

**Who writes what.** Agents may edit `contexts` and the body sections, plus
the blackboard; every other frontmatter field belongs to CLI commands and
humans (base prompt `prompt.md`). A specialized authoring skill may grant an
explicit exception. `coga/log.md` is written only by CLI commands.

## Body regions

Only `## Description`, `## Context`, and the live blackboard reach the agent
([coga/prompt-composition](../prompt-composition/SKILL.md)). Any other `##`
section above the fence, such as `## Acceptance Criteria`, is silently dropped
from prompts: put what later steps must read under those two headings or on
the blackboard.

## Creating, authoring, showing

- `coga create "<dir/>Title"` writes a raw `draft` (no Slack, no launch). A
  `/` separates an optional sub-directory prefix (created if missing) from
  the title leaf, which is slugified for the ref and kept verbatim as the
  title. It fails on `..`, a `_`-prefixed segment, nesting inside an existing
  task, or a non-slug-like prefix component (a literal slash in a title).
  `--workflow` is optional in draft ([coga/workflows](../workflows/SKILL.md)).
  `--description` fills `## Description` and rejects a `##` line or an
  own-line fence; blank capture is intended only under `v2/`
  (convention owned by `coga/roadmap` and `coga/tasks/v2/README.md`), and `coga validate` warns
  `empty-description` on non-terminal tickets. `--owner` overrides the local
  `user`; empty fails.
- `coga ticket [title|ref]` runs the guided `bootstrap/ticket` interview on a
  new draft or an existing ticket at any status. It chooses workflow, contexts
  and main agent with the human, repairs an out-of-vocabulary status, and
  validates afterwards: a draft left without a workflow is rejected there.
  `bootstrap/ticket` is injected only into that prompt, never persisted in
  `skills:`; a local `coga/skills/bootstrap/ticket/` overrides it. Standard
  `claude`/`codex` receive the prompt as system/developer context
  (`[agents.<type>].discussion` overrides the argv template).
- `coga show <ref>` renders the ticket and its `coga/log.md` history for
  humans; bootstrap targets show only `ticket.md`. Read files directly for
  scripting.

Installed `coga <cmd> --help` is the syntax authority.

## Ticket relationships

The ticket model carries exactly three relationships — one ticket-to-person
and two ticket-to-ticket — and each has one spelling. Nothing else in a
ticket body is read by a command: a prose `### Blocks` or "supersedes" note is
a pointer for humans, and a reader that trusts it as state will be wrong the
moment it drifts. Each relationship rides an existing writer rather than a
frontmatter key, so there is no `superseded_by`, `dependencies`, or
`assignee` field to keep in sync with the status it would only restate.

- **Ownership: `owner:`, written by `coga owner <slug> <name>`.** The owner
  is the human of record — the `owner` step role resolves to it, megalaunch
  and the dependency drain select on it, Slack mentions derive from it. The
  command is the only writer: it validates the prospective ticket, writes
  under the publication barrier, appends `owner '<old>' → '<new>'` to the
  audit log, and syncs to control under the ordinary state guard, without a
  Slack post. It accepts every status except the terminal outcomes (a
  finished record keeps the owner it finished under) and `in_progress`,
  because a live session's routing lease compares `owner` — pause the ticket
  first. A hand edit of `owner:` skips all four steps, which is how a ticket
  ends up naming someone who handed it off months earlier; `coga validate`
  cannot tell a stale owner from a current one, so the command is the
  discipline.
- **Dependency: a blocker ask naming the prerequisite's exact
  path-qualified slug.** Declaring that ticket B waits on ticket A is
  `coga block --task <B> --reason "Depends on <A>: <what B needs from it>"`,
  run once B is `active` (block accepts `active`, `in_progress`, and
  `blocked`; activate a draft first). That is not a workaround for a missing
  field — the blocker *is* the mechanism. The ask is visible in
  `coga status --blocked` and the blocker reminders, and the megalaunch
  dependency drain ([coga/megalaunch](../megalaunch/SKILL.md)) reads the slug out of the reason and retries B
  automatically once A is `done` or has been retired. The slug must be the
  complete path-qualified ref (`v2/some-ticket`, not `some-ticket`), matched
  as a whole token; a title or a partial slug names nothing. A dependency
  declared from the successor's side ("this blocks X") is invisible to every
  command and stays prose.
- **Supersession: `coga mark canceled <old> --message "Superseded by <new>"`.**
  When a newer ticket replaces an older one, the older one is canceled with a
  reason that begins `Superseded by ` followed by the successor's exact
  path-qualified slug (and a date if useful). Cancellation already provides
  everything a separate `superseded` terminal would: it is terminal, so the
  ticket leaves `coga status`, blocker sweeps, and launch candidates; the
  reason is required and lands in the audit log; `step:` is cleared and the
  body and blackboard are left as history. A superseded ticket left at
  `paused` or `draft` is the failure mode — it keeps surfacing as live work.
  When readers of the file itself need the pointer, `## Context` opens with
  the same words in bold: `**Superseded by `<new>` (<date>).**`; that line is
  a courtesy copy of the log reason, not the record. A design pivot *within*
  one ticket is a different shape and keeps its `## Superseded designs`
  convention (`dev/code`).
