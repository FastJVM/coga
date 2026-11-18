---
title: Stop megalaunch when an agent fails to start
status: blocked
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
---

## Description

On 2026-11-14, `coga megalaunch --pick` launched v1/microkernel/06 and 07 with codex. Each agent exited with code 1 within about 4 s ('Error loading configuration: default_permissions requires a `[permissions]` table', caused by a stray repo-local `.codex/config.toml`). Megalaunch logged `outcome_status: failed` for each, left both tickets `in_progress` with no agent work behind them, and went on to the next pick (08 was activated before the run was interrupted). Getting them back took `coga mark paused` then `coga mark active`, and 08 could not go back to `draft`.

Wanted: when a launched agent process exits non-zero before doing any work, megalaunch stops the whole run instead of moving on to the next task, in every megalaunch loop (bare sweep, dependency drain, and explicit `--pick`/`--relaunch` selection), and restores the failed ticket to its pre-launch status (for example `active`, or `draft` for a pick megalaunch itself activated). The ticket is not marked `blocked`: an agent that cannot start is a Coga/environment problem, not a problem with the ticket, so no ask is recorded against it. The summary row names the failed-to-start task and the agent's exit code; the agent's own error stays visible on the console above (the PTY does not buffer it, and capturing stderr is out of scope). The operator fixes the environment and runs `coga megalaunch --relaunch`.

Done when: a megalaunch run whose first picked task's agent fails to start (reproducible with a fake agent command that exits 1 immediately) ends after that task with exit 1, launches and activates no later pick, leaves that ticket at its pre-launch status with no live launch claim, and reports the task and exit code in the summary; and an agent that does real work and then exits non-zero still follows today's `failed` path unchanged. Tests cover both cases.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Scope

- Megalaunch only. Single `coga launch` is out of scope: the operator is present and sees the failure, and the owner confirmed it has no equivalent problem.
- Do not fix the codex config itself; the stray `.codex/config.toml` was only the trigger.

### Current contract (read before changing)

- `coga/megalaunch` topic — `src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md` — is edited by this ticket (cited, not attached). Today's rule (Sessions): "an exit that changes neither step nor status is `failed`", and the run keeps going; any `failed` row only makes the final exit 1 (Budget, agent, scope, summary). Explicit selection stage 3 activates each pick only when reached, so the pre-launch status to restore is the one read at that reread (`draft`/`paused`/`blocked`/`active`/`in_progress`). Update the Sessions and summary sections in the same PR to describe the new stop-and-restore rule.
- `coga/launch` topic (`.../contexts/coga/launch/SKILL.md`) owns the per-launch claim and activation; read it, change it only if the shared launch path changes.
- Launch claims and their recovery: `docs/contexts/coga-dev/internals/launch-claims/SKILL.md` (`launch_generation` is megalaunch's session claim). Restoring status must also release the claim and publish like other lifecycle mutations; do not hand-edit frontmatter.

### Code pointers

- `src/coga/megalaunch.py` — the run loop, per-task classification, and summary rows.
- `src/coga/launch.py` — session outcome classification (`_session_outcome_status`) and where `outcome_status = "failed"` is set for usage records; `src/coga/usage.py` holds `OutcomeStatus`.
- PTY supervisor: `src/coga/repl_supervisor.py` (POSIX) and `src/coga/repl_supervisor_nt.py` (Windows) owns the agent process exit.

### Restoring the pre-launch status

There is no existing transition back to `draft`, and none from `in_progress` back to `active`: CLI `mark` only allows `active` from `draft`/`paused`, and activation freezes the workflow snapshot and may add a default `agent:`. Megalaunch already holds the exact pre-activation ticket bytes (the exact-byte preflight/reread). Restore by a compare-and-set write of those exact bytes back, publish it, and log it, so that a draft, paused, blocked, or active pick returns exactly as it was, with any `launch_generation` claim gone. Follow `src/coga/commands/mark.py` as the pattern for publishing a lifecycle mutation with strict compare-and-set; never hand-edit frontmatter. A task that was already `in_progress` before this run resumes to `in_progress` with the run's claim cleared.

### Tests

Reuse the fake-agent patterns in `tests/test_megalaunch.py` and `tests/conftest.py`; the fake must go through the same session spawn path megalaunch uses, so a fake that exits 1 immediately exercises the real failure classification.

### Open design choice for the implementer

Pick the "failed to start" signal and record why on the blackboard. Candidates: non-zero exit with no agent transcript/session id recorded (launch already captures transcript identity for usage; verify it works for both claude and codex), no prompt consumed, or elapsed time under a small threshold. Prefer a structural signal over a pure timer, but keep a short elapsed-time fallback in case the transcript signal is unreliable for one agent; name any threshold as a constant and say why. If stderr capture turns out to be wanted, file it as a separate ticket (a bounded PTY output buffer in both supervisors) rather than growing this one. When restore is impossible (the ticket changed underneath, or publication fails), stop the run anyway and report that the ticket needs manual reconciliation.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: stop-megalaunch-when-an-agent-fails-to-start

## Implement handoff (2026-11-17, claude)

Implemented on the branch (commit b6bf135c8), pushed; no PR yet.

### Failed-to-start signal (design choice)
`megalaunch._agent_failed_to_start`: natural non-zero exit (not crash/signal,
timeout or done teardown), no done signal, ticket byte-identical to the claim
the child ran under (admitted rendering under Git, start write without), AND
`AgentSessionResult.elapsed_seconds < STARTUP_FAILURE_WINDOW_SECONDS` (20 s).
- Structural part = untouched claimed ticket + no done signal. Transcript
  identity was rejected: usage parsing only exists for claude/codex (custom
  CLIs and test fakes have none), returns "not found" mixed with ambiguity and
  parse failures as free-text `usage_status: unknown` reasons, and claude's
  fallback window search means a missing pinned file is not proof. Plumbing a
  reliable "transcript located" bit out of `usage.capture_session` would be a
  bigger shared-core change than this ticket warrants.
- 20 s window: the incident died in ~4 s; the measurement (around
  `run_with_done_marker`) includes held-child proof (control fetch) and the
  admission push, so it needs headroom for a slow network. It keeps an agent
  that worked >20 s without touching its ticket on the ordinary `failed` path.
- A session result that does not report elapsed (`None`) is never classified
  as a failed start (keeps stubbed fakes and any other caller on today's path).

### Restore
`_restore_after_failed_start`: under `git.state_lock`, CAS local == claim,
write the step's pre-launch bytes (selection: deferred-activation capture of
draft/paused/blocked; else the preflight read of active/in_progress), drop
`launch_generation` if present (only re-rendered then), log
`restored (in_progress → X) — agent failed to start (exit N); megalaunch run
stopped`, `sync_task_state(strict, expect={ticket: claim})`. Refused publish →
put claim bytes back + retract log; uncertain → keep local restore; either way
the row says manual reconciliation. Row: outcome `failed`, `stops_run=True`,
detail `agent failed to start (exited with code N); run stopped; restored to X; ...`.
Sweep returns before the drain; drain returns; selection breaks (later picks
never reread/activated). Exit 1 via the existing failed count.
- Drain: pre-launch for a drained ticket is the post-activation `active`
  bytes (dependency answers kept), documented in the topic. Restoring to
  `blocked` would discard a legitimate automatic answer.
- `_as_drained` now uses `dataclasses.replace` so the flag survives.

### Docs
coga/megalaunch Sessions + summary; coga-dev launch-claims (new "Failed agent
start" section, notes the one sanctioned backward compensation);
agent-spawn mentions `elapsed_seconds`.

### Follow-ups / not done
- stderr capture not attempted (out of scope); no ticket filed since nobody
  asked for it yet. Next step may file one if the reviewer wants it.
- Single `coga launch` unchanged by design.

## Peer review

Codex independently completed a direct review of Claude's implementation on
head `8358decdf9a675633c872cf0905af798ed3c1c85` against base `e8e2833d9b186c130aa253ba5483d6726761316b`. The branch was rebased onto current main
and pushed with an explicit lease. The review found a must-fix behavioral
regression that requires revisiting the startup signal.

Linux PTY reproduction used `script -qec` with terminal sizes 80×24 (fake
Claude) and 120×36 (fake Codex). In an isolated Git-disabled fixture, save two
draft picks, run `coga megalaunch --relaunch` (add `--agent codex` for the
Codex case), and decline draft interviews. In the cold case the fake CLI
prints a diagnostic and exits 1. The diagnostic preceded the summary, the
summary named the first pick and exit 1, megalaunch exited 1, and both drafts
were byte-identical to their original state with no claim. In the work case
add a shell write of a separate artifact before exit 1, leaving the ticket
alone. The artifact existed, yet both providers' fake CLIs reproduced the
same startup-failure summary, draft restoration and skipped second pick.
The branch test for work followed by failure edits the blackboard and misses
this case.

The code cannot distinguish these two runs using ticket bytes and elapsed
time. The owner needs to decide the evidence contract for transcriptless
CLIs, where the current observations cannot distinguish startup failure
from work. Claude and Codex have parsed activity evidence worth evaluating
for that decision, and a regression test should exercise work outside the
ticket through the real supervisor. Native Windows and macOS verification
is deferred to release.

## PR

```yaml
title: Stop megalaunch when an agent fails to start
author: claude
author_evidence: >-
  Implement step ran as a Claude Code session (Opus 5.5) launched by coga
  megalaunch; this handoff was written by that session.
head: 8358decdf9a675633c872cf0905af798ed3c1c85
base: e8e2833d9b186c130aa253ba5483d6726761316b
depth: deep
rationale: >-
  Changes megalaunch run control and adds a backward lifecycle compensation
  (restoring a claimed ticket to its pre-launch bytes); the failed-start
  heuristic (untouched ticket plus a 20 s window) is a judgment call worth
  reviewing. Direct review found a reproducible false startup classification
  after real work outside the ticket.
implementation: >-
  AgentSessionResult gains elapsed_seconds measured around the PTY watcher.
  Megalaunch classifies a natural non-zero exit with no done signal, an
  untouched claimed ticket and elapsed under STARTUP_FAILURE_WINDOW_SECONDS as
  a failed start, restores the step's pre-launch bytes by compare-and-set
  without the launch claim, logs and strictly publishes it, and sets
  stops_run so the sweep, drain and selection loops all stop.
deviations: >-
  Transcript identity was not used as the structural signal (see blackboard
  rationale); the untouched claimed ticket is the structural signal instead.
  A drained ticket restores to active, keeping its dependency answer.
limitations: >-
  A failed start slower than 20 s, or one that writes its ticket, keeps the
  old failed-and-continue path. No real claude or codex binary was exercised;
  tests model the PTY watcher. Windows not run (release-only per testing topic).
files:
  src/coga/launch.py: Report the supervised session's elapsed seconds on AgentSessionResult.
  src/coga/megalaunch.py: Detect a failed agent start, restore the ticket, stop every loop.
  tests/test_megalaunch.py: >-
    Cover sweep (active, in_progress), pick of drafts, drain, git publication,
    worked-then-failed and over-window cases.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Document the stop-and-restore rule and summary row.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Document the restore compare-and-set as the one sanctioned backward compensation.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Document elapsed_seconds on AgentSessionResult.
review:
  reviewer: codex
  kind: independent
  status: failed
  head: 8358decdf9a675633c872cf0905af798ed3c1c85
  base: e8e2833d9b186c130aa253ba5483d6726761316b
  detail: >-
    Direct review completed. Real PTY runs reproduced a false failed-to-start
    classification after a child wrote a work artifact and exited 1.
checks:
  - command: .venv/bin/python -m pytest
    status: failed
    head: 8358decdf9a675633c872cf0905af798ed3c1c85
    base: e8e2833d9b186c130aa253ba5483d6726761316b
    detail: >-
      Interrupted at 37% after the PTY regression blocked review. No full-suite result.
  - command: .venv/bin/python -m pytest tests/test_megalaunch.py
    status: passed
    head: 8358decdf9a675633c872cf0905af798ed3c1c85
    base: e8e2833d9b186c130aa253ba5483d6726761316b
    detail: >-
      169 passed on Linux.
  - command: git diff origin/main...HEAD --check
    status: passed
    head: 8358decdf9a675633c872cf0905af798ed3c1c85
    base: e8e2833d9b186c130aa253ba5483d6726761316b
    detail: >-
      No whitespace errors in the reviewed diff.
  - command: >-
      script -qec 'stty rows 24 cols 80; coga megalaunch --relaunch' /dev/null
    status: failed
    head: 8358decdf9a675633c872cf0905af798ed3c1c85
    base: e8e2833d9b186c130aa253ba5483d6726761316b
    detail: >-
      Ran with two draft picks and a fake Claude. The cold exit passed, but
      the fast exit after creating an artifact restored the first draft and
      stopped the run. Repeated at 120×36 with a fake Codex and --agent codex.
```

---

## Blockers

- [ ] [2026-11-17 21:30] [agent:codex] id=20261117T213044 Decide what startup evidence transcriptless agent CLIs must provide, or narrow the guarantee for those CLIs. A real PTY reproduction shows the current 20-second rule rolls back a ticket and stops the queue after an agent creates a work artifact and exits 1 without touching the ticket.
