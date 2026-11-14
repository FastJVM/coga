# Pair 283a63, output Y (author)

## Authored ticket (full)

````markdown
---
title: Flag stalled in-progress tickets in coga status
status: draft
owner: trial-owner
workflow: code/with-review
---

## Description

Make stalled work visible in `coga status`: tickets can remain `in_progress` for days after an agent session dies or an owner gate is forgotten. Mark an `in_progress` ticket as stalled when the timestamp of its most recent parseable, ticket-specific `coga/log.md` entry is older than a configurable threshold, and add `--stalled` to list only those tickets. Done means the normal view visibly identifies stalled tickets, the filter selects them correctly, a validated `coga.toml` setting controls the threshold with a sensible default, and focused tests and the owning documentation cover the behavior.

This is a read-only indication, not a new lifecycle status. Notifications, automatic transitions, recovery actions, and detecting whether an agent is alive are outside this ticket.

## Context

### Authoring assumptions

The human delegated these choices: default to 48 hours, apply only to `in_progress` tickets (including owner-held steps), and treat missing or wholly unparseable ticket history as unknown age, excluded from `--stalled`. Use a strict older-than comparison: exactly 48 hours is not stalled at the default. “Most recent” means the last parseable matching entry in file order, matching `logfile.last_activity_map`, even if timestamps are out of order. Compare against local wall-clock time, matching `logfile.append_log` and its timezone-less, minute-resolution timestamps; do not reinterpret existing log entries as UTC. This inherits the log format’s cross-timezone limitation. Future timestamps are not stalled. Show unknown log age distinctly for an in-progress ticket without changing the existing meaning of the `Updated` column. Record the chosen configuration spelling and units in help/configuration documentation; reject invalid values clearly. Keep owner `trial-owner`, omit `agent` for the configured default at activation, and use the human-selected `code/with-review` workflow.

### Implementation pointers and required reading

- `commands.status.status` delegates to `views.render_status`; keep the CLI head thin. `views.last_updated_map` feeds both status and the megalaunch picker and falls back to Git when the log has no entry. Stalled detection must use log evidence alone, without changing that shared Updated/picker behavior. Inspect `logfile.last_activity_map` and reuse its ticket-ref and timestamp parsing where appropriate; do not use file mtime or Git as a stalled-age fallback.
- Read `coga/lifecycle`, cited rather than attached: `src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md`, section “Triage: `coga status`”. Status is a pure read with no network or mutation; preserve existing directory scoping, sorting and terminal visibility. Define and test how `--stalled` combines with `--blocked` and `--dirs`, with clear errors for incompatible modes.
- Read `coga/configuration`, cited rather than attached: `src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`, sections “Allowlists”, “Unknown keys fail loud”, and “Other configuration surfaces”. Inspect `config.load_config` and its allowlists before choosing the setting. Update the package-owned lifecycle/configuration contracts and any dependent help or configuration template in the same PR. Do not create local copies of shipped topics.
- Start from existing view/status, logfile, and configuration tests. Cover old/recent entries, multiple and out-of-order entries per ticket, local-time comparison, other-ticket isolation, threshold boundaries, non-in-progress states, missing/malformed history, configuration default/override/invalid input, and the filter's interaction with existing modes. Use controlled times rather than sleeping.

No additional contexts or skills are attached: the required facts and targeted reads are above. No new reusable knowledge file is needed. The configured peer is `claude`; its CLI is deliberately unavailable in this trial checkout, so the selected workflow can be authored here but peer execution requires an available configured peer later.

Independent authoring review found no need to split the scope or attach further contexts. Trimming the open-pr skill’s incident/recovery material and the address-pr-comments skill’s GraphQL examples is separate workflow maintenance, outside this ticket.

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
