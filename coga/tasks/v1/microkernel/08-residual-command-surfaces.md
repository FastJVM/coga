---
title: Classify residual command surfaces
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga/init
- coga/tickets
- coga/skill-management
- coga/recurring/scheduling
- coga/checkout-cleanup
- coga-dev/codebase
- coga-dev/testing
- coga-dev/current-direction
- coga-dev/microkernel
- coga-dev/project-stage
- coga/cli
- coga/checkouts
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
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
step: 6 (open-pr)
---

## Description

Move authoring and skill-management procedure policy out of permanent core
heads, and give task-to-recurring-template promotion an explicit owner. The
kernel should supply execution, validation, task IO and guarded publication;
the command ticket should own the procedure users want to change. This is a
proposal for cold evaluation and owner scope review, not a settled placement.

### Approved implementation scope — 2026-11-17

The owner directed this step to ship promotion first under
`coga promote-recurring`. Promotion's guarded publication failures now
return 75 (previously a warning could exit zero). The remaining increments
have separate draft execution tickets:

- `v1/microkernel/move-ticket-authoring-to-a-command-ticket` owns authoring,
  including the migration of existing `bootstrap/ticket` overrides.
- `v1/microkernel/move-skill-management-to-command-tickets` owns the full
  skill family, including the status spelling and read-only dispatch decision.

Both follow-ups depend on `v1/microkernel/03-launch-decomposition` as described
below. The design and acceptance criteria for those increments remain
reference material for their owners. This implementation reviews the
promotion-specific criteria and the shared packaging and verification criteria.

### Original objectives and proposed implementation scope

Advance editable behavior and ticket ownership by putting the complete
procedure beside a stateless command ticket. Advance simplification by deleting
command-to-command imports and replaced coordinators, not by adding forwarding
modules. This ticket owns three bounded implementation increments, after owner
approval: promotion, authoring, then the complete skill command family. The
owner may split these into execution tickets at review-design; until then all
three remain assigned here. Moving only the skill parser is not completion.

### Proposed shape: ownership and consumers

| Current surface | Proposed owner | Retained shared operation and actual consumers |
| --- | --- | --- |
| `commands/ticket.py`, authoring snapshots and `authoring.finalize_authored` | Package `bootstrap/ticket/ticket.py` and sibling `authoring.py` | `launch.spawn_agent_session` is also used by launch and megalaunch; `validate.assert_task_valid`, task IO and `git.publish` remain shared. The finalizer has one direct production caller, `commands.ticket._run_authoring_session`; megalaunch reaches that coordinator indirectly. |
| `authoring.resolve_authoring_agent`, `AUTHORING_AGENT_ENV` | Small shared authoring-agent policy module in core, with both consumers migrated | `commands.ticket.ticket`/picker and `megalaunch._author_draft` use the same precedence. Do not retain the finalizer merely to keep this resolver. |
| `commands.create.create_draft`, `_split_create_path` | Shared creation machinery in `src/coga/create.py`, with presentation in callers | Both raw create and authoring need path splitting, validation, creation and its publication. Preserve their one creation operation and messages; edge must not import `commands.create`. |
| `commands/skill.py` and procedure-specific `skill_manager.py` implementation | `bootstrap/skill/ticket.py`, sibling `skill_manager.py`; separate read entry below | Install/update/remove/status policy has one command family. `skill_update.run_update_json` consumes the public command as a subprocess, not individual implementation symbols. Test imports and generic runner dispatch are not independent consumers. |
| `skill_manager.skills_root`, `bundled_skills_root` | `paths.py`, reused by validation and moved skill implementation | `validate._check_shebang_executables` uses both roots; skill operations also use them. Init and `agent_skills.refresh_agent_skill_view` do not import skill_manager; do not invent an init dependency. |
| `skill_manager.SKILL_UPDATE_BRANCH` | Shared branch-protection contract in core, consumed by updater and branch cleanup | `branchsweep` protects this exact branch in candidate classification and ref handling. Move the constant to a small appropriate shared home, without making branch cleanup import the edge implementation. |
| `recurring.promote_task`, `PromoteOutcome`, promotion-only transform/render helpers and command presentation | `bootstrap/recurring-promote/ticket.py` and sibling `promotion.py` | Keep `recurring.Template.load`, schedule validation, effective catalog/name validation, `delete_task.run_delete_task`, task IO, log IO and `git.publish`. Removal also serves delete and recurring replacement. |

Perform an import/call audit during implementation before moving each symbol.
Helpers used only within one moved implementation move with it. In particular,
`skill_manager.gh_skill_repo`, digest/include logic, download/archive handling,
update classification and PR coordination have no second core production
consumer in the baseline. `skill_manager._verbatim_patch_ids` calls shared
branch-sweep support: retain that support where it is shared, not this wrapper.
The promotion name pattern is also used by recurring selection/catalog parsing;
expose the existing check as shared rather than copying the pattern. The
promotion workflow check, frontmatter transform and YAML renderer have only
promotion callers and move. Retain schedule validation as a public shared
operation over the existing validator, not a duplicate cron parser.

### Invocation and editable paths

The proposed final paths, relative to
`src/coga/resources/templates/coga/`, are:

| Invocation proposal | Alias expansion | Script and implementation |
| --- | --- | --- |
| `coga ticket [target] [flags]` | `launch bootstrap/ticket --` | `bootstrap/ticket/{ticket.py,authoring.py}` |
| `coga skill install\|install-local\|install-url\|update\|remove ...` | `launch bootstrap/skill --` | `bootstrap/skill/{ticket.py,skill_manager.py}` |
| `coga skill-status [--check] [--json]` | `launch --read-only bootstrap/skill-status --` | `bootstrap/skill-status/ticket.py`, using the effective skill implementation as described below |
| `coga promote-recurring <task> --schedule <cron> [--name <name>]` | `launch bootstrap/recurring-promote --` | `bootstrap/recurring-promote/{ticket.py,promotion.py}` |

These spellings are proposals requiring the owner's answers below. Existing
aliases cannot replace only a nested subcommand. Do not add nested alias
machinery or silently run `skill status` through writer dispatch. Proposed
migration removes `recurring promote` and replaces it with `promote-recurring`;
`recurring` still serves its other siblings. Proposed skill migration replaces
`skill status` with `skill-status`; the writer parser rejects `status` with the
new spelling before mutation. Preserve flags/results; changed command spelling
and alias stderr framing are the deliberate differences. No compatibility head
or permanent wrapper is implied. If the owner requires the old spellings,
revise the dispatch design before implementation rather than smuggling policy
selection into launch by command name.

For a full local fork, copy each selected `bootstrap/<ref>/` directory to
`coga/bootstrap/<ref>/` with all siblings, then edit the local implementation.
For authoring instructions, copy/edit the independently resolved
`coga/skills/bootstrap/ticket/` as well when desired. A local fork is not
updated by wheel upgrades; removing it rejoins package defaults. No live copies
are added to this source repo. Keep imports local to the selected ticket or
use shared core; do not hard-code installed-package implementation paths.

Skill status and writes must share the same classification/digest code, not
copy it. The status entry resolves the effective `bootstrap/skill` directory
through existing bootstrap resolution and invokes an explicitly named read
entry in its sibling implementation using Python. This is procedure-owned
composition between two concrete tickets, not new kernel plugin discovery.
It must honor a local full fork, fail loud if that fork omits the read entry,
and never fall back to stock code. Document this dependency in both tickets;
the discoverability sibling must include it in complete-copy results. Keep the
read entry separate from the writer parser so write operands cannot enter a
read-only invocation. If this proves more complex than one shared wheel edge
module, evaluate that alternative at owner review with a complete implementation
fork path; do not duplicate the manager to preserve the proposed layout.

### Authoring increment

Consume the shared one-session executor from
`v1/microkernel/03-launch-decomposition`; verify its landed public seams before
coding. Today `launch.spawn_agent_session` already supplies one-shot execution,
but the coordinator also reaches private readiness helpers. Do not recursively
call `launch bootstrap/ticket` from its script, chain workflows, bump the
interviewed ticket, or make core load procedure code.

`megalaunch._author_draft` currently imports `_authoring_ticket`, kickoff and
`_run_authoring_session` from `commands.ticket`. Remove that dependency in the
same migration: invoke the public command-ticket authoring operation in a
subprocess with the selected target and interviewer, preserving picked-draft
error presentation and no picker. Core must not import or path-load the moved
coordinator. Coordinate this call-site change with
`v1/microkernel/09-work-orchestration-commands-to-tickets`; if its queue move
lands first, update that effective caller instead. A retained-state 75 must
stop queue progress/publication, not be swallowed as an ordinary skipped
draft. Test both direct authoring and the picked-draft path.

Move target selection (bare interview, new title, existing qualified or unique
bare-leaf ref), ambiguity/parked refusal, ephemeral skill/step projection,
agent picker, kickoff and post-exit coordination together. Preserve the
interviewer precedence and validation of the winning term; never persist the
interviewer choice onto the target. Check TTY, configured agent, CLI presence
and Windows command representability before creating a new draft. The current
`before_create` path checks representability, while TTY/CLI checks are later in
`_run_authoring_session`: completing readiness-before-create is an explicit
correction required by this spec, not a claim that all of it already happens.

The child session uses the existing discussion interface, authoring skill and
stateless identity, no execution step or blocker-resolution preamble, ambient
environment scrubbed by `config.scrub_op_auth_env`, no target or bootstrap
secret injection. Publish the launch audit before entering the interview and
preserve usage/log teardown. Do not pass outer script completion authority
into the interviewer. Nonzero agent exit keeps the current process-status
translation and does not run successful finalization.

After successful agent exit, reload configuration, refuse a changed Git
destination, discover all changed/new surviving authored tasks and validate
them before publication (including the named unchanged target). Retain
workflow-less draft rejection, duplicate/discovery errors, symlink refusal,
relocated roots, mode changes, deletions, attachments and file-to-directory
conversion. Select exact changed files by the entry snapshot, including
changed supporting knowledge; untouched entry-dirty attachments are excluded.
Publish the selected task/support paths together through `git.publish` with
required paths and its existing eligibility/concurrency guards. Preserve shared
validation and publication safeguards; do not replace the operation with one
publish per ticket or an unconditional exit sweep.

A child process's `git.state_sweep_withheld` ContextVar cannot control its
parent launcher. Finalization refusal therefore needs the generic retained
state exit 75 so neither parent teardown refresh nor sweep separates retained
tickets from knowledge. Test the entire alias/launch/subprocess path, not only
a mocked finalizer. Coordinate generic retention behavior with the launch
sibling; no authoring-name special case in core. This deliberately normalizes
guarded finalization failures to 75; ordinary argument/readiness errors remain 2.

### Skill increment

Move the complete six-subcommand procedure and its manager logic; direct
`gh skill` remains the external implementation for GitHub/local installation,
not a replacement for URL handling or Coga's update results. Preserve source
precedence, one measured result per managed installed skill, all current JSON
fields/status meanings, exact refs and namespace collision checks, gh
capability preflight before writes and nested GitHub-ref refusal. Preserve
URL include pruning, source/installed digests and legacy repair, local
adaptation/conflict classification, force semantics, notes and metadata-only
PR changes. Status and update must continue using the same comparisons.

For `--pr`, retain local staged/unstaged/untracked preflight and clean skills
baseline before updates; then protect hand-pushed open-PR commits using the
actual push destination/host, ancestry and whitespace-sensitive patch checks.
Carry the observed remote head into the push lease. Preserve exact job commit
identity, skills-only staging/commit, harmless unrelated edits, original branch
restoration in `finally`, verification capture, draft PR create/update and
failure reporting. Do not claim stronger verification gating than the current
flow: it records verification outcomes in the PR. No new plugin system, source
support reduction or changed gh overwrite policy.

`skill status` currently loads without a user and never sweeps; the proposed
read entry must preserve that, including dirty state, no agent/TTY and no
launch audit/Git writes, through the launch sibling's read-only contract.
Writer invocations preserve their current mutation/publication semantics.
A refused branch-claim preflight currently withholds the sweep; propagate 75
across the command-ticket process boundary so that remains true. Test stdout
JSON uncontaminated by aliases, launch framing or shared-helper diagnostics.

The recurring reporting job stays owned by
`v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`.
It may continue calling public `coga skill update --all --pr --json`; this
remains a real user invocation, so do not introduce core-to-edge imports to
avoid that process. Preserve its structured failures and 0/1/2 report contract;
coordinate retained-state 75 propagation without letting it become an ordinary
failure followed by publication. No skill-manager follow-up remains unowned:
this increment includes provenance, PR flow and status, not only installation.

### Promotion increment

Move the coordinator and transform unchanged except explicit partial-failure
handling. Validate cron, source status, destination/name and workflow before
writing; preserve refusal of `in_progress` and `blocked`. Convert frozen
workflow to name, strip task-only fields and `coga/period-task`, warn on dropped
skills/blackboard, retain extension fields and body above the fence. Copy file
or directory task correctly, preserving attachments, directories, symlinks and
modes, excluding `.state-snapshot.json`; reload the destination with
`recurring.Template.load` before invoking shared local deletion. Do not replace
`run_delete_task` with the publishing `coga delete` command.

Retain cleanup of an invalid partially built destination, but report cleanup
failure instead of hiding it with `ignore_errors=True`. If source removal
fails, retain the verified destination and surviving source, name both paths
and the failed operation, and exit 75. No success audit or success message.
This is ordered filesystem work, not a distributed atomic transaction or an
automatic rollback of a possibly partial source deletion. Preserve explicit
human-attributed promotion audit only after successful source removal, then
one publication of source deletion, destination and log. Publication refusal
or failure keeps local evidence, reports recovery and exits 75; parent launch
must not refresh or separately sweep it. Test guarded publication refusal for
copied symlinks rather than silently dereferencing attachments. Do not promise
that arbitrary symlink attachments can be published by `git.publish`.

### Acceptance criteria

- [ ] Owner resolves the dispatch/scope questions; every surface above has an
      approved retained or moved owner. Leave the open-placement rows until
      their implementation and receipts land; naming a future move is not closure.
- [ ] Implement all three increments or record owner-approved execution-ticket
      assignments before narrowing scope. No deferred skill or promotion row
      loses its named owner. Shared helpers retain actual multiple consumers.
- [ ] Each moved procedure executes through its proposed alias/ticket path
      from an installed wheel, and through a complete edited local copy with
      package resources read-only. No agent is needed for deterministic skill
      or promotion invocations; no per-invocation stateful ticket is created.
- [ ] Authoring tests cover bare/new/existing interviews, full readiness before
      draft creation, picker/precedence, scrubbed no-secret child, kickoff,
      all-authored validation and one guarded finalization. Failure through
      the real launcher retains edits and suppresses parent publication.
- [ ] Skill tests preserve GitHub, URL, local and unmanaged/bundled outcomes,
      include/digest/adaptation rules, PR/branch guards and JSON. Read status
      works without user/agent/TTY and leaves dirty state untouched. Writer
      failures retain the prior publication exclusions across processes.
- [ ] Promotion tests cover both task shapes, transforms, attachments, failed
      validation/copy/cleanup/delete/publication and audit ordering; successful
      control contains the whole move after one promotion publication.
- [ ] Remove replaced registrations, single-consumer coordinators and obsolete
      imports; no core forwarding stubs or core import/path-load of edge code.
      Keep generic recipe/reporting and shared primitives with their owners.
- [ ] Update package command tickets as capability owners, user authoring,
      skill-management, recurring/templates, edge-code, script-tickets and
      state-publication topics as appropriate; CLI remains an index. Update
      local microkernel placement/codebase topics, dependent invocations,
      required resource manifest and packaging tests in the same PR. Do not
      edit archives, recreate live twins or duplicate specifications.
- [ ] Carry forward `test_ticket`, `test_authoring`, `test_create`,
      `test_skill_manager`, `test_skill_update`, `test_recurring`, `test_git`,
      `test_aliases`, `test_cli`, `test_launch`, `test_launch_script`,
      `test_megalaunch`,
      `test_branchsweep`, `test_init`, `test_packaging` and their relevant
      fixtures. Preserve cancellation fixture
      coverage when its command monkeypatch targets move. Run affected tests,
      full Linux suite, CLI smoke and task validation. Receipts record full
      revision, OS/Python, command, counts and runtime; Windows/macOS checks
      are deferred to release under current testing policy.

### Reduction baseline and expected change

Baseline `eccd3b31f199525707e1292f1517dc082ba5b511` (fetched main,
2026-11-14). Counts are physical lines including blanks/comments, using
`splitlines`; named symbol spans use Python AST `end_lineno - lineno + 1`,
excluding decorators and intervening gaps. They are scope estimates, not savings.

- Authoring: `commands/ticket.py` 423 + `authoring.py` 352 = 775 lines.
  The 59-line resolver and shared constant stay as shared policy; most other
  lines relocate. Creation adapter is 175 lines, with `create_draft` 64 and
  `_split_create_path` 15: extraction reduces coupling, not total behavior.
- Skills: `commands/skill.py` 211 + `skill_manager.py` 2,123 = 2,334 lines.
  Retain the two path helpers and shared branch constant; the rest is procedure
  scope. Do not count the 434-line `skill_update.py` reporting job as savings
  here: its migration belongs to the recipe sibling.
- Promotion: `commands.recurring.promote` 82 lines; `PromoteOutcome` 9,
  `promote_task` 104, `_template_frontmatter` 34,
  `_render_template_text` 11, `_validate_promoted_workflow` 15 = 255 named
  symbol lines, plus promotion-only constants/imports. Do not count all 2,781
  lines of `recurring.py` or all 391 command lines as removable.
- Combined direct scope is approximately 3,364 lines before shared extraction
  and the creation adapter. Most is relocation. Delete the replaced Typer
  registration/adapters and command-to-command dependency; consolidate parser
  presentation with script entrypoints. New dispatch/fork/error tests and
  scripts may offset deletions. Record actual before/after core, edge and
  ticket-script totals and removed dependency paths at named revisions;
  report tests, docs and packaged resource copies separately. No reduction
  is claimed by this design step.

### Out of scope

No implementation, branch or PR in this design step. No prompt-assembly
replacement, new launch service, generic plugin registry, nested alias system,
new supported skill sources, recurring scheduling redesign, `recurring list`
migration, recipe-registry changes, arbitrary deletion atomicity, or discovery
command implementation. The launch, read/report, recipes and discoverability
siblings retain those responsibilities. Classification can proceed now;
implementation waits only for the specific approved execution contracts it needs.

## Context

Required reads beyond the attached topics: `coga-dev/packaging` at
`docs/contexts/coga-dev/packaging/SKILL.md` (ownership and wheel rules), and
package user topics under
`src/coga/resources/templates/coga/bootstrap/contexts/`: `coga/tickets/authoring`,
`coga/recurring/templates`, `coga/edge-code`, `coga/script-tickets`,
`coga/state-publication`, `coga/knowledge` and `coga/extension-model`.
They are cited rather than attached; read their authoring, promotion,
invocation, ownership, publication and local-fork sections before implementation.

Code relationships to recheck: `commands.ticket._run_authoring_session`
passes scrubbed ambient env to `launch.spawn_agent_session`, snapshots before
spawn and calls `authoring.finalize_authored` only on zero agent exit.
`finalize_authored` validates authored refs then calls `git.publish` with exact
changed paths and `require_paths`. `commands.skill.update` runs local/remote
preflights before `skill_manager.update_skills` and then
`run_skill_update_pr_flow`; `skill_update.build_update_command` invokes that
public CLI from the reporting job. `commands.recurring.promote` calls
`recurring.promote_task` before its explicit audit/move publication;
`promote_task` uses `Template.load` before `delete_task.run_delete_task`.
These relationships, not module residence or test imports, support the boundary.

Dependencies by exact task ref:
`v1/microkernel/03-launch-decomposition` owns one-session/public readiness and
generic stateless read/retained-state execution;
`v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co` owns the
recurring skill reporting job;
`v1/microkernel/05-make-packaged-behavior-discoverable-and-editable` owns source
inspection and complete local copies;
`v1/microkernel/06-read-report-commands-as-ticket-workflows` owns read/report
heads and the sibling recurring-list spelling decision. Coordinate invocation
choices at owner review. None requires reading superseded archive material.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-microkernel-08-residual-command-surfaces-c6e747


## Design handoff — 2026-11-14

Investigated clean, fetched main at `eccd3b31f199525707e1292f1517dc082ba5b511`.
This step changes only this ticket. No code, branch or PR was created.
The proposed implementation remains assigned here in three increments; scope
splits require explicit execution-ticket assignments at owner review.

Key findings: the authoring resolver is shared with megalaunch, finalization is
not directly shared, although megalaunch imports its coordinator; skill_manager's core consumers need only roots and the protected branch
constant, not acquisition/update policy. Init/agent-view support does not import
the manager. Promotion's ordered filesystem work is not atomic. ContextVar sweep
withholding does not cross a command-ticket subprocess: retained-state 75 must
be tested through parent teardown. Existing authoring pre-create checks do not
cover every readiness condition; the proposed correction is explicit.

Verification: `coga validate --task
v1/microkernel/08-residual-command-surfaces --json` returned `ok_count: 1`, no
issues; `git diff --check` passed. Final `git fetch origin main` succeeded and
`git rev-list --left-right --count HEAD...origin/main` returned `0 0`.
No production code changed; full-suite receipts belong to implementation and
review, with native checks deferred to release. Ready for cold design evaluation.

## Open Questions

For the owner review-design gate (do not block this design step):

1. Approve `promote-recurring` as the replacement for `recurring promote`,
   coordinated with the read/report sibling's recurring-list decision? This
   avoids adding nested alias dispatch or retaining a command-specific wrapper.
2. Approve splitting `skill status` into the explicit read-only `skill-status`
   alias, retaining `skill` for writes, and the shared effective implementation
   path? Keeping the mixed spelling instead needs a reviewed pre-dispatch
   policy adapter; it cannot be implemented as a blind writer alias.
3. Approve implementation of all three increments here, or assign concrete
   follow-up tickets at scope review? Proposed order is promotion → authoring
   → complete skill family; none is dropped from the v1 placement gate.

## Evaluator review

Cold evaluation, 2026-11-14, on main `4b30967bb` (ticket-only commits since the
design baseline `eccd3b31f`). Read the body as the implementer would; no
ticket-body edits, branch, code or PR.

**Verdict: implementable in shape, not yet ready as written.** The ownership
table, consumer audit and baseline counts check out. Before implementation
starts, resolve findings 1–3 at review-design. Finding 4 is a scope decision
that blocks part of the work.

### Must resolve before implementation

1. **The documented `bootstrap/ticket` override breaks under the move.**
   `tasks.resolve_bootstrap` chooses between local and packaged as a whole
   directory: if a local `coga/bootstrap/ticket/ticket.md` exists, the local
   directory wins. The packaged `bootstrap/ticket/ticket.md` tells users to
   create exactly that file to change the install-wide authoring agent, and
   `authoring.resolve_authoring_agent` reads its `agent:` as precedence step 5.
   Once `ticket.py` exists only in the package, a repo that followed this advice
   resolves to a local directory with no script. `coga ticket` would then
   become a bare agent launch of that ticket, which skips readiness, the entry
   snapshot and guarded finalization. Separately, adding `ticket.py` changes
   what bare `coga launch bootstrap/ticket` does. A stateless script target
   runs exactly one phase (`launch_script.run_script_chain`), so the launch
   that ticket.md currently describes as an agent session becomes a script.
   The spec needs to say: (a) where the install-level default-agent setting
   lives after the move; (b) that a local `bootstrap/ticket` without
   `ticket.py` fails loudly and never falls back to an agent; (c) the new
   meaning of `coga launch bootstrap/ticket [--agent]`, given that launch's own
   `--agent` comes before `--`; (d) the ticket.md text and the
   `coga/tickets/authoring` updates. Each needs a test.
2. **The rule for nested spellings conflicts with sibling 06.** 06 (Open
   question 2) prefers to keep a fixed `recurring list` subcommand adapter over
   the read-only launch API. 08 removes `recurring promote` and rejects an
   adapter for `skill status`. 03's draft read-only contract explicitly lets a
   consumer use "a thin argv-parsing adapter" for mixed heads. If the owner
   approves 06's adapter, `recurring promote` and `skill status` could use the
   same pattern without renaming. The owner should pick one rule for all
   nested heads (adapter or rename) across 06 and 08. Questions 1 and 2 should
   state the adapter option and what it costs, not only renaming.
3. **Promotion changes an exit code without listing it.** Today
   `commands.recurring.promote` treats a `git.publish` `GitError` as a yellow
   `[git] sync failed` warning and exits 0. The Promotion increment says it
   moves the code "unchanged except explicit partial-failure handling", but it
   also requires publication refusal or failure to exit 75. That is a separate
   change in user-visible behavior. Add it to the list of deliberate
   differences, beside spelling and stderr framing, and test it.

### Scope and dependency decision (blocks part of the work)

4. **Two of the three increments depend on sibling work that has not landed.**
   `skill-status` needs `launch --read-only`, which exists only as a draft in
   `v1/microkernel/03-launch-decomposition` (step 5, review). Authoring needs
   03's public readiness seams. Promotion needs neither and can start once
   approved. The acceptance criterion "implement all three increments" in one
   ticket either holds this ticket in progress until 03 merges or forces a
   `coga block` partway through. Recommendation for Open question 3: split into
   three execution tickets or PRs, with promotion first. About 3.4k lines move
   plus new tests, which is too much to review as one PR. Each later ticket
   should depend on 03 by exact ref.

### Optional recommendations

- **Existing `create.py`.** `src/coga/create.py` already exists (413 lines,
  `create_task`, used by retire). Say to move `create_draft` and
  `_split_create_path` into that module; the current wording reads like a new
  file.
- **Private branchsweep import.** The edge `skill_manager.py` would still call
  the private `branchsweep._verbatim_patch_ids`; today it imports it lazily to
  avoid a cycle. Make it a public shared helper as part of the move. An edge
  module should not import a private core symbol.
- **`bootstrap/skill` naming.** A `bootstrap/skill/` directory sitting beside
  the `bootstrap/skills/` library, packaged and locally as `coga/bootstrap/skill/`
  next to `coga/skills/`, is easy to confuse. Consider a distinct ref such as
  `bootstrap/skill-manage`.
- **Exit 75 is already handled.** For stateless targets, `run_script_chain`
  already returns early on 75, and `commands/launch.py` sets
  `git.state_sweep_withheld`. The implementer should verify and test this
  existing generic path rather than build new retention.
- **The reporting job becomes a nested launch.** `skill_update.run_update_json`
  runs `coga skill update --all --pr --json` in a subprocess. After the move
  that is a nested `coga launch bootstrap/skill` inside the `skill-update`
  recurring period, which adds launch audit lines and alias stderr. Add one
  test that runs the real job against the alias path and checks that stdout is
  JSON its parser accepts and that the log entries are as expected.

### Verified as stated

Line counts (`commands/ticket.py` 423, `authoring.py` 352, `commands/skill.py`
211, `skill_manager.py` 2,123, `commands/create.py` 175, `recurring.py` 2,781,
`commands/recurring.py` 391, `skill_update.py` 434). Core consumers outside the
moved code:
- `skill_manager`: only `validate` (both skill roots) and `branchsweep`
  (`SKILL_UPDATE_BRANCH`).
- `finalize_authored`: called only from `commands/ticket.py`.
- `megalaunch`: imports `resolve_authoring_agent` at module level and imports
  the `commands.ticket` coordinator lazily inside `_author_draft`.
- `promote_task`: used only by `commands/recurring.py`. Its order is copy (with
  `.state-snapshot.json` excluded) → `Template.load` →
  `rmtree(..., ignore_errors=True)` on failure → `run_delete_task` → audit.
- `skill_update`: calls the public CLI through `subprocess.run`.

Default aliases have no `ticket`, `skill-status` or `promote-recurring`
collision once the built-ins are removed.

## Implementation intake — 2026-11-17

The projected ticket matches fetched main at `09a2451a4`. The feature
branch has no unique commits and no associated PR. The transition to
`implement` did not record answers to the design evaluator's scope and
dispatch questions. Launch decomposition and read/report are both still in
review. Asked the owner to decide whether promotion goes first with separate
execution tickets and whether the command spellings use top-level aliases or
preserve nested dispatch. The authoring override migration and promotion's
publication-failure exit code also need explicit treatment before their
respective implementations. Implementation is awaiting owner direction.

## Promotion implementation handoff — 2026-11-17

`coga promote-recurring` now dispatches through `bootstrap/recurring-promote`.
It verifies the destination before removing the source, then guards the
source deletion, destination files and promotion audit as one publication.
Exit 75 preserves local state on partial failure or publication refusal.
The two follow-up drafts in the approved scope above are on control.

At base `b252b9cfbaa4971b147d46c26e885a5ec314708d` and feature head `e9d717c1addec249ba49cb3c53d3c229eed79325`, physical lines
(`bytes.splitlines()` across changed paths, including blanks/comments) went from
5,326 to 5,020 in core Python and 0 to 398 in ticket Python. No `coga_edge`
files changed. Combined production scope increased by 92 lines. Most of the
procedure moved, the nested Typer adapter and core procedure ownership were
removed, and failure reporting and guarded publication checks were added.
Documentation (including the packaged command contract) went from 893 to
922 lines. Tests and the package manifest went from 16,451 to 16,570 lines.
There is one packaged procedure owner and no checked-in local duplicate.

## Peer review — 2026-11-17

Claude (Opus 5.5) ran `/code-review` at default effort on `main...HEAD`. It
returned with eight unverified findings, reviewing head
`63c35085288d09ba0cfda94c3497fbdf314d38d0` on base `291b1d58af4d940ebd8a0ed14e0dba26b18f10f1` after this step's
unconditional rebase. Codex wrote the implementation, so this was an
independent review. I checked each finding against the code.

Applied in `be11d4a5edf456be2b1acfce385fc0107bfa746e` (`peer-review: apply review findings`), with the owner
approving the approach for the two behavior fixes:

1. **Gitignored attachments broke publication.** Copied files such as
   `__pycache__/*.pyc` were added to `require_paths`, so promotion exited 75
   after the move. The old command published them fine. They are now dropped
   from the required set with `git check-ignore --no-index`. The new test
   reproduces the 75 without the fix.
2. **Symlink refusal came only after the source was deleted.** With Git
   enabled, a directory task holding any symlink is now refused with exit 2
   before anything moves. The test now asserts that the task, log and control
   are unchanged. The post-move symlink check stays as a backstop.
3. **Stale `recurring promote` spelling.** Fixed in the shipped
   `coga/recurring`, `coga/recurring/scheduling` and `coga/cli` topics.
4. **Misleading collision message.** A name used only by a bundled or other
   effective definition now names that definition instead of saying the
   local directory exists. A test covers it.
5. The command ticket documents the symlink and ignored-file behavior.

Not changed, with reasons:

- **`None` from `git.publish` with Git enabled is treated as 75.** This covers
  the soft-skips for "not a git repo" and a missing control branch. Promotion
  deliberately treats unconfirmed publication of a move as retained state.
  The cases are rare with Git enabled, and launch treats the same condition
  as "publication not confirmed".
- **The removed `--agent` refusal.** A global `--agent` on the alias now reaches
  generic launch, as it does for every other script alias. That handling
  belongs to the launch sibling, not to promotion.

Verification at `be11d4a5edf456be2b1acfce385fc0107bfa746e`: full Linux suite 4908 passed, 33 skipped; promotion
tests 19 passed; validate, CLI smoke and `git diff --check` passed. Main has
since gained one log-only commit (`76a799cf6`, `coga/log.md`). I did not
rebase again, so the receipts stay valid for this head. Native Windows and
macOS checks are deferred to release.

## PR

```yaml
title: Move recurring promotion to a command ticket
author: codex
author_evidence: "Codex implemented the change in the attended implementation session; Claude applied the peer-review fixes in be11d4a5e."
head: be11d4a5edf456be2b1acfce385fc0107bfa746e
base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
depth: deep
rationale: "Review the changed command dispatch and retained-state behavior around Git publication. The review fixes landed after the reviewed revision."
implementation: "The default alias launches the packaged procedure. With Git enabled, promotion refuses symlinked attachments before anything moves. It verifies the template before removing the source and requires the source deletion, the non-ignored destination files and the audit in one guarded publication."
deviations: "The promoted spelling is coga promote-recurring. The procedure rejects occupied effective names, including bundled definitions, and returns 75 on publication refusal or failure. Symlinked directory tasks are refused with exit 2 while Git sync is enabled. A global --agent is no longer refused by promotion itself."
limitations: "Authoring and skill management have their own execution tickets. With Git enabled, a publish soft-skip (not a git repo, or a missing control branch) exits 75 with the move retained. Native Windows and macOS verification is deferred to release. Checks used Python 3.12.12."
files:
  docs/contexts/coga-dev/codebase/SKILL.md: "Point contributors to the promotion ticket's implementation."
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: "Name the relocated promotion audit writer."
  docs/contexts/coga-dev/microkernel/SKILL.md: "Close the promotion placement and point remaining rows to their execution tickets."
  src/coga/aliases.py: "Route the new top-level spelling through the generic launch command."
  src/coga/commands/recurring.py: "Remove the replaced recurring promote adapter."
  src/coga/recurring.py: "Retain shared schedule and template-name checks and remove the promotion procedure."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: "Index the new default alias and drop promote from the recurring row."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: "Name the new promotion spelling in the command overview."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: "Use the current promotion spelling in the variants and gate text."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: "Link the promotion procedure and recovery to its command ticket."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/promotion.py: "Own the template transformation, validation, attachments, removal and audit, and name a shadowed effective definition."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/ticket.md: "Own the command contract, symlink and ignored-file rules, local customization and recovery."
  src/coga/resources/templates/coga/bootstrap/recurring-promote/ticket.py: "Parse arguments, refuse symlinks up front, and publish the complete non-ignored move through the shared Git guard."
  src/coga/validate.py: "Use the shared schedule check under its public name."
  tests/conftest.py: "Update the publication-stub comment for subprocess dispatch."
  tests/required_package_resources.txt: "Pin all three command-ticket resources."
  tests/test_packaging.py: "Exercise the alias through a read-only installed wheel and an edited local copy."
  tests/test_recurring.py: "Carry forward promotion cases; cover one Git publication, ignored attachments, up-front symlink refusal, bundled-name collisions and retained failures."
review:
  reviewer: claude
  kind: independent
  status: passed
  head: 63c35085288d09ba0cfda94c3497fbdf314d38d0
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Claude /code-review (default effort) returned eight findings on the implementation head. Two behavior fixes, three doc fixes and the message fix were applied in be11d4a5e. The two remaining findings were judged non-blocking (see Peer review). The fix commit itself was not re-reviewed by a tool."
checks:
- command: PYTHONPATH=$PWD/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/home/n/Code/coga-pytest-bt
  status: passed
  head: be11d4a5edf456be2b1acfce385fc0107bfa746e
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Pop!_OS 24.04 LTS, Linux x86_64 7.2.15-76070215-generic, Python 3.12.12. 4908 passed, 33 skipped in 850.28s."
- command: PYTHONPATH=$PWD/src TERM=dumb .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_recurring.py -k promot
  status: passed
  head: be11d4a5edf456be2b1acfce385fc0107bfa746e
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Pop!_OS 24.04 LTS, Linux x86_64 7.2.15-76070215-generic, Python 3.12.12. 19 passed, 526 deselected in 7.48s."
- command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task v1/microkernel/08-residual-command-surfaces --json
  status: passed
  head: be11d4a5edf456be2b1acfce385fc0107bfa746e
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Pop!_OS 24.04 LTS, Linux x86_64 7.2.15-76070215-generic, Python 3.12.12. ok_count 1, no issues."
- command: PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli --help | grep promote-recurring
  status: passed
  head: be11d4a5edf456be2b1acfce385fc0107bfa746e
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Pop!_OS 24.04 LTS, Linux x86_64 7.2.15-76070215-generic, Python 3.12.12. The alias row shows coga launch bootstrap/recurring-promote --."
- command: git diff --check main HEAD
  status: passed
  head: be11d4a5edf456be2b1acfce385fc0107bfa746e
  base: 291b1d58af4d940ebd8a0ed14e0dba26b18f10f1
  detail: "Passed."
```

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Close the two residual rows of the "Open command placements" table:

- **`coga ticket`**: write the co-versioning proof for its current head, or
  move it to the edge. The current split is the `bootstrap/ticket` interview
  target, `coga.authoring` finalize (validation and sync after the agent
  exits), and `commands/ticket.py`, the argument-to-draft coordinator that
  calls finalize inline. A plain `launch bootstrap/ticket` alias cannot
  replace it because the head drafts a ticket on the fly and owns the
  post-exit phase.
- **`skill *`**: record its explicit classification as a thin wrapper over
  `gh skill`, either external tooling (extractable as a `gh` extension) or
  a co-versioned package command, with the owner direction recorded.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      classify unnecessary coordinator/wrapper layers as well as placement,
      identify concrete deletions or reuse of existing authoring/finalization
      primitives, and estimate the kernel and total production-code impact.
      Hand implementation to the migration follow-up with that baseline;
      preserve validation and post-exit finalization, and keep `skill *`
      migration outside this classification ticket.

- [ ] `ticket` has a written co-versioning proof in `coga-dev/microkernel`,
      or is moved to the edge with unchanged behavior and tests.
- [ ] `skill *` has an explicit classification and reason in
      `coga-dev/microkernel`.
- [ ] Both rows leave the local-only `coga-dev/microkernel` table;
      `docs/archive/cli-extension-audit.md`, `coga/tickets/authoring`,
      `coga/skill-management` and the `coga/cli` index match.
- [ ] Any migration found here becomes its own follow-up ticket.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Already settled and out of scope (Dream W39 F48): default aliases are argv
sugar; fresh `init` is kernel; `delete` is a thin head over the `delete-task`
recipe; bare `recurring` is a thin head over `recurring-scan`.

##### Premise check (2026-10-16, pull-forward to v1)

- Delivered in part (Dream W39 F48): aliases, `init`, `delete`, bare
  `recurring` are classified in extension-model and the audit. Scope narrowed
  to `ticket` and `skill *`, the two surfaces still in the open table.

Previous ref: `microkernel/residual-command-surfaces` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
