---
title: where have code review disappeared?
status: in_progress
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
step: 2 (human-owns-and-finishes)
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
  (workflow coverage) and `v1/07-lifecycle-writes-read-control-s-ticket-before-modi`
  (stale-state publication). Retired tickets' blackboards need the recovery
  recipe in `coga/tickets/discovery`; PR bodies need `gh`.
- 2026-09-30: the owner folded the empty stub
  `codex-doesn-t-exist-properly-for-agent-restart` into this ticket.

Previous ref: `where-have-code-review-disappeared` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Peer-review audit (2026-10-23, agent-produces, claude)

**Verdict: 3 of 12 completed reviews were not peer-reviewed (1 more is still
running). Pattern: every one is a ticket whose main agent is `claude` but
whose `implement` ran as `codex` under an override, so `other-agent` routed
review back to `codex`. Every Claude-implemented ticket got a real Codex
review. The routing rule worked as written. The gap is in the rule, which
ignores the override. It is not a routing bug.**

Scope: the 10 most recent `→ peer-review` handoffs in `coga/log.md` (lines
9024–9212) included only 2 implemented by codex, so the window extends back
through line 8907 to reach 3. That gives 13 rows. All are `code/with-review`.
No `docs/with-review` handoff fell in the window. Every ticket has
`agent: claude` (main agent), so the routing rule always picks `codex` as the
peer. "Impl" comes from the `implement` run record's `cli`, and "Reviewer"
from the `peer-review` run record's `cli`.

| # | Ticket | Workflow | Impl | Main | Reviewer | Peer review | Real notes | Chain → peer-review | Evidence (log.md lines) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | windows-native/02-pr-ci-with-linux-and-windows-test-jobs | code/with-review | claude | claude | codex (launched) | **pending** | n/a, review not finished | auto (chain spawn 9214, same minute) | 9212 handoff, 9213 impl run, 9214 |
| 2 | surface-a-chat-end-log-line-that-was-written-but-n | code/with-review | codex | claude | codex | **no** | yes, codex found and fixed 1 must-fix. Blackboard says "recorded as **self-review**" | auto (megalaunch resume 9151–9152) | 9143, 9149, 9150, 9154, 9153 (bump notes "Direct Codex self-review"), 9157 (PR #1090 "disclosed Codex self-review only") |
| 3 | blocks/08-trim-launch-prompt-and-workflow-topics | code/with-review | claude | claude | codex | yes | yes, 2 findings fixed | auto (9134) | 9132, 9133, 9134, 9145, 9144 |
| 4 | keep-the-file-list-when-a-control-fast-forward-ref | code/with-review | codex | claude | codex | **no** | yes, 1 correctness fix. Blackboard says "recorded as **self-review**" | auto (megalaunch 9126–9127) | 9118, 9124, 9125, 9136, 9135 |
| 5 | blocks/09-trim-setup-and-extension-topics | code/with-review | claude | claude | codex | yes | yes, twin/orphan finding fixed | auto (megalaunch 9026–9027) | 9024, 9025, 9029, 9028 |
| 6 | blocks/07-trim-the-tickets-family-and-secrets | code/with-review | claude | claude | codex | yes | yes. Receipt labeled "self-review" because codex also wrote corrections | blocked + manual relaunch (2 runs) | 9007, 9008, 9011 block, 9012, 9109 relaunch, 9120, 9119 |
| 7 | blocks/06-collapse-state-publication-into-one-user-topic | code/with-review | claude | claude | codex | yes | yes. Receipt `kind: self` (same reason) | blocked + manual relaunch (2 runs) | 8998, 8999, 9002 block, 9003, 9067 relaunch, 9098, 9097 |
| 8 | blocks/05-trim-the-notifications-family | code/with-review | claude | claude | codex | yes | yes. Receipt "self-review" (same reason) | blocked + manual relaunch (2 runs) | 8989, 8990, 8993 block, 8994, 9058 relaunch, 9061, 9060 |
| 9 | blocks/04-trim-and-consolidate-the-recurring-family | code/with-review | claude | claude | codex | yes | yes. Receipt "self-review" (same reason) | blocked + manual relaunch (2 runs) | 8980, 8981, 8984 block, 8985, 9049 relaunch, 9052, 9051 |
| 10 | blocks/03-trim-the-checkouts-and-checkout-cleanup-family | code/with-review | claude | claude | codex | yes | yes, "independent review" | blocked + manual relaunch (2 runs) | 8971, 8972, 8975 block, 8976, 9038 relaunch, 9041, 9040 |
| 11 | blocks/02-delete-the-code-topic-and-remove-coga-repo-only | code/with-review | claude | claude | codex | yes | yes, "direct, independent Codex review" | auto (8961) | 8959, 8960, 8961, 8963, 8962 |
| 12 | blocks/01-self-document-coga-toml-and-split-the-agents-to | code/with-review | claude | claude | codex | yes | yes, 1 doc error fixed | auto (8945) | 8943, 8944, 8945, 8947, 8946 |
| 13 | let-the-autofix-generator-attach-repo-default-contexts | code/with-review | codex | claude | codex | **no** | yes, 1 contract gap fixed. Bump says "Self-review complete" | auto (8909) | **8896 `launched (operator=claude, launch_agent=codex, agent=codex)`**, 8907, 8908, 8909, 8912, 8911, PR #1079 |

### Findings

- **Override gap, not a routing bug.** Line 8896 is direct evidence:
  `operator=claude, launch_agent=codex`. Implement ran as a `--agent codex`
  override on a claude-main ticket. As `coga/launch` specifies, the override
  ends at the `other-agent` step, and `other-agent` resolves to claude's peer,
  which is `codex`. The same `operator=claude, launch_agent=codex` →
  `peer-review → codex` shape appears further back, outside the window:
  8847/8859 (context-audiences/02), 8828/8830 (fix-parser-bugs…), and
  8675/8683 (report-of-usage…). The control case is 7908
  (autofix-write-ups…). There, codex implemented and review went to
  `claude`, which is consistent with a codex-main ticket.
- **Megalaunch hides the override.** Rows 2 and 4 were implemented by codex
  through megalaunch, but the log line is only `launched via coga
  megalaunch` (9118, 9143), with no `launch_agent=`. `coga/launch` tells
  readers to get the real CLI from the `launch_agent=` field. These rows have
  none, so the run record's `cli` is the only attribution. I did not
  determine how megalaunch picked codex (a `megalaunch.py` `agent_override`
  or a selection setting).
- **The codex reviewer is honest about it.** All three "no" rows label their
  receipt as self-review on the blackboard. Row 2's PR text also discloses
  it. The PR bodies for rows 4 and 13 were not checked with `gh`.
- **Chain health.** In this window, none of the reviews needed a manual
  relaunch because the chain stopped after `implement`. Each peer-review
  session started in the same minute as the handoff. That was either a
  `coga launch` chain spawn (logged as `[human:…] launched (operator=codex…)`)
  or a megalaunch resume. Rows 6–10 have two run records and a manual
  relaunch, but they come from deliberate `coga block` calls on PR #1081 (a
  cross-ticket dependency), not from a chain stop. The owner's earlier
  "chain stops after implement" report is **not reproduced** in this sample.
- **Receipt label vs. the ticket's rule.** Rows 6–9 count as peer review by
  this ticket's rule because the CLIs differ. Their PR receipts still say
  `self` because codex also authored fixes and rebase resolutions. A reader
  of a PR could undercount peer review.

### Weak spots / assumptions

- "Chain spawn" vs. "manual launch": both write the identical
  `[human:<owner>] launched (operator=…)` line (`launch.py`
  `_launch_log_message`). I classified a launch as a chain spawn when it fell
  in the same minute as the bump, with no preceding `started … via coga
  launch` / `activated` lines. A human relaunch shows those lines (e.g.
  9036–9038).
- `coga/launch` says the `[agent:<name>]` on a lifecycle line credits the
  configured operator under an override. Line 8907 instead shows
  `[agent:codex]` while the operator was claude. The doc and the behavior
  disagree, so the attribution in `advanced` lines is not reliable for
  telling override from main. I used the run-record `cli` instead.
- Row 1 is still in flight (peer-review launched 9214). Its result is not
  in the log yet.
- "Real notes" was judged from each ticket's `## Peer review` blackboard
  section. Every row has concrete findings with commit SHAs.

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
