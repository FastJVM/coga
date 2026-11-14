# Pair 283a63, output X (author)

## Authored ticket (full)

````markdown
---
title: Flag stalled in-progress tickets in coga status
status: draft
owner: trial-owner
contexts:
  - coga-dev/principles
workflow: code/with-review
---

## Description

Make stalled work visible in `coga status`: agent sessions can die and owner gates can be forgotten, leaving tickets `in_progress` for days. Mark an `in_progress` ticket as stalled when its most recent parseable entry in the configured global `coga/log.md` is older than a configurable threshold, and add `coga status --stalled` to list only stalled tickets. Done means the default marker and filtered view agree, shared configuration controls the threshold with a sensible default, documented edge cases are tested, and status remains read-only with no notifications or automatic actions.


## Context

### Scope and authoring assumptions

The human selected `code/with-review` and delegated remaining choices. Use a default of three elapsed days and shared `[status].stalled_days`, a strictly positive integer; reject booleans, zero, negative values, non-integers, malformed tables, and unknown keys with normal configuration errors. Treat this as team policy, with no local override. This ticket authorizes the future implementation of the configuration schema and shipped documentation/template, not changing this repository's `coga.toml` or `coga.local.toml` during authoring.

Only `in_progress` qualifies, including owner-held steps. Stalled is a derived display marker, never a new lifecycle status or persisted ticket field. Compare against one captured local current time, consistent with the timezone-free minute-resolution log envelopes: age strictly greater than the threshold is stalled; exact equality and future entries are not. Keep the canonical status intact for sorting and totals.

A ticket without a parseable log timestamp shows `activity unknown` and is excluded from `--stalled`. A missing log has the same outcome; preserve existing log-reader handling of unreadable logs and malformed lines. Never substitute ticket mtime or Git history for the stalled signal. Use the existing log reader's last parseable matching entry in file order. Log retention can remove matching history and ticket moves can orphan old log tags; both can produce `activity unknown`. Do not invent history recovery or rewrite the log.

Use a plain-text `stalled` marker, understandable without color. Preserve directory scope, recursion, sorting, and reverse options in the filtered view. With no matches, report a clear empty result. Reject `--stalled` combined with `--blocked` or `--dirs` with a useful usage error; `--all` does not expand eligibility beyond `in_progress`. Preserve other status summaries and warnings. No notifications, lifecycle changes, network calls, or automatic recovery actions are in scope.

Keep `owner: trial-owner`; leave the main agent absent for configured selection at activation. The configured Claude peer executable is currently absent in this checkout, so the requested workflow's peer-review step needs an available peer before it can run; do not substitute a workflow silently.

### Implementation pointers and required reading

`commands.status.status` is the thin CLI entrypoint and `views.render_status` owns rendering. `logfile.last_activity_map` already scans the global log once for per-ref activity and skips malformed timestamps; reuse that signal efficiently. `views.last_updated_map` backs the existing Updated column with Git history when the log is silent, so it cannot be used unmodified to classify stalled tickets. Keep this feature scoped to status rather than changing megalaunch eligibility or the shared Updated semantics. `validate.validate_repo` already accepts an `idle_hours` threshold (72 hours by default) for its `stuck-in-progress` warning; use it as precedent, while preserving validation’s existing threshold and command contract in this ticket.

`coga/lifecycle`, at `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md`, is cited rather than attached; read “Status: whether work happens” and “Triage: coga status”. Status and workflow position are separate; this change adds triage information without changing either. Update the owning triage contract in the same PR.

`coga/configuration`, at `src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`, is cited rather than attached; read “Allowlists” and “Unknown keys fail loud”. `config.load_config` validates shared and local configuration against fixed schemas. Extend configuration validation and document the new policy in the package owner and shipped template; do not create repo-local counterparts of packaged definitions.

`coga-dev/testing`, at `docs/contexts/coga-dev/testing/SKILL.md`, is cited rather than attached; read “Verification tiers and receipts” for the required Linux checks and receipts. Extend relevant tests in `tests/test_status.py`, `tests/test_views.py`, `tests/test_config.py`, and log-reader tests as needed. Use controlled time to cover both sides of the strict boundary and equality, default/custom thresholds, invalid configuration, all lifecycle statuses including owner gates, missing/malformed/future history, filter combinations and directory scope, and read-only behavior. Keep implementation and owning documentation in the same PR.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

````
