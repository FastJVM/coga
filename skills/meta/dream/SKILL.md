---
name: meta/dream
description: Use for the periodic repo-wide self-improvement pass. Scan all tickets, blackboards, contexts, skills, and workflows — find knowledge gaps, stale content, and emergent patterns. Write proposals to the task blackboard for a human to review.
---

# Dream — self-improvement pass

You are doing a periodic walk of the entire Relay repo, looking for
things to improve. You are not fixing anything directly — every
suggestion goes to the blackboard as a proposal for a human to review
and accept or reject.

## What to scan

1. **Every ticket** across every project under `<project>/.relay/tasks/`.
   Read `ticket.md`, the body of `blackboard.md`, and the last few log
   entries. Focus on tasks with status `active`, `paused`, `done` within
   the last 30 days, and anything `failed`.
2. **Every context block** under `contexts/`.
3. **Every skill** under `skills/`.
4. **Every workflow** under `workflows/`.

## What to look for

- **Context gaps.** Tickets that reference domain knowledge with no
  matching context block. Patterns that repeat across tickets but are
  not captured anywhere. Findings on blackboards that describe
  durable facts about the world but have not been promoted to a
  context block.
- **Skill gaps.** Workflow steps with no skill, or steps where multiple
  blackboards show agents consistently struggling with the same thing.
- **Workflow gaps.** Groups of tickets that follow the same ad-hoc
  pattern but have no formalized workflow.
- **Stale content.** Context blocks or skills that contradict what
  recent blackboards say. Skills that reference file paths or APIs that
  no longer exist.
- **Stale locks and stuck tasks.** Tasks in `active` status with no log
  activity for 7+ days. Lock files held for more than a few hours.
- **Broken references.** Tickets that reference contexts or skills that
  don't exist. Workflow step `skill:` pointers to missing skills.

## Validation script

Run `cli/scripts/validate.py` (or the moral equivalent) for the
deterministic checks — broken references, stale locks, invalid status
values, required-file completeness. The deterministic output is the
easy part; your job is to interpret it alongside the softer pattern
analysis above.

## Output

Write proposals to this task's blackboard, under Findings and Decisions.
Each proposal must be **concrete**:

- Not: "consider adding context for retry logic"
- But: "create context block `infra/retry-patterns` covering: exponential
  backoff defaults, jitter, 429 handling, Retry-After header. Evidence:
  tickets 003, 011, 014 all rediscovered this."

Post a summary to the Slack feed via `relay feed` when done. The human
reviews the blackboard and accepts or rejects individual proposals by
acting on them directly.

## Boundaries

- Do not create or edit context/skill/workflow files yourself. All
  changes go through human review.
- Do not modify tickets other than writing to this task's blackboard.
- Do not panic unless the repo is in a state you cannot even scan.
