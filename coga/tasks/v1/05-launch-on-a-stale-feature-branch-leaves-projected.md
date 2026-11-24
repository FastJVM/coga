---
title: Launch on a stale feature branch leaves projected ticket and log.md dirty
status: blocked
owner: nicktoper
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

### Report (seed)

When `coga launch <slug>` runs on a feature branch far behind the control branch, state sync correctly lands ticket and log commits on `main` through the plumbing path, but also writes the same state into the feature branch's working tree. Seen in solarmonero with coga 0.4.1: branch `coga/exp-zen4-1-long-window-execution-82b5ec` was 130 commits behind `main`, and `main` had renamed the ticket from `exp/zen4/1-long-window-execution.md` to `04-long-window-execution.md`. After launch and `coga block`, the checkout held an untracked `coga/tasks/04-long-window-execution.md` (byte-identical to `main`) and a modified `coga/log.md` that appended two lines to a stale copy missing about 100 lines from `main`. Those leftovers block or conflict with later `git merge origin/main`, `pull` and `checkout`. The workaround was to stash both files and merge `main`. Expected: on a non-control branch, coga leaves no dirty coga-managed files, or it first brings the branch up to date with the control branch, or it at least warns that the branch is behind and the files it wrote are copies. Related: coga-bump-on-feature-branch-leaves-stale-index-loc, 06-fix-coga-git-sync-failures-that-leave-main-diverge.

### Problem under the design this ticket targets

The leftovers come from two mechanisms that v1/03
(`v1/03-use-git-like-everyone-remove-coga-s-publication-ab`) deletes:
launch's checkout preparation projects the control copy of the ticket onto
the feature branch (`checkouts.enter_ticket_checkout` →
`_project_after_switch`), and lifecycle commands publish ticket and log to
control through plumbing (`git.sync_task_state` → `git.publish`) while the
working tree keeps the branch-relative copies. After 03 there is no control
branch, no projection, and no publication. Ticket and log are ordinary files
on whatever branch is checked out, and `coga/log.md` merges by union. So the
reported failure should become impossible by construction. This ticket
protects that with a regression test and documents how a branch that is
behind its base behaves. It does **not** patch today's `git.py`/`checkouts.py`:
that code is being deleted, and a fix there would be throwaway work (see
Out of scope and Open Questions).

Implement only after v1/03's implementation PR has merged. If 03's design
changes before then, re-check this spec against the merged model first.

### Acceptance criteria

- [ ] A test (`tests/test_stale_branch_state.py` or inside the plain-Git
      test module 03 adds) builds a Git repo fixture: `main` has a ticket
      renamed from `coga/tasks/exp/a.md` to `coga/tasks/04-a.md`, and
      `coga/log.md` gains at least 3 lines after the branch point. A
      feature branch, created before the rename, carries the old path and
      is at least 2 commits behind `main`.
- [ ] On that branch, the test runs the lifecycle sequence a session
      performs: a `run:`-step `coga launch` (or `coga mark`/`bump`,
      whichever 03 leaves as the no-agent entry), then `coga block --task
      exp/a --reason x`. Afterwards `git status --porcelain` lists only
      `coga/tasks/exp/a.md` and `coga/log.md` as modified. There are no
      untracked files, and in particular no `coga/tasks/04-a.md`.
- [ ] No commit was created and the branch tip is unchanged (`git
      rev-parse HEAD` before and after are equal). `main` is unchanged too,
      so nothing was published.
- [ ] After `git commit -am state`, `git merge main` completes without a
      conflict in `coga/log.md`: the union driver keeps both sides. The
      merged log has every `main` line plus the branch's new lines. If Git
      reports a rename/modify conflict for the ticket, the test asserts
      only that it is Git's ordinary conflict on that one path, not a
      Coga-written file. Record which of the two outcomes the test
      observed on the blackboard.
- [ ] The test also covers dirty files: with ticket and log left
      uncommitted, `git merge main` fails only by Git's own "would be
      overwritten" refusal, which the `coga/git` topic documents (next
      item).
- [ ] The user topic `coga/git` (created by 03) gets a short "Branch
      behind its base" paragraph. On a branch, Coga reads and writes the
      branch's copy of the ticket and log. Renames and edits made on the
      base appear only after you merge or rebase the base. Commit or stash
      ticket/log changes before `git merge`/`pull`, as with any file. The
      log merges by union. No other topic restates this. Link it instead.
- [ ] If the owner accepts Open Question 1, `git/open-branch` reusing a
      recorded branch prints one stderr line `note: <branch> is N commits
      behind <base>; merge or rebase it to pick up state changed there`
      when N > 0. The base is the local ref that 03 settles for open-branch;
      the script does no extra fetch. A test with a stubbed repo covers
      N > 0 and N = 0.
- [ ] `python -m pytest` passes and `coga validate --json` reports no errors.

### Proposed shape

1. After 03 merges, read its `coga/git` topic and test helpers. Reuse its
   no-`.git`/plain-Git fixtures rather than a new harness.
2. Write the regression test first. Run it before any other change: under
   03 it is expected to pass. If it fails, the failure is a 03 regression.
   Fix it in the module 03 left responsible (ticket write in the lifecycle
   commands, `logfile.append_log`), not with new Git code in the kernel.
3. Add the `coga/git` paragraph in
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/git/SKILL.md`.
4. Only on a yes to Open Question 1: add the behind-count note to
   `git/open-branch/run.py`'s reuse path with
   `git rev-list --count <branch>..<base>`. A failed count is silent (no
   base ref locally) and never fails the step.
5. Update the v1 README row for 05 to its outcome.

### Out of scope

- Any change to today's `src/coga/git.py`, `checkouts.py`, `state_sweep.py`
  or the launch boundary. 03 deletes them.
- Automatically merging or rebasing the base into a feature branch, or
  fetching from the kernel (03 decisions 1, 4, 9: the kernel does not know
  Git; fail-stop).
- Detecting a ticket renamed on the base and redirecting the branch to the
  new path. Git's rename detection at merge time owns that.
- The sibling reports `coga-bump-on-feature-branch-leaves-stale-index-loc`
  and `06-fix-coga-git-sync-failures-that-leave-main-diverge`. They are
  separate tickets, and 03 likely moots them as well.

## Context

### Codebase facts (design survey, 2026-11-20, main at 258ca14c7)

- Today's projection: `checkouts.enter_ticket_checkout` switches to the
  recorded branch, then `_project_after_switch` writes control's ticket
  bytes at control's path (`plan.rel`) unstaged and records them via
  `git.record_projected_baseline`. If control renamed the ticket, this
  produces the untracked new-path file from the report. 03 deletes
  `checkouts.py` and `_prepare_step_checkout`.
- Today's publication: `git.sync_task_state` (called by bump/block/mark)
  passes the ticket and `log_path(cfg)` to `git.publish`. That commits onto
  control through plumbing and leaves the working-tree log as the branch's
  copy plus the new lines, which is the stale log in the report. 03 deletes
  `git.py`.
- The launch boundary (`coga/checkouts/launch-boundary`, since #909,
  2026-09-29, so present in 0.4.1) returns an ordinary launch's checkout to
  `main`. It discards projected/log files already proven on control, so the
  report's leftovers point to a path that skipped or refused the return:
  a megalaunch pick, a recorded-`worktree:` launch, or a refused return.
  This was not reproduced. It matters only if 03 does not land (Open
  Question 2).
- v1 README: "05 … likely moot under 03; re-check before work." 03 is at
  `review-design`. Its §6 creates `coga/git` and sets
  `coga/.gitattributes` to `/log.md merge=union`. Its Open Question 6
  (branch base for `open-branch`, fetch or not) decides which base ref the
  optional note in this ticket compares against.

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

<!-- coga:blackboard -->

## Design notes (2026-11-20)

- Specced against v1/03's plain-Git model. The README already marks 05
  "likely moot under 03". Patching `git.py`/`checkouts.py` now would be
  deleted with 03.
- The report's root cause under 0.4.1 was not reproduced. Hypothesis: an
  exempt launch (megalaunch pick / recorded worktree) or a refused return,
  because the launch boundary would otherwise have cleaned proven
  projected/log files.

## Open Questions

1. **Stale-branch note in `git/open-branch`.** Should reusing a recorded
   branch print "N commits behind <base>"? The reporter asked for "at
   least a warning". It costs one `git rev-list --count` in a script step,
   with no kernel Git. Recommended: yes, local refs only, no fetch.
2. **If 03 slips or is rejected:** should this ticket instead fix today's
   code? That would mean reproducing the exempt-launch path and making
   projection/publication leave no branch-relative dirt. Or should 05 wait?
   Recommended: wait. 0.4.x users have the documented stash-and-merge
   workaround.
3. **Cancel instead?** If the owner considers 03's own tests sufficient,
   05 can be canceled as superseded rather than adding a dedicated
   regression test. Recommended: keep it. The test is small and pins the
   exact field failure.

---

## Blockers

- [ ] [2026-11-20 17:21] [agent:codex] id=20261120T172106 Relaunch evaluate-design from a clean, current main checkout. The supplied checkout is on refresh-v1-microkernel-readmes-after-retro, holding unmerged commit 258ca14c7 for refresh-the-v1-microkernel-task-readmes-after-the (in progress, no linked PR). The unstaged ticket and log files matched fetched origin/main before blocking. Preserve the implementation branch and its commit when returning to main.

---

## Blocker reminders

- ea6035f1e67d last_reminded: 2026-11-23 14:48
