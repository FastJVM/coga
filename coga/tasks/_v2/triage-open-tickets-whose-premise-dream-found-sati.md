---
title: Triage open tickets whose premise Dream found satisfied or stale
status: draft
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 1 (brief-and-hand-off)
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-01, ks-03, ks-08, ks-15, ks-21). Dream does not edit another ticket's body or lifecycle, so these need an owner verdict (cancel with reason, record already-satisfied, or edit the stale reference):

- _v2/repoint-the-launch-topic-chat-occupancy-guard-owne (draft): premise already satisfied on main (dce68cd22; docs/contexts/coga/launch/SKILL.md:35-38 names coga/checkouts/chat as owner of direct-chat occupancy). Body also has duplicated Description/Context. Cancel or record already satisfied.
- _v2/autofix/name-cross-repo-retire-follow-ups-with-the-repo-th (draft, step 4 review): behavior shipped by #873 (git.classify_checkout foreign-linked, autoclose CheckoutOutcome.manual_command); its PR #870 closed unmerged; branch fix/retire-followup-owner still exists locally and on origin. Close as satisfied and retire the branch.
- _v2/marketing/1st-users (draft): audit point 2 cites deleted topic coga/agents; repoint to the shipped coga.toml [agents.*] comments.
- v1/41-verify-posthog-telemetry-with-the-live-clean-wheel (blocked) and v1/44-build-the-launch-plan (in_progress): blackboards cite deleted coga/telemetry and coga/telemetry/operations; repoint to coga/recurring/phone-home/operations.md and the phone-home ticket's Closed wire contract (also _v2/add-a-failed-terminal-status.md:390).
- _v2/launch-locks/checkout-exclusivity-lock design.md (in_progress, awaiting review-design): premises predate the shipped direct-chat occupancy guard (d3875e8be; coga/checkouts/chat, coga-dev/internals/launch-claims); the design should say how .coga/launch.lock composes with that guard and drop the stale 'concurrent launches safe' premise.

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

Previous ref: `triage-open-tickets-whose-premise-dream-found-sati` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
