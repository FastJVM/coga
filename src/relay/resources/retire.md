Retire the done ticket `{slug}`.

Retire is the slug-targeted launcher for `retro/done-ticket`: extract durable
knowledge from one finished task, then delete it. When new durable knowledge
exists, Retro opens a PR that records the `## Retro` marker, edits the knowledge
base, and deletes the source task directory in the same PR. When no new durable
knowledge exists, there is no PR to bundle the deletion into, so Retro
direct-deletes the task via `relay delete` — no marker, no PR. This task is the
ad-hoc shell that drives that single skill against the named slug. Do not
invent additional steps. Branch hygiene (local prune, stale-branch sweep) is a
Dream concern, not retire's.

### Console Progress

Write short progress updates to the console before and after each phase: retro
result, PR open when applicable, final status mark. Include the slug or PR link
being acted on. The blackboard remains the durable record; console progress is
for the human watching the run.

### Ordered Pass

Run these in order. Stop and ask if any precondition fails — do not improvise.

1. **Run `retro/done-ticket` against `{slug}`.** Read the skill at
   `relay-os/bootstrap/skills/retro/done-ticket/SKILL.md` unless a local
   `relay-os/skills/retro/done-ticket/SKILL.md` override exists, and follow
   it. The skill stops and asks if the slug is ambiguous, the task is not `status: done`,
   or any required evidence file is missing. When new durable knowledge exists,
   it opens a PR that records the `## Retro` marker, edits the knowledge base,
   and deletes `relay-os/tasks/{slug}/` in the same PR. When no new durable
   knowledge exists, it direct-deletes `relay-os/tasks/{slug}/` via
   `relay delete` — a working-tree `git rm` plus a direct
   `Ticket: {slug} — deleted` commit, with no PR and no marker. Recovery is via
   `git restore`.

2. **Mark this retire task done.** Run `relay mark done <this-task-slug>`
   with a `--message` summarizing what happened: the retro PR link, or
   "direct-deleted, no durable knowledge" when retro found nothing durable.

### Stop conditions

- Source task is not `status: done` → escalate via `relay panic` with the
  reason. Retire only operates on done tickets.
- Source task is missing → escalate; the slug is wrong.
- Retro skill stops and asks → surface the reason; do not improvise.
- Anything outside the allowed scope above → escalate, do not improvise.
