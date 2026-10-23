---
title: where have code review disappeared?
status: active
owner: nicktoper
agent: claude
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
---

## Description

Check that peer code review by the other agent is still happening. The owner
expects no problem but wants evidence. Take the 10 most recent handoffs into
a `peer-review` step (`code/with-review` or `docs/with-review`), ordered by the
handoff line in `coga/log.md`. If fewer than 3 of those 10 were implemented by
`codex`, extend further back until at least 3 are, and say so. For each,
record the implementing agent, the main agent, the agent that ran
`peer-review`, and whether the review produced real review notes from that
agent. Also note whether the chain reached `peer-review` on its own or needed
a manual relaunch: two or more peer-review run records, or a manual `launch`
line, between the handoff and the next bump.

Write the result to this ticket's blackboard as a table (ticket, workflow,
implementer, reviewer, peer review yes/no, evidence line refs) plus a one-line
verdict: "all peer-reviewed by the other agent" or "N were not, and here is
the pattern". A review counts as peer review only when the reviewing CLI
differs from the implementing CLI. If that disagrees with the routing rule
below, say which one is broken. Do not fix anything. The owner decides the next step
from the table.

## Context

- **Routing rule** (from `coga/launch`, "The step chain", cited not
  attached): a step with `assignee: other-agent` runs the *main agent's*
  configured peer. `coga.toml` defines exactly two agents, `claude` and
  `codex`. This differs from "opposite of the implementer" when `implement`
  ran under a `--agent` override: if the main agent is `claude` but `codex`
  implemented, the routing rule still sends review to `codex`. Record both so
  the owner can tell a routing bug from an override gap.
- `code/design-then-implement` is out: its `other-agent` step is
  `evaluate-design`, a design review, and its code goes straight to `open-pr`.
- **Evidence sources:** `coga/log.md` lines of the form
  `[<slug>] [agent:<x>] advanced to step N (peer-review) → <y>` (the
  handoff), the following `[system] {...}` JSON run record for
  `"step":"peer-review"` (`cli`, `outcome`), the ticket blackboard (done
  tickets may be retired; `coga/tickets/discovery` has the recovery recipe),
  and the PR body. `code/with-self-review` tickets never involve the other
  agent by design, so leave them out of the 10.
- **Lead to check, not a conclusion:** while authoring, two recent log lines
  showed the reviewer equal to the implementer:
  `[keep-the-file-list-when-a-control-fast-forward-ref] [agent:codex] advanced to step 2 (peer-review) → codex`
  and the same for `surface-a-chat-end-log-line-that-was-written-but-n`.
  Their run outcomes say "self-review". In `surface-a-chat-end-…` the later
  `open-pr` step went to `claude`, which suggests `claude` was the main agent
  and `codex` implemented under an override. The cold review found more
  codex→codex handoffs further back in the log. Claude-implemented tickets
  (`blocks/0x-*`) went to `codex` as expected. Expect at least some "not
  peer-reviewed" rows.
- The owner also reported earlier that the chain sometimes stops after the
  `implement` bump (and, from Zach, that a Codex window stays open). If the
  table shows a manual relaunch on the review step, flag it. The earlier
  fix-oriented scope for that is archived under the blackboard's
  "Superseded designs" for reuse.
- Related tickets: `make-every-code-workflow-review-with-the-other-age`
  (workflow coverage) and `lifecycle-writes-read-control-s-ticket-before-modi`
  (stale-state publication). Retired tickets' blackboards need the recovery
  recipe in `coga/tickets/discovery`; PR bodies need `gh`.
- 2026-09-30: the owner folded the empty stub
  `codex-doesn-t-exist-properly-for-agent-restart` into this ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-10-23 — fix-the-chain scope replaced by an audit

The owner reframed the ticket as an audit of the last 10 peer reviews and
expects no problem. The original investigation-and-fix scope is kept below in
case the audit finds one.

### Description (superseded)

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

### Context (superseded)

**Consolidated `codex-doesn-t-exist-properly-for-agent-restart`
(2026-09-30, owner approved).** That title-only stub carried no additional
description, evidence, or acceptance criteria. This ticket owns its Codex
session-exit/restart concern through the two observed failure shapes above:
an exiting session that fails to hand off, and a window that stays open after
the step completes. Confirm the mechanism for each; consolidation is not
evidence that they share a root cause.

Sandboxed publication recovery is owned by
`lifecycle-writes-read-control-s-ticket-before-modi`, which absorbs
`ticket-sync-fails-with-read-only-git-inside-agent`. Coordinate any stale-state
chain finding with that ticket rather than implementing a second publication
retry here. Workflow review coverage remains separately owned by
`make-every-code-workflow-review-with-the-other-age`.

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
