Retire the done ticket `{slug}`.

Retire is the slug-targeted launcher for `retro/done-ticket`: extract durable
knowledge from one finished task, then delete it. When new durable knowledge
exists, Retro opens a PR that records the `## Retro` marker, edits the knowledge
base, and deletes the source task directory in the same PR. When no new durable
knowledge exists, there is no PR to bundle the deletion into, so Retro
direct-deletes the task via `coga delete` — no marker, no PR. This task is the
ad-hoc shell that drives that single skill against the named slug. Do not
invent additional steps. The complete Retro pass runs in one subagent inside a
dedicated linked worktree; do not run it in this retire task's checkout. Branch
hygiene (local prune, stale-branch sweep) is a Dream concern, not retire's.

### Console Progress

Write short progress updates to the console before and after each phase: retro
result, PR open when applicable, final status mark. Include the slug or PR link
being acted on. The blackboard remains the durable record; console progress is
for the human watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not improvise.

1. **Run `retro/done-ticket` against `{slug}`.**
   First copy the source task's complete resolved artifact (its bare Markdown
   file or its whole directory, including sibling attachments), repo-global
   `coga/log.md`, and current local contexts/skills into a read-only temporary
   evidence snapshot. Use ordinary copies, not symlinks. Then delegate the
   complete pass to one subagent inside a dedicated linked git worktree,
   passing `{slug}`, the snapshot path, and this task's absolute repo root. Use
   native `isolation: worktree` when the
   agent supports it; otherwise create a temporary checkout with
   `git worktree add` and tell the subagent its exact cwd. Fetch the configured
   remote control branch first and base the worktree's unique temporary branch
   on that fresh tip. Do not run Retro in this retire task's checkout or fall
   back to an unisolated subagent. In the
   isolated subagent, read the skill at
   package `bootstrap/skills/retro/done-ticket/SKILL.md` unless a local
   `coga/skills/retro/done-ticket/SKILL.md` override exists, and follow it.
   The skill verifies the linked-worktree boundary before reading the snapshot;
   all Retro branch switches and deletes stay inside it. When new durable
   knowledge exists, Retro opens a PR that records the `## Retro` marker, edits
   the knowledge base, and deletes `coga/tasks/{slug}/` in the same PR. When no
   new durable knowledge exists, it runs
   `coga delete {slug} --keep-control-checkout`, landing the direct
   `Ticket: {slug} — deleted` commit on the remote control branch without
   refreshing the operator's checkout, with no PR and no marker. Recovery is
   via `git restore`.

   After the subagent returns, verify the PR branch is pushed or the direct
   deletion is present on the remote control branch, and verify the isolated
   worktree is clean. Explicitly remove the worktree from outside it and delete
   its caller-created temporary branch and the temporary snapshot; mutating
   subagents are not guaranteed to auto-clean. If durability or cleanup cannot
   be verified, preserve both paths and block.

2. **Mark this retire task done.** Run `coga mark done <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, or
   "direct-deleted, no durable knowledge" when retro found nothing durable.

### Stop conditions

- Source task is not `status: done` → escalate via `coga block` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- A complete evidence snapshot or linked-worktree subagent execution is
  unavailable → escalate; never run Retro in this task's checkout as a
  fallback.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.
