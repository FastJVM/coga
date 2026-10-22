---
name: coga-dev/internals
description: Index of the concurrency and publication guarantees behind coga launch, megalaunch, the recurring runner, and open-pr, with one line and a link per internals page; attaching it loads only this index, not the child pages.
---

# Coga implementation internals

These pages hold what a change to `src/coga/launch.py`,
`src/coga/launch_script.py`, `src/coga/megalaunch.py`,
`src/coga/repl_supervisor.py`, `src/coga/pr_assist.py`,
`src/coga/open_pr.py`, `src/coga/step_gate.py`, or the recurring runner must
not break. They are not attached by default: operating Coga needs
[launch](../../coga/launch/SKILL.md) and [megalaunch](../../coga/megalaunch/SKILL.md), not
these proofs. Links are navigation only, so attaching this index does not
load any child page. Attach the specific page a ticket touches.

Shared ground rules: control is the only durable home for task state, Coga
never commits on a local branch, every publication is one `git.publish`
whose provenance check is the cross-checkout compare-and-set (`coga/state-publication`),
and the local state lock serializes only one checkout's writers.

## Guarantees and their pages

- [Agent config](agent-config/SKILL.md): the key-level `[agents.*]`
  merge, `default_agent` validation and freezing, and `peer` resolution.
- [Agent spawn](agent-spawn/SKILL.md): every agent goes through
  `spawn_agent_session`; prompt-file delivery above 120,000 bytes; sentinel
  scoping and exit classification; missing file versus missing CLI.
- [Assist publication](assist-publication/SKILL.md): every
  assist write lands on control, never the PR branch; the identity only
  attributes.
- [Launch claims](launch-claims/SKILL.md): megalaunch's
  exact-byte preflight, strict compare-and-set claim, the `pending:` seal,
  the held-child proof, admission ordering under the state lock, and direct
  chat's occupancy guard and receipt.
- [Claim recovery](claim-recovery/SKILL.md): pending, admitted,
  and `released:` forms; ordinary-launch reconciliation of a released
  witness; retained evidence.
- [State publication](state-publication/SKILL.md): publication invariants and
  root membership machinery; the [publish primitive](state-publication/publish/SKILL.md)
  owns the transaction.
- [Recurring admission](recurring-admission/SKILL.md): frozen
  period generations, the pre-spawn lease, the serviced-period ledger read,
  inactivity gate ordering, exact-ledger creation, and why delegation exists.
- [Recurring clone](recurring-clone/SKILL.md): clone-scoped runs — the
  clone ledger's location, the script deadline, bounded output, and
  process-tree termination including the Windows job object.
- [Recurring autofix](recurring-autofix/SKILL.md): why the run record is
  built, analyst parsing and heading demotion, the analyst's stdin, and the
  subscription auth retry.
- [Recurring control](recurring-control/SKILL.md): where
  recurring runs may start, the off-branch relay into a control worktree, the
  `--all` entry gate, and the owner gate read from the fetched control tip.
- [Recurring temp worktrees](recurring-temp-worktrees/SKILL.md):
  how an unattended `--all` child services a parked checkout from a temporary
  linked worktree, and recovery of its survivors.
- [Git refresh](git-refresh/SKILL.md): `git.refresh`,
  `fast_forward_control`, the staleness probe, stranded-ticket-write
  detection, and launch preparation details.
- [Branch sweep](branch-sweep/SKILL.md): checkout disposal and branch-sweep
  mechanics behind `coga/checkout-cleanup` — classification, forced local
  deletion, the merged-PR verdict, and retirement-tag collisions.
- [Git regressions](git-regressions/SKILL.md): why `git.publish`
  refuses a state file, and shipping a stored-ticket schema conversion.
- [Spool merge](spool-merge/SKILL.md): `merge=union` append-only
  files, the one-line-per-event log encoding, and union publication.
- [Blackboard IO](blackboard-io/SKILL.md): the fence matcher, body-section
  parser, superseded-design projection, stock-blackboard check, creation
  template, and blackboard writer races.
- [Activity capture](activity-capture/SKILL.md): the bounded,
  secret-redacted usage record captured after each agent session.
- [Usage pricing](usage-pricing/SKILL.md): record facts a future
  dollar-cost price table must handle.
- [Notifications](notifications/SKILL.md): `fatal` versus best-effort posts,
  the `preflight_post` gate, redaction, the module behind each producer, and
  message format.

## Not covered here

What launch does and what advances a step (`coga/launch`, `coga/lifecycle`),
the git primitive (`coga/state-publication`), and where code lives and how it is tested
(`coga-dev/codebase`, `coga-dev/testing`).
