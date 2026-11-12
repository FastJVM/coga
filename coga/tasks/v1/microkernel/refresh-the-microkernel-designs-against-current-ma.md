---
title: Refresh the microkernel designs against current main
status: in_progress
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 1 (agent-produces)
agent: claude
contexts:
  - coga-dev/principles
  - coga-dev/microkernel/objectives
---

## Description

The microkernel tickets were parked on 2026-10-27 and pulled back into v1 on 2026-11-12 because hackability is a base promise of the open-source 1.0: a contributor (Zach) got lost trying to change the peer-review behavior. Their designs and inventories are stale (launch.py is now 4,577 lines; launch-decomposition still cites 3,782). Run the _v2/README premise check on every ticket in v1/microkernel/ against current main, refresh each design's inventory and proposed boundary, flag what already shipped or no longer applies, and propose the execution order and which ticket owns the workflow-declared checkout policy. The owner decides the refreshed scope before any child implementation resumes.

Judge every design against the attached `coga-dev/microkernel/objectives`
context, linked from the group's README. For each child, state which objective
it advances and drop or defer work that advances none.

### Owner clarification — 2026-11-12

The owner asked to establish the objectives in a standing Coga-dev context
before continuing the design refresh. Its owner is
`docs/contexts/coga-dev/microkernel/objectives/SKILL.md`. The refreshed designs
will apply that direction, including access to editable wheel-delivered
behavior; detailed scope and execution order still need review.

## Context

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

## Current handoff

- Starting checkout: clean `main`, fetched and fast-forward checked at
  `63e7bb28129de084f7f619c3a8dfa2e8762b1550` on 2026-11-12. No branch or PR is
  recorded for this planning step; edits are Coga design state on control.
- The owner redirected this session to the objectives only. Their standing
  owner is now `coga-dev/microkernel/objectives`, attached above; the group and
  the current-boundary topic link to it. Command classification, migration
  order, and child implementation have not been approved by that clarification.
- The full refresh remains pending. No child design or lifecycle state was
  edited. Keep this step open for the continuing attended discussion.
- Preliminary evidence for later verification: `commands/launch.py` is a
  100-line adapter and `src/coga/launch.py` is the 4,577-line service (the split
  landed in `b3007ef2e`); edge wheel delivery landed in `bc46823c4`, and the
  current registry has 12 recipes. These observations are not a completed
  premise check or an accepted scope.

## Objectives-context verification

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/refresh-the-microkernel-designs-against-current-ma --json`
  — 1 task OK; no issues or fixes.
- Read-only checks: the new context resolves through `resolve_context_path`,
  its links and the group's links to it exist, its header contains only
  `name` and `description`, and this ticket preserves all CLI-owned fields
  and exactly one blackboard fence. Context size: 111 lines, about 1,459 tokens.
- `git diff --check` — clean. Documentation only; behavioral tests are not
  needed for this objectives note. The overall refresh is not complete, so
  no workflow transition is requested by this handoff.
