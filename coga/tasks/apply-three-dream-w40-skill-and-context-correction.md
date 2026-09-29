---
title: Apply three Dream W40 skill and context corrections after PR 909 lands
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
launch_generation: 3e1a7f13-2b6c-4ad3-a313-8d56712cffec
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). Three stale findings target files that open PR #909 (branch `launch-normalizes-checkout`, "Launch moves the checkout to main before and after a ticket session") is also rewriting, but #909's diff does not carry these fixes. Apply them on top of #909 once it merges (or is closed), keeping live/packaged twins byte-identical.

1. `coga/skills/code/self-qa/SKILL.md` (Dream shard ks-09, class stale): the last Gotcha says state sync "treats every uncommitted `coga/` file as task state" and names contexts and skills. Current `git.sync_coga_state` publishes only dirty paths under the tasks directory, `coga/log.md` and `coga/recurring/`; `coga/internals/state-publication` says contexts, skills, workflows and config are never swept. Narrow the gotcha to recurring templates / `ticket.py` under `coga/recurring/` and link `coga/internals/state-publication` "Pre-review state publication hazard" instead of restating it.
2. `docs/contexts/dev/code/SKILL.md` (shard ca-03, class drift): lines ~40-42 send stored-ticket schema conversions to `coga/sync`, which has no conversion rules; the owner is `coga/internals/git-regressions` "Shipping a stored-ticket schema conversion". Repoint the link (and the packaged twin).
3. `coga/skills/code/implement/SKILL.md` (shard ks-07, class stale; this file is also edited by open PR #912): the skill says "Any `python` works" for `seed_local_config.py`, but the helper (live and packaged) does `import tomllib` at module top, so Python < 3.11 dies before the re-exec fallback runs. Recorded as an unfixed adjacent finding on done ticket `document-how-to-recover-a-retired-ticket-s-body-fr`. Either defer the `tomllib` import until after the re-exec decision, or narrow the claim to 3.11+. This needs a human choice between a code fix and a doc narrowing.

Verification: `python -m pytest tests/test_packaging.py` plus the helper under a 3.9/3.10 interpreter if the code route is chosen.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
