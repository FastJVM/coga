---
title: Propagate local Coga config into worktrees
status: done
owner: zach
agent: claude
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
---

## Description

Make Coga-created and Coga-recommended feature checkouts usable for mutating
commands without manually rediscovering that `coga/coga.local.toml` is absent.
Linked worktrees and independent-clone fallbacks omit this gitignored file, so
commands that require an actor fail with exit 2 even though Coga instructed the
agent to create the checkout.

Apply the existing Retro/Dream policy consistently: ordinary-copy the primary
checkout's complete `coga.local.toml` to the same repo-relative path in the
isolated checkout, restrict it to the current user, and never print, symlink,
snapshot, stage, or commit it. This intentionally carries the same
machine-local capabilities into another checkout on the same machine.

## Context

- The live and packaged `code/implement` skill tells agents to create a linked
  worktree with `git worktree add`, or an independent clone under `/tmp` when
  `.git` metadata is read-only. Neither path carries ignored files.
- Packaged `workflows/docs/with-review.md` has the same linked-worktree gap.
- `src/coga/open_pr.py`, `open_pr`, tells an agent to recreate a missing
  recorded checkout with `git worktree add`; this recovery diagnostic is the
  current successor to the removed bootstrap open-pr recipe. It needs to
  direct the agent to establish local config before using that checkout.
- `src/coga/config.py`, `load_config`, deliberately requires `user` for commands that create or mutate
  task state. This guard is correct; the defect is that Coga's prescribed
  checkout flow does not satisfy it.
- Exact precedent: live and packaged `recurring/dream/ticket.md`,
  packaged `skills/retro/done-ticket/SKILL.md`, and
  `src/coga/resources/retire.md` already require an ordinary copy and cleanup.

Policy:

- Source is the primary checkout's valid `coga.local.toml`. If it is absent or
  invalid, fail loud before the first Coga command; never synthesize a user.
- If the destination file is absent, copy it byte-for-byte and set mode `0600`.
- If the destination already exists, preserve its contents when its parsed
  `user` equals the source actor, but tighten its mode to `0600`. If the actor
  differs, either file cannot be parsed, or permissions cannot be tightened,
  fail loud instead of overwriting or continuing.
- Apply the same rule on initial creation and resumed sessions. Remove copied
  config during teardown only for disposable checkouts whose owning flow
  already removes the checkout.

Done means:

- live and packaged `code/implement`, packaged `docs/with-review`, and
  `src/coga/open_pr.py` (`open_pr` recovery guidance) establish or
  verify local config before the first mutating Coga command;
- linked worktrees and independent-clone fallbacks are both covered;
- the destination actor equals the source actor; a conflicting actor fails
  loud without overwriting either file;
- local config remains ignored and sentinel credential values never appear in
  output, snapshots, staged files, or commits;
- tests cover missing source, fresh destination, same-actor resume, conflicting
  actor, a same-actor destination with overly broad permissions, linked
  worktree, and independent-clone guidance; and
- live and packaged copies of changed workflow, skill, or context files remain
  synchronized.

Out of scope: weakening the requirement for an explicit actor. Execution-ready
validation of a separately provisioned runner belongs to sibling ticket
`v2/fail-validation-when-local-user-is-required-for-ex`. Future internal
worktree automation remains owned by
`v2/reintroduce-per-launch-worktree-isolation`, which must preserve this
policy.
<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/851
branch: propagate-local-config
worktree: /tmp/coga-local-config

## Implement

- Human approved an ordinary attachment beside code/implement; no new core command.
- Feature worktree created from main; primary checkout retains its existing log change.
- Recovery guidance moved from the ticket's stale recipe.py reference to
  src/coga/open_pr.py, open_pr. Updating that current surface.
- dev/code owns the copy/resume policy; changed skills and docs workflow point to it.
- Regression suite covers linked worktrees, independent clones, missing/invalid
  source, same-actor resume and broad permissions, conflicting/invalid destination,
  symlinks, and absence of sentinel values from output and Git state.
- Initial tests stopped at missing tomlkit; declared test dependencies installed
  into /tmp/coga-local-config-venv after sandbox network approval.


## Verification and handoff

- Commit: aba21842c — Propagate local config into feature checkouts.
- Feature branch is clean and contains latest fetched origin/main (7277dd030).
  No feature push or PR. Rebase changed only upstream task/log state.
- Added ordinary seed_local_config.py attachment; it validates source/destination
  config, verifies ignored/untracked placement, copies bytes privately, preserves
  same-actor destination contents, and fails without revealing config values.
- Updated live and packaged code/implement and dev/code, bundled docs/with-review,
  and open_pr recovery guidance. Packaged helper inclusion and twin identity pass.
- Actual feature checkout seeded successfully using the helper. Its ignored local
  config stays in place for subsequent steps; no teardown is part of this step.
- No task layout, composition algorithm, or workflow routing changed; example
  fixture updates and structural validation are not needed.
- Verification (Python is /tmp/coga-local-config-venv/bin/python):
  - `python -m pytest -q` — 2673 passed (full suite).
  - `python -m pytest tests/test_seed_local_config.py tests/test_packaging.py -q`
    — 30 passed, including strengthened literal-webhook and Git snapshot checks.
  - After rebase: `python -m pytest tests/test_seed_local_config.py tests/test_packaging.py tests/test_open_pr.py tests/test_open_pr_command.py -q`
    — 78 passed.
  - `git diff --check`, clean feature `git status --short`, and
    `git merge-base --is-ancestor origin/main HEAD` passed.
- Initial dependency failure was resolved by installing declared extras in an
  isolated environment. One attempted focused command named a nonexistent test
  file; the corrected command above passed. No unresolved test failures.


## Peer review

- `codex review --base main` ran in `/tmp/coga-local-config` and returned.
  It found one P2: the bundled-helper discovery snippet called
  `bootstrap_skill_dir` without its required config argument. Corrected live
  and packaged `dev/code` to use configuration-independent
  `packaged_template_path`; executed the lookup and verified the helper exists.
- Manual review found stale `coga/codebase` guidance describing the old policy
  and this ticket as a draft. Replaced it with a pointer to the owning
  `dev/code` contract in both live and packaged contexts.
- Review initially could not initialize under the filesystem sandbox; rerun
  outside the sandbox returned successfully. Its default Python lacked
  `tomlkit`; verification uses the prepared test environment instead.
- `git fetch origin main && git rebase FETCH_HEAD` completed cleanly.
- Post-fix focused check:
  `PYTHONPATH=/tmp/coga-local-config/src /tmp/coga-local-config-venv/bin/python -m pytest tests/test_seed_local_config.py tests/test_packaging.py -q`
  — 30 passed.
- No interactive terminal, pager, or rendered notification behavior changed.
  The changed surface is checkout instructions and a plain setup helper;
  subprocess tests exercise its output, failure exits, actual linked worktrees,
  independent clones, actor preservation, permissions, and Git exclusion.

- Full post-rebase verification:
  `PYTHONPATH=/tmp/coga-local-config/src /tmp/coga-local-config-venv/bin/python -m pytest -q`
  — 2674 passed in 175.92s. `git diff --check` passed.
- Review fixes committed as `196439122` (implementation rebased to `c8cd1c0f1`).
  Feature checkout is clean, with two commits ahead of fetched `origin/main`
  (`30f3cadd6`). No unresolved must-fix findings; no feature push or PR yet.

## Open PR

- `coga open-pr` ran from the primary control checkout (separate-worktree
  layout) and opened https://github.com/FastJVM/coga/pull/851 (ready, not
  draft). Base advanced only through non-overlapping task/log state; no rebase
  or force push was needed. Feature worktree `/tmp/coga-local-config` remains
  in place for the merge/review step.

## PR

Feature worktrees and independent clones omit ignored local config, causing
actor-required Coga commands to fail. Add an ordinary attachment beside
`code/implement` that copies the primary config privately, preserves existing
same-actor contents while restricting permissions, and refuses invalid or
conflicting config without exposing credentials.

Creation, resume, docs workflow, and missing-checkout recovery guidance now
require setup before running Coga. The `dev/code` context owns the policy;
live and packaged guidance stays synchronized, including the corrected bundled
helper lookup. Regression coverage exercises real worktrees and clones,
permissions, actor conflicts, invalid source/destination config, and exclusion
from output and Git state.

Test plan: `PYTHONPATH=/tmp/coga-local-config/src /tmp/coga-local-config-venv/bin/python -m pytest -q` (2674 passed); focused `tests/test_seed_local_config.py tests/test_packaging.py -q` (30 passed); executed the bundled-helper lookup and ran `git diff --check`.
