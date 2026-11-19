---
title: 'Recipe migration, part 5 (parked): move branch-sweep and autofix replay adapters'
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
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
step: 2 (evaluate-design)
agent: claude
launch_generation: bb6da563-ea9b-4216-9a98-20a5669d3f31
---

## Description

Part 5 of the recipe migration. Remove the `branch-sweep` and
`autofix-analyze` entries from `runner.RECIPES` by moving each adapter out of
core. The shared implementations stay in core. After 04b–04d remove five
entries, this leaves five: `recurring-scan`, `open-pr`, `delete-task`,
`publish-state`, `prepare-checkout`.

- `branch-sweep`: the recurring job calls the recipe wrapper. Separately,
  `checkout_disposal._sweep_owned_branches` calls `sweep_branches` with an
  owned-branch restriction, and `skill_manager` reuses the patch-ID support.
  Those shared primitives stay in core.
- `autofix-analyze`: recurring scans and named runs use live analysis
  (`recurring_autofix.run_autofix`). This recipe replays a saved run record
  instead. The shared analysis and ticketing stay in core; only the replay
  adapter moves.

Objectives advanced (`coga-dev/microkernel/objectives`):

- **Hackability.** A user can find and fork the sweep's orchestration and
  report, and the replay's verdict handling, without editing the wheel.
- **Small kernel.** Two registry entries and their adapter code leave core.
- **Simplification.** One duplicated create/sync/notify tail in
  `recurring_autofix.py` is deduplicated.

**Activation (confirmed 2026-11-18).** The stateless publication contract
came from `v1/microkernel/06-read-report-commands-as-ticket-workflows` (PR
#1240, merged). Ordinary `coga launch bootstrap/<name> -- args` runs a
bootstrap `ticket.py` with its argv, skips the checkout boundary, and keeps
the CLI end-of-command sweep (`coga/script-tickets`, `coga/launch`,
`coga/state-publication`). `coga retire` already uses this as a writing
command ticket: `retire = "launch bootstrap/retire --"`. Part 04 (PR #1245,
merged) delivered `runner.run_entry`. **Implementation still waits** for
04b, 04c and 04d to merge, because this ticket edits the same registry,
docs and tests. The owner chose on 2026-11-18 to design now, so the
branch-sweep part may need rework if `v1/why-is-the-code-so-big` lands first
(see Open Questions Q1/Q2 on the blackboard).

Done when both adapters run outside core with unchanged behavior,
`coga run branch-sweep` and `coga run autofix-analyze` exit 2, and the
checklist below holds.

### Acceptance criteria

- [ ] `runner.RECIPES` has no `branch-sweep` or `autofix-analyze` entry, and
      `runner.py` no longer imports `run_branch_sweep_recipe` or
      `run_autofix_analyze_recipe`. `coga run branch-sweep` and
      `coga run autofix-analyze` exit 2 through the existing
      `UnknownRecipeError` path in `commands/run.py`, with no stub or
      forwarding entry. `tests/test_runner.py::EXPECTED_RECIPES` is updated.
- [ ] `src/coga_edge/branch_sweep.py` holds the branch-sweep adapter. It
      imports only stdlib and shared `coga.*`, never another edge module,
      and production `src/coga/` neither imports nor path-loads it.
- [ ] The packaged `recurring/branch-sweep/ticket.py` runs the edge module
      through `runner.run_entry(..., scheduled=True)`. A clone-scoped run
      (no `COGA_SCRIPT_TASK`) never bumps. A launched period task bumps once
      after success, and a bump failure becomes the exit status.
- [ ] A new packaged command ticket `bootstrap/branch-sweep/` (`ticket.md`
      plus a thin `ticket.py` shim) and a default alias
      `branch-sweep = "launch bootstrap/branch-sweep --"` provide
      `coga branch-sweep` and
      `coga branch-sweep --publish-and-release-local <branch> <oid>`. Their
      argv validation, exit codes (0/2), stdout report and stderr messages
      are byte-identical to today's `coga run branch-sweep`.
- [ ] A new packaged command ticket `bootstrap/autofix-analyze/` holds the
      complete replay adapter beside `ticket.md`: the parser, run-log
      selection and verdict handling. A default alias
      `autofix-analyze = "launch bootstrap/autofix-analyze --"` provides
      `coga autofix-analyze [<run-log.md>] [--agent X] [--dry-run]`. Its
      operands, defaults, `--help` text, output and exits (0/1/2) match
      today's recipe. Only the argparse `prog` changes, to
      `coga autofix-analyze`.
- [ ] `recurring_autofix.run_autofix_analyze_recipe` and
      `_resolve_run_log` are deleted from core. A new core helper,
      `recurring_autofix.announce_autofix_ticket`, now does the
      `git.sync_task_state` + `post` step that was duplicated. Both
      `run_autofix` and the replay script call it, so it has two
      production consumers.
- [ ] Per-symbol audit of `branchsweep.py` and `recurring_autofix.py` is
      recorded on the blackboard and in the PR. Every symbol left in core
      has a production consumer other than the moved adapter. Every symbol
      the edge module imports is public: no `from coga.branchsweep import _x`.
- [ ] Old callers: stock, customized and parked `run_recipe(...,
      "branch-sweep", ...)` shims, plus every markdown or skill text naming
      `coga run branch-sweep` or `coga run autofix-analyze`, are covered by
      the `coga/edge-code/edge-code-upgrades.md` inventory/callers passages
      and fixtures, the same way 04b–04d do it.
- [ ] Every same-PR surface listed in Context is updated. Packaging tests
      require the new package files and accept no live twins.
- [ ] `tests/test_branchsweep.py` adapter tests (report, failure exit,
      release operation) and `tests/test_recurring_autofix.py` replay
      tests pass against the moved code. The suites for
      `checkout_disposal`, `skill_manager`, `branchcleanup`, retire,
      recurring, the runner and the recurring shims pass unchanged.
- [ ] Verification follows the shared migration rules in 04c. Report
      before/after production line counts per file (core / edge / ticket
      scripts, `wc -l`) from baseline `6ec117021`, separating moved,
      deleted and deduplicated code. Run the per-change Linux receipt from
      `coga-dev/testing`, the packaging checks, and `coga validate` in a
      disposable fixture.

### Proposed shape

Start from current main after 04b–04d have merged. Re-run every consumer
grep at that revision. If `v1/why-is-the-code-so-big` has merged by then,
re-derive the branch-sweep symbol list against its smaller module and apply
the owner's answers to Q1/Q2 before moving anything.

**A. Branch-sweep adapter → `src/coga_edge/branch_sweep.py`.**

1. Move these from `src/coga/branchsweep.py`. Each one's only production
   consumer is `run_branch_sweep_recipe`, or a helper reached only from it:
   - `run_branch_sweep_recipe`, as the module's worker
     `_run(cfg, argv) -> int`, unchanged.
   - `render_sweep_report` and `SWEEP_REPORT_HEADING`.
   - `discharge_owned_followups`, unless Q2 says otherwise.
   - The release operation, unless Q1 drops it: `_release_local_draft`,
     `_ReleaseRefused`, `_github_git_identity`, `_release_repository`,
     `_check_release_tip`, `_check_release_claims`,
     `_release_control_refs`, `_RELEASE_OPTION`.
2. Promote to public names any helpers the moved code still uses that also
   serve `sweep_branches` in core. Today those are `_publish_retirement_tag`,
   `_terminal_owners`, `_merged_prs`, `_closed_unmerged_prs`,
   `_live_ticket_branches`, `_draft_claim`, `_worktree_paths_by_branch`,
   `_note` and `_git`. Each then has two consumers: core `sweep_branches`
   and the edge adapter. Rename them in place, update their internal
   callers and `__all__`, and add no aliases. Drop any name the moved code
   no longer needs.
3. Keep in core, with their existing consumers: `sweep_branches`,
   `BranchSweepResult` (`checkout_disposal`), `_verbatim_patch_ids`
   (`skill_manager`; rename it to public too while touching it),
   `merged_pr_verdict`, and every sweep internal. Also keep
   `autoclose.dispose_worklist_backlog`. Its consumers are the autoclose
   job and `discharge_owned_followups`, so it must stay in core either way:
   two edge modules cannot share a sibling import.
4. Entry point:
   `main(argv: list[str] | None = None, *, scheduled: bool = False) -> int`,
   which returns
   `runner.run_entry("branch-sweep", _run, argv, scheduled=scheduled)`.
   No root resolver: it works on the invoking config's root, as today.
   Add the `if __name__ == "__main__"` guard required by the 04b–04d
   edge-module shape.
5. `src/coga/resources/templates/coga/recurring/branch-sweep/ticket.py`
   becomes a shim: `from coga_edge.branch_sweep import main`,
   `raise SystemExit(main([], scheduled=True))`. Delete its hand-rolled
   `COGA_TASK_SLUG` bump. `run_entry`'s scheduled bump replaces it, and
   it bumps only when `COGA_SCRIPT_TASK` names the task.
6. New `src/coga/resources/templates/coga/bootstrap/branch-sweep/ticket.md`
   is the command contract, modeled on `bootstrap/retire/ticket.md`: no
   agent phase, no task per invocation. Its operations are a plain sweep,
   and the release operation if Q1 keeps it. It also covers the exit
   codes, report destination (stdout, since a stateless target has no
   blackboard) and the configured-workspace requirement.
   `bootstrap/branch-sweep/ticket.py` is a shim:
   `raise SystemExit(main(sys.argv[1:]))`.
7. Add `"branch-sweep": "launch bootstrap/branch-sweep --"` to
   `aliases.DEFAULT_ALIASES`. Extend the comment above it the way the
   `retire` comment explains its `--`.

**B. Autofix replay adapter → `bootstrap/autofix-analyze/`.**

1. New `src/coga/resources/templates/coga/bootstrap/autofix-analyze/ticket.md`
   is the command contract, moved out of `coga/recurring/autofix`'s
   "Operating it" bullet. That bullet becomes a link.
   `ticket.py` holds the whole adapter beside it, following the 06 rule of
   full implementations beside report tickets:
   - the argparse parser (`prog="coga autofix-analyze"`, same operands, help
     and defaults);
   - the run-log selection now in `_resolve_run_log`, including the newest
     `.coga/recurring-runs/*.md`;
   - the ok/duplicate/dry-run/create branches, with identical messages
     and exits.
   It imports only core: `recurring_autofix.analyze_record`,
   `create_autofix_ticket`, `announce_autofix_ticket`, `AutofixUnavailable`,
   `config.load_config` and `ConfigError`. It needs no `coga_edge` module
   because no second shim consumes it.
2. In `src/coga/recurring_autofix.py`:
   - delete `run_autofix_analyze_recipe`, `_resolve_run_log` and the
     `--- recipe surface ---` banner;
   - drop `argparse` if it becomes unused;
   - add `announce_autofix_ticket(cfg, slug, task_dir, title, *, source: str)`,
     which calls `git.sync_task_state` and `post` with the existing message
     shapes (source `"the recurring sweep"` vs the run-log file name);
   - call it from `run_autofix`;
   - rewrite the module docstring's "That is why it is a *recipe*
     (`coga run autofix-analyze`)" sentence. The property it protects (text-only
     analysis; mutations on deterministic paths) is unchanged.
3. Add `"autofix-analyze": "launch bootstrap/autofix-analyze --"` to
   `aliases.DEFAULT_ALIASES`.

**C. Registry, docs, tests, packaging, all in the same PR.**

- `runner.py`: remove both entries and imports. Fix the
  `FAILURE_REPORT_CHARS` comment if the constant it cites moved.
- Tests: in `tests/test_branchsweep.py` and `tests/test_recurring_autofix.py`,
  import the moved code from its new owners. For the bootstrap
  `ticket.py`, use the loading approach 06's report tests use. Add shim
  tests to `tests/test_recurring_shims.py`, alias tests where 06 put
  them, and a `coga run <name>` exit-2 test for each removed name.
- Packaging: add the new package files to
  `tests/required_package_resources.txt` and `tests/test_packaging.py`'s
  lists, and the edge module to the wheel checks 04b–04d use.
- Update the docs and strings listed in Context.

### Out of scope

- Shrinking or redesigning `sweep_branches`, the retirement-tag rules, or
  the proofs. That is `v1/why-is-the-code-so-big`.
- Deciding whether `--publish-and-release-local` should exist (Q1) or
  where `discharge_owned_followups` belongs long-term (Q2). This ticket
  moves what main has, unless the owner answers otherwise first.
- Moving live analysis (`run_autofix`, `analyze_record`, prompt building,
  ticket creation) or the sweep's run-record writing.
- Changing the branch-sweep schedule, clone scope, or the
  `autoclose-merged` job (04c).
- Adopting the migration on this repo's own recurring state. Record a
  rollout plan on the blackboard; don't perform it in the PR. This repo's
  `coga/recurring/branch-sweep/ticket.md` is a state-only carrier, so
  nothing local changes.
- `recurring-scan`, `open-pr`, `delete-task`, `publish-state`,
  `prepare-checkout`.

## Context

### Codebase facts at `6ec117021` (re-verify after 04b–04d)

- `src/coga/runner.py`: `RECIPES` currently holds 12 names. `run_recipe`
  raises `UnknownRecipeError`, and `commands/run.py::run` turns that into
  exit 2. `run_entry(name, worker, argv, *, root, scheduled, cfg)` runs
  `run_reported` → `_publish_after` (`state_sweep.sweep_root`) → bump only
  when `scheduled` and `task_env.is_script_task` confirms
  `COGA_SCRIPT_TASK`.
- `src/coga/branchsweep.py` is 1,730 lines.
  `run_branch_sweep_recipe(cfg, argv, *, result=None)` accepts `[]` or
  exactly `["--publish-and-release-local", branch, oid]`; anything else
  exits 2. A sweep runs `sweep_branches` then `discharge_owned_followups`,
  then writes `render_sweep_report` to the env blackboard
  (`task_env.blackboard_from_env`) or to stdout. It exits 2 on
  `result.failure`. Its only production caller is `runner.RECIPES`.
- Shared consumers that keep symbols in core:
  - `checkout_disposal._sweep_owned_branches` lazily imports
    `sweep_branches` and `BranchSweepResult` (lazily because `branchsweep`
    imports `checkout_disposal.live_checkout_claim`);
  - `skill_manager` imports `branchsweep._verbatim_patch_ids` as
    `patch_ids`;
  - `branchcleanup` mentions `merged_pr_verdict` only in a comment.
- `discharge_owned_followups` uses `autoclose.dispose_worklist_backlog`,
  several `retire_worklist` functions, `git.publish`, `git.state_lock` and
  `atomicio.atomic_write_text`. The recipe is its only caller.
- `src/coga/recurring_autofix.py` is 1,035 lines.
  `run_autofix_analyze_recipe` and `_resolve_run_log` are reached only
  from `runner.RECIPES`. `recurring_runner` imports `run_autofix` and
  record types, not the recipe. `run_autofix` and the recipe both end
  with `create_autofix_ticket` → `git.sync_task_state` →
  `notification.post`.
- The clone-scoped runner, `recurring_runner._run_clone_scoped` →
  `run_clone_template`, subprocesses the template `ticket.py` with no
  period task and keeps stdout in `.coga/recurring-clone/branch-sweep.log`
  and the run record. A named `coga recurring launch branch-sweep` runs it
  now, ignoring the clone ledger, but adds an owner gate, control catch-up
  and an autofix pass. That is why it does not replace the manual command.
- Precedents to copy: `bootstrap/retire/` for a writing script command
  ticket behind a `--` alias; `bootstrap/{show,status,usage}` and 06's tests
  for loading a bootstrap `ticket.py` in tests; 04c's ticket body for the
  shared migration rules (edge home, old callers, verification table).

### Surfaces naming the removed spellings or moved code

- Code: `src/coga/branchcleanup.py`. A user-facing note says "`coga run
  branch-sweep` prunes the branch on its next run"; change it to
  `coga branch-sweep` and update `tests/test_branchcleanup.py` and
  `tests/test_retire.py` to match.
- Package docs:
  - `bootstrap/contexts/coga/cli` (recipe list and alias table);
  - `coga/extension-model` (the `autofix-analyze` line);
  - `coga/recurring/autofix` ("Operating it");
  - `coga/checkout-cleanup/branch-sweep` (the release command and the
    `skipped-worktree-pinned` sentence);
  - `coga/checkout-cleanup/terminal-owners`;
  - skill `coga/branch-sweep/sweep`, which names
    `coga.branchsweep.run_branch_sweep_recipe` and `coga run branch-sweep`;
  - workflow `branch-sweep/sweep.md`;
  - `recurring/branch-sweep/ticket.md` (on-demand spellings);
  - `coga/edge-code/edge-code-upgrades.md` (add both names to the callers
    regex).
- Local docs: `docs/contexts/coga-dev/microkernel` (the registry count) and
  `coga-dev/codebase` (source map).

### Rules

From `coga-dev/microkernel` (cited, not attached):
- Core keeps shared infra with at least two real consumers, or a reviewed
  co-versioned command contract.
- Production `src/coga/` never imports `coga_edge`.
- Count callers of one symbol, not copies of one body.

Read its "Edge packaging invariants" section, plus `coga-dev/packaging`,
`coga-dev/testing`, and the package-owned `coga/edge-code`,
`coga/script-tickets` and `coga/state-publication` under
`src/coga/resources/templates/coga/bootstrap/contexts/`.

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

## Design step status (2026-11-18)

Spec written against main `6ec117021` (Description + Context). The original
blocker is resolved: PRs #1245 and #1240 merged. The owner chose to design
now rather than wait for `v1/why-is-the-code-so-big`.

Implementation gate: 04b, 04c and 04d must merge first.
- At design time, 04b and 04c were blocked at implement and 04d was in
  review.
- `v1/why-is-the-code-so-big` was blocked at design, waiting for owner
  answers to its Q1–Q6.
- If it lands before implementation, re-derive the branch-sweep symbol
  list against the smaller module (Proposed shape preamble).

Key design choices, with reasons:
- **Branch-sweep goes to `coga_edge`, not beside a ticket.** Two shims
  consume it (the recurring template and the new `bootstrap/branch-sweep`).
  Shims can't import another ticket's directory, so the 04b–04d edge home
  fits.
- **Autofix replay goes beside its own bootstrap ticket.** It has a single
  consumer, so 06's rule (full implementation beside the ticket) applies.
- **Manual spellings become aliases over ordinary bootstrap launch**
  (`retire` precedent), not `coga recurring launch`. The latter adds an
  owner gate, control catch-up and an autofix pass, and can't carry the
  release argv.
- **`announce_autofix_ticket` dedupes** the sync+notify tail shared by
  `run_autofix` and the replay, so it has two consumers.

## Open Questions

- **Q1. Keep `--publish-and-release-local`?**
  `v1/why-is-the-code-so-big` proposes dropping it.
  - If it stays, moving it needs about nine private `branchsweep` helpers
    promoted to public names, because each also serves `sweep_branches`.
    That widens core's surface just to keep the manual operation.
  - If the owner drops it, do that in why-is-the-code-so-big (or here,
    before the move). The bootstrap ticket then has one operation, and no
    promotions are needed.
  - Default in the spec: keep it unchanged and promote the helpers.
- **Q2. Where does `discharge_owned_followups` live?**
  why-is-the-code-so-big proposes `autoclose.py`. After 04c, the autoclose
  *job* lives in `coga_edge.autoclose`, which `coga_edge.branch_sweep`
  cannot import.
  - Placing it in core `autoclose.py` would leave it with one consumer
    (the branch-sweep adapter), which the microkernel rule disallows.
  - Default in the spec: it moves to `coga_edge.branch_sweep` with its
    only caller. Confirm, or say what the second consumer would be.
- **Q3. New default aliases `branch-sweep` and `autofix-analyze`?**
  - They keep a stable spelling (`coga branch-sweep`,
    `coga autofix-analyze`).
  - The alternative is documenting
    `coga launch bootstrap/<name> -- ...` only. That costs users a longer
    spelling but adds nothing to `DEFAULT_ALIASES`.
  - Default in the spec: add both.
- **Q4. Accept the publication-timing change for the scheduled sweep?**
  - Today the clone-scoped `ticket.py` child does no state sweep.
    `discharge_owned_followups` publishes only `retires.md`, and the
    parent `coga recurring` publishes the rest at its own exit.
  - With `run_entry`, the child also runs `sweep_root` when it exits, so
    other dirty eligible state publishes a little earlier.
  - Default in the spec: accept it, for consistency with 04b–04d. The
    alternative is a non-publishing entry, which would need a new
    `run_entry` option.

## Rollout plan (not part of the PR)

After the release, follow `coga/edge-code/edge-code-upgrades.md` on this
repo.
- `coga/recurring/branch-sweep/` is a state-only carrier and resolves the
  packaged shim, so nothing local changes.
- Grep `coga/recurring` and `coga/tasks` for `coga run branch-sweep` and
  `coga run autofix-analyze`. Rewrite live, non-frozen instructions only.

---

## Blockers

- [x] [2026-11-16 22:20] [agent:claude] id=20261116T222004 Activation condition unmet: design needs v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co (PR #1245; 04b-04d also wait on it) and v1/microkernel/06-read-report-commands-as-ticket-workflows (PR #1240, stateless publication contract) merged to main first. Unblock once both merge, or tell me to design against the open PR heads instead.
  resolved: [2026-11-18 18:22] [human:nicktoper] PR #1245 (part 04) and PR #1240 (part 06 stateless publication contract) both merged to main. Owner chose to design both moves (branch-sweep and autofix-analyze replay) now against current main, accepting that the branch-sweep part may need rework once v1/why-is-the-code-so-big and 04b-04d land; implementation still waits on those.

## Coordination: branch-sweep simplification first (2026-11-17)

`v1/why-is-the-code-so-big` is the pilot that simplifies
`src/coga/branchsweep.py` (~1,730 lines, proposed target ≤ 300). Move the
branch-sweep recipe only after that ticket lands, so this migration moves the
small module instead of code that is about to be cut. Its spec also moves
`discharge_owned_followups` to `autoclose.py` and drops
`--publish-and-release-local`, which changes what this ticket would migrate.

---

## Blocker reminders

- d09c90ff76bd last_reminded: 2026-11-18 09:02
