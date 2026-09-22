---
name: coga/internals/human-assist
description: The `coga launch <slug> --agent <type>` assist on an owner-held step — when it is entered, the recorded-checkout alignment and PR-head proof it runs before composition, the scripts it may run, and the assist identity its child inherits.
---

# Human-step assist

An explicit `coga launch <slug> --agent <type>` whose derived operator for
the current (or prospectively activated) step is the human owner runs one
visible assisting session on that step. The role decides, not the name: an
explicitly declared agent step is never an assist, and a human whose nickname
matches an agent type is never an agent. An override on an agent step is an
ordinary launch ([launch](../../launch/SKILL.md)). The banner names the
assist; the ticket's owner, main-agent choice, and roles are unchanged, and
the override never continues to a later step.

A human-step override without a TTY is refused before any recorded-checkout
or PR validation.

## Recorded checkout

`_recorded_single_checkout_assist_branch` qualifies only when Git sync is
enabled, `## Dev` records `branch:`, `worktree:`, and `pr:`, launch runs from
exactly that checkout (primary, linked worktree, or independent fallback
clone), and it is on the recorded branch. Otherwise the assist gets ordinary
launch handling with no alignment and no assist identity.

## Alignment before composition

Before any skill refresh, config, ticket, secret, expected-step, or prompt
derivation, for draft, active, in_progress, paused, and blocked tickets:

1. The recorded branch must not share the control branch's name.
2. `pr_assist.verify_recorded_assist_pr_head`: the PR is `OPEN`, its head
   branch is the recorded branch, and its head repository (host, owner, name)
   equals the configured remote's push URL, so a same-named base-repository
   branch cannot stand in for a fork head.
3. `_align_recorded_assist_checkout` fetches the branch into its
   remote-tracking ref; that OID must equal the PR head. A behind checkout is
   fast-forwarded (`merge --ff-only`); an ahead or diverged tip refuses, as
   does dirt other than Coga's live task, log, and recurring state.
4. After a move, config and target reload (the slug resolved from the user's
   prefix must still resolve to the same task) and the loop repeats; three
   consecutive moves refuse ("retry once the PR branch is stable").

After classification the recorded branch, PR URL, and PR head are checked
again; any change since alignment refuses.

## Scripts under an assist

When the target carries `ticket.py`
([script tickets](../../script-tickets/SKILL.md)), the assist validates the
agent name, resolves secrets, preflights live notification config
(`preflight_post`) and push auth, activates and starts the ticket, and only
then runs the script. Agent CLI lookup, skill refresh, and composition stay
deferred until the script leaves agent work open. The script child receives
`COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, and the three `COGA_ASSIST_*`
values; its result is published to control right after it exits. Its
completion still credits `system`. Once a script advances to an agent step,
that step's derived agent owns routing and the assist identity for later
chained scripts; the override stops participating in routing.

## Identity, not a publication path

The agent child inherits `COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, and
`COGA_ASSIST_PR`. In-session `bump`, `mark`, and `block` read them through
`pr_assist.assist_session_from_env`, which applies only when
`COGA_EXPECTED_TASK` names the same task, and requires the PR and a
configured agent. They attribute audit lines to the assisting agent instead
of the owner, including after a script hands the chain to an agent step.
Nested non-assist spawns clear all three.

What an assist publishes, and where, is in
[assist publication](../assist-publication/SKILL.md).
