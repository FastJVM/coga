---
title: Publish build vision before handing off starter tickets
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
step: 4 (review)
agent: claude
---

## Description

The build onboarding must not hand over `coga launch <slug>` for its starter tickets until the agreed `product/vision` is confirmed on the published branch. Today `build/onboarding.md` presents the batch and launch command in chat and only then runs `coga bump`, whose end-of-command sweep is what publishes the vision. A fresh clone taken in between, or after a failed push, gets tickets whose `product/vision` context is missing (reported: `broken-context` from validate, launch exit 2).

Fix: onboarding explicitly publishes the vision (and the generated tickets) before the launch handoff, using the shared publication path #977 shipped, and only presents the batch as launchable once that publication succeeded. If publication fails, the files stay on disk, the step does not bump, and the agent tells the human in chat that the handoff is unfinished (naming the failure and how to retry) and records the same on the onboarding ticket's blackboard — it never presents launch commands as ready.

Done when an automated test runs onboarding's publish-then-handoff path from an empty repository and shows: the vision and starter tickets are on the published branch; a fresh clone resolves every generated ticket's contexts and `coga validate` passes; the same holds with a relocated `[layout] contexts` root; and a forced publication failure leaves recoverable files, no bump, and the explicit unfinished-handoff record. Live and packaged `build/onboarding.md` stay byte-identical.

## Context

### Background

Reported 2026-10-07 by another AI on the downstream thinkpick repo: six generated tickets referenced `product/vision`, which was not tracked in Git. That report was never independently reproduced; reproducing it is optional — the revision may be unobtainable — and the ordering gap above is confirmed by reading the current template.

### Already shipped — reuse, do not redo

PR #977 (sibling ticket `publish-all-coga-and-context-files-automatically`, merged 2026-10-08) made `git.sync_coga_state` publish everything under `git.coga_root_paths` — the Coga root plus the contexts root, including a relocated or previous one — via `git.publish`. `tests/test_layout_contexts.py` already asserts a relocated `product/vision` is tracked after publication and composes in a fresh clone. That sibling owns the publication policy; this ticket owns only the onboarding ordering, the failure handoff, and the end-to-end onboarding test.

### Design notes and constraints

- The owner chose an explicit publish before the handoff over merely reordering bump-then-handoff, so onboarding can detect and report failure. There is no `coga sync`/publish CLI today, so this likely needs a callable entry point. Respect the microkernel rule (`coga/extension-model`): prefer reusing an existing command or a registered `coga run` recipe with a stable argv/stdout/exit contract over a new core command, and justify any core placement.
- `coga/workflows/build/onboarding.md` and `src/coga/resources/templates/coga/workflows/build/onboarding.md` are twins (enforced by `tests/test_packaging.py`); edit both.
- Cited, not attached, because they are editing or reference targets: `coga/internals/state-publication` (`docs/contexts/coga/internals/state-publication/SKILL.md` — end-of-command sweep and guided authoring sections), `coga/sync` (`docs/contexts/coga/sync/SKILL.md`), and `dev/checkouts` (`docs/contexts/dev/checkouts/SKILL.md`), all touched by #977. `coga/init` (`docs/contexts/coga/init/SKILL.md`) covers seeding the onboarding ticket only; update it if the handoff contract it describes changes.
- The old done ticket remove-coga-build-and-project is historical: current source includes build onboarding.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/986
branch: onboarding-publish-before-handoff

Plan: add a registered `coga run publish-state [--message M] [PATH...]` recipe
(strict wrapper over `git.publish(cfg, coga_root_paths(cfg), …,
require_paths=PATHS)`; exit 0 only when every named path is confirmed on
control) and make `build/onboarding` generate-batch run it before presenting
the launch command. Failure: non-zero exit, `runner` appends `## Recipe
Failure` to the onboarding blackboard automatically; agent also notes it,
does not bump.

## Implement handoff (2026-10-08, claude)

Branch `onboarding-publish-before-handoff` pushed (336d5b00a, on origin/main 8078e71a3). No PR yet.

What changed:
- New registered recipe `publish-state` (`src/coga/publish_state.py`,
  `publish_state.run_publish_state_recipe`, added to `runner.RECIPES`).
  `coga run publish-state [--message M] [PATH...]` = one `git.publish` over
  `git.coga_root_paths(cfg)` with PATHs as `require_paths`. Exit 0: every named
  file confirmed on control (stdout lists them), or `[git].enabled = false`
  (stdout says local-only). Exit 1: refused / failed / uncertain / not a repo /
  no control branch; files stay on disk; `runner.run_reported` appends
  `## Recipe Failure` to an inherited `COGA_TASK_BLACKBOARD`. Exit 2: bad argv,
  or a named path outside the Coga roots / not a regular file (pre-write).
- `build/onboarding` generate-batch (both twins, byte-identical): no launch
  command until after approval *and* `coga run publish-state <vision> <tickets>`
  exits 0; non-zero → no handoff, no bump, tell user failure + retry, write
  `## Unfinished handoff` on its blackboard.
- Docs: `coga/internals/state-publication` new "Strict publication on demand"
  section (owner of the contract); recipe lists in `coga/extension-model`,
  `coga/cli`, CLAUDE.md/AGENTS.md; `coga/first-task` one clause. Packaged
  bootstrap twins updated. `coga/init` unchanged (it only covers seeding).

Decisions:
- Placement: registered recipe rather than core command or command ticket.
  It is a repository-independent deterministic command whose exit code *is*
  the contract (the sweep swallows failures, so no existing command can
  report one); a bootstrap `ticket.py` command ticket would need nested
  `coga launch` machinery inside the onboarding session for a 1-call wrapper.
  No new publication policy — reuses #977's `publish`/`coga_root_paths`.
- `[git].enabled = false` exits 0 with an explicit local-only message, so a
  git-disabled repo can still finish onboarding; template tells the agent to
  say the batch is launchable from this checkout only.
- `require_paths` alone accepts a file missing both on disk and control, so the
  recipe checks each named path is a regular file first.

Follow-up candidate (not done here): `dev/checkouts` "Publish pre-branch
ticket edits" uses `python -c '...sync_coga_state...'` + a porcelain check
because the sweep can't report failure; `coga run publish-state <ticket>`
would be a direct fit (and a second consumer). Also the python one-liner fails
when the shell's `python` lacks coga (hit this session: used the uv tool's
interpreter).

## PR

```yaml
title: Publish build vision before handing off starter tickets
author: claude/codex
author_evidence: 'Original implementation: Claude Code, per implement handoff. Recovery commit 3210d12d7 credits Claude Opus 5.5, but interrupted-session identity was not independently verified. Codex authored peer-review fixes f408bd760 and b1ad4596b in this attended session.'
head: b1ad4596ba50e456a0df476643e9f29ce230ea59
base: 7e3d2b880a50a49c37fe28d09990511ff873dd48
depth: deep
rationale: New registered publication recipe and onboarding handoff contract deserve owner inspection. Full suite and final Codex review passed; final review is conservatively self-review because Codex authored the follow-up fixes. Agent chat and no-bump compliance remain prose instructions.
implementation: The publish-state recipe fetches control and calls git.publish over coga_root_paths with every named file required. Onboarding publishes the vision and approved starter tickets before handing over launch commands; on failure it reports an unfinished handoff and does not bump. CLI dispatch excludes publish-state from the generic exit sweep, including missing-user failures and the optional -- separator.
deviations: Placement is a registered recipe (kernel class 2) rather than an existing command, because no existing command reports publication failure; justified in the state-publication topic and handoff.
limitations: Tests cover publication end to end, fresh-clone context resolution and validation for default/relocated layouts, recoverable failures and the Recipe Failure blackboard record. They do not execute an agent following the chat/no-bump/Unfinished handoff instructions. Git-disabled repositories remain local-only by design. Verification used Python 3.12.12, not 3.11.
files:
  AGENTS.md: Add `publish-state` to the fixed recipe registry list.
  CLAUDE.md: Add `publish-state` to the fixed recipe registry list.
  coga/workflows/build/onboarding.md: Publish vision and tickets via `coga run publish-state` before the launch handoff; failure path with no bump.
  src/coga/resources/templates/coga/workflows/build/onboarding.md: Packaged twin of the onboarding workflow (byte-identical).
  docs/contexts/coga/internals/state-publication/SKILL.md: Own the `publish-state` contract (strict publication on demand).
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/state-publication/SKILL.md: Packaged twin.
  docs/contexts/coga/extension-model/SKILL.md: Add `publish-state` to the closed `RECIPES` list with a pointer to its contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Packaged twin.
  docs/contexts/coga/cli/SKILL.md: Add `publish-state` to the `coga run` names.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Packaged twin.
  docs/contexts/coga/first-task/SKILL.md: Note starter tickets are offered only once published.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Packaged twin.
  src/coga/publish_state.py: The recipe implementation.
  src/coga/runner.py: Register `publish-state` in `RECIPES`.
  tests/test_runner.py: Expected fixed registry includes `publish-state`.
  tests/test_publish_state.py: End-to-end publication and fresh-clone checks, refusals, stale control, git-disabled behavior, and missing-user regressions with and without the option separator.
  src/coga/cli.py: Exclude publish-state from the exit sweep before recipe dispatch, normalize the optional -- separator, and generalize the withheld-sweep diagnostic.
review:
  reviewer: codex
  kind: self
  status: passed
  head: b1ad4596ba50e456a0df476643e9f29ce230ea59
  base: 7e3d2b880a50a49c37fe28d09990511ff873dd48
  detail: 'codex review --base main returned on the final head with no actionable regressions; its 66 publication/runner/packaging checks passed. Separate review invocation, conservatively classified as self-review because Codex authored the fixes. Previous returned reviews found pre-dispatch and option-separator sweep bypasses; both are corrected. Log: /tmp/coga-onboarding-review-verified.log.'
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest
  status: passed
  head: b1ad4596ba50e456a0df476643e9f29ce230ea59
  base: 7e3d2b880a50a49c37fe28d09990511ff873dd48
  detail: 3541 passed in 285.63s on Python 3.12.12; /tmp/coga-onboarding-pytest-verified.log.
- command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --json
  status: passed
  head: b1ad4596ba50e456a0df476643e9f29ce230ea59
  base: 7e3d2b880a50a49c37fe28d09990511ff873dd48
  detail: 237 valid tickets, zero errors, 27 warnings; /tmp/coga-onboarding-validate-verified.json.
- command: git diff --check
  status: passed
  head: b1ad4596ba50e456a0df476643e9f29ce230ea59
  base: 7e3d2b880a50a49c37fe28d09990511ff873dd48
  detail: No whitespace errors.
```

## Recovery note (2026-10-09, orient session)

The 22:17 peer-review session died without bumping. Its uncommitted fixes were
committed unreviewed as `3210d12d7` on `onboarding-publish-before-handoff` and
pushed: publish-state fetches control before publishing and withholds the CLI
exit sweep on failure (topic + twin + tests updated). Only
`tests/test_publish_state.py` was run (9 passed). Review this commit as part of
peer-review; the full suite is still owed.


## Peer review

2026-10-09, Codex. Complete. Final `codex review --base main` **returned**
with no actionable findings on head `b1ad4596ba50e456a0df476643e9f29ce230ea59`,
base `7e3d2b880a50a49c37fe28d09990511ff873dd48`.
The review ran as a separate Codex invocation; final review is conservatively
self-review because Codex authored the follow-up fixes. Original implementation
was Claude; recovery-session identity is not independently verified.

Two earlier returned reviews exposed the same publication boundary failure:
missing-user configuration refused before the recipe guard, and the valid
`run -- publish-state` spelling bypassed the first CLI exclusion. The owner
approved excluding publish-state from the generic sweep. Commits f408bd760
and b1ad4596b implement that exclusion, including the optional separator, and
add subprocess regressions. The new regression failed before the fix because
the remote advanced despite exit 2; both spellings now preserve remote and
local file bytes. Publication topic and packaged twin updated.

Final checks: `PYTHONPATH=$PWD/src .venv/bin/python -m pytest` -> 3541 passed
in 285.63s (Python 3.12.12); `PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli
validate --json` -> 237 valid, 0 errors, 27 warnings; `git diff --check` clean.
The review's own targeted publication/runner/packaging run passed 66 tests.
Exact revision receipts and every diff-path reason are in ## PR. Logs are
/tmp/coga-onboarding-{review,pytest,validate}-verified.{log,json} as applicable.
Earlier runs are superseded, not claimed as verification of the final head.

Plain stdout/stderr only: no raw-terminal, pager, TTY or rendered-message
surface changed. CLI subprocess output is exercised. Agent chat/no-bump and
Unfinished handoff instructions remain prose, not an automated agent run;
that limitation is explicit in the PR preparation. Advisory depth: deep.

Fetched/rebased before the fixes and verification, force-with-lease pushed
final head, then fetched and returned to clean main. No material control
drift remained. Peer-review work is complete; bump once to open-pr, then stop.
