---
title: Classify read and report commands under the small-core rule
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga/tickets
- coga/lifecycle
- coga/usage
- coga/recurring
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
step: 3 (review-design)
---

## Description

Move deterministic report and inspection policy into script command tickets
where the resulting command remains as quick, quiet and usable as today's
direct CLI. Keep shared readers, rendering and validation primitives in core
when they have real consumers. Refreshed proposal for owner scope review.

### Objectives advanced

Hackability: users can change a report by editing its owning script. Ticket
ownership: report heads become aliases to those scripts. Simplification:
remove redundant heads and repeated formatting/argument scaffolding while
reusing actual shared readers and checks.

### Proposed shape

This is a proposal for the evaluate-design and owner review-design gates, not
approval to change the mixed-command contracts below. Implement after those
choices are resolved and the necessary stateless dispatch is on main.

1. Use package-owned directory command tickets at
   `src/coga/resources/templates/coga/bootstrap/{show,status,validate,usage,recurring-list}/`
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
   their existing modules. A small shared edge helper for show/status is
   justified only by their actual common operator-cell behavior; avoid two
   copies or a core-to-edge import. Update tests to import the owning
   implementation, rather than retaining forwarding render functions in core.
4. Move usage grouping-option selection and `_format_rollup` /
   `_format_overall` from `commands/usage.py` into its script. Keep
   `usage.load_records`, `usage.rollup`, record models, capture and append
   logic in core: the repo's weekly usage-report also consumes the reader
   and rollup. Preserve deduplication, unknown accounting and timestamp
   semantics by calling those readers rather than reparsing log lines.
5. Put validation argument handling and report serialization in the
   validation ticket. Consolidate the duplicate presentation in
   `commands/validate.validate` and `validate._main` onto that owner; preserve
   `python -m coga.validate` only as a thin entry to the selected public
   invocation if the owner elects to retain that documented spelling.
   Do not import edge code from `coga.validate`. Preserve `validate.run`,
   `validate_task`, `assert_task_valid` and their shared checks as direct
   core APIs. Preserve fixes through `apply_safe_fixes`, including its
   state lock, concurrent-byte check and atomic write. Resolve the mixed
   dispatch question below before removing the old validate head. A pure
   report target must reject `--fix` before any repair; it cannot upgrade
   its launch policy in the child.
6. Move `commands/recurring.list_recurring`'s selection/presentation and
   `_print_templates_table` / `_print_picked_table` into recurring-list's
   script. Keep `recurring.list_templates` and its package-aware effective
   catalog, selection, clone ledger and scheduling machinery in core.
   Preserve catalog errors, bundled-available summary, clone rows, picked
   tasks and the `--agent` refusal. Resolve the two-word dispatch choice
   below; do not add nested alias machinery for this one surface.
7. Proposed prompt diagnostic disposition: retain `launch --prompt-report`
   as a composition diagnostic in launch, including script-target refusal,
   warnings and `_format_prompt_report`. It describes the launch-selected
   composition before spawn, including override/resource provenance, rather
   than an independent ticket report. This is a proposed co-versioned
   adapter decision for owner review, not a claim of two rendering callers.
   `compose.compose_prompt_report` remains the write-free Python API.
   The CLI currently refreshes `.agent-skills/`; preserve and document that
   effect rather than claiming the entire flag is write-free. Moving this
   formatter to a ticket would require a new invocation that duplicates
   launch target/operator classification; do not build that parallel path.
8. Delete replaced command registrations, builtin alias collisions and
   obsolete single-consumer wrappers in `cli.py` / `aliases.py`. Keep
   retained adapters explicit in the placement decision, with the reason
   and deferred work; do not declare the open-placement row settled merely
   because files moved. Update the package contract owners listed in Context,
   `bootstrap/skills/coga/show/SKILL.md`, packaging resource inventory and
   required-resource tests. Do not recreate live local definition copies.

### Stateless prerequisite and mixed operations

Implementation depends on `v1/microkernel/03-launch-decomposition`'s explicit
read-only bootstrap dispatch: `require_user=False` throughout, no agent/TTY,
no checkout normalization, Git refresh/write, audit, skill materialization,
notification, lifecycle or exit publication; inherited streams and integer
exit codes pass through. Use the same executor and environment isolation as
ordinary scripts. The sibling records implementation work, but this design's
main snapshot has no `read_only` API yet. Verify the landed contract before
starting migration; only that contract is a dependency, not all launch work.

Current `validate --fix` is also non-sweeping and loads with
`require_user=False`: `apply_safe_fixes` writes the selected ticket locally,
without audit, lifecycle or publication. Ordinary writer launch would require
a user and can refresh/publish unrelated dirt. Read-only launch must not run
a repair. Neither is a semantics-preserving substitute. Owner review must
settle the question on the blackboard; until then the implementation must
not silently change repair publication or route fixes through read-only mode.
Explicit `--check-slack` and `--check-github` remain opt-in network probes;
`--task` rejects either. Preserve those probes without making normal reads
perform network calls. A read invocation may make these explicitly requested
probes but must still have no local/publication effects.

### Acceptance criteria

- [ ] Record the owner-selected disposition for each of the six surfaces,
      including mixed validation, two-word recurring dispatch and the prompt
      diagnostic. No unresolved publication choice reaches implementation.
- [ ] Effective local report scripts can change selection/formatting without
      editing the installed wheel. Fresh-wheel tests find all five package
      definitions and demonstrate one local override. No core imports or
      path-loads ticket/edge implementations.
- [ ] Compare baseline and migrated public invocations in disposable repos
      using captured argv/stdout/stderr/exit results. Fix clock, terminal width,
      color and report timestamps for meaningful comparisons. Preserve normal
      stdout bytes and JSON schemas; account separately for the documented
      stderr alias line and help's command-path framing. Preserve parse-error
      exit 2, validation error exit 1, and successful exit 0.
- [ ] Cover show task-prefix and bootstrap resolution/history/missing target;
      status subtree, no-recurse, dirs, all/terminal counts, blocked asks,
      order aliases, reverse, narrow rendering and stale/index-lock/sync hints;
      usage every grouping, exact task filter, dates, empty/unknown records
      and bad inputs; validation task/repo modes, JSON/text, thresholds,
      fixes, malformed config and probe refusals; recurring empty/local/
      package/disabled/error/clone catalogs and picked period tasks.
- [ ] Run reads/help/refusals without configured user/agent, without TTY,
      offline, from feature and control checkouts, with dirty ticket, log,
      context and local definitions. Assert no fetch/push/spawn/notification
      or sweep calls and unchanged tracked/untracked bytes, index, HEAD,
      refs, lifecycle and log. Explicit probes are the only network exception.
      Verify no generated skill view is created by the five report scripts.
- [ ] Verify the owner-selected fix path separately: only a missing fence
      plus blackboard region is repaired, existing body/frontmatter is
      preserved, concurrent writes are refused, scoped validation stays
      scoped, and publication/user requirements match the approved contract.
      Keep ordinary bootstrap writers/stateful scripts covered so read policy
      never becomes an accidental global no-publication mode.
- [ ] Core validation preflights remain callable by launch, activation,
      creation, bump and owner reassignment. Carry existing validation issue
      and fix JSON fields and usage `Rollup.to_dict()` through unchanged;
      downstream weekly usage and Dream drift checks continue to work.
- [ ] Carry forward `tests/test_commands.py`, `test_cli.py`, `test_status.py`,
      `test_views.py`, `test_validate.py`, `test_usage.py`, `test_usage_report.py`,
      `test_recurring.py`, `test_compose.py`, `test_launch.py`,
      `test_launch_script.py`, `test_log_retention.py` and packaging coverage.
      Update CLI-driven tests to exercise real alias/subprocess dispatch,
      rather than testing removed heads through the old Typer app alone.
      Run the full Linux suite and scoped validation with exact receipts per
      `coga-dev/testing`; Windows/macOS are deferred to release.
- [ ] Update owning user topics, CLI index and local microkernel decision in
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
  call `_operator_cell`, so retain one implementation of that edge formatting.
- `src/coga/commands/validate.py`, `validate`, and
  `src/coga/validate.py`, `_main`, separately parse, invoke `run` /
  `validate_task` and serialize `ValidationReport`. Launch's preflight in
  `src/coga/launch.py` imports `assert_task_valid`; mark, bump, create,
  authoring and owner reassignment also use that gate. Shared checks cannot
  become a ticket-only dependency.
- `src/coga/commands/usage.py`, `usage`, passes `load_records` to `rollup`.
  `coga/recurring/usage-report/report.py` also invokes rollup for model and
  agent groupings. Keep those real shared readers; move report formatting.
- `src/coga/commands/recurring.py`, `list_recurring`, calls
  `src/coga/recurring.py`, `list_templates(include_available=True)` and
  `tasks.list_tasks`; only that command calls its two table helpers.
- `src/coga/cli.py`, `_should_sweep_coga_state`, excludes validate for all
  options, including fixes; `validate.apply_safe_fixes` repairs under
  `git.state_lock` and never publishes. `cli.main` rewrites only a first-token
  alias and prints its expansion on stderr. `src/coga/aliases.py`,
  `validate_aliases`, refuses a name still registered as a built-in.
- `src/coga/launch.py`, `_LaunchInvocation._align_and_classify`'s prompt-report path, calls
  `_refresh_agent_skills_for_launch` before `compose_prompt_report` and
  `_format_prompt_report`; `cli._should_sweep_coga_state` skips its sweep.
  This is already non-sweeping, but includes ignored local skill-view writes.

### Contract owners to read and update during implementation

Under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`:
`tickets/authoring` (show), `lifecycle` (status), `first-task` (validation),
`usage`, `recurring/scheduling` (list), `prompt-composition`, `launch`,
`script-tickets`, `extension-model`, `edge-code`, `state-publication` and
`cli`. Update each owner only for the contract it owns; link rather than
repeat dispatch specifications. `docs/contexts/coga-dev/microkernel/SKILL.md`
owns the placement decision; `coga-dev/testing` and `coga-dev/packaging`
own verification and package inventory. The customization sibling owns the
unified inspection/copy command; this ticket supplies editable report files
and the acceptance example, not a competing customization API.

<!-- coga:blackboard -->

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

## Open Questions

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

## Evaluator review

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

##### Acceptance criteria

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
