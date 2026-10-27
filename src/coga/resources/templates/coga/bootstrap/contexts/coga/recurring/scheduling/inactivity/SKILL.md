---
name: coga/recurring/scheduling/inactivity
description: Repo inactivity and session liveness — the human-commit gate on sweeps, completion signaling and terminal-ticket recovery, and how late teardown differs from unfinished timeouts.
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

## Session completion and liveness

Repo inactivity decides whether to start scheduled work. Once an agent is
running, the supervisor watches its completion separately; timeout settings
and their precedence are in [scheduling](../SKILL.md#variants).

Session-ending commands atomically write the task's qualified slug to
`COGA_DONE_SENTINEL`. The supervisor accepts only its launched slug, so
repointing `COGA_REPO_ROOT`, `COGA_TASK_*`, and the expected task to another
worktree does not change the signal's identity. Preserve the inherited
sentinel path when doing so. A failed write warns on stderr with the path and
error. An absent variable also warns when `COGA_EXPECTED_TASK` or
`COGA_SUPERVISED` witnesses a supervised launch. The lifecycle transition
remains successful; the warning explains that teardown may need a backstop.
Unsupervised commands with no sentinel stay quiet.

For ordinary ticket launches, an independent backstop checks the exact
launched ticket at most once a second. With Git publication and a configured
remote, it reads that ticket's blob in the local remote-tracking control ref,
so completion published from a linked worktree is visible even when the
launching working copy stays stale. It never fetches or scans other tasks,
and caches unchanged blobs. Repositories without publication or a configured
remote use the local ticket, caching its file metadata. A configured remote
with unavailable control state does not fall back to an unpublished local
transition: publication may still be running.

The backstop accepts only `done` or `canceled` from the launched recurring
generation, when present. It allows five seconds of continuously observed
terminal state for the normal signal to arrive, then tears down the REPL
with a `ticket-terminal` reason and a clean completion result. It does not
claim a sentinel was observed. Missing, unreadable or malformed tickets,
another recurring generation, blocked/paused tickets and nonfinal workflow
bumps do not prove completion. Stateless bootstrap targets and ticket-authoring
interviews still require their sentinel; this does not change
[delegated completion](../../delegation/SKILL.md).
An independent clone's remote changes become visible only when the launching
repository's tracking ref is updated.

If an idle or wall-clock limit starts teardown first, the process result
remains timeout/124. The recurring report nevertheless records `completed`
with a `late teardown: done signal not observed before liveness stop` note
when the final ticket is provably terminal, including its final status.
Missing tickets and unfinished runs remain `timed-out`; a real crash or a
damaged template keeps its failure classification. This separates completed
work with a lost signal from a wedged agent without rewriting process-exit
evidence.
