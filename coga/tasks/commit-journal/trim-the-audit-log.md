---
title: Trim coga/log.md to a configurable age with a weekly recurring job
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
- coga/recurring/templates
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
agent: claude
launch_generation: pending:e45a7127-ad8d-4f0f-bc72-5667b323de46
---

## Description

Bound the growth of `coga/log.md` with an age-based retention setting and a
shipped weekly recurring template that deletes log lines older than the
retention window (git history keeps them; no archive file). Trimming is on by
default in every adopting repo; a repo can change the window or turn trimming
off in `coga.toml`. The design proposes the default window from measured
sizes (see Context) and the owner approves it at the design gate.

Done when the setting is documented in `coga/configuration`; the recurring
template and its workflow ship in both the live and packaged trees (twins
byte-identical per `tests/test_packaging.py`); a run against a seeded log
removes expired events while preserving required reader state and concurrent
new events (see "Lines that must survive"); recurring jobs neither re-fire nor
change pause/resume behavior because of a trim; the union-merge invariant is
resolved and `coga-dev/internals/spool-merge` updated; a verified adoption path
delivers the template and default to existing repos as well as fresh `init`
seeds; and `python -m pytest` passes. Verification must exercise cutoff
boundaries, disabled and repeated/no-op runs, and concurrent/stale-copy
publication and merge cases, not just a standalone filtering function.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/coalesce-coga-state-commits` and
`commit-journal/publish-log-lines-left-uncommitted`. These are provenance, not
dependencies: publish the trim through existing state-publication machinery;
commit coalescing and unrelated publication-warning changes stay out of scope.

### Owner decisions (2026-10-23)

- Retention is bounded by **age in days**, not size or line count.
- Trimmed lines are **deleted**; git history is the archive.
- The template runs **weekly** and is **on by default** for adopting repos.
  This is a behavior change for adopters: the PR and release notes say so.
- The **default window is the design's call**, with the numbers below.

### Size facts (2026-10-23, this repo)

A 90-day cutoff keeps about 6,886 of 9,255 lines and 1.94 MB of 2.46 MB
(about 79%). Usage `[system]` JSON records are 1,329 lines but about 1.36 MB
(about 55% of bytes). Re-measure during design with the proposed retention
exceptions included; explain the expected steady-state size and whether it
meets the goal. Record size is a possible follow-up, outside this ticket.

### The append-only invariant (most important)

Read `coga-dev/internals/spool-merge` at
`docs/contexts/coga-dev/internals/spool-merge/SKILL.md` (cited, not attached),
sections "`merge=union` files", "One event per log line", "How `publish` lands
a union path", and "Crash-safe replacement is not a lock"; this is an editing
target. `coga/.gitattributes` and its packaged twin mark `log.md` as
`merge=union`; `logfile` describes it as append-only. Trimming breaks that
justification unless a healing reader makes resurrection harmless.

`git._merge_union_bytes` can land a deletion when the base contained the line;
this does not prove safety for git-native merges, stale branches/clones, or
working copies missing peer additions. The design must resolve resurrection
and concurrent-event loss, amend the invariant and attribute as needed, and
update the topic and affected public contracts in the same PR. Locally,
`logfile.append_log` opens the file for append without acquiring
`git.state_lock`; a trim's atomic read/replace or lock alone is insufficient.
Include races with local appends as well as cross-checkout publication.

Legacy events may span untimestamped continuation lines (roughly 500 in the
measurement). Preserve or remove each event with its continuations; specify a
conservative policy for orphan, malformed, and incomplete lines instead of
silently assigning them an age. Preserve the v1 encoding of retained events.

### Lines that must survive

Inventory the `logfile` reader API (`log_lines`, `iter_log_messages`,
`iter_log_messages_reverse`, `task_log_lines`, `last_activity_map`,
`first_activity_map`) and direct readers across `src/coga/`, `src/coga_edge/`,
and live/packaged scripts and templates. Include the CLI's unpublished-line
check and rollback writers such as `logfile.retract_log_lines`, not only
display readers. Known hazards:

- **Recurring serviced-period ledger.** The high-water mark is a
  `created|reused <task-ref> for <period>` line tagged `recurring/<name>`.
  Keep at least the greatest valid calendar period per template regardless of
  age, using the ordering of `recurring._LedgerAccumulator` and
  `recurring.period_key_at_least`, not the last file line or newest event
  timestamp. `recurring.read_serviced_ledger` has forward and bounded reverse
  readers; the design must preserve deduplication and explicitly handle
  malformed-record errors rather than silently repairing them by deletion.
- **Pause provenance.** `recurring._pause_origins` uses creation and pause
  events, timestamp order, and same-minute append order to distinguish machine
  pauses from human pauses. Keep sufficient evidence for existing paused
  periods to retain the same resume eligibility after trimming.
- **Usage records.** `usage` parses `[system]` JSON lines; `coga usage
  --since` is unbounded, so state the tradeoff for reports reaching past the
  window.
- **Task history.** Retro, retire, `coga show`, activity maps and
  `service_order.service_order` consume per-task history. Decide whether full
  histories of still-open tasks survive, and identify the minimum facts
  needed to preserve lifecycle and scheduling behavior if they do not.
- **Phone-home cursor.** `coga_edge.phone_home._cursor` stores an offset and
  prefix digest; rewriting the consumed prefix baselines movement to zero.
  Fix this or seek explicit acceptance at the design gate. Record any accepted
  loss in `coga/recurring/phone-home/ticket.md`, sections "State, publication,
  and loss" and "Scope and approximate movement", and its packaged twin.

Read `coga/recurring/scheduling` at
`docs/contexts/coga/recurring/scheduling/SKILL.md` (cited, not attached),
sections "Periods and the serviced-period ledger" and "Admission and
unfinished runs", for the ledger and pause contracts above. Update affected
contracts and their packaged twins with the implementation.

### Placement and shipping

Read `coga-dev/microkernel` at `docs/contexts/coga-dev/microkernel/SKILL.md`
(cited, not attached), sections "The microkernel rule" and "The `ticket.py`
script phase". Deterministic trim work belongs at the edge, entered through
`coga/recurring/<name>/ticket.py` and using shared core infra, unless the design
proves a `runner.RECIPES` contract is needed. Use the template/workflow pairing
at `coga/recurring/blocker-reminders/` and
`coga/workflows/blocker-reminders/run.md` as a lifecycle example, not a reason
to add a core recipe. The script must complete disabled and no-op periods too;
exit 0 with an open step would fall through to an agent. Choose the template
name, weekly cron, scope and `run_when_inactive` during design.

`recurring.scan_due` discovers local templates;
`commands.update.copy_fresh_templates` seeds fresh repos only. Name the
delivery trigger for existing repos and verify it on a pre-feature fixture,
preserving local customizations and opt-outs. Read `coga/edge-code` at
`docs/contexts/coga/edge-code/SKILL.md` (cited, not attached), sections
"Wheel-owned edge implementations" and "Explicit local forks": a wheel can
update an imported edge implementation, but does not install new repo
templates, schedules or workflows. Do not expand this into a general updater.

### Config

Read `coga/configuration` at `docs/contexts/coga/configuration/SKILL.md`
(cited, not attached), sections "Allowlists" and "Unknown keys fail loud";
update it and its packaged twin with the schema and default in `config.py`.
The design selects the key, day-count validation, disable representation,
cutoff clock/timezone and exact boundary. This repo needs no config edit for
default-on behavior; agents must not edit `coga.toml` or `coga.local.toml`.

The trim commit is bookkeeping: subject it so
`recurring_activity.is_machine_commit` classifies it as non-activity
(`Log: recurring/…` and `Ticket: recurring/…` already are).

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
