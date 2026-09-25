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

Done when a `code/with-review` ticket launched with `coga launch` goes from
`implement` → bump → a fresh peer-agent process on `peer-review` → bump → the
main agent on `open-pr`, with no manual relaunch. Megalaunch must chain the
same way, up to its 8-step cap. A test must fail on today's behavior and pass
after the fix.

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
  agent step. The `coga launch` chain decision is the `while True:` chain
  loop inside `commands.launch._launch` (the block commented "Agent launches
  chain across consecutive agent-owned steps"). Compare the two.
- `bump.resolve_other_agent` / `bump.resolve_main_agent`: turn the step's role
  token into a concrete agent. `coga/coga.toml` defines exactly two agents
  (`claude`, `codex`), so `other-agent` should infer the peer.
- Recent commits that touched this path are good places to bisect:
  `Simplify git sync (#848)`, `Scrub 1Password auth from launched task
  environments (#879)`, `Detect stranded ticket writes across checkouts
  (#850)`, and `Preserve edits during released claim recovery (#842)`. A
  sync change that makes the supervisor reread a stale ticket copy, and so
  see "no progress", would produce exactly this symptom.

**Rule out the non-bug first.** `code/with-self-review` routes implement →
self-qa → pr to `agent` and `review` to `owner`, so it never involves the other
agent by design. The ticket on the current branch
(`run-the-landed-branch-sweep-daily-from-autoclose`) uses it. Before fixing
anything, look at a recent run record under `.coga/` for a `code/with-review`
or `code/design-then-implement` ticket and confirm the chain really stopped
after an `agent` → `other-agent` bump. Possible causes: a stale ticket reread
(the #848 sync theory), `_classify_exit` misclassifying the bump exit, or peer
resolution returning the same agent (in which case the fix belongs in `bump`,
not the supervisor). Megalaunch advancing only one step may have a separate
cause, so don't assume one fix covers both. Whether workflows *should* all have
an other-agent review is out of scope here. See
`make-every-code-workflow-review-with-the-other-age`.

**Dogfooding caveat:** this ticket runs on `code/with-review`, the path it is
fixing. Expect to relaunch `peer-review` by hand (`coga launch <slug>`) if the
chain still breaks.

**Topic update:** If the chain contract itself changes, update
`docs/contexts/coga/launch/SKILL.md` in the same PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
