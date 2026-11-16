---
title: Classify read and report commands under the small-core rule
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga/tickets
- coga/recurring
- coga-dev/codebase
- coga-dev/testing
- coga-dev/current-direction
- coga-dev/project-stage
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

Move deterministic report and inspection policy into script command tickets
while preserving command output, failure behavior and quiet operation. Keep
shared readers, rendering and validation contracts in core when they have real
consumers. The owner approved revising the design around these retained core
contracts on 2026-11-15; this authoring session does not advance the review gate.

### Objectives advanced

Hackability: users can change a report by editing its owning script. Ticket
ownership: report heads become aliases to those scripts. Simplification:
remove redundant heads and repeated formatting/argument scaffolding while
reusing actual shared readers and checks.

### Proposed shape

The dispositions below are the revised design for owner review. Implementation
preserves the mixed-command contracts and waits for the necessary stateless
dispatch on main; this authoring session does not advance the workflow.

1. Use package-owned directory command tickets at
   `src/coga/resources/templates/coga/bootstrap/{show,status,usage,recurring-list}/`
   with `ticket.md` and the exact sibling `ticket.py`. No workflow, status,
   per-invocation task, agent, or completion command. Prefer full report
   implementations beside their tickets so copying a definition exposes its
   policy; use `coga_edge` only if an actual packaging constraint requires it,
   with a complete implementation-copy path rather than a wrapper-only fork.
   Shared core never imports these implementations. Local-first resolution
   must execute an edited local report, including its helpers.
2. After the launch prerequisite lands, replace `show`, `status`, and `usage`
   built-ins with default aliases shaped as
   `show = "launch --read-only bootstrap/show --"` (likewise status/usage).
   The separator sends report flags, including `--help`, to the script.
   Keep one parser per report, preserving current operands, defaults, errors,
   exits and help information. Do not add command-name exceptions to launch
   or CLI finalization. Alias expansion stays on stderr; its additional
   expansion line is the sole intended framing change, never JSON stdout.
3. Move `views.render_show`, `views.render_status`, and their report-only
   helpers/constants to ticket-owned code. Their single production callers
   do not establish shared infrastructure. Keep `views.last_updated_map`
   and its `_git_updated_by_slug` dependency in core while megalaunch and
   status both consume them. Keep shared Git proofs, log readers, task
   discovery, blocker parsing, operator derivation and service ordering in
   their existing modules. Rename `views._operator_cell` to the shared core
   API `views.operator_cell`, consumed by both report scripts; it wraps
   `bump.resolve_operator` and has two real production callers. Neither
   ticket imports the other ticket's helpers. Local scripts may replace their
   own operator-cell presentation without copying another definition. Update
   tests to import the owning implementation, rather than retaining forwarding render functions in core.
4. Move usage grouping-option selection and `_format_rollup` /
   `_format_overall` from `commands/usage.py` into its script. Keep
   `usage.load_records`, `usage.rollup`, record models, capture and append
   logic in core: the repo's weekly usage-report also consumes the reader
   and rollup. Preserve deduplication, unknown accounting and timestamp
   semantics by calling those readers rather than reparsing log lines.
5. Retain `coga validate` as a thin core head and `python -m coga.validate`
   as a core module entry. Consolidate their duplicated option-to-report
   execution and serialization into one core entry in `validate.py`, with
   thin CLI/parser adapters preserving each invocation's existing syntax and
   diagnostics. Do not create a validation bootstrap ticket or an edge import.
   `dream_validate_drift.build_validate_command` / `run_validate_json` back
   the fixed `validate-drift` recipe and invoke
   `sys.executable -m coga.validate --json`, with `--fix` by default and
   optional `--idle-hours` / `--max-blackboard-kb`. Preserve this argv contract,
   JSON fields (`generated_at`, `ok_count`, `fixes`, `issues`) and exits 0/1/2.
   The public command and recipe are real consumers of the fix-capable entry
   and serialization. Preserve `validate.run`, `validate_task`,
   `assert_task_valid` and shared checks as core APIs; keep `apply_safe_fixes`'s
   state lock, concurrent-byte check and atomic write. Both entrypoints remain
   user-independent, non-sweeping local operations, including `--fix`.
6. Move `commands/recurring.list_recurring`'s selection/presentation and
   `_print_templates_table` / `_print_picked_table` into recurring-list's
   script. Keep `recurring.list_templates` and its package-aware effective
   catalog, selection, clone ledger and scheduling machinery in core.
   Preserve catalog errors, bundled-available summary, clone rows, picked
   tasks and the `--agent` refusal. Retain `recurring list` as a fixed core
   subcommand adapter to the same read-only bootstrap launch API, forwarding
   flags and help to `bootstrap/recurring-list`. This preserves the two-word
   spelling with no nested alias mechanism or second executor. Record the
   adapter as a settled co-versioned dispatch exception in the microkernel
   topic: its contract must agree with launch's private read-only boundary,
   while selection and formatting belong entirely to the script.
7. Retain `launch --prompt-report` as a composition diagnostic in launch, including script-target refusal,
   warnings and `_format_prompt_report`. It describes the launch-selected
   composition before spawn, including override/resource provenance, rather
   than an independent ticket report. Record this as a settled co-versioned
   launch diagnostic adapter, not a claim of two rendering callers.
   `compose.compose_prompt_report` remains the write-free Python API.
   The CLI currently refreshes `.agent-skills/`; preserve and document that
   effect rather than claiming the entire flag is write-free. Moving this
   formatter to a ticket would require a new invocation that duplicates
   launch target/operator classification; do not build that parallel path.
8. Delete replaced command registrations, builtin alias collisions and
   obsolete single-consumer wrappers in `cli.py` / `aliases.py`. Keep
   retained core contracts explicit in the placement decision with their
   reasons. After implementation and verification, remove these five report
   heads from the open-placements row and record validation and the fixed
   recurring-list adapter under settled decisions; file relocation alone
   does not settle the row. Update the package contract owners listed in Context,
   `bootstrap/skills/coga/show/SKILL.md`, packaging resource inventory and
   required-resource tests. Do not recreate live local definition copies.

### Stateless prerequisite and mixed operations

Implementation depends on `v1/microkernel/03-launch-decomposition`'s explicit
read-only bootstrap dispatch: `require_user=False` throughout, no agent/TTY,
no checkout normalization, Git refresh/write, audit, skill materialization,
notification, lifecycle or exit publication; inherited streams and integer
exit codes pass through. Use the same executor and environment isolation as
ordinary scripts. PR #1233 is still OPEN and unmerged as checked on
2026-11-15 at main `0f336bef647715f62fc66854864228ff432c98b4`. Owner override, 2026-11-15: implementation may stack on PR #1233 before
merge; the owner will merge the dependent changes in order. Verify the
read-only contract on the stacked branch; only read-only dispatch is a
dependency, not all launch work. Verify that report
`--help` passes through `launch --read-only bootstrap/show -- --help` to
the script rather than Typer's launch help. Validation stays outside this
dispatch and must preserve its malformed-config diagnostic and exit 2.

Current `validate --fix` is also non-sweeping and loads with
`require_user=False`: `apply_safe_fixes` writes the selected ticket locally,
without audit, lifecycle or publication. Ordinary writer launch would require
a user and can refresh/publish unrelated dirt. Read-only launch must not run
a repair. Retaining validation in core preserves these semantics for both
the public head and automated `validate-drift` caller; no new generic
local-write mode is required by this ticket. The recipe's own later fix
publication remains its separate responsibility, unchanged by this refactor.
Explicit `--check-slack` and `--check-github` remain opt-in network probes;
`--task` rejects either. Preserve those probes without making normal reads
perform network calls. A read invocation may make these explicitly requested
probes but must still have no local/publication effects.

### Startup cost

Accept the extra interpreter startup inherent in the four script reports in
exchange for editable behavior. Do not promise equal latency or invent a
hard threshold. Measure baseline and migrated `show` / `status` median wall
time using the same disposable fixture, interpreter and environment, with
one warmup and at least ten measured runs per command. Report absolute and
relative overhead in the implementation receipt so the owner can assess it.

### Acceptance criteria

- [x] Implement the six dispositions specified above: four script reports,
      retained shared validation with two thin entries, and launch's retained
      prompt diagnostic. Verify the launch prerequisite before migration.
- [x] Effective local report scripts can change selection/formatting without
      editing the installed wheel. Fresh-wheel tests find all four package
      definitions and demonstrate one local override. No core imports or
      path-loads ticket/edge implementations.
- [x] Compare baseline and migrated public invocations in disposable repos
      using captured argv/stdout/stderr/exit results. Fix clock, terminal width,
      color and report timestamps for meaningful comparisons. Preserve normal
      stdout bytes and JSON schemas; account separately for the documented
      stderr alias line and help's command-path framing. Preserve parse-error
      exit 2, validation error exit 1, and successful exit 0.
- [x] Cover show task-prefix and bootstrap resolution/history/missing target;
      status subtree, no-recurse, dirs, all/terminal counts, blocked asks,
      order aliases, reverse, narrow rendering and stale/index-lock/sync hints;
      usage every grouping, exact task filter, dates, empty/unknown records
      and bad inputs; validation task/repo modes, JSON/text, thresholds,
      fixes, malformed config and probe refusals; recurring empty/local/
      package/disabled/error/clone catalogs and picked period tasks.
- [x] Run reads/help/refusals without configured user/agent, without TTY,
      offline, from feature and control checkouts, with dirty ticket, log,
      context and local definitions. Reuse the recording fakes in `tests/test_launch_script.py` to assert
      no fetch/push/agent-spawn/notification
      or sweep calls and unchanged tracked/untracked bytes, index, HEAD,
      refs, lifecycle and log. Explicit probes are the only network exception.
      Verify no generated skill view is created by the four report scripts.
- [x] Verify the retained core fix path separately: only a missing fence
      plus blackboard region is repaired, existing body/frontmatter is
      preserved, concurrent writes are refused, scoped validation stays
      scoped, and both entries require no user and perform no publication.
      Keep ordinary bootstrap writers/stateful scripts covered so read policy
      never becomes an accidental global no-publication mode.
- [x] Core validation preflights remain callable by launch, activation,
      creation, bump and owner reassignment. Carry existing validation issue
      and fix JSON fields and usage `Rollup.to_dict()` through unchanged;
      downstream weekly usage continues to work. Exercise `coga run
      validate-drift`'s `build_validate_command` / `run_validate_json` against
      the module entry with default `--fix`, thresholds, JSON payload and
      exits 0/1 (valid inputs for the recipe) versus 2 (failure).
- [x] Carry forward `tests/test_commands.py`, `test_cli.py`, `test_status.py`,
      `test_views.py`, `test_validate.py`, `test_usage.py`, `test_usage_report.py`,
      `test_recurring.py`, `test_compose.py`, `test_launch.py`,
      `test_launch_script.py`, `test_log_retention.py` and packaging coverage.
      Update CLI-driven tests to exercise real alias/subprocess dispatch,
      rather than testing removed heads through the old Typer app alone.
      Run the full Linux suite and scoped validation with exact receipts per
      `coga-dev/testing`; Windows/macOS are deferred to release.
- [x] Update owning user topics, CLI index and local microkernel decision in
      the implementation PR. Report named baseline/final revisions and physical
      lines (including blanks/comments) across affected core, edge and ticket
      scripts; list removed entrypoints/dependency paths and duplicates.
      Report relocation separately from deletion, and tests/docs/package copies
      separately. Make no reduction claim for this design-only step.

### Out of scope

New dashboards, new report features or JSON for show/status, cosmetic renames,
new recipe names, a second read protocol/executor, nested alias infrastructure,
changes to validation rules or safe-fix policy, usage capture/schema changes,
recurring scheduling/admission, lifecycle migration, general customization
inspection/copy tooling, and the rest of launch decomposition. Do not edit
`coga.toml` or `coga.local.toml` in this step.

## Context

### Verified source relationships

Baseline: `57b37dfc1aeddf13cde81d7eda13725587935b85` on main (2026-11-14).
Physical `wc -l` counts: commands show 37, status 96, validate 116, usage 108,
recurring 391 (only list and its render helpers are in scope); views 701,
validator 2,059, usage 1,349, compose 614. These are inventories, not proposed
wholesale extraction totals.

- `src/coga/commands/show.py`, `show`, calls `views.render_show`;
  `src/coga/commands/status.py`, `status`, calls `views.render_status`.
  In `src/coga/views.py`, only `last_updated_map` has a second production
  importer: `src/coga/megalaunch.py` uses it for the picker. Renderer test
  imports are not additional production consumers. Show and status both
  call `_operator_cell`, so retain it as the shared core `views.operator_cell` API.
- `src/coga/commands/validate.py`, `validate`, and
  `src/coga/validate.py`, `_main`, separately parse, invoke `run` /
  `validate_task` and serialize `ValidationReport`. Launch's preflight in
  `src/coga/launch.py` imports `assert_task_valid`; mark, bump, create,
  authoring and owner reassignment also use that gate. Shared checks cannot
  become a ticket-only dependency. `dream_validate_drift.build_validate_command`
  and `run_validate_json` also consume the module JSON/fix contract for
  `runner.RECIPES["validate-drift"]`; this requires shared core serialization.
  The recipe's own later publication is separate from the validator's local fix.
- `src/coga/commands/usage.py`, `usage`, passes `load_records` to `rollup`.
  `coga/recurring/usage-report/report.py` also invokes rollup for model and
  agent groupings. Keep those real shared readers; move report formatting.
- `src/coga/commands/recurring.py`, `list_recurring`, calls
  `src/coga/recurring.py`, `list_templates(include_available=True)` and
  `tasks.list_tasks`; only that command calls its two table helpers.
  Status's recurring footer also calls `recurring.list_templates`; retain
  that shared catalog API rather than moving it with list presentation.
- `src/coga/cli.py`, `_should_sweep_coga_state`, excludes validate for all
  options, including fixes; `validate.apply_safe_fixes` repairs under
  `git.state_lock` and never publishes. `cli.main` rewrites only a first-token
  alias and prints its expansion on stderr. `src/coga/aliases.py`,
  `validate_aliases`, refuses a name still registered as a built-in.
- `src/coga/launch.py`, `_LaunchInvocation._align_and_classify`'s prompt-report path, calls
  `_refresh_agent_skills_for_launch` before `compose_prompt_report` and
  `_format_prompt_report`; `cli._should_sweep_coga_state` skips its sweep.
  This is already non-sweeping, but includes ignored local skill-view writes.

### Readiness review disposition — 2026-11-15

The owner confirmed this revised design after independent authoring review.
That review found the behavior implementable and the existing workflow and
single-PR scope appropriate. Its required context cleanup and stale-wording
fix are applied. Broader context trimming is optional; testing and checkout
rules remain attached because they apply across the remaining workflow.
The owner subsequently authorized implementing on top of PR #1233 before
its merge, with the owner merging the dependent branches in order. The
implementation verifies the read-only contract on the stacked branch.
Authoring did not advance the review-design gate.

### Cited editing targets

These refs are cited rather than attached because implementation edits them:
`coga/lifecycle` at `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md`
(read “Triage”), `coga/usage` at the corresponding `coga/usage/SKILL.md`
(read “The read API” and “Retained history”), `coga/cli` at the corresponding
`coga/cli/SKILL.md` (command index and aliases), and `coga-dev/microkernel`
at `docs/contexts/coga-dev/microkernel/SKILL.md` (microkernel rule, open
placements and migration). Across implementation, peer review and publication,
preserve pure local status/usage reads, exact usage filtering and shared
rollups, positional aliases with stderr framing, and core-to-edge dependency
direction. Settle placements only after implementation and verification.
The symbol-based relationships above supply the relevant current facts;
update each owner for its own contract in the same implementation PR.

### Contract owners to read and update during implementation

Under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`:
`tickets/authoring` (show), `lifecycle` (status), `first-task` (validation),
`usage`, `recurring/scheduling` (list), `prompt-composition`, `launch`,
`script-tickets`, `extension-model`, `edge-code`, `state-publication` and
`cli`. Update each owner only for the contract it owns; link rather than
repeat dispatch specifications. `docs/contexts/coga-dev/microkernel/SKILL.md`
owns the placement decision. `coga-dev/testing` is attached read-only
verification guidance across implementation, peer review and publication; this
ticket does not change its policy. `coga-dev/packaging` owns package inventory. The customization sibling owns the
unified inspection/copy command; this ticket supplies editable report files
and the acceptance example, not a competing customization API.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-microkernel-06-read-report-commands-as-ticket-a9e2cd


## Design handoff — 2026-11-14

Completed source investigation at `57b37dfc1aeddf13cde81d7eda13725587935b85`.
Clean main start; fetched origin/main and fast-forward check confirmed already
current. No code, branch or PR created. Spec now sits under Description/Context,
with symbol-based evidence, consumer boundaries, differential acceptance and
whole-system counting method. The launch sibling's blackboard records read-only
implementation, but that API is not yet present in this main snapshot.

Verification: `coga validate --task
v1/microkernel/06-read-report-commands-as-ticket-workflows --json` reported
1 checked, no fixes and no issues; `git diff --check` passed. No runtime
changes, so no implementation/full-suite receipt is claimed. Final fetch found
only unrelated marketing-ticket/log changes; preserved and byte-verified the
design outside the repo, fast-forwarded to
`988c8d14aa391562e1fb6b5dd3f08aeb3734c6f5`, then reapplied it unchanged.

## Prior design questions — superseded by the revised body

1. **Mixed validation dispatch:** current `validate --fix` requires no user,
   repairs locally and never publishes. Read-only scripts cannot repair;
   ordinary launch writes require user/refresh/publication. Prefer preserving
   the current public contract and temporarily retaining the mixed validation
   adapter until the launch sibling supplies a justified generic local-write
   contract. Does the owner approve that bounded deferral, or explicitly want
   a changed fix contract? An ordinary launch adapter alone does not preserve
   existing semantics. Do not infer permission to publish unrelated dirt.
2. **Recurring list spelling:** one-word aliases cannot replace `recurring
   list`. Prefer retaining only a fixed subcommand adapter to the read-only
   bootstrap launch API, with all list policy in the ticket, rather than
   introducing nested aliases or renaming the public command. Approve this
   residual adapter and its explicit co-versioning/placement exception, or
   choose a public one-word spelling before implementation.
3. **Prompt diagnostic disposition:** approve keeping the existing launch
   flag and composition formatter as a co-versioned diagnostic adapter,
   including its documented `.agent-skills/` effect? A separate script would
   duplicate launch classification; keeping it is a deliberate scope decision,
   not proof that the renderer is shared.

These are review-design decisions, not blockers to completing this design
step. The evaluator should test their completeness; implementation must wait
for the selected contracts rather than silently changing semantics.

## Prior evaluator review — 2026-11-14

Cold review, 2026-11-14, at main `b11ac6739aca3e828db56e99b41e1ce9c706b94f`,
plus the read-only dispatch implementation on
`origin/coga/v1-microkernel-03-launch-decomposition-6852fc` (`0bf44d2a1`,
PR #1233, open and not merged). The ticket body is composed correctly: every
spec section is a `###` under `## Description`, background is under
`## Context`. The baseline line counts and most consumer claims check out
(`views.last_updated_map` has exactly one other production importer,
`megalaunch.py`; `_operator_cell` is called by both renderers;
`coga/recurring/usage-report/report.py` consumes `rollup`; recurring-list's
table helpers have one caller). The show/status/usage shape is implementable.
**Verdict: not ready as written.** Two must-fix gaps in the validation and
shared-helper parts would force an implementer to guess. Neither needs new
research; both need a sentence in the spec and an owner choice.

### Must resolve before implementation

1. **Validation has a second core consumer the spec omits.**
   `src/coga/dream_validate_drift.py` (`build_validate_command`,
   `run_validate_json`) backs the fixed `validate-drift` recipe in
   `runner.RECIPES`. It subprocesses `sys.executable -m coga.validate --json`
   and, by default, `--fix`. The packaged
   `bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md` documents
   that spelling. `coga-dev/internals/git-regressions` relies on it as a
   source-pinned validator. So:
   - The JSON serialization of `ValidationReport` (`generated_at`, `ok_count`,
     `fixes`, `issues`) and the fix-capable entry already have two real
     consumers, the public head and a core recipe. Under the microkernel
     rule, that presentation qualifies to stay in core. Proposed shape item 5
     ("put ... report serialization in the validation ticket"; keep
     `python -m coga.validate` only "if the owner elects") conflicts with that
     rule and with "do not import edge code from `coga.validate`". A core
     recipe cannot reach a ticket-owned serializer.
   - Open Question 1 frames the fix path as a public-CLI decision only. The
     recipe is a second, automated `--fix` caller, so the owner's answer must
     cover it too.
   - The acceptance line "Dream drift checks continue to work" is not
     testable as written. Name the recipe and its exact command contract.
   Fix: state that `python -m coga.validate` (argv, JSON payload, exits 0/1/2,
   `--fix`) is a retained core contract for `validate-drift`. Then reduce
   ticket ownership to whatever presentation that leaves (the text renderer),
   or say that `validate` stays a core head and why. Either way, the
   duplicate presentation in `commands/validate.validate` and `validate._main`
   should fold into one *core* entry, not into the ticket.

2. **The `_operator_cell` home is undecided and, as described, cannot work
   with local overrides.** Item 3 allows "a small shared edge helper for
   show/status" but names neither its path nor how two separate ticket
   directories import it. If the helper sits beside one report, the other
   report's `ticket.py` imports across ticket directories. A user who copies
   only `bootstrap/status` locally then keeps importing the package copy of
   that helper, which defeats the acceptance criterion that copying a
   definition exposes its policy. If it sits in `coga_edge`, the
   wrapper-only-fork problem in the objectives returns. Meanwhile
   `_operator_cell` is 20 lines over core `bump.resolve_operator`, with two
   real callers. "Count callers of one symbol" puts it in core as a public
   `views.operator_cell` (or beside `resolve_operator`). Fix: name the home.
   The rule-consistent choice is core, which removes the cross-ticket import
   question. A deliberate edge choice must spell out its import path and
   local-override behavior.

### Should resolve (implementer would otherwise guess)

3. **"As quick ... as today's direct CLI" has no criterion.** Every
   migrated read spawns a second interpreter that re-imports `coga`. Measured
   on this machine: `coga status` takes about 0.82 s end to end. A bare child
   `import coga.views, coga.config, coga.tasks` takes 0.17–0.28 s, roughly
   +25–35% per call, before any target resolution. Agents call `coga show`
   and `coga status` often. Either add a bounded latency acceptance check
   (for example, median wall time of migrated `status`/`show` within X% or
   Y ms of baseline in the same fixture) or drop "as quick" from the
   Description and record the accepted cost.
4. **The dependency is a PR branch, not main.** Read-only dispatch exists
   only on PR #1233. Its documented contract (bootstrap `ticket.py` only,
   exit 2 refusals, stdout to the script, alias framing on stderr, no sweep
   via `cli._read_only_launch_requested`, and `--` separator handling) matches
   what this design assumes. Two points still need checking once it lands:
   - its "requires valid existing repo configuration" refusal must keep
     today's validate malformed-config behavior (red message, exit 2) for the
     comparison criterion;
   - `coga show --help` must reach the script through
     `launch --read-only bootstrap/show -- --help` and must not be consumed by
     Typer's launch help.

   Make the precondition explicit: the implement step starts only after
   #1233 merges, and a refusal path asserts both points.
5. **Recurring-list adapter (Open Question 2).** The preferred residual
   `recurring list` subcommand adapter keeps a co-versioned head. Say what
   row the open-placements table gets afterwards. Emptying that table is a
   v1 gate (`coga-dev/microkernel`), so a retained adapter must be recorded as
   a settled core-adapter decision with its reason, not left open.

### Optional

6. Open Question 3 (prompt-report) is well argued; keeping it in launch is
   consistent with `coga-dev/microkernel` and with sibling 03's own Context
   ("Prompt-report rendering is a read-only compose diagnostic").
7. The acceptance list is broad. The no-effects criterion (item 4 in the
   acceptance list) could name its harness, for example the recording fakes
   already in `tests/test_launch_script.py` on the PR branch, so a later
   implementer reuses them instead of building a second one.
8. The status recurring footer (`views.py` near the `coga recurring list`
   pointer) calls a `recurring.py` helper that both `recurring list` and status
   share. Its core placement is already implied by "keep
   `recurring.list_templates`"; naming it avoids moving it by accident.

Scope: one coherent PR is plausible for show/status/usage/recurring-list. If
the owner keeps `validate` mostly in core (finding 1), splitting validation
into its own follow-up would keep this PR's comparison matrix tractable.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the read/report heads: `coga show`, `coga status`,
`coga validate`, `coga usage`, and `coga recurring list`. Keep shared
rendering (`coga.views`) and validation infrastructure in core where they have
two or more consumers. Decide for each head whether it is a thin read-view
wrapper with a co-versioning proof, an edge command, or alias sugar.

Preserve quick read ergonomics and machine-readable output (`--json`).

##### Startup cost

Accept the extra interpreter startup inherent in the four script reports in
exchange for editable behavior. Do not promise equal latency or invent a
hard threshold. Measure baseline and migrated `show` / `status` median wall
time using the same disposable fixture, interpreter and environment, with
one warmup and at least ten measured runs per command. Report absolute and
relative overhead in the implementation receipt so the owner can assess it.

### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      identify redundant command/report wrappers and duplicated rendering or
      checking, reusing the existing views and validation primitives where
      they serve actual callers. Report code and dependency reduction across
      core and edge while preserving quick deterministic reads, JSON, and
      exit codes.

- [ ] Each head is classified as edge command, read-view wrapper with a
      written co-versioning proof, or alias sugar, and recorded in
      the local-only `coga-dev/microkernel` topic.
- [ ] Reusable render/check/report logic moves out of command files only
      where an existing edge shape supports it without hidden transient
      parameters.
- [ ] `validate` stays fail-loud with stable exit codes and JSON for
      automation (Dream, CI, `coga launch` preflights).
- [ ] `launch --prompt-report` gets its home decided here, as handed off by
      `v1/microkernel/03-launch-decomposition`.
- [ ] The row leaves the "Open command placements" table; tests and the
      `coga/cli` index are updated.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

`show` and `status` already render through `coga.views`; verify the current
split before moving anything. A parameterized read must not smuggle hidden
launch-time input into a ticket: if a head keeps a tiny Typer layer to pass a
display parameter, say why and keep the substance outside the command file.

##### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{show,status,validate,usage,recurring}.py`.
- Surfaces resolve; the old pointer to the pre-split extension-model table now
  lives in `docs/archive/cli-extension-audit.md`.
- Not delivered: the row is open in extension-model.

Previous ref: `microkernel/read-report-commands-as-ticket-workflows` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.


## Implementation progress — 2026-11-15

Owner explicitly overrode the merge prerequisite in this attended session:
“implement it; I'll merge on top of each other.” Merged dependency PR #1233
at `0bf44d2a1ff5e5e846f29007f707c6d461cdee9e`; baseline after that merge
was `15c867b6ea7b48ec8a4ff01fa7df06e904c7dda2`. Reconciled current
origin/main with only newer ticket/log linkage. No PR opened in implement.

Four complete report scripts now live beside their package command tickets.
Show/status/usage are default read-only aliases. Recurring list is a fixed
forwarding adapter; it restores its caller's sweep policy after the read
API, avoiding a misleading retained-writer warning. Core validation has one
execution/rendering contract, two thin parsers and unchanged local safe-fix
semantics. Shared activity/operator, usage and recurring readers stay in core.
Updated contract owners, CLI index, show skill and packaging inventory.

Verification complete: final Linux suite at
`932888b381582ff39ad234052ae6f113fa0ebb9e`: 4,944 passed, 33 skipped in
1,037.66s (17m17s), Pop!_OS 24.04 LTS, Python 3.12.12. Exact command and
full head/base receipt are in PR preparation below. Scoped validation checked
1 task and seeded validation checked 5; both had no fixes or issues.
Native Windows/macOS and Python 3.11 floor suite are deferred to release.

Earlier checks: 12 dispatch/no-effects cases passed; differential matrix
116/116; wheel/local-override and seeded smoke passed. One initial full
attempt was interrupted after discovering two old autoclose tests invoking
the removed status head. An intervening full run passed 4,944/33 in 1,290.72s.
A final review then made the wheel test's copied files writable for portable
cleanup; its focused check passed, and the full final run above includes it.
No unresolved failures or adjacent bug obligations remain.

Differential comparison: 116/116 baseline/migrated public invocations at
widths 60 and 120 match after isolating alias stderr and normalizing parser
command-path/usage wrapping. Frozen datetime, fixed color and terminal width;
includes task/bootstrap show, status scope/ordering/blocked/terminal modes,
all usage groupings, exact filters/dates/unknown/duplicate records, recurring
local/package/disabled/error rows and validation modes/probe refusals.
Commands: `.venv/bin/python /tmp/coga06-matrix.py` and normalization of its
captured `/tmp/coga06-matrix/results.json`. Initial smoke matrix also matched.

Startup benchmark: `.venv/bin/python /tmp/coga06-baseline.py` captured the
baseline source. Final paired run: `.venv/bin/python
/tmp/coga06-paired-timing.py`; same disposable fixture, Python 3.12.12,
TERM=dumb, width 100, one warmup plus ten measured calls per source/command,
alternating order to reduce machine-load bias. At runtime source
`87fd7b19f7b0e049f082fc5e05fef460d910da3a` (production unchanged at
`932888b381582ff39ad234052ae6f113fa0ebb9e`), median show:
0.357473s -> 0.533026s (+0.175553s, +49.11%); status:
0.277857s -> 0.485878s (+0.208021s, +74.87%). Full-suite load was present
on both paired measurements. These are accepted extra interpreter costs,
not a latency guarantee. The earlier light-load comparison measured about
0.16s overhead per command.


## Whole-system accounting

Baseline `15c867b6ea7b48ec8a4ff01fa7df06e904c7dda2` (dependency merged,
before report changes) versus final implementation
`932888b381582ff39ad234052ae6f113fa0ebb9e`. Count method: `git show
<revision>:<path>` physical lines via `splitlines()`, including blank/comment
lines; missing paths count zero. Same named paths at both revisions.

| Production path | Before | After |
| --- | ---: | ---: |
| src/coga/aliases.py | 95 | 95 |
| src/coga/cli.py | 675 | 672 |
| src/coga/commands/recurring.py | 391 | 274 |
| src/coga/commands/show.py | 37 | 0 |
| src/coga/commands/status.py | 96 | 0 |
| src/coga/commands/usage.py | 108 | 0 |
| src/coga/commands/validate.py | 116 | 65 |
| src/coga/views.py | 701 | 97 |
| src/coga/validate.py | 2059 | 2078 |
| bootstrap/show/ticket.py (under package resources) | 0 | 100 |
| bootstrap/status/ticket.py | 0 | 618 |
| bootstrap/usage/ticket.py | 0 | 114 |
| bootstrap/recurring-list/ticket.py | 0 | 149 |
| Total | 4278 | 4262 |

Core: 4278 -> 3281; full ticket scripts: 0 -> 981; coga_edge: 0 -> 0
in this scope. Most of the core decrease is relocation, not deletion.
Whole-system physical delta is -16 lines; validation's two adapters plus
engine decrease by 32 lines through consolidated execution/serialization.
The recurring adapter adds scaffolding; no wholesale complexity reduction
is claimed from moving files. Removed three built-in heads/registrations,
their collision entries, core renderer entrypoints and recurring's private
table helpers; no forwarding render functions or core-to-ticket imports.
Shared operator cells/activity clocks, usage rollups and recurring catalog
readers remain single shared implementations. Prompt-report remains launch's
existing diagnostic; no new parallel classifier/executor was introduced.

Separately, `git diff --numstat <baseline> <final>`: tests/inventory/helper
files, 19 paths, +314/-80 lines; documentation and package ticket Markdown,
19 paths, +175/-12 lines (excludes routine ticket/log changes from main).
These are committed package owners only; no physical/live counterparts or
forwarders were added. The four scripts are counted once as production,
not again as package copies. PR #1233's own decomposition changes predate
this counting baseline and are not claimed as this ticket's simplification.


## Implement handoff — 2026-11-15

Implemented and pushed branch
`coga/v1-microkernel-06-read-report-commands-as-ticket-a9e2cd` at
`932888b381582ff39ad234052ae6f113fa0ebb9e`. Final fetch found no new main
commits; merge base is `a8d0e9f8cc5b97ff68f60962826cd5a3448113f9`. Only
this projected ticket is dirty and it was never staged or committed.

Peer review should inspect the report ownership boundary, validation's shared
entry and the recurring-list forwarding policy. PR #1233 is included at
`0bf44d2a1ff5e5e846f29007f707c6d461cdee9e` by explicit owner direction;
it must merge before or with this branch. Its own code is not claimed as
this report extraction's reduction. No PR was opened in implement.
Independent code review is next; the prepared advisory depth is deep.
No coga.toml or coga.local.toml edits. All code, docs and tests are committed;
startup overhead and release-only native verification are disclosed above.


## Peer review

2026-11-16, Claude (Opus 5.5) peer-review session. The `/code-review` skill
(default effort) **returned** against `main...HEAD` after rebasing onto
`3d589e7d434dce7e758afa262ad5b8f1e5fb9a65` (main moved only by ticket/log commits). It covered the whole branch,
including stacked PR #1233. Independent of implementation (Codex authored it).
The review covered head `c43fd777d591ff84944fdb24325d786eba000545`. The fixes
below are small and were re-verified by the full suite at final head `de22be4715a86bc8025f9170caaae151079cada3`,
but no second review ran on that head.

Findings and dispositions:
1. Confirmed: report `--help` (`status`/`show`/`usage`/`recurring list`)
   exits 2 with "No coga.toml found" outside a repo or with a broken config;
   it used to print help. The attending owner chose **accept and document**
   over a package-only fallback. Documented in `coga/launch` "Read-only
   command dispatch".
3–4. Fixed: validation caught every `ValueError` as an exit-2 option refusal,
   and the module entry split the message on `;`. A dedicated
   `ValidationOptionError` now carries the long and short refusals. Tests
   cover both probe refusals and confirm internal ValueErrors are not masked.
5. Fixed: the `recurring list` adapter now passes its exits through
   `process_exit_status`, like `coga launch`.
Belong to stacked PR #1233 code, not this ticket; left for that PR/owner:
(2) megalaunch Windows `agent_command_refusal` now runs against the plain
launch env instead of the supervised step env; (6) the read-only path returns
a negative code when the child is killed by a signal (-2 → shell 254, not 130);
(7) `launch(read_only=True)` sets `state_sweep_withheld` without resetting it,
which the recurring adapter compensates for; (9) a dead `agent` lookup in
megalaunch preflight; (10) attended launch composes the prompt twice.
(8) Ad-hoc `TOMLDecodeError` handling predates this branch.

No terminal-only surface beyond CLI output, which the differential matrix and
spot checks covered.


## PR

```yaml
title: "Move read reports into editable command tickets"
author: codex
author_evidence: "This implementation session ran as Codex; identity comes from the session, not ticket assignment."
head: de22be4715a86bc8025f9170caaae151079cada3
base: 3d589e7d434dce7e758afa262ad5b8f1e5fb9a65
depth: deep
rationale: "Significant ownership/dispatch change stacked on an open dependency; independent review returned with fixes applied, and residual #1233 findings need the owner."
implementation: "Four complete editable script reports, three read-only aliases, a recurring-list adapter and shared validation execution/rendering; contracts and packaging updated."
deviations: "Owner authorized stacking PR #1233 before merge; the dependency is included in this branch."
limitations: "Windows/macOS and Python 3.11 floor suite deferred to release. Startup adds an interpreter. Report --help now needs a valid repo config (owner-accepted, documented). PR #1233 must land before or with this branch; its own review findings are listed under Peer review."
files:
  "docs/contexts/coga-dev/codebase/SKILL.md": "Stacked PR #1233 read-only executor dependency."
  "docs/contexts/coga-dev/internals/agent-spawn/SKILL.md": "Stacked PR #1233 read-only executor dependency."
  "docs/contexts/coga-dev/internals/state-publication/SKILL.md": "Stacked PR #1233 read-only executor dependency."
  "docs/contexts/coga-dev/microkernel/SKILL.md": "Update the owning report/shared-core contract or index."
  "docs/contexts/coga-dev/packaging/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/aliases.py": "Replace report built-ins with default read-only aliases."
  "src/coga/cli.py": "Remove replaced registrations and command-name sweep exceptions."
  "src/coga/commands/launch.py": "Stacked PR #1233 read-only executor dependency."
  "src/coga/commands/recurring.py": "Forward list argv/help to the same read-only launch API."
  "src/coga/commands/show.py": "Remove replaced show head."
  "src/coga/commands/status.py": "Remove replaced status head."
  "src/coga/commands/validate.py": "Keep the public parser over shared core execution/rendering."
  "src/coga/launch.py": "Stacked PR #1233 read-only executor dependency."
  "src/coga/launch_script.py": "Stacked PR #1233 read-only executor dependency."
  "src/coga/megalaunch.py": "Stacked PR #1233 read-only executor dependency."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md": "Stacked PR #1233 read-only executor dependency."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md": "Stacked PR #1233 read-only executor dependency."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/recurring-list/ticket.md": "Own the stateless report behavior and customization route."
  "src/coga/resources/templates/coga/bootstrap/recurring-list/ticket.py": "Own the complete editable report parser and presentation."
  "src/coga/resources/templates/coga/bootstrap/show/ticket.md": "Own the stateless report behavior and customization route."
  "src/coga/resources/templates/coga/bootstrap/show/ticket.py": "Own the complete editable report parser and presentation."
  "src/coga/resources/templates/coga/bootstrap/skills/coga/show/SKILL.md": "Update the owning report/shared-core contract or index."
  "src/coga/resources/templates/coga/bootstrap/status/ticket.md": "Own the stateless report behavior and customization route."
  "src/coga/resources/templates/coga/bootstrap/status/ticket.py": "Own the complete editable report parser and presentation."
  "src/coga/resources/templates/coga/bootstrap/usage/ticket.md": "Own the stateless report behavior and customization route."
  "src/coga/commands/usage.py": "Remove replaced usage head."
  "src/coga/resources/templates/coga/bootstrap/usage/ticket.py": "Own the complete editable report parser and presentation."
  "src/coga/validate.py": "Consolidate CLI/module execution and stable report serialization."
  "src/coga/views.py": "Retain only shared activity and operator APIs."
  "tests/conftest.py": "Verify moved reports, shared validation or resource ownership."
  "tests/report_helpers.py": "Verify moved reports, shared validation or resource ownership."
  "tests/required_package_resources.txt": "Verify moved reports, shared validation or resource ownership."
  "tests/test_aliases.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_autoclose.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_cli.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_commands.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_dream_validate_drift.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_git.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_launch_script.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_log_retention.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_megalaunch.py": "Stacked PR #1233 read-only executor dependency."
  "tests/test_packaging.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_recurring.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_recurring_state.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_smoke.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_status.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_usage.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_validate.py": "Verify moved reports, shared validation or resource ownership."
  "tests/test_views.py": "Verify moved reports, shared validation or resource ownership."
review:
  reviewer: claude
  kind: independent
  status: returned
  head: c43fd777d591ff84944fdb24325d786eba000545
  base: 3d589e7d434dce7e758afa262ad5b8f1e5fb9a65
  detail: "/code-review (default effort) by Claude Opus 5.5 returned 10 findings across the branch including stacked #1233. Fixed validation error narrowing and recurring-list exit normalization; help-outside-repo regression accepted and documented by owner; #1233-owned findings recorded in Peer review. The fix commits after the reviewed head were not re-reviewed; the full suite covers the final head."
checks:
  - command: "TERM=dumb PYTHONPATH=$PWD/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga06-pytest-peer2 -q -p no:cacheprovider"
    status: passed
    head: de22be4715a86bc8025f9170caaae151079cada3
    base: 3d589e7d434dce7e758afa262ad5b8f1e5fb9a65
    detail: "4947 passed, 33 skipped in 1111.74s (18m31s); Pop!_OS 24.04 LTS, Python 3.12.12. Windows/macOS and Python 3.11 floor suite deferred to release. Implementation-session receipts (4944/33 at 932888b38, differential matrix 116/116, timing) are historical."
  - command: "TERM=dumb PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task v1/microkernel/06-read-report-commands-as-ticket-workflows --json"
    status: passed
    head: de22be4715a86bc8025f9170caaae151079cada3
    base: 3d589e7d434dce7e758afa262ad5b8f1e5fb9a65
    detail: "1 task checked, no fixes or issues; Pop!_OS 24.04 LTS, Python 3.12.12."
  - command: "git diff --check origin/main...HEAD"
    status: passed
    head: de22be4715a86bc8025f9170caaae151079cada3
    base: 3d589e7d434dce7e758afa262ad5b8f1e5fb9a65
    detail: "No whitespace errors."
```
