---
title: 'Recipe migration, part 4: move Dream''s validate-drift and orphan-marker workers
  to the edge'
status: done
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
agent: claude
---

## Description

Part 4 of the recipe migration. Move Dream's two Python workers,
`validate-drift` (847-line `dream_validate_drift.py`) and
`cleanup-orphan-markers` (336-line `dream_cleanup_orphan_markers.py`), into
`coga_edge.validate_drift` and `coga_edge.cleanup_orphan_markers`, and remove
both `runner.RECIPES` entries. Dream's packaged `ticket.md` phases call
`coga run validate-drift` and `coga run cleanup-orphan-markers` today.

Done when Dream's phases invoke the edge workers, both names exit 2 through
`coga run`, and the checklist below holds.

### Invocation (owner decision 2026-11-16)

Dream stays agent-backed. Its ordered phases invoke the workers as
`python -m coga_edge.<worker>`, with the same flags they pass today. Do not
add a Dream `ticket.py`, a child task, or general attachment copying. A full
local Dream fork copies the worker module beside its ticket and points its
phase text at that local file; document that passage in the edge-code
upgrade procedure. These workers never bump, but still get 04's exit
publication. Their `--cwd` cross-root parsing supplies the root resolver.

### Behavior to preserve

Drift repair and full classifier coverage; the orphan-marker scan stays
report-only.

### Surfaces to update in the same PR

Dream's packaged `ticket.md` Phase 1/5 passages; skills
`bootstrap/dream/tasks/validate-drift` and
`bootstrap/dream/tasks/cleanup-orphan-markers`; plus the shared list below.
The migration fixtures must include frozen Dream Phase 1/5 instructions and
parked or customized Dream copies.

### Acceptance

- [ ] Both entries removed; names exit 2; no core stub.
- [ ] Classifier/repair and report-only scan tests pass against the edge modules.
- [ ] Both private `append_report` copies are deleted in favor of
      `blackboard.append_blackboard_report`.
- [ ] Old and new Dream passages are covered by fixtures against the
      installed wheel and a complete local fork.
- [ ] The shared migration rules below are satisfied.

### Shared migration rules (from the group record in 04)

Depends on `v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`
(shared reporting/publication infra) being merged; that ticket also holds the
registry disposition table and the owner decisions of 2026-11-16. Start from
current main after that merge.

- **Edge home.** The job moves to `src/coga_edge/<recipe_name>.py`. Its
  packaged definition selects it; core never imports or path-loads it.
  It imports only stdlib and shared `coga.*`, never sibling edge modules, so
  a copied module is a complete local fork.
- **Remove the registry name.** Delete the `runner.RECIPES` entry and the
  core module. The removed name takes the existing unknown-recipe exit-2 path
  in `commands/run.py`; add no forwarding entry or core stub.
- **Entry sequence.** Use 04's shared report → publish → bump sequence.
  Scheduled runs bump exactly once after success and propagate bump failure;
  manual runs never advance the outer task.
- **Reporting.** Report through `blackboard.append_blackboard_report` and
  delete the job's private `append_report` copy, if any. Supply the job's own
  root resolver to `runner.run_reported`.
- **Shared helpers stay.** A helper with another production consumer stays in
  core; audit individual symbols with `grep`, not modules.
- **Old callers.** Follow the package-owned
  `coga/edge-code/edge-code-upgrades.md`. Inventory old template/period
  shims (and, where relevant, frozen Dream passages), including parked and
  customized copies. Ship concrete old/new invocation passages and fixtures
  that test stock, customized and parked callers against the read-only
  installed wheel and a complete local fork, preserving state bytes. Do not
  overwrite running code, frozen workflow/lifecycle state, recurring parent
  blackboards or unknown customizations. Adopting the migration on this
  repo's own periods is a separate rollout: record its plan on this ticket's
  blackboard; do not perform it in the implementation PR.
- **Same-PR owner updates.** Rewrite every surface naming the removed
  spelling or core module (listed per ticket below), plus the `coga/cli`
  recipe index, `coga-dev/microkernel`, `coga-dev/codebase` and the AGENTS.md
  `runner.RECIPES` text. Edit package copies under `src/coga/resources/`;
  keep `coga-dev/` topics local. Packaging checks require one owner, no live
  twins.
- **Verification.** Report production code before/after at named revisions
  as a per-file table (core / edge / scripts, physical lines via `wc -l`),
  marking deleted code and removed duplicates separately from moved code. Run
  the job's suites plus runner/recurring/shared-consumer suites, packaging
  checks and the per-change Linux receipt in `coga-dev/testing` (native
  Windows/macOS receipts are release-only; record them as deferred), plus
  `coga validate` in a disposable fixture.

## Context

Rules from `coga-dev/microkernel` (cited, not attached): core keeps shared
infra with at least two real consumers or a reviewed co-versioned command
contract; production `src/coga/` never imports `coga_edge`; count callers of
one symbol, not copies of one body. Read its "Edge packaging invariants"
section, plus `coga-dev/packaging`, `coga-dev/testing` and the package-owned
`coga/edge-code`, `coga/script-tickets` and `coga/state-publication` under
`src/coga/resources/templates/coga/bootstrap/contexts/`.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## PR

```yaml
title: Move Dream's validate-drift and orphan-marker workers to the edge
author: claude
author_evidence: >-
  Attended megalaunch implement session run by Claude Opus 5.5; see the
  implement handoff above.
head: dd074a6bcfb5b6da3f81b205aad697531a086b47
base: a2536cbbdd5e28bfed634af2b7f8b96bd8c7fab2
depth: deep
rationale: >-
  Removes two coga run recipe names (a user-visible exit-2 change for frozen
  Dream bodies) and ships a migration runbook; read the runbook passages, the
  Dream phase text and the edge-distribution fixtures closely.
implementation: >-
  Moves Dream's two workers into coga_edge with main() over runner.run_entry
  (report then publish, never bump) and their own target_root resolvers;
  deletes both private append_report copies and the RECIPES/RECIPE_ROOTS
  entries; rewrites Dream Phase 1/5, both skills and owner docs; ships old,
  new and fork passages plus a fork copy command in the upgrade runbook.
deviations: >-
  The orphan worker keeps its PyYAML import (Coga's own runtime dependency)
  to preserve load_status behavior, so its import rule is stdlib, PyYAML and
  coga, not strictly stdlib and coga. The "older recipe" wording in Dream's
  Phase 6 blackboard rule is kept as historical.
limitations: >-
  Rollout on this repo is not performed (plan on the blackboard). Native
  Windows/macOS receipts are release-only and deferred. The Dream agent must
  use the interpreter that runs coga; nothing resolves it automatically.
files:
  AGENTS.md: Edge implementations may also be selected by packaged instructions (Dream).
  docs/contexts/coga-dev/codebase/SKILL.md: Source map entry for the two Dream edge workers.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Live producer path renamed to coga_edge/validate_drift.py.
  docs/contexts/coga-dev/microkernel/SKILL.md: append_report example, validation paragraph and edge invariant updated.
  src/coga/resources/__init__.py: Docstring names the moved module.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Recipe index drops the two removed names.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Dream workers as forkable edge attachments.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md: Concrete old/new/fork Dream passages, fork copy command, callers regex.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Validation module entry consumer renamed.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/SKILL.md: Runs line points at the edge module.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md: Runs/How to Run point at the edge module.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Phase 1/5 invoke python -m coga_edge workers.
  src/coga/runner.py: Removes the two RECIPES and RECIPE_ROOTS entries and their imports.
  src/coga/validate.py: Docstring no longer names the removed recipe.
  src/coga/dream_cleanup_orphan_markers.py: Moved to the edge (old name).
  src/coga_edge/cleanup_orphan_markers.py: Moved worker with main() over run_entry; append_report deleted.
  src/coga/dream_validate_drift.py: Moved to the edge (old name).
  src/coga_edge/validate_drift.py: Moved worker with main() over run_entry; append_report deleted.
  tests/fixtures/edge-migration/README.md: Describes the real Dream passage reconciliation.
  tests/test_checkouts.py: Extra-publication case runs the edge orphan worker.
  tests/test_dream_skill_scripts.py: Workers run as python -m coga_edge modules from the task.
  tests/test_dream_validate_drift.py: Tests import and run coga_edge.validate_drift.
  tests/test_dream_worker_templates.py: Pins new Dream/skill commands and absence of old ones.
  tests/test_edge_distribution.py: Import purity, passage reconciliation and wheel/fork execution fixtures.
  tests/test_runner.py: Registry list, removed names exit 2, cwd root cases through the edge worker.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    Code review has not run yet; the workflow's peer-review step follows
    this implement step.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: dd074a6bcfb5b6da3f81b205aad697531a086b47
    base: a2536cbbdd5e28bfed634af2b7f8b96bd8c7fab2
    detail: >-
      5010 passed, 33 skipped in 809s on Linux, run on the working tree
      committed as 983269bad; src/tests/docs trees are byte-identical in
      dd074a6bc (rebase over a ticket-only state commit).
  - command: coga validate --json (seeded fixture copy, .venv interpreter)
    status: passed
    head: dd074a6bcfb5b6da3f81b205aad697531a086b47
    base: a2536cbbdd5e28bfed634af2b7f8b96bd8c7fab2
    detail: >-
      Disposable copy of tests/fixtures/seeded-repo; exit 0, 0 issues.
      python -m coga_edge.validate_drift --no-fix there reported no drift;
      coga run validate-drift exited 2 with unknown recipe.
  - command: native Windows/macOS receipts
    status: not-run
    detail: Release-only per coga-dev/testing; deferred.
```

---

## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Dev

pr: https://github.com/FastJVM/coga/pull/1265
branch: coga/v1-microkernel-04d-dream-workers-to-edge

---

## Implement handoff — 2026-11-18

Attended megalaunch session (Claude Opus 5.5). Blocker resolved first: owner
merged PR #1245 (`133bb5fee`) in-session; `coga unblock` recorded it. Branch
started from main `b8429e30c`; implementation commit `983269bad`, rebased
over the state-only `a2536cbbd` as `dd074a6bc` (identical `src`/`tests`/`docs`
trees) and pushed.

- **Edge modules.** `git mv` of `src/coga/dream_validate_drift.py` →
  `src/coga_edge/validate_drift.py` and `src/coga/dream_cleanup_orphan_markers.py`
  → `src/coga_edge/cleanup_orphan_markers.py`. Logic unchanged; each gains a
  docstring and `main()` = `runner.run_entry(name, worker, sys.argv[1:],
  root=target_root)` (`scheduled=False`: never bumps; exit publication of the
  target root). Both private `append_report` copies deleted; call sites use
  `blackboard.append_blackboard_report`. Imports: stdlib + `coga.*` (+ PyYAML
  in the orphan worker, a Coga runtime dependency; kept for behavior
  preservation of `load_status`), no `coga_edge` sibling import.
- **Registry.** `validate-drift` / `cleanup-orphan-markers` removed from
  `runner.RECIPES` and `RECIPE_ROOTS` (only `skill-update` remains there for
  04b); runner imports no Dream module. Both names exit 2 via the existing
  unknown-recipe path. No stub.
- **Shared helpers audit (grep per symbol).** `task_env.cwd_option_root` and
  `discover_coga_os_root` still used by `skill_update.py`; `blackboard_from_env`
  and `append_blackboard_report` by many core modules. Nothing left core-only
  for Dream.
- **Dream body (package).** Phase 1/5 now `python -m coga_edge.validate_drift`
  / `python -m coga_edge.cleanup_orphan_markers` (no flags, as before); run
  order labels "edge worker"; dispatch paragraph says use the interpreter that
  runs `coga`, worker publishes on exit and never advances Dream, an import
  failure is a failed phase. "older recipe" wording in the Phase 6 blackboard
  rule kept (historical; a test pins it).
- **Skills** `bootstrap/dream/tasks/{validate-drift,cleanup-orphan-markers}`:
  Runs/How to Run point at the module; fork note.
- **Upgrade runbook** (`coga/edge-code/edge-code-upgrades.md`): callers regex
  now only the removed names; the placeholder "later recipe-removal release"
  section replaced by concrete `dream-phase-{1,5}-{old,new,fork}` passages, a
  `dream-fork-copy` command (refuses overwrite), fork rules and reconcile.
  `coga/edge-code` SKILL describes Dream workers as forkable attachments.
- **Docs:** `coga/cli` recipe list, `coga/first-task`, `coga-dev/microkernel`
  (append_report example, validation paragraph, invariants line),
  `coga-dev/codebase` source map, `coga-dev/internals/notifications`,
  AGENTS.md edge sentence, `resources/__init__.py` and `validate.py`
  docstrings.
- **Tests:** `test_runner` (registry, removed names exit 2, `--cwd` root cases
  run the edge worker through `run_reported` with its resolver);
  `test_dream_validate_drift`/`test_dream_skill_scripts` run `python -m
  coga_edge.*`; `test_checkouts` extra-publication case uses the orphan
  worker; `test_dream_worker_templates` pins new commands and absence of old;
  `test_edge_distribution`: import purity for both workers; wheels tag Dream
  reports per build; legacy adoption reconciles stock/period/parked Dream
  copies with the shipped passages and refuses a customized copy (left in the
  callers inventory); new test runs the reconciled package and fork commands
  from a Dream period env against a **read-only installed wheel** and a full
  local fork (report origin proves which code ran), checks a stale `coga run
  validate-drift` exits 2, frontmatter/prior blackboard/other files unchanged.

### Session incident (resolved)

A manual smoke run of `python -m coga_edge.cleanup_orphan_markers` from a
scratch fixture inherited this session's `COGA_*` env, so it reported a
no-op `## Dream Skill: cleanup-orphan-markers` section into this ticket and
its exit publication pushed it to control. Removed locally; the bump
publishes the removal. Lesson for reviewers: run Dream workers by hand with
`env -u COGA_TASK_BLACKBOARD -u COGA_COGA_OS_ROOT ...` inside a launched
session.

### Rollout plan for this repo (not performed here)

After merge and installing the new wheel in every writer:
`coga/recurring/dream/ticket.md` is a state-only carrier, so future Dream
periods take the new packaged body automatically. The one existing period
`coga/tasks/recurring/dream/ticket.md` is `status: done` and contains each
old passage exactly once; if it is ever resumed instead of replaced, apply the
runbook `reconcile` with `dream-phase-{1,5}-old` → `-new`. No parked or
customized Dream copies exist (`rg` callers inventory: only that period plus
historical mentions in ticket prose/evidence, which are not instructions).

### Production line counts (`wc -l`, `b8429e30c` → `dd074a6bc`)

| File | Layer | Before | After | Note |
| --- | --- | --- | --- | --- |
| `src/coga/dream_validate_drift.py` | core | 851 | 0 | moved |
| `src/coga/dream_cleanup_orphan_markers.py` | core | 344 | 0 | moved |
| `src/coga_edge/validate_drift.py` | edge | 0 | 864 | moved; −4 `append_report` (deleted dup), +17 docstring/`main` |
| `src/coga_edge/cleanup_orphan_markers.py` | edge | 0 | 361 | moved; −4 `append_report` (deleted dup), +21 docstring/`main` |
| `src/coga/runner.py` | core | 364 | 352 | −12: 2 RECIPES, 2 RECIPE_ROOTS entries, 8 import lines deleted |
| `src/coga/validate.py`, `resources/__init__.py` | core | 2085, 27 | 2085, 27 | docstring only |

Core −1,207; edge +1,225; net production +18 (entry points). Relocation, not
reduction; deleted: two duplicate `append_report` helpers, two registry
entries and two root-resolver entries plus core's imports of both parsers.
Tests/docs reported separately in the PR receipt.

---

## Blockers

- [x] [2026-11-16 22:19] [agent:claude] id=20261116T221924 Prerequisite not merged: v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co (PR #1245, open, step review) must merge first. This ticket must start from main after that merge and use its shared report->publish->bump entry sequence and run_reported root-resolver support, which are absent from main at 77e263258.
  resolved: [2026-11-18 17:31] [human:nicktoper] Prerequisite resolved: PR #1245 (v1/microkernel/04) merged to main as 133bb5fee on 2026-11-18. Start 04d from current main, using 04's shared report->publish->bump entry sequence and run_reported root-resolver support.

---

## Blocker reminders

- 576c34ebc29d last_reminded: 2026-11-18 09:02

## Peer review

Codex independently reviewed Claude Opus 5.5's implementation. Direct review
completed against base `bd1f2bec80550bff576505cee1605a5f89e89fc1` and final head `bb7f1280d38cf3335be0bff971e16bd323b753c7`.
The migration previously matched passages across the entire ticket, allowing
a historical quotation to be rewritten when the body had been customized.
The runbook now scopes the edit to the authored body. It also ships a
replacement for the old dispatch paragraph so resumed periods use the
correct interpreter and phase commands. The installed-wheel fixture now
executes the virtual environment's Python without following a symlink out
of that environment. The orphan scan now uses the shared Ticket reader for
the exact done-status gate. Re-reviewed the final diff with no unresolved must-fix
findings.

Linux, Pop!_OS 24.04 LTS, Python 3.11.15. Full suite 5010 passed, 33 skipped, 0 failed in 249.38s. Focused suite
769 passed, 0 skipped, 0 failed in 159.88s. Disposable seeded-repo validation passed. Native Windows and
macOS verification is deferred to release.

For rollout, reconcile the dispatch paragraph as well as the two phase
passages if the existing done period is ever resumed. Production Python counts below use `wc -l` at the review base and head.

| Path | Layer | Before | After | Change |
| --- | --- | ---: | ---: | --- |
| `src/coga/dream_validate_drift.py` | Core | 851 | 0 | Moved |
| `src/coga/dream_cleanup_orphan_markers.py` | Core | 344 | 0 | Moved |
| `src/coga_edge/validate_drift.py` | Edge | 0 | 864 | Moved logic, removed report wrapper, added entrypoint |
| `src/coga_edge/cleanup_orphan_markers.py` | Edge | 0 | 350 | Moved logic, removed report wrapper and duplicate status parsing, added entrypoint |
| `src/coga/runner.py` | Core | 364 | 352 | Deleted registry and resolver entries and two imports |
| `src/coga/validate.py` | Core | 2085 | 2085 | Docstring |
| `src/coga/resources/__init__.py` | Core | 27 | 27 | Docstring |

Core −1,207, edge +1,214, net +7. No standalone script was added. Docs and
packaged definitions add 233 lines and remove 66. Tests and fixture
documentation add 259 lines and remove 71. These separate counts use
rename-aware `git diff --numstat`.

## PR

```yaml
"title": "Move Dream's validation and orphan scan workers to the edge"
"author": "claude"
"author_evidence": "Claude Opus 5.5 implemented the migration, as recorded in the implement handoff and\
  \ first commit. Codex independently reviewed it and authored the follow-up fixes."
"head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
"base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
"depth": "skim"
"rationale": "The workers retain their existing classifier, repair, and report-only logic. Review the\
  \ upgrade passages because existing local and frozen Dream copies require coordinated edits before resuming\
  \ under the new wheel."
"implementation": "Dream invokes both edge workers through the shared report and publication entry. The\
  \ recipe names are retired. The migration replaces the dispatch and phase passages only in the authored\
  \ ticket body, preserving archived blackboard text. The worker move adds seven net production Python\
  \ lines after replacing duplicate status parsing with the shared Ticket reader. Separately, docs and\
  \ packaged definitions add 233 lines and remove 66, while tests and fixture documentation add 259 and\
  \ remove 71."
"deviations": "Dream stays agent-backed and the workers never advance it. Cleanup uses the canonical Ticket\
  \ reader for its exact done-status gate."
"limitations": "Native Windows and macOS checks are deferred to release. Adopting this upgrade in Coga's\
  \ own saved Dream period is a separate rollout."
"files":
  "AGENTS.md": "Describe shipped edge implementations selected by packaged definitions."
  "docs/contexts/coga-dev/codebase/SKILL.md": "Map Dream's workers to the edge source paths."
  "docs/contexts/coga-dev/internals/notifications/SKILL.md": "Point the notification producer inventory\
    \ at the migrated worker."
  "docs/contexts/coga-dev/microkernel/SKILL.md": "Record worker placement and shared reporting ownership."
  "src/coga/resources/__init__.py": "Update the resource loader's description of Dream."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md": "Remove the two recipe names\
    \ from the CLI inventory."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md": "Document the Dream\
    \ worker fork boundary."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md": "Ship exact\
    \ old, new and fork passages, copy instructions, and a body-only reconciliation procedure."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md": "Describe Dream's execution\
    \ of validator fixes through the edge worker."
  "src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/SKILL.md": "Update\
    \ the orphan scan's invocation and reporting contract."
  "src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md": "Update\
    \ the drift repair invocation, arguments and reporting contract."
  "src/coga/resources/templates/coga/recurring/dream/ticket.md": "Run both workers from the agent-backed\
    \ phase instructions."
  "src/coga/runner.py": "Remove the recipes and their root resolver registrations."
  "src/coga/validate.py": "Describe the validator's CLI and module entrypoints."
  "src/coga/dream_cleanup_orphan_markers.py": "Remove the core orphan worker and its private report wrapper."
  "src/coga/dream_validate_drift.py": "Remove the core drift worker and its private report wrapper."
  "src/coga_edge/cleanup_orphan_markers.py": "Run the report-only scan through the shared entry and publication\
    \ path."
  "src/coga_edge/validate_drift.py": "Run drift classification and safe repair through the shared entry\
    \ and publication path."
  "tests/fixtures/edge-migration/README.md": "Explain the legacy Dream fixture and preservation checks."
  "tests/test_checkouts.py": "Exercise real worker exit publication in the checkout accounting test."
  "tests/test_dream_skill_scripts.py": "Exercise Dream's CLI worker modules including the report-only\
    \ scan."
  "tests/test_dream_validate_drift.py": "Keep drift classification and repair coverage on the migrated\
    \ module."
  "tests/test_dream_worker_templates.py": "Verify the packaged phase commands and reject retired spellings."
  "tests/test_edge_distribution.py": "Exercise the upgrade passages, historical blackboard protection,\
    \ wheel installation and complete fork."
  "tests/test_runner.py": "Pin exit 2 for the removed names and exercise cross-root report routing."
"review":
  "reviewer": "codex"
  "kind": "independent"
  "status": "passed"
  "head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
  "detail": "Direct review completed. Fixed blackboard rewrite risk, stale dispatch instructions, the\
    \ installed-wheel fixture's Python selection and the orphan worker's direct YAML dependency. Re-reviewed\
    \ the final diff with no unresolved must-fix findings."
"checks":
- "command": "env TMPDIR=/home/n/Code/coga-04d-pytest.Apisih TERM=dumb /home/n/Code/coga/.venv/peer-review.wT1qVC/venv/bin/python\
    \ -m pytest -n 8 --dist loadfile"
  "status": "passed"
  "head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
  "detail": "Pop!_OS 24.04 LTS, Python 3.11.15. 5010 passed, 33 skipped, 0 failed in 249.38s."
- "command": "env TMPDIR=/home/n/Code/coga-04d-pytest.Apisih TERM=dumb /home/n/Code/coga/.venv/peer-review.wT1qVC/venv/bin/python\
    \ -m pytest tests/test_dream_validate_drift.py tests/test_dream_skill_scripts.py tests/test_dream_worker_templates.py\
    \ tests/test_runner.py tests/test_recurring.py tests/test_blackboard.py tests/test_packaging.py tests/test_edge_distribution.py"
  "status": "passed"
  "head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
  "detail": "Pop!_OS 24.04 LTS, Python 3.11.15. 769 passed, 0 skipped, 0 failed in 159.88s."
- "command": "cd /tmp/coga-04d-fixture.uWEnnM/coga && env -u SLACK_WEBHOOK_URL /home/n/Code/coga/.venv/peer-review.wT1qVC/venv/bin/coga\
    \ validate --json"
  "status": "passed"
  "head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
  "detail": "Disposable seeded repo. Exit 0, five valid entries, zero issues or fixes."
- "command": "git diff --check bd1f2bec80550bff576505cee1605a5f89e89fc1...bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "status": "passed"
  "head": "bb7f1280d38cf3335be0bff971e16bd323b753c7"
  "base": "bd1f2bec80550bff576505cee1605a5f89e89fc1"
  "detail": "Passed with no whitespace errors."
- "command": "Native Windows and macOS full suites"
  "status": "not-run"
  "detail": "Deferred to release under coga-dev/testing."
```
