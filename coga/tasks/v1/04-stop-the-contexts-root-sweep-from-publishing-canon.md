---
title: Stop the contexts-root sweep from publishing canonical topics without their
  packaged twins
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
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
  - name: peer-review
    skills:
    - code/peer-review
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
step: 2 (evaluate-design)
agent: claude
---

## Description

Coga keeps hand-maintained twins of shipped resources in the package and in
this repo's live Coga roots. A feature-branch state sweep can publish the live
half to control before the packaged half merges, leaving main's packaging
checks red. Make `src/coga/resources/` the single committed source of shipped
definitions, read from the installed package at runtime, with deliberate repo
overrides taking precedence. An editable install reads the source tree; an
installed wheel reads its resources. Runtime consumers must never mutate
package resources; normal source authoring remains allowed.

The owner has rejected excluding twin paths from the sweep and publishing
both halves together. Preserve ordinary state publication. Repos retain their
own definitions, deliberate overrides, real state, and the justified physical
scaffolds below. Package upgrades change fallback content without copying it
back into repos. Recurring parents participate in fallback resolution, while
all mutable state stays in the repo or owning clone.

### Acceptance criteria

- [ ] Shipped contexts, skills and their attachments, workflows, bootstrap
  tickets, recurring definitions/scripts/runbooks, and prompt resources each
  have one committed package owner. This repo has no undeclared live
  counterparts. Required-resource checks prevent deleting both copies from
  becoming a vacuous pass. All `coga-dev/` files remain local-only.
- [ ] Every removed live definition resolves through the installed package in
  both editable and fresh-wheel installations. Local overrides win by ref;
  malformed/unreadable overrides fail visibly without selecting stock text.
  Agent skill discovery and workflow freezing use the same effective refs.
- [ ] All nine currently bundled parents (`autoclose-merged`, `branch-sweep`,
  `blocker-reminders`, `dream`, `phone-home`, `skill-update`,
  `address-pr-comments`, `resolve-conflicts`, `trim-log`) work without local definition
  tickets. Listing/status, validation, due scans, clone scans and named launch
  agree on selection, definition source and dependencies.
- [ ] Package-backed recurring runs read/write only repo-owned parent state,
  worklists, period tasks and shared log, or clone-local ledgers/logs. Repeated
  and interleaved updates preserve unrelated blackboard keys, phone-home's
  complete `period_state`, snapshots, retirement records and CAS safeguards.
  A state-only local directory/file never shadows a package definition.
- [ ] Override boundaries include scripts and supporting files: no silent
  mixture of a local job body with a packaged `ticket.py`. Repo-specific jobs
  and attachments survive. Existing frozen workflows, period bodies,
  delegates and copied scripts are not regenerated during upgrade/migration;
  old state snapshots and legitimate unfinished periods remain usable.
- [ ] Existing repos with no new selection file retain local-only recurring
  activation. Deleted or `_name`-parked jobs do not reappear. Explicitly
  disabled jobs stay disabled under sweeps, `--force` and named recurring
  launch. Adding a bundled job in a package upgrade does not enable it in an
  existing repo. Fresh-init defaults follow the owner decision at review.
- [ ] Fresh init copies only approved scaffolds and real initial state. It
  creates no reusable shipped definitions in live roots. Clone setup and
  package upgrades never overwrite customization, reseed state, or recreate
  removed definitions. A documented, rehearsed operator migration preserves
  old seeds, customized overrides, parked jobs and saved state.
- [ ] The compatibility stage is merged and in use on control before any
  dependent removal is published. A regression exercises the first live-copy
  deletion/state conversion from a feature checkout against that control
  version; control's package, navigation and representative runtime checks
  stay green before the cutover PR merges.
- [ ] A separate final-state regression edits packaged content on a feature
  branch, both dirty and committed, then runs a mutating CLI exit sweep.
  Control's packaged bytes stay unchanged while ordinary local task,
  recurring-state and repo-context edits publish; control's packaging checks
  pass. No publication guard, root membership or provenance rule is weakened.
- [ ] Build the verification wheel from a pristine disposable clone and run
  installed-artifact smoke tests outside the editable source path. Cover all
  resource types and all nine parents with outward effects stubbed; compare
  package-resource bytes before/after and exercise read-only resources.
- [ ] The owning topics, `AGENTS.md`, indexes, shipped instructions and local
  development links describe the new ownership and navigation. Context-link
  validation reads the actual package tree. The relevant tests, seeded-repo
  validation and full suite pass after reconciliation with current main.

### Proposed shape

#### 1. Keep package ownership explicit

Keep user topics at
`src/coga/resources/templates/coga/bootstrap/contexts/<ref>/`, including their
supporting files. Delete their `docs/contexts/coga/` counterparts after the
compatibility stage. Keep `docs/contexts/coga-dev/` and all other repo-only
knowledge. Do not replace removed topics with forwarding files or symlinks in
live roots: indexes link directly to the package owners.

Move the currently seeded reusable workflows (including `direct/body`,
`build/onboarding`, and recurring workflows) into package
`bootstrap/workflows/`, and `skills/direct/body/` into `bootstrap/skills/`.
Their logical refs stay unchanged. Keep recurring definitions together at
package `templates/coga/recurring/<name>/`; bootstrap tickets retain their
existing package directories. Top-level prompt resources retain their
existing replace-only override mechanism. There must be only one packaged
definition per logical ref, not a second fallback copy under the old seed
path.

Use the existing `src/coga/paths.py` resolvers as the entry point for reusable
refs, and align `src/coga/agent_skills.py`, `refresh_agent_skill_view()`, with
them. Tighten the skill and bootstrap-ticket resolvers where their current
`is_file()` check could mistake an invalid override for absence. Preserve the
context artifact checks and workflow loader's fail-loud behavior.

Resolution is by artifact/ref, not by merging text. A local skill, context,
bootstrap ticket or recurring definition owns its directory and supporting
files; a local workflow owns its file. A local recurring ticket with no
`ticket.py` is agent-backed if otherwise valid: omission does not inherit the
packaged script. To retain a deterministic phase while customizing the job,
copy its required siblings deliberately. `scope: clone` still requires the
script. A supporting file or script left without its local definition is an
incomplete override, except the recognized state-only contents below.

#### 2. One effective recurring catalog and explicit activation

Add shared definition discovery/resolution in `src/coga/recurring.py` (proposed
`iter_template_sources()` and `resolve_template_source()`; names may change).
Return the job's logical name, definition directory, origin and selection
status separately from its local state path. `Template.path` and
`Template.ticket_path` denote the selected **definition**, never a writable
parent. All consumers listed in Context must use this catalog rather than
walking `paths.recurring_dir()` themselves.

Propose a repo-owned `coga/recurring/jobs.toml`, with a `[jobs]` table mapping
job names to booleans. This is recurring selection data, not another copy of
job schedules/bodies or a new `coga.toml` section:

- `true`: enable the local definition if present, otherwise the bundled one.
- `false`: disable either definition. Named recurring launch and force refuse
  it with the path and the remedy; they do not silently enable it.
- No entry: ordinary local definitions retain their current activation;
  bundled-only jobs are available but disabled. No file means the same rule,
  preserving pre-upgrade behavior. State-only parents do not count as local
  definitions or as opt-in evidence.
- `_name/` parks `name`, including its package fallback, regardless of a true
  selection. An active local definition and its parked counterpart are an
  ambiguous configuration and must be reported. Likewise, two active/parked
  state carriers require cursor reconciliation, never guessing. Parking by
  renaming moves the state with the directory; false selection can disable a
  bundled job while leaving its carrier in place. Unparking preserves state.
- Invalid TOML, unknown keys, invalid names or non-boolean values are visible
  configuration errors. A true entry naming no available definition is an
  error, not an empty scan. A false entry may retain a tombstone for a removed
  job. A newly bundled name has no entry and therefore stays disabled.

Fresh init writes explicit true entries for today's nine jobs, subject to
owner approval; subsequent init/upgrade never refreshes that list. Local
custom jobs keep existing semantics without registration. Read-only views
show source and disabled/parked reasons without creating state; validation
checks enabled definitions and selection errors, preserving the existing
skip of parked bodies. Template failures keep existing per-template reporting
and do not hide healthy jobs. No special registry of recurring workflows is
introduced.

Disabling prevents recurring scheduling/resumption, not deletion of an existing
period. An explicit ordinary `coga launch recurring/<name>` of an already
materialized task retains its current lifecycle contract; it does not enable
the parent or create another period.

#### 3. Preserve state paths without preserving definitions

Keep the durable blackboard at the existing repo path
`coga/recurring/<name>/ticket.md`. For a package-backed parent it becomes a
**state-only carrier**, not a copied definition. Its shape is empty YAML
frontmatter (`{}`), a reserved own-line `<!-- coga:recurring-state -->` marker,
then exactly one ordinary blackboard fence and the saved blackboard. It has no
schedule, body instructions, workflow or script. The parser must require that
shape exactly above the fence. An unmarked ticket with a missing schedule, or
a marked file with definition fields/prose, is malformed; neither is a quiet
fallback. The marker is proposed only for recurring parent storage, never
ordinary tasks or period tickets.

This keeps old parent paths and snapshot identities valid while removing the
mutable definition. A local parent with a genuine override remains a normal
full template; its blackboard is still the sole state owner. There is no
second `state.md`, no dual write, and no state copied into package resources.
The deliberate state-only carrier is an explicitly classified exception to
the same-path inventory, validated by shape rather than exempted wholesale.

Add a small shared `src/coga/recurring_state.py` for this classification and
repo-state access (proposed `parent_state_path()` and
`ensure_parent_state()`). It has multiple real consumers: creation/snapshots,
completion/publication, phone-home, and audit retention. The write path always derives from
`cfg.repo_root`, never from a resolved definition path. State lookup recognizes
a unique parked parent when preserving existing state, including retention
inputs, without enabling it or inventing a second active carrier. Reuse the fence-aware
blackboard APIs, existing state/admission locks and expected-byte writes.

On the first admitted repo-scoped execution, initialize the carrier once from
the selected package definition's initial blackboard, before snapshotting its
keys. Do not initialize during list/status/validation or reseed existing
state, including an intentionally empty state region. Initialization and
publication must detect concurrent creation/update rather than overwrite it.
Direct supported recipe execution, including phone-home, obtains the same
state before writing. Invalid state fails visibly; it must not reset a
counter to the package seed. Respect `log_transaction.ensure_clear()` before
initializing or changing state; a pending retention receipt is not permission
to copy, reset or migrate its cursor.

A directory containing only the carrier and recognized runtime state such as
`retires.md` still resolves the selected package definition. `ticket.py` or
supporting definition files alongside a state-only carrier are an incomplete
fork and must be repaired explicitly; they are never silently inherited or
ignored. A full local override is the escape hatch for arbitrary custom
attachments. State alone does not select a job.

Keep `retires.md` at its existing repo-local path and preserve its union/CAS
behavior. `worklist_for_period_task()` must recognize a selected bundled
parent even when no local definition exists, while retaining the existing
removed/parked-parent behavior. `all_worklists()` must continue to find durable
records independent of definition origin. Shared serviced-period evidence
stays in `coga/log.md` under the current retention/high-water contract. Clone success ledgers/logs stay in the primary
clone's `.coga/recurring-clone/`; `branch-sweep` creates no period task and no
package-side state.

Main now also ships `trim-log`. Preserve its transaction with phone-home:
schema-1 cursor migration and schema-2 `seen_movements` state remain owned by
the existing movement-cursor code. Update retention's parent/script discovery
to accept a valid carrier plus a compatible effective packaged shim, including
disabled/parked phone-home state. Missing local `ticket.py` must not mean an
incompatible fork when the selected definition is packaged. Preserve full-fork
and frozen-script refusals. Pin the selection/local override and package
script identity used by the decision, rechecking it on retries, alongside the
existing config/inventory/cursor guards. No new fallback lookup may erase
unread movement protection or bypass a pending log-mutation receipt.

Change `src/coga_edge/trim_log.py`, `install()`, to adopt via explicit recurring
selection plus the existing reviewed attribute update, rather than copying
definitions/workflows. Preserve its explicit opt-in, parking, fork and
attribute refusals. Already customized local installations remain overrides;
absent legacy trim-log stays unselected. Once this replacement is landed,
remove the temporary `rollout/trim-log/coga/` definition copies and their
staged-twin assertions/links; they are not a permanent exception to the
single-source rule. The attribute rollout remains a real physical scaffold.

Update recurring creation, forced snapshots, control adoption and completion
to carry definition metadata and writable parent paths separately. In
particular, do not turn `period_state.parent_ticket_path()` into a package
resolver. `_sync_recurring_create()` must not skip its full ledger/CAS path
merely because a local parent directory did not exist before first use. Its
publication overlays, leases and restoration operate only on local state.
Template-damage checks compare the selected definition; they must not mistake
a legitimate carrier update for rewritten instructions.

Period creation still copies only `ticket.py`, freezes the body/workflow and
`delegate`, and snapshots state by parent name. Supporting files remain at
the selected definition directory; instructions name that effective location
through resolver-based examples instead of assuming a live parent copy.
Scripts execute with repository cwd and repo-local output paths. Runtime
execution/validation must not generate bytecode or other artifacts under
package resources. Existing materialized periods retain their snapshots,
frozen instructions and scripts; package updates apply to future creation,
not regeneration of an unfinished run. Skill/context refs and bootstrap
delegate targets keep their existing resolution semantics; this does not add
content pinning of those dependencies.

#### 4. Init scaffolds and the source-repo inventory

Replace `commands.update.copy_fresh_templates()`'s blanket copy with a small,
reviewed scaffold allowlist. Retain these materializations for concrete
reasons, with the same classification reflected in packaging tests:

| Materialization | Reason and ownership after init |
| --- | --- |
| `coga/coga.toml`, `coga/context.md` | Actual repo configuration and repo context, customized by its owner; seeds are never reapplied. |
| `coga/log.md` | Real retained audit history, initially empty; retention and its publication guards remain authoritative. |
| `coga/.gitattributes` | Git requires physical attributes: `/log.md -merge` after retention adoption and `retires.md` union merging; preserve guarded rollout of the existing repo rule. |
| `coga/.gitignore` and `<contexts-root>/.gitignore` | Physical ignore rules and managed blocks; the latter also keeps an otherwise empty relocated root trackable. |
| `recurring/jobs.toml` | Explicit repo activation choices, initialized once rather than refreshed on upgrade. |
| `contexts/_template/`, `skills/_template/`, `workflows/_template.md` | Ignored editable authoring starters, not committed canonical definitions. Keep package seeds; remove this repo's tracked starter copies and allow only ignored local starter materializations. |
| `tasks/coga-build.md` | A real, mutable onboarding task only for the existing eligible empty-repo case; preserve pruning and owner stamping. |
| Recurring carriers/worklists, period tasks, `.coga/` ledgers, local config and generated agent views | Runtime state with existing tracking/locality rules; no installed definition copy. |

No whole reusable-definition directory is on the init allowlist. Keep
`_setup_initialized_clone()` limited to clone setup; it must not add the
selection file to an existing repo or restore missing seeds. Preserve all
repo-only workflows/skills/jobs, especially `usage-report` and `upstream-coga`,
and their attachments. No actual `coga.toml` or `coga.local.toml` edit is
needed for this design.

#### 5. Migration and two ordered landings

Recommend two sibling implementation deliverables at `review-design`, with
this design as their agreed contract. Do not start a deletion branch against
pre-compatibility main. Splitting the ticket is an owner decision; follow
`coga/tickets/discovery` if approved, without retaining an umbrella task.

**A — runtime compatibility and deletion-tolerant checks.** Land the catalog,
selection/carrier support, dependency fallbacks, init changes and reader/writer
updates first. Keep this repo's existing live definitions during this stage.
Move package seed refs as above while keeping their live resolutions valid.
Update owning topics and links to their eventual package owners now, keeping
any still-present twins synchronized until cutover. Update Dream's scans and
hard-coded live-path consumers before deleting their inputs.

A's packaging policy is deliberately transitional: package resources are
required; legacy counterparts are optional and, when present as definitions,
still checked for approved equality/divergence. Recognized state carriers are
validated as state. Remove the twin-count floor, mandatory canonical-context
existence, and phone-home's mandatory live-definition assertion; retain
required resources, seed-zero checks and the local-only audience prohibition.
Record the exact legacy removal inventory so this temporary allowance cannot
silently grow. Navigation resolves actual package paths and remains valid
with any removable counterpart absent. Tests/harnesses that open live skills,
workflows or parents must also tolerate removal. These checks must actually
be on control, not merely in the later branch.

**B — repo migration, removal, and strict ownership.** Reconcile with merged A
and verify the CLI in every participating checkout uses A or newer. During a
short coordinated migration window, quiesce state writers/recurring sessions,
back up local definitions plus complete blackboards/attachments, and inventory
active, parked, deleted and customized jobs. Compare definitions and sibling
files separately from mutable blackboards, using a known prior seed/version
when needed. A changed file is not presumed disposable merely because its
name matches a bundled resource. Ambiguity retains an intentional local
override until the owner decides; record the reason, never silently delete it.

Publish selection before removing its dependent definitions (it changes
nothing while equivalent locals still exist). For each approved bundled
parent, replace the definition with a carrier preserving the entire saved
blackboard byte-for-byte and remove only its reviewed definition siblings.
Keep nontrivial state even for jobs with no declared `state_keys`; retain
worklists, the shared log, clone ledgers, frozen periods and custom jobs.
Read state from freshly reconciled control, never from the package's zero
seed. A parent with no useful state can have no local ticket until first use.
Do not leave a carrier plus orphaned definition siblings at an intermediate
publication: prepare that parent's conversion as one guarded state change.

Live-copy deletions/conversions are normal Coga state and may reach control
before B's source/test commit. Use the ordinary publication path and inspect
its receipt; do not exclude paths, suppress guards, or commit the packaged
side through a state command. `coga run publish-state` without path operands
can sweep deletions; named operands must be existing files, so verify removed
paths separately in the resulting control tree. Reconcile any publication
conflict without discarding newer state. Check control with A's runtime and
packaging tests after selection, after the first conversion/deletion, and
after the full removal, before enabling B's strict test policy.

B replaces temporary twin equality with an inverse check: fail on every
unapproved live counterpart, even byte-identical ones. Keep explicit reasons
for scaffolds/state carriers and any reviewed override, require those reasons
to describe real current files, and reject new accidental package/live copies.
Do not preserve phone-home's full definition merely for its counters. Land
B's final ownership tests/docs after the removals are safe; no intermediate
control commit may depend on unmerged B runtime support.

The operator migration lives with the shipped init/recurring contracts, with
a linked release-note entry. It must work on customized existing repos and
rehearse a rollback: keep writers quiesced, retain current state/ledgers,
restore definitions from verified backups if needed, and restore selection
without replaying periods. Require A-or-newer clients after migration; old
clients cannot interpret carriers. Drain or defer migration of a job whose
frozen custom instructions still require removed definition attachments;
never rewrite frozen workflows or discard an unfinished period just to finish
the migration. Retained custom attachments are documented overrides, not
silent exceptions. Automatic seed-recognition/migration tooling is not
required.

#### 6. Verification and documentation

Extend existing tests rather than create a second test harness for the same
contracts. The implementer should cover:

- `tests/test_paths.py`, `test_compose.py`, `test_init.py`,
  `test_bootstrap_workflow_review_sections.py`, and packaging tests: each
  fallback type, exact override precedence, invalid override diagnostics,
  direct/body and recurring workflow dependencies, generated skill discovery,
  fresh-init contents and unchanged clone setup.
- `tests/test_recurring.py`, `test_recurring_clone.py`, `test_period_state.py`,
  `test_recurring_shims.py`, `test_retire_worklist.py`, `test_trim_log.py`,
  `test_log_retention.py`, `test_telemetry.py`, and validation tests:
  all nine bundled parents, absent local roots, selected/disabled/parked
  jobs, whole-directory forks, carrier-only and worklist-only directories,
  dependency failures, frozen retries, forced runs, create/adoption races,
  state-key warnings, retained high-water evidence and repeated/alternating
  phone-home/trim-log writers, including parked cursors and interrupted trim
  recovery. Exercise deterministic
  scripts, agent composition/dispatch and delegates through the real routing
  seams, stubbing agent/Slack/GitHub/telemetry/destructive outward effects.
- `tests/test_git.py`: use actual temporary control and feature checkouts to
  exercise both A-to-B transition publications and final packaged-only edits.
  Run the control checkout's own compatibility code/checks, not B imports via
  the primary checkout's editable install. Include dirty topic deletions and
  the committed recurring-deletion adoption path, parent state conversion,
  preserved counters/worklists, and an ordinary local context/task edit as
  positive controls. Preserve existing refusal/concurrency coverage.
- `tests/test_packaging.py`: inverse counterpart inventory, required package
  resources, state-carrier shape/exception reasons, package-only defaults,
  forbidden `coga-dev/` contents, and negative tests adding an accidental twin
  or deleting a required fallback. Build from a pristine disposable clone to
  catch Hatch walk/force-include collisions. Install the wheel into an
  isolated environment, assert imports originate there, remove inherited
  editable `PYTHONPATH`, and run smoke coverage from a separate project. Also
  test read-only resources and compare the resource tree after repeated runs.

Update `docs/README.md`, `AGENTS.md`, `coga-dev/{packaging,testing,codebase}`,
and affected user owners: `context-layout`, `knowledge`, `init`,
`recurring/{templates,scheduling}`, `period-task`, `edge-code` and its upgrade
note, `skill-management`, plus checkout/publication guidance that describes
twins. Fix dependent prompt/skill/workflow/bootstrap/recurring instructions
and links, including README and local repo-only guidance where they link to
removed owners. Dream's knowledge/contract audit must scan package source
when operating in this source repo, and never edit installed resources in an
adopting repo; replace its twin-divergence shard with the single-source check.
Keep one owner per fact and point indexes at it. Extend
`test_context_navigation_has_no_broken_links` to check real package-relative
links and inbound links from local Coga-dev topics and live repo guidance,
without reading archives or permitting required shipped development refs.

Run focused suites during implementation, then `python -m pytest`,
`coga validate --json` (separating pre-existing live-ticket findings), and
seeded-repo validation with notifications isolated. Record exact commands,
wheel provenance/import paths and results at handoff. No implementation test
pass is claimed by this design step.

### Out of scope

Changing what the state sweep publishes, changing schedule/ledger/retention semantics,
introducing new recurring jobs, changing telemetry consent/delivery, replacing
Coga's CLI/recipe dispatch, auto-merging upstream changes into local forks,
automatic migration tooling, moving local Coga-dev topics into the wheel,
rewriting frozen task histories, or repairing historical commits. No branch,
code, PR, repo configuration edit, deletion, or migration is performed during
this design step.

## Context

### Verified source relationships (2026-10-28)

These are pre-migration paths and symbols, not line-number claims.

- `src/coga/paths.py`, `packaged_template_path()` uses
  `importlib.resources.files("coga.resources")`. `resolve_skill_path()`,
  `resolve_workflow_path()` and `resolve_context_path()` currently fall back
  only to `bootstrap/{skills,workflows,contexts}`. Moving seeded reusable refs
  there lets existing composition/creation resolve them without local copies.
- `src/coga/agent_skills.py`, `refresh_agent_skill_view()` combines
  `_skill_refs()` of packaged bootstrap skills and local skills. Keeping the
  shipped direct/body skill in the bootstrap root also makes it visible here.
  `src/coga/checkout_policy.py`, `_changed_skill()` and `_changed_section()`
  compare resolved skill/workflow content with the bootstrap package copies;
  preserve this checkout-policy witness when removing locals.
- `src/coga/tasks.py`, `resolve_bootstrap()` checks local then packaged ticket
  directories and returns a `BootstrapRef` with that directory. Its current
  `is_file()` test, like skill lookup, needs to distinguish bad overrides from
  absence. `paths.load_resource()` already refuses unreadable prompt overrides.
- `src/coga/commands/update.py`, `copy_fresh_templates()` calls
  `_copy_resource_tree(..., skip_top={"bootstrap"})`, thereby copying all
  non-bootstrap definitions today. `src/coga/commands/init.py`, `_do_init()`
  uses it, then relocates scaffolds, prunes onboarding and stamps owners.
  `_setup_initialized_clone()` instead wires local setup without reseeding.
- `src/coga/recurring.py`, `scan_due()`, `scan_clone_due()`, `create_named()`,
  `list_templates()` and `_template_period_targets()` inspect local
  `recurring_dir()` directly. `Template.load()` validates that directory's
  definition; `script_entry_point` derives from its siblings.
  `_create_at_slug()` freezes a period and copies the script, then
  `_write_state_snapshot()` currently reads `Template.ticket_path` as state.
- `src/coga/validate.py`, `_check_recurring_templates()` separately walks the
  local recurring root, loads tickets, checks fences/dependencies and compiles
  entrypoints. It must share effective definitions with the scanners while
  validating local carriers separately from definitions.
- `src/coga/recurring_runner.py`, `run_recurring_named()` currently probes
  `_declares_clone_scope(recurring_dir(cfg) / name)` before dispatch.
  `_record_forced_period_locally()` reloads the local template for state keys;
  `_template_description()` reads that same path for damage detection. All
  three need definition lookup separated from local state access.
- `src/coga/recurring_runner.py`, `_sync_recurring_create()` passes the local
  parent to `_sync_recurring_create_paths()`, whose ledger reconciliation,
  `_adopt_control_template()`, forced snapshot rebuilding and final restore
  can write it. `_local_parent_state_lease()` uses
  `period_state.parent_ticket_path()` for the parent lease. Keep every such
  path repo-local; audit these callers rather than globally changing
  `recurring_dir()` to a package fallback.
- `src/coga/period_state.py`, `write_snapshot()` stores only parent name and
  key values; `parent_ticket_path()` reconstructs the repo path used by
  `stale_keys()` and `src/coga/mark.py`, `mark_done()`'s publication closure.
  Keeping the state-carrier path avoids a snapshot-format migration.
- `src/coga_edge/phone_home.py`, `run_phone_home()` locks, reads the local
  parent blackboard, increments `period_state`, CAS-writes and publishes the
  parent before any delivery. Preserve all fields and reservation ordering.
  It needs shared first-use state initialization when the definition is bundled.
- `src/coga/log_publication.py`, `read_inputs()` pins active/parked phone-home
  directories in a Git revision; `cursor_state()` feeds unread-movement
  protection. `src/coga_edge/trim_log.py`, `_phone_compatible()` currently
  requires a local stock shim next to that parent; `_check_local_inputs()`
  calls it before `trim()` performs guarded cursor/log replacement.
  `src/coga/log_transaction.py`, `ensure_clear()` protects outstanding
  receipts. Carrier/fallback support must preserve these inputs and barriers.
  `src/coga/movement_cursor.py`, `migrate()` and `cursor()` own schema-1/2
  interpretation; this change must preserve their state, not implement a
  competing migration. `trim_log.install()` currently copies `_INSTALL_FILES`
  from package seeds and applies `_attribute_plan()`; its copy behavior is
  another materializer to replace.
- `src/coga/retire_worklist.py`, `template_worklist_path()` derives local
  `retires.md`; `worklist_for_period_task()` currently requires a local
  `ticket.md`. `all_worklists()` walks local worklists. `src/coga/autoclose.py`,
  `_report_retire_followups()` consumes the period worklist through that helper;
  these records must survive removal of definition siblings.
- `src/coga/recurring_clone.py`, `run_clone_template()` executes the supplied
  script with host-repo cwd and writes its clone-local log/ledger. The selected
  script may become packaged, but those write destinations do not change.
- `src/coga/git.py`, `sync_coga_state()` passes `coga_root_paths()` to
  `publish()`; `_state_areas()` includes both the Coga root and configured
  contexts root. `_routine_state_areas()` additionally permits committed
  task/log/recurring changes from feature branches. Thus live recurring
  deletions can publish even after being committed to a feature branch.
  Package source is outside this repo's configured state roots.
- `tests/test_packaging.py`, `_live_counterparts()` and
  `_discover_live_packaged_twins()` derive the inventory below.
  `_context_distribution_problems()` requires live contexts today,
  `test_twin_discovery_still_walks_the_packaged_tree()` imposes a count floor,
  and `test_phone_home_matches_seed_except_period_state_and_seed_is_unused()`
  requires the live phone-home definition. These need A-stage compatibility.
  `_context_link_problems()` currently remaps package contexts onto their live
  counterparts before resolving relative links; remove that assumption.
- `tests/test_packaging.py`, `test_wheel_includes_bootstrap_batteries()` and
  `test_installed_wheel_init_and_phone_home_are_isolated()` build from the
  current working tree today. `pyproject.toml`'s wheel `exclude` and
  `force-include` tables must select moved resources exactly once; build the
  proof from a pristine clone, outside editable imports.

### Inventory and migration evidence

The current mapping discovers 103 file pairs: 51 context files, 20 skill
files (including `seed_local_config.py` and the skill starter), 10 workflows
(including the workflow starter), 15 recurring files, two bootstrap command
tickets, and five root scaffolds. Recompute before implementation; this is a
snapshot, not a replacement for derived coverage.

The final reconciliation added a ninth bundled parent, `trim-log`, and its
workflow/runbook/script. It has no live counterpart yet: five temporary files
(including `.gitattributes`) live in `rollout/trim-log/coga/` and are checked by
`tests/test_packaging.py`, `test_staged_trim_log_rollout_matches_packaged_files()`.
The derived live-pair total remains 103. Include these staged copies in the
removal inventory. Existing-repo migration must not infer activation from
their presence outside the live recurring root.

The two bootstrap pairs are `address-pr-comments/ticket.md` and
`resolve-conflicts/ticket.md`. Recurring pairs include both operational
runbooks, the eight installed parent definitions and their scripts. Context inventory
includes `docs/contexts/.gitignore` and supporting files, not just `SKILL.md`.
The context starter is already package-only; the skill and workflow starters
are tracked live despite their ignore rule. `coga/recurring/autoclose-merged/
retires.md`, `usage-report/`, and `upstream-coga/` are repo-only and must not
be lost in a directory deletion.

Current `INTENTIONALLY_DIVERGENT_TWINS` entries are `coga/.gitattributes`,
`coga/.gitignore`,
`coga/coga.toml`, `coga/context.md`, `coga/log.md`, and
`coga/recurring/phone-home/ticket.md`. The last exemption is for mutable
`period_state`, not a justified permanently forked definition. The physical
`.gitattributes` must remain; its new temporary divergence protects the
trim-log adoption order and may only be removed after that adoption succeeds.

### Background and cited owners

Observed failures on 2026-10-21: 001aad66f published topic deletions/architecture
edits; e9a88b970 published topic edits during `coga create`. Tests should cover
the publication boundary, not replay those commits.

Owner-authorized historical reading was restricted to recorded twin rationale.
`docs/archive/context-migration.md`, “Distribution” and “Cutover”, records the
prior docs-library migration, mandatory fallback twins and coordinated
package/checkout rollout. It provides historical context, not a current
requirement to duplicate definitions; the present owner decision changes
ownership while retaining human navigation through the index. No archive
content is an implementation target or a shipped dependency.

Cited rather than attached; read these owners before changing them:

- `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`): “Where
  bundled resources live”, “Distribution states for a context”, “Canonical
  copies and twins”, “Wheel packaging”. It remains local.
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`): “Context
  audiences”, “Local first, then bundled”, and “Publication and ownership”.
- `coga/recurring/templates` (`docs/contexts/coga/recurring/templates/SKILL.md`):
  “Fields”, “The template-to-period transform”, “First firing is retroactive”,
  and “Cross-run state surfaces”; `coga/period-task`
  (`docs/contexts/coga/period-task/SKILL.md`): “Persistent state lives in the
  parent's blackboard”.
- `coga/recurring/scheduling` (`docs/contexts/coga/recurring/scheduling/SKILL.md`):
  “Periods and the serviced-period ledger”, “Repo scope and clone scope”,
  “What a sweep does per template”, and “Variants”.
- `coga/init` (`docs/contexts/coga/init/SKILL.md`): “Fresh repo” and “Clone of a
  repo that already uses Coga”; `coga/knowledge`
  (`docs/contexts/coga/knowledge/SKILL.md`): “Where knowledge lives”.
- `trim-log`'s package `recurring/trim-log/ticket.md` and `operations.md`:
  “Transaction and completion”, “Adoption after the compatible wheel upgrade”,
  and “Interrupted maintenance”; `docs/release-notes/audit-retention.md`
  summarizes that already-landed behavior. Update its adoption links/procedure
  together with the installer; retain its consent and recovery boundaries.
- `coga/tickets/discovery` (`docs/contexts/coga/tickets/discovery/SKILL.md`):
  sibling deliverables and no umbrella ticket, if the owner approves splitting.

User-topic paths above are pre-migration: their owning files move to
`src/coga/resources/templates/coga/bootstrap/contexts/`. Update the owner and
its dependent references in the same stage; do not leave the new contract
only in this ticket.

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

Previous ref: `stop-the-contexts-root-sweep-from-publishing-canon` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->


## Design handoff

Reconciled to `7d9c95053c2a518e90f72a834eab9255011f5d61`. Control renamed
this ticket to `v1/04-stop-the-contexts-root-sweep-from-publishing-canon` and
added trim-log retention while design was underway. The draft was backed up
and byte-verified at `/tmp/coga-contexts-package-design-20261028.md`, main
fast-forwarded, and the prose reapplied to the new path while retaining
control's lifecycle header, guide and Previous ref note.

The implementable spec is under Description; source relationships, inventory
and cited owners are under Context. This step changed only this ticket on
`main`, with no branch, code, PR, configuration change or migration.

Selected design: package-owned definitions; whole-directory overrides; one
shared effective recurring catalog; repo selection in `recurring/jobs.toml`;
explicitly marked state-only parent tickets at the existing writable paths.
The carrier keeps old snapshots, phone-home state and frozen-period state
paths usable without retaining a copied definition. Existing local custom
parents keep their ordinary blackboard; no dual state store is introduced.
Reconciliation adds trim-log to fallback coverage, preserves schema-2 telemetry
state and retention receipts, and replaces its definition-copying installer.
The existing source repo's unadopted trim-log must stay off until explicitly
selected after its prerequisites; fresh-init proposals now cover nine jobs.

The 103-pair inventory includes bootstrap tickets, scripts, runbooks, both
tracked starter copies and the contexts ignore file. Phone-home counters
must survive in a carrier; its old divergence exemption is not permission to
retain the full definition. Repo-only jobs and retirement worklists remain.

Rollout needs compatibility on control before any removal. The recommended
split is two real sibling deliverables: A adds fallback/state/init support,
prepares links and makes checks deletion-tolerant; B migrates this repo and
enforces the inverse single-source check. B must test intermediate state
publications against A's imports and checks, as well as the final packaged-edit
sweep. Do not start that migration or create sibling tickets in this step.

Historical reading was owner-authorized for twin rationale only. The context
migration record establishes the former docs ownership and coordinated
cutover; it does not require overriding the present package-only decision.
No unresolved conflict with that owner decision was found in the record.

## Open Questions

For the owner at `review-design`, after the independent evaluator:

1. Approve `recurring/jobs.toml` selection semantics: existing local jobs keep
   working without a file; bundled-only jobs need explicit true; false disables
   local and bundled definitions; `_name` parking suppresses fallback; named
   recurring launch/force cannot bypass disabling. Approve selecting today's
   nine jobs on fresh init while newly bundled names stay off in existing
   repos. This is a proposal, not an assumed product decision.
2. Approve the migration boundary: remove only verified old seeds, preserve
   all state and customized directories as intentional overrides, and use
   whole-directory forks (including scripts/supporting files) rather than
   field-level schedule overrides. Unknown provenance remains local for owner
   classification. Is the documented operator migration with quiesced writers
   sufficient, including deferred migration of incompatible frozen custom runs?
3. Approve the scaffold/state classification in Description, especially the
   marked `recurring/<name>/ticket.md` state carrier and ignored starter
   materializations. The carrier preserves the legacy path without keeping
   shipped instructions; it is not a malformed override fallback rule.
4. Approve splitting implementation into compatibility and cutover sibling
   tickets so the dependency can actually merge first. If kept as one ticket,
   an explicit staged-publication workflow is needed before implementation;
   one deletion PR against today's control cannot meet the rollout criterion.

## Verification

- Start: clean `main`, no Dev branch or PR for this ticket; `git fetch origin
  main` and `git merge --ff-only origin/main` succeeded at
  `e9c9e1acc0a114497d41a5ead21fd2e1adefb3b5`.
- Inventory: loaded `tests/test_packaging.py` with `.venv/bin/python` and ran
  `_discover_live_packaged_twins()` / `_packaged_template_files()`; 103 pairs.
  The ambient `python` cannot import this checkout's Coga package; use the
  checkout venv for Python verification.
- `coga validate --task stop-the-contexts-root-sweep-from-publishing-canon
  --json`: 1 OK, no issues.
- A `.venv/bin/python` structural/composition check compared the lifecycle
  header and ticket guide with HEAD, required exactly Description and Context
  as top-level body sections, and verified all spec subsections appear in
  `compose.compose_prompt(..., launch_context="megalaunch")`: passed.
- `git diff --check`: passed. These verify ticket structure, not implementation
  behavior; the required runtime, transition and wheel tests are specified for
  implementation and have not been claimed as run here.
- After reconciliation, `coga validate --task
  v1/04-stop-the-contexts-root-sweep-from-publishing-canon --json`: 1 OK,
  no issues. Repeated the structure/composition check against the current
  control header/guide/rename note and included the nine-parent/trim-log
  requirements: passed. Recomputed the inventory on reconciled main: 103 live
  pairs plus the five explicitly staged trim-log files. Only this renamed
  ticket is dirty.
- Final `git fetch origin main` confirmed HEAD equals `origin/main` at
  `7d9c95053c2a518e90f72a834eab9255011f5d61`; `git diff --check` remains clean.
  Handoff is to the frozen `evaluate-design` step, not implementation or owner
  approval. Use the current path-qualified ref above for the transition.
