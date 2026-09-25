---
title: Keep cross-clone retire follow-ups from being discharged silently
status: in_progress
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
step: 1 (implement)
---

## Description

## What broke

The 2026-09-21 evening autoclose sweep ran clean (`coga run autoclose` exited 0, 7 closed, 7 recorded, 9 open in `retires.md`, ticket `done`), but the agent had to do a by-hand step the durable worklist is supposed to make unnecessary: mirror one entry onto the parent blackboard because the worklist is about to lose it.

`coga/recurring/autoclose-merged/retires.md` is documented as "a record of debt" that is only dropped "once both its worktree directory and its local branch are gone". The discharge rule, however, checks `branch:` only against the local branches of the clone the sweep runs from. This recurring task fires from two clones of the same repo (`/home/n/Code/multiply` and `/home/n/Code/codex/multiply`). An entry whose worktree directory has vanished but whose branch survives in the *other* clone is judged "branch gone" and silently discharged — the debt is deleted from the one place meant to hold it, with no output saying so.

## Evidence

From the run's blackboard:

> `2a-portable-telemetry-client-extraction` — branch `refactor/portable-telemetry` only in `/home/n/Code/codex/multiply`; the next sweep from this clone will drop its worklist line, so the by-hand cleanup is recorded on the parent.

and its Gotchas:

> The sweep's `retires.md` discharge rule only sees branches in the clone it runs from. […] a follow-up whose branch lives in the other clone is dropped from the worklist as soon as its worktree directory vanishes, so cross-clone entries must be mirrored on the parent blackboard before that happens.

The parent blackboard (`coga/recurring/autoclose-merged/ticket.md`, section "Debt the worklist cannot hold (branch-only, other clones)") already carries such a hand-mirrored entry for exactly this reason. Two more entries in `retires.md` today record worktrees under `/home/n/Code/codex/multiply-*` (`2-startup-upgrade-probe`, `3-manual-hook-updates`) and will hit the same rule once their directories are removed.

This is a zero-exit failure: a job that silently un-records work it was supposed to keep, forcing a human/agent workaround on every cross-clone entry.

## Not covered by the open tickets

`autofix/name-cross-repo-retire-follow-ups-with-the-repo-th` (PR FastJVM/coga#870) changes only the *per-run report wording* for cross-repo checkouts. Its blackboard lists this exact discharge behaviour under "Adjacent findings (not fixed here)": "The worklist discharge rule judges `branch:` against the ticket repo only, so a cross-repo entry drops as soon as its worktree dir is gone while the branch survives in the owning repo […] deliberately out of scope for this text-only ticket." `autofix/make-dream-block-instead-of-done-when-its-retro-ch` is unrelated.

## Where it lives

Upstream FastJVM/coga (package-backed; primary source checkout `/home/n/Code/claude/coga`, same layout as PRs #778/#870):

- `src/coga/retire_worklist.py` — `local_branches(root)`, `is_discharged(entry, root=, branches=)`, `reconcile_worklist(...)`. `is_discharged` treats `entry.branch not in branches` as "branch gone" using only the ticket repo's branch list.
- `src/coga/autoclose.py` — `_report_retire_followups` / `_worklist_root`, which drive the reconcile. PR #870 adds `locate_checkout` / `coga.git.worktree_relation`, which already resolves a worktree's owning repo root at record time; that verdict is currently not persisted in the worklist line.
- Repo-side docs that state the discharge contract: `coga/recurring/autoclose-merged/retires.md` header, `coga/workflows/autoclose-merged/sweep.md`, the `coga/autoclose/sweep` skill (line format section), and the "Debt the worklist cannot hold" section of `coga/recurring/autoclose-merged/ticket.md`.

## What a fix has to do

1. Make the worklist hold the information the discharge rule needs. Either record the owning repo root on the line at record time (extending the `slug — branch, worktree, recorded` format with an `owner` field, using the resolution PR #870 introduces) or, at reconcile time, probe the branch in the repo that owns the recorded worktree rather than only in `root`. The `merge=union` line format and the parse regex in `retire_worklist.py` must keep accepting existing lines without an owner.
2. Change `is_discharged` so "branch gone" is only concluded for the repo that owns the checkout. When the owner is another clone that cannot be reached from this run (path missing, not a git repo), treat the branch as unknown — the docstring already says an unknown branch keeps its entry — instead of discharging.
3. When an entry is kept for that reason, say so in the run report (one line naming the owning clone and the by-hand `git -C <owner> branch -d <branch>`), so the agent no longer has to mirror it on the parent blackboard.
4. Keep the sweep non-destructive and exiting zero; only the worklist's keep/drop decision and report text change.
5. Add tests in `tests/test_retire_worklist.py` / `tests/test_autoclose.py` with two real `git init` repos: worktree dir removed, branch present only in the non-ticket repo → entry retained; branch deleted there too → entry discharged; owner path missing → retained.
6. Update the docs listed above so the stated discharge rule matches, and retire the "Debt the worklist cannot hold" workaround section on the recurring blackboard once the worklist can hold it.

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

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `active`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement handoff — 2026-09-24

- Human approved persisting the owning clone in each worklist entry, checking
  branches there, and reporting retained debt with the owning-clone cleanup
  command. Keep old lines readable; unresolved ownership retains debt, with
  manual ownership backfill potentially needed for old entries.
- Verified the attached `run-log.md` corroborates the cross-clone loss.
  `src/coga/retire_worklist.py` plus `is_discharged` currently checks only the
  caller's branch set; `src/coga/autoclose.py` plus `_report_retire_followups`
  constructs entries without persisting an owner. No implementation yet.
- This session's checkout is occupied by `retired-ticket-recovery`, with
  that other ticket and the audit log dirty. Left its branch and state in place.
- Prepared control checkout: `/home/n/Code/codex/coga-control`, branch `main`.
  Seeded local config with `code/implement/seed_local_config.py`; explicitly
  fetched `origin main` and fast-forwarded. Before this handoff, the published
  ticket there was byte-identical to this session's live ticket.
- Per the occupied-primary rule in `code/implement`, relaunch from that control
  checkout, then create a separate feature checkout for implementation. No
  feature branch or `## Dev` record yet; no bump until implementation completes.
- Relaunch: `cd /home/n/Code/codex/coga-control && coga launch autofix/keep-cross-clone-retire-follow-ups-from-being-disc`.
