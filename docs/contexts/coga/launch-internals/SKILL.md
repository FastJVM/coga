---
name: coga/launch-internals
description: Index of the concurrency and publication guarantees behind coga launch, megalaunch, the recurring runner, and open-pr, with one line and a link per internals page; attaching it loads only this index, not the child pages.
---

# Coga launch internals (index)

These pages hold what a change to `src/coga/commands/launch.py`,
`src/coga/launch_script.py`, `src/coga/megalaunch.py`,
`src/coga/repl_supervisor.py`, `src/coga/pr_assist.py`,
`src/coga/open_pr.py`, `src/coga/step_gate.py`, or the recurring runner must
not break. They are not attached by default: operating Coga needs
[launch](../launch/SKILL.md) and [megalaunch](../megalaunch/SKILL.md), not
these proofs. Links are navigation only, so attaching this index does not
load any child page. Attach the specific page a ticket touches.

Shared ground rules: control is the only durable home for task state, Coga
never commits on a local branch, every publication is one `git.publish`
whose provenance check is the cross-checkout compare-and-set (`coga/sync`),
and the local state lock serializes only one checkout's writers.

## Guarantees and their pages

- [Agent spawn](../internals/agent-spawn/SKILL.md): every agent goes through
  `spawn_agent_session`; prompt-file delivery above 120,000 bytes; sentinel
  scoping and exit classification; missing file versus missing CLI.
- [Script tickets](../script-tickets/SKILL.md): the exact `ticket.py`
  classifier, the script-first order, reloads after moving syncs, no
  operands, and `system` completion attribution.
- [Human assist](../internals/human-assist/SKILL.md): when an `--agent`
  override is an assist; recorded-checkout alignment and PR-head proof
  before composition; scripts under an assist.
- [Assist publication](../internals/assist-publication/SKILL.md): every
  assist write lands on control, never the PR branch; the identity only
  attributes.
- [Launch claims](../internals/launch-claims/SKILL.md): megalaunch's
  exact-byte preflight, strict compare-and-set claim, the `pending:` seal,
  the held-child proof, and admission ordering under the state lock.
- [Claim recovery](../internals/claim-recovery/SKILL.md): pending, admitted,
  and `released:` forms; ordinary-launch reconciliation of a released
  witness; retained evidence.
- [PR publication](../internals/pr-publication/SKILL.md): `coga open-pr`'s
  checkout gate, freshness and stranded-ticket checks,
  leased push, and control-only `pr:` record
  ([preparation](../internals/pr-publication/preparation/SKILL.md),
  [existing PR](../internals/pr-publication/existing-pr/SKILL.md)).
- [State publication](../internals/state-publication/SKILL.md): strict
  versus best-effort publication, the provenance check, and the state lock
  itself ([publish](../internals/state-publication/publish/SKILL.md),
  [sweep](../internals/state-publication/sweep/SKILL.md),
  [authoring](../internals/state-publication/authoring/SKILL.md)).
- [Recurring admission](../internals/recurring-admission/SKILL.md): frozen
  period generations, the pre-spawn lease, and exact-ledger creation.
- [Recurring control](../internals/recurring-control/SKILL.md): where
  recurring runs may start, the off-branch relay into a control worktree, the
  `--all` entry gate, and the owner gate read from the fetched control tip.
- [Recurring temp worktrees](../internals/recurring-temp-worktrees/SKILL.md):
  how an unattended `--all` child services a parked checkout from a temporary
  linked worktree, and recovery of its survivors.
- [Git refresh](../internals/git-refresh/SKILL.md): `git.refresh`,
  `fast_forward_control`, the staleness probe, and stranded-ticket-write
  detection.
- [Git regressions](../internals/git-regressions/SKILL.md): why `git.publish`
  refuses a state file, and shipping a stored-ticket schema conversion.
- [Spool merge](../internals/spool-merge/SKILL.md): `merge=union` append-only
  files, the one-line-per-event log encoding, and union publication.
- [Activity capture](../internals/activity-capture/SKILL.md): the bounded,
  secret-redacted usage record captured after each agent session.

## Not covered here

What launch does and what advances a step (`coga/launch`, `coga/lifecycle`),
the git primitive (`coga/sync`), and where code lives and how it is tested
(`coga/codebase`, `coga/testing`).
