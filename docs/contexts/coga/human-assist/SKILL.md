---
name: coga/human-assist
description: The `coga launch <slug> --agent <type>` assist on an owner-held step — when it is entered, the recorded checkout and PR-head proof it requires before composition, the scripts it may run, and whom its lifecycle lines credit.
---

# Human-step assist

An explicit `coga launch <slug> --agent <type>` whose derived operator for
the current (or prospectively activated) step is the human owner runs one
visible assisting session on that step. The role decides, not the name: an
explicitly declared agent step is never an assist, and a human whose nickname
matches an agent type is never an agent. An override on an agent step is an
ordinary launch ([launch](../launch/SKILL.md)). The banner names the
assist; the ticket's owner, main-agent choice, and roles are unchanged, and
the override never continues to a later step.

A human-step override without a TTY is refused before any recorded-checkout
or PR validation.

## Recorded checkout

The assist runs on the ticket's PR branch only when Git sync is enabled,
`## Dev` records `branch:`, `worktree:`, and `pr:`, launch runs from exactly
that checkout (primary, linked worktree, or independent fallback clone), and
it is on the recorded branch. Otherwise the assist gets ordinary launch
handling with no alignment and no assist identity. Launch's checkout
boundary never moves this checkout
([coga/checkouts/launch-boundary](../checkouts/launch-boundary/SKILL.md)).

## PR-head proof before composition

Before anything is composed, and for draft, active, in_progress, paused, and
blocked tickets alike, launch proves the checkout holds the PR's head:

1. The recorded branch must not share the control branch's name.
2. The PR is open, its head branch is the recorded branch, and its head
   repository is the configured remote's, so a same-named base-repository
   branch cannot stand in for a fork head.
3. The fetched branch tip must equal the PR head. A behind checkout is
   fast-forwarded; an ahead or diverged tip refuses, as does dirt outside the
   Coga roots. A PR branch that keeps moving refuses with "retry once the PR
   branch is stable".

Any change to the recorded branch, PR URL, or PR head after that proof
refuses.

## Scripts under an assist

When the target carries `ticket.py`
([script tickets](../script-tickets/SKILL.md)), the assist validates the
agent name, resolves secrets, preflights notification config and push auth,
activates and starts the ticket, and only then runs the script. Agent CLI
lookup and composition stay deferred until the script leaves agent work
open. The script's result is published to control right after it exits. Once
a script advances to an agent step, that step's derived agent owns routing;
the override stops participating.

## Attribution

An assist is the exception to launch's attribution rule: in-session `bump`,
`mark`, and `block` lines credit the assisting agent instead of the owner,
including after a script hands the chain to an agent step. A script's own
completion inside an assist still credits `system`. The identity only
attributes; it grants no publication authority, and nested non-assist
spawns drop it.

Everything an assist publishes lands on control, never on the PR branch. The
environment contract, alignment loop, and publication table are in
[assist publication](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/assist-publication/SKILL.md).
