---
title: 'Simplify branchsweep (pilot: cut Coga''s code size)'
status: blocked
owner: nicktoper
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
step: 1 (design)
agent: claude
---

## Description

The owner's hypothesis is that most of Coga's ~60k lines in `src/coga/` serve
no real purpose. Modules look far more complex than the job they do; `git.py`
and `launch.py` are typical examples. This ticket is the **pilot** of a
module-by-module simplification. It codesigns `src/coga/branchsweep.py` with
the owner, then implements the simplification.

`branchsweep`'s essential job is small. For each branch, it checks whether the
PR merged or is still active and deletes the branch once it has landed. The
module is ~1,730 lines, carries a 75-line docstring, and imports 16 other
Coga modules. Most of that is incident-driven edge-case handling.

The design must:

1. State the module's essential job in one sentence.
2. List every mechanism and edge case it carries. Give each one a verdict with
   a reason:
   - **cut**: not worth keeping.
   - **fix at the source**: the incident came from elsewhere, often a state
     Coga itself produced. Fix it there and the sweep no longer needs to
     handle it.
   - **lift a level**: stop handling it in code. Fail loud and leave the
     judgment to the agent or human, guided by text.
   - **keep**: only if it is truly mechanical and earns its lines.
3. Give a target size, then implement it.

The design step is an attended codesign. The agent proposes verdicts, and the
owner settles them live in that session before the bump. Open questions do not
wait for `review-design`.

Done means a merged PR that brings `branchsweep.py` to the agreed target size,
or records on the blackboard why it could not. Every cut, moved, or kept
mechanism must trace to a verdict in the design. Mechanisms that guard
against data loss need an explicit verdict and reason. These include the
`retired/` archive tag before delete and the closed-unmerged authorization. The topics that describe the removed behavior must be updated in the
same PR. A short "method notes" section on the blackboard records what the
pilot taught for the next modules.

**Status of this spec:** the verdicts below are the agent's *proposals*
(2026-11-17). The owner settles them in an attended session. The blackboard's
`## Open Questions` lists the ones that change the shape. Until the owner
settles them, read every verdict as provisional.

### Essential job

For each local and `origin` branch that no live ticket records, delete it once
its tip is already preserved, either on the control branch or inside the head
of a GitHub PR for that branch with no PR still open. Report every branch it
keeps, with the reason.

The unifying idea is **containment**. Today the sweep accepts a tip *equal
to* a merged head, then adds patch-id, state-path and archive machinery to
cover the shapes that are not equal. Instead, the sweep deletes a ref only
when its tip is an ancestor of (or equal to) a durable ref:

- the control branch, local or remote-tracking; or
- the head of a PR for that branch name. GitHub keeps `refs/pull/<n>/head`
  for merged and closed PRs alike, so that head is durable.

Under that rule a delete loses no commit, so the archive tag and the
draft-release path have nothing left to protect. Anything not contained is
kept and reported, and a human decides.

### Mechanism inventory and proposed verdicts

| # | Mechanism (current symbol) | Verdict | Reason |
|---|---|---|---|
| 1 | Merged-PR lookup by head name plus the "no open PR" condition (`_merged_prs`, `_closed_unmerged_prs`, `prs_for_head(..., "open")`) | **keep, simplified** | This is the core signal. Make one `gh pr list --head <b> --state all --json number,state,headRefOid` call per branch instead of up to three. |
| 2 | Tip equal to the merged head | **keep** (subsumed by containment) | `git merge-base --is-ancestor <tip> <head>` covers both equal and lagging tips. |
| 3 | Ref *lags* the merged head because the last push came from another checkout | **keep** (subsumed by containment) | The same single ancestry check. The PR head is fetched from `refs/pull/<n>/head` when missing (`_fetch_pr_head`, kept). |
| 4 | Ref *walked past* the merged head through Coga state-sync commits; the "only Coga state paths" analysis (`_non_state_paths`, `coga_root_prefix`, `is_coga_state_path`, `state_root_unavailable`) | **fix at the source (already fixed)** → cut | Coga no longer merges control state into feature branches: the `Merge <control> state into <branch>` shape appears only in the `branchsweep.py` docstring. `git.sync_task_state` publishes ticket state to control. A ref with commits past its merged head is new work, so keep it and report it. |
| 5 | Ref rebased by another checkout and merged from that copy; `git patch-id --verbatim` matching (`_verbatim_patch_ids`, the patch-matching half of `merged_pr_verdict`) | **lift a level** → cut from sweep | This is rare and has a human remedy. Report it as "not contained in PR #n's head" and leave the decision to the human. The topic gives the review commands (`git log <pr-head>..<tip>`, then `git branch -D`). `_verbatim_patch_ids` **moves** to `skill_manager.py`, its only other consumer. |
| 6 | `MergedPrVerdict` / `_SourceDifference` / `comparison_incomplete` | **cut** | These are the result types of #4/#5. A plain kept-reason string replaces them. |
| 7 | Broad "any mention pins" scan of every live ticket file, plus the period-task exception (`_live_ticket_branches`, `_MENTION_*`, `_task_files`, `_PERIOD_TASK_PREFIX`) | **fix at the source** → keep only `## Dev` `branch:` claims | The incident was a draft that named its branch only in prose. Under containment, deleting such a branch loses no commit: the work is on the PR head or control. The `bootstrap/ticket` guide already makes `## Dev` `branch:` the record. Read `parse_branch_names(blackboard)` for every non-terminal ticket. This also removes the need for the period-task exception, which existed only because the broad scan matched generated reports. An unreadable ticket still counts as live (fail safe, one `except`). |
| 8 | Closed-unmerged PR authorized through terminal ownership (`_terminal_owners`, `_closed_pr_claim`, `retires.md` scan, recorded-worktree check, `removed_worktree` param) — **data-loss guard** | **fix at the source**: authority comes from the caller | Only ticket-scoped disposal (`checkout_disposal._sweep_owned_branches`) can know the ticket is terminal, and it already runs `live_checkout_claim` per branch before calling the sweep. It passes `closed_ok=True`. The sweep then accepts a closed PR's head under the same containment rule, and `refs/pull/<n>/head` preserves the work. The daily sweep never treats a closed PR as authority and reports such branches as kept. Data-loss reason: containment in a GitHub-kept PR ref, plus an explicit terminal-ticket caller. |
| 9 | `retired/<branch>` archive tag with the `@<sha12>` fallback, local mirroring, and divergent-tip selection (`_publish_retirement_tag`, `_archived_object`, `_mirror_local_tag`, `_containing_tip`, `retirement_failures`) — **data-loss guard** | **cut** | Under containment, every deleted tip is reachable from control or from `refs/pull/<n>/head`, both durable on the remote. The tag duplicated that. The report names the PR number and tip for recovery (`git fetch origin refs/pull/<n>/head`). Existing `retired/*` tags (285 here) stay untouched; nothing reads them. |
| 10 | Worktree pinning, and removal under `[git].worktrees_ticket_owned` (`_inspect_pinning_worktree`, `_remove_pinning_worktree`, `worktree_removed`, `worktree_pinned`) | **cut removal; keep pinning as git's own refusal** | Ticket work no longer creates linked worktrees (`coga/checkouts`; `coga/checkout-cleanup` says so). Keep `git worktree prune`, one call that stops a wiped `/tmp` registration from pinning. A branch still checked out is skipped and reported "checked out in <path>", read from `git worktree list --porcelain`. Retire's own legacy-worktree removal (`branchcleanup.remove_ticket_worktree`) is untouched. The `worktrees_ticket_owned` key is removed (see #17). |
| 11 | Protection of the skill-update branch (`SKILL_UPDATE_BRANCH`) | **cut** (open question Q3) | The open-PR guard covers it while an update is in flight. Between runs, its tip is contained in a merged head, and the next skill-update run recreates the branch. Cutting it also removes the `skill_manager` import cycle. |
| 12 | Control branch and checked-out branch skipped | **keep** | Mechanical; two lines. |
| 13 | Release-local-draft path (`--publish-and-release-local`, `_release_local_draft`, `_check_release_*`, `_release_repository`, `_github_git_identity`, `_draft_claim`, `_report_retained_draft`, `_ReleaseRefused`) | **lift a level** → cut | This is a ~200-line CLI that wraps `git push`/`git branch -D` behind proofs, so it duplicates the agent or human. The report says why a branch was kept. The `branch-sweep` topic tells the human how to inspect it and delete it by hand. `run_branch_sweep_recipe` takes no arguments again. |
| 14 | Local-before-remote ordering; tip recheck before delete; logged `-D` tip; remote delete with `--force-with-lease` (`branchcleanup.delete_local_branch` / `force_delete_local_branch` / `delete_remote_branch`) | **keep** (reuse unchanged) | These are mechanical data-loss guards that cost a few lines here. They live in `branchcleanup`, which is outside this pilot. |
| 15 | Stop-early gates: local enumeration failure, worktree prune/list failure, `gh` unavailable | **keep, simplified** | Each becomes one recorded failure plus exit 2. A per-branch `gh` or `git` error records that branch's failure and **continues** with the others (required: one problem branch must not stop the sweep). Only a failure of a whole listing (local refs, `ls-remote`, worktrees) stops the sweep. |
| 16 | Retire follow-up settlement (`discharge_owned_followups`, `followups_*` fields) | **move** to `autoclose.py`, beside `dispose_worklist_backlog` (open question Q2) | This is worklist disposal, not branch sweeping. Its collaborators are all autoclose and `retire_worklist` code. `run_branch_sweep_recipe` still calls it, so behavior is unchanged. Simplifying it belongs to the `autoclose.py` follow-up ticket. Its lines are **not** counted as savings. |
| 17 | `[git].worktrees_ticket_owned` config key (`config.py` `git_worktrees_ticket_owned`, `_parse_git`, `commands/init.py`, template `coga.toml` comment) | **cut** | Its only reader is #10. `_parse_git` then rejects the key as an unknown key, with a message saying it was removed. Check `_parse_git`'s known-keys tuple. This repo does not set it. |
| 18 | Report: `render_sweep_report`, blackboard append via `blackboard_from_env`, stdout fallback, ~15 result fields and the `failure` precedence chain | **keep, simplified** | Print `## Branch Sweep` with three parts: deleted (local/remote), kept (branch: reason), and failures. Output goes to stdout only. The clone-scoped run keeps stdout in `.coga/recurring-clone/branch-sweep.log` and the run record. Cut the blackboard append: the packaged template is `scope: clone` and has no period task (open question Q4). |
| 19 | Non-UTF-8 ref names abort the sweep (known failure in `coga-dev/internals/branch-sweep`) | **fix** while here | Pass `errors="surrogateescape"` in `_git`, as `branchcleanup._git` does. |

### Where failures surface

The sweep runs unattended. Every kept branch and every failure becomes a line
in the `## Branch Sweep` report on stdout, which the clone runner keeps in
`.coga/recurring-clone/branch-sweep.log` and the run record. Any failure makes
the recipe exit 2, which the recurring runner records as a failed run. A
per-branch failure never stops the remaining branches. In the disposal path,
the report lines are added to `CheckoutDisposal.notes` as they are today.

### Acceptance criteria

- [ ] The owner has settled every verdict in the inventory, and the
      blackboard records the settled list. Any verdict the owner changed is
      implemented as settled.
- [ ] `src/coga/branchsweep.py` is **≤ 300 lines**, docstring included, with
      `discharge_owned_followups` moved out per #16. If #16 stays in place,
      the target is ≤ 420. The PR description states the before and after
      line counts.
- [ ] `branchsweep.py` imports at most 6 Coga modules (today it imports 16).
- [ ] The daily sweep deletes a local or remote ref only when its tip is an
      ancestor of the control ref or of the head of a merged PR for that
      branch name, and no PR for that head is open.
- [ ] A closed-unmerged PR authorizes deletion only when the caller passes
      `closed_ok=True` (`checkout_disposal._sweep_owned_branches`). The daily
      sweep reports such a branch as kept.
- [ ] A branch named by a non-terminal ticket's `## Dev` `branch:`, the
      control branch, or the checked-out branch is never deleted, and the
      report says why.
- [ ] A branch checked out in a worktree is kept and reported. The sweep
      removes no worktree. `[git].worktrees_ticket_owned` no longer exists,
      and setting it fails config loading with a message naming the removal.
- [ ] One branch's `gh`/`git` error is reported, and the sweep continues with
      the remaining branches. The recipe then exits 2.
- [ ] `coga run branch-sweep` accepts no arguments. `--publish-and-release-local`
      is gone.
- [ ] `skill_manager` no longer imports from `branchsweep`.
      `_verbatim_patch_ids` lives in `skill_manager.py`.
- [ ] The topics in `## Context` / *Topics to update* describe the new
      behavior, with no stale references to removed symbols
      (`grep -rn "_terminal_owners\|merged_pr_verdict\|retired/\|worktrees_ticket_owned\|publish-and-release-local" src docs/contexts`
      returns only intentional mentions, such as "existing `retired/` tags
      are left as-is").
- [ ] Tests for removed behavior are deleted, not ported. A small
      `tests/test_branchsweep.py` covers the following and passes, with
      `python -m pytest`:
      - delete at equal tip, at a lagging tip, and when landed on control;
      - keep when there are commits past the head;
      - keep for an open PR, for a live `## Dev` claim, for a checked-out
        branch, and for a closed PR without `closed_ok`;
      - delete for a closed PR with `closed_ok`;
      - per-branch failure isolation;
      - local-before-remote ordering.
- [ ] `coga validate --json` is clean. The blackboard has a `## Method notes`
      section for the next modules.
- [ ] `v1/microkernel/04e-…` has a blackboard note pointing here (the design
      step has already done this).

### Proposed shape

1. **`src/coga/branchsweep.py`** (rewrite). Public surface:
   - `BranchSweepResult(local_deleted, remote_deleted, kept: list[str], failures: list[str], notes)`.
     `notes` stays so that `checkout_disposal` can pass `disposal.notes`.
   - `sweep_branches(cfg, root, *, echo=print, result=None, only=None, closed_ok=False)`.
     It does the following in order:
     1. `git worktree prune`, then parse `git worktree list --porcelain` into
        `{branch: path}`;
     2. list local refs with `for-each-ref` and remote refs with `ls-remote --heads`;
     3. collect live claims from `parse_branch_names` over non-terminal
        tickets, read through `list_tasks` / `read_ticket` /
        `read_blackboard`;
     4. for each branch in a `try`: run the skip checks (control, current,
        claimed, checked out); make one `gh` call; refuse if a PR is open;
        build the candidate heads from merged PRs, plus closed PRs when
        `closed_ok`; fetch each missing head from `refs/pull/<n>/head`;
        then test the local tip and the remote tip separately with
        `--is-ancestor` against the heads and control refs; delete the local
        ref through `branchcleanup.force_delete_local_branch` (or
        `delete_local_branch` for the control-landed `-d` path), then the
        remote through `delete_remote_branch`;
     5. collect every outcome in `result`.
   - `render_sweep_report(result, *, generated_at) -> str`.
   - `run_branch_sweep_recipe(cfg, argv, *, result=None) -> int`: refuse
     arguments, run `sweep_branches` and then
     `autoclose.discharge_owned_followups`, print the report, and exit 2 on
     any failure.
   - The module docstring is ≤ 15 lines and states the essential job and the
     containment rule.
2. **`src/coga/autoclose.py`**: receives `discharge_owned_followups`
   unchanged. Its result fields move into a small dataclass, or it returns
   its lines for the report.
3. **`src/coga/checkout_disposal.py`**, `_sweep_owned_branches`: call
   `sweep_branches(..., only=unclaimed, closed_ok=True)` and drop
   `removed_worktree`. Update the module docstring's sweep mention.
4. **`src/coga/skill_manager.py`**: inline `_verbatim_patch_ids` (moved
   verbatim) and drop the lazy import.
5. **`src/coga/config.py`, `src/coga/commands/init.py`, template `coga.toml`**:
   remove `worktrees_ticket_owned` (#17).
6. **`src/coga/branchcleanup.py`**: no behavior change. Fix only the comment
   in `delete_local_branch` that names `merged_pr_verdict`. Drop exports
   that end up with zero consumers (`inspect_worktree_for_removal` and
   `remove_inspected_worktree` stay if retire still uses them).
7. **Topics and templates** (same PR):
   - `checkout-cleanup/branch-sweep/SKILL.md`: rewrite to containment, the
     kept-reasons list, and manual review of kept branches; drop the
     archive, release, and `worktrees_ticket_owned` sections.
   - `checkout-cleanup/terminal-owners/SKILL.md`: closed-PR authority only
     on the disposal path, via the caller.
   - `checkout-cleanup/SKILL.md`: leaf descriptions and the restricted-sweep
     paragraph.
   - `recurring/branch-sweep/ticket.md` steps 3–8 and `ticket.py` (drop the
     legacy period-task bump if Q4 is settled that way).
   - `bootstrap/workflows/branch-sweep/sweep.md` and
     `bootstrap/skills/coga/branch-sweep/sweep/SKILL.md`.
   - `docs/contexts/coga-dev/internals/branch-sweep/SKILL.md`: drop the
     verdict, retained-draft, retirement-tag, and non-UTF-8 sections.
   - Grep for other mentions: `coga/cli`, `coga/recurring/templates`,
     `coga-dev/codebase`, `coga-dev/codebase/gotchas`, `retire.md`.
8. **Tests**:
   - Rewrite `tests/test_branchsweep.py` to the matrix in the acceptance
     criteria.
   - Delete sweep cases in `tests/test_recurring.py`,
     `tests/test_branchcleanup.py`, `tests/test_retire.py`, and
     `tests/test_runner.py` that assert removed behavior. These include
     retirement tags, the draft release, state-only walk-past, patch-id,
     worktree removal, and terminal owners in the daily sweep.
   - Keep the ones that still describe live behavior.

Order: write the new module and its tests first, then rewire the callers,
then remove config, then update the topics, then delete the dead tests.

### Out of scope

- Simplifying `branchcleanup.py`, `autoclose.py`, `checkout_disposal.py`, or
  `retire_worklist.py` beyond the call-site edits above. Each gets its own
  follow-up ticket using the method notes.
- Moving the recipe to the edge (`v1/microkernel/04e`).
- Deleting existing `retired/*` tags or migrating anything that reads them
  (nothing does).
- Creating the sibling simplification tickets.
- Changing retire's own legacy-worktree removal.

## Context

### Why simplify, and how to judge each case

- **The current code is too complex.** Edge cases that once caused incidents
  should be re-examined, not preserved by default. A defensive branch that
  encodes judgment works against `coga-dev/principles`
  (`docs/contexts/coga-dev/principles/SKILL.md`, cited, not attached).
  Three principles apply: "Text above code", "Amplify agents, don't
  duplicate them", and "Keep everything at human scale". "Fail loud" replaces
  silent defensive handling.
- **The design step is a codesign.** Run it attended, with the owner. Propose
  verdicts and let the owner decide; do not settle the cut list alone.
- **Tests are out of scope as a target** (~100k lines). Tests shrink with the
  code they cover. Delete tests for removed behavior rather than porting them.

### What `branchsweep.py` carries today (as of 2026-11-17)

The module docstring lists the mechanisms the design must give verdicts on:

- merged-PR lookup by head branch name, with a "no open PR" condition;
- the `merged_pr_verdict` patch-id and "only Coga state paths" analysis for
  refs that walked past, lag, or were rebased from the merged head;
- broad "any mention pins" matching against live ticket text, plus a recurring
  period-task exception;
- closed-unmerged PRs authorized through terminal-ticket ownership
  (`_terminal_owners`, `_closed_pr_claim`, `retire_worklist`);
- `retired/<branch>` archive tags with an `@<sha12>` fallback;
- worktree pinning and removal under `[git].worktrees_ticket_owned`;
- protection of the skill-update branch;
- the release-local-draft path (`--publish-and-release-local`);
- report rendering onto the period task's blackboard.

Coupling, which the design must take into account:

- The deletion plumbing is shared with `branchcleanup.py` (~1,175 lines), which
  retire also uses.
- `autoclose.py` (~1,842 lines) is imported by the sweep and also references
  it.
- `checkout_disposal.py` and `retire_worklist.py` are coupled to the sweep.
- `config.py` and `skill_manager.py` reference it.
- `runner.RECIPES["branch-sweep"]` calls `run_branch_sweep_recipe`.

The design decides how far the pilot reaches into these modules. Record that
boundary explicitly.

The sweep runs unattended as a recurring job. A "fail loud" verdict must say
where the failure surfaces: the period task's blackboard report or a
notification. One problem branch must not stop the sweep of the others.

### Topics to update in the same PR

These describe current sweep behavior. Edit them (do not attach them) when
behavior changes:

- `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`
- `.../coga/checkout-cleanup/terminal-owners/SKILL.md`
- `.../coga/checkout-cleanup/SKILL.md`
- the `branch-sweep/sweep` workflow and the `coga/branch-sweep/sweep` skill
  under the package `bootstrap/`
- the recurring job `src/coga/resources/templates/coga/recurring/branch-sweep/`
  (`ticket.md`, `ticket.py`)
- `tests/test_branchsweep.py` (~3k lines) and the sweep cases in
  `tests/test_recurring.py`: delete the tests for removed behavior

### Coordination with `v1/microkernel`

`v1/microkernel/04e-second-pass-move-branch-sweep-and-autofix-repl` (parked)
plans to move the branch-sweep recipe to the edge. Simplify first, so 04e
moves the smaller module. Moving ~1,700 lines only to cut most of them later
is wasted work. Leave a note on 04e's blackboard pointing here.

### After the pilot

Creating the sibling tickets is a follow-up, not part of this ticket's done.
Once the pilot lands, the owner creates them, carrying the method notes. Candidates, by size: `recurring_runner.py` (~5.7k lines),
`launch.py` (~4.6k), `git.py` (~3.8k), `recurring.py` (~2.8k),
`megalaunch.py` (~2.4k), `skill_manager.py` (~2.1k), `validate.py` (~2.1k),
`config.py` (~2.0k), `commands/init.py` (~2.0k), `autoclose.py` (~1.8k).

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

## Design step status (2026-11-17)

The spec is written under `## Description` (essential job, 19-row verdict
table, acceptance criteria, proposed shape, out of scope). All verdicts are
**proposals**. The ticket requires the owner to settle them live before the
bump. This session ran in a megalaunch queue with no owner available, so it
blocked instead of bumping.

Investigation facts the verdicts rest on:

- `sweep_branches` has two callers: the daily recipe
  (`run_branch_sweep_recipe`) and ticket-scoped disposal
  (`checkout_disposal._sweep_owned_branches`, with `only=`). The only reader
  of `merged_pr_verdict` is a comment in `branchcleanup.delete_local_branch`.
  `skill_manager` lazily imports `_verbatim_patch_ids`.
- The "walked past via state-sync" shape (`Merge <control> state into
  <branch>`) no longer appears anywhere in `src/` except the branchsweep
  docstring, because `git.sync_task_state` publishes ticket state to control.
- `coga/checkout-cleanup` already says ticket work no longer creates linked
  worktrees. No repo here sets `worktrees_ticket_owned`.
- This clone has 22 local branches, 16 on origin, and 285 `retired/*` tags.
  Nothing reads the tags back.
- Lines in `branchsweep.py` by area (approximate):
  - archive tag: ~150
  - release-local-draft: ~180
  - verdict, patch-id and state paths: ~210
  - terminal owners and closed PRs: ~110
  - mention scan: ~90
  - worktree removal: ~95
  - follow-up discharge: ~105
  - docstrings: ~150
  - core loop, listings and report: the rest

## Open Questions

Each one must be settled with the owner before the bump.

- **Q1 — Containment replaces the archive tag (#9) and patch-id/state-path
  analysis (#4, #5).** Is "tip is an ancestor of control or of a GitHub PR
  head (`refs/pull/<n>/head`)" an acceptable sole data-loss guard? The cost
  is twofold. First, a rebased-and-merged copy is kept and reported instead
  of auto-deleted. Second, recovery depends on GitHub keeping PR refs rather
  than our own tag.
- **Q2 — Pilot boundary for `discharge_owned_followups` (#16).** Should it
  move to `autoclose.py` unchanged (target ≤ 300 lines), or stay in
  `branchsweep.py` (target ≤ 420)? The other option is to cut it outright.
  That would mean clone-owned `retires.md` entries wait for a manual
  `coga retire` in the owning clone.
- **Q3 — Skill-update branch protection (#11).** Cut it, relying on the
  open-PR guard and recreation by the next update run, or keep it as a
  one-line protected name?
- **Q4 — Legacy period-task path (#18).** The packaged template is
  `scope: clone`, so it has no period task. Should the pilot drop
  `blackboard_from_env` reporting, the `COGA_TASK_SLUG` bump in `ticket.py`,
  and the compatibility `branch-sweep/sweep` workflow? Or should it keep the
  workflow file and only drop the blackboard append?
- **Q5 — Live-claim scan narrowed to `## Dev` `branch:` (#7).** Is this
  acceptable, given that under containment a mistaken delete loses no
  commit?
- **Q6 — Removing `[git].worktrees_ticket_owned` (#17).** Should a
  leftover setting be a hard config error, or a one-release deprecation
  warning?

---

## Blockers

- [ ] [2026-11-17 16:23] [agent:claude] id=20261117T162308 Design spec written with 19 proposed verdicts (Description table). Per the ticket, the owner must settle them live before bump: answer Open Questions Q1-Q6 on the blackboard — chiefly Q1 (replace retired/ archive tag + patch-id/state-path analysis with 'tip contained in control or a GitHub PR head') and Q2 (move discharge_owned_followups to autoclose.py → branchsweep.py target <=300 lines). Relaunch this task attended to settle them, then bump.
