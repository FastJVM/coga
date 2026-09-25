---
title: Document how to recover a retired ticket's body from git, including pre-rename
  paths
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
agent: claude
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `gap` findings with no open owner. Two findings about the same missing recipe: how to read a retired/deleted ticket's body back from git, including tickets deleted before the `relay-os/` → `coga/` rename, which a `coga/tasks/`-scoped history search silently misses. Decide the owning surface (the recovery recipe in `coga/tasks/v2/README.md`, `coga/tickets` (the ticket-file contract, formerly part of `coga/architecture`), and/or `bootstrap/ticket`'s citation guidance) and add it once.

**F36 — No context or skill says how to read a retired ticket's body back from Git**  
(Dream 2026-W39 Phase 2, shard ks-19; class `gap`; target `coga/contexts/coga/architecture/SKILL.md`)

Tickets repeatedly need the body of a ticket that `coga retire` (or an older cleanup) already deleted, and each rediscovers the recipe on its own: `triage-five-review-comments-that-merged-unanswered` (done) was told "recover the source ticket from Git history if it has been retired" and used `git show 6c305673^:coga/tasks/verify-the-pr-review-comment-loop-once-the-review.md`; `the-ticket-interview-never-asks-what-done-means` (in_progress) records "the file was deleted in `ffb0a383` — it is not on disk. Recovered at design time with `git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md`"; `adjudicate-parked-and-active-tickets-whose-premise` (done) notes wording "reachable only through git history" and had to recover accepted interview prompts the same way. The only written recipe is in `coga/tasks/v2/README.md` (`git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` to find the deleting commit, then `git show <commit>^:<path>`), scoped to the parked-draft premise check — it is not a context or skill and does not compose into launch prompts for ordinary tickets. The closest knowledge text, `coga/contexts/coga/architecture/SKILL.md` (~line 41, "renaming a task orphans its whole prior history under the retired tag ... grep the retired tag when reconstructing the trail"), covers only the `coga/log.md` trail, not the deleted ticket file; `dev/code` "Who retires the checkout" says retire acts "at the lifecycle event where the ticket still exists" without saying where the body goes afterwards. Grep of `coga/contexts/**/SKILL.md` and repo-authored `coga/skills/**` for `git show`/`--diff-filter=D`/"recover" against tasks found no such guidance. Proposed: one sentence plus the two-command recipe beside the architecture context's retired-tag passage (or in `dev/code` next to "Who retires the checkout"), stating that a retired ticket's body and blackboard survive only as a Git blob, that `coga show <slug>` will not find it, and that the `v2/README.md` premise check should link to that owner rather than restate it. No open ticket owns this: task-title grep for retired/recover/git-history found only `preserve-edits-during-released-claim-recovery`, which is unrelated (launch admission).

**F43 — Ticket-history recovery recipe misses tickets deleted before the `relay-os` → `coga` rename**  
(Dream 2026-W39 Phase 2, shard ks-22; class `gap`; target `coga/tasks/v2/README.md (the `git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*'` recovery recipe; same gap in `bootstrap/ticket`'s citation guidance)`)

Two independent tickets rediscovered that the task tree was `relay-os/tasks/` before commit `d0645a197` ("Rename relay to coga (full rebrand)", PR #454), so any history search scoped to `coga/tasks/` silently misses tickets deleted before the rename. `coga/tasks/adjudicate-the-eight-premise-dead-v2-drafts.md` (Context, "Recoverable autotrigger background") found six of seven cited slugs absent until it searched the old path: "The four retired hazard tickets were deleted under `relay-os/tasks/`, so searching only `coga/tasks/` history misses them. All four source bodies were recovered with `git show <deletion>^:relay-os/tasks/<slug>/ticket.md`" (commits `d7086ecd`, `078dd705`, `2584de1d`, `c008c23b`). `coga/tasks/simplify-ticket-format.md` (Context, line ~540) independently had to run its `watchers` history search "under both `coga/tasks/` and the former `relay-os/tasks/`". `coga/tasks/v2/README.md` lines 76-78 carry the only written recipe for recovering a dangling citation and it names only `'coga/tasks/<slug>*'`; `docs/migrating-to-coga.md` records the rename for operators but says nothing about history recovery, and no context or skill under `coga/contexts/`, `coga/skills/coga`, `coga/skills/code`, or `coga/skills/bootstrap` mentions `relay-os/tasks` at all (grep empty). Proposed change: extend the README recipe (and the `bootstrap/ticket` citation guidance that points to it) with one sentence — search both pathspecs, e.g. `-- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'`, because deletions before `d0645a197` live under the old tree. Owner search: grep of every task file for `pre-rename`/`relay-os/tasks` finds only historical mentions (`launch-activates-before-preflight` done, `four-parked-tickets-carry-premises-that-have-since` done, `no-durable-runbook-covers-running-coga-headless` canceled); no open ticket proposes fixing the recipe, and the in_progress `adjudicate-the-eight-premise-dead-v2-drafts` only inlines the recovered bodies into the autotrigger draft, not the README.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/893
branch: retired-ticket-recovery
worktree: /home/n/Code/codex/coga

Single-checkout layout. The owner changed course from the control-checkout
plan: `dream-under-codex` (PR #891) was confirmed pushed (local ==
origin), its task/log state was published, `../coga-control` was removed, and
this primary checkout switched to `main` and branched here.

## Implementation (2026-09-24)

Commit 375935944, rebased on origin/main 970806606.

- `coga/tickets` `## Where tasks live and how they are named` (live + packaged
  twin): new paragraph plus recipe
  `git log origin/main --diff-filter=D --name-only -- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'`
  then `git show <commit>^:<path>`.
  - Deviations from the plan, both from testing on real slugs:
    - It searches `origin/main`, not `--all`. `--all` surfaced an off-main
      "Refresh coga state after launch" deletion of
      `improve-prompt-for-relay-ticket` ahead of the real `ffb0a3835`.
    - "Newest hit = retirement; older hits = rename or `.md` ↔ `<slug>/`
      conversion" replaced the planned "`— deleted` subject" rule, because
      Retro deletes tickets inside its "New context: …" PR commits, not in
      `— deleted` commits.
  - Also notes that old directory-form tasks kept a sibling `blackboard.md`.
  - Verified on `detect-recurring-runs-that-mark-done-without-advan`
    (pre-rename, `d7086ecde`) and on `improve-prompt-for-relay-ticket`.
- `coga/tasks/v2/README.md` premise check item 3: the inline recipe is
  replaced with a link to the `coga/tickets` anchor.
- `bootstrap/ticket` (packaged only; there is no live twin under
  `coga/skills/bootstrap/`): a paragraph after "Citing code in `## Context`"
  says to copy the cited ticket's substance, cite it for provenance only, and
  recover a retired source with the `coga/tickets` recipe.
- Tests: `.venv/bin/python -m pytest` gave 2932 passed, 1 failed. The failure
  is `test_live_and_packaged_copies_stay_identical`, on
  `coga/recurring/phone-home/ticket.md` twin drift. It is pre-existing and
  already noted in PR #892's log line; this branch doesn't touch it.

## Plan (agreed with the owner)

- Single owner is `coga/tickets` (`docs/contexts/coga/tickets/SKILL.md`, plus
  its packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md`).
  In `## Where tasks live and how they are named`, right after the sentence
  "moving a task orphans its history under the old tag", add a short
  paragraph saying:
  - A retired or deleted ticket (`coga retire`, `delete-task`, Retro) keeps its
    body and blackboard only as a git blob, so `coga show <slug>` won't find it.
  - Recipe: `git log --all --diff-filter=D --name-only -- 'coga/tasks/<slug>*' 'relay-os/tasks/<slug>*'`,
    then `git show <commit>^:<path>`.
  - The task tree was `relay-os/tasks/` before d0645a197 ("Rename relay to
    coga", #454), so search both pathspecs.
  - If the relay-os pathspec only hits d0645a197, the file was renamed there,
    not retired. Search the coga path for the later deletion.
- `coga/tasks/v2/README.md` premise check item 3: replace the inline recipe
  with a link to `coga/tickets`.
- `bootstrap/ticket` (packaged `bootstrap/skills/bootstrap/ticket/SKILL.md`
  plus a live twin if one exists): add one pointer line to the citation
  guidance about recovering a cited ticket that has been retired, linking to
  `coga/tickets`.
- Run `python -m pytest tests/test_packaging.py` and the full suite.

## Adjacent finding (not fixed here)

- `code/implement/seed_local_config.py` does `import tomllib` at module top.
  So on Python < 3.11 (for example the system `python3` 3.9.12 here) it fails
  with ModuleNotFoundError before reaching the documented fallback that
  "re-runs itself under the `coga` console script's interpreter". The skill's
  claim that "any `python` works" is false on 3.9.
  Workaround: run it with the interpreter from the shebang of `which coga`.
  No follow-up ticket exists yet.


## Peer review

- `codex review --base main` returned: no actionable defects found; no
  must-fix edits were needed.
- `git fetch origin main` and `git rebase FETCH_HEAD` completed cleanly onto
  `346ea8d0a`. The canonical `coga/tickets` and packaged twin still match
  byte-for-byte (`cmp`); `git diff --check` passed.
- Executed the documented history search and `git show` for
  `detect-recurring-runs-that-mark-done-without-advan` at `d7086ecde^`
  (both `relay-os/tasks/.../ticket.md` and sibling `blackboard.md`) and
  `improve-prompt-for-relay-ticket` at `ffb0a3835^` (`coga/tasks/...md`).
  All bodies were recovered successfully. This is a documentation-only
  change with no terminal or rendered interaction to exercise.
- Review tool ran `.venv/bin/python -m pytest tests/test_packaging.py -q`:
  22 passed, 1 failed. The failure is the existing phone-home twin drift;
  both files are unchanged from `origin/main`, whose blobs also differ.

- Post-rebase `.venv/bin/python -m pytest`: 2932 passed, 1 failed in
  189.63s; the sole failure is the same pre-existing phone-home twin drift.

## PR

Document recovery of retired ticket bodies and blackboards in `coga/tickets`,
including deletions under the former `relay-os/tasks/` tree and separate
historical blackboards. Point the parked-ticket premise check and ticket
citation guidance at that owner; keep its packaged context twin synchronized.

Test plan: verified recovery of pre-rename and current-path tickets with the
documented Git commands; packaging checks: 22 passed, 1 pre-existing failure
from unchanged phone-home twin drift; post-rebase `.venv/bin/python -m pytest`: 2932 passed, 1 failed (the same baseline mismatch).

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `document-how-to-recover-a-retired-ticket-s-body-fr`
Recorded: 2026-09-25T02:24:10+00:00

    Branch 'retired-ticket-recovery' is not safe to publish. current branch does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Overlapping paths: coga/log.md. Reconcile it and relaunch, or `coga block --task document-how-to-recover-a-retired-ticket-s-body-fr`.
