# Relay protocol

You are an agent working on a single ticket inside a Relay repo. This
document tells you how to operate within Relay — not what to do. What
to do comes from the skill, contexts, and ticket body below this protocol
in the composed prompt.

This protocol is the same for every task in every project. Read it once,
then rely on it.

## Your identity in this session

The composed prompt above includes a header that names the task you're
working on (project, task ID, title). You can also reach the same
information through environment variables that `relay launch` sets when
it spawns you:

| Env var             | What it holds                                            |
|---------------------|----------------------------------------------------------|
| `RELAY_TASK_ID`     | Numeric task ID, zero-padded to 3 digits — e.g. `003`    |
| `RELAY_PROJECT`     | Project name — e.g. `email-tool`                         |
| `RELAY_TASK_SLUG`   | Slug portion only, no ID prefix — e.g. `fix-retry-logic` |
| `RELAY_TASK_DIR`    | Absolute path to the task directory                      |
| `RELAY_BLACKBOARD`  | Shortcut for `$RELAY_TASK_DIR/blackboard.md`             |
| `RELAY_REPO_ROOT`   | Absolute path to the Relay repo root                     |

Use these in shell commands rather than hard-coding values. For
example: `relay step --task $RELAY_TASK_ID`. A snippet that uses the
env var works in every session; a snippet that hard-codes `003` is
copy-paste rot waiting to happen.

These env vars are not secret — they're identifying information for
your task. Other env vars present in your environment may be secret;
see "Secrets" below.

## Files in a task directory

Every task is a directory at
`$RELAY_REPO_ROOT/projects/<project>/relay-os/tasks/<id>-<slug>/` (for
local-type projects) or
`<project-path>/relay-os/tasks/<id>-<slug>/` (for repo-type projects,
where `<project-path>` lives wherever `relay.local.toml` says). Either
way, `$RELAY_TASK_DIR` always resolves to the right place.

The directory contains three files:

- **`ticket.md`** — YAML frontmatter plus description/context. This is
  the source of truth for the task's assignee, status, workflow step,
  mode, and context references. **You do not edit it.** If you discover
  domain knowledge that belongs attached to this task, write the
  suggestion under **Findings** on the blackboard and surface it via
  `relay feed` — a human decides whether to add it to `contexts`.
- **`blackboard.md`** — the shared workspace for you and the human. This
  is where you write. See "Blackboard discipline" below.
- **`log.md`** — append-only structured log. **You do not write to this
  file.** CLI commands (`relay step`, `relay panic`, `relay feed`,
  `relay launch`) append to it as a side effect. Writing to it directly
  corrupts the audit trail.

Reassignment, status changes, and step advances happen through CLI
commands or direct human edits — not through you.

## Blackboard discipline

The blackboard has a fixed skeleton with five sections: **Plan**,
**Notes**, **Findings**, **Blockers**, **Decisions**. Read selectively —
if you only need Findings for your current step, load only that section.

Write to every section as the work warrants:

- **Plan** — your current working plan. Update when intent changes. Note
  what changed and why. This is live state, not history; git preserves
  the full trail.
- **Findings** — discovered facts, intermediate results, research
  outputs. The next session (yours or someone else's) reads this to
  understand what was learned. Be specific. "retry worked" is useless;
  "retry succeeded after switching to exponential backoff with jitter;
  Stripe 429 resolved in 3 attempts with 1s/4s/12s delays" is useful.
- **Decisions** — rationale for choices that affect future work. Format:
  `[YYYY-MM-DD] [actor] decision + reason`. An agent relaunching
  this task reads Decisions first to pick up context.
- **Blockers** — anything stalling progress. Write a blocker before you
  panic, so the human can read what stopped you without having to
  reconstruct it from chat.
- **Notes** — free space. Drop observations, links, half-formed thoughts.
  If a note matures into a finding or decision, move it.

Rule of thumb: write to the blackboard after any meaningful progress or
any meaningful decision. An agent that writes is recoverable across
crashes and handoffs; one that does not is not.

## Workflow steps

The ticket's `step` field tells you which step you are on, in the format
`N (name)`. Do the work that step requires — the step's skill or inline
instruction is elsewhere in the composed prompt above this section.

When the step is complete, call:

    relay step --task $RELAY_TASK_ID

Do not skip steps. Do not try to advance past work that isn't done. Do
not move backwards. If a previous step needs rework, call `relay panic`
and describe why — a human decides whether to reassign or restart.

If the ticket has no workflow, there are no steps. You are done when
the task is done; you signal completion by setting status to `done` or
by calling `relay panic` if you cannot finish.

## Escalation — `relay panic`

Call:

    relay panic --task $RELAY_TASK_ID --reason "<short, concrete reason>"

when you are stuck and cannot proceed. Before panicking, write the
blocker to the **Blockers** section of the blackboard so the human can
see what stopped you.

After panicking, **stop**. Do not continue trying. Panic is not a
failure state — it is the correct way for an autonomous agent to hand
control back to a human. Speculation, retries, or "best-effort" work
after a panic is worse than no work.

Be specific about the reason. "429 retry logic unclear, need decision
on backoff ceiling" is actionable. "stuck" is not.

## Feed — `relay feed`

Call:

    relay feed --task $RELAY_TASK_ID --message "<short fyi>"

to post an informational update to the shared Slack channel. Use it for
milestones the team would want to see in passing: "opened PR #142",
"downloaded Q4 forms to /drive/2026", "classified 83 updates, 12 kept".

Do not use feed for blockers — that is what panic is for. Do not use
feed for every step transition — `relay step` already posts to feed.
Keep messages short and concrete.

## Frontmatter discipline

YAML frontmatter in `ticket.md` is machine-parsable. You **read** it —
it's the source of truth for the task's assignee, status, workflow
step, mode, and contexts. You do **not edit** it. Every field — `title`,
`status`, `mode`, `owner`, `assignee`, `watchers`, `workflow`, `step`,
`contexts` — changes through CLI commands or direct human edits.

If you think a field should change (a context is missing, a step is
wrong, a status is stale), write the suggestion under **Findings** on
the blackboard and surface it via `relay feed`. A human decides whether
to apply it. Editing frontmatter yourself is out of scope regardless of
how obvious the change looks.

**One exception: interactive ticket creation.** During the initial
scaffolding flow — specifically, the `meta/create-suggest` skill run
immediately after `relay create` — the agent writes proposed values
(workflow, contexts, mode, assignee) directly into frontmatter as a
live draft. That exception is sanctioned because the human is present
and approving each field as it lands. It applies **only** in that
interactive creation flow; if the human steps away or the session is
not interactive, stop writing to frontmatter and fall back to
Findings-plus-feed like every other case.

## Secrets

Any environment variables present when you start were intentionally
injected by `relay launch` from `relay.local.toml`. Use them. Never
echo them to the blackboard, the log, or stdout. Never write them to
files, including files you create.

Distinguish carefully: the `RELAY_*` vars listed in "Your identity"
above are not secret — they identify your task. Vars like
`STRIPE_SECRET_KEY`, `LINKEDIN_TOKEN`, `SLACK_WEBHOOK` are secret —
treat their values as sensitive even when troubleshooting.

## Summary

Read ticket + context + skill + blackboard. Do the step's work. Write
findings and decisions as you go. Advance or panic when done. Never
touch `log.md`. Never touch `ticket.md` frontmatter. Never leak
secrets. Use `$RELAY_TASK_ID` in commands.
