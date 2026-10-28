# Recurring sweep — 2026-09-10 10:01:44

- repo: coga
- mode: bare sweep
- templates scanned: 7
- tasks run: 3
- problems: 0

## Scan

```
autoclose-merged     ready (Thu 08:00)          launch
blocker-reminders    ready (Thu 10:00)          launch
branch-sweep         overdue 3d (Mon 07:00)     skip (done)
digest               ready (Thu 09:00)          launch
dream                overdue 3d (Mon 09:00)     skip (done)
resolve-conflicts    overdue 3d (Mon 08:00)     skip (paused)
skill-update         overdue 3d (Mon 09:00)     skip (done)
```

## Task outcomes

### recurring/autoclose-merged — completed

- template: `autoclose-merged`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-09-10T17:02:07+00:00
Task: `recurring/autoclose-merged`

1 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `autofix/escalate-watchdog-paused-recurring-tasks-instead-o` "Escalate watchdog-paused recurring tasks instead of skipping them": worktree `/tmp/coga-watchdog-pauses`, branch `fix/watchdog-pauses` — `coga retire autofix/escalate-watchdog-paused-recurring-tasks-instead-o`

## Run notes — 2026-09-10

- `coga run autoclose` closed 1 ticket:
  `autofix/escalate-watchdog-paused-recurring-tasks-instead-o` (FastJVM/coga
  PR #778, merged; final step). No other PR-linked open ticket qualified.
- It still records `branch: fix/watchdog-pauses` /
  `worktree: /tmp/coga-watchdog-pauses`, so the sweep named a retire
  follow-up. Mirrored to the parent recurring blackboard (this period
  blackboard is deleted next firing).
- Checked the 2026-09-09 follow-ups before mirroring: neither has been
  retired (`/home/n/Code/coga-banner-opening` still on disk;
  `/tmp/multiply-receiver` still listed `prunable`). Left in place.

## Gotchas

- An auto-closed ticket's checkout is not necessarily a worktree of the repo
  holding the ticket. This multiply `coga/` owns tickets whose feature work
  lives in the FastJVM/coga checkout at `/home/n/Code/claude/coga`; `coga
  retire` requires a same-repo linked worktree, so those follow-ups have to be
  run from the other checkout. The sweep names the command without checking
  which repo the worktree belongs to.
```

### recurring/digest — completed

- template: `digest`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-09-10

`coga run digest` posted one digest for period **2026-09-10**: 56 items.

- Spool: 10 pending records consumed (Done/Canceled from 2026-09-09 10:38
  through 2026-09-10 10:02); drained to anchor `3dae1a62cacd`.
- Git scan range `6189856..29ea79f` — 113 commits, 47 reported after the
  state-sync filter.
- Parent blackboard (`coga/recurring/digest/ticket.md` → `### Digest State`)
  advanced: `last_commit: 29ea79f678f5c6fd7da71960700405793a27c30b`,
  `posted: yes`.

No blockers. Nothing durable to extract — the run was routine.
```

### recurring/blocker-reminders — completed

- template: `blocker-reminders`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.


## Run 2026-09-10

- Period `2026-09-10` (newest `created recurring/blocker-reminders for ...` line in `coga/log.md`).
- **Blocked sweep:** `coga run blocker-reminders` → `[blockers] no unresolved blockers to remind.`
  No task in the repo carries `status: blocked`.
- **Paused escape hatch:** ran the same shared primitives
  (`list_tasks` → `read_ticket` → `read_blackboard` → `parse_blockers_text` →
  `_fingerprint` / `reminder_fingerprints`) filtered to `status: paused`.
  Exactly one live paused task: `recurring/resolve-conflicts`, one unresolved
  blocker `id=20260819T135355`, fingerprint `65c9a6d7a831`, already watermarked
  `last_reminded: 2026-09-02 12:47` → correctly skipped, no repeat post.
- **Reminders posted:** 0. **Watermarks written:** 0. Git tree clean, nothing to sync.
- Note: `grep` for `status: paused` also hits
  `tasks/recovery/route-dream-2026-w37-findings/dream-2026-w37.md`. That is an
  *attachment* — an archived snapshot of the paused `recurring/dream` period
  ticket kept beside an ordinary `status: active` recovery task — not a live
  task. `list_tasks` resolves that directory through its `ticket.md`, so the
  attachment is excluded, as intended; it carries no `## Blockers` anyway.
  The live `recurring/dream` period task is `status: done`.
- Parent blackboard needs no update: it stores no cross-run dedup state (that
  lives on each reminded task) and the template declares no `state_keys:`.
```

## Sweep notes

- launching 3 due task(s) sequentially
