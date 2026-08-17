---
slug: service-recurring-from-a-temp-control-worktree-ins
title: Service recurring from a temp control worktree instead of failing the repo
status: active
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/cli
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

When `coga recurring --all <path>` dispatches a repo whose primary checkout is
not sitting on the configured control branch, the child refuses before scanning
and the parent reports the whole repo as failed. Service that repo's
**recipe-backed** templates from a temporary linked worktree of
`<remote>/<control-branch>` instead, leaving the operator's checkout untouched.

Do **not** implement this by moving the operator's checkout (stash → switch →
run → switch back → pop). That option was considered and rejected; the reasons
are recorded under `## Context` and the rejection is part of this ticket's
scope, not an open question.

## Context

### The failure being fixed

`_sync_control_checkout_ahead` (`src/coga/recurring_runner.py:918`) returns
early when the checkout is not on the control branch:

```
configured control branch 'main' is not checked out (branch 'agent/…')
```

Because that path returns before `_fetch_control_branch`, `fetched` stays
`False`, so the "Resolve in that checkout — e.g. `git -C … rebase …`" hint is
never appended: the operator gets a diagnosis with no remedy. With
`require_fresh_control` set (every `--all` child, see
`_run_repo_recurring:558`), `run_recurring_scan` returns
`git.STALE_CONTROL_EXIT_CODE` (`recurring_runner.py:637-652`) and
`run_recurring_all_repos:236` counts the repo in its `N repo(s) failed` line.

The gate itself is correct — the scan reads working-tree templates and period
tasks and writes period state, so running it from a stale feature branch could
re-fire runs the control branch already serviced. The defect is that the only
recovery is a human noticing cron output and running `git checkout` by hand.
A repo left parked on a feature branch (e.g. a workflow stopped at a
human-owned step) fails every sweep until someone intervenes.

### Why the temp worktree is the right shape

An unattended sweep can only ever run recipe templates today:
`run_recurring_scan` calls
`scan_due(cfg, allow_interactive=_interactive_stdio_has_tty(), force=force)`
(`recurring_runner.py:657`), which reaches `create_template(...,
allow_agent=allow_interactive)` (`recurring.py:338`) and drops agent templates
when there is no TTY. Recipe tasks then run through `_run_recipe_task:748` as
plain `python -m coga.cli run <recipe>` subprocesses — deterministic, no REPL,
no agent CLI. So the set this ticket needs to serve is exactly the set that
needs no interactive checkout, and a detached worktree at the control tip is
enough to run it.

`git worktree add --detach <tmp> <remote>/<control-branch>` gives "be on the
control branch, elsewhere" with no mutation of the operator's checkout: a
dirty tree is irrelevant, concurrent agent sessions are unaffected, and a crash
leaves nothing but a stale temp directory to reap.

### Rejected: stash / switch / restore

Considered and rejected (2026-08-17). It is not merely riskier; it breaks in
this codebase specifically:

- **The window is the whole sweep, not a moment.** `recurring` launches as well
  as scans, sequentially, with a 15-minute default idle timeout per REPL
  (`COGA_REPL_IDLE_TIMEOUT`) plus `max_session`. Under `--all` the operator's
  work would sit in a stash, on a branch they did not choose, for as long as
  the sweep runs.
- **`stash pop` conflicts against the scan's own writes.** The scan writes
  `coga/tasks/**`, `coga/log.md`, and template blackboards
  (`last_serviced_period`) — precisely the paths a human is likely to have
  uncommitted edits in. An unattended job would leave conflict markers inside a
  ticket plus a half-applied stash: the silent-wrong-answer failure mode
  principle 6 forbids.
- **It races Coga's own sessions.** Git has no worktree-level lock, and
  `coga launch` already rechecks the active branch and sampled HEAD immediately
  before every fast-forward *because* a concurrent checkout switch is a known
  hazard. A scheduler performing that switch would attack an invariant the rest
  of the system defends.
- **Ordinary git sharp edges:** plain `git stash` skips untracked files (`-u`)
  and ignored ones (`-a`, which would sweep `node_modules` / `.venv` / `.env`);
  `git checkout <control>` fails outright when the control branch is already
  checked out in another linked worktree — the layout Coga recommends — so the
  auto-switch would break on exactly the well-configured repos; mid-rebase,
  mid-merge, and mid-bisect states cannot switch at all; submodules do not
  follow.
- **No crash safety.** A cron timeout, reboot, or SIGKILL between stash and pop
  strands the work in a stash entry the operator never created.

### Design questions for the design step

1. **Trigger scope.** Only when the control branch is not checked out, or also
   when it *is* checked out but the tree is too dirty / diverged to fast-forward
   (the `fetched == True` branch of the same gate)? The second is a larger
   behavior change and may deserve its own decision.
2. **Attended runs.** Should a TTY-attended `coga recurring` in a
   feature-branch checkout also use the temp worktree for its recipe templates,
   or keep failing loud so the human fixes the checkout? Agent templates cannot
   use this path regardless — decide what they report.
3. **Worktree location and lifecycle.** Where the temp worktree lives, naming,
   removal on every exit path including signals, and reaping a leftover from a
   killed run. There is no generic "create a temp worktree" helper today —
   `branchcleanup.remove_ticket_worktree:114`, `git.is_linked_worktree:4194`,
   and `git._worktree_holding_branch:4018` are the existing neighbours to reuse
   or extend.
4. **Concurrency.** Two sweeps over the same repo must not collide on the temp
   path, and the existing `--all` duplicate-remote grouping
   (`_duplicate_remote_checkouts:437`) already assumes one runner per remote
   workspace — confirm that still holds.
5. **State landing.** Period tasks created in the temp worktree must reach the
   control branch and the operator's checkout the same way an ordinary run's
   would; confirm the existing sync path works unmodified from a detached
   worktree, and what happens to the repo-global `coga/log.md` serviced-period
   ledger.
6. **Reporting.** The `--all` summary needs a distinct outcome for "serviced
   from a temp control worktree" so it is not silently indistinguishable from
   an ordinary sweep, and agent templates skipped this way should be named.

### Independently shippable

Whatever the design concludes, the missing-remedy gap in the current error is
worth closing on its own: the not-checked-out branch of
`_sync_control_checkout_ahead` should name the exact fix
(`git -C <root> checkout <control-branch>`) the way the post-fetch branch names
its rebase command. Small and contained; do it even if the worktree path is
scoped down.

### Verification

- New tests alongside `tests/` covering: a feature-branch checkout with a dirty
  tree is serviced for recipe templates and its worktree is left byte-identical
  (branch, HEAD, `git status --porcelain`, `git stash list`); the temp worktree
  is removed on success, on recipe failure, and on signal; agent templates are
  still skipped with an honest report.
- `python -m pytest`
- `coga validate --json`

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
