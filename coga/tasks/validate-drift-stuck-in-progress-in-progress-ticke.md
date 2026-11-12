---
title: 'validate-drift: stuck-in-progress — in-progress tickets idle for days'
status: in_progress
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
step: 2 (human-executes)
agent: claude
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. validate-drift: stuck-in-progress

Remediation (recipe): ask the owner whether the task should be relaunched, blocked, paused, or bumped; the skill does not change lifecycle state silently.

This run's members: v1/01-webhook-for-slack-is-public (in_progress but idle for 78.0h), v1/18-handle-gh-not-being-installed-by-default (in_progress but idle for 173.4h).

coga validate --json is the live member list; membership is not copied between runs. Keep this ticket open until the class is empty or the decision is recorded in a context. Before closing with accepted warnings remaining, preserve the tag line 'validate-drift: stuck-in-progress', the decision, rationale, and scope in the appropriate context.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Brief for the owner (brief-and-hand-off, 2026-11-12)

**Goal.** Empty the `validate-drift: stuck-in-progress` class. For each idle in_progress ticket, choose relaunch, block, pause, or bump. Otherwise, record an accepted-warning decision in a context. Live members from `coga validate --json` on 2026-11-12:

| Member | Step (assignee) | Idle | Why it is idle |
|---|---|---|---|
| `v1/01-webhook-for-slack-is-public` | 3 cleanup-and-verify (agent) | 82.9h | The agent step was never relaunched after the approve step was bumped on 2026-11-08. Its action list mixes owner [O] items 1–4 and 7 (new Slack hook, `~/.bashrc:150`, magicator2 secret, other machines, revoke the old hook) with agent [A] checks 5, 6, 8 and 9. |
| `v1/18-handle-gh-not-being-installed-by-default` | 3 review-design (owner = **zach**, not nicktoper) | 178.4h | It waits on the owner to answer 3 design questions: pin vs latest `gh`, off-PATH fallback, and `gh_release.py` placement. |

**Ordered steps.**
1. **01-webhook.** Before you relaunch, do owner items 1–4 from its blackboard. The agent's verification needs a rotated `SLACK_WEBHOOK_URL`. Then run `coga launch v1/01-webhook-for-slack-is-public`. The agent pauses before item 7 (revoke); revoke only after item 6 passes. If the rotation can't happen soon, run `coga pause` on the ticket (or block it with the concrete ask) so validate stops flagging it as idle in_progress.
2. **18-gh.** Ping zach to answer the 3 open questions on that ticket's blackboard, then run `coga bump` (review-design → implement). If zach is unavailable, run `coga block --task v1/18-handle-gh-not-being-installed-by-default --reason "<the 3 questions>"` so the wait is visible and not stuck.
3. Optional: if long idle owner-gate steps are acceptable, record an accepted-warning decision with the tag line `validate-drift: stuck-in-progress`, the rationale, and the scope in a context. Otherwise there's nothing to record.

**Irreversible action.** Revoking the old Slack webhook `B0B0KD0BTQB` (01-webhook item 7) is permanent. Do it only after the new hook is verified, or notifications will have a gap. Every other choice here (relaunch, pause, block, bump) is a reversible lifecycle transition.

**Done check (verify-read-only step).** Run `coga validate --json`, which should show no `stuck-in-progress` entries. Alternatively, a context should hold the tag line, decision, rationale, and scope for any accepted warnings. Also confirm each member's status and step moved as decided.
