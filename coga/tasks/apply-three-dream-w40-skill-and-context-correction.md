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
launch_generation: 8dd51850-5fc0-43ed-a945-a3e54cc940d5
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). Three stale findings target files that open PR #909 (branch `launch-normalizes-checkout`, "Launch moves the checkout to main before and after a ticket session") is also rewriting, but #909's diff does not carry these fixes. Apply them on top of #909 once it merges (or is closed), keeping live/packaged twins byte-identical.

1. `coga/skills/code/self-qa/SKILL.md` (Dream shard ks-09, class stale): the last Gotcha says state sync "treats every uncommitted `coga/` file as task state" and names contexts and skills. Current `git.sync_coga_state` publishes only dirty paths under the tasks directory, `coga/log.md` and `coga/recurring/`; `coga/internals/state-publication` says contexts, skills, workflows and config are never swept. Narrow the gotcha to recurring templates / `ticket.py` under `coga/recurring/` and link `coga/internals/state-publication` "Pre-review state publication hazard" instead of restating it.
2. `docs/contexts/dev/code/SKILL.md` (shard ca-03, class drift): lines ~40-42 send stored-ticket schema conversions to `coga/sync`, which has no conversion rules; the owner is `coga/internals/git-regressions` "Shipping a stored-ticket schema conversion". Repoint the link (and the packaged twin).
3. `coga/skills/code/implement/SKILL.md` (shard ks-07, class stale; this file is also edited by open PR #912): the skill says "Any `python` works" for `seed_local_config.py`, but the helper (live and packaged) does `import tomllib` at module top, so Python < 3.11 dies before the re-exec fallback runs. Recorded as an unfixed adjacent finding on done ticket `document-how-to-recover-a-retired-ticket-s-body-fr`. Either defer the `tomllib` import until after the re-exec decision, or narrow the claim to 3.11+. This needs a human choice between a code fix and a doc narrowing.

Verification: `python -m pytest tests/test_packaging.py` plus the helper under a 3.9/3.10 interpreter if the code route is chosen.

## Context

<!-- coga:blackboard -->

## Dev

branch: dream-w40-doc-corrections

## Implementation plan (2026-09-29)

- Blocker resolved with `coga unblock`: [PR #909](https://github.com/FastJVM/coga/pull/909)
  merged at 21:27:50 UTC; the owner chose to document Python 3.11+ for
  starting `seed_local_config.py`. Keep the helper code unchanged.
- [PR #912](https://github.com/FastJVM/coga/pull/912) closed without merging
  at 21:28:05 UTC. The current files still need all three corrections.
- Start check passed: `git fetch origin main`, clean `main`, then
  `git merge --ff-only origin/main`. No launch return witness is set;
  return to clean `main` before writing the handoff and bumping.
- Narrow the self-QA gotcha to recurring templates and `ticket.py`, linking
  the publication hazard owner. `src/coga/git.py` plus `sync_coga_state`
  confirms the sweep selects only task, log, and recurring paths.
- Link stored-ticket conversions in `dev/code` to `coga/internals/git-regressions`
  ("Shipping a stored-ticket schema conversion").
- Require Python 3.11+ in `code/implement` and `dev/checkouts`; keep all four
  live/packaged pairs byte-identical. The helper's top-level `tomllib` import
  runs before `_reexec_under_coga_interpreter` can handle a missing Coga import.
- Run packaging and full-suite checks with the existing `.venv/bin/python`
  (Python 3.12.12, test extras available). No Python 3.9/3.10 helper run is
  needed for the selected documentation route. Push the branch; no PR in
  this step.

---

## Blockers

- [x] [2026-09-29 12:32] [agent:claude] id=20260929T123206 Depends on launch-moves-the-checkout-to-main-before-and-after (PR #909 is still open): merge or close #909 before applying these corrections. Owner must also choose the seed_local_config.py route: defer the tomllib import until after the re-exec decision, or narrow the documentation to Python 3.11+.
  resolved: [2026-09-29 14:40] [human:nicktoper] PR #909 merged on 2026-09-29 at 21:27:50 UTC. Owner chose the documentation route: require Python 3.11+ to start seed_local_config.py, preserving the existing helper code and updating both code/implement and dev/checkouts with their packaged twins.
