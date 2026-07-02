---
slug: branch-cleanup-as-recurring-tasks
title: branch cleanup as recurring tasks
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/recurring
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Build a recurring **branch sweep**: a script-mode job that deletes local and
remote git branches whose work has already landed, as a safety net behind the
retire-time deletion that `src/coga/branchcleanup.py` now performs. Retire
handles the common path, but its cleanup is best-effort (git/gh failures are
swallowed), and branches also leak when a ticket is deleted without going
through retire or a session dies mid-flight. The sweep's first run also prunes
the merged part of the pre-existing backlog (~10 local / ~29 remote stale
branches accumulated before retire-time deletion shipped); abandoned no-PR
branches are skipped-and-reported by design and may need one manual pass.

Model it 1:1 on `autoclose-merged`, which is the shape to copy end to end:

1. New sweep function (e.g. `src/coga/branchsweep.py`, mirroring
   `autoclose.sweep_merged` and reusing `branchcleanup.py`'s delete helpers):
   enumerate actual local and `origin` branches and delete the ones that are
   safe (gates below). No ticket-matching guesswork — the gate is GitHub, not
   Coga state.
2. Script skill `coga/skills/coga/branch-sweep/sweep/SKILL.md` with
   `script: run.py` that imports and calls the sweep function directly
   (same pattern as `coga/autoclose/sweep`).
3. One-step script workflow `coga/workflows/branch-sweep/sweep.md`
   (same shape as `autoclose-merged/sweep`).
4. Recurring task `coga/recurring/branch-sweep/ticket.md` with
   `autonomy: auto` and a weekly schedule (retire handles the daily flow;
   weekly is enough for leaks).

Because the runnable unit is the workflow + script skill, the sweep runs
**both ways**: on schedule via `coga recurring`, on demand via
`coga recurring launch branch-sweep`, or as a standalone one-off ticket that
sets `workflow: branch-sweep/sweep`. Note that in the recurring ticket's body.

**Deletion gates (all must hold):**

- Never `main` (the control branch), never the currently checked-out branch
  (git already refuses branches checked out in any worktree).
- Skip any branch recorded under a live (not-`done`) ticket's blackboard
  `## Dev` `branch:` line — a mid-workflow merged PR must not lose its branch
  while the ticket is still moving (autoclose treats those as suspicious for
  the same reason).
- **Remote** delete only when GitHub reports a **merged** PR for that head
  branch **and no open PR** (`gh pr list --head <branch>` with
  `--state merged` non-empty and `--state open` empty — by branch name, no
  ticket needed). The no-open-PR condition closes the branch-reuse hole: a
  branch that once merged a PR and was later reused for a new open PR must
  survive. Do not use ancestry: squash-merge leaves the tip a non-ancestor of
  `main`. Deleting `origin/<branch>` is not reflog-protected, so merged-PR is
  the only authorization.
- **Local** delete follows `branchcleanup.py`'s existing policy: prefer
  `git branch -d`; if that refuses but the PR merged (squash case), log the
  tip SHA then `-D`; unmerged with no merged PR → skip and report.
- `gh` missing/unauthed → skip gated deletes and report, never force.

Out of scope: changing retire-time deletion, and the autocommit idea from the
sibling ticket (`handle-better-delete-branches-autcommit`) — still its own
future ticket.

## Context

- `src/coga/branchcleanup.py` is the retire-time deleter — read its module
  docstring for the full safety model; reuse its local/remote delete helpers
  rather than duplicating them. Note they are private (`_delete_remote`,
  `_delete_local`) and shaped around a single ticket — decide between
  importing them or a small refactor to export them, and note the choice on
  the blackboard. `src/coga/autoclose.py` has `parse_branch_name()` (already
  normalizes the inconsistent `branch:` forms: bare, `- ` list item,
  backtick-wrapped) — use it for the live-ticket skip-list instead of a new
  regex; enumerate not-`done` tickets the same way `sweep_merged()` does.
  Its `pr_state()` is URL-keyed and does **not** cover the by-branch-name
  gate — write a new small gh helper for `gh pr list --head`.
- The model to copy: recurring ticket `coga/recurring/autoclose-merged/`,
  workflow `coga/workflows/autoclose-merged/sweep.md`, script skill
  `coga/skills/coga/autoclose/sweep/` (SKILL.md + run.py).
- **Packaged-copy sync checklist** — each new file has a shipped twin; add
  both or `coga init` drifts from this repo:
  - `coga/recurring/branch-sweep/` ↔
    `src/coga/resources/templates/coga/recurring/branch-sweep/`
  - `coga/workflows/branch-sweep/` ↔
    `src/coga/resources/templates/coga/workflows/branch-sweep/`
  - `coga/skills/coga/branch-sweep/` ↔
    `src/coga/resources/templates/coga/bootstrap/skills/coga/branch-sweep/`
- Tests: follow `tests/test_branchcleanup.py` (real temp git repo + bare
  origin) and `tests/test_autoclose.py`. Cover at minimum: squash-merged
  branch deleted, open-PR branch skipped, no-PR branch skipped,
  live-ticket branch skipped, `main`/checked-out never touched, `gh`
  unavailable → no deletes.
- History: retire-time deletion was ticket
  `handle-better-delete-branches-autcommit` — its blackboard has the design
  rationale (ancestry vs PR-merged gating) and the evaluator review that
  killed the earlier ticket-matching sweep design; this ticket's gh-by-branch-
  name gate is the answer to that objection.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap decisions (2026-07-01)

- Ticket was nearly obsoleted by retire-time deletion
  (`handle-better-delete-branches-autcommit` → `src/coga/branchcleanup.py`,
  shipped). Kept and repurposed: the sweep is now the **safety net** for
  branches that leak past retire (best-effort failures, tickets deleted
  without retire, dead sessions), and its first run clears the pre-retire
  backlog — so no separate one-off backlog ticket.
- Gate is **GitHub by branch name** (`gh pr list --head <branch> --state
  merged`), not ticket matching — answers the old evaluator objection that
  retired tickets lose their `branch:` line.
- Human wants it runnable **both ways**: scheduled recurring task and
  standalone/on-demand ticket. Achieved by making the workflow + script skill
  the runnable unit; recurring ticket is just one caller.
- Weekly schedule proposed (retire covers the daily flow) — human to confirm.
- Post-review edits: added the no-open-PR condition to the remote gate
  (branch-reuse hole), clarified `pr_state()` is URL-keyed so a new by-branch
  gh helper is needed, and softened "clears the backlog" (no-PR branches are
  skipped by design — expect a manual residue pass).

## Follow-up (2026-07-02)

- Confirmed workflow `code/with-review` + `agent: claude` per human request
  (these were already correct from the earlier bootstrap pass).
- Fixed `assignee:` from stale `nick` to `claude` — the `implement` step
  declares `assignee: agent`, which resolves off the ticket's `agent:` field,
  so the frontmatter should already reflect who picks it up first rather than
  the human owner.
- Attached the one context the evaluator flagged as missing: `dev/code`
  (the `## Dev` `branch:`/`pr:`/`worktree:` convention the sweep's live-ticket
  skip-list gate depends on, and which the implementer also needs for their
  own branch/PR bookkeeping on this code ticket).
- Everything else the evaluator raised under "Assumptions to question" was
  already resolved in the prior pass (no-open-PR gate, `pr_state()` caveat,
  softened backlog language, enumeration-mechanism pointer) — nothing left
  outstanding there.

## Evaluator review

**1. Description clarity — strong.** A cold agent can start immediately. The deliverable is enumerated as four concrete artifacts with exact paths, the model to copy (`autoclose-merged`) is named and exists in all three live locations (`coga/recurring/autoclose-merged/ticket.md`, `coga/workflows/autoclose-merged/sweep.md`, `coga/skills/coga/autoclose/sweep/{SKILL.md,run.py}`), and the deletion gates are spelled out rather than deferred to implementation. Factual claims check out: `src/coga/branchcleanup.py` exists and its module docstring states exactly the safety model the ticket summarizes (merged-PR gate for remote, `-d` then logged `-D` for local, gh-unavailable → skip); `src/coga/autoclose.py` has `pr_state()` (line 95), `parse_branch_name()` (line 71), and `sweep_merged()` (line 193); `tests/test_branchcleanup.py` and `tests/test_autoclose.py` exist. Branch counts are plausible: 11 local (≈9-10 stale after `main` and checked-out branches) and 29 remote (≈27 stale after `origin/main`/`HEAD`) — the "~29 remote" slightly counts main/HEAD, but the "~" covers it.

**2. Workflow fit — correct.** The build work is genuinely code-shaped (new Python module, tests, skill/workflow/recurring files, packaged twins, a PR), which is what `code/with-review` is for. The frontmatter's `autonomy: interactive` describes the build ticket, while the deliverable's recurring ticket will be `autonomy: auto` — the ticket keeps these distinct correctly. This is the same distinction the earlier evaluator review (preserved in `coga/tasks/handle-better-delete-branches-autcommit.md`) flagged, and it's handled here.

**3. Contexts — relevant, one plausible addition.** `coga/recurring` is exactly right: the agent is authoring a recurring task and needs the creation contract (5-field cron required, weekly period key `YYYY-Www`, description extraction via `## Description` to next `## `, the `###`-only-headings gotcha, blackboard-as-state rules). One candidate missing context: `dev/code` (`coga/contexts/dev/code/SKILL.md`), which defines the `## Dev` `branch:` convention the skip-list gate depends on. The ticket partially compensates by directing the implementer to `parse_branch_name()` instead of a new regex, which encodes the format variance — so this is optional, but attaching `dev/code` would be cheap insurance since the sweep's core safety gate reads that convention.

**4. Broad-context vs copied-fact — well judged.** The ticket already does the right thing: the load-bearing facts (squash-merge defeats ancestry, remote delete not reflog-protected, `parse_branch_name` normalizes three `branch:` forms, the exact packaged-twin path pairs) are copied into the body rather than left implicit in an attached context. The packaged-sync checklist in `## Context` is accurate — I verified `src/coga/resources/templates/coga/recurring/autoclose-merged/`, `.../workflows/autoclose-merged/`, and `.../bootstrap/skills/coga/autoclose/` all exist, so the three claimed twin locations follow the real pattern. `coga/recurring` is broad but nearly all of it applies here; attaching it (not excerpting) is correct.

**5. Scope — reasonable as one ticket.** It looks large (module + tests + skill + workflow + recurring ticket, each duplicated into the packaged tree), but the pieces are useless separately and the `autoclose-merged` precedent shows this exact bundle shipping as one unit. Out-of-scope lines (retire-time deletion unchanged, autocommit stays in the sibling ticket) are explicit. No split needed.

**6. Assumptions to question before launch:**

- **"Reuse `branchcleanup.py`'s delete helpers" understates the work.** The helpers are private (`_delete_remote`, `_delete_local`, `_pr_merged`) and shaped around a single ticket's `BranchCleanupResult` with a URL-keyed PR check. Reuse means either importing privates or a small refactor to export them — the implementer should decide which and note it on the blackboard, not silently duplicate.
- **`pr_state()` doesn't cover the ticket's gate.** `pr_state()` takes a PR URL; the sweep's gate is `gh pr list --head <branch> --state merged` (by branch name). A new gh helper is needed; `pr_state` is only reusable conceptually. The `## Context` mention of `pr_state()` could mislead a fast reader into thinking the gh check already exists in the needed shape.
- **Branch reuse hole in the merged-PR gate.** `gh pr list --head <branch> --state merged` returns a hit if that head *ever* had a merged PR — including a branch later reused for a new, still-open PR. The live-ticket skip-list catches most of this, but a reused branch on a deleted/done ticket slips through. Consider also requiring no *open* PR for the head (`--state open` empty) before deleting.
- **"First run clears the backlog" oversells slightly.** Only backlog branches with merged PRs get deleted; abandoned no-PR branches are skipped-and-reported by design. Expect a residue that needs one manual pass — fine, but the recurring ticket body shouldn't promise a clean slate.
- Minor: building the live-ticket skip-list requires enumerating not-`done` tickets' blackboards; the ticket names `parse_branch_name()` for parsing but not the enumeration mechanism (presumably the same task iteration `sweep_merged()` uses — worth confirming in `autoclose.py` line 193ff before writing new listing code).

**Bottom line:** Launchable as written. Well-scoped, factually accurate (every named file/function verified), and it explicitly answers the objections that killed the earlier sweep design. Before implementation: decide the private-helper reuse strategy, close the branch-reuse hole in the merged-PR gate (check for open PRs too), and optionally attach `dev/code`.
