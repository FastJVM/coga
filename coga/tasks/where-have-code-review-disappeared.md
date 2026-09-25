---
title: where have code review disappeared?
status: draft
owner: nicktoper
agent: claude
workflow: code/with-review
contexts:
  - coga/launch
---

## Description

The peer code review by the other agent has stopped happening. The owner saw
this under both `coga launch` and `coga megalaunch`. When the implementing
agent runs `coga bump` at the end of `implement`, the agent session just
exits. The supervisor doesn't start the peer agent (claude → codex, or the
reverse) as a fresh process for the `peer-review` step, so the review never
runs. Megalaunch also appears to advance only one step per ticket and not
chain through the workflow's agent steps. Find out why the chain stops, fix
it, and pin it with a regression test.

Second part: audit every workflow (bundled ones under
`src/coga/resources/templates/coga/bootstrap/workflows/` and repo-local ones
under `coga/workflows/`) and make sure every code-producing workflow runs its
review with the other agent (`assignee: other-agent`), or document why one
intentionally doesn't.

Done when a `code/with-review` ticket launched with `coga launch` goes from
`implement` → bump → a fresh peer-agent process on `peer-review` → bump → the
main agent on `open-pr`, with no manual relaunch. Megalaunch must chain the
same way, up to its 8-step cap. A test must fail on today's behavior and pass
after the fix. The workflow audit's result must be recorded on the blackboard,
and any workflow changed to use `other-agent` must have its packaged twin and
live copy kept in sync.

## Context

**Expected contract** (from `coga/launch`, attached, section "The step
chain"): after a clean exit, the supervisor rereads the ticket and continues
when the task is still `in_progress`, the step advanced, and the next operator
is an agent. `agent` and `other-agent` rotate CLIs. The observed behavior
breaks this. Megalaunch (`docs/contexts/coga/megalaunch/SKILL.md`, cited not
attached) says a task chains through at most 8 agent steps per run, and an
exit that changes neither step nor status is `failed`.

**Code to start from:**
- `repl_supervisor.run_with_done_marker` and `repl_supervisor._classify_exit`:
  the PTY watcher and done-sentinel release that decide how a session ended.
  Check whether a bump-triggered exit is classified as a clean, progressing
  exit.
- `megalaunch._chain_stop_result`: the decision to stop or continue after an
  agent step. The `coga launch` chain decision lives in the launch command
  path and uses the same kind of check. Compare the two.
- `bump.resolve_other_agent` / `bump.resolve_main_agent`: turn the step's role
  token into a concrete agent. `coga/coga.toml` defines exactly two agents
  (`claude`, `codex`), so `other-agent` should infer the peer.
- Recent commits that touched this path are good places to bisect:
  `Simplify git sync (#848)`, `Scrub 1Password auth from launched task
  environments (#879)`, `Detect stranded ticket writes across checkouts
  (#850)`, and `Preserve edits during released claim recovery (#842)`. A
  sync change that makes the supervisor reread a stale ticket copy, and so
  see "no progress", would produce exactly this symptom.

**Lead for the audit, found while authoring:** `code/with-self-review` routes
every step to `assignee: agent` (implement → self-qa → pr → review), so it
never involves the other agent by design. The ticket on the current branch
(`run-the-landed-branch-sweep-daily-from-autoclose`) uses it. Some "missing
review" may come from tickets being authored with that workflow, not only from
the chain bug. Decide with the owner whether `with-self-review` should stay as
a deliberate lighter option or gain an `other-agent` step. Also check which
workflow `bootstrap/ticket` steers toward. Current bundled step owners:
`code/with-review` and `docs/with-review` run `peer-review` as other-agent;
`code/design-then-implement` runs only `evaluate-design` as other-agent and
has no code review after `implement`; `code/with-self-review` has no
other-agent step.

**Dogfooding caveat:** this ticket runs on `code/with-review`, the path it is
fixing. Expect to relaunch `peer-review` by hand (`coga launch <slug>`) if the
chain still breaks.

**Twins:** any change to a bundled workflow must keep
`src/coga/resources/templates/coga/bootstrap/workflows/<path>` and
`coga/workflows/<path>` byte-identical where both exist
(`tests/test_packaging.py`). If the chain contract itself changes, update
`docs/contexts/coga/launch/SKILL.md` in the same PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
