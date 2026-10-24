---
title: Coalesce Coga state commits to one per lifecycle event
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Coga's own state publication buries real work in `git log`. Of the last 300
commits on `main` (as of 2026-10-23), 233 are bookkeeping: `Ticket: …`,
`Log: …`, and `Sync coga state …`. A single launched step routinely lands 3–5
of them; for example, `make-every-code-workflow-review-with-the-other-age`
step 2→3 produced `Log`, `Log`, `Ticket … step 3`, `Log`, `Log`, `Sync coga
state`, `Ticket … step 4`, `Log`. Design and implement a publication scheme
that cuts the bookkeeping commits per launched step to the minimum the
publication contract allows, then implement it.

The design step sets the target bound and argues it. Three publishes are
inherent today: the launch-audit `Log:` written before the agent runs, the
`Ticket: … step N` bump the next operator needs at once, and the usage-record
`Log:` written after the agent's final answer, after the bump. The launch line
can likely ride the bump commit (`git.sync_task_state` already publishes the
ticket and `log.md` together). Folding the usage record in means delaying the
bump's publish, rewriting shared `main`, or leaving the line dirty, and each of
those breaks a constraint below. So expect a bound like "one lifecycle commit
plus at most one teardown log commit", not one commit.

Done when the owner has approved the design's bound, a test asserts that
bound for a seeded launch-and-bump, `recurring_activity` keeps today's
classification (see Context), `coga/state-publication` is updated in the same
PR, and `python -m pytest` passes.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/publish-log-lines-left-uncommitted` and
`commit-journal/trim-the-audit-log`.

### Sequencing

Land `commit-journal/publish-log-lines-left-uncommitted` first: its inventory
of every log write and its publish path is an input to this design. Coalescing
deliberately defers some log lines (for example the launch line until the
bump), so this ticket must re-run that classification and update the
deliberate-deferral list in `coga/state-publication` so no deferred line ends
up stranded at an owner hand-off.

### Where commits come from

- `git.sync_log` publishes `coga/log.md` alone as `Log: <slug>`. Callers:
  `LaunchSession` publishes the launch-audit line ("launched (operator=…)")
  immediately, which is the easiest commit to fold away;
  `spawn_agent_session.record_and_publish_launch_audit` publishes it only when
  `commit_log` is set (bootstrap targets); the launch teardown publishes the
  usage record; `launch_script` covers the script phase; `recurring_runner`
  publishes recurring launches.
- `git.sync_task_state` publishes one ticket write and `log.md` together as
  `Ticket: <slug> — <event>` (`bump`, `checkouts`, `megalaunch`,
  `commands/create`, `commands/owner`, `commands/unblock`, …).
- `git.sync_coga_state` is the catch-all sweep. A plain `Sync coga state`
  comes from the CLI end-of-command sweep (`cli._should_sweep_coga_state`):
  in the example above, `a2388fbe0` carried the agent's own `pr:`
  blackboard edit, swept by a coga command the agent ran before bumping.
  Launch adds `… before launch` and `… before checkout return`. A sweep
  with nothing dirty already no-ops.
- The teardown ordering is explained in a `launch.py` comment: the usage
  record lands in `log.md` *after* the agent's final `bump`/`mark` sync.

### Inactivity classification

`recurring_activity._MACHINE_SUBJECT` treats as machine (non-activity)
commits: `Log:` except `Log: bootstrap/`, `Sync coga state`,
`Ticket: recurring/`, `Ticket: autofix/`, and a few others. Ordinary
`Ticket: <slug> — …` lifecycle commits count as human activity. Preserve
exactly that: if a coalesced commit carries a lifecycle event, it must still
count as activity, and log-only/sweep commits must not. Do not widen the
regex to make the repo look idle.

### Constraints and topics (cited, not attached; read first)

- `coga/state-publication` (`docs/contexts/coga/state-publication/SKILL.md`,
  "When Coga publishes") owns the user contract: lifecycle commands publish as
  soon as write, log line, and notification are final; teardown publishes the
  log after usage capture. Coalescing must not delay a lifecycle publication
  another checkout needs, must not rewrite or force-push `main`, and must not
  make a failed publish silent. Edited by this ticket.
- `coga-dev/internals/state-publication` owns the sweep's selection, skips,
  and publish primitive; `coga-dev/internals/spool-merge` owns the
  union-safe log publish.
- Keep commit subjects informative: a coalesced commit still names the
  ticket and the event (for example `Ticket: <slug> — step 4 (review)`).
- Out of scope: log size (sibling trim ticket) and the read-only-sandbox
  sync failures owned by `fix-coga-git-sync-failures-that-leave-main-diverge`.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
