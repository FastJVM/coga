---
title: Verify Dream under codex on the real repo (first period after merge)
status: in_progress
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 2 (human-executes)
agent: claude
---

## Description

This is the confirmation run for `make-dream-run-correctly-under-codex`,
done on the real repo once that ticket's PR merges. That ticket's
implement step already got a codex Dream run clean in the scratch repo
`FastJVM/coga-dream-scratch`. This run confirms the same result on
`FastJVM/coga`.

Use the first Dream period after the merge, not a fixed week. The
scheduled sweep may already run an earlier period under claude. The owner:
1. applies the `.codex/config.toml` grant recipe from `coga/codebase`
   (`## Sandbox and cross-machine dev loop`) to their primary checkout and
   trusts it in codex;
2. runs `coga dream --agent codex` attended, before the sweep takes that
   period.

**Done** when the run passes the preflight and finishes all six phases, and
it routes findings to real PRs, draft tickets, and markers. Its run record
must show `usage_status: ok`. Its summary goes on this blackboard, next to
the W39 claude baseline and the scratch run recorded on the parent ticket.
The `verify-read-only` step lists every new gap as a proposed ticket with
evidence; the owner files each one or rejects it. No gap is left only on the
blackboard.

Do not launch before `make-dream-run-correctly-under-codex` has merged.

## Context

- **Parent ticket:** `make-dream-run-correctly-under-codex`. The run/fix
  loop log on its blackboard shows what the scratch runs hit and how each
  was fixed.
- **W39 claude baseline (2026-09-21):**
  - validate-drift: 50 issues, 3 class drafts;
  - 4 knowledge PRs and 7 deletes;
  - 6 stale/drift PRs;
  - 12 drafts;
  - about 1 hour and 94 agent turns.
- The grant applies to every codex session in the repo; the owner accepted
  that on 2026-09-22.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Brief (brief-and-hand-off, 2026-10-07, read-only)

**Goal.** Run one attended codex Dream on `FastJVM/coga` for the first
period that has not been serviced since #891 merged, and confirm it matches
the clean scratch run (parent ticket, iteration 2).

**Which period: W42, not W40.** #891 merged 2026-09-25 (released in coga
0.4.0, which is the installed `~/.local/bin/coga`). The scheduled sweep then
took both available periods under claude:
- W40 on 2026-09-29: 10 PRs (#920–#929), 11 drafts, 9 deletes, 119 turns;
- W41 on 2026-10-05: 8 PRs (#953–#960), 3 drafts, 8 deletes, 80 turns.

So the first open period is **2026-W42**, which starts Mon 2026-10-12. The
slug still says w40; the body says "first period after merge, not a fixed
week", so W42 qualifies. No cron runs the sweep: the only crontab line is a
Monday 09:00 `uv tool upgrade coga`. The owner has been starting
`coga recurring` by hand around 11:26 on Mondays. The owner just needs to
run Dream before running that week's sweep.

**State already in place (checked read-only):**
- `/home/n/Code/coga/.codex/config.toml` matches the recipe in
  `coga/testing` § "Codex sandbox grant". It has
  `writable_roots = ["/home/n/Code/coga/.git"]`, which is the
  `--git-common-dir` output. It is gitignored. Note: the ticket points at
  `coga/codebase` `## Sandbox and cross-machine dev loop`; that section has
  moved to `coga/testing`.
- `~/.codex/config.toml` already marks `/home/n/Code/coga` as trusted.
- codex-cli is 0.160.1; the scratch runs used 0.155.1.

**Ordered steps (owner):**
1. On or after Mon 2026-10-12, and **before** any `coga recurring` that week:
   `cd /home/n/Code/coga`, be on `main` (clean, pulled), and confirm
   `cat .codex/config.toml` still shows the grant. Run from this checkout
   on `main`. On another branch, the named launch relays into a different
   worktree on `main` (`coga/internals/recurring-control`), and that worktree
   may not have the gitignored grant. W40 ran from `~/Code/claude/coga`; if
   you use that checkout instead, apply the grant there with its own
   common-dir path and trust it.
2. `coga dream --agent codex` and stay attended. Watch the
   agent-capability preflight line first. If it fails, stop and record why.
3. Let it finish all six phases and close the task. Then run the normal
   `coga recurring` sweep. Dream is already serviced for W42, so the sweep
   skips it.
4. Relaunch this ticket (it goes to `verify-read-only`).

**Irreversible action.** Step 2 writes to the real repo, under the codex
grant (network on, `.git` writable). It pushes branches, opens real PRs on
`FastJVM/coga`, direct-deletes period tickets on `main` (Retro), creates
draft tickets, posts to Slack, and marks W42 as serviced. That last one
means there is no claude W42 run to compare against. The grant also applies
to every other codex session in this checkout (accepted 2026-09-22).

**Done check (verify-read-only step):**
- the preflight passed, and all six phases (preflight, validate-drift,
  knowledge scan, contract audit, Retro, execute/disposition) report results;
- every reported PR exists on `FastJVM/coga`, and every draft and marker
  exists;
- the `recurring/dream` W42 run record in `coga/log.md` shows
  `agent: codex` and `usage_status: ok`, with session = the parent id;
- the summary goes here, next to the W39 claude baseline and scratch
  iteration 2 (see the table on the parent ticket). W40 and W41 under claude
  are extra comparison points;
- watch for the known scratch issues. The knowledge scan went `partial`
  because of oversized owner-search output, and actor attribution was wrong
  (`[agent:claude]` on codex lines). Any new gap becomes a proposed ticket
  with evidence, for the owner to file or reject.
