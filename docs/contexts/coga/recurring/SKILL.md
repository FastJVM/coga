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
repo-global `coga/log.md` ([ledger](scheduling/SKILL.md#periods-and-the-serviced-period-ledger)).

That is the default `scope: repo`. A `scope: clone` template instead runs its
`ticket.py` once per period in every clone, with no period task, for work on
clone- or machine-local state such as local branches
([scheduling](scheduling/SKILL.md#repo-scope-and-clone-scope)).

Templates live outside `tasks/` on purpose: anything with a `ticket.md` under
`coga/tasks/` is a task, and a template has no `status:`, is never launched
directly, and survives across periods. The `tasks/recurring/` prefix marks a
period task as machine-generated and safe to reap and regenerate — which
licenses the scanner and Dream's retro pass to delete it without a PR. A
directory whose name starts with `_` is parked and ignored.

Coga installs no scheduler: point one cron entry at `coga recurring` (or
`--all <path>`). There is deliberately no separate headless runbook: unattended
operation is covered here and in [coga/secrets](../secrets/SKILL.md)
(service-account auth), and scheduling behavior is
[coga/recurring/scheduling](scheduling/SKILL.md).

## Commands

`coga recurring` sweeps due templates; `coga recurring launch <name>` (and
default aliases such as `coga dream`) fires one now; `list` and `promote`
inspect and create templates. What each spelling does is in
[scheduling](scheduling/SKILL.md#variants); flags are `coga recurring --help`'s.

## Where each part is specified

- [coga/recurring/templates](templates/SKILL.md) — template fields, parking,
  the template-to-period transform, promotion, cross-run state surfaces, the
  `ticket.py` authoring and reporting contract.
- [coga/recurring/scheduling](scheduling/SKILL.md) — period keys and the
  serviced-period ledger, repo and clone scope, sweep order (Dream last),
  status handling, the command variants and gates, TTY admission, unfinished
  runs and exit codes; its leaf [inactivity](scheduling/inactivity/SKILL.md)
  owns the repo-inactivity gate.
- [coga/recurring/delegation](delegation/SKILL.md) — `delegate:` periods
  serviced by one bootstrap agent launch; never a nested `coga launch`.
- [coga/recurring/autofix](autofix/SKILL.md) — the post-sweep run record,
  one-shot analyst, autofix tickets, and template-damage detection.
- [coga/period-task](../period-task/SKILL.md) — the small context the creator
  attaches to every period task: parent-blackboard state versus per-run scratch.
- [Dream template](https://github.com/FastJVM/coga/blob/main/coga/recurring/dream/ticket.md) — the built-in janitor template and its fixed
  phases; REM for repo-specific maintenance.
- Internals: [recurring-control](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-control/SKILL.md)
  (control-branch requirement, relay, owner authorization),
  [recurring-temp-worktrees](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-temp-worktrees/SKILL.md)
  (`--all` off-branch service), and
  [recurring-admission](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-admission/SKILL.md) (period
  generations, leases, ledger reads and freshness),
  [recurring-clone](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-clone/SKILL.md)
  (clone-scoped runs) and
  [recurring-autofix](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-autofix/SKILL.md)
  (analyst spawning and parsing).

Attaching `coga/recurring` composes only this overview; attach the child you need.

Procedures live in skills, e.g. `coga/recurring/verify` (fire a template in a
disposable clone before it merges).
