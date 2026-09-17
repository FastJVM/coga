---
title: 'Define the recipe reporting contract: report durability and failure surface'
status: in_progress
owner: nicktoper
agent: claude
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
step: 3 (open-pr)
---

## Description

Two halves of one missing contract for deterministic `ticket.py` recipes,
which are five of the seven shipped recurring templates.

**1. Nobody records that a recipe's report blackboard is per-run.** Coga states
the "period blackboards are scratch" rule twice for *agents* —
`coga/contexts/coga/period-task/SKILL.md` ("nothing in your task directory
survives to the next firing") and the recurring context's Gotchas — but nowhere
for *recipe code*, which reaches the same file through `COGA_TASK_BLACKBOARD` /
`coga.task_env.blackboard_from_env`. The knowledge that does exist covers only
containment: `coga/contexts/coga/codebase/SKILL.md` says the helper "refuses a
blackboard outside the `tasks/` tree of the root the recipe is operating on" —
i.e. *which repo*, never *which task and for how long*. Four shipped recipes
append reports through it (`src/coga/autoclose.py`, `src/coga/dream_validate_drift.py`,
`src/coga/dream_cleanup_orphan_markers.py`, `src/coga/skill_update.py`), and
under a recurring template every one resolves to
`coga/tasks/recurring/<name>/ticket.md`, which the next firing deletes. Three
are correct because their durable output is a PR or a run summary; autoclose's
retire follow-up was not, and `render_retire_report`'s docstring claiming the
target was "a long-lived recurring task's blackboard" is recorded as exactly why
that bug survived review. `digest-can-clobber-recurring-last-serviced-period`
is the same class from another angle.

**2. A failing recipe's detail reaches no durable surface, and nothing owns the
rule.** It is stated only in a source docstring: `run_skill_update_recipe`
(`src/coga/skill_update.py`) documents that both non-zero exits leave a
`## Skill Update` section on the blackboard "rather than to stderr alone, which
the recurring sweep discards", then names the debt itself — "the first instance
of a property the other recipes still lack — `dream_validate_drift`,
`dream_cleanup_orphan_markers`, `branchsweep`, `autoclose`, `blocker_reminders`
and `recurring_autofix` all exit non-zero to stderr alone. It belongs in the
recipe layer rather than here; do not paste a seventh copy, generalize it
instead." Nothing in `coga/contexts/coga/recurring/SKILL.md` carries this, and
no ticket owns the generalization. Two independently filed tickets show the
cost: `autofix/stop-the-digest-spool-drain-leaking-a-blank-line-e` ("The job
exits 0 and posts correctly, so nothing in the sweep reports it — this is a
silent, monotonic growth leak in a git-tracked state file") and
`recurring-sweep-wedges-on-the-ticket-py-it-copies` ("Nothing increments a
problem counter, so the sweep still exits `problems: 0`").

## Context

Part 1 is a paragraph for recipe authors, in the recurring or codebase context
(with its enforced twin): `blackboard_from_env` is a per-run reporting surface,
not durable storage; anything that must outlive the period goes to the
template's own blackboard, a template sibling file (the `recurring/digest/spool.md`
precedent, and the `retires.md` proposed by `persist-autoclose-retire-follow-ups`),
or the repo-global `coga/log.md`.

Part 2 is the generalization the docstring asks for — the recipe layer owning
"a failing recipe writes its detail to a durable surface" once, rather than a
seventh pasted copy — plus stating that contract in the recurring context.

Related and already routed this Dream run: a proposal PR corrects the recurring
context's claim that the blackboard is where every `ticket.py` phase writes what
it found (four of five shipped templates write nothing). Check it before editing
the same section.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: recipe-reporting-contract
worktree: /home/n/Code/claude/coga-recipe-reporting-contract

Separate-checkout layout: the primary checkout runs the megalaunch queue and
stays on `main`.

## Plan

- **Part 1 (report durability)** is a context paragraph, not code. Owner: the
  recurring context's "deterministic half" constraint bullet (the passage
  written for `ticket.py` authors), with its packaged twin. The codebase
  context gets one sentence pointing there from the `blackboard_from_env`
  containment bullet, since that bullet is where a code reader lands.
- **Part 2 (failure surface)** goes in `runner.run_recipe`, the one seam every
  registered recipe crosses: it tees `sys.stderr` while the recipe runs and,
  on a non-zero return or an escaping exception, appends a `## Recipe Failure`
  section (recipe, exit, task, stderr tail / traceback) to the period
  blackboard resolved by `blackboard_from_env(cfg.repo_root)`. No blackboard
  → nothing extra (stderr already reaches the console). A write failure never
  replaces the recipe's own exit code.
- The four shipped `ticket.py` shims (live + packaged twins) switch from
  importing `run_<x>_recipe` directly to `run_recipe(load_config(), "<name>", [])`
  so the deterministic firing crosses the layer; `tests/test_recurring_shims.py`
  is updated to pin that shape, and the four skill docs that say the shim
  "calls `run_x_recipe` directly" are corrected (with twins).
- `run_skill_update_recipe`'s docstring stops naming the debt and instead
  names the layer; its own exit-2 `## Skill Update` report stays because it
  carries what stderr cannot (the PR-not-confirmed state).

## Findings

- PR #774 (merged) already corrected the recurring context's "every ticket.py
  writes to the blackboard" claim: the analyst-channel paragraph now says the
  record "is populated only by runs that choose to write to it". PR #817
  (open) edits the period-task context only and says "Nothing in the
  ticket.py contract asks a recipe to write a run report there" — still true
  after this change for *successful* runs; the new obligation is on the
  layer, for failures, and the wording here is kept consistent with that.
- PR #820 (open, `persist-autoclose-retire-follow-ups`) adds a paragraph to
  the recurring context's "Last-run state" section about `retires.md`. Part 1
  is placed in the constraint bullet instead, so the two do not collide, and
  cites `retires.md` as that ticket's proposal.
- The failure surface chain is: period blackboard → sweep run record
  (`recurring_autofix.blackboard_for_ref`) → `.coga/recurring-runs/<stamp>.md`
  and, when ticketed, the committed `run-log.md`. A failed `ticket.py` leaves
  the period `in_progress`, so the section also survives on the ticket until
  the retry succeeds and Dream reaps it.
- The ticket counts "five of seven" `ticket.py` templates; on current `main`
  it is four of six (`digest` was removed). Not material to the change.

## Implement — done

Commit `4ca44bea` on `recipe-reporting-contract` (rebased on `origin/main`,
already current). Not pushed; no PR yet.

What changed:

- `src/coga/runner.py` — `run_recipe` tees `sys.stderr` (`_StderrTail`, a
  transparent proxy so `isatty`/`fileno` still describe the console) and on a
  non-zero return or an escaping `Exception`/`SystemExit`/`typer.Exit` (zero
  codes are returns, not failures) appends `## Recipe Failure` via
  `append_blackboard_report` to `blackboard_from_env(cfg.repo_root)`.
  `render_failure_section` bounds the body to 4000 chars (the run record's
  per-task budget) and strips ANSI. A write failure warns on the real stderr
  and never outranks the recipe's exit.
- Four shims × two copies now `run_recipe(load_config(), "<name>", [])`;
  four skill docs (with twins) say so; `tests/test_recurring_shims.py` and
  `tests/test_skill_update.py::test_skill_update_ships_as_a_recurring_template`
  pin the new shape.
- Recurring context: new sixth constraint bullet "The recipe reporting
  contract" (Part 1 + Part 2), plus one sentence in the dispatch bullet
  saying what "the failure is recorded" records. Codebase context: the
  `runner.py` source-layout line and the `blackboard_from_env` containment
  bullet point at the contract. All twins byte-identical.
- `run_skill_update_recipe` docstring: names the layer instead of the debt;
  its own exit-2 report stays (carries the PR-not-confirmed state).

Decisions:

- Layer = `run_recipe`, not `launch_script.run_script_phase`. Capturing the
  child's fd 2 there would cover non-recipe `ticket.py` files too, but the
  child inherits the console and the docstring names the recipe layer; the
  context tells a non-recipe `ticket.py` author to route through `run_recipe`
  or write their own reason.
- Universal, blackboard-gated: `open-pr`/`delete-task`/`recurring-scan` get
  the same property when run inside a task session. Judged desirable (a
  failed `coga open-pr` leaves its reason on the ticket) and harmless
  otherwise (no blackboard → nothing).
- Skill-update keeps a one-line duplication on exit 2 (its report + the
  layer's stderr tail). Accepted over a heuristic "skip if the recipe already
  wrote" that autoclose's unrelated retire report would defeat.
- Tests call recipe functions directly and are unaffected; only
  `run_recipe` callers see the section.

Verification: `PYTHONPATH=<worktree>/src .venv/bin/python -m pytest`
→ 2569 passed (full suite; run in two invocations after fixing the one
template-shape assertion). `git diff --check` clean. `coga validate --json`
in the worktree matches main's standing baseline plus `missing-user` (no
`coga.local.toml` there). Note for the next agent: a relative `PYTHONPATH`
makes subprocess `ticket.py` children import the editable install on `main`
instead of the worktree — use the absolute path.

Adjacent observations (not fixed here):

- PR #817 (period-task context) says "Nothing in the `ticket.py` contract
  asks a recipe to write a run report there" — still true for success; if
  it lands after this, no edit needed. PR #820 adds a `retires.md` paragraph
  under "Last-run state"; the new bullet cites that ticket by slug and stays
  correct either way, though "gives autoclose a `retires.md`" reads as
  present tense once #820 merges — fine.
- `recurring_runner._run_delegated_task`'s docstring still references
  `_run_recipe_task`, which no longer exists.
- `tests/test_recurring_shims.py` module docstring says "five recurring
  templates"; there are four shims.

## Peer review

`codex review --base main` **returned** from the recorded feature checkout.
It reported one P2: failure reporting used the invoking config's root after
`validate-drift` / `skill-update --cwd` selected another repo, bypassing the
recipe's blackboard-containment refusal. Fixed by sharing the recipes' existing
argument parsers with report-target resolution (including `--cwd=`, abbreviated
options, and unknown targets). Cleanup-orphan-markers retains its own root
resolver. The append also takes the target root's publication barrier. The
registry and recipe call/return contracts are unchanged.

Additional reproduced gaps fixed: an own-line blackboard fence in captured
stderr became a second structural fence; a 4000-character detail lost the
report's header in the run-record tail; a path-resolution exception could
replace the original recipe failure. Diagnostics are now indented, the whole
section fits the run-record budget, and resolution/render/write failures are
inside the best-effort guard. Added regression coverage for all three and for
cross-root refusal/acceptance. Updated the recurring owner and architecture
pointer, including their packaged twins; the analyst-channel paragraph now
distinguishes optional successful reports from layer-owned failure reports.

Verification:

- `PYTHONPATH=/home/n/Code/claude/coga-recipe-reporting-contract/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -o cache_dir=/tmp/coga-recipe-peer-pytest-cache` — **2586 passed** in 184.18s, after rebase and all fixes.
- `PYTHONPATH=/home/n/Code/claude/coga-recipe-reporting-contract/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_runner.py tests/test_recurring_shims.py tests/test_skill_update.py tests/test_dream_validate_drift.py tests/test_packaging.py -q -o cache_dir=/tmp/coga-recipe-peer-pytest-cache` — 113 passed.
- Real terminal, after fixes: `PYTHONPATH=/home/n/Code/claude/coga-recipe-reporting-contract/src /home/n/Code/claude/coga/.venv/bin/python /tmp/coga-recipe-peer-terminal.py`, driven through a PTY at 80x24 and 40x12. Observed red failure text and child stderr at both sizes; checked `isatty`, `fileno`, encoding, exit 2, an ANSI-free blackboard report, and restoration of stderr. Only disposable fixture tickets were used.
- `PYTHONPATH=/home/n/Code/claude/coga-recipe-reporting-contract/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --task define-the-recipe-reporting-contract-report-durabi --json` from primary — no issues.
- `git diff --check` — clean.

Ran `git fetch origin main` followed by `git rebase FETCH_HEAD` successfully
before applying the fixes. Feature commits: `86a66ede` (implementation, rebased
from the earlier `4ca44bea`) and `f845e44f` (`peer-review: preserve failure report
containment and ticket structure`). No unresolved review findings. The recorded
feature branch is committed and ready for the mechanical open-pr step.

## PR

Registered recipes now record nonzero exits and exceptions on the task
blackboard so recurring run records retain the failure reason. All four shipped
recurring shims use the shared runner. Reporting preserves console output and
the original failure, respects the recipe's target repository, keeps diagnostic
text from becoming ticket structure, and fits the complete report within the
run-record budget.

The recurring context defines period reports as temporary and names the durable
homes for cross-run state. Context pointers, recipe skills, and packaged twins
are updated with regression coverage for the reporting contract.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-recipe-reporting-contract/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -o cache_dir=/tmp/coga-recipe-peer-pytest-cache` — 2586 passed; real-PTY smoke at 80x24 and 40x12 passed; task validation and `git diff --check` clean.
