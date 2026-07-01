---
slug: remove-relay-migration-script
title: remove relay migration script
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
step: 3 (open-pr)
---

## Description



## Context

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.

## Implement notes

- Ticket body is empty beyond the title. Current frozen workflow is `code/with-review` at step 1 (`implement`), so workflow is present, but implementation scope is underspecified.
- Candidate target found: root `migrate-to-coga.sh`.
- Live references that would become stale if the script is removed:
  - `docs/migrating-to-coga.md`
  - `coga/workflows/coga/cutover.md`
  - draft follow-up ticket `coga/tasks/coga-rename-follow-ups-post-repo-rename.md`
- Relevant posture context: `coga/contexts/coga/project-stage/SKILL.md` says no migration scripts for ticket frontmatter; edit the few existing tickets by hand.
- Human confirmed scope: delete `migrate-to-coga.sh`, replace docs/workflow/task references with manual migration guidance, and leave historical `relay` mentions alone.

## Dev

branch: drop-relay-migration-script
worktree: /tmp/coga-drop-relay-migration-script
commit: 6fe9f49b Remove relay migration script

## Result

- Deleted root `migrate-to-coga.sh`.
- Replaced the host-repo migration script instructions in `docs/migrating-to-coga.md` with a manual checklist.
- Updated `coga/workflows/coga/cutover.md` and draft task `coga/tasks/coga-rename-follow-ups-post-repo-rename.md` so they no longer point at a migration script.
- Verification:
  - `PYTHONPATH=/tmp/coga-drop-relay-migration-script/src python -m pytest` — 935 passed, 1 skipped.
  - `PYTHONPATH=/tmp/coga-drop-relay-migration-script/src python -m coga.cli validate --task remove-relay-migration-script --json` — passed.
  - `git diff --check` — passed.

## Peer review

- Ran `codex review --base main` from `/tmp/coga-drop-relay-migration-script`.
- Review found one must-fix: the manual checklist replaced ticket frontmatter refs but omitted workflow definition frontmatter refs, which the deleted script previously swept.
- Applied fix in `docs/migrating-to-coga.md`: manual migration now says to update markdown YAML frontmatter refs in tickets and workflow definitions.
- Peer-review commit: `4e558620 peer-review: clarify workflow ref migration`.
- Verification after fix:
  - `PYTHONPATH=/tmp/coga-drop-relay-migration-script/src python -m coga.cli validate --task remove-relay-migration-script --json` — passed.
  - `git diff --check` — passed.
  - `PYTHONPATH=/tmp/coga-drop-relay-migration-script/src python -m pytest` — 935 passed, 1 skipped.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1186176,"cli":"codex","input_tokens":174855,"model":"gpt-5.5","output_tokens":6056,"provider":"openai","schema":1,"session_id":"019f1bcd-3f15-7173-bee8-b40a6e2a0464","slug":"remove-relay-migration-script","step":"peer-review","title":"remove relay migration script","ts":"2026-07-01T03:59:34.691411Z","usage_status":"ok"}
