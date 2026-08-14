---
name: coga/autoclose/sweep
description: Close final-step Coga tickets whose linked GitHub PR has merged.
---

# Autoclose Merged Tickets

This skill documents the `autoclose` recipe used by the
`recurring/autoclose-merged/` ticket. The recipe runs the merged-ticket
auto-close sweep — the sole trigger for closing
tickets whose PR has merged:

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
never implicit.

Two surfaces, both silent when the sweep stranded nothing:

- a `## Autoclose Sweep: retire follow-ups` section listing the exact
  `coga retire <slug>` per ticket — appended to the task blackboard when run
  under a task, written to stdout otherwise;
- one trailing Slack line for the whole sweep. The per-ticket `🎉 ... merged`
  line is left alone: it announces a lifecycle event and normally lands in the
  daily digest, while a retire hint is an operational to-do.

Run it directly with `coga run autoclose`. `gh` failures and task validation
failures are hard failures; an undeliverable retire summary is not — the
tickets are already closed and the report is already written.
