---
slug: retire-decide-the-fate-of-two-premise-dead-v2-drafts-whos
title: Retire decide-the-fate-of-two-premise-dead-v2-drafts-whos
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

Retire the done ticket `decide-the-fate-of-two-premise-dead-v2-drafts-whos`.

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

1. **Run `retro/done-ticket` against `decide-the-fate-of-two-premise-dead-v2-drafts-whos`.**
   First copy the source task's complete resolved artifact (its bare Markdown
   file or its whole directory, including sibling attachments), repo-global
   `coga/log.md`, and current local contexts/skills into a read-only temporary
   evidence snapshot. Use ordinary copies, not symlinks. Then delegate the
   complete pass to one subagent inside a dedicated isolated git checkout,
   passing `decide-the-fate-of-two-premise-dead-v2-drafts-whos`, the snapshot path, and this task's absolute repo root. Use
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
   the knowledge base, and deletes `coga/tasks/decide-the-fate-of-two-premise-dead-v2-drafts-whos/` in the same PR. When no
   new durable knowledge exists, it runs
   `coga delete decide-the-fate-of-two-premise-dead-v2-drafts-whos --keep-control-checkout` from a linked worktree or
   ordinary `coga delete decide-the-fate-of-two-premise-dead-v2-drafts-whos` from an independent clone. Both land the
   direct `Ticket: decide-the-fate-of-two-premise-dead-v2-drafts-whos — deleted` commit on the remote control branch
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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-08-18 — already satisfied, no Retro rerun

**Phase 1 (`retro/done-ticket`) not run: its work was already completed.**

Findings, in order:

- Source artifact `coga/tasks/decide-the-fate-of-two-premise-dead-v2-drafts-whos.md`
  is absent from this checkout. It was a bare Markdown file, never a directory.
- Git history explains why: `0de678ef` — `Ticket:
  decide-the-fate-of-two-premise-dead-v2-drafts-whos — deleted` (2026-08-17,
  232 deletions, single file). `git merge-base --is-ancestor 0de678ef
  origin/main` passes, so the deletion is durable on the remote control branch.
- That commit is Retro's own no-durable-knowledge direct-delete path, run under
  Dream, not an ad-hoc removal. `coga/tasks/recurring/dream/ticket.md` lists
  this slug in its Phase 4 eligible-done set, then under **"No durable
  knowledge — 10 (direct-deleted, no marker, no PR)"**, and again in its
  direct-deletes ledger against hash `0de678ef` with the caller verification
  ("all 10 absent from `origin/main`; isolated worktree clean, config copy
  removed, worktree + temp branch removed; evidence snapshot deleted").
- Consistent with that path: no `## Retro` marker exists anywhere for this slug,
  and the one open PR (#699) is unrelated.

**Decision — close as already satisfied.** Retire's contract is "extract durable
knowledge from one finished task, then delete it." Both halves are done, by the
skill this shell exists to drive, with the deletion durable on `origin/main`.
Restoring the file via `git restore` to rerun Retro would re-litigate a
disposition Dream already made and the owner already accepted.

Precedent applied rather than re-asking: `retire-coga-important-support-second-webhook`
hit this exact shape (shell left `in_progress` while its source was
direct-deleted out from under it) and was blocked for the owner on 2026-08-13.
The owner's answer, `coga/log.md` line 3418 (2026-08-14): "Owner confirmed the
prior direct deletion in commit bc94a150 already satisfied retirement; do not
restore the source or rerun Retro. Close this retire shell as already
satisfied." That shell was then marked done. Same facts here, so the same
disposition.

No isolated checkout, snapshot, or `coga.local.toml` copy was created this run —
there was no Retro pass to isolate — so there is nothing to clean up.
