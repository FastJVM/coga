---
slug: stop-trimming-blackboard-but-refuse-to-launch-befo
title: refuse first launch when blackboard needs synthesis
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- coga/architecture
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Change first-launch handling so Coga stops automatically trimming or replacing a
ticket's blackboard at activation time. Instead, if a draft ticket's blackboard
contains substantive authoring/evaluator material at the first launch boundary,
refuse to start and tell the operator to synthesize that material into the
ticket body before work begins.

This is specifically about the common `coga ticket` / evaluator path: evaluators
often fill the blackboard with review notes, but nobody merges those notes back
into `## Description` / `## Context`. Launching from that state gives the
implementer a giant scratchpad instead of a concise source of truth. The fix is
not to delete the scratchpad for them; it is to block the first launch until the
ticket has been made launch-ready.

## Context

Current behavior promotes draft/paused blackboard scratch during activation:
`src/coga/mark.py` calls `promote_to_production_notes`, and
`coga/contexts/coga/architecture/SKILL.md` documents that activation replaces
the whole blackboard unless it already has `## Production notes`. This ticket
should replace that model.

Implementation shape:

- Guard only the first launch/activation boundary: a draft ticket becoming
  active via `coga launch`, and the equivalent `coga mark active` path if that
  would otherwise bypass the guard. Do not block normal relaunches of
  `active` / `in_progress` work, workflow step launches, or post-launch
  blackboard growth.
- Treat the stock placeholder blackboard as empty. Treat substantive authoring
  sections such as `## Evaluator review`, `## Ticket authoring notes`,
  `## Proposals`, or a large non-placeholder blackboard as requiring synthesis
  unless it is explicitly already `## Production notes`.
- Refusal must happen before status changes, workflow freezing, log writes,
  Slack posts, prompt composition, or agent spawn. The ticket must remain a
  draft with its blackboard intact.
- The error message should be actionable: summarize that the blackboard has
  pre-launch notes, ask the operator to merge the important parts into
  `## Description` / `## Context`, and say they may keep durable launch notes
  under `## Production notes` if the blackboard content is intentionally part of
  the run.
- Stop trimming automatically. Remove or retire the activation-time
  blackboard replacement path; do not silently delete evaluator output.
- Update tests around `mark active` / `launch` and update the architecture
  context so the durable explanation matches the new behavior.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Ticket authoring notes

- Set workflow to `code/with-review` and initial assignee to `claude` on 2026-07-01.
- `PYTHONPATH=src python -m coga.cli validate --task stop-trimming-blackboard-but-refuse-to-launch-befo --json` passes with only the expected draft warning: workflow is not frozen until first launch.
- Ticket body now captures the first-launch-only guard, the no-trimming rule, and the source/doc/test touchpoints.

## Dev

- branch: refuse-blackboard-synthesis
- worktree: /tmp/coga-refuse-blackboard-synthesis
- commit: d7dd4e93

## Implementation notes

- Replaced activation-time blackboard replacement with a draft-only prelaunch readiness check.
- `coga mark active` and launch-time auto-activation now refuse draft tickets whose blackboard has known authoring sections (`## Evaluator review`, `## Ticket authoring notes`, `## Proposals`) or a large custom scratchpad, unless the blackboard already has `## Production notes`.
- The refusal happens before workflow freezing, status/log writes, prompt composition, or agent spawn; paused reactivation is left alone as post-launch state.
- Updated the live and packaged `coga/architecture` contexts to describe the new guard.
- Verification in `/tmp/coga-refuse-blackboard-synthesis`: focused `tests/test_blackboard.py tests/test_mark.py tests/test_launch.py` passed (`111 passed`), full `python -m pytest` passed (`992 passed, 1 skipped`), and task-scoped validation passed with only the branch-copy unfrozen-workflow warning.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":5101184,"cli":"codex","input_tokens":181233,"model":"gpt-5.5","output_tokens":22207,"provider":"openai","schema":1,"session_id":"019f210d-20b0-7e00-893a-153b9d40c324","slug":"stop-trimming-blackboard-but-refuse-to-launch-befo","step":"implement","title":"refuse first launch when blackboard needs synthesis","ts":"2026-07-02T04:28:43.901706Z","usage_status":"ok"}
