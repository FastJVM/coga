---
title: Name cross-repo retire follow-ups with the repo that owns them
status: draft
owner: nicktoper
agent: claude
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
step: 4 (review)
---

## Description

## What broke

The 2026-09-10 autoclose sweep exited clean (`problems: 0`, ticket `done`), but
the one actionable thing it produced — a `coga retire` follow-up command — is
not runnable as written. `coga run autoclose` names the follow-up purely from
the `branch:`/`worktree:` fields recorded on the closed ticket, without checking
which git repository that worktree actually belongs to. When the checkout is a
linked worktree of a *different* repo than the one holding the ticket, the
emitted command fails `coga retire`'s same-repo worktree proof if a human pastes
it where the sweep printed it.

## Evidence

From the run's blackboard (mirrored into
`coga/recurring/autoclose-merged/ticket.md`):

> `autofix/escalate-watchdog-paused-recurring-tasks-instead-o` […]: worktree
> `/tmp/coga-watchdog-pauses`, branch `fix/watchdog-pauses` — `coga retire
> autofix/escalate-watchdog-paused-recurring-tasks-instead-o`

and the agent's own gotcha in the same blackboard:

> An auto-closed ticket's checkout is not necessarily a worktree of the repo
> holding the ticket. […] `coga retire` requires a same-repo linked worktree, so
> those follow-ups have to be run from the other checkout. **The sweep names the
> command without checking which repo the worktree belongs to.**

`/tmp/coga-watchdog-pauses` is a linked worktree of `/home/n/Code/claude/coga`
(FastJVM/coga), not of this multiply repo. The correction only exists because a
human noticed and hand-annotated the mirrored entry; a run that nobody reads
emits a command that silently fails.

This is not the already-known persistence bug
(`autofix/persist-autoclose-retire-follow-ups-beyond-the-per`, canceled as
superseded by the upstream `persist-autoclose-retire-follow-ups` ticket) — that
one is about *where* the section is written. This is about the *content* of the
line being wrong for cross-repo checkouts. It is also unrelated to the open
`autofix/make-dream-block-instead-of-done-when-its-retro-ch`.

Corroborating signal that these follow-ups do not get acted on: the run checked
the 2026-09-09 entries and found neither retired —
`/home/n/Code/coga-banner-opening` still on disk, `/tmp/multiply-receiver` still
listed `prunable`. Follow-ups are accumulating, so an unrunnable one will sit
there indefinitely.

## Where it lives

- Recipe: `coga.autoclose.sweep_merged`, dispatched by `coga run autoclose`
  (package-backed; the fix likely belongs upstream in FastJVM/coga, same as
  PR #778 did).
- Repo-side surfaces that document the contract and must be updated to match:
  `coga/workflows/autoclose-merged/sweep.md` (step: "It then names the `coga
  retire` follow-up for each closed ticket that still records a `branch:` or
  `worktree:`") and `coga/recurring/autoclose-merged/ticket.md` Description
  step 6.

## What a fix has to do

1. When the sweep is about to name a retire follow-up, resolve the recorded
   `worktree:` path to its owning repository — e.g. `git -C <worktree>
   rev-parse --path-format=absolute --git-common-dir` (or the main worktree's
   toplevel) — and compare it to the repo root that owns the ticket.
2. Same repo: emit today's line unchanged.
3. Different repo: emit a line that is actually runnable — name the owning
   checkout explicitly (e.g. `coga retire <slug>` *run from
   `/home/n/Code/claude/coga`*) and state that `coga retire` from the ticket's
   repo will fail its same-repo worktree proof.
4. Worktree path missing from disk or not a git worktree at all (the
   `/tmp/multiply-receiver` `prunable` case): say so rather than naming a
   command that cannot resolve, and point at the branch-only cleanup.
5. Keep the sweep non-destructive and keep it exiting zero — this changes only
   what the follow-up section says, never what it does.
6. Update `coga/workflows/autoclose-merged/sweep.md` and
   `coga/recurring/autoclose-merged/ticket.md` so the documented step 6 matches
   the new behaviour, and drop the hand-written cross-repo caveat from the
   parent blackboard entry once the sweep emits it itself.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `in_progress`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/870
branch: fix/retire-followup-owner
worktree: /tmp/coga-retire-owner

Repository: FastJVM/coga; primary source checkout `/home/n/Code/claude/coga`
(linked worktree of that repo — itself the cross-repo case this ticket is
about). This Multiply checkout owns the ticket and runs its workflow
transitions. Tests: `PYTHONPATH=/tmp/coga-retire-owner/src
/home/n/Code/claude/coga/.venv/bin/python -m pytest` from the worktree.

## Decisions (attended, 2026-09-21)

- Human approved: fix upstream; cross-repo line names the owning repo root and
  the by-hand git cleanup there instead of a `coga retire` that cannot work
  from either side; worklist format and discharge rule untouched.
- Multiply-side doc edits (`coga/workflows/autoclose-merged/sweep.md`,
  `coga/recurring/autoclose-merged/ticket.md` step 6) are committed directly
  on multiply `main` locally, no push.
- The hand-written cross-repo caveats on the recurring blackboard stay (they
  describe entries recorded before the fix, which the per-run report never
  re-emits); one line added saying future runs annotate this themselves.

## Findings (2026-09-21, implement)

- Confirmed against `run-log.md`: the 2026-09-10 run named
  `coga retire autofix/escalate-watchdog-paused-recurring-tasks-instead-o` for
  worktree `/tmp/coga-watchdog-pauses`, a linked worktree of
  `/home/n/Code/claude/coga` (FastJVM/coga), not of this repo. Not transient,
  not already fixed: upstream `coga.autoclose` (`ClosedTicket.retire_command`,
  `render_retire_report`, `render_retire_summary`) still names the command
  from `branch:`/`worktree:` alone, with no repo check.
- Landscape moved since the ticket was written: upstream
  `persist-autoclose-retire-follow-ups` landed (`coga.retire_worklist`,
  `coga/recurring/<name>/retires.md`). The worklist line format is
  `slug — branch, worktree, recorded`; its discharge rule (dir gone AND branch
  not local to the ticket repo) is unchanged by this ticket. Only the per-run
  report and Slack summary wording change here.
- The fix lives upstream in FastJVM/coga (package-backed recipe), same layout
  as PR #778: feature worktree of `/home/n/Code/claude/coga`, ticket here.
- **Ticket item 3's suggested wording is itself unrunnable.** `coga retire
  <slug>` resolves the task in the *current* repo (`commands/retire.py`:
  `root = git._toplevel(ref.ticket_path)`), so from the owning checkout the
  slug does not exist, and from the ticket's repo
  `branchcleanup._is_linked_worktree_of` fails (common git dir differs) and
  the worktree is preserved. For a cross-repo checkout no `coga retire`
  invocation disposes of it; the honest follow-up names the owning repo root
  (first `worktree` of `git -C <path> worktree list --porcelain`) and the
  by-hand `git -C <owner> worktree remove <path>` / `branch -d <branch>`.
- Same-repo proof to reuse: compare `git rev-parse --path-format=absolute
  --git-common-dir` of the recorded worktree with that of the ticket repo's
  git root (`autoclose._worklist_root` already computes the latter).
- Multiply-side copies of `coga/workflows/autoclose-merged/sweep.md` and
  `coga/recurring/autoclose-merged/ticket.md` have already drifted from the
  upstream packaged templates (agent-backed `coga run autoclose` here vs
  script-backed `ticket.py` upstream); only their step-6 wording is in scope.

## Implementation (2026-09-21)

Upstream, one commit on `fix/retire-followup-owner` (`/tmp/coga-retire-owner`,
rebased onto `origin/main` at `fc15f1a00`; 8 files, +426/-20):

- `src/coga/autoclose.py`: new `CheckoutHome` + `locate_checkout(root,
  worktree)` → `same` / `other(owner)` / `gone` / `untracked` / `unknown`.
  Same-repo test is the `--git-common-dir` comparison
  `branchcleanup._is_linked_worktree_of` makes; owner is the first entry of
  `git worktree list --porcelain`. `render_retire_report` /
  `render_retire_summary` take a `homes` mapping; `_followup_line` renders
  per kind. `_report_retire_followups` computes the root once (shared with the
  worklist reconcile) and judges every pending item against it. `unknown`
  (no worktree recorded, or ticket repo not a git repo) keeps today's exact
  line, so the existing non-git test fixtures are unaffected.
- `retires.md` line format and discharge rule untouched (out of scope).
- Docs, live + packaged: `coga/autoclose/sweep` SKILL.md,
  `workflows/autoclose-merged/sweep.md`, `recurring/autoclose-merged/ticket.md`.
- Tests: 8 added in `tests/test_autoclose.py` (real `git init` repos in
  `tmp_path`, one end-to-end recipe run). Full suite
  `PYTHONPATH=src .venv/bin/python -m pytest`: **2664 passed**, 1 deselected
  (see below). `example/` `coga validate --json`: no issues. Smoke on the
  real case: `locate_checkout(/home/n/Code/multiply, /tmp/coga-retire-owner)`
  → `other`, owner `/home/n/Code/claude/coga`; `/tmp/multiply-receiver` → `gone`.

Multiply side, committed on `main` locally (`bd417bf`, no push):
`coga/workflows/autoclose-merged/sweep.md` and
`coga/recurring/autoclose-merged/ticket.md` step 6 updated; blackboard caveats
kept with a note that future runs annotate ownership themselves.

## Adjacent findings (not fixed here)

- Pre-existing upstream test failure on clean `main` (reproduced at
  `76785989b` with my change stashed):
  `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical` —
  `coga/contexts/coga/extension-model/SKILL.md` has drifted from its packaged
  twin. Unrelated to this change; deselected for the full run.
- The worklist discharge rule judges `branch:` against the ticket repo only,
  so a cross-repo entry drops as soon as its worktree dir is gone while the
  branch survives in the owning repo — the "Debt the worklist cannot hold"
  section on the recurring blackboard. Extending the worklist line with the
  owner would fix it; deliberately out of scope for this text-only ticket.

## Self-QA (2026-09-21, attended)

Both passes ran against `fix/retire-followup-owner` in `/tmp/coga-retire-owner`
and **returned** before anything was bumped: `/code-review` (default effort,
forked, 3 findings) and `/simplify` (4 review agents, reuse / simplification /
efficiency / altitude). I also read the diff by hand against `retire.py` and
`branchcleanup.py` to probe the rationale each follow-up line gives.

`/code-review` found three "line names a command that won't run" bugs: an
independent clone rendered as `other` with itself as owner (`git -C X worktree
remove X`); a relative `worktree:` pasted unresolved into the cross-repo
command; and primary checkout / subdir / symlink / no-`branch:` rendered as
`same` → plain `coga retire` that retire refuses. `/simplify`'s altitude
angle showed the first and third are one bug: `locate_checkout` had copied half
of `branchcleanup._is_linked_worktree_of` (dropped `git_dir != common_dir`)
because `autoclose` cannot import `branchcleanup` (cycle).

Fix shape, human-approved (option A): the proof now lives once in
`coga.git.worktree_relation` (`WorktreeRelation` enum + `WorktreeHome`),
called by both `branchcleanup.remove_ticket_worktree` and the sweep;
`branchcleanup._git_path` deleted. `CheckoutHome` carries the resolved `path`,
`untracked` became `preserved` with retire's `reason` (not a worktree / own
checkout / running checkout / independent clone / symlink / no `branch:`), the
verdict rides on `ClosedTicket.home` (no `homes` side table; renderers back to
their original signatures), the gone line hedges the branch delete, and the
docs say the outcome once per surface. Commit `ffee12f72` on the branch.

Verified: `PYTHONPATH=src .venv/bin/python -m pytest` **2665 passed**, 1
deselected (the pre-existing `extension-model` twin drift on `main`, unrelated);
`example/` `coga validate --json` no issues (needs `env -u SLACK_WEBHOOK_URL`
in this shell); live/packaged twins byte-identical; smoke on the real case:
`/tmp/coga-retire-owner` → `other` owned by `/home/n/Code/claude/coga`,
`/tmp/multiply-receiver` → `gone`, `/home/n/Code/multiply` → `preserved` (the
checkout retire runs from), `/home/n/Code/claude/coga` → `preserved`
(independent checkout). No terminal/TTY surface in this diff.

Skipped, for the PR reviewer or a follow-up: `_followup_line`'s prose still
restates what `remove_ticket_worktree` will do from 900 lines away (the
altitude review's "split retire's read-only prefix into a shared verdict"
idea — bigger than this ticket); test `_git`/`_init_repo` helpers duplicate
the per-module convention in `tests/`; `is_linked_worktree` could be
expressed through `worktree_relation` but was left untouched. `origin/main`
has moved since the rebase (Dream ran 12:24); the PR step may need a rebase.

## Publication (2026-09-21, attended)

- Branch was 2 ahead / 27 behind `origin/main` (Dream had run); rebased
  `fix/retire-followup-owner` in `/tmp/coga-retire-owner` onto `origin/main`
  at `35160d0b2`. `git range-diff` shows both patches unchanged (`=`); now
  `77812c6ad` + `7db37a31f`. `git diff --check origin/main...HEAD` clean.
- Post-rebase full suite: **2665 passed, 1 failed** — the failure is the same
  pre-existing `tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
  (`extension-model` twin drift already on `main`; that file is not in this
  diff). Nothing new.
- `coga open-pr` from this Multiply checkout (cross-repo worktree, as #778)
  opened https://github.com/FastJVM/coga/pull/870 — open, non-draft, base
  `main`, head `7db37a31f`, GitHub reports `MERGEABLE`. Feature worktree is
  clean and in sync with `origin/fix/retire-followup-owner`.
- Left for the reviewer: the items under `## Self-QA` "Skipped".
