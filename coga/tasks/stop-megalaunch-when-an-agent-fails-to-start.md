---
title: Stop megalaunch when an agent fails to start
status: done
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
agent: claude
---

## Description

On 2026-11-14, `coga megalaunch --pick` launched v1/microkernel/06 and 07 with codex. Each agent exited with code 1 within about 4 s ('Error loading configuration: default_permissions requires a `[permissions]` table', caused by a stray repo-local `.codex/config.toml`). Megalaunch logged `outcome_status: failed` for each, left both tickets `in_progress` with no agent work behind them, and went on to the next pick (08 was activated before the run was interrupted). Getting them back took `coga mark paused` then `coga mark active`, and 08 could not go back to `draft`.

Wanted: when the POSIX terminal supervisor confirms that the operating system refused to execute the agent command, megalaunch stops the whole run instead of moving on to the next task, in every megalaunch loop (bare sweep, dependency drain, and explicit `--pick`/`--relaunch` selection), and restores the failed ticket to its pre-launch status (for example `active`, or `draft` for a pick megalaunch itself activated). The ticket is not marked `blocked`: an agent that cannot start is a Coga/environment problem, not a problem with the ticket, so no ask is recorded against it. The summary row names the failed-to-start task and the agent's exit code; the agent's own error stays visible on the console above (the PTY does not buffer it, and capturing stderr is out of scope). The operator fixes the environment and runs `coga megalaunch --relaunch`.

Done when: a megalaunch run whose first picked agent cannot execute (reproducible with an executable script whose interpreter is missing) ends after that task with exit 1, launches and activates no later pick, leaves that ticket at its pre-launch status with no live launch claim, and reports the task and exit code in the summary; and an agent that does real work and then exits non-zero still follows today's `failed` path unchanged. Tests cover both cases. The owner approved this narrower guarantee after the review. An agent that executes and then exits nonzero, including the reported Codex configuration refusal, continues through the ordinary failed path. Supervisors without confirmed execution-failure evidence retain the existing behavior.

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

Use the real POSIX supervisor with a fake agent executable whose interpreter is missing.
Reproduce an ordinary failed run with a fake CLI that writes a separate work
artifact and then exits nonzero while leaving the ticket alone.

### Startup evidence

The POSIX PTY child reports an OS execution failure before the agent can run.
An ordinary exit code, elapsed time, or missing transcript alone cannot
establish that no work occurred. When restoration is unavailable or
publication fails, stop the queue and report that the ticket needs manual
reconciliation.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1253
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

Codex completed a direct review of the final diff on head `948d8c88430f083d91209eae0a559736e33cb37c` against
base `96f680ad78b6149e4ff39b5638330b9024d8a2cf`. Claude authored the original change. Codex authored the
review fixes and self-reviewed them, so the final diff has mixed authorship
and no independent review of those fixes. The owner accepted the limited
guarantee for a rare failure. The review replaced the timing heuristic with
the POSIX supervisor's explicit execution-failure observation. The admitted
bytes come from the admission write, so a subsequent ticket edit cannot
become the rollback baseline. The earlier outside-ticket work regression
is resolved.

Re-ran `coga megalaunch --relaunch` under Linux PTYs at 80×24 with a fake
Claude executable whose interpreter was missing, and 120×36 with a fake
Codex that wrote a separate artifact and exited 1. The first displayed
the OS diagnostic above the summary, restored the first draft byte for
byte, kept the second draft untouched, and exited 1. The second attempted
both picks, reported both ordinary failures and preserved the work
artifact. Automated tests also distinguish a real execution failure from
a working CLI that exits 127. Native Windows and macOS verification is
deferred to release.

## PR

```yaml
title: Stop megalaunch on confirmed agent execution failure
author: claude-codex
author_evidence: Claude Code (Opus 5.5) wrote the initial implementation. Codex wrote the
  startup-evidence and recovery fixes during peer review.
head: 948d8c88430f083d91209eae0a559736e33cb37c
base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
depth: deep
rationale: Changes queue control and introduces a backward compensation for an admitted
  ticket. The owner approved requiring confirmed execution failure, and the reviewer authored
  the final fix.
implementation: The POSIX PTY supervisor records an OS execution failure separately from
  the exit code. Megalaunch stops any queue loop on that observation, atomically restores
  the pre-launch bytes with the generation cleared by compare-and-set, and publishes the
  result strictly. Restoration failures stop the queue and report that manual reconciliation
  is needed.
deviations: Uses positive OS execution-failure evidence in place of the original timing
  heuristic. The original Codex configuration error still follows the ordinary failed path.
  A drained ticket restores to active and keeps its dependency answer.
limitations: The positive signal is available on the POSIX PTY path. Native Windows and
  macOS verification is deferred to release. Terminal checks used fake executables. Linux
  checks use Python 3.12.12 and do not establish the Python 3.11 floor.
files:
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Document transport of the OS execution-failure
    observation.
  docs/contexts/coga-dev/internals/launch-claims/SKILL.md: Document the guarded claim compensation
    and publication recovery.
  src/coga/launch.py: Carry the supervisor observation through the session result.
  src/coga/megalaunch.py: Stop every queue loop and compensate the claim using its exact
    admitted bytes.
  src/coga/repl_supervisor.py: Identify failure of exec separately from a CLI exit with
    the same code.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md: Specify
    when the run stops and what the operator sees.
  tests/test_megalaunch.py: Exercise sweep, drain, picks, Git publication and real PTY evidence.
    The POSIX PTY test is excluded on Windows because the Windows supervisor does not emit
    the signal.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 948d8c88430f083d91209eae0a559736e33cb37c
  base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
  detail: Direct review of the final diff completed. Codex independently reviewed Claude's
    original diff, identified the regression, and implemented and self-reviewed the final
    fixes. Linux PTY checks verified both the stop and continue paths.
checks:
- command: TMPDIR=/home/n/Code/coga-test-tmp.pNzcsj .venv/bin/python -m pytest
  status: passed
  head: 948d8c88430f083d91209eae0a559736e33cb37c
  base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. 4991 passed, 33 skipped in 893.27 seconds.
    No failures.
- command: .venv/bin/python -m pytest tests/test_megalaunch.py -k 'posix_pty_distinguishes
    or fails_to_start or restores_draft or failed_start or pending_claim_blocks_remote_lifecycle'
    -q
  status: passed
  head: 948d8c88430f083d91209eae0a559736e33cb37c
  base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. Nine focused tests passed.
- command: .venv/bin/python /tmp/coga-stop-megalaunch-terminal.py
  status: passed
  head: 948d8c88430f083d91209eae0a559736e33cb37c
  base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. The harness drove script -qec with a real terminal
    at 80×24 and 120×36. Both expected queue and ticket outcomes passed.
- command: git diff origin/main...HEAD --check
  status: passed
  head: 948d8c88430f083d91209eae0a559736e33cb37c
  base: 96f680ad78b6149e4ff39b5638330b9024d8a2cf
  detail: No whitespace errors in the reviewed diff.
```

## Blockers

- [x] [2026-11-17 21:30] [agent:codex] id=20261117T213044 Decide what startup evidence transcriptless agent CLIs must provide, or narrow the guarantee for those CLIs. A real PTY reproduction shows the current 20-second rule rolls back a ticket and stops the queue after an agent creates a work artifact and exits 1 without touching the ticket.
  resolved: [2026-11-17 22:06] [human:nicktoper] Require positive startup-failure evidence before restoring the ticket and stopping the queue. An ambiguous nonzero exit, including one from a transcriptless CLI without explicit evidence, follows the existing failed path.
