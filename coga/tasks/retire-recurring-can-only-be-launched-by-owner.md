---
slug: retire-recurring-can-only-be-launched-by-owner
title: Retire recurring-can-only-be-launched-by-owner
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
---

## Description

Retire the done ticket `recurring-can-only-be-launched-by-owner`.

Retire is the slug-targeted launcher for `retro/done-ticket`: extract durable
knowledge from one finished task, then delete it. When new durable knowledge
exists, Retro opens a PR that records the `## Retro` marker, edits the knowledge
base, and deletes the source task directory in the same PR. When no new durable
knowledge exists, there is no PR to bundle the deletion into, so Retro
direct-deletes the task via `coga delete` — no marker, no PR. This task is the
ad-hoc shell that drives that single skill against the named slug. Do not
invent additional steps. The complete Retro pass runs in one subagent inside a
dedicated isolated checkout; do not run it in this retire task's checkout.
Branch hygiene (local prune, stale-branch sweep) is a Dream concern, not
retire's.

### Console Progress

Write short progress updates to the console before and after each phase: retro
result, PR open when applicable, final status mark. Include the slug or PR link
being acted on. The blackboard remains the durable record; console progress is
for the human watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not improvise.

1. **Run `retro/done-ticket` against `recurring-can-only-be-launched-by-owner`.**
   First copy the source task's complete resolved artifact (its bare Markdown
   file or its whole directory, including sibling attachments), repo-global
   `coga/log.md`, and current local contexts/skills into a read-only temporary
   evidence snapshot. Use ordinary copies, not symlinks. Then delegate the
   complete pass to one subagent inside a dedicated isolated git checkout,
   passing `recurring-can-only-be-launched-by-owner`, the snapshot path, and this task's absolute repo root. Use
   native `isolation: worktree` when the
   agent supports it; otherwise create a temporary checkout with
   `git worktree add` and tell the subagent its exact cwd. Fetch the configured
   remote control branch first and base the checkout's unique temporary branch
   on that fresh tip. If the managed sandbox makes the primary `.git` metadata
   read-only, use an independent `git clone --no-hardlinks` under `/tmp`,
   repointed to the configured real remote. Do not run Retro in this retire
   task's checkout or fall back to an unisolated subagent. Before any Coga
   command, ordinary-copy the caller's gitignored `coga.local.toml` to the same
   repo-relative path in the isolated checkout; never symlink, snapshot, stage,
   or commit it. In the
   isolated subagent, read the skill at
   package `bootstrap/skills/retro/done-ticket/SKILL.md` unless a local
   `coga/skills/retro/done-ticket/SKILL.md` override exists, and follow it.
   The skill verifies the isolated-checkout boundary before reading the snapshot;
   all Retro branch switches and deletes stay inside it. When new durable
   knowledge exists, Retro opens a PR that records the `## Retro` marker, edits
   the knowledge base, and deletes `coga/tasks/recurring-can-only-be-launched-by-owner/` in the same PR. When no
   new durable knowledge exists, it runs
   `coga delete recurring-can-only-be-launched-by-owner --keep-control-checkout` from a linked worktree or
   ordinary `coga delete recurring-can-only-be-launched-by-owner` from an independent clone. Both land the
   direct `Ticket: recurring-can-only-be-launched-by-owner — deleted` commit on the remote control branch
   without refreshing the operator's checkout, with no PR and no marker.
   Recovery is via `git restore`.

   After the subagent returns, verify the PR branch is pushed or the direct
   deletion is present on the remote control branch, and verify the isolated
   checkout is clean. Remove the copied `coga.local.toml`; then remove the
   linked worktree and its temporary branch, or delete the exact independent
   clone directory. Delete the temporary snapshot too. Mutating subagents are
   not guaranteed to auto-clean. If durability or cleanup cannot be verified,
   preserve both paths and block.

2. **Mark this retire task done.** Run `coga mark done <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, or
   "direct-deleted, no durable knowledge" when retro found nothing durable.

### Stop conditions

- Source task is not `status: done` → escalate via `coga block` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- A complete evidence snapshot, machine-local config copy, or isolated
  worktree/clone execution is unavailable → escalate; never run Retro in this
  task's checkout as a fallback.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.

## Context

<!-- coga:blackboard -->

## Finding: retro pass already ran — no work left

Phase 1 (`retro/done-ticket`) was **already executed for this slug** by Dream
2026-W34 before this retire task ever launched. No snapshot, isolated
checkout, or subagent was created here: there is no source artifact left to
snapshot, and re-running Retro against a deleted ticket is not possible.

Evidence:

- `coga/tasks/recurring-can-only-be-launched-by-owner.md` is absent from the
  working tree **and** from `origin/main`; the only remaining match under
  `coga/tasks/` is this retire shell itself.
- Deletion commit `59181000` — `Ticket: recurring-can-only-be-launched-by-owner
  — deleted` (2026-08-17 14:50, nicktoper), 168 lines removed, task file only.
  Verified as an ancestor of `origin/main`, so the deletion is durable on the
  control branch.
- The commit shape is Retro's **direct-delete** path: a bare
  `Ticket: <slug> — deleted` commit on the control branch, no PR, no `## Retro`
  marker, and no `coga/log.md` edit in the diff. That is the documented outcome
  for "no new durable knowledge".
- Timing places it inside the Dream 2026-W34 run (`coga/log.md`:3589–3593,
  14:26–14:55), which reported "11 done tickets cleared (10 direct-deleted)".
  This slug was one of them.
- Source ticket was legitimately `done` first: auto-bumped on merge of PR #687
  (`coga/log.md`:3425).

## Decision

Did not `coga block`. The "source task is missing" stop condition guards
against a *wrong slug*; here the slug is right and the retire outcome —
knowledge extracted (none durable), ticket deleted from the control branch —
is already achieved and verified. Blocking would park a task whose desired end
state exists. Nothing to clean up: no worktree, clone, snapshot, or copied
`coga.local.toml` was created by this run.

Phase 2: marking done with the direct-delete summary.
