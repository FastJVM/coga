---
title: Trim coga/log.md to a configurable age with a weekly recurring job
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

`coga/log.md` only ever grows: on 2026-10-23 it was about 9,250 lines and
2.46 MB in this repo. Add an age-based retention setting to `coga.toml` and a
shipped weekly recurring template that deletes log lines older than the
retention window (git history keeps them; no archive file). Trimming is on by
default in every adopting repo; a repo can change the window or turn trimming
off in `coga.toml`. The design proposes the default window from measured
sizes (see Context) and the owner approves it at the design gate.

Done when the setting is documented in `coga/configuration`; the recurring
template and its workflow ship in both the live and packaged trees (twins
byte-identical per `tests/test_packaging.py`); a run against a seeded log
removes lines older than the window while keeping every line a reader still
needs (see "Lines that must survive"); recurring jobs do not re-fire after a
trim; the union-merge invariant is resolved and `coga-dev/internals/spool-merge`
updated; existing adopters get the template and default (not only new `init`
seeds); and `python -m pytest` passes.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/coalesce-coga-state-commits` and
`commit-journal/publish-log-lines-left-uncommitted`. Not blocked on either:
a trim is one publish from its `ticket.py`.

### Owner decisions (2026-10-23)

- Retention is bounded by **age in days**, not size or line count.
- Trimmed lines are **deleted**; git history is the archive.
- The template runs **weekly** and is **on by default** for adopting repos.
  This is a behavior change for adopters: the PR and release notes say so.
- The **default window is the design's call**, with the numbers below.

### Size facts (2026-10-23, this repo)

A 90-day cutoff keeps about 6,886 of 9,255 lines and 1.94 MB of 2.46 MB
(about 79%). Usage `[system]` JSON records are 1,329 lines but about 1.36 MB
(about 55% of bytes). At current volume an age window alone settles in the
megabytes; the design should say what window meets the goal and whether that
is acceptable, and note record size as a possible follow-up rather than
widening this ticket.

### The append-only invariant (most important)

`coga/log.md` carries `merge=union` (`coga/.gitattributes`, packaged twin
under `src/coga/resources/templates/coga/`), and `logfile`'s module docstring
calls it an append-only audit trail. `coga-dev/internals/spool-merge` says the
log is union-safe *because every writer only appends*, and that "a file that is
compacted, trimmed, or rewritten without such a healing reader must never
carry the attribute: union would resurrect deletions." Coga's own `publish`
three-way merge lands deletions when the base had the line, but git-native
merges of stale branches or clones, and working copies that lack the line, need
explicit analysis. The design must either amend the invariant (and the
attribute) or argue why trimming is safe, and update that topic in the same PR.
It must also handle the roughly 500 legacy lines that have no timestamp
(multi-line git errors such as `hint:`, `CONFLICT`, `fatal:`; see spool-merge's
legacy-line policy).

### Lines that must survive

Inventory readers through the `logfile` reader API (`log_lines`,
`iter_log_messages`, `task_log_lines`, `last_activity_map`,
`first_activity_map`) plus a whole-tree search, including `commands/`,
`resources/`, and `src/coga_edge/`. Known readers include `recurring`,
`recurring_runner`, `recurring_clone`, `service_order`, `usage`, `views`,
`validate`, `megalaunch`, `mark`, `authoring`, `repl_supervisor`,
`commands/{delete,owner,recurring}`, `bootstrap/retire/ticket.py`, and
`coga_edge/phone_home`. Known hazards:

- **Recurring serviced-period ledger.** The high-water mark is a
  `created|reused <task-ref> for <period>` line tagged `recurring/<name>`
  (`coga/recurring/scheduling`, "Periods and the serviced-period ledger").
  If a template's newest record is trimmed, that period re-fires. Keep at
  least the newest valid record per template regardless of age.
- **Usage records.** `usage` parses `[system]` JSON lines; `coga usage
  --since` is unbounded, so state the tradeoff for reports reaching past the
  window.
- **Task history.** Retro, retire, `coga show`, and activity maps read
  per-task lines; decide whether lines of still-open tasks survive the window.
- **Phone-home cursor.** `coga_edge/phone_home` keeps an offset+digest cursor
  on `log.md`; a rewrite logs "audit log rewritten or truncated; movement
  baselined to zero", which would lose telemetry movement every week. Fix or
  accept it explicitly.

### Placement and shipping

Follow `coga-dev/microkernel` (cited, not attached): deterministic trim work
belongs in the template's reserved `ticket.py` beside
`coga/recurring/<name>/ticket.md` using shared core infra, as
`blocker-reminders` does (template plus `coga/workflows/blocker-reminders/run`
workflow, both with packaged twins), unless the design shows it needs a
`runner.RECIPES` contract. Template frontmatter (`schedule:`,
`schedule_comment:`, `scope:`, `run_when_inactive`) is owned by
`coga/recurring/templates`; decide `run_when_inactive`. Say how existing
adopters receive the shipped template and default.

### Config

The key's schema, default, and docs go in `config.py` and the
`coga/configuration` topic. Because trimming is on by default, this repo's
`coga/coga.toml` needs no edit; agents must not edit `coga.toml`.

The trim commit is bookkeeping: subject it so `recurring_activity` classifies
it as non-activity (`Log: recurring/…` and `Ticket: recurring/…` already are).

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
