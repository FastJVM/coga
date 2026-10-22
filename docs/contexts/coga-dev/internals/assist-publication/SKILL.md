---
name: coga-dev/internals/assist-publication
description: The recorded assist's alignment loop and `COGA_ASSIST_*` identity, and where a human-step assist's lifecycle, script, and audit writes are published (control only, never the PR branch), how failures behave, and what the assist identity does and does not authorize.
---

# Assist publication

A recorded human-step assist
([human assist](../../../coga/human-assist/SKILL.md)) runs in the checkout that holds
the PR's feature branch. That checkout's copy of the ticket is the live one,
yet nothing the assist generates is committed to that branch. Every write
goes through the same `git.publish` path as any other checkout and lands on
the control branch only (`coga/sync`; the strict-versus-best-effort split is
in `coga-dev/internals/state-publication/publish`).

## Alignment and identity

`_recorded_single_checkout_assist_branch` decides whether the recorded
checkout qualifies. Before any skill refresh, config, ticket, secret,
expected-step, or prompt derivation:

1. The recorded branch must not share the control branch's name.
2. `pr_assist.verify_recorded_assist_pr_head`: the PR is `OPEN`, its head
   branch is the recorded branch, and its head repository (host, owner, name)
   equals the configured remote's push URL.
3. `_align_recorded_assist_checkout` fetches the branch into its
   remote-tracking ref; that OID must equal the PR head. A behind checkout is
   fast-forwarded (`merge --ff-only`); an ahead or diverged tip refuses, as
   does dirt outside `git.coga_root_paths`.
4. After a move, config and target reload (the slug resolved from the user's
   prefix must still resolve to the same task) and the loop repeats; three
   consecutive moves refuse.

After classification the recorded branch, PR URL, and PR head are checked
again. A script under an assist also preflights notifications with
`preflight_post`, and its child receives `COGA_EXPECTED_TASK`,
`COGA_EXPECTED_STEP`, and the three `COGA_ASSIST_*` values.

The agent child inherits `COGA_ASSIST_AGENT`, `COGA_ASSIST_BRANCH`, and
`COGA_ASSIST_PR`. In-session `bump`, `mark`, and `block` read them through
`pr_assist.assist_session_from_env`, which applies only when
`COGA_EXPECTED_TASK` names the same task, and requires the PR and a
configured agent. Nested non-assist spawns clear all three.

## What is published, and where

| Write | Destination |
| --- | --- |
| Inline activation (draft, paused, blocked) | control |
| `active → in_progress` start | control |
| `launched as a script` line, `script exited with code N`, and the script's ticket result (published immediately after the child exits) | control |
| In-session `coga bump`, `mark`, `block`, `unblock` | control |
| A successful `requires: pr` bump | control |
| Teardown usage record and launch log line | control (`sync_log`) |

The feature branch receives only commits the agent or human make on purpose,
plus whatever `coga open-pr` pushes
([PR publication](../../../coga/pr-publication/SKILL.md)).

## Consequences

- The single checkout keeps Coga's live task, log, and recurring state dirty
  by design. Assist alignment tolerates dirt under the Coga roots
  (`git.coga_root_paths`, the same membership publication uses) and nothing
  else.
  `coga open-pr` has no such carve-out: it runs only from a checkout on the
  control branch, and a recorded clone with any dirt refuses
  ([PR publication](../../../coga/pr-publication/SKILL.md)).
- Assist writes use ordinary best-effort publication: a refused or failed
  sync is reported on stderr and in the log, the local transition stands,
  and the end-of-command state sweep retries it. There is no assist lease,
  compensation, or uncertain-push retention; those belong to megalaunch
  claims ([launch claims](../launch-claims/SKILL.md)) and recurring
  admission (`coga-dev/internals/recurring-admission`).
- Publication authority comes from the PR-head proof made before
  composition, not from the environment. `COGA_ASSIST_*` only attributes
  audit lines to the assisting agent. Inside an assist, `coga bump` refuses
  every rewind (`--to` / `--backward`); a human rewinds outside the assist.
- The deterministic attribution marker (`COGA_SCRIPT_TASK`,
  [script tickets](../../../coga/script-tickets/SKILL.md)) is independent of the
  assist identity. A script inside an assist credits `system`, and the marker
  can never stand in for the PR-head proof.
- A missing assist agent or PR on a script launch raises
  `ScriptPublicationError` before any user code runs, as does a notification
  configuration that fails `preflight_post`. If notification config breaks
  while the script runs, the child's exit code stays authoritative.

## Source notes

The comment above `ASSIST_BRANCH_ENV` in `src/coga/repl_supervisor.py` still
describes publishing generated task and log commits back to the PR branch.
It is stale: `src/coga/pr_assist.py` and every lifecycle caller publish to
control only.
