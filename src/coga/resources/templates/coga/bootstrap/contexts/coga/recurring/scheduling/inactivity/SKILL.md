---
name: coga/recurring/scheduling/inactivity
description: The repo-inactivity gate on scheduled sweeps — the `idle_days` window, the human-commit signal and machine-subject classification, how non-exempt templates are skipped, and what `--force` and named launches bypass.
---

# Repo inactivity

Part of [coga/recurring/scheduling](../SKILL.md).

Scheduled sweeps check human activity after control-branch catch-up, owner
admission and agent-override validation, before the due scan. The shared
`[recurring] idle_days` window (documented in the
[shipped coga.toml](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/coga.toml);
see [configuration](../../../configuration/SKILL.md)) defaults to 14.
Let `last` be the local calendar date of the newest human committer timestamp:
the repo is inactive when `(today - last).days >= idle_days`. Thirteen days is
active at the default; fourteen is inactive. A new human commit wakes the
repo automatically; there is no persisted dormant state.

The signal is first-parent history of both resolving refs,
`refs/heads/<control_branch>` and `refs/remotes/<remote>/<control_branch>`,
using configured Git names. The newest human timestamp across both wins,
even with out-of-order clocks. The check performs no fetch. Missing both refs
or a Git failure treats the repo as active and prints one yellow note.
Git-disabled repos are silently active. Resolved history with no human commit
is inactive and displays `never` as its last activity.

A commit subject is machine-written when:

- they start with `Log:`, `Sync coga state`, `Dream`, `Ticket: recurring/`,
  `Autofix:`, `Ticket: autofix/`, or `Update Coga-managed skills` (including
  squash-merge suffixes); `Log: bootstrap/*` is an explicit human exception;
- they end with `— blocker reminder`;
- they are `Merge pull request #N from <owner>/<branch>` with a branch starting
  `claude/dream-`, `coga/dream`, `dream/`, or `coga/skill-update`.

Everything else is human, including ordinary `Ticket: <slug> — …` events.
Authors do not matter. Unmerged branches, worktrees and GitHub review comments
are invisible. Consequently `address-pr-comments` and `resolve-conflicts`
pause during prolonged reviews without control commits. Hand edits published
as `Sync coga state` do not keep a repo awake, and the broad `Dream` prefix can
misclassify a human title. Conversely, agent-created ordinary tickets and
Dream merges from unlisted branches count as human. These are accepted limits
of subject-based classification; an ordinary commit or explicit override
recovers from false inactivity.

On an inactive, non-forced sweep each template's frontmatter is read
leniently for `run_when_inactive` and its schedule; a template not setting
`run_when_inactive: true` is skipped before strict validation, period or
ledger handling. A stale or rejected key on a non-exempt template therefore
raises no template error and no alert while the repo is dormant; it surfaces
when the repo wakes, under `--force`, or in `coga validate`. Malformed YAML, frontmatter that is not a mapping,
a missing `ticket.md`, or a non-boolean `run_when_inactive` leaves the
exemption undecidable and is still a template error; the scan reports it and
continues with the other templates. An
unparseable schedule gets the skip row with `-` as its firing. No period is
created, resumed, re-launched or watchdog-escalated; existing bytes remain
untouched. Exempt templates are fully validated and retain normal creation,
resume, launch and watchdog escalation. The table prints one row per non-exempt template:
`skip (repo inactive since YYYY-MM-DD)` (or `never`), after one header naming
the last human date, days idle and configured window. Run-record scan lines
carry the same rows.

Inactivity skips are not problems or unlaunched creates. An all-skipped sweep
exits 0, and `--all` counts its child as swept. On an inactive repo autofix runs
only if an exempt template recorded a launch outcome: errors and watchdog
escalation without a launch do not reach the analyst. An all-skipped sweep
writes no autofix run log, makes no analyst call and creates no ticket.

`--force` bypasses the check entirely, including every `--all` child. Named
launches (`coga recurring launch <name>` and aliases such as `coga dream`)
never consult it. `idle_days = 0` disables it.
