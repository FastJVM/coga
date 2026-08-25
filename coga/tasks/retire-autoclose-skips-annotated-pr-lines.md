---
slug: retire-autoclose-skips-annotated-pr-lines
title: Retire autoclose-skips-annotated-pr-lines
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

Retire the done ticket `autoclose-skips-annotated-pr-lines`.

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

1. **Run `retro/done-ticket` against `autoclose-skips-annotated-pr-lines`.**
   First copy the source task's complete resolved artifact (its bare Markdown
   file or its whole directory, including sibling attachments), repo-global
   `coga/log.md`, and current local contexts/skills into a read-only temporary
   evidence snapshot. Use ordinary copies, not symlinks. Then delegate the
   complete pass to one subagent inside a dedicated isolated git checkout,
   passing `autoclose-skips-annotated-pr-lines`, the snapshot path, and this task's absolute repo root. Use
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
   the knowledge base, and deletes `coga/tasks/autoclose-skips-annotated-pr-lines/` in the same PR. When no
   new durable knowledge exists, it runs
   `coga delete autoclose-skips-annotated-pr-lines --keep-control-checkout` from a linked worktree or
   ordinary `coga delete autoclose-skips-annotated-pr-lines` from an independent clone. Both land the
   direct `Ticket: autoclose-skips-annotated-pr-lines — deleted` commit on the remote control branch
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
- Source task is missing → first decide **which** kind of missing. If the slug
  is wrong or unknown, escalate.

  Otherwise ask two questions in order.

  **Is it gone from the control branch?** That branch is the authority, not
  your working tree. Retro direct-deletes from a linked worktree with
  `coga delete --keep-control-checkout`, which deliberately leaves the
  operator's checkout untouched, so the source directory can still sit on your
  disk while already being absent from `<remote>/<control-branch>`. Requiring
  absence in both places would send this shell into a Retro run whose fresh
  isolated base lacks the source — which stops, recreating exactly the blocker
  this path exists to avoid. Fetch and check the control branch; a stale local
  copy is not evidence that the task is still live.

  **Did Retro actually process it?** Absence alone does not answer this. Every
  deletion — Retro's and an ordinary user's `coga delete <slug>` — writes the
  same `Ticket: <slug> — deleted` subject, so that commit being an ancestor of
  the control branch proves the directory is gone, not that any knowledge was
  extracted. Closing on the generic commit alone would silently skip Retro and
  discard durable knowledge. Require evidence that ties the deletion to a
  Retro/Dream pass, such as:
  - the deleting commit (or its PR) also adds or updates the source task's
    `## Retro` marker — the knowledge-bearing route;
  - a Dream run's `## Findings` / `## Dream Run Summary`, or a retro PR body,
    naming this slug as processed;
  - a `coga/log.md` line or retro PR recording the no-durable-knowledge
    direct-delete for this slug.

  With absence from the control branch **and** Retro evidence, this shell is
  **orphaned, not broken**: retire's whole contract — knowledge extracted,
  ticket deleted — is already satisfied by the skill this shell exists to
  drive. Record the evidence on this shell's blackboard and `coga mark done`
  it as already satisfied. Do **not** `git restore` the source to rerun Retro,
  and do **not** `coga block` — the missing-source stop condition guards
  against a wrong slug, not against a retirement that already happened.

  With absence but **no** Retro evidence, something deleted the ticket without
  extracting from it. Do not mark this shell done; escalate via `coga block`
  naming the slug and the bare deletion commit, so a human decides whether to
  restore and rerun Retro.
- A complete evidence snapshot, machine-local config copy, or isolated
  worktree/clone execution is unavailable → escalate; never run Retro in this
  task's checkout as a fallback.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Retro run

- Preconditions checked on 2026-08-25: fetched `origin/main`; the source artifact
  is the bare file `coga/tasks/autoclose-skips-annotated-pr-lines.md`, is present
  on the fresh control-branch tip, and has `status: done` with PR #706 recorded.
- The caller has `coga/coga.local.toml`, so the required ordinary config copy is
  available for an isolated checkout. Existing unrelated operator-checkout edits
  in `coga/log.md` and
  `coga/tasks/reconcile-recurring-wrapper-tty-admission-guidance.md` are being
  left untouched.
- The isolated Retro pass classified the ticket as **no new durable knowledge**:
  the annotated-`pr:` and placeholder rules are already present in the live and
  packaged `dev/code` contexts, while the remaining safeguards are explicit in
  current code/tests. No PR or `## Retro` marker was created.
- Retro direct-deleted the source with commit
  `1598bcad9830f9655dc2b95e8cf8d577e6dace1c` (`Ticket:
  autoclose-skips-annotated-pr-lines — deleted`). Independent verification after
  a fresh fetch found `origin/main` at that commit, the commit's sole change was
  deletion of the exact source task file, the source is absent from the control
  branch, and the isolated linked checkout is clean.
- Cleanup verified: removed the copied machine-local config, the exact linked
  checkout and its Git worktree metadata, the unique temporary branch, its
  parent directory, and the read-only evidence snapshot. No recovery paths
  remain because the direct deletion is durable on `origin/main`.
