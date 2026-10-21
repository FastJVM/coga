---
title: Count failed important alerts in recurring problems
status: draft
owner: nicktoper
workflow: null
---

## Description

Imported at the owner's request from [FastJVM/multiply PR #195](https://github.com/FastJVM/multiply/pull/195), replacing the proposed client-side inbox entry with a Coga-owned draft.

- upstream-id: multiply/dream-2026-w43-u1
- repo: FastJVM/multiply
- date: 2026-10-20
- class: gap
- target: recurring sweep problem accounting; non-fatal important notification delivery
- evidence: Multiply `autofix/configure-important-webhook-so-autoclose-s-refusal`, fix item 4 and `run-log.md`; [Multiply PR #134](https://github.com/FastJVM/multiply/pull/134)

### Reported problem

The 2026-09-22 autoclose run preserved five checkouts and attempted its human-action alert with `important=True, fatal=False`. The important webhook was unresolved, so delivery failed non-fatally, while the recurring sweep still reported `problems: 0`. The local Multiply ticket fixed configuration and explicitly left failure accounting to Coga.

The [source run record](https://github.com/FastJVM/multiply/blob/main/coga/tasks/autofix/configure-important-webhook-so-autoclose-s-refusal/run-log.md) already contains the preserved-checkout details and the missing-webhook warning. As [PR #195's review](https://github.com/FastJVM/multiply/pull/195#discussion_r4328927483) notes, simply adding that warning to raw run output would duplicate existing behavior. The missing behavior is accounting for the unsuccessful important alert in the sweep's problem summary.

### Requested outcome

Reproduce against current Coga and make a non-fatal important-alert delivery failure visible in the sweep's `problems` total. Preserve the successful underlying cleanup work and its lifecycle outcome; a notification failure must not undo it. Cover unresolved routes and transport failures, with successful or intentionally disabled notifications not counted as failures and each failure counted once.

Start with `src/coga/autoclose.py`, `src/coga/notification/__init__.py`, `src/coga/recurring_runner.py`, and the run-record accounting in `src/coga/recurring_autofix.py`. Read `coga/notifications/failures` and the relevant recurring contract before choosing the propagation mechanism. Add focused regression coverage and update the owning contract and packaged twin if behavior changes.

This is a draft for triage, not a request to change Multiply's webhook configuration.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
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
