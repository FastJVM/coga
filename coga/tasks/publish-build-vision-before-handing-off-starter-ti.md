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
step: 2 (peer-review)
agent: claude
launch_generation: 04fa14fc-b161-40cc-873b-c0588e5ba7e2
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
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) under coga megalaunch; this handoff. Recovery commit 3210d12d7 credits Claude Opus 5.5; the interrupted session identity was not independently verified.
head: 7ec148c2e42168f42e1da06a7294a5b1d37cb65b
base: e4b297bd235d8060b10f65074380776e6c7ae867
depth: deep
rationale: New registered publication recipe and handoff contract; Codex review returned one unresolved P2 failure-before-dispatch finding. Do not publish the PR until corrected and re-reviewed.
implementation: New `publish-state` recipe wraps `git.publish(cfg, coga_root_paths(cfg), msg, require_paths=PATHS)` with an exit-coded contract; `build/onboarding` generate-batch runs it on the vision and starter tickets after approval and hands over `coga launch` and bumps only on exit 0, otherwise reports the unfinished handoff in chat and on its blackboard.
deviations: Placement is a registered recipe (kernel class 2) rather than an existing command, because no existing command reports publication failure; justified in the state-publication topic and handoff.
limitations: The onboarding agent's chat behavior is prose-only; tests cover the recipe end to end (empty repo via real `coga init`, bare origin, fresh clone, relocated contexts root, forced failure) but not an agent following the template. `[git].enabled = false` exits 0 as local-only by design.
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
  tests/test_publish_state.py: End-to-end onboarding publish-then-handoff tests (default and relocated contexts, forced failure, refusals, git disabled).
  src/coga/cli.py: Generalize the withheld-sweep diagnostic to include strict publication failures.
review:
  reviewer: codex
  kind: independent
  status: failed
  head: 7ec148c2e42168f42e1da06a7294a5b1d37cb65b
  base: e4b297bd235d8060b10f65074380776e6c7ae867
  detail: 'codex review --base main returned. Separate Codex review of the Claude implementation found P2: missing user fails config loading before the recipe guard, then the CLI exit sweep can publish dirty tickets without a committed feature-branch vision. Recovery-session authorship is not independently verified. Full log: /tmp/coga-onboarding-review.log.'
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest
  status: passed
  head: 7ec148c2e42168f42e1da06a7294a5b1d37cb65b
  base: e4b297bd235d8060b10f65074380776e6c7ae867
  detail: 3539 passed in 294.77s on Python 3.12.12.
- command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --json
  status: passed
  head: 7ec148c2e42168f42e1da06a7294a5b1d37cb65b
  base: e4b297bd235d8060b10f65074380776e6c7ae867
  detail: 237 valid tickets, zero errors, 26 warnings.
- command: git diff --check
  status: passed
  head: 7ec148c2e42168f42e1da06a7294a5b1d37cb65b
  base: e4b297bd235d8060b10f65074380776e6c7ae867
  detail: No whitespace errors.
```

### Recovery note (2026-10-09, orient session)

The 22:17 peer-review session died without bumping. Its uncommitted fixes were
committed unreviewed as `3210d12d7` on `onboarding-publish-before-handoff` and
pushed: publish-state fetches control before publishing and withholds the CLI
exit sweep on failure (topic + twin + tests updated). Only
`tests/test_publish_state.py` was run (9 passed). Review this commit as part of
peer-review; the full suite is still owed.


## Peer review

2026-10-09, Codex. Start check passed on clean main; fetched origin/main and
unconditionally rebased the feature branch. Pushed rebased head
`7ec148c2e42168f42e1da06a7294a5b1d37cb65b`, base
`e4b297bd235d8060b10f65074380776e6c7ae867`; returned to clean main before this note.

`codex review --base main` **returned**, with one must-fix P2: a missing
`user` in coga.local.toml makes commands.run fail before the recipe can
withhold the exit sweep. The generic sweep can then publish dirty starter
tickets without a required vision committed on a feature branch. The review
reproduced this. Initial sandbox attempt could not initialize the app-server;
the escalated run completed. No code was edited in this session.

Proposed correction, awaiting attending human confirmation: exclude
`run publish-state` from the generic CLI sweep, including pre-dispatch
failures; keep publication inside the explicit recipe. Add a subprocess
missing-user regression and update the publication topic/twin. Tradeoff:
successful calls also get no redundant exit sweep. Re-run full suite and
review after fixing. This confirmation follows the attended-session rule to
discuss substantive changes before code edits. Do not bump yet.

Checks on the reviewed revision: full suite 3539 passed (294.77s), validation
237 valid tickets / 0 errors / 26 warnings, diff whitespace clean. Exact
commands and revision receipts are in ## PR. Plain stdout/stderr only; no
raw-terminal, pager, TTY, or rendered-message surface changed. Tests exercise
CLI subprocess output; onboarding chat/no-bump instructions remain prose,
not an automated agent execution, as disclosed in the PR limitations.
