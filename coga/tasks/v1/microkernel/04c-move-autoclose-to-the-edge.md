---
title: 'Recipe migration, part 3: move autoclose to the edge'
status: in_progress
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
step: 2 (peer-review)
agent: claude
launch_generation: 4c4aa0b8-f4c3-494b-b78e-61c99dc9a74d
---

## Description

Part 3 of the recipe migration. Move the `autoclose` job out of the 1,842-line
`src/coga/autoclose.py` into `coga_edge.autoclose` and remove its
`runner.RECIPES` entry. The packaged `recurring/autoclose-merged/ticket.py`
currently calls `runner.run_recipe(load_config(), "autoclose", [])` then
subprocesses `bump`; rewrite it to run the edge module. The `autoclose` alias
keeps launching that same job.

Done when the job runs from the edge with unchanged behavior, `autoclose`
exits 2 through `coga run`, only helpers with another production consumer
remain in core, and the checklist below holds.

### Per-symbol shared-helper audit

`autoclose.py` also holds Dev parsers and GitHub helpers. At `db39c6007`,
production importers of its symbols were `launch`, `open_pr`,
`checkout_disposal`, `step_gate`, `commands/bump`, `branchsweep`,
`branchcleanup`, `retire_worklist`, `checkouts`, `git`, `pr_assist` and the
packaged `bootstrap/retire/ticket.py`. Re-run the audit per symbol. Keep each
helper with at least one other production consumer in core (rename the module
only if what remains no longer fits its name, and update every importer).
Move everything else with the job. Record the per-symbol table on the
blackboard and in the PR.

### Behavior to preserve

Eligibility, checkout disposal, the worklist and review-thread reports. The
shim runs **autoclose then bump**; the old autoclose → global branch-sweep →
bump sequence is obsolete. Autoclose's shared checkout-disposal path does the
restricted owned-branch work (`checkout_disposal._sweep_owned_branches`); the
separate branch-sweep template owns the clone-wide sweep. Do not reintroduce
the broad cleanup.

### Surfaces to update in the same PR

The packaged `autoclose-merged` shim and runbook; skill `coga/autoclose/sweep`;
plus the shared list below.

### Acceptance

- [ ] Entry removed; `coga run autoclose` exits 2; alias still launches the job.
- [ ] Eligibility/disposal/worklist/review-thread tests pass against the edge
      module; launch/PR/bump-gate/branch-cleanup/retire suites pass unchanged.
- [ ] Per-symbol audit table recorded; nothing left in core without another
      production consumer.
- [ ] Old stock, customized and parked shims are covered by fixtures.
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

---

## Dev

branch: coga/v1-microkernel-04c-autoclose-to-edge

---

## Blockers

- [x] [2026-11-16 22:18] [agent:claude] id=20261116T221849 Prerequisite not merged: v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co (PR #1245, open, step review) must merge first. This ticket must start from main after that merge and use its run_entry report→publish→bump sequence and run_reported root resolver, which are absent from main at 58697fc1f.
  resolved: [2026-11-19 10:44] [human:nicktoper] Prerequisite merged: PR #1245 (v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co) merged 2026-11-19 as 133bb5fe; origin/main now carries runner.run_entry and runner.run_reported. Start implementation from current main.

---

## Blocker reminders

- 9fadbd39834a last_reminded: 2026-11-18 09:02

---

## Implement handoff (2026-11-19, agent: claude / claude-opus-5-5, manual megalaunch session)

A prior session committed `bb5911617` locally but never pushed or bumped.
This session rebased it onto `origin/main` `a7b57a2d6` (119 commits, incl.
sibling 04b blocker-reminders/skill-update and 04d Dream migrations) as
`0489f1562` and resolved the conflicts:

- `edge-code-upgrades.md` "Recipe-backed recurring shims" is now one section
  for all three jobs (04b's section generalized): autoclose added to the
  caller inventory, its three stock baselines (705/827/898) and blobs, the
  PR 898 branch-sweep drop note, and an autoclose hand-port passage. The
  `locate-job` / `job-fork-copy` commands now take an explicit `MODULE` (the
  autoclose template name `autoclose-merged` does not derive its module);
  04b's adoption test sets `MODULE` accordingly.
- `tests/test_recurring_shims.py`: with every period shim now an edge shim,
  the registry-shim test and `SHIMMED_TEMPLATES` had no consumer and were
  removed; `EDGE_SHIMMED_TEMPLATES` lists all three jobs.
- `coga/cli`, `coga/edge-code`, `coga-dev/codebase`, `coga-dev/microkernel`,
  `coga-dev/internals/notifications`, AGENTS.md, test_runner/test_packaging/
  test_edge_distribution: union of both sides.

What changed overall: `src/coga/autoclose.py` deleted; the job is
`src/coga_edge/autoclose.py` (`main` → `runner.run_entry`); shared `## Dev`
parsers + `gh` lookups → new `src/coga/dev_links.py`; the `retires.md`
backlog walk shared with branch-sweep → `checkout_disposal.py`; `autoclose`
left `runner.RECIPES`; packaged shim is `main([], scheduled=True)` (autoclose
then bump, no global branch sweep); private `_append_blackboard_report`
deleted.

## Per-symbol shared-helper audit (grep, production `src/` only, at 0489f1562)

| Symbol (new home) | Other production consumers | Decision |
|---|---|---|
| `dev_links.parse_pr_url` | launch, open_pr, step_gate, checkout_disposal, branchcleanup, pr_assist, bootstrap/retire/ticket.py | core |
| `dev_links.parse_branch_name` | launch, open_pr, step_gate, commands/bump, branchcleanup, retire ticket.py | core |
| `dev_links.parse_branch_names` | checkout_disposal, retire_worklist, branchsweep, checkouts, retire ticket.py | core |
| `dev_links.parse_worktree_path` | launch, open_pr, commands/bump, checkouts, checkout_disposal, branchcleanup, branchsweep, retire ticket.py | core |
| `dev_links.dev_heading_line` | checkouts | core |
| `dev_links.read_dev_blackboard` | checkout_disposal | core |
| `dev_links.GhError` | branchcleanup, branchsweep, pr_assist | core |
| `dev_links.pr_state` | branchcleanup, branchsweep | core |
| `dev_links.pr_head` | branchcleanup | core |
| `dev_links.prs_for_head` | branchcleanup, branchsweep | core |
| `dev_links.pr_view` | pr_assist | core |
| `dev_links.parse_pr_number` | used by `parse_pr_url` (`_looks_like_pr_url`) | core (dependency of shared parser) |
| `checkout_disposal.dispose_worklist_backlog` | branchsweep | core |
| `checkout_disposal.owner_held_branch` | branchsweep | core |
| `checkout_disposal.CheckoutOutcome`, `describe_checkout` | return type / renderer of `dispose_worklist_backlog` | core (part of shared interface) |
| `ReviewThread`, `ClosedTicket`, `AutocloseResult`, `pr_review_threads`, `unanswered_review_threads`, `sweep_merged`, `_try_bump_one`, `_dispose_checkouts`, report renderers, `run_autoclose`, `main` | none | edge (`coga_edge.autoclose`) |
| `_append_blackboard_report` | none | deleted (uses `blackboard.append_blackboard_report`) |

## Production code before/after (`wc -l`, base `a7b57a2d6` → head `0489f1562`)

| File | Before | After | Δ | Kind |
|---|---|---|---|---|
| core `src/coga/autoclose.py` | 1842 | 0 | −1842 | deleted (moved) |
| core `src/coga/dev_links.py` | 0 | 341 | +341 | moved shared helpers |
| core `src/coga/checkout_disposal.py` | 429 | 755 | +326 | moved shared backlog walk |
| core `runner.py` / `step_gate.py` / `workflow.py` / `branchsweep.py` | 344/115/218/1730 | 342/110/216/1729 | −10 | deleted registry entry, lazy-import workarounds |
| core importers (launch, open_pr, bump, checkouts, git, pr_assist, branchcleanup, retire_worklist) | — | — | 0 | import path only |
| edge `src/coga_edge/autoclose.py` | 0 | 1234 | +1234 | moved job |
| script `recurring/autoclose-merged/ticket.py` | 25 | 8 | −17 | deleted (shim simplification) |
| script `bootstrap/retire/ticket.py` | 423 | 423 | 0 | import path only |

Core −1185, edge +1234, scripts −17: net +32 (module headers/imports).
This is relocation, not reduction. Removed: the `autoclose` registry entry,
the shim's own bump + global branch-sweep path, the private report wrapper,
and the `step_gate`/`workflow` lazy imports that existed to avoid a cycle
through the old module. Tests/docs/fixtures counted separately (git diff).

## Rollout plan for this repo's own periods (not performed here)

This repo's `coga/recurring/autoclose-merged/` is a state-only carrier
(`ticket.md` + `retires.md`, no `ticket.py`), and the current period
`coga/tasks/recurring/autoclose-merged/` is `done` with no `ticket.py`. The
runbook inventory finds no autoclose caller. After merge and reinstall, the
next period copies the new packaged shim; re-run the inventory then. (The
inventory does find `coga/tasks/recurring/blocker-reminders/ticket.py` as an
old 04b-era stock 827 shim — that is 04b's rollout, not this ticket's.)

---

## PR

```yaml
title: Move the autoclose job to the edge
author: claude
author_evidence: >-
  Original commit bb5911617 by an earlier Claude implement session (not pushed);
  rebased, conflict-resolved and verified by this Claude (claude-opus-5-5)
  megalaunch implement session as 0489f1562691948bc8ed51bd2a8c920a1c18936d.
head: 0489f1562691948bc8ed51bd2a8c920a1c18936d
base: a7b57a2d6d4712a226cf49fae9c70b7f35ff02fc
depth: deep
rationale: >-
  Large relocation (1842-line core module split into edge job, dev_links and
  checkout_disposal) touching every Dev-parser importer, plus a merged
  shim-adoption runbook shared with 04b; no code review has run yet.
implementation: >-
  Deletes src/coga/autoclose.py. The job lives in coga_edge.autoclose whose
  main runs runner.run_entry; the packaged autoclose-merged shim calls
  main([], scheduled=True) (autoclose then bump, no global branch sweep).
  Shared Dev parsers and gh lookups move to coga.dev_links; the retires.md
  backlog walk shared with branch-sweep moves to checkout_disposal. The
  autoclose runner.RECIPES entry is removed, so coga run autoclose exits 2;
  the autoclose alias still launches the period. The edge-code upgrade runbook
  section for recipe-backed shims now covers all three moved jobs with an
  explicit MODULE variable.
deviations: >-
  Rebase onto main with 04b merged required generalizing 04b's runbook section
  (MODULE env var for locate-job/job-fork-copy) and removing the now-unused
  registry-shim test in test_recurring_shims.
limitations: >-
  Relocation, not reduction (net +32 production lines). Native Windows/macOS
  receipts are release-only and deferred. This repo's own period rollout is a
  plan on the blackboard, not performed.
files:
  AGENTS.md: Name autoclose among the edge-shim jobs.
  docs/contexts/coga-dev/codebase/SKILL.md: Source map for coga_edge/autoclose.py and dev_links.py.
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Point stale coga.autoclose references at new homes.
  docs/contexts/coga-dev/internals/branch-sweep/SKILL.md: Point stale coga.autoclose references at new homes.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Point stale coga.autoclose references at new homes.
  docs/contexts/coga-dev/internals/notifications/SKILL.md: Producer list names coga_edge/autoclose.py.
  docs/contexts/coga-dev/microkernel/SKILL.md: Record the autoclose move and per-symbol audit outcome.
  src/coga/branchcleanup.py: Import shared helpers from dev_links.
  src/coga/branchsweep.py: Import from dev_links and checkout_disposal.
  src/coga/checkout_disposal.py: Receives the shared retires.md backlog walk.
  src/coga/checkouts.py: Import shared helpers from dev_links.
  src/coga/commands/bump.py: Import shared helpers from dev_links.
  src/coga/dev_links.py: New core home of the shared Dev parsers and gh lookups.
  src/coga/git.py: Docstring reference to dev_links.
  src/coga/launch.py: Import shared helpers from dev_links.
  src/coga/open_pr.py: Import shared helpers from dev_links.
  src/coga/pr_assist.py: Import shared helpers from dev_links.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Recipe index drops autoclose.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Autoclose is a self-contained edge job.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md: Old-shim inventory, baselines, hand-port and fork for autoclose.
  src/coga/resources/templates/coga/bootstrap/retire/ticket.py: Import shared helpers from dev_links.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Stale module reference updated.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Skill describes the edge job and its sequence.
  src/coga/resources/templates/coga/bootstrap/workflows/autoclose-merged/sweep.md: Workflow text matches the edge shim.
  src/coga/resources/templates/coga/recurring/autoclose-merged/operations.md: Runbook points at the edge module and upgrade procedure.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Template contract names the edge job.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py: Shim runs coga_edge.autoclose main.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Stale autoclose reference updated.
  src/coga/retire_worklist.py: Import shared helpers from dev_links.
  src/coga/runner.py: Remove the autoclose registry entry.
  src/coga/step_gate.py: Module-level dev_links import replaces cycle-avoiding lazy import.
  src/coga/workflow.py: Module-level import replaces cycle-avoiding lazy import.
  src/coga/autoclose.py: Removed (renamed to the edge module).
  src/coga_edge/autoclose.py: The moved autoclose job with main/run_entry.
  tests/fixtures/edge-migration/README.md: Document the autoclose shim baselines.
  tests/fixtures/edge-migration/autoclose-old-705.py: Stock PR 705 shim baseline.
  tests/fixtures/edge-migration/autoclose-old-827.py: Stock PR 827 shim baseline.
  tests/fixtures/edge-migration/autoclose-old-898.py: Stock PR 898 shim baseline.
  tests/test_autoclose.py: Eligibility/report tests against the edge module.
  tests/test_autoclose_dispose.py: Disposal tests against the edge module.
  tests/test_autoclose_sweep.py: Sweep skill tests against the edge module.
  tests/test_branchsweep.py: Patch targets follow moved helpers.
  tests/test_create.py: Patch targets follow moved helpers.
  tests/test_edge_distribution.py: Forkability and documented old-shim adoption for autoclose.
  tests/test_git.py: Patch targets follow moved helpers.
  tests/test_notification_messages.py: Patch targets follow moved helpers.
  tests/test_open_pr.py: Patch targets follow moved helpers.
  tests/test_open_pr_command.py: Patch targets follow moved helpers.
  tests/test_packaging.py: Wheel ships coga_edge/autoclose.py; installed smoke patches it.
  tests/test_recurring_shims.py: Autoclose shim is an edge shim; obsolete registry-shim test removed.
  tests/test_runner.py: autoclose takes the unknown-recipe exit 2.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Peer review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 0489f1562691948bc8ed51bd2a8c920a1c18936d
    base: a7b57a2d6d4712a226cf49fae9c70b7f35ff02fc
    detail: 5186 passed, 33 skipped in 842s (Linux).
  - command: .venv/bin/python -m pytest -q -x tests/test_autoclose.py tests/test_autoclose_dispose.py tests/test_autoclose_sweep.py tests/test_recurring_shims.py tests/test_runner.py tests/test_edge_distribution.py tests/test_branchsweep.py
    status: passed
    head: 0489f1562691948bc8ed51bd2a8c920a1c18936d
    base: a7b57a2d6d4712a226cf49fae9c70b7f35ff02fc
    detail: 449 passed.
  - command: coga validate --json (disposable copy of tests/fixtures/seeded-repo)
    status: passed
    head: 0489f1562691948bc8ed51bd2a8c920a1c18936d
    base: a7b57a2d6d4712a226cf49fae9c70b7f35ff02fc
    detail: ok_count 5, issues 0.
  - command: coga run autoclose (disposable seeded fixture)
    status: passed
    head: 0489f1562691948bc8ed51bd2a8c920a1c18936d
    base: a7b57a2d6d4712a226cf49fae9c70b7f35ff02fc
    detail: "Exit 2, unknown recipe 'autoclose'."
  - command: native Windows/macOS receipts
    status: not-run
    detail: Release-only per coga-dev/testing; deferred.
```
