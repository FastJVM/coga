---
title: 'Gigantic refactor: move recurring recipes out of core'
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
step: 3 (review-design)
agent: claude
---

## Description

The owner identified the current pattern as an antipattern on 2026-09-23 while
reviewing PR 880: work belonging to one recurring ticket lives in a core module,
gets registered in `runner.RECIPES`, and is called back through `run_recipe`
from the ticket's otherwise empty `ticket.py`. Registration does not make that
implementation shared. Put ticket-owned deterministic work beside its ticket,
while retaining actual shared infrastructure and individually reviewed command
contracts. Keep the work deterministic and preserve its operational behavior.

Phone-home has already made this move. This ticket audits the remaining ten
registry entries and moves five job implementations: autoclose, blocker
reminders, skill update, validation drift, and orphan-marker detection. Dream's
last two are explicitly invoked attachments, since they run inside its ordered
agent process. The consumer audit below names the survivors and their reasons;
the owner explicitly approved retaining `open-pr` as a named exception on
2026-09-28.

### Acceptance criteria

- [ ] Account for all ten current entries using the production relationships
  in the audit below. Tests, packaged twins, aliases, and the generic runner
  are not extra independent consumers. Apply the test to the behavior/symbol
  being retained: a shared parser does not justify retaining its surrounding
  single-ticket job.
- [ ] Remove `autoclose`, `blocker-reminders`, `skill-update`,
  `validate-drift`, and `cleanup-orphan-markers` from `runner.RECIPES`.
  The fixed registry contains only
  `branch-sweep`, `recurring-scan`, `autofix-analyze`, `open-pr`, and
  `delete-task`. Removed names fail through the existing unknown-recipe
  exit-2 path. There is no fallback registry, dynamic discovery, forwarding
  core stub, or indefinite compatibility alias for them.
- [ ] The three recurring scripts contain their job logic rather than importing
  it from core; Dream owns its two ordinary Python attachments. Delete the
  now-unneeded core modules for blocker reminders, skill update, validation
  drift, and orphan detection. Retain only shared parsing/GitHub support in
  `src/coga/autoclose.py`, as detailed below. Production core code never
  imports, path-loads, or scans an edge implementation.
- [ ] Preserve the existing successful and failing behavior, reports, flags,
  and result data structures of the moved workers. Autoclose keeps the final
  step eligibility checks, notification preflight, partial-failure evidence,
  shared checkout-disposal proofs, durable `retires.md` reconciliation, and
  report-only unanswered review-thread handling. Blocker reminders keep their
  post/watermark order and duplicate suppression. Skill update keeps its
  rich failure/follow-up reports and 0/1/2 results. Validation keeps its safe
  repair set and classifier coverage; orphan detection still reports
  candidates without deleting them.
- [ ] Reserved script execution still needs no agent/TTY and bumps through a
  CLI subprocess only after success. Autoclose runs its own job, then the
  retained branch-sweep recipe, then bumps exactly once; either worker failure
  stops that sequence. Propagate bump failure. Explicit hand invocations of
  moved workers do not advance an inherited task. Dream remains agent-backed,
  with validation at Phase 1 and orphan detection at Phase 5; neither
  attachment bumps, creates a child task, or becomes an automatic launch phase.
- [ ] Every moved worker uses `runner.run_reported` for the existing
  `## Recipe Failure` floor, without registry membership. Preserve real-time
  stderr, original return/exception behavior, bounded ANSI-free diagnostic
  sections, ticket-structure escaping, optional blackboard behavior, and
  best-effort reporting failures. Target selection respects the actual
  operating root, including `--cwd`, `--cwd=...`, abbreviated options,
  invalid arguments, unknown roots, and orphan detection's environment-based
  root. The target root's publication barrier protects the append.
- [ ] Preserve the per-command publication boundary for all moved entrypoints,
  including manual runs and Dream attachments that never bump. After worker
  reporting, use shared publication infrastructure to sweep the operating
  root's task/log/recurring state on success, ordinary failure, and escaping
  exceptions, subject to the existing sweep exclusions. Publication failures
  warn and leave local evidence without replacing the worker's result. Unknown
  targets never fall back to publishing the invoking repo. Verify that reports
  and in-scope safe repairs reach control without a later lifecycle command.
- [ ] After the upgrade prerequisite has landed, both fresh installs and
  previously initialized repos can run the moved code from the installed
  wheel's supported distribution path. Test existing template/period copies,
  named Dream attachments, and local adaptations according to that dependency's
  upgrade policy. Include old Dream Phase 1/5 instructions in initialized
  templates and materialized periods, not just Python files. Removing registry
  names must not leave a runnable old period shim or Dream instruction silently
  referring to a deleted entry.
- [ ] Update the owning contexts, invocation skills, recurring bodies, prompt,
  source map, live references and packaged twins in the same implementation
  PR. `AGENTS.md` and `CLAUDE.md` agree. None implies that registering a recipe,
  needing Python, or being a recurring job proves a core home. Keep the
  existing top-level launch aliases and do not edit `coga.toml` or
  `coga.local.toml`.
- [ ] Behavioral tests exercise packaged edge files and actual script launch,
  including failure recording, absence of unintended agent fallback, and
  completion order. Shared consumer regressions, wheel/twin checks, the full
  test suite, CLI smoke, and task/repository validation receive the verification
  described below. Update fixtures where their old registry calls changed.

### Proposed shape

#### Order and distribution prerequisite

Owner confirmed on 2026-09-28: land
`ship-edge-ticket-py-code-upgrades-with-the-wheel` **before this refactor**.
Its design is currently a draft. Do not implement a second updater, move the
jobs back into importable `coga.*` modules, or settle its local-edit policy
inside this ticket. At implementation start, read its merged contract and
record the chosen delivery mechanism on this blackboard.

The prerequisite must support all code being moved: reserved `ticket.py`
implementations, ordinary Dream attachments, and the transition from existing
copied period shims and old Dream Phase 1/5 commands frozen into template and
period bodies. Delivering new attachments alone does not migrate those commands.
Follow its policy for an already-materialized or running period; do not
overwrite executing code, frozen instructions, or customized copies
opportunistically.
If its merged scope omits one of these cases, resolve that dependency before
contracting the registry. The tradeoff is sequencing delay in exchange for
avoiding more installations stranded on old edge code.

The paths below name logical ticket ownership and the current resource layout.
Use the dependency's approved wheel distribution mechanism at those boundaries;
do not invent a new path resolver here. Keep canonical and packaged twins as
required by the packaging contract then in force.

#### Move the job bodies and keep the shared support

1. Move the job-specific contents of `src/coga/autoclose.py` into
   `coga/recurring/autoclose-merged/ticket.py` and its packaged twin. This
   includes `AutocloseResult`, `ClosedTicket`, `CheckoutOutcome`,
   `ReviewThread`, `sweep_merged`, `run_autoclose_recipe`, checkout/worklist
   orchestration, and review-thread lookup/reporting used only by that job.
   Keep `src/coga/autoclose.py` as a small shared support module for
   `parse_pr_url`, `parse_branch_name`, `parse_worktree_path`,
   `parse_pr_number`, `GhError`, `pr_view`, `pr_state`, `pr_head`,
   `prs_for_head`, and their implementation dependencies. These support the
   existing core callers listed below. Rewrite its module description/exports;
   do not leave re-exports of the moved job. A support-module rename is
   unnecessary for this ticket.
2. Move `src/coga/blocker_reminders.py` into
   `coga/recurring/blocker-reminders/ticket.py` and
   `src/coga/skill_update.py` into `coga/recurring/skill-update/ticket.py`,
   with packaged twins. Keep `blackboard`, `notification`, `skill_manager`,
   and other shared primitives in core. The skill updater's job is the report
   and invocation of `coga skill update`; do not move or duplicate the actual
   shared skill-management implementation.
3. Move `src/coga/dream_validate_drift.py` to
   `coga/recurring/dream/validate_drift.py` and
   `src/coga/dream_cleanup_orphan_markers.py` to
   `coga/recurring/dream/cleanup_orphan_markers.py`, plus packaged twins.
   Update Dream's explicit phase instructions and corresponding invocation
   skills. With today's layout, the explicit commands use
   `python "$COGA_COGA_OS_ROOT/recurring/dream/validate_drift.py"` and
   `python "$COGA_COGA_OS_ROOT/recurring/dream/cleanup_orphan_markers.py"`
   with the interpreter that imports the active Coga package. Keep using the
   current period's inherited `COGA_TASK_*` reporting metadata. These are
   template-owned attachments, not period siblings: current creation copies
   only `ticket.py`. If the prerequisite changes their distribution path,
   update the documented explicit invocation to its supported equivalent.
   Do not add general attachment copying or a Dream `ticket.py`.
4. Give each edge file import-safe worker functions and a guarded `main`.
   Keep callable result objects for behavioral tests; a function need not be
   renamed solely because its old name ends in `_recipe`. Scheduled scripts
   call `run_reported` around their worker and subprocess
   `[sys.executable, "-m", "coga.cli", "bump", slug]` after success.
   Autoclose calls `run_recipe` only for the shared branch sweep. A hand-run
   autoclose worker retains the old autoclose-only scope. Scheduled execution
   must identify its own launch target using the existing script-task metadata
   contract, not merely the presence of `COGA_TASK_SLUG`; hand execution in
   another task must never bump that task.

Keep ordinary Python argv for manual invocation, including skill-update's
`--cwd`/`--pr-title`/`--no-pr` and validation's existing flags. Scheduled
`ticket.py` execution still supplies no operands. Replace removed `coga run`
examples with either the on-demand recurring launch when the whole period is
intended (`coga autoclose`, `coga skill-update`,
`coga recurring launch blocker-reminders`) or the explicit Python worker
invocation when only the old worker/its options are intended. Do not silently
turn an autoclose-only manual example into a branch sweep too.

#### Make failure reporting independent of recipe placement

Keep the already-shared `src/coga/runner.py`, `run_reported`, rather than
creating another reporting subsystem. Add a keyword-only root resolver, for
example `failure_root: Callable[[], Path | None] | None = None`. Omission
uses `cfg.repo_root`; a supplied resolver returning `None` means the target
cannot be established and suppresses the blackboard append, never falls back
to the invoking repo. Evaluate the resolver only on failure, inside the
existing best-effort reporting guard. A resolver exception cannot replace
the worker's original failure.

Move the policy in `runner._failure_root` to its owning edge files. The
skill-update and validation closures use their own `recipe_parser` with
`parse_known_args`, suppressing the second parse's help/errors, and then
`task_env.discover_coga_os_root`. The orphan worker supplies its own
`coga_os_root`. Thus argument refusals remain reportable without duplicating
CLI parsing semantics or making core import edge parsers. The shared
`_record_failure` still resolves `blackboard_from_env(root)` and calls
`append_blackboard_report` using that root's config/barrier. Keep the existing
four-argument `run_reported` call used by phone-home working.

The richer worker reports stay as they are; do not infer that a prior report
makes the generic failure section redundant. No subprocess fd-capture redesign
or guaranteed reporting of failures before the wrapper starts is implied.

#### Preserve the entrypoint publication boundary

Extract the reusable publication boundary from `src/coga/cli.py`,
`_sweep_coga_state`, into shared infrastructure consumed by both the CLI and
the moved edge entrypoints. It reloads the selected root's config and calls
`git.sync_coga_state`; keep the existing publisher, barrier, path scope and
refusal handling. The CLI retains its command/relay admission policy. Shared
execution must respect the withheld-sweep state, and edge entrypoints must
preserve help and retry-without-sweep (exit 75) exclusions. Do not spoof CLI
argv, add a registry entry, or run a lifecycle command merely to publish.

Each edge `main` owns an outer completion boundary around its reported work.
On success, ordinary nonzero return, or escaping exception, attempt the sweep
after `run_reported` has finished its generic failure append. A scheduled
autoclose run encloses both its own worker and the retained branch sweep, so
either worker's failure is reported before publication; only successful work
then reaches the existing single bump subprocess. Manual autoclose encloses
only its own worker. Dream attachments and other manual runs publish at their
own exit without bumping or advancing an inherited task. Keep `run_reported`
itself reporting-only, preserving phone-home and existing registry callers.

The edge owns target selection on both successful and failing exits. Reuse
its parser/root policy described above, including `--cwd` forms and orphan
detection's environment root; supply the established operating root to shared
publication infrastructure. This is a separate publication resolution from
the failure-only `failure_root` callback: do not change that callback's lazy
contract. A missing/invalid target or resolver failure skips publication
without falling back to the invoking config. Load the target's actual config
so its layout and Git settings govern the sweep, including nested Coga roots.

Publication is best effort: config, resolution and publication failures emit
a warning and preserve the worker's original return code or escaping exception
and the local writes. They do not turn a successful worker into a failure or
replace a failed worker's evidence. A successful worker may still bump after
a failed publication attempt, as under existing best-effort semantics; bump
failure itself continues to propagate. Sweep only the existing task/log/
recurring path scope, leaving repairs outside that scope for normal review.
The tradeoff is a small shared-infrastructure extraction to keep the existing
per-command durability attempt while moving job ownership out of core.

#### Rewrite the rule and its callers

`docs/contexts/coga/extension-model/SKILL.md` owns the revised rule and closed
registry inventory: shared infrastructure needs independent production uses;
otherwise a reviewed command exception must name its invariant/transaction.
Registry membership is the result of that review, never the proof. Record
the individually retained commands from this audit rather than a class-wide
allowance for recurring work. Preserve the existing parked-command review
status; this ticket does not settle every command head.

Summarize and link that owner from `AGENTS.md`, `CLAUDE.md`,
`src/coga/resources/prompt.md`, and `coga/codebase`. Update
`coga/recurring/templates` for the reporting helper and delivery mechanism;
`coga/script-tickets`, `coga/dream`, `coga/recurring/scheduling`,
`coga/notifications/producers`, and `coga/notifications/failures` for moved
symbols and invocation changes; `coga/internals/state-publication` for the
shared CLI/edge exit boundary; and `coga/packaging` only where the shipped
resource facts changed. Update the three recurring bodies and skills plus
Dream's body and its two bootstrap skills. Check the dated
`docs/design/cli-extension-audit.md`: retain its historical framing and link
the new decision instead of leaving its old inventory as current guidance.

Search active docs, scripts, templates, tests and pending task instructions
for old imports/commands; fix executable instructions that would break.
Historical run logs and completed-ticket evidence remain historical; do not
rewrite them to pretend old commands never ran. Never edit `coga/log.md`.

#### Verification for implementation

Use `tests/conftest.py`, `load_phone_home`, as the precedent for loading a
packaged edge file by path for tests. Update existing behavior suites to load
the moved code; keep shared parser tests against core. Replace
`tests/test_recurring_shims.py` assertions that require every job to be a
registry shim with behavior checks for the new ownership and completion
boundaries. Include the `tests/test_megalaunch.py` reminder-scan import, which
is test-only and does not justify a production core module.

Exercise worker failures, root refusal/selection and parser refusals through
the edge wrapper, not just by calling worker functions. Keep the
`tests/test_runner.py` cross-root/barrier, stream, exception, bounded-report
and blackboard-structure coverage; include a root-resolver exception and
phone-home's unchanged call. Run both autoclose/branch-sweep order paths and
the standalone branch sweep. Exercise both Dream attachments from a configured
nested Coga root; prove Dream remains agent-backed and that the attachments
write only the inherited period blackboard and do not advance it.

Add entrypoint-level publication checks against disposable Git repositories
with a control ref (including an off-control checkout), inspecting the control
tree after the Python entrypoint exits without a later Coga command. Cover
successful reports and in-scope validation repairs, nonzero worker results,
parser refusals and escaping exceptions with their generic failure sections.
Verify target-root isolation, nested roots, absent blackboard metadata,
unknown roots, help, exit 75 and withheld-sweep exclusions. Inject config,
resolver and publication failures to prove the original result/exception and
local evidence survive. Check reporting-before-sweep and sweep-before-bump
ordering for scheduled scripts, both autoclose failure positions, and no
advancement for manual/Dream execution. Keep the CLI publication regressions,
including `tests/test_git.py`, when extracting its shared infrastructure.

Run affected suites for autoclose, disposal, reminders, skill update, Dream,
runner, script launch, aliases, branch cleanup, retire, PR publication,
recurring/autofix, megalaunch and notifications, then the full suite:
`PYTHONPATH=$PWD/src .venv/bin/python -m pytest` with a Coga-capable Python
3.11+ interpreter. `tests/test_packaging.py` must prove twin identity and wheel
inclusion; also run its pristine-tree wheel check and the prerequisite's
upgrade/local-edit regression fixtures, explicitly covering old Dream bodies
in both initialized templates and materialized periods under the dependency's
customization/running-period policy. Smoke `coga --help`, surviving recipe
help/argument validation and rejection of removed names using disposable
fixtures; never run destructive recipes against the live repo for verification.
Run `coga validate --task gigantic-refactor-move-recurring-recipes-out-of-co
--json`, repository validation against its documented baseline,
`git diff --check`, and `cmp AGENTS.md CLAUDE.md`. Record exact commands and
results on the blackboard/PR.

### Out of scope

- Designing the edge updater, its local-override policy, or a second migration
  mechanism; the named prerequisite owns those decisions.
- Migrating all CLI heads from the parked `v2/cleanup-core-commands` proposals,
  deleting `coga run`, a plugin registry, new execution metadata, general
  attachment discovery/copying, or configuration edits.
- Changing recurring schedules, workflow steps, launch/claim/publication
  rules, safety proofs, reminder policy, skill-update policy, Dream phase
  order, validation fixes, autofix agent behavior, or orphan deletion policy.
  Sharing the existing publication boundary with moved entrypoints as specified
  above is in scope; deferring publication until a later command is not.
- Reopening phone-home telemetry behavior or the completed report-durability
  design; preserve their shared helper and reporting guarantees.
- Broad helper renames, optional abstractions, and unrelated cleanup discovered
  while moving code.

## Context

### Consumer audit — source snapshot, 2026-09-28

The generic `src/coga/commands/run.py`, `run`, calls
`src/coga/runner.py`, `run_recipe`; that dispatch and a manual spelling alone
do not add a second owner for each job. The following records production uses
separately from verification. Recheck the graph after the prerequisite lands.

| Entry | Production relationship and proposed placement | Existing verification to carry forward |
| --- | --- | --- |
| `autoclose` | `coga/recurring/autoclose-merged/ticket.py` invokes `src/coga/autoclose.py`, `run_autoclose_recipe`, through the registry. `src/coga/aliases.py`, `DEFAULT_ALIASES["autoclose"]`, only launches that same template. No second job caller of `sweep_merged` exists. Move the job to this ticket; keep the shared symbols listed below. | `tests/test_autoclose.py`, `tests/test_autoclose_dispose.py`, `tests/test_autoclose_sweep.py`, `tests/test_notification_messages.py`, `tests/test_recurring_shims.py`. |
| `blocker-reminders` | Its recurring `ticket.py` calls `src/coga/blocker_reminders.py`, `run_blocker_reminders_recipe`, which calls `remind_blocked_tasks`/`scan_blocker_reminders`. The additional reminder-scan import in megalaunch is in a test, not the drain implementation. Move the whole module to the template's `ticket.py`. | `tests/test_blocker_reminders.py`, `tests/test_megalaunch.py`, `test_megalaunch_drain_keeps_ask_open_when_activation_refuses`, and the recurring script tests. |
| `branch-sweep` | Both `coga/recurring/branch-sweep/ticket.py` and `coga/recurring/autoclose-merged/ticket.py` call `src/coga/branchsweep.py`, `run_branch_sweep_recipe`/`sweep_branches`. These are independent weekly and daily invocations, not twins. Keep this shared implementation and thin registered adapter. | `tests/test_branchsweep.py`, `tests/test_recurring_shims.py`, plus `tests/test_branchcleanup.py`. |
| `skill-update` | Its recurring `ticket.py` calls `src/coga/skill_update.py`, `run_skill_update_recipe`. The top-level alias launches that same ticket; the worker calls the separate public `coga skill update` command. `src/coga/commands/skill.py`, `update`, does not consume the reporting job. Move the reporting job to its ticket. | `tests/test_skill_update.py`, `tests/test_recurring_shims.py`, parser/root cases in `tests/test_runner.py`. |
| `validate-drift` | `coga/recurring/dream/ticket.md`, Phase 1, and its invocation skill direct one Dream agent to `src/coga/dream_validate_drift.py`, `run_validate_drift_recipe`. `run_validate_json` calls the public validator; the validator does not call this classifier/reporter. Move to Dream's explicitly invoked attachment. | `tests/test_dream_validate_drift.py` (including `test_classifier_explicitly_covers_every_emitted_validator_kind`), `tests/test_dream_skill_scripts.py`, `tests/test_dream_worker_templates.py`, root cases in `tests/test_runner.py`. |
| `cleanup-orphan-markers` | Dream's Phase 5 and its invocation skill call `src/coga/dream_cleanup_orphan_markers.py`, `run_cleanup_orphan_markers_recipe`. `find_candidates` and `render_report` are owned by this one phase; the worker checks the delete skill but does not call deletion. Move to Dream's explicitly invoked attachment. | `tests/test_dream_skill_scripts.py`, `tests/test_dream_worker_templates.py`, `tests/test_runner.py`. |
| `recurring-scan` | `src/coga/commands/recurring.py`, `main`, calls `run_recipe`; `src/coga/recurring_runner.py`, `_run_repo_recurring`, subprocesses that same entry for `run_recurring_all_repos`/temporary control worktrees, and `_recurring_scan_relay_argv` supplies the off-control relay. `run_recurring_scan_recipe` adapts argv to `run_recurring_scan`. Keep the package-co-versioned launcher entry: `src/coga/cli.py`, `_is_recurring_all_child`, recognizes this exact dispatch plus `--require-fresh-control` to suppress the wrong checkout's exit sweep. This is launch/admission/publication machinery, not one recurring ticket's business logic. | `tests/test_recurring.py`, `tests/test_cli.py`, `tests/test_runner.py`; preserve the private relay flags and exit behavior. |
| `autofix-analyze` | `src/coga/recurring_autofix.py`, `analyze_record` and `create_autofix_ticket`, have two operational paths: `run_autofix`, called after scans and named runs by `src/coga/recurring_runner.py`, and `run_autofix_analyze_recipe`, which replays a saved record independently. Keep the shared analysis/ticketing implementation and thin replay command. The sweep does not call the recipe wrapper; do not count it as doing so. | `tests/test_recurring_autofix.py`, `tests/test_recurring.py`, `tests/test_runner.py`. |
| `open-pr` | `src/coga/aliases.py`, `DEFAULT_ALIASES["open-pr"]`, and the `code/open-pr` skill lead to `src/coga/open_pr.py`, `run_open_pr_recipe`/`open_pr`. These are one command, not independent consumers of the whole publisher. Owner-approved named exception (2026-09-28): retain its co-versioned gate-producing publication contract. `open_pr` records `pr:` through `src/coga/blackboard.py`, `update_blackboard_under_barrier`; `src/coga/step_gate.py`, `_has_pr`, reads the artifact before bump. Its shared `same_git_checkout` separately serves launch and bump. Do not claim the network push, GitHub PR and local record are one atomic transaction, or that the shared helper proves the whole command shared. | `tests/test_open_pr.py`, `tests/test_open_pr_command.py`, launch/bump gate tests, `tests/test_runner.py`. |
| `delete-task` | `src/coga/delete_task.py`, `run_delete_task`, is shared by its recipe, `src/coga/commands/delete.py`, `delete`, and `src/coga/recurring.py`, `create_template`/`promote_task`. It holds `git.state_lock` for local removal; callers decide whether to publish deletion immediately or replace a period and publish the replacement together. Keep the shared operation and working-tree-only recipe contract; replacing it with `coga delete` would change publication timing. | `tests/test_commands.py`, `tests/test_recurring.py`, `tests/test_runner.py`, Dream delete-surface tests. |

### Shared symbols and reporting facts

- `src/coga/autoclose.py`, `parse_pr_url`/`parse_branch_name`/
  `parse_worktree_path`, are imported by `src/coga/open_pr.py`, `open_pr`,
  `src/coga/commands/launch.py`, `src/coga/commands/retire.py`,
  `src/coga/commands/bump.py`, and shared checkout/gate code.
  `src/coga/step_gate.py`, `_has_pr`/`_has_branch_linkage`, use lazy imports
  because autoclose currently imports mark/validate; moving the job must not
  reintroduce that cycle. `src/coga/pr_assist.py` uses `pr_view` and the same
  PR parser; `src/coga/branchcleanup.py` and `src/coga/branchsweep.py` share
  `prs_for_head`. Keep the transitive support needed by these shared operations.
- `src/coga/runner.py`, `run_recipe`, already delegates to `run_reported`;
  `coga/recurring/phone-home/ticket.py`, `main`, uses `run_reported` directly.
  `_failure_root` currently imports validation/skill-update parsers and the
  orphan worker's root selector, so it cannot remain unchanged after the move.
  `_record_failure` uses `blackboard_from_env` and a config with the selected
  `repo_root` for `append_blackboard_report`; preserve both containment and
  the publication barrier rather than using the invoking config blindly.
- `src/coga/commands/update.py`, `copy_fresh_templates`, copies non-bootstrap
  templates into a fresh repo. `src/coga/recurring.py`, `_create_at_slug`,
  copies only the template's reserved `ticket.py` into a period task; arbitrary
  siblings remain beside the template. Consequently Dream attachment commands
  must use the parent/distribution path, not assume files under
  `COGA_TASK_DIR`. These are the current distribution facts the prerequisite
  must reconcile before the implementation removes any registry entry.

### Contract reading and related work

The following topics are cited rather than attached; they are the owners to
read and update at the named sections, not specifications to duplicate here:

- `coga/extension-model` (`docs/contexts/coga/extension-model/SKILL.md`):
  “The microkernel rule”, “Open command placements”, and “coga run”.
  Current blanket registry permission is what this ticket changes.
- `coga/recurring/templates`
  (`docs/contexts/coga/recurring/templates/SKILL.md`): “The template-to-period
  transform” and “ticket.py completion and reporting”. Period reports are
  temporary; durable state stays on the parent/worklist/log.
- `coga/script-tickets` (`docs/contexts/coga/script-tickets/SKILL.md`):
  “Classifier”, “One deterministic phase”, and “COGA_TASK_* contract”. Only
  the exact `ticket.py` filename participates in launch dispatch.
- `coga/dream` (`docs/contexts/coga/dream/SKILL.md`): the ordered phases;
  `coga/internals/pr-publication`
  (`docs/contexts/coga/internals/pr-publication/SKILL.md`): “Checks, in order”
  and “Where the record lands”; `coga/recurring/autofix`
  (`docs/contexts/coga/recurring/autofix/SKILL.md`): “The loop” and
  “Operating it”. These constrain the survivors and explicit phase calls.
- `coga/packaging` (`docs/contexts/coga/packaging/SKILL.md`): distribution,
  twin mapping and wheel checks; `coga/testing`
  (`docs/contexts/coga/testing/SKILL.md`): packaged script tests, absolute
  `PYTHONPATH`, and the known validation baseline.
- `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`): one owner per
  fact and same-PR updates to references; `coga/project-stage`
  (`docs/contexts/coga/project-stage/SKILL.md`): bounded migration only,
  with no indefinite compatibility surfaces.
- `coga/internals/state-publication`
  (`docs/contexts/coga/internals/state-publication/SKILL.md`): “Invariants”,
  “Best-effort versus strict” and “The end-of-command sweep”.
  `src/coga/cli.py`, `_sweep_coga_state`/`main`, currently supplies the exit
  publication missing from direct `runner.run_reported` calls; share that
  infrastructure with the moved entrypoints while retaining its scope and
  exclusions.

Related task state at design time: the edge-upgrade prerequisite is `draft`;
`autoclose-should-be-script-only` is an empty draft (the current scheduled
template is already script-only, so this is not authority to redesign it);
`define-the-recipe-reporting-contract-report-durabi` is `done`, and its helper
has been extended by phone-home. The `v2/cleanup-core-commands/` proposals
remain parked and do not override the current extension-model contract.

<!-- coga:blackboard -->

## Design investigation — 2026-09-28

- Owner confirmed in the attended session: land `ship-edge-ticket-py-code-upgrades-with-the-wheel` first, then this refactor. Its distribution design is still a draft; this ticket must consume its settled upgrade/override contract rather than invent another one.
- Owner explicitly approved retaining `open-pr` as a named exception after discussing its single command consumer and its gate-producing publication write. The design does not use its shared checkout helper to classify the entire publisher as shared.
- `src/coga/runner.py`, `run_reported`, already supplies the edge failure-reporting seam introduced with phone-home. Its `_failure_root` still imports the three ticket-owned recipe parsers/root selectors; removing that core-to-edge dependency is part of the design.
- `coga/recurring/autoclose-merged/ticket.py` calls both `autoclose` and `branch-sweep`, in that order. `coga/recurring/branch-sweep/ticket.py` independently calls the same branch sweep. Keep the shared sweep and its safety proofs; count symbols and independent production uses, not forwarding aliases or tests.
- Dream remains agent-backed: `coga/recurring/dream/ticket.md` explicitly invokes validation in Phase 1 and orphan detection in Phase 5. Move those implementations to explicitly invoked attachments; adding a Dream `ticket.py` would change launch timing and is not an equivalent move.
- Correction from checking `src/coga/recurring.py`, `_create_at_slug`: named attachments do not travel to periods; only `ticket.py` is copied. The design invokes Dream's attachments from the parent template/distribution path and does not change generic copying.
- Investigation and written design only in this step; no implementation, branch, commit, or PR.

## Open Questions

No unanswered owner questions. Implementation depends on the edge-upgrade
ticket's reviewed and merged distribution contract, including named attachments
and pre-existing period shims and Dream instructions; that design belongs to
the prerequisite. The owner approved the evaluator-gap revisions on 2026-09-30
as recorded below; advancing the review-design gate remains pending.

## Design handoff

The Description contains the acceptance checklist, proposed shape and exclusions;
Context contains all ten recipe decisions with production consumers and test
touchpoints. Owner decisions are recorded above. Only this ticket was edited
during design; production changes and tests belong to implementation after the
upgrade prerequisite.

Verification before handoff:

- `PYTHONPATH=$PWD/src coga validate --task gigantic-refactor-move-recurring-recipes-out-of-co --json` — 1 task OK, no issues.
- `git diff --check` — clean.
- Read-only structural check — lifecycle frontmatter unchanged, exactly one
  blackboard fence, all required spec sections under Description/Context,
  exactly ten audit entries, and no bare source-line citations.
- Read-only `compose_prompt_report` under
  `PYTHONPATH=$PWD/src .venv/bin/python` — confirmed all spec subsections,
  the audit and Open Questions reach the prompt. Measured candidate context
  payloads on an in-memory copy and kept targeted owner-section citations;
  no frontmatter or disk changes from composition.

## Evaluator review

Cold review, 2026-09-29. **One must-fix design gap before implementation.**
The ownership split and ten-entry consumer audit match the current source;
the implementation also remains conditional on the named upgrade prerequisite
landing. This review does not approve the design on the owner's behalf.

Disposition, 2026-09-30: the owner approved the revisions below. The must-fix
and optional recommendation are addressed in the ticket design; the original
findings remain here as review evidence. Implementation and its verification
remain future work.

### Must resolve before implementation

1. **Preserve the publication boundary when replacing `coga run` with Python
   entrypoints.** The proposed wrappers specify failure reporting and scheduled
   completion, but do not account for publication supplied by the CLI itself.
   `src/coga/cli.py`, `main`, calls `_sweep_coga_state` on ordinary success,
   nonzero exit, and escaping exceptions; `_SWEEPING_COMMANDS` includes `run`.
   In contrast, `src/coga/runner.py`, `run_reported`/`_record_failure`, and
   `src/coga/blackboard.py`, `append_blackboard_report`, only run the worker
   and append locally under the barrier. They do not publish those bytes.

   This matters for both explicitly invoked Dream attachments and manual
   worker runs, which intentionally will not bump. For example,
   `src/coga/dream_validate_drift.py`, `run_validate_drift_recipe`, appends
   its report after `run_validate_json` invokes `python -m coga.validate`;
   that validator subprocess has no CLI exit sweep either. Replacing the
   outer `coga run validate-drift` with the specified Python attachment
   leaves its report and default safe repairs unpublished until some later
   Coga command. The same gap affects the generic failure section after a
   failed attachment. A later Dream bump is not the existing per-command
   boundary, and a standalone invocation may have no later command at all.

   Evidence: `docs/contexts/coga/internals/state-publication/SKILL.md`,
   “Invariants” and “The end-of-command sweep”, defines control as the durable
   home and specifies the exit sweep; `tests/test_git.py`,
   `test_ordinary_run_still_sweeps_off_control`, explicitly tests
   `coga run autoclose`. An in-memory probe through actual `cli.main` and
   `run_reported`, stubbing the worker and Git transport, observed
   `worker → publish sweep` for CLI exits 0 and 2, versus only `worker` for
   direct `run_reported` at both exits.

   **Requested resolution:** name how the replacement entrypoints preserve
   that publication boundary using shared infrastructure, including failure
   and manual execution, without advancing Dream or an inherited task. Add
   entrypoint-level verification that the resulting reports/repairs reach
   control and publication failure preserves the original worker result.
   Alternatively, the owner must explicitly accept deferred publication and
   revise the preservation criteria, the publication exclusion, and the
   owning contract. The current “preserve operational behavior” requirement
   and “publication rules” exclusion do not authorize that change implicitly.

### Optional recommendations

- Make the prerequisite's upgrade fixture explicitly include **old Dream
  instructions**, as well as old Python shims. The existing-template/period
  criterion is broad enough to cover this, but the prerequisite paragraph
  names code and copied shims specifically. `commands/update.py`,
  `copy_fresh_templates`, seeds `recurring/dream/ticket.md`, and
  `recurring.py`, `_create_at_slug`, freezes `template.body` into the period.
  Its Phase 1/5 instructions still name the two recipes being removed.
  Delivering new attachments alone does not update those commands. Exercise
  a previously initialized template and a materialized period with those
  bodies under the prerequisite's approved customization/running-period
  policy before accepting the registry contraction.

### Verified constraints and scope

- Confirmed the five jobs' production callers, the retained autoclose
  parsers/GitHub dependencies, the two branch-sweep invocations, recurring
  relay dispatch, independent autofix replay, open-pr's gate-producing write,
  and delete-task's separately controlled publication timing. Tests, aliases,
  and packaged twins were not counted as independent job consumers.
- `launch_script.run_script_phase` supplies `COGA_SCRIPT_TASK` and no argv;
  `task_env.is_script_task` checks target identity. The design correctly
  requires more than an inherited slug for completion. Dream's attachments
  must remain outside the reserved filename classifier.
- The reporting resolver proposal matches today's parser/root policies and
  preserves phone-home's existing four-argument `run_reported` call. Current
  tests cover the stated root, diagnostic, failure, and launch seams; the
  refactor must move that coverage onto the packaged edge entrypoints.
- `coga/tasks/ship-edge-ticket-py-code-upgrades-with-the-wheel.md` is still
  `draft`, step `design`, with unresolved delivery/local-edit questions.
  That is the ticket's already-declared implementation prerequisite, not a
  reason to block this evaluator handoff. The frozen workflow correctly
  advances from `evaluate-design` to the owner-held `review-design` gate.

### Review verification

- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_runner.py tests/test_recurring_shims.py tests/test_launch_script.py tests/test_dream_skill_scripts.py tests/test_dream_validate_drift.py tests/test_dream_worker_templates.py -q`
  — **147 passed**.
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_cli.py tests/test_git.py::test_ordinary_run_still_sweeps_off_control -q`
  — **19 passed**.
- `PYTHONPATH=$PWD/src coga validate --task gigantic-refactor-move-recurring-recipes-out-of-co --json`
  — **1 task OK, no issues**.
- `git diff --check` and `cmp AGENTS.md CLAUDE.md` — clean/matching.
- Review changes are confined to this blackboard. No ticket-body edits,
  implementation, branch, commit, or PR were produced; the CLI owns the
  ensuing workflow transition and audit publication.

## Owner review revisions — 2026-09-30

- Owner approved the proposed design revisions in the attended session.
  Resolved evaluator must-fix 1 by specifying a shared CLI/edge publication
  boundary after reporting, with target config reload, existing sweep scope
  and exclusions, and best-effort failure semantics. `run_reported` remains
  reporting-only. Scheduled completion still bumps only after successful
  work; manual workers and Dream attachments never advance an inherited task.
- Added entrypoint/control-tree verification for reports, safe repairs and
  failures, publication fault injection, target isolation and completion
  ordering. These checks belong to implementation, not this prose revision.
- Accepted the optional recommendation: prerequisite coverage now explicitly
  includes old Dream Phase 1/5 commands in initialized templates and frozen
  periods under its approved customization/running-period policy. The
  prerequisite is still draft; its delivery mechanism remains undecided here.
- Only this ticket's body and blackboard changed. No production code, owning
  topic contract, configuration, lifecycle frontmatter, or audit log was
  edited. The owner approved revisions, not a workflow advance; remain at
  review-design until explicitly asked to advance.

Revision verification:

- `PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task gigantic-refactor-move-recurring-recipes-out-of-co --json`
  — 1 task OK, no issues or fixes.
- `git diff --check` — clean; `cmp AGENTS.md CLAUDE.md` — matching.
- Read-only Python comparison against `git show HEAD:<task-path>` confirmed
  unchanged lifecycle frontmatter and exactly one blackboard fence;
  `git diff --name-only` confirmed only this ticket changed.
- No behavioral tests run: this step revised the design only.
