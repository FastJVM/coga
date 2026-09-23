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
