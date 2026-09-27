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

**Additional report from Zach (relayed by owner, 2026-09-27):** the Codex
window stays open and the next step never starts. Zach relayed Claude's
explanation that the completion signal goes to an old session instead of the
current one, and is trying `--no-daemon` in his side-projects repo. No result
from that experiment has been reported. This is a second observed failure
shape alongside the exiting session above; establish which occurs in each
reproduction rather than assuming they have the same cause.

## Context

**Expected contract** (from `coga/launch`, attached, section "The step
chain"): after a clean exit, the supervisor rereads the ticket and continues
when the task is still `in_progress`, the step advanced, and the next operator
is an agent. `agent` and `other-agent` rotate CLIs. The observed behavior
breaks this. Megalaunch (`docs/contexts/coga/megalaunch/SKILL.md`, cited not
attached) says a task chains through at most 8 agent steps per run, and an
exit that changes neither step nor status is `failed`.

**Codex daemon hypothesis — plausible, not confirmed:** the installed
`codex --help` documents `--no-daemon` as "Run without the shared background
server, even if it is already running." This is Codex's shared server, not a
Coga daemon. Coga's `run_with_done_marker` creates a fresh sentinel path and
exports it as `COGA_DONE_SENTINEL` in the child environment. `coga bump` calls
`emit_done_marker` to write the ticket's `id_slug` there; the supervisor polls
its own path and accepts matching content. If command execution through the
shared server retains an earlier launch's environment, bump could write to an
old path and leave the current supervisor waiting. Code inspection establishes
the Coga mechanism, but does not establish that Codex retains that environment.

To test this hypothesis:
- Record the Codex version and launch arguments, then compare the sentinel
  path supplied by the current supervisor with `COGA_DONE_SENTINEL` seen by a
  shell command inside the launched Codex session. Inspect only the relevant
  variable, not the full environment, which may contain credentials.
- Observe which file bump writes, its ticket-slug content, and whether the
  current supervisor detects it. Distinguish a wrong or missing environment
  value from a write failure or a later chain-decision failure.
- Compare equivalent launches with the shared server and `--no-daemon`,
  including consecutive steps/launches where stale environment could matter.
  Record whether the window closes and the next agent starts in each case.
- Treat `--no-daemon` as an experiment or workaround until verified. If it
  restores chaining, identify the environment mismatch or other mechanism
  before choosing the durable fix, and pin the confirmed failure with a
  regression test. Do not assume this explains the separate megalaunch report.

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
