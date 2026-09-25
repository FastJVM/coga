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

A retired or deleted task (`coga retire`, `delete-task`, Retro) leaves its
body and blackboard only as a Git blob; `coga show` no longer finds it. Find
the deleting commit on the control branch (`origin/main` by default), then
read the file from its parent:

```bash
git log origin/main --diff-filter=D --name-only -- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'
git show <commit>^:<path>
```

Search both pathspecs: the tree was `relay-os/tasks/` before the relay → coga
rename (`d0645a197`, #454), so a `coga/tasks/`-only search misses earlier
deletions. The newest hit is the retirement; older hits are that rename or a
`.md` ↔ `<slug>/` format conversion. Older directory-form tasks kept the
blackboard in a sibling `blackboard.md`; read it the same way.

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
- **Authoring agent.** `authoring.resolve_authoring_agent` picks who runs
  the interview, for `coga ticket` and megalaunch's picked drafts alike;
  the first set term wins: (1) `--agent`, `coga megalaunch --agent`, or the
  `--pick-agent` answer; (2) `COGA_AUTHORING_AGENT`; (3) `[authoring] agent`
  in `coga.local.toml`; (4) the target ticket's `agent:`; (5)
  `bootstrap/ticket`'s `agent:`, the install-level default; (6)
  `Config.default_agent()`. An unknown name from any term fails loud naming
  that term, never falling through. The choice selects the interviewer only
  and is never written to the ticket. `coga ticket --pick-agent` (TTY only;
  refused with `--agent`) lists the configured types in declaration order,
  marks the would-be default, and takes Enter for it; with no valid default,
  Enter re-prompts. One configured type is used without asking; none fails.
  It prints how to make the choice stick and writes no config. Megalaunch
  never prompts: an unresolvable agent is reported and the draft left.
- `coga show <ref>` renders the ticket and its `coga/log.md` history for
  humans; bootstrap targets show only `ticket.md`. Read files directly for
  scripting.

Installed `coga <cmd> --help` is the syntax authority.

## Ownership and ticket relationships

`owner:` is the human of record: owner steps route to that person, megalaunch
filters by owner, and notifications mention them. Reassign with
`coga owner <slug> <name>`. There is no independent `assignee:` or legacy
`human:` field to update. The command preserves status, step, and body, rejects
blank or unchanged names and terminal records, and writes an audit line without
a Slack post.

An `in_progress` agent step must stop and be paused before reassignment. An
`in_progress` **owner-held gate** instead requires `--assist-stopped`: the
human confirms any assisting agent has stopped, from outside that ticket's
supervised session. This preserves the gate so its new owner can still bump
it. Coga has no cross-checkout live-session registry; the flag is an explicit
human attestation, not an automatic liveness check. A supervised session cannot
reassign its own ticket, and an outstanding `launch_generation` is refused;
stop the session and follow [claim recovery](../internals/claim-recovery/SKILL.md)
first. Reassignment never clears or invalidates a launch claim.

The package-private transaction is why this command lives in core: it holds
`git.state_lock` across the read, prospective validation, local byte comparison,
write, audit, and strict publication with the original ticket bytes as `expect`.
A concurrent local edit is preserved. A definite publication failure restores
only the command's own ticket bytes and retracts its audit; an uncertain push
keeps the write for reconciliation. Both failures exit 75 to suppress the generic
sweep. Refresh/reconcile control before retrying. With Git disabled or unavailable
through a documented soft-skip, the local write remains the result
([state publication](../internals/state-publication/SKILL.md)).

Ticket-to-ticket relationships use the dependency and supersession conventions
in [coga/lifecycle](../lifecycle/SKILL.md), rather than new `dependencies:` or
`superseded_by:` frontmatter. Successor-side “this blocks X” prose is a human
pointer, not machine-readable ordering.
