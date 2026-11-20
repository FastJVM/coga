---
title: 'Recipe migration, part 2: move blocker-reminders and skill-update to the edge'
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

Part 2 of the recipe migration. Move the `blocker-reminders` (244-line
`blocker_reminders.py`) and `skill-update` (434-line `skill_update.py`) jobs
out of core into `coga_edge.blocker_reminders` and `coga_edge.skill_update`,
and remove both `runner.RECIPES` entries. Both packaged
recurring shims (`recurring/{blocker-reminders,skill-update}/ticket.py`)
currently call `runner.run_recipe(load_config(), "<name>", [])` and then
subprocess `bump`, so each shim is rewritten to run its edge module.

Done when both jobs run from the edge with unchanged behavior, the names exit
2 through `coga run`, and the checklist below holds.

### Behavior to preserve

- Blocker reminders: scan of `blocked` and `paused` tasks, one reminder per
  unresolved blocker, watermark order and the watermark as a permanent dedup
  key, retry when the watermark write fails (the packaged
  `recurring/blocker-reminders/ticket.md` owns the contract).
- Skill update: rich skill reports and its 0/1/2 results. Keep the distinct
  public skill updater and other skill-management helpers in core for their
  own consumers; only the reporting job moves.

### Surfaces to update in the same PR

Packaged shims and runbooks for both jobs; skills `bootstrap/skill-update`
and `coga/blockers/remind`; plus the shared list below.

### Acceptance

- [ ] Both entries removed; names exit 2; no core stub.
- [ ] Watermark/dedup and 0/1/2 report tests pass against the edge modules.
- [ ] Old stock, customized and parked shims are covered by fixtures.
- [ ] The `skill_update` private `append_report` is deleted in favor of
      `blackboard.append_blackboard_report`.
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

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1272
branch: coga/v1-microkernel-04b-blocker-reminders-skill-update-to-edge

---

## Implement handoff — 2026-11-19

Megalaunch session, Claude Opus 5.5 (`claude-opus-5-5`). Blocker resolved first
(#1245 merged as `133bb5fee`; `coga unblock` recorded it). Branch
`coga/v1-microkernel-04b-blocker-reminders-skill-update-to-edge` from main
`6e0cca987`, rebased onto `48fc239bc` (state-only commit); single commit
`337329c1d`, pushed. No PR (code/open-pr step).

**Coordination:** 04d's PR #1265 (open) edits the same shared surfaces
(`runner.RECIPES`/`RECIPE_ROOTS`, `edge-code-upgrades.md`, `coga/cli`,
`coga-dev/microkernel`, `coga-dev/codebase`, AGENTS.md,
`tests/test_edge_distribution.py` incl. the `edge_wheels` fixture). The runbook
section here is self-contained (own `recipe-shim-callers`/`locate-job`/
`job-fork-copy` commands; existing `callers`/`reconcile` untouched) to keep the
conflict mechanical. Whichever merges second rebases.

### What changed

- **Edge modules.** `git mv` of `src/coga/blocker_reminders.py` →
  `src/coga_edge/blocker_reminders.py` and `src/coga/skill_update.py` →
  `src/coga_edge/skill_update.py`. Logic unchanged. Workers renamed
  `run_blocker_reminders` / `run_skill_update` (no longer recipes). Each module
  has `main(argv=None)` = `runner.run_entry(name, worker, argv, scheduled=True)`
  (skill-update passes `root=target_root`) and a `__main__` block. The private
  `skill_update.append_report` is deleted; the call site uses
  `blackboard.append_blackboard_report`. Imports: stdlib + `coga.*` only.
- **Decision: `scheduled=True` always.** `run_entry` bumps only when
  `COGA_SCRIPT_TASK` names exactly `COGA_TASK_SLUG`'s task, which launch sets
  only for a ticket.py child, so a hand run (`python -m coga_edge.<job>`) never
  advances a task (tested). One entry also makes "module copied over
  `ticket.py`" a complete fork that still completes its step, like phone-home.
  Caveat documented in the runbook: a ported custom shim must drop its own bump.
- **Registry.** Both names removed from `runner.RECIPES`, and `skill-update` from
  `RECIPE_ROOTS`; runner imports neither module. Old names take the existing
  unknown-recipe exit 2; no stub.
- **Shims** (`recurring/{blocker-reminders,skill-update}/ticket.py`):
  `from coga_edge.<mod> import main` / `raise SystemExit(main([]))` (explicit
  `[]`, as before: launch argv is ignored).
- **Shared helpers audit (grep per symbol):** only `runner.py` imported either
  module; `skill_manager` / `coga skill update` stay in core for their own
  consumers. `recurring._pause_origins`, `blackboard.*`, `task_env.*` remain
  shared core.
- **Old callers** (`coga/edge-code/edge-code-upgrades.md`, new section "Recipe-backed
  recurring shims"): two stock shim generations — PR 705 (`df1d06022`, direct
  `coga.<module>` import → now ModuleNotFoundError) and PR 827 (`368ae080b`,
  `run_recipe` + own bump → now unknown recipe); `recipe-shim-callers`
  inventory (matches only old shims, not new shims or fork copies), baseline
  extraction + blob ids, `locate-job`, reuse of `compare`/`replace`, hand-port
  old/new passages, `job-fork-copy` (refuses anything but absent or stock new
  shim). Fixtures `tests/fixtures/edge-migration/{blocker-reminders,skill-update}-old-{705,827}.py`.
- **Docs:** packaged blocker-reminders/skill-update `ticket.md`, skills
  `bootstrap/skill-update` and `coga/blockers/remind` (hand run is now
  `python -m coga_edge.<job>`), `coga/cli` recipe list, `coga/edge-code`,
  `coga/script-tickets`, `coga/recurring/templates`, `coga-dev/microkernel`
  (append_report rule + edge invariants), `coga-dev/codebase` (+gotchas),
  `coga-dev/internals/notifications`, AGENTS.md edge sentence, `skill_manager`
  docstring (no `coga_edge` text in core: purity test).
- **Tests:** `test_blocker_reminders` (new: failed watermark write → retried
  next run, then permanent dedup; `main` bumps only a launched script task;
  `coga run blocker-reminders` exits 2), `test_skill_update` (edge import; hand
  run via `python -m` subprocess reports no-op, never advances the task; removed
  name exits 2), `test_recurring_shims` (edge-shim structural contract;
  headless period launch + failure-surface through the stock edge shims),
  `test_runner` (registry list, removed names exit 2 and absent from
  RECIPE_ROOTS, `--cwd` containment rows run the edge worker through
  `run_reported` with its resolver), `test_packaging` (wheel contains both
  modules; installed smoke stubs the edge workers), `test_edge_distribution`
  (import purity; new `test_documented_recipe_shim_adoption_runs_the_installed_wheel_or_a_fork[package|fork]`:
  stock 827 template override, 827 period, 705 parked copy and a customized
  827 period are inventoried, compared, replaced (customized refused and left),
  optional `job-fork-copy`; then with the installed wheel **read-only** the
  parked shim runs wheel B by hand, `coga launch recurring/blocker-reminders`
  completes the period running wheel B or the local fork (output tag proves
  which), stale `coga run blocker-reminders` exits 2; non-.py state bytes
  preserved), `test_megalaunch`/`test_recurring_activity`/`test_skill_manager`
  path updates.

### Verification (Linux, Pop!_OS 24.04 LTS, Python 3.12.12, `.venv`)

- `python -m pytest -q -p no:cacheprovider` on committed head `337329c1d`,
  merge-base `48fc239bc`, clean tree: **5013 passed, 33 skipped, 0 failed**
  (978 s). An earlier pre-commit run found 2 failures (a missed
  `from coga import skill_update` in test_skill_manager, and `coga_edge` text in
  a core docstring tripping the kernel-purity test); both fixed before commit.
- `coga validate --json` in a disposable copy of `tests/fixtures/seeded-repo`:
  exit 0, 0 issues, 0 fixes (the session env's bare `SLACK_WEBHOOK_URL` had to
  be unset for the CLI).
- Native Windows/macOS receipts: release-only, deferred.
- No code review has run yet (later workflow steps).

### Production line counts (`wc -l`, `6e0cca987` → `337329c1d`)

| File | Layer | Before | After | Note |
| --- | --- | ---: | ---: | --- |
| `src/coga/blocker_reminders.py` | core | 244 | 0 | moved |
| `src/coga/skill_update.py` | core | 438 | 0 | moved |
| `src/coga_edge/blocker_reminders.py` | edge | 0 | 271 | moved; +docstring, `main`, `__main__` |
| `src/coga_edge/skill_update.py` | edge | 0 | 460 | moved; −4 private `append_report` (deleted dup), +docstring, `main`, `__main__` |
| `src/coga/runner.py` | core | 364 | 356 | −8: 2 RECIPES, 1 RECIPE_ROOTS entry, 5 import lines deleted |
| `src/coga/skill_manager.py` | core | 2123 | 2123 | docstring only |
| `recurring/blocker-reminders/ticket.py` | script | 25 | 8 | shim rewritten; own bump deleted (run_entry) |
| `recurring/skill-update/ticket.py` | script | 25 | 8 | same |

Core −690; edge +731; scripts −34; net production +7. Relocation, not
reduction. Deleted: one duplicate `append_report`, two registry entries, one
root-resolver entry, two shim-local bump implementations. Docs/packaged
definitions +186/−33; tests +337/−65 plus 96 lines of new old-shim fixtures
(`git diff --numstat`).

### Rollout plan for this repo (not performed here)

After merge, and after installing the new wheel in every writer (runbook step 2
quiesce first): `coga/recurring/{blocker-reminders,skill-update}/ticket.md` are
state-only carriers, so future periods copy the new packaged shim
automatically. The one frozen caller is the period shim
`coga/tasks/recurring/blocker-reminders/ticket.py` (stock PR-827 blob
`035f27cb`; period currently `status: done`). If that period is resumed rather
than replaced, run the runbook `compare`/`replace` with `JOB=blocker-reminders`
before the next sweep, otherwise it fails with `unknown recipe`. No skill-update
period, parked copy or customized copy exists (`recipe-shim-callers` inventory
on main: only that file).

Filed as draft `v1/microkernel/11-roll-out-the-04b-edge-shims-on-this-repo-s-blocker`
(open-pr step, 2026-11-19); the merge does not discharge it.

---

## Peer review

Direct review by Codex completed independently of Claude Opus 5.5's
implementation. Final reviewed head `23e60fa0f07b4d85a1e39c4867c52021614fce39`, base `e190b7ebdd405bc332c1874cab0fdd688c65aa31`.
Codex authored the peer-review corrective commit and checked its final diff.

- Fixed a lifecycle regression in the new entrypoints. A manual invocation
  could inherit a valid launched script's task metadata and complete the outer
  task. Packaged shims now opt in explicitly. The standalone `ticket.py` fork
  still completes its launched step, and module entrypoints default to manual.
- Confirmed the reminder worker's post-before-watermark order and skill-update's
  report and 0/1/2 paths, registry removals, shared publication and bump contract,
  and standard-library/shared-core dependency boundary. Verified the old-shim
  runbook preserves customized files until deliberately hand-ported, including
  `--no-pr` with the read-only installed wheel. No remaining must-fix findings.
- In a real TTY using a disposable seeded repo, ran
  `python -m coga_edge.blocker_reminders` and
  `python -m coga_edge.skill_update --no-pr`. Saw the expected no-op status
  and report. Both removed names through `python -m coga.cli run` displayed
  the unknown-recipe diagnostic and exited 2.
- Linux full suite: 5013 passed, 33 skipped, 0 failed in 1126.05 s. Python 3.11 focused: 138 passed, 0 skipped, 0 failed in 59.57 s.
  Native Windows and macOS deferred to release.

Final production line counts below use `wc -l` at the base and head above.
Shim paths are relative to the packaged `templates/coga/recurring/` directory.

| Path | Layer | Base | Head | Change |
| --- | --- | ---: | ---: | --- |
| `src/coga/blocker_reminders.py` | core | 244 | 0 | Moved |
| `src/coga/skill_update.py` | core | 438 | 0 | Moved, private report wrapper removed |
| `src/coga_edge/blocker_reminders.py` | edge | 0 | 270 | Moved worker, added entrypoint |
| `src/coga_edge/skill_update.py` | edge | 0 | 459 | Moved worker, added entrypoint |
| `src/coga/runner.py` | core | 364 | 356 | Removed two recipes and one resolver |
| `src/coga/skill_manager.py` | core | 2123 | 2123 | Docstring only |
| `blocker-reminders/ticket.py` | script | 25 | 8 | Replaced local bump with shared entry |
| `skill-update/ticket.py` | script | 25 | 8 | Replaced local bump with shared entry |

Production changes primarily relocate the workers. Deletion accounts for the private report wrapper, registry wiring and shim-local bumps. Documentation and packaged definitions excluding executable shims: +189/−36. Tests and their fixtures: +439/−66 (git diff --numstat).

## PR

```yaml
title: Move blocker-reminders and skill-update jobs to the edge
author: claude
author_evidence: Claude Opus 5.5 (claude-opus-5-5) implemented this in the 2026-11-19
  megalaunch implement session; commit 337329c1d.
head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
depth: skim
rationale: The worker behavior is preserved and the changes to invocation and migration
  are bounded. Skim the explicit scheduling selection and the operator procedure for
  migrating old local shims.
implementation: Both jobs move to coga_edge and use the shared report, publish, and
  bump sequence. The registry names and the skill-update resolver entry are removed.
  The skill-update report uses the shared appender. The runbook migration is tested
  with stock, customized, and parked callers, a read-only wheel, and a local fork.
deviations: Packaged shims explicitly pass scheduled=True. A full fork installed as
  ticket.py also opts in. The module entrypoints default to manual execution even
  with inherited script attribution. Custom shims must opt in and remove their old
  separate bump.
limitations: 'Native Windows and macOS verification deferred to release. The separate
  rollout to this repository''s frozen blocker-reminders period remains pending. Shared
  surfaces overlap with PR #1265.'
files:
  AGENTS.md: Name the jobs now shipped as edge implementations and that a moved job
    leaves runner.RECIPES.
  docs/contexts/coga-dev/codebase/SKILL.md: Map the two edge job modules.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Describe the edge-shim shape for
    these jobs.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Point the producer inventory
    at the moved module.
  docs/contexts/coga-dev/microkernel/SKILL.md: Record the append_report deletion rule
    and the jobs' edge placement.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Remove both
    names from the recipe list.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Document
    the jobs' fork boundary.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md: Ship
    old-shim inventory, baselines, locate, hand-port and fork-copy procedure.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Distinguish
    registry shims from edge shims.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Mention
    run_entry for edge code.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/skill-update/SKILL.md: Update
    invocation and hand-run contract.
  src/coga/resources/templates/coga/bootstrap/skills/coga/blockers/remind/SKILL.md: Update
    invocation and hand-run contract.
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md: Name the
    edge job the shim runs.
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py: Import
    shim running the edge main.
  src/coga/resources/templates/coga/recurring/skill-update/ticket.md: Name the edge
    job the shim runs.
  src/coga/resources/templates/coga/recurring/skill-update/ticket.py: Import shim
    running the edge main.
  src/coga/runner.py: Remove both registry entries, the resolver entry and imports.
  src/coga/skill_manager.py: Docstring no longer names the moved module.
  src/coga/blocker_reminders.py: Moved to the edge.
  src/coga/skill_update.py: Moved to the edge.
  src/coga_edge/blocker_reminders.py: Move the reminder worker and expose the shared
    entry sequence with explicit scheduled mode.
  src/coga_edge/skill_update.py: Move the reporting worker, share the appender, and
    expose the shared entry sequence with explicit scoped scheduling.
  tests/fixtures/edge-migration/README.md: Describe the old-shim baselines.
  tests/fixtures/edge-migration/blocker-reminders-old-705.py: Stock PR 705 baseline.
  tests/fixtures/edge-migration/blocker-reminders-old-827.py: Stock PR 827 baseline.
  tests/fixtures/edge-migration/skill-update-old-705.py: Stock PR 705 baseline.
  tests/fixtures/edge-migration/skill-update-old-827.py: Stock PR 827 baseline.
  tests/test_blocker_reminders.py: Edge import; watermark retry; main bump gating;
    removed name.
  tests/test_edge_distribution.py: Exercise installed-wheel adoption for old shims,
    the documented hand-port with custom argv, and a complete local fork.
  tests/test_megalaunch.py: Edge import.
  tests/test_packaging.py: Wheel contents; installed smoke stubs the edge workers.
  tests/test_recurring_activity.py: Moved module path.
  tests/test_recurring_shims.py: Edge shim contract and end-to-end launches.
  tests/test_runner.py: Registry list, removed names, cwd containment via edge worker.
  tests/test_skill_manager.py: Edge import.
  tests/test_skill_update.py: Edge import; hand run via python -m; removed name.
checks:
- command: TERM=dumb TMPDIR=/home/n/Code/.coga-review-tmp .venv/bin/python -m pytest
    -q -p no:cacheprovider
  status: passed
  head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
  base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
  detail: Pop!_OS 24.04 LTS, Python 3.12.12. 5013 passed, 33 skipped, 0 failed in
    1126.05 s.
- command: TERM=dumb TMPDIR=/home/n/Code/.coga-review-tmp /home/n/Code/.coga-review-tmp/py311/bin/python
    -m pytest -q -p no:cacheprovider tests/test_blocker_reminders.py tests/test_skill_update.py
    tests/test_runner.py tests/test_recurring_shims.py tests/test_edge_distribution.py
  status: passed
  head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
  base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
  detail: Pop!_OS 24.04 LTS, Python 3.11.15. 138 passed, 0 skipped, 0 failed in 59.57
    s.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json
  status: passed
  head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
  base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
  detail: Disposable copy of the seeded repo. Exit 0, five successful checks, zero
    issues, zero fixes.
- command: git diff origin/main...HEAD --check
  status: passed
  head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
  base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
  detail: Exit 0.
- command: Native Windows and macOS full suites
  status: not-run
  detail: Deferred to release per coga-dev/testing.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 23e60fa0f07b4d85a1e39c4867c52021614fce39
  base: e190b7ebdd405bc332c1874cab0fdd688c65aa31
  detail: Direct Codex peer review completed. Codex fixed a manual-run lifecycle regression
    and exercised the documented customized shim migration. Final re-review found
    no remaining must-fix issues.
```

## Implement attempt — 2026-11-16 (not started)

Precondition unmet: the body requires `v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`
merged first. Its PR https://github.com/FastJVM/coga/pull/1245 is still OPEN and
`origin/main` (5e1e4b129) lacks `runner.run_entry`, `runner.RECIPE_ROOTS`,
`state_sweep` and the per-job `target_root` resolvers this migration builds on.
No branch created, no code changed. Resume from current main once #1245 merges
(04's handoff: delete the `RECIPE_ROOTS` entry with the registry entry and pass
`root=target_root` to `run_entry`).

---

## Blockers

- [x] [2026-11-16 22:18] [agent:claude] id=20261116T221808 Waiting on v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co: its PR #1245 (runner.run_entry, RECIPE_ROOTS, state_sweep) is not merged, and this migration must start from main after that merge.
  resolved: [2026-11-19 09:33] [human:nicktoper] Precondition met: PR #1245 (v1/microkernel/04) merged 2026-11-19T01:31Z as 133bb5fe; origin/main now has runner.run_entry, RECIPE_ROOTS and state_sweep. Proceed from current main.

---

## Blocker reminders

- 95826f51edb1 last_reminded: 2026-11-18 09:02
