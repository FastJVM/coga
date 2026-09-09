---
name: coga/autoclose/sweep
description: Close final-step Coga tickets whose linked GitHub PR has merged.
---

# Autoclose Merged Tickets

This skill documents the merged-ticket auto-close sweep behind the
`recurring/autoclose-merged/` ticket. That ticket's `ticket.py` calls
`coga.autoclose.run_autoclose_recipe` directly — no agent, no composed
prompt — and the same sweep is available as `coga run autoclose`. It is the
sole trigger for closing tickets whose PR has merged:

1. scan active and in-progress tickets,
2. read each ticket blackboard's `## Dev` `pr:` link,
3. check the linked PR state with `gh pr view`, and
4. mark the ticket `done` only when it is on its final workflow step, or has no
   workflow, and the PR is merged, and
5. report the `coga retire` follow-up for every ticket it closed that still
   records a `branch:` or `worktree:` under `## Dev`.

The scope is defined by `coga.autoclose.sweep_merged`.
Mid-workflow merges stay untouched because they are suspicious and need a human
to finish the ticket explicitly.

## The retire follow-up

Closing a ticket does not dispose of its feature checkout — `coga retire` does,
and it owns the safety proofs (same-repo linked worktree, no other live ticket
sharing it, no open PR for the head, branch landed at the recorded merged head).
Autoclose stays non-destructive and only *names* that follow-up, because
implicit destruction cuts against the principle that destructive behavior is
never implicit. Dream likewise leaves a checkout-bearing done ticket in place,
so the named command and the `## Dev` evidence it consumes remain valid until a
human retires it — the *evidence* is durable; the reported list of follow-ups
is not (see below).

Two surfaces, both silent when the sweep stranded nothing:

- a `## Autoclose Sweep: retire follow-ups` section listing the exact
  `coga retire <slug>` per ticket — appended to the task blackboard when run
  under a task, written to stdout otherwise. **That blackboard surface is
  per-run, not a durable worklist.** Autoclose's only recurring caller is
  `recurring/autoclose-merged`, and the `coga/recurring` context is explicit
  that a period task's blackboard is scratch space for one firing, deleted with
  the task the next period. The sweep only rediscovers tickets it closes in the
  *current* run, so a stranded checkout is never re-listed: a follow-up nobody
  acted on before the next firing is gone from every surface while the checkout
  is still there. A recurring follow-up needs a home outside the period task;
  the open ticket `persist-autoclose-retire-follow-ups` proposes a `retires.md`
  beside the recurring template. Until that lands, read both surfaces as a
  notification, not a backlog;
- one trailing Slack line for the whole sweep. The per-ticket `🎉 ... merged`
  line is left alone: it announces a lifecycle event and normally lands in the
  daily digest, while a retire hint is an operational to-do.

Run it directly with `coga run autoclose`. Live notification configuration is
preflighted before each affected ticket closes. Later `gh` or task-validation
failures remain hard failures, but any earlier closures are still reported.
After the report exists, a transiently undeliverable retire summary is
non-fatal and is recorded against the period task in the repo-global log.
