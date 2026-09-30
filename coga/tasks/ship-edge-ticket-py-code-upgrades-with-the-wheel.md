---
title: Ship edge ticket.py code upgrades with the wheel
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (implement)
agent: claude
---

## Description

Coga ships code that is not in core, such as a recurring template's `ticket.py`, as packaged template files. `coga init` copies them into the repo. After that, `pip install -U coga` updates `src/coga/` but leaves every existing repo running its old copy of the edge code. The only way the new copy arrives is a template sync, if one happens at all.

PR 880 (phone-home telemetry) turns this into a real problem: following the microkernel rule, it moves roughly 340 lines of telemetry logic out of `src/coga/telemetry.py` and into `coga/recurring/phone-home/ticket.py`. A fix to that code, or to its closed payload, would then never reach repos initialized earlier.

Owner direction (2026-09-23, in chat): "upgrade: needs to be written in a ticket, we'll fix it and move it back into the wheel."

### Agreed direction

Owner selected in the attended design session on 2026-09-30:

1. **Thin repo-owned shim, wheel-owned default implementation.** Ship edge
   implementations in a separate `coga_edge` Python package in the same Coga
   distribution and wheel. The repo still owns the executable `ticket.py` and
   can replace it with a local fork. Core must not import the edge package.
2. **One-time reviewed migration for existing repos.** Installing a wheel does
   not discover or rewrite repositories. Existing full copies must adopt the
   shim once; thereafter implementation fixes follow wheel upgrades without
   a template sync. Preserve customizations for manual reconciliation and
   leave running periods untouched until stopped.

This gives up a complete implementation snapshot in each default period task:
the frozen shim calls the installed wheel, just as existing recipe shims call
installed core. Reproducibility requires retaining the wheel version as well
as the repo revision. An explicit full local fork retains local behavior but
does not automatically receive upstream implementation fixes. Repo-owned
markdown, schedules, workflows, and shims still require reviewed edits when
their own contracts change.

### Acceptance criteria

- [ ] The Coga wheel and editable install include `coga_edge`, with phone-home
  implemented in `src/coga_edge/phone_home.py`. There is no second distribution,
  install step, dependency version, entry-point registry, or public CLI command.
  Production code under `src/coga/` does not import or path-load `coga_edge` or
  ticket implementations. Edge code imports only appropriate shared core
  infrastructure; moving a job into this package does not make it kernel code.
- [ ] Both `coga/recurring/phone-home/ticket.py` and its packaged template twin
  are byte-identical thin shims that invoke the wheel implementation's `main`
  and return its exit code. No job logic or duplicate completion lives in the
  shim. Fresh init installs that shim; recurring creation copies it unchanged.
  Existing period shims use the currently installed implementation even when
  the originating template has since changed or disappeared.
- [ ] An installed-wheel A-to-B test reuses one initialized repo and one
  already-materialized period shim. After replacing A with B, the next script
  process demonstrably runs B's implementation without init, recreation,
  template sync, or repo source writes. Verify both the recurring-template
  invocation and the period invocation, with fake transport and admission
  suppression retained. Distinguish implementation behavior, not merely the
  distribution's reported version.
- [ ] A local full implementation replacing a template's `ticket.py` runs as
  that repo's fork; new periods copy it. A fork placed in an existing period
  remains that period's implementation regardless of template or wheel changes.
  Wheel installation and normal launch never overwrite, merge, or bypass
  either copy. Test each case across A-to-B installation. A missing edge module
  fails visibly through normal script failure; it never falls back to an old
  bundled implementation or an agent with a success result.
- [ ] Phone-home retains its existing closed payload, admission gates, opt-out,
  parent state/cursor, locking/publication, deadlines, loss semantics, receipt,
  report, and failure behavior. Its private worker subprocess executes the
  same selected implementation as its parent, including a full local fork.
  Launch still requires no agent or TTY for successful deterministic completion;
  completion remains one CLI bump after success, and bump failure propagates.
  Direct invocation outside a launch still prints its report without advancing
  a task. No new telemetry event, field, endpoint, configuration, or bypass.
- [ ] The packaging topic documents an executable operator procedure for
  adopting shims in existing repos, including baseline comparison, customized
  files, existing and parked period copies, running sessions, and rollback.
  Demonstrate the procedure against an old full-code fixture with parent
  telemetry state and an existing period. Preserve ticket frontmatter,
  blackboards, `period_state`, generation, workflow, and unrelated attachments.
  Unknown or edited source is preserved for review, never assumed upstream
  merely because its path is familiar or Git reports a clean tree.
- [ ] The distribution contract covers explicit ordinary Python attachments
  as well as reserved `ticket.py`: each future edge worker gets a direct module
  entry point or a plain attachment shim as needed, with no generic dispatcher
  and no expansion of automatic copying or execution. The later recipe-removal
  ticket uses the same reviewed migration policy for old shims and old Dream
  Phase 1/5 instructions in templates and outstanding periods before removing
  their registry targets. A representative migration fixture proves those
  instructions are inventoried and reconciled; this ticket does not remove
  recipes or implement the future Dream workers.
- [ ] Owning topics and packaged twins describe the settled placement, upgrade,
  override, and migration rules. Telemetry and its operations topic identify the
  new implementation/key location and retain the existing operational safeguards.
  No current surface claims all default telemetry logic remains in a copied
  `ticket.py`, or that an installer upgrades legacy copies automatically.
- [ ] Relevant behavioral tests, installed-wheel upgrade/fork tests, twin tests,
  pristine-tree wheel build, CLI smoke, full pytest suite, and validation pass.
  Record exact commands and counts. Adapt existing telemetry transport guards
  to the moved module; do not turn off CI/pytest suppression or contact PostHog.

### Proposed shape

#### Distribution and execution

Add a deliberately small `src/coga_edge/` package with `__init__.py` and
`phone_home.py`. Add `src/coga_edge` to the wheel's `packages` list in
`pyproject.toml`; retain the existing resource exclusions and force-includes.
There is one distribution version and one install transaction. Verify both
editable imports and installed-wheel imports from outside the source checkout.

Move the phone-home implementation, including `run_phone_home`, `main`, the
private worker entry, and constants, from the current ticket script into
`src/coga_edge/phone_home.py`. This becomes its sole canonical implementation;
there is no full implementation twin under the recurring templates. Replace
the live and packaged reserved scripts with ordinary imports of `main` behind
the `__main__` guard. Keep the stable entry function within this distribution
shape so routine implementation releases do not require new shims.

Keep `src/coga/launch_script.py`, `script_entry_point` and `run_script_phase`,
and `src/coga/recurring.py`, `_create_at_slug`, on their existing execution and
copying contract. No local-file hash checks, package resolution by slug,
fallback dispatch, automatic migration, or template refreshing enters launch.
The shim, not core, chooses the edge implementation. The package has no eager
imports or job side effects in `__init__.py`.

Preserve phone-home's self-subprocess structure: `_bounded_worker` can continue
to execute its own `__file__` with the private worker arguments, provided the
module retains the matching `__main__` worker dispatch. This selects the
wheel's module by default and the copied implementation for a local full fork.
Retain `_PACKAGE_FILE` admission evidence for the installed Coga dependency and
the implementation's own path, cwd, and target checks. Transport tests must
exercise this child entry as well as the in-process worker functions.

#### Local edits and the one-time migration

Use a documented, bounded operator migration with ordinary file and Git
operations, not a new permanent CLI or recurring updater. The packaging topic
owns the procedure and commands for finding the installed implementation and
template resources using the same interpreter that runs Coga. Its runbook must:

1. Inventory the affected recurring templates and materialized period copies,
   including paused/blocked/parked copies that could later be resumed. For
   recipe removal, inventory the exact old command references in both template
   and period bodies too. Do not infer ownership solely from a slug or filename.
2. Quiesce affected launches/sweeps across the participating checkouts before
   changing the wheel or executable files. Wait for a running script/worker
   to exit or explicitly stop its session; a ticket status alone is not proof
   that no process is executing. An already-running process is not promised a
   hot upgrade. Leave its code and frozen instructions untouched while it runs.
3. Obtain the old shipped source from the known installed/released artifact
   and compare exact file bytes. Git cleanliness alone cannot distinguish a
   committed local customization from upstream. Keep unknown baselines and
   differences as review items. Use old/new artifact diffs to reconcile
   affected instruction passages without replacing whole tickets or state.
4. Install the new wheel in the operator's existing environment. Prepare a
   reviewed repo diff replacing proven stock full scripts with the packaged
   shims, both in the parent template and in each outstanding period selected
   for continued execution. For edits, explicitly choose a port to the new
   implementation or a retained full local fork. Do not reset parent markers,
   regenerate periods, or auto-complete/cancel tasks to obtain new files.
5. Merge the reviewed migration through normal repo practice, ensure each
   executing checkout and interpreter have the corresponding repo/wheel pair,
   and resume. Test the migration in a scratch fixture with suppressed/fake
   delivery; do not run production phone-home merely to inspect its source.
   If rolling back, restore a compatible wheel and the reviewed executable
   changes together; never roll back telemetry state or audit history.

This ticket supplies and tests the migration procedure; it does not authorize
editing external client repos or performing a fleet rollout. Unmigrated legacy
copies continue to be legacy copies, and are explicitly outside the promise of
automatic implementation upgrades. Upstream fixes apply on the next process
invocation after a migrated repo upgrades its wheel.

For customization after adoption, document how to locate and inspect the
installed plain Python implementation, copy the complete self-contained module
over the repo's `ticket.py`, and commit the fork. Merely editing a wrapper that
still imports the default module is not an implementation fork: its imported
behavior still follows the wheel. A fork must maintain compatibility with the
shared core it imports. Restoring the stock shim rejoins wheel updates.

#### Follow-on recipe migration

`gigantic-refactor-move-recurring-recipes-out-of-co` must consume this approved
shape, replacing its proposed full copied implementations with wheel-owned
edge modules and repo shims. Ordinary Dream attachments can be direct module
invocations from explicit instructions or thin named attachment wrappers;
neither becomes an automatic phase. No general attachment copying is added.

For that later release, old `coga run` instructions and old shims are part of
the same one-time reviewed migration. Its implementation must inventory and
reconcile actual old Dream Phase 1/5 passages in templates and outstanding
periods, preserving other instructions and all lifecycle state. Running
periods finish under the old wheel or are explicitly stopped before migration.
Customized callers of removed core symbols/recipes require reconciliation,
not a claim that retaining their bytes preserves compatibility. Do not ship
that contraction as an unattended wheel-only upgrade to unmigrated testers;
record adoption of the required migration before their upgrade. No indefinite
forwarders or legacy registry are introduced by this ticket.

#### Tests and documentation

Update `tests/conftest.py`, `load_phone_home` and
`_reject_production_telemetry`, to target the canonical edge module while
preserving test isolation. Adapt `tests/test_telemetry.py` to the moved symbols,
and retain subprocess coverage of the thin shim and private worker. Extend
`tests/test_packaging.py` to assert the edge package ships, source and installed
imports work, and fresh init still produces the expected shim and unused state.

Add an isolated two-wheel regression: build A and B with an observable,
fixture-only implementation difference; initialize once under A, materialize a
period, install B into that same environment, and launch fresh subprocesses
from outside the source tree. Assert B's implementation is selected without
touching source copies. Repeat for template and period forks and for the
documented legacy-to-shim migration. Use fake transport with production gates
preserved; no production test hooks are needed. A missing-module test must
exercise the actual launch failure path without agent fallback. Include
legacy Dream instruction fixtures to make the later migration boundary
reviewable without moving its recipes here.

Update `coga/packaging` as owner of distribution/adoption/override mechanics;
`coga/extension-model` as owner of the one-way core/edge import boundary;
`coga/telemetry` as owner of phone-home's location and execution contract; and
`coga/telemetry/operations` for source inspection, key rotation, and operational
invocations. Update the source map in `coga/codebase` and summarize/link the
new option in `coga/script-tickets` and `coga/recurring/templates`. Fix affected
cross-references and each packaged twin in the same implementation PR.
Keep the design on this ticket until implementation; do not publish proposed
behavior as already shipped in the contexts during the design step.

### Out of scope

- Automatic repository rewriting during package installation, launch, or sweep;
  a template-sync service, digest manifest, new updater command, or plugin API.
- Moving other recipes, removing registry entries, implementing Dream workers,
  or changing generic attachment copying. The dependent refactor owns those.
- Changes to init's existing-repo behavior, `upstream-coga`, or skill-update.
  None is the owner of wheel code delivery or this one-time operator migration.
- Telemetry feature/schema changes, production ingestion proof, credential
  rotation, new config/frontmatter fields, or edits to `coga.toml` and
  `coga.local.toml`.
- Automatic synchronization of local forks, hot replacement of running code,
  complete per-period dependency pinning, or migration of external repos in
  this implementation PR.

### Related
- PR 880 / `marketing/add-telemetry`
- `recurring-sweep-wedges-on-the-ticket-py-it-copies`
- `gigantic-refactor-move-recurring-recipes-out-of-co` (the other recipes will hit the same issue)

## Context

Code facts below are the design-time snapshot; verify the named caller/callee
relationships before implementing.

- `src/coga/commands/init.py`, `_do_init`, calls
  `src/coga/commands/update.py`, `copy_fresh_templates`, to seed non-bootstrap
  resources. `_setup_initialized_clone` only repairs local setup and refuses
  a configured re-init. Neither updates existing recurring source files.
- `src/coga/recurring.py`, `Template.script_entry_point`, supplies the source
  that `_create_at_slug` copies into a created period; only `ticket.py` travels.
  `src/coga/launch_script.py`, `script_entry_point`, selects that local sibling,
  and `run_script_phase` subprocesses it after reloading moving launch state.
- `coga/recurring/phone-home/ticket.py`, `main`, wraps `run_phone_home` in
  `src/coga/runner.py`, `run_reported`, then invokes CLI bump after success.
  `_bounded_worker` executes the implementation file with `--worker`, handled
  by `_worker_main`. Its packaged twin is currently the same full implementation.
- `tests/conftest.py`, `load_phone_home`, path-loads that packaged script;
  `_reject_production_telemetry` patches its transport and test capture key.
  `tests/test_packaging.py`, `test_installed_wheel_init_and_phone_home_are_isolated`,
  covers fresh init with the installed artifact, not an upgrade. Its
  `test_live_and_packaged_copies_stay_identical` remains the shim/topic twin gate.
- `coga/recurring/upstream-coga/ticket.py`, `sweep`, turns client findings into
  tickets. `src/coga/skill_update.py`, `run_skill_update_recipe`, orchestrates
  installed skill updates. These are unrelated mechanisms, despite their names.
- Cite rather than attach `coga/packaging`
  (`docs/contexts/coga/packaging/SKILL.md`), sections “Canonical copies and twins”
  and “Wheel packaging”: preserve twin discovery and verify a pristine build.
- Cite rather than attach `coga/extension-model`
  (`docs/contexts/coga/extension-model/SKILL.md`), “The microkernel rule” and
  “Choosing a home”; and `coga/principles`
  (`docs/contexts/coga/principles/SKILL.md`), “Hackable” and “Memory via PR”.
  Ship ticket-owned code without core imports or silent repo rewrites.
- Cite rather than attach `coga/script-tickets`
  (`docs/contexts/coga/script-tickets/SKILL.md`), “Classifier”, “One deterministic
  phase”, and “Chaining”; and `coga/recurring/templates`
  (`docs/contexts/coga/recurring/templates/SKILL.md`), “The template-to-period
  transform”. Keep local classification, environment, copying, and completion.
- Read all of `coga/telemetry` (`docs/contexts/coga/telemetry/SKILL.md`) and
  `coga/telemetry/operations`
  (`docs/contexts/coga/telemetry/operations/SKILL.md`) before the move; cited
  rather than attached because these are explicit owning-topic edit targets.
  The existing closed data and production suppression contracts must survive.
- Cite rather than attach `coga/testing`
  (`docs/contexts/coga/testing/SKILL.md`), “Commands” and “CI posture and receipts”;
  `coga/project-stage` (`docs/contexts/coga/project-stage/SKILL.md`),
  “Compatibility is migration-only”; and `coga/knowledge`
  (`docs/contexts/coga/knowledge/SKILL.md`), “Narrative links, never restates”.
  Use a bounded migration, exact test receipts, and one owning topic per fact.

<!-- coga:blackboard -->

## Design investigation (2026-09-30)

- Two copies can become stale: `src/coga/commands/update.py`,
  `copy_fresh_templates`, seeds the recurring template from package resources;
  `src/coga/recurring.py`, `_create_at_slug`, then copies only its reserved
  `ticket.py` into the period task. Updating a template alone does not update
  an existing period. Other attachments are not copied.
- `src/coga/launch_script.py`, `script_entry_point` and `run_script_phase`,
  classify the exact sibling and subprocess it with the current interpreter,
  no operands, host-repo cwd, and scoped task environment. Core does not import
  the script. Preserve this boundary unless the design explicitly changes it.
- `src/coga/commands/init.py`, `_setup_initialized_clone`, performs local
  setup, not an upgrade. `coga/recurring/upstream-coga/ticket.py`, `sweep`,
  collects client findings into tickets; it is not a distribution mechanism.
  `src/coga/skill_update.py`, `run_skill_update_recipe`, concerns installed
  skills, not recurring template code.
- Phone-home already lives at the edge: `coga/recurring/phone-home/ticket.py`
  and its packaged twin hold `run_phone_home`, `main`, and `_worker_main`.
  `_bounded_worker` subprocesses `__file__`, so moving the implementation must
  preserve the private worker entry as well as the normal entry. Preserve
  admission, closed payload, state reservation, bounded delivery, reporting,
  and CLI completion semantics; this task does not redesign telemetry.
- `tests/conftest.py`, `load_phone_home`, loads the packaged script by path
  and `_reject_production_telemetry` intercepts its transport.
  `tests/test_packaging.py`, `test_installed_wheel_init_and_phone_home_are_isolated`,
  covers a fresh install only. Add an actual old-to-new wheel regression,
  existing period coverage, and local-override coverage during implementation.
- Dependency: `gigantic-refactor-move-recurring-recipes-out-of-co` is at
  owner `review-design`. Its Description explicitly requires this distribution
  policy first, including ordinary Dream attachments and old Phase 1/5 commands
  in template and period bodies before registry names disappear. This ticket
  must define the migration boundary or explicitly resolve that dependency;
  a new shim alone cannot repair old copied code or old instructions.
- Relevant contracts read: product/vision, coga/principles, extension-model,
  packaging, init, script-tickets, recurring/templates, telemetry and
  telemetry/operations, knowledge, testing, project-stage. Project-stage permits
  a bounded migration of shipped surfaces, not indefinite compatibility paths.

## Owner decisions (2026-09-30)

- Selected **thin shim + wheel-owned default implementation** in the attended
  session. Keep job logic outside `coga.*`; local customization is an explicit
  repo-owned fork. Subsequent wheel upgrades update the default implementation
  without rewriting the shim or adding launch-time source synchronization.
- Approved **one-time reviewed migration** for existing repositories. Inventory
  templates and period copies, reconcile customizations manually, and leave
  executing periods untouched until stopped. The automatic-upgrade promise
  starts after adoption; it does not cover legacy full copies or local forks.

## Design result

The specification is under `## Description` with nested acceptance criteria,
proposed shape, and out-of-scope sections. `## Context` names the verified
symbols and focused topic sections. Proposed package: `src/coga_edge`, shipped
in the existing wheel; phone-home is the first consumer, and launch/core never
imports it. Packaging owns the bounded migration runbook. The dependent recipe
refactor must adapt its implementation placement and migrate old Dream commands
before deleting their registry targets; that refactor remains separate work.

## Open Questions

None. Both distribution and legacy adoption choices were answered by the owner
in this attended session. Independent evaluation and owner review still follow.

No code, branch, or PR created. Only this ticket was edited during design.

## Design verification

- `coga validate --task ship-edge-ticket-py-code-upgrades-with-the-wheel --json`:
  `ok_count: 1`, no issues.
- `git diff --check`: clean.
- A `PYTHONPATH=src python` read-only check using
  `coga.compose._extract_section` confirmed all three specification subsections
  compose under Description, Context is present, the blackboard fence is unique,
  and frontmatter is byte-identical to HEAD. The first ambient-Python attempt
  could not import `coga.compose`; the source-path rerun passed.
- No implementation tests run: this step changes only the design ticket.

## Evaluator review

Reviewer: claude (cold evaluate-design pass, 2026-09-30). No ticket-body,
code, branch, or PR changes.

**Verdict: the direction is sound and can be implemented. Resolve the three items
below before implementation.** Each one is a place where an implementer would
otherwise have to guess what "done" means.

### Verified claims

- `coga/recurring/phone-home/ticket.py` (373 lines) is byte-identical to its
  packaged twin. It holds `run_phone_home`, `main`, `_worker_main`, and
  `_bounded_worker`, and the last of these subprocesses `Path(__file__).resolve()`
  with `--worker`. The `__main__` guard dispatches `--worker`. `_PACKAGE_FILE`
  is `Path(coga.__file__)`, and `_admitted` checks `_PACKAGE_FILE`,
  `Path(__file__)`, `repo_root`, and cwd against `_development_tree`.
- The script imports only stdlib and `coga.*` (no sibling imports), so a
  full-module fork copied from the wheel is feasible today.
- `pyproject.toml` `packages = ["src/coga"]`. The dev `.venv` editable `.pth`
  points to `src/`, so `src/coga_edge` becomes importable in editable mode
  without a reinstall.
- `docs/contexts/coga/script-tickets` "One deterministic phase" step 5: a
  non-zero script exit posts `💥 script failed` and launch exits with that
  code. A shim `ImportError` therefore already fails visibly with no agent
  fallback, so AC4's missing-module clause can be tested as written.
- `tests/conftest.py` `load_phone_home` path-loads the packaged script as
  `phone_home_ticket`. `_reject_production_telemetry` patches that module
  object. `tests/test_telemetry.py` spawns `PHONE_HOME_SCRIPT --worker` directly
  (`test_real_worker_inherits_test_gate`) and fakes `__file__` in
  `test_admission_all_gates_and_symlinks`.
  `test_packaging.py::test_installed_wheel_init_and_phone_home_are_isolated`
  uses `pip install --target` + `PYTHONPATH` rather than a venv, and it
  path-loads the repo `ticket.py` to read `_PACKAGE_FILE`, which a shim will no
  longer have.
- The telemetry topic ("Weekly usage snapshots", "Transport and reports") and
  `telemetry/operations` (`POSTHOG_CAPTURE_KEY` location, release-verification
  invocation) name `ticket.py` as the implementation, so both need edits as
  planned. Dream's template has literal `coga run` passages (`validate-drift`,
  `cleanup-orphan-markers`, `delete-task`), so the AC7 fixture has real
  material to model.

### Must resolve before implementation

1. **AC6 and AC7 require proof of a manual procedure without defining what the
   proof observes.** "Demonstrate the procedure against an old full-code
   fixture" and "a representative migration fixture proves those instructions
   are inventoried and reconciled" can be read as a pytest test, a recorded
   manual run, or a scripted runbook. Out of Scope forbids an updater command,
   so a test can only run the runbook's literal commands. Specify the
   assertions. Suggested:
   (a) the runbook's documented inventory commands, run on the fixture, list
   exactly the parent template, the outstanding and parked period copies, and
   (for AC7) each old `coga run` passage in the template and period bodies;
   (b) the byte comparison classifies a stock copy as replaceable and an edited
   copy as a review item;
   (c) after the documented replacement, frontmatter, blackboard,
   `period_state`, generation, workflow, unrelated attachments, and non-target
   body text are byte-identical, and the next script run uses the shim.
   Also say whether AC7 reconciliation is asserted, or only the inventory is
   asserted (this ticket rewrites no Dream text).
2. **The fork contract depends on an unstated module constraint.** A "complete
   self-contained module" copied over `ticket.py` works only if
   `coga_edge/phone_home.py` imports only stdlib and shared `coga.*` (never a
   sibling `coga_edge` module or a relative import), and if it carries its own
   `__main__` dispatch for both the normal and `--worker` entries. Put both in
   an acceptance criterion and in `coga/packaging`. Otherwise a later refactor
   that factors helpers into `coga_edge/_common.py` silently breaks every
   fork and the documented fork procedure.
3. **AC3's invocation surface and install mechanics are ambiguous.**
   - "Verify both the recurring-template invocation and the period
     invocation" does not say whether each goes through `coga launch` (which
     needs git and sync setup in the scratch repo) or through a direct
     `python <path>/ticket.py`. The Proposed Shape says "launch fresh
     subprocesses", and AC5 requires launch semantics.
   - Templates are normally created, not launched, so the "template
     invocation" is presumably a direct run.
   - "Install B into that same environment" fits a venv. The existing test
     uses `--target`, where replacing A means a `--upgrade` reinstall into the
     target directory.

   State one of: "template via direct script run, period via `coga launch` with
   a local bare remote", or "both via direct script run, launch covered
   separately". Also state the install mechanism.

### Recommendations (optional, ordered by impact)

- **Size the migration to the real legacy population.** The phone-home
  `ticket.py` has one upstream revision (`ac14d63fc`, PR 880, 2026-09-23),
  and it landed after the last version bump (`6e505d810`, 0.3.2 on
  2026-09-09). No tagged release carries it, so every legacy full copy comes
  from a main-branch install that still reports 0.3.2.
  - For phone-home, the "known released artifact" baseline is effectively
    the PR 880 blob.
  - The claim that "reproducibility requires retaining the wheel version" is
    weak while `coga_version` does not change between A and B.

  The owner may want the runbook to name the Git blob as a baseline source,
  and may want to note that a version string alone cannot identify an
  unreleased implementation.
- **Import the edge module by name in tests.** `load_phone_home` should use
  `importlib.import_module("coga_edge.phone_home")`, not a path-load under
  `phone_home_ticket`. Otherwise in-process tests that go through the shim's
  `from coga_edge.phone_home import main` bypass the transport and key patches
  applied to a second module object. Subprocess coverage is still protected
  by the inherited `PYTEST_CURRENT_TEST`/`CI` gates.
- **Enforce the one-way import rule with a test.** Add a static (AST or grep)
  test asserting that no module under `src/coga/` imports or path-loads
  `coga_edge`. AC1 states the rule, but nothing would keep it true.
- **Test worker-follows-fork in-process.** With gates preserved, the child is
  never spawned (`_bounded_worker` returns `suppressed` first). To prove that
  the worker runs the selected implementation (AC5) without new hooks, patch
  `_admitted` in-process on the fork module and capture the `Popen` argv, as
  `test_parent_deadline_kills_and_reaps_sleeping_worker` already does, then
  assert that argv[1] is the fork path. Pair this with a direct
  `python <fork> --worker capture` gate test.
- **Build wheels A and B once.** Build them in a module-scoped fixture (or
  derive B by rewriting `coga_edge/phone_home.py` and `RECORD` in a copy of A)
  and reuse them across the template, period, fork, missing-module, and
  migration cases. Nine AC scenarios with repeated `pip wheel` runs would
  noticeably slow the suite.
- **Update the microkernel summaries.** "Everything else stays at the edge"
  is summarized in `AGENTS.md`, `CLAUDE.md`, and `src/coga/resources/prompt.md`
  as well as extension-model and its packaged twin. Per `coga/knowledge`, the
  same PR should add a one-line summary or link for the `coga_edge` shipping
  option so these don't read as "edge code is only a sibling file".
- **Admission scope moves.** `Path(__file__)` will now be the wheel module,
  not the repo's `ticket.py`. The shim's location is still covered by the
  `repo_root` and cwd checks. The telemetry topic should say this explicitly
  so it is not read as a dropped gate.

### Coherence

The scope is one PR, though a large one (nine ACs with wheel-matrix tests).
Proposed Shape, ACs, and Out of Scope agree: no launch, recurring, or init
changes, no updater, and no recipe moves. The `code/design-then-implement`
workflow fits. Keeping `coga_edge` outside `src/coga/`, imported only by
shims, respects the microkernel boundary, provided extension-model records it
as an edge shipping location and not a second core.
