---
title: Branch sweep strands squash-merged branches whose tip moved
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/principles
- coga/architecture
- coga/codebase
- coga/recurring
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (self-qa)
---

## Description

`branch-sweep` deletes almost nothing. A dry run today (delete calls stubbed,
every other gate live) over 71 local branches: **3 deleted, 9 worktree-pinned,
54 skipped.** Roughly 37 of those 54 are branches whose PR demonstrably merged
weeks ago. They will never age out — the gate that rejects them cannot become
true with time.

### The mechanism

`branchcleanup.delete_local_branch` has two doors:

1. `local_branch_landed(root, branch, landed_ref)` — tip reachable from the
   control branch → `git branch -d`. This repo squash-merges, so a merged
   branch tip is almost never an ancestor of `main`; the door is effectively
   closed for normal work.
2. otherwise, force-delete only when `branchsweep.branch_merged_without_open_pr`
   finds a merged PR whose `headRefOid` **equals the current local tip**.

Door 2 is defeated by Coga itself. Coga's state sync keeps committing to a
feature branch that is still checked out after its PR is pushed and merged —
`Sync coga state`, `Log: bootstrap/orient`, `Ticket: <slug> — done`. The local
tip walks past the merged head, `headRefOid == tip` is false, and the branch is
reported as *"has unmerged work and no merged PR — left in place"* forever.

Worked example: `megalaunch-dir-scope-no-in-progress`, PR #540 merged, local tip
~100 commits past the merged head, every one of them Coga bookkeeping.

A second shape hits the `dream/*` batch: the merged `headRefOid` is not in the
local object graph at all (`git rev-list <head>..<branch>` → *invalid revision
range*). The branch was rebased or force-pushed before merge and the local ref
is a dead lineage. Same outcome, different cause — a fix must handle both.

### Second defect: the live-ticket guard is blind to prose links

`branchsweep._live_ticket_branches` protects a branch only when a non-terminal
ticket records it under a `## Dev` `branch:` line — it calls
`autoclose.parse_branch_name` on the blackboard and nothing else. A ticket that
names its branch anywhere else is invisible to that guard.

Live example found while clearing the backlog: the draft ticket
`persist-autoclose-retire-follow-ups` owns the branch
`autoclose-retires-durable-home`, which carries two unpushed commits
(`fa3880b1`, `c5cb1548`) touching `src/coga/autoclose.py`, the autoclose sweep
skill and its tests. The ticket names that branch three times —
`ticket.md:89`, `handoff-manifest.md:6` ("Coga source branch:
`autoclose-retires-durable-home`"), and `multiply-ticket-history.md:215`
("commit `fa3880b1`, **not pushed**") — but has **no `## Dev` section at all**,
so the guard returns nothing for it.

Today only the "no merged PR" rule keeps that branch alive. The moment a PR for
that head merges while follow-up work sits unpushed on the same ref, the sweep
force-deletes a branch a live ticket still depends on. Widening the merged gate
(above) makes this strictly more likely to fire, so the two changes must ship
together.

Options, in rough order of preference:

1. Scan the whole task directory, not just the `## Dev` blackboard region, for
   branch names — cheap, no authoring burden, some false positives (a ticket
   that merely mentions a branch pins it). False positives are the safe
   direction here.
2. Keep the `## Dev` parse as the contract and make it enforceable: have
   `coga validate` flag a non-terminal ticket that references a local branch
   name without recording it under `## Dev`.
3. Require `## Dev` and treat its absence on a non-terminal ticket as an error.
   Cleanest contract, largest migration.

Whichever is chosen, add a regression test: a non-terminal ticket that names a
branch outside `## Dev`, plus a merged PR at that branch's exact tip, must not
delete the branch.

### Proposed shape (first defect)

Widen door 2 without loosening what it protects. Treat a branch as landed when
**both** hold:

- the merged PR's `headRefOid` is an ancestor of the local tip, and
- `git diff <control>...<branch>` touches nothing outside `coga/tasks/**` and
  `coga/log.md`.

That is the same carve-out `validate --check-github` already makes for
generated state divergence (see `github_preflight.py`), so the rule is not new
policy — it is an existing rule applied at a second site. A branch carrying
real source changes plus sync commits still fails the second clause and stays
skipped, which is correct.

The dead-lineage shape fails the ancestor clause. Decide explicitly whether the
path-scope clause alone is enough there, or whether those need a separate
signal; do not silently widen to "merged PR exists, delete" — that force-deletes
work that was never pushed.

### Also in scope

`run_branch_sweep_recipe` writes its report to stdout only, never to
`COGA_TASK_BLACKBOARD`. The 2026-09-08 period task landed with an empty
blackboard, so there is no durable record of what any sweep decided. Write the
report to the blackboard when the variable is set, stdout otherwise — the
contract the other recipes already follow. Coordinate with
`define-the-recipe-reporting-contract-report-durabi...` rather than duplicating
it; if that ticket owns the change, say so here and drop it from this one.

### Out of scope

- Worktree hygiene. 21 linked worktrees pin their branches and `branch-sweep`
  refuses those on purpose; removing worktrees is `coga retire`'s job. Tickets
  that ended without retire leak both. Separate ticket.
- The 6 no-PR-ever branches and 1 closed-unmerged branch. The sweep requires a
  merged PR by design; these need a human.

### Done when

- A branch whose PR squash-merged and whose only later commits are Coga state
  commits is deleted by the sweep.
- A branch with real unmerged source changes is still skipped, with the
  existing message.
- A worktree-pinned branch is still preserved and reported
  `skipped-worktree-pinned`.
- Tests in `tests/test_branchsweep.py` cover: tip-moved-by-sync-commits,
  tip-moved-by-real-changes, and merged-head-absent-from-local-graph.
- The sweep's report reaches the period task blackboard.
- A non-terminal ticket that names its branch outside `## Dev` still pins that
  branch, proven by a test with a merged PR at the branch's exact tip.

## Context

Reproduce the dry run before changing anything — it is the measurement this
ticket is judged against:

```python
import coga.branchsweep as bs
from coga.config import load_config
from coga import git

cfg = load_config(); root = git._toplevel(cfg.repo_root)
deleted = []
def fake_local(root, branch, pr_merged, echo, result, *, landed_ref="HEAD", expected_tip=None):
    if bs.local_branch_landed(root, branch, landed_ref) or pr_merged:
        result.local_deleted = True; deleted.append(branch)
def fake_remote(cfg, root, branch, merged, echo, result):
    result.remote_deleted = True
bs.delete_local_branch = fake_local; bs.delete_remote_branch = fake_remote
res = bs.sweep_branches(cfg, root, echo=lambda m: None)
print(len(deleted), len(res.worktree_pinned), len(res.skipped))
```

Baseline on 2026-09-09: `3 9 54`.

Relevant source:

- `src/coga/branchsweep.py` — `sweep_branches`, `branch_merged_without_open_pr`,
  `_merged_for_tip`, `run_branch_sweep_recipe`
- `src/coga/branchcleanup.py` — `delete_local_branch` (:721),
  `local_branch_landed` (:827), `_is_ancestor` (:864)
- `src/coga/github_preflight.py` — the existing generated-state carve-out to reuse
- `coga/recurring/branch-sweep/` — template, `ticket.py`, and the skill whose
  documented contract must move with the behavior

Note the template ticket body and the `coga/branch-sweep/sweep` skill both
describe the current "merged PR for that exact tip" rule in prose. Both need
updating in the same PR, and the packaged twin under
`src/coga/resources/templates/coga/` must stay byte-identical.

<!-- coga:blackboard -->
## Dev
branch: branch-sweep-landed
worktree: /home/n/Code/claude/coga-branch-sweep-landed

## Baseline (2026-09-15, dry run with deletes stubbed)

`2 14 18` — deleted / worktree-pinned / skipped. The backlog shrank since the
ticket's 2026-09-09 `3 9 54` measurement, and its shape changed: **zero**
"tip moved by sync commits" branches remain today, and 15 of the 18 skipped
are the ticket's "dead lineage" shape (merged `headRefOid` absent locally).

Probing those 15 (`git fetch origin refs/pull/<n>/head`, then ancestry):
in 14 of 15 the local tip is an **ancestor of the merged head** — the branch
was pushed, one more commit (review fix) was pushed from another checkout
(the retired worktree), then merged; retire deleted the remote branch, so the
head never reached this checkout. Not a rebase or force-push: the local ref
simply lags. The 15th (`cite-symbols-rule`) has both sides: 15 local-only
commits (all `Ticket:`/`Log:`/`Merge main state into` bookkeeping) and one
head-only source commit.

## Design

One rule replaces the exact-tip gate (`merged_pr_verdict`): a merged PR for
the head name, with no open PR, vouches for the local ref iff every commit in
`git rev-list <tip> ^<merged head> ^<control>` touches only Coga state paths
(`github_preflight.is_coga_state_path`, the `validate --check-github`
carve-out, now exported). Paths come from one
`git diff-tree --stdin --cc --name-only`: a clean merge lists nothing, an evil
merge lists the file it resolved, non-merge commits list their diff (verified
in a scratch repo). Vacuously true for the exact tip and for a lagging tip;
true for sync-only later commits including clean `Merge main state into X`;
false for any real source commit, with the offending paths in the note.

- The ticket's literal `git diff <control>...<branch>` clause would reject
  the exact case it targets whenever no control merge followed the PR — the
  PR's own source diff sits between the fork point and the merged head — and
  the plain `diff <head> <tip>` tree diff rejects the shape where Coga merged
  control back into the branch after the squash (tree gains all of main's
  later changes). The per-commit rule is the one that is right for both.
- Dead lineage: the "separate signal" is fetching `refs/pull/<n>/head`
  (objects only, `--no-write-fetch-head`, no ref written). GitHub keeps that
  ref after branch deletion. A genuinely diverged ref with local source
  commits still fails the rule — the ticket's "merged PR exists, delete" is
  not what ships. Unfetchable head → skipped with a note naming the PR.
- Remote ref: exact-tip only, unchanged. Its objects are usually not local
  and ancestry never authorized remote deletes. A remote half that outlived
  a widened local delete is reported "skipping remote (no merged PR)" and
  stays for a human; none of today's 15 candidates has a remote half.
- Live-ticket guard: option 1. `_live_ticket_branches(cfg, candidates)`
  scans every file of every non-terminal task (ticket above and below the
  fence, all attachments) for any local/remote branch name as a whole token
  (`(?<![\w./-])name(?![\w./-])`). A ticket whose frontmatter cannot be
  read is treated as live (conservative). `## Dev` parse dropped from the
  sweep — the scan subsumes it.
- Report: `render_sweep_report` writes `## Branch Sweep` (counts, outcome
  lists, every decision including the cleanup helpers' notes, now folded into
  `BranchSweepResult.notes`) to `COGA_TASK_BLACKBOARD` via the shared
  `blackboard.append_blackboard_report`, stdout otherwise; written before the
  exit code so a failed sweep is recorded. The reporting-contract draft
  (`define-the-recipe-reporting-contract-report-durabi`) owns the *general*
  rule (per-run durability paragraph, failure-surface generalization); this
  ticket only makes branch-sweep follow the pattern autoclose/skill-update
  already use, so nothing was dropped from here.
- Also: `delete_local_branch`'s refusal now reads "no merged PR vouching for
  it", since a merged PR may exist and still refuse; the sweep notes the
  verdict's reason separately in that case. `coga_root_prefix` /
  `is_coga_state_path` un-underscored in `github_preflight.py` (2 consumers).
- Sweep now fails loud (`state_root_unavailable`) if `git rev-parse
  --show-prefix` cannot locate the Coga root — same posture as the worktree
  probe, rather than silently narrowing back to exact-tip.

## Result (same dry run, new gate)

`12 6 2`. All 11 `dream/*-1788913097` plus `sweep-republishes-stranded-claim-release`
delete; `fix/watchdog-pauses` and `resolve-step-one-assignee` now report
`skipped-worktree-pinned` (they are held by worktrees; before, they were
skipped with no landed signal). Skipped: `branch-sweep-landed` (this branch,
no PR yet) and `guard-reauthor-in-progress` (no PR ever — by design).
`autoclose-retires-durable-home` pins via its draft ticket's prose, as the
ticket required. The mention scan pins 17 branches in total; the extra pins
come from the `in_progress` `recurring/autoclose-merged` period blackboard
(its retire follow-up report names the branches — deferring to `coga retire`
is the intended outcome, and the pin lapses when that period task closes)
and one v2 draft that mentions `coga/skill-update`, the weekly branch the
skill-update job rebuilds with `checkout -B` anyway.

## Verification

- `PYTHONPATH=$PWD/src <venv>/python -m pytest tests/test_branchsweep.py` →
  35 passed (was 24; added: sync-commits-deleted, real-changes-skipped,
  evil-merge-kept, head-absent-fetched-and-deleted, head-unfetchable-kept,
  diverged-lineage-skipped, prose-mention-pins, attachment-mention-pins,
  whole-name-only, three verdict unit tests, three report tests).
- Related modules (packaging twins, branchcleanup, autoclose, retire, runner,
  validate, open_pr, launch): 546 passed.
- Full suite from the feature worktree: `PYTHONPATH=$PWD/src
  /home/n/Code/claude/coga/.venv/bin/python -m pytest -q` → 2507 passed,
  0 failed (2:47). Branch rebased on `origin/main` (`ffb0e361`), clean.

## Adjacent, not fixed here

- `branchsweep._current_branch` still uses `rev-parse --abbrev-ref HEAD`
  (the shadowable spelling `coga/codebase` warns about). Out of scope.
- `recurring/autoclose-merged` is `in_progress` and dirty in the primary
  checkout (`git status`), which is why its blackboard pins branches today;
  looks like a dead or in-flight run, not something this ticket touches.
