---
slug: branch-sweep-strands-squash-merged-branches-whose
title: Branch sweep strands squash-merged branches whose tip moved
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/principles
  - coga/architecture
  - coga/codebase
  - coga/recurring
skills: []
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
secrets: null
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
