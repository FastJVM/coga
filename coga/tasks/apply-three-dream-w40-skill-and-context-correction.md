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
step: 3 (open-pr)
agent: claude
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

pr: https://github.com/FastJVM/coga/pull/933
branch: dream-w40-doc-corrections

## Implementation handoff (2026-09-29)

- Blocker resolved with `coga unblock`: [PR #909](https://github.com/FastJVM/coga/pull/909)
  merged at 21:27:50 UTC; the owner chose to document Python 3.11+ for
  starting `seed_local_config.py`. The helper code is unchanged.
- [PR #912](https://github.com/FastJVM/coga/pull/912) closed without merging
  at 21:28:05 UTC, so there was no pending overlap to preserve.
- Pushed commit `846685a7a` on `dream-w40-doc-corrections`, rebased onto
  `origin/main` at `7d7607bfd`. The eight-file diff changes only the four
  documents below and their byte-identical packaged twins.
- `code/self-qa`: narrowed the gotcha to recurring templates and `ticket.py`
  under `coga/recurring/`, linking the publication owner's "Pre-review state
  publication hazard" instead of repeating it. `src/coga/git.py` plus
  `sync_coga_state` confirms the task/log/recurring sweep boundary.
- `dev/code`: linked stored-ticket conversions directly to
  `coga/internals/git-regressions`, "Shipping a stored-ticket schema conversion".
- `code/implement` and `dev/checkouts`: require Python 3.11+ to start the
  helper, preserving the documented re-exec when Coga cannot be imported.
  `dev/checkouts` explains that `tomllib` imports before the fallback.
- Verification (Python 3.12.12):
  - `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_packaging.py`
    — 23 passed, including a final run on commit `846685a7a`.
  - `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` — 3,110 passed after
    rebasing onto `1afee0a21` (earlier runs also passed all 3,107 tests).
  - Further upstream merges changed docs and an autoclose message/test;
    `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_packaging.py tests/test_autoclose.py tests/test_autoclose_dispose.py tests/test_autoclose_sweep.py tests/test_retro_skill_template.py tests/test_seed_local_config.py tests/test_code_implement_skill.py tests/test_usage_report.py`
    — 197 passed after rebasing onto `cebb81456`. The last rebase added
    only task/log state; packaging passed again as recorded above.
  - `git diff --check origin/main...HEAD` passed. No validation behavior,
    task layout, or workflow semantics changed; no fixture update was needed.
- Returned the launch checkout to clean `main` at `origin/main` before this
  handoff. Ready for peer review; no PR opened. The Python 3.9/3.10 helper
  check is inapplicable to the owner's documentation-only choice.

---

## Peer review

- `codex review --base main` returned successfully with no actionable
  regressions or must-fix findings. The first sandboxed attempt could not
  initialize its app server; the unsandboxed retry completed. Its ambient
  interpreter lacked `tomlkit`, so its packaging-test attempt failed; the
  checkout venv verification below passed.
- Checked the corrected guidance against `sync_coga_state`, the helper's
  top-level `tomllib` import and re-exec path, and both linked owning topics.
  All four canonical/packaged pairs are byte-identical. This is documentation
  only; no terminal UI or rendered notification surface changed.
- Rebased without conflicts and pushed `b6ce69362` on
  `dream-w40-doc-corrections`, based on `origin/main` at `f8057ea93`.
  `git range-diff` confirms the reviewed patch is unchanged across rebases.
- Verification with Python 3.12.12:
  - `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` — 3,114 passed on
    `1416cb7bf`; after upstream PR #914 landed, 3,135 passed on `0ff183a91`.
  - The final rebase added only unrelated Google-agent skills and task/log
    state; `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_packaging.py`
    — 23 passed on final commit `b6ce69362`.
  - `git diff --check origin/main...HEAD` passed on the final branch.
- Returned to clean `main` at `f8057ea93` before writing this handoff.
  No review fixes or design decisions remain. No PR opened in this step.

## PR

Correct three stale Dream W40 instructions: limit the self-QA publication
warning to recurring templates and `ticket.py` and link its owning topic;
point stored-ticket schema conversions to `coga/internals/git-regressions`;
and require Python 3.11+ to start `seed_local_config.py` in both implementation
and checkout guidance. The owner's documentation-only choice preserves the
helper code and its existing re-exec fallback. All four packaged twins match.

Test plan: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` (3,135 passed before
the final unrelated skill/state rebase); `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_packaging.py`
(23 passed on final head); `git diff --check origin/main...HEAD` (passed).

## Blockers

- [x] [2026-09-29 12:32] [agent:claude] id=20260929T123206 Depends on launch-moves-the-checkout-to-main-before-and-after (PR #909 is still open): merge or close #909 before applying these corrections. Owner must also choose the seed_local_config.py route: defer the tomllib import until after the re-exec decision, or narrow the documentation to Python 3.11+.
  resolved: [2026-09-29 14:40] [human:nicktoper] PR #909 merged on 2026-09-29 at 21:27:50 UTC. Owner chose the documentation route: require Python 3.11+ to start seed_local_config.py, preserving the existing helper code and updating both code/implement and dev/checkouts with their packaged twins.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `apply-three-dream-w40-skill-and-context-correction`
Recorded: 2026-09-30T03:54:16+00:00

    Branch 'dream-w40-doc-corrections' is not safe to publish. refs/heads/dream-w40-doc-corrections does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Reconcile it and relaunch, or `coga block --task apply-three-dream-w40-skill-and-context-correction`.
