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

## Implementation preflight (2026-09-29)

- Start check passed: `git fetch origin main`, clean `main`, and
  `git merge --ff-only origin/main` (already up to date). No feature branch
  or implementation changes were made; tests have not run.
- GitHub confirms [PR #909](https://github.com/FastJVM/coga/pull/909) is
  still **OPEN**, with no merge or close timestamp. Its owning task is
  `launch-moves-the-checkout-to-main-before-and-after`
  (`coga/tasks/launch-moves-the-checkout-to-main-before-and-after.md`). The
  description explicitly requires waiting for that PR to merge or close.
- [PR #912](https://github.com/FastJVM/coga/pull/912) is also **OPEN**.
  Recheck its overlap with `code/implement` when resuming; it is not an
  additional prerequisite stated by this ticket.
- The three findings remain present on `main`: `code/self-qa` still claims
  every uncommitted `coga/` file is swept; `dev/code` still links stored-ticket
  conversions to `coga/sync`; and `code/implement` still says any `python`
  works. `src/coga/git.py` plus `sync_coga_state` selects only the configured
  task, log, and recurring paths, confirming the first correction's scope.
- `coga/skills/code/implement/seed_local_config.py` imports `tomllib` before
  the guarded `coga.config` import that calls `_reexec_under_coga_interpreter`.
  The referenced done ticket records this as unfixed; no human choice between
  deferring that import and documenting Python 3.11+ is recorded here.
- Related wording to keep consistent after that choice: `dev/checkouts`
  ("What a fresh checkout lacks") also says any `python` may run the helper.
  Update it and its packaged twin if the documentation route is selected.

Resume after #909 merges or closes and the owner chooses the helper route.
Refresh the overlapping files, apply the three corrections with their twins
under `src/coga/resources/templates/coga/bootstrap/`, and run the prescribed
packaging/full-suite checks (plus a real Python 3.9/3.10 helper check for the
code route). Do not advance `implement` while these prerequisites remain open.

---

## Blockers

- [x] [2026-09-29 12:32] [agent:claude] id=20260929T123206 Depends on launch-moves-the-checkout-to-main-before-and-after (PR #909 is still open): merge or close #909 before applying these corrections. Owner must also choose the seed_local_config.py route: defer the tomllib import until after the re-exec decision, or narrow the documentation to Python 3.11+.
  resolved: [2026-09-29 14:40] [human:nicktoper] PR #909 merged on 2026-09-29 at 21:27:50 UTC. Owner chose the documentation route: require Python 3.11+ to start seed_local_config.py, preserving the existing helper code and updating both code/implement and dev/checkouts with their packaged twins.
