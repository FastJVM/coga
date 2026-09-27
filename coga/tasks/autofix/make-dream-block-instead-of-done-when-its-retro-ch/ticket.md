---
title: Make Dream block instead of done when its Retro checkout can't land
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
step: 3 (pr)
---

## Description

## What broke

The `recurring/dream` run of 2026-08-31 finished with work it could not land, marked its ticket `done` anyway, and the sweep therefore reported `problems: 0`. Two `coga/log.md` audit-trail lines and a `/tmp` worktree are still stranded on this machine as a result.

From the dream blackboard's `### human-needed` section:

> **Two audit-trail lines are unpushed.** `coga/log.md` lines recording the PR #33 and #34 Slack posts exist only on local branch `dream/retro-2026-W36-1788212557` (worktree `/tmp/dream-retro-2026-W36`). Both `git cherry-pick` and `git push` of that branch were denied by the permission classifier, so Dream could not land them. **The worktree and branch were deliberately preserved rather than removed** — deleting them would destroy the lines.

Verified in the repo as of this sweep:

- `git worktree list` still shows `/tmp/dream-retro-2026-W36  d420b30 [dream/retro-2026-W36-1788212557]`.
- `git log --oneline main..dream/retro-2026-W36-1788212557` → two commits (`d420b30`, `3e4c60a`), both `Sync coga state`.
- `git diff main...dream/retro-2026-W36-1788212557 --stat` → `coga/log.md | 2 ++`. The audit lines are real and are only there.

## Why this is a defect and not just a human-needed note

`coga/recurring/dream/ticket.md:214-221` is explicit about this exact case:

> After the subagent returns, verify every PR branch is pushed, every direct delete is present on the remote control branch, and the isolated checkout is clean. […] **If durability or cleanup cannot be verified, preserve the paths and surface a blocker.**

Dream did the first half (preserved the paths) and skipped the second (surface a blocker). It marked itself `done` and demoted the failure to prose in a blackboard that a later Dream run is designed to retire. Because the ticket status is `done` and the recipe exited 0, the sweep's problem count is 0 and nothing routes anywhere — the failure is invisible to every downstream consumer. Compounding it, `recurring/branch-sweep` will now see `dream/retro-2026-W36-*` forever as `skipped-worktree-pinned` (it already lists six such branches, four in `/tmp`), so the leak is self-perpetuating and silent.

## Where it lives

- `coga/recurring/dream/ticket.md` — the durability/cleanup verification contract at lines ~214-221, and the Phase 6 disposition + final status mark. The template states the blocker requirement but does not make it binding on the terminal status: nothing forbids marking `done` while preserved-unlanded paths exist.
- The Retro-pass delegation section (~lines 188-213) is where the isolated checkout writes `coga/log.md`. Dream's audit lines are append-only history for the *repo*, but they are produced inside a temporary branch whose only exit is a push or cherry-pick the sandbox may refuse — a design that has no fallback.
- `coga/log.md` write path / `coga` sync: whatever appends `Sync coga state` commits in the isolated checkout.

## What a fix has to do

1. **Make the contract binding.** If the isolated checkout is preserved because durability or cleanup could not be verified, Dream must end blocked (`coga block --task recurring/dream --reason ...` naming the branch, worktree path and the unlanded paths), not `done`. Marking `done` with preserved paths should be impossible, not merely discouraged.
2. **Give the sweep something to see.** A recurring task left blocked must count toward the sweep's `problems:` line, so `problems: 0` stops being true when a run stranded work. (Note the related environment gap the same run reported: `[notification.slack].important_webhook` is unconfigured — `coga/coga.toml:75-90` has it commented out — so failure alerts cannot route even once they are raised. Out of scope here, but the alerting path is dead until it is set.)
3. **Remove the single point of failure for audit lines.** Dream's `coga/log.md` history should not depend on a push from a temporary branch succeeding. Either write the repo-global log lines from Dream's own (primary) checkout after the subagent returns, or define an explicit reconciliation the next sync performs for a preserved Dream branch. A denied push is a foreseeable sandbox outcome, not an exceptional one.
4. **Close out the current instance** as part of the fix: land the two commits from `dream/retro-2026-W36-1788212557` onto `main`, then `git worktree remove /tmp/dream-retro-2026-W36 && git branch -D dream/retro-2026-W36-1788212557`. Do not delete either before the two `coga/log.md` lines exist on `main`.

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

## Dev

pr: https://github.com/FastJVM/coga/pull/907
branch: dream-block-on-stranded-retro

Plan (agreed with owner 2026-09-27): template-only fix in `coga/recurring/dream/ticket.md` + packaged twin.
- Phase 4 delegation: subagent must not run `coga slack` / log-writing commands in the isolated checkout; Dream posts FYIs from its own checkout.
- Replace "surface a blocker" with an exact `coga block` naming preserved branch/checkout/run dir and unlanded paths.
- Final status: `coga mark done` only when nothing was preserved; otherwise end with that `coga block`.
- Item 2 already satisfied in core (`recurring_runner._task_outcome`: blocked → `unfinished` → problem); add agent-blocked regression test.
- Item 4 (stranded `dream/retro-2026-W36-*` + `/tmp/dream-retro-2026-W36`) lives in multiply, absent here — out of scope; manual close-out there.

## Implement handoff (2026-09-27)

Commit `fd9b8e162` on `dream-block-on-stranded-retro` (pushed, rebased on origin/main). No PR yet.

Changed (`coga/recurring/dream/ticket.md` + byte-identical packaged twin):
- Phase 4 delegation: subagent must not run `coga slack`/log-writing commands in the isolated checkout; Dream posts PR FYIs via `coga slack --task <this-dream-task>` from its own checkout (fix item 3 — root cause: only `coga slack` → `logfile.append_log` wrote those lines; retro skill never asked for it).
- Durability check now fetches and requires `git log <remote>/<control-branch>..HEAD` empty (unpushed temp-branch commits = unverified).
- "surface a blocker" replaced: preserve paths, record `### Stranded Retro work` (branch, path, run dir, commits, unlanded paths, land/remove commands).
- `### Slack` closing rule: stranded work → `coga block` with a named reason, never `coga mark done`; attended session asks the human to land it first (reconciles with base-prompt Session conduct).
- Item 2 was already true in core (`recurring_runner._task_outcome`: blocked → `unfinished` → `is_problem`); added `test_a_blocked_agent_run_counts_as_a_problem` (supervisor reports `kind="done"` for a blocked agent session).
- Added `test_dream_blocks_instead_of_done_when_retro_work_is_stranded` in `tests/test_dream_worker_templates.py`.

Verification: `python -m pytest` → 2947 passed; targeted re-run after rebase → 108 passed.

Out of scope / follow-up: item 4 (land `dream/retro-2026-W36-1788212557` two `coga/log.md` commits, then `git worktree remove /tmp/dream-retro-2026-W36 && git branch -D ...`) must be done by a human in the multiply repo; neither exists here. `[notification.slack].important_webhook` gap also noted as out of scope in the ticket.
Decision: enforcement is prompt-level only (owner accepted the tradeoff; code-level detection of Dream temp checkouts would put Dream-only logic in core).

## Self-QA (2026-09-27)

Review form: `/code-review` (Skill, default effort, forked) against `main` — **returned** with 2 findings, both confirmed and fixed; plus my own read of the diff. `/simplify` (4 agents: reuse, simplification, efficiency, altitude) — **all returned**; fixes applied. No review is in flight.

Fixed in `8c792fd2b` (pushed on `dream-block-on-stranded-retro`):
- Must-fix: "no uncommitted changes" check falsely blocked healthy runs — `coga delete --keep-control-checkout` pushes via `git.publish(fast_forward=False)` and leaves the landed deletion in the worktree. Retro's Isolation boundary now owns a "nothing unlanded" check (`git log <remote>/<control>..HEAD` empty; no untracked; one `git diff --name-only <remote>/<control> -- <listed paths>` empty); Dream cites it; Retro step 9 wording aligned.
- Should-fix: Retro step 12 told the subagent to post Slack FYIs (implement handoff's "retro skill never asked for it" was wrong). Step 12 is now "Hand PR FYIs to the caller" (`pr` receipts in `progress.md`); Dream keeps only its caller-side half.
- Simplify: shorter `coga block` reason, dropped duplicated closing sentence, `RETRO_SKILL` test constant, trimmed wording-guard assertions.
- Owning topic `coga/dream` (Results and safety, both twins) now records stranded → `blocked`.
- Skipped: module-level cached `_norm` test helper (pre-existing pattern, follow-up at most).

No terminal/TTY surface touched; no hand sweep needed.
Verification: `python -m pytest` → 2948 passed + 1 failure (`test_retro_skill_template` raw-text wrap) fixed, affected files re-run 47 passed; `coga validate --json` ok.
