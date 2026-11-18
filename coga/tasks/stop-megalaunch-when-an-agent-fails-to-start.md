---
title: Stop megalaunch when an agent fails to start
status: in_progress
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
step: 1 (implement)
agent: claude
launch_generation: c91709af-7198-40a4-abd3-dd75ccbee9e8
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
