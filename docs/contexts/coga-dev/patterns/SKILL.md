---
name: coga-dev/patterns
description: Rules of thumb for composing a new feature from Coga's core primitives when it collects events, carries state across runs, or changes state others need to know about, without hidden state, hidden queues, or unsafe concurrent writes.
---

# Coga patterns

Compositions of the core primitives (`coga/architecture`) recur often enough
to be worth naming, so a new feature reaches for the established shape instead
of re-deriving it — or inventing a hidden `.queue` dotfile that breaks Coga's
durable-file model (`coga/architecture`).

## Rules of thumb for a new composition

- **No hidden state.** Anything that accumulates between runs is a real,
  git-tracked, human-readable file under the Coga root — openable
  mid-flight, never a dotfile or opaque store.
- **No hidden queue.** Prefer posting or recording an event the moment it
  happens. Coga once batched outcomes into a daily digest spool and removed
  it (#786): at Coga's volume a queue only added a consumer, a drain step,
  and a class of drain/merge bugs. Add batching only when the live feed is
  demonstrably too noisy, and then as a visible file, not a service.
- **Capture at event time, not from history.** Record what happened when it
  fires, so nothing depends on reconstructing it from `git log`, and work
  that is done and deleted before a later reader runs is still accounted for.
  Session usage records in `coga/log.md` are the example (`coga/usage`).
- **Reuse the recurring machinery for the periodic half.** A scheduled
  reader is a `recurring/<job>/` template (`coga/recurring`) whose
  deterministic half is the reserved sibling `ticket.py`, with its cadence in
  `schedule:` frontmatter. The cadence is declared in the repo, but it is
  serviced only when an operator or an external scheduler runs
  `coga recurring`; Coga ships no daemon of its own.
- **Cross-run state lives beside the template, not in the period task.**
  `coga/recurring/<job>/` persists across runs; each period task is gone next
  period.
- **Stay correct by shape under concurrent writers.** Coga allows several
  processes and clones to write state at once. Atomic file replacement is
  crash-safety, not a lock; `merge=union` resolves only pure appends. A
  composition needs append-only regions, disjoint hunks, or an explicit
  publish guard — see `coga-dev/internals/spool-merge`.

## Sync for new commands

A command that changes state others need to know about reaches both sync
layers:

1. Make the three notification decisions — surface, destination, preflight
   policy — described in
   [notification internals](../internals/notifications/SKILL.md#adding-a-notifying-command).
2. Publish its task through `git.sync_task_state` at the logic boundary where
   the write, validation, log append, and notification post have all
   finalized ([publication implementation](../internals/state-publication/publish/SKILL.md)).
   The end-of-command sweep is a backstop with a generic message, not a
   substitute for the readable, individually attributed publish. It is
   opt-in: a new state-changing top-level command gets that backstop only
   once it is added to the sweeping allowlist
   ([the end-of-command sweep](../internals/state-publication/SKILL.md#the-end-of-command-sweep)).
3. Echo the local outcome to stdout before posting, so it stays visible
   above any notification error.

Never bypass both layers when the team needs awareness; never post chatter
that is not an outcome, urgent exception, or explicit FYI.

Owner decision (2026-10-01): the base prompt carries no rule forbidding
agents to commit Coga state, though a hand commit on local control diverges
it from origin and blocks launch. Prevention in the prompt would let agents
hide the divergence; the remedy belongs in a deterministic CLI guard that
detects it. Reopen only if such a guard proves insufficient.

## Not covered here

- The primitives themselves — `coga/architecture` and `coga/recurring`.
- How state lands on control across checkouts — `coga/state-publication`.
- The checkout-local admission and publication barrier used by launches —
  `coga-dev/internals/launch-claims`.
