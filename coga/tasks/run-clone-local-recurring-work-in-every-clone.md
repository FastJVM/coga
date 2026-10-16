---
title: Run clone-local recurring work in every clone
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
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
step: 4 (review)
contexts:
- coga/recurring
- coga/recurring/scheduling
- coga/recurring/templates
- dev/checkout-cleanup
- dev/checkout-cleanup/branch-sweep
- dev/checkout-cleanup/foreign-ownership
agent: claude
---

## Description

Recurring period tickets are shared through main and serviced once per period by whichever clone sweeps first. That is right for shared state, but wrong for work on clone- or machine-local state. On 2026-10-16 this checkout had 46 local branches (34 with merged PRs) because the daily autoclose always ran from ~/Code/claude/coga; a manual coga run branch-sweep here deleted 28 local + 2 remote, and 9 in ~/Code/codex/coga. Affected jobs: branch-sweep (local refs), the disposal half of autoclose-merged (worktrees/branches; other clones' retires.md entries never discharge), and upstream-coga (reads machine-local [upstream] checkouts). Proposed: a recurring template scope field — repo (default, today's shared period ticket) vs clone (serviced per clone, last-serviced recorded in .coga/, no ticket, no commit) — and split autoclose so ticket closure stays repo-scoped while branch/worktree disposal runs per clone. Tradeoff: clone-scoped runs leave no git-visible record. Alternative considered: an opportunistic local sweep on chat/launch, rejected because a sweep took over 2 minutes of gh lookups. Related: autoclose-re-posts-another-clone-s-primary-checkou, and the cross-clone 'records checkout outside this repository' refusal in branch-sweep reports.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/1033
branch: clone-scoped-recurring

## Plan (agreed with owner 2026-10-16)
- `scope: repo | clone` template field (default repo). Clone scope requires
  `ticket.py`, rejects `delegate:`; no period task, no commit, no log ledger.
- Per-clone ledger + report under the primary checkout's `.coga/recurring/`
  (resolved via git common dir so temp control worktrees record against the
  real clone). Runner sets `COGA_RECURRING_SCOPE=clone`, no `COGA_TASK_SLUG`.
- Runs after shared launches in `run_recurring_scan`; same owner/control/
  inactivity gates; outcomes go to the RunRecord.
- `--all`: duplicate-remote clones get a clone-only child sweep.
- Flip `branch-sweep` (daily) and `upstream-coga` to `scope: clone`; drop
  branch-sweep from `autoclose-merged/ticket.py`.
- Owner decision: per-clone `retires.md` worklist discharge is a follow-up
  ticket (needs its own publish design), not this PR.

## Implementation handoff (implement, 2026-10-16)

Implemented per the agreed plan.
- `src/coga/recurring_clone.py` (new): `clone_state_dir` keeps the per-clone
  ledger and log at `<primary checkout coga dir>/.coga/recurring-clone/`. It
  finds the primary through git's common dir, so a temp control worktree
  records for the owning clone. Also holds `read_clone_ledger`,
  `record_clone_period` and `run_clone_template`. The runner calls
  `ticket.py` with `COGA_RECURRING_SCOPE/TEMPLATE/PERIOD`, the template's
  `secrets`, and no `COGA_TASK_*`. Output goes to `<name>.log`. Only exit 0
  advances the ledger.
- `src/coga/recurring.py`:
  - `Template.load` validates `scope` (repo|clone). Clone scope requires
    `ticket.py` and rejects `delegate`/`state_keys`/`workflow`.
  - `Template.scope`/`clone_scoped` properties.
  - `_declares_clone_scope` keeps clone templates out of `scan_due` and
    `_template_period_targets`.
  - `scan_clone_due` and `CloneScan`/`CloneDue` are new.
  - `list_templates` reports clone rows from this clone's ledger.
  - `create_named` refuses clone templates.
- `src/coga/recurring_runner.py`:
  - `_run_clone_scoped` runs after the shared launches, on both the no-due
    and launch paths, and records `TaskOutcome`s for autofix.
  - New `clone_only` mode, threaded through the relay argv,
    `_service_from_control_worktree` and `_run_repo_recurring`, as the recipe
    flag `--clone-only`.
  - `run_recurring_all_repos` now gives duplicate-remote checkouts a
    clone-only child instead of skipping them.
  - `run_recurring_named` runs a clone template now, ignoring its ledger.
- `commands/recurring.py`: the list table shows `clone · due in this clone` or
  `clone · ran here <ts>`.
- Templates:
  - `branch-sweep` is `scope: clone`, daily, `run_when_inactive: true`, with
    no workflow.
  - `upstream-coga` (local-only) is `scope: clone`; its unused
    `workflows/upstream-coga/run.md` is deleted.
  - `autoclose-merged/ticket.py` no longer runs branch-sweep.
  - The packaged `workflows/branch-sweep/sweep.md` is kept on purpose:
    downstream repos' repo-scoped copies of the old template still name it.
- Docs (owner `coga/recurring/scheduling`, new section "Repo scope and clone
  scope"), plus templates, recurring overview, codebase map, branch-sweep,
  terminal-owners, lifecycle, the autoclose and branch-sweep skills, and the
  autoclose workflow, all with their twins.

### Incident during implement: template changes reached main early
Running `coga create` (for the follow-up ticket) from the feature branch let
the exit sweep adopt the committed `coga/recurring/` changes onto control
(`0591ae8bd Sync coga state`). That is `git._candidates` committed-path
adoption over `_routine_state_areas`, working as designed. So main held the
new templates before the code that understands `scope:`. Owner chose to fix
forward rather than revert, because any later coga command on this branch
would adopt them again. Commit `Keep clone shims working under pre-clone-scope
Coga` makes the branch-sweep and upstream-coga shims bump `COGA_TASK_SLUG`
when set: old code runs them as one-step `direct/body` periods. Otherwise they
return the exit code. The handoff bump will publish the compatible versions.
Until this PR merges, main runs branch-sweep as a daily shared period and
autoclose without the branch pass. Expect the same adoption for anyone who
edits recurring templates on a branch; worth a line in `dev/checkouts`
(not done here).

### Notes for review
- The live `coga/tasks/recurring/upstream-coga` (done) period task will no
  longer be replaced by the shared scan; Dream's retro pass reaps it.
- First firing is retroactive per clone: each clone's first sweep runs both
  clone templates once.
- `upstream-coga`'s old-code bump path has no direct test; it mirrors the
  branch-sweep shim, which is covered by
  `test_clone_shim_bumps_only_when_run_as_a_period_task`.
- Follow-up filed (owner decision): `discharge-retires-md-entries-in-the-clone-that-own`.

## Peer review

Independent direct Codex review **completed** on 2026-10-16 for head
`c1d8227d7d05dd91e59c2b5f9cd66682960e6379` against base
`0246eb492a3f405108ccfb310fee37f055cbd9b5`. Claude implemented per the prior receipt;
this fresh session reviewed directly without a child reviewer CLI. No must-fix
findings and no product-code edits. Rebased on current main; final rebase added
only an unrelated ticket and log line, which were also inspected. Deep review
remains recommended because this adds a recurring scheduling mode.

Real PTY: `recurring list` at 100x30 and 160x35 showed readable clone due labels;
the narrower table ellipsizes names/schedules. A disposable Python probe swept
two independent workspaces twice, asserting one clone-job invocation each and
no tasks/ or log.md. Initial probe refused inherited Slack config before running;
rerun with SLACK_WEBHOOK_URL unset passed. No production cleanup was invoked.
Per-clone retires.md discharge remains deferred as agreed.

Repository validation has two missing-context errors on the marketing demo
ticket, also present on main. Owner confirmed marketing/plan and
marketing/positioning were removed by design; stale references left separately.
Final suite: 3696 passed, 5 skipped in 302.06s on Python 3.12.12.
Task validation passes; exact check receipts are below. Branch committed and
pushed; latest fetch still equals the reviewed base. The launcher owns returning
the checkout to main (COGA_LAUNCH_RETURNS_CHECKOUT=1).

## PR

```yaml
title: Run clone-local recurring work in every clone
author: claude
author_evidence: Attended implement session run by Claude Opus 5.5 (claude-opus-5-5) under coga launch;
  no agent override.
head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
depth: deep
rationale: New recurring scheduling mode and multi-clone dispatch merit deep review. Independent direct
  review completed without must-fix findings. Repository validation reports stale references to intentionally
  removed marketing contexts.
implementation: 'Adds `scope: clone` templates that run their ticket.py per clone with a clone-local ledger
  under the primary checkout''s .coga/, wires them into bare, named, clone-only and --all sweeps, flips
  branch-sweep (daily) and upstream-coga to clone scope, and drops the branch pass from autoclose-merged.'
deviations: Shims for branch-sweep and upstream-coga also bump when COGA_TASK_SLUG is set, for old-code
  compatibility after the state sweep adopted the templates onto main early (see handoff). Per-clone retires.md
  discharge deferred to a follow-up ticket by owner decision.
limitations: Clone runs leave no git-visible scheduling record (accepted). Per-clone retires.md discharge
  remains a follow-up. Production destructive sweeps were not run; cleanup is exercised in disposable-repository
  tests. Repository validation has two stale marketing context references already on main; owner confirms
  intentional context removal. Python 3.11 was not tested; suite interpreter is 3.12.12.
files:
  coga/skills/coga/autoclose/sweep/SKILL.md: Branch pass now belongs to the clone-scoped branch sweep.
  coga/skills/coga/branch-sweep/sweep/SKILL.md: Describe clone scope; drop the single-clone caveat.
  coga/workflows/autoclose-merged/sweep.md: Autoclose no longer runs branch-sweep.
  coga/workflows/upstream-coga/run.md: Deleted; clone-scoped templates take no workflow.
  docs/contexts/coga/codebase/SKILL.md: Name recurring_clone.py in the source map.
  docs/contexts/coga/lifecycle/SKILL.md: Branch cleanup is each clone's daily sweep.
  docs/contexts/coga/recurring/SKILL.md: Overview of scope and the new module.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Owner of the repo-vs-clone scope contract and --all
    clone-only children.
  docs/contexts/coga/recurring/templates/SKILL.md: Document the scope field and inactivity exemptions.
  docs/contexts/dev/checkout-cleanup/branch-sweep/SKILL.md: Branch sweep is clone-scoped and daily.
  docs/contexts/dev/checkout-cleanup/terminal-owners/SKILL.md: Cleanup happens in the clone holding the
    branch.
  src/coga/commands/recurring.py: Show clone-scoped rows in `coga recurring list`.
  src/coga/recurring.py: Scope validation, clone scan, shared-scan exclusion, list rows.
  src/coga/recurring_clone.py: Clone-local ledger, log and script runner.
  src/coga/recurring_runner.py: Run clone templates in sweeps, named launches, --clone-only and --all
    duplicates.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/branch-sweep/SKILL.md: Packaged
    twin.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/terminal-owners/SKILL.md: Packaged
    twin.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/sweep/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.md: Packaged twin; closure only.
  src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py: Packaged twin; no branch pass.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.md: Packaged twin; scope clone, daily.
  src/coga/resources/templates/coga/recurring/branch-sweep/ticket.py: Packaged twin of the compatible
    clone shim.
  src/coga/resources/templates/coga/workflows/autoclose-merged/sweep.md: Packaged twin.
  tests/test_branchsweep.py: Daily branch pass is exercised through the clone shim.
  tests/test_recurring.py: --all duplicates get clone-only children; branch-sweep is inactivity-exempt.
  tests/test_recurring_clone.py: New coverage for validation, ledger, failure retry, inactivity, named
    and clone-only runs, primary resolution.
  tests/test_recurring_shims.py: Clone shim bump/no-bump matrix; autoclose shim no longer sweeps branches.
  tests/test_upstream_coga.py: Live job is clone-scoped with no workflow.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
  base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
  detail: Direct Codex review completed in this fresh peer session. Claude implementation identity comes
    from implement handoff. Reviewed rebased diff, scope validation, runner wiring and admission, ledger
    placement, packaged twins, shims, and tests. No must-fix findings; no child reviewer CLI. Final rebase
    added only an unrelated ticket and log line; reviewed those changes too.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
  base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
  detail: 3696 passed, 5 skipped in 302.06s; Python 3.12.12. Final rebased head.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: c63c4c98b119a1b8c2078f8263a8640ae4589978
  base: 37f9994e8fabf5bf24d35bcfa6415a94b4d0683b
  detail: 3696 passed, 5 skipped in 373.77s; Python 3.12.12. Historical receipt before bookkeeping-only
    rebase.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task run-clone-local-recurring-work-in-every-clone
    --json
  status: passed
  head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
  base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
  detail: 1 OK, no issues.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
  status: failed
  head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
  base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
  detail: '267 OK, 44 warnings, 2 broken-context errors: marketing/plan and marketing/positioning on marketing/demo-hackability-ask-claude-to-add-a-command-live.
    Identical references and missing paths confirmed on main; owner confirms intentional context removal.
    Unrelated stale references left separately.'
- command: git diff --check
  status: passed
  head: c1d8227d7d05dd91e59c2b5f9cd66682960e6379
  base: 0246eb492a3f405108ccfb310fee37f055cbd9b5
  detail: No whitespace errors.
- command: stty cols 100 rows 30; PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli recurring
    list
  status: passed
  head: c63c4c98b119a1b8c2078f8263a8640ae4589978
  base: 37f9994e8fabf5bf24d35bcfa6415a94b4d0683b
  detail: Real PTY. Clone due labels readable; existing table ellipsizes names and schedules.
- command: stty cols 160 rows 35; PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli recurring
    list
  status: passed
  head: c63c4c98b119a1b8c2078f8263a8640ae4589978
  base: 37f9994e8fabf5bf24d35bcfa6415a94b4d0683b
  detail: Real PTY. Full template names, schedules and clone due labels readable.
```
