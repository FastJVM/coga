# Pair 732331, output X (author)

## Authored ticket (full)

````markdown
---
title: Flag stalled in-progress tickets in coga status
status: draft
owner: trial-owner
workflow: code/with-review
---

## Description

Make stalled work visible in `coga status`: tickets regularly remain
`in_progress` for days after an agent session dies or an owner gate is
forgotten. Mark an `in_progress` ticket as stalled when its most recent
entry in the configured repo-global `coga/log.md` is older than a configurable
threshold, defaulting to 48 hours. Provide `coga status --stalled` to list
only those tickets, including tickets waiting at owner gates.

Done means the ordinary status view clearly marks stalled tickets, the
stalled-only filter returns exactly that set within the requested directory
scope, and a validated setting in shared `coga.toml` changes the threshold.
Cover threshold boundaries, status eligibility, missing log history, and
configuration validation with focused tests, and document the behavior and
configuration in the same PR. This is read-only triage: no notifications,
automatic transitions, recovery actions, or process-liveness detection.


## Context

### Authoring assumptions

The human specified log age as the signal and chose `code/with-review`,
leaving details to author judgment. Use a 48-hour default, strict elapsed
age greater than the threshold (equality is not stalled), and `--stalled`.
Only `in_progress` qualifies, irrespective of the current step's operator.
A ticket with no usable log timestamp has unknown age and is not stalled;
do not substitute Git commit or filesystem modification times. Choose a
clear unknown-age presentation without changing the existing Updated
column's fallback semantics. These authoring assumptions were confirmed by the human.

Use a finite positive numeric duration in hours, rejecting booleans; choose the exact config key and
schema placement during implementation to fit existing configuration
conventions. Apply normal shared/local configuration precedence and reject
invalid values through existing config diagnostics. Document the default,
units, supported values, and placement. Keep directory recursion and sorting
working with the filter. Explicitly define and test interactions with
`--all`, `--blocked`, and `--dirs`; contradictory view modes should fail
clearly rather than silently discard a requested filter.

“Most recent” means the greatest usable timestamp for the exact task ref,
not the last matching line in file order: cross-checkout publication can
leave log entries unsorted. Test unordered history and use a consistent
clock convention with the existing log format. Preserve unrelated consumers
when adding this timestamp selection.

### Source and contract pointers

- `coga.commands.status.status` is the thin CLI entrypoint;
  `coga.views.render_status` owns status rendering and filtering.
- `coga.logfile.last_activity_map` provides log timestamps by task ref,
  currently selecting the final parseable line in file order.
  `coga.logfile.first_activity_map` documents unsorted published history.
  `coga.views.last_updated_map` is shared with the megalaunch picker and
  falls back to Git history when log data is absent. Stalled detection must
  use log timestamps directly; preserve unrelated Updated and picker behavior.
- Existing `coga.validate.run` has a `stuck-in-progress` log-age
  warning with its own `idle_hours` argument (72 hours by default). This
  ticket adds status triage; changing validator policy is out of scope.
- Read and update `coga/lifecycle`, cited rather than attached:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md`,
  section “Triage: `coga status`”. Status is a pure read with no network or
  state mutation; its existing Updated column uses log age with Git fallback.
- Read and update `coga/configuration`, cited rather than attached:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`,
  the shared/local configuration split and schema sections relevant to the
  new setting. Both configuration files are schema validated; unknown keys
  fail loudly. Update applicable shipped configuration examples and CLI help
  in the same PR. Do not change this repo's actual config files in this task.

Independent review found no scope split or missing attached context. Shared
`code/open-pr` and `code/address-pr-comments` skills dominated their respective
measured steps and are candidates for a separate maintenance review; trimming
them is not required for this task.

No new reusable context or skill is needed. Keep owner `trial-owner` and
leave the main agent unset for the configured default at activation.
The configured peer `claude` exists, but its CLI is deliberately absent in
this trial checkout; running the later peer-review step requires a working
peer installation. This does not change the chosen workflow.

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
