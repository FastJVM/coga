---
title: Surface a chat-end log line that was written but never published
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
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
agent: claude
launch_generation: 3af31713-152e-4fcd-bd1a-23fc3cd931eb
---

## Description

On 2026-10-08 a `coga chat` (bootstrap/orient, session 9b6ffa69-cc90-4fbc-9e26-ef2d0b7ebf33) in the multiply repo ended and appended its usage line to `coga/log.md`, but the line was never committed or pushed. The checkout sat with that uncommitted edit for two weeks, unnoticed, until `coga recurring --all` on 2026-10-22 could not fast-forward `main` over it (372 commits behind). It was repaired by hand by re-appending the line on current main (multiply commit daccdc5b). Find why the chat-end publication left the line unpublished without failing loudly (the line was written 2026-10-08 11:40:41 -0700, at session end), make that path either publish the line or report the failure at the end of the chat, and consider whether recurring or launch should detect and offer to recover a stranded CLI-written `log.md` tail rather than refusing the clone outright.

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

<!-- coga:blackboard -->

## Dev

branch: codex/chat-end-log-publication

## Investigation and plan

- Started on clean `main`, fetched and fast-forward checked against `origin/main`.
- Confirmed multiply repair commit `daccdc5b7c6507ba7b93f920dd239dc67ea48b9c`
  via GitHub: it re-appends the session's 2026-10-08 18:40:41Z usage record.
  The record was captured after the agent's final claim that its work was pushed.
- Both current `src/coga/launch.py` `spawn_agent_session` and its October 8
  predecessor in `src/coga/commands/launch.py` call `git.sync_log` after capture.
  The predecessor was checked at `93b1df8cfb5abab190952ef04ab3f1012643602c`.
  This was not a missing teardown call. The original supervisor stderr and
  installed version are unavailable; the exact historical Git failure is unknown.
- `src/coga/git.py` `sync_log` collapses unchanged, skipped, and failed publication
  to `False`, which the session caller ignores. It also does not require the log
  to be included, so an excluded log can silently look like a successful no-op.
  Add a required-log check and an explicit session-end failure summary, with
  regression coverage for successful, rejected, skipped, and excluded publication.
- Evaluate stranded-tail recovery through the existing strict `publish-state`
  recipe. Avoid automatic broad publication at recurring admission: a log-shaped
  line alone does not prove CLI ownership, and the recipe sweeps other Coga edits.
  Document the recovery and verify concurrent remote/local log lines survive.

## Implementation progress

- Reproduced the silent excluded-log case before changing production code:
  a Git-ignored, untracked log was written but `sync_log` returned `False`
  without a diagnostic. The focused pre-fix run had 6 failures and 4 passes.
  This demonstrates a real publication gap, not proof of the October 8 trigger.
- `git.sync_log` now requires the log and returns `None` for failure/skip,
  distinct from an already-published `False`. `launch.spawn_agent_session`
  summarizes an unconfirmed publication at session end without changing the
  agent's exit result; explicitly disabled Git remains informational.
- `recurring_runner._sync_control_checkout_ahead` now offers the strict
  recovery command for an isolated unstaged log tail on behind control.
  Admission still preserves state and refuses; recovery is never automatic.
- User contracts updated with their packaged twins; internal wrapper return
  semantics updated in `coga-dev/internals/state-publication/publish`.
- No task-layout, prompt-composition, workflow, or validation behavior changes;
  seeded fixture edits and `coga validate --json` are not applicable.

## Verification before reconciliation

- Interpreter: Python 3.12.12 from `.venv/bin/python`. Actual implementer:
  Codex (GPT-6 session), despite the ticket's configured `agent: claude`.
- Regression-first command:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_git.py tests/test_launch.py tests/test_recurring.py -k 'sync_log or spawn_reports_unpublished_session_log or pre_scan_catch_up_offers_recovery' -q`
  failed as expected before the fix (6 failed, 4 passed, 959 deselected), then
  passed after the initial fix (10 passed, 959 deselected).
- Intermediate affected-suite command:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_git.py tests/test_launch.py tests/test_recurring.py tests/test_publish_state.py tests/test_packaging.py -q`
  returned 1011 passed. This preceded the final mode/partial-line guard coverage
  and preservation of nonzero agent results; final verification follows below.
- Full suite:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest -q`
  returned **4001 passed, 7 skipped** (351.77 s) on implementation commit
  `8eff4292a042d65b2940bf9f17a823f81233987e`, merge base
  `878308c9b062bc158c023635cb18074f7b85ce81`. It began on uncommitted implementation
  bytes, which were committed unchanged during the run: `git diff --quiet HEAD --
  src tests docs` succeeded; only this live ticket remained dirty.
- `git diff --check` and `cmp` of both edited canonical/package topic pairs passed.
- Python 3.11.15 is present but has no pytest (`python3.11 -m pytest --version`
  reports `No module named pytest`); no 3.11 test claim is made.
- Current upstream drift is only `coga/log.md` and another ticket. Rebase and
  fresh affected-suite verification remain before push/handoff. No PR opened;
  independent review belongs to the next workflow step.
