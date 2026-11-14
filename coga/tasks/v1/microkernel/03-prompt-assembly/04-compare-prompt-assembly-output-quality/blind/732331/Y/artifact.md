# Pair 732331, output Y (author)

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

Make stalled work visible in `coga status`: agent sessions can die or owner
gates can be forgotten while tickets remain `in_progress` for days. Mark an
`in_progress` ticket as stalled when its most recent usable entry for its exact
ref in `coga/log.md` is strictly older than a configurable threshold. Add
`--stalled` to list only those tickets; keep this a read-only triage view with
no notifications, lifecycle changes, or automatic recovery actions.

Done means normal status output visibly marks stalled tickets, `--stalled`
returns only matching tickets within the selected scope, and a documented,
validated threshold in `coga.toml` controls the result with a sensible default.
Tests must cover the age boundary, configuration, missing history, and filter
behavior, including out-of-order timestamps using last usable line semantics
and rejection of `[status]` overrides in `coga.local.toml`, and the owning user topics must describe the shipped behavior.


## Context

### Authoring assumptions and scope

Use `[status].stalled_hours`, a positive integer with default `48`, shared
configuration only; reject booleans, zero, negatives, and other invalid types.
The human delegated these details to authoring judgment. Keep owner
`trial-owner`; leave the main agent absent for the configured default at
activation. Use `code/with-review` as explicitly requested.

Only `in_progress` tickets qualify, including owner-held workflow steps and
materialized recurring tasks. At exactly the threshold a ticket is not stalled;
a future timestamp is not stalled. Use the existing log reader's timestamp
convention and last matching usable line semantics. Missing, trimmed, renamed,
or wholly malformed history means unknown activity: show that explicitly for
`in_progress` tickets and exclude them from `--stalled`. Do not infer stalled
age from Git commits, file mtimes, or live process checks. This intentionally
leaves tickets without usable retained history unclassified.

Keep existing directory, recursion, sorting, and `--all` behavior when adding
the filter. Reject `--stalled` with `--blocked` or `--dirs` with a clear usage
error. Make the stalled marker readable in wide and narrow/plain output and
give an unambiguous empty result when no stalled tickets match. Preserve the
existing Updated column and its Git fallback; it is distinct from log-only
stalled classification. Changes to megalaunch, log retention, notifications,
and automated ticket actions are outside this ticket.

### Workflow availability

The configured peer is Claude, whose executable is deliberately absent in this
trial checkout. `code/with-review` requires an available configured peer before
its peer-review step can launch; keep the requested workflow and resolve peer
availability in the execution environment.

### Source pointers and documentation ownership

`commands.status.status` owns the CLI flags; `views.render_status` builds and
filters rows, and `views._build_table` renders them. `logfile.last_activity_map`
already reads last usable log timestamps in one pass per exact ticket ref.
`views.last_updated_map` adds a Git fallback and is shared with megalaunch;
using that fallback for stalled classification would violate this ticket.
`config.Config` and `config.load_config` own configuration and allowlist
validation. Relevant tests are `tests/test_status.py`, `tests/test_views.py`,
`tests/test_config.py`, and `tests/test_logfile.py`.

`coga/lifecycle` is cited rather than attached: read and update “Triage:
`coga status`” in
`src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md`.
Status remains a pure read with no network or state mutation.
`coga/configuration` is cited rather than attached: read and update “Allowlists”
and “Unknown keys fail loud” in
`src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`.
New configuration must be explicitly allowed and validated. Update the package
configuration template's guidance if needed; do not edit the live repository's
`coga.toml` or `coga.local.toml`. Keep one package owner for each shipped topic
and fix dependent restatements in the same PR.

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
