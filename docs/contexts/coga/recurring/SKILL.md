---
name: coga/recurring
description: Overview of Coga's recurring system — templates, period tasks, the sweep commands, and which child topic owns each part; attaching it does not load the children.
---

# Recurring tasks

A recurring **template** is a ticket-format directory at `coga/recurring/<name>/` whose
`ticket.md` carries a `schedule:` cron. When a template is due, `coga recurring`
materializes one **period task** at the stable ref `recurring/<name>`
(`coga/tasks/recurring/<name>/`) and launches it through the ordinary task
lifecycle. The period is not in the slug; the serviced period is recorded in the
repo-global `coga/log.md`.

Templates live outside `tasks/` on purpose: anything with a `ticket.md` under
`coga/tasks/` is a task, and a template has no `status:`, is never launched
directly, and survives across periods. The `tasks/recurring/` prefix marks a
period task as machine-generated and safe to reap and regenerate — which
licenses the scanner and Dream's retro pass to delete it without a PR. A
directory whose name starts with `_` is parked and ignored.

Coga installs no scheduler: point one cron entry at `coga recurring` (or
`--all <path>`).

## Commands

| Command | What it does |
| --- | --- |
| `coga recurring` | Sweep: create/launch every due template for the current period. |
| `coga recurring --force` | Ignore schedule and status filters; real runs, real side effects. |
| `coga recurring --all <path>` | Sweep every Coga repo below `<path>`, one fresh process each. |
| `coga recurring --interactive` | Attended, human-stepped debug sweep with no liveness limits. |
| `coga recurring launch <name>` | Create/launch one template now, ignoring its schedule. |
| `coga recurring promote <task> --schedule "<cron>"` | Turn an existing task into a template. |
| `coga recurring list` | Read-only: templates, firings, period state, picked tasks. |

The bare, forced and `--all` spellings translate their flags into argv for the
fixed `recurring-scan` recipe run through `coga run`. Default aliases wrap named
launches: `coga dream`, `coga autoclose`, `coga skill-update` each expand to
`recurring launch <name>`.

## Where each part is specified

- [coga/recurring/templates](templates/SKILL.md) — template fields, parking,
  the template-to-period transform, promotion, cross-run state surfaces, the
  `ticket.py` authoring and reporting contract.
- [coga/recurring/scheduling](scheduling/SKILL.md) — period keys and the
  serviced-period ledger, sweep order (Dream last), status handling, `--force`,
  named launches, `--all`, the `owner` gate, TTY admission, unfinished runs and
  exit codes.
- [coga/recurring/delegation](delegation/SKILL.md) — `delegate:` periods
  serviced by one bootstrap agent launch; never a nested `coga launch`.
- [coga/recurring/autofix](autofix/SKILL.md) — the post-sweep run record,
  one-shot analyst, autofix tickets, and template-damage detection.
- [coga/period-task](../period-task/SKILL.md) — the small context the creator
  attaches to every period task: parent-blackboard state versus per-run scratch.
- [coga/dream](../dream/SKILL.md) — the built-in janitor template and its fixed
  phases; REM for repo-specific maintenance.
- Internals: [recurring-control](../internals/recurring-control/SKILL.md)
  (control-branch requirement, relay, owner authorization),
  [recurring-temp-worktrees](../internals/recurring-temp-worktrees/SKILL.md)
  (`--all` off-branch service), and
  [recurring-admission](../internals/recurring-admission/SKILL.md) (period
  generations, leases, ledger freshness).

Attaching `coga/recurring` composes only this overview; attach the child you need.

Procedures live in skills, e.g. `coga/recurring/verify` (fire a template in a
disposable clone before it merges).

Implementation: `src/coga/recurring.py` (templates, creation, ledger),
`src/coga/recurring_runner.py` (sweeps, admission, delegation, temp worktrees),
`src/coga/recurring_autofix.py` (post-sweep analysis).
