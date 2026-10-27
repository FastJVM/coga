---
title: Name where ticket checkout reservation receipts live in git-refresh
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:3ed57e1d-1830-4374-8c91-bb1e587262b2
---

## Description

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-03; extract from done ticket automate-checkout-setup-and-deduplicate-instructio, which stays on disk as retirement debt because its branch checkout-prep-automation survives in the sibling clone /home/n/Code/codex/coga). Target: docs/contexts/coga-dev/internals/git-refresh/SKILL.md 'Branch creation' (local-only).

The ticket's implementation deliberately stored branch-reservation receipts in the worktree's private Git directory (git rev-parse --git-path coga/checkout-receipts; src/coga/checkouts.py _RECEIPT_DIR) instead of the spec'd .coga/, because a state sweep could publish .coga/ files in a repo that does not ignore .coga/. Only the module docstring says so. Suggested sentence after 'never brings back its name or base.': 'The reservation receipt lives in this worktree's private Git directory (checkouts._RECEIPT_DIR under git rev-parse --git-path), not .coga/, because a sweep could publish .coga/ in a repo that does not ignore it; it is retry evidence, never task state, and removing it never deletes a branch.'
Why a draft: open Retro PR #1106 edits the same file (other hunks); land after it.

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

## Dev

branch: docs/ticket-checkout-receipt-location

## Implementation handoff

- Added the receipt's private Git location, the reason to avoid `.coga/`, and
  its retry-only/removal semantics to the Branch creation bullet in the
  local-only git-refresh topic. Verified against `src/coga/checkouts.py`
  (`_RECEIPT_DIR`, `_receipt_path`, and `_discard_receipt`). No runtime,
  fixture, or packaged-context change was needed.
- PR #1106 merged on 2026-10-26 as
  `cfe7d33988a49f56d7ba59a261b9245bb2b552b3`, an ancestor of the implementation
  base; the ordering dependency is satisfied.
- Committed and pushed `88693816c4de07334feb649b116b2eef7f5992d0`.
  `git fetch origin main` followed by `git rebase FETCH_HEAD` reported the
  branch already up to date. A second fetch before returning to `main`
  confirmed control remained at `963c515ca3d6723bd56bbd111ce2af94b49adf54`.
  The manual checkout procedure returned this checkout to clean, current
  `main` before writing this handoff.
- The full suite passed on Linux/Python 3.12.12: 4121 passed, 10 skipped.
  It ran with only the topic dirty; the tested blob
  `04fed2e77c22ac421f554d102b6169451b970957` matches the committed blob,
  the commit's parent matches the tested starting HEAD, and
  `git diff --exit-code HEAD` confirmed the committed tree was identical.
  No rebase or edit changed the tested tree.
- No unresolved implementation issues or adjacent bugs found. Independent
  review and PR creation remain later workflow steps; no PR was opened.

## PR

```yaml
title: Document ticket checkout reservation receipt storage
author: codex
author_evidence: >-
  Actual implementing agent was this Codex session, coga-launch
  3a462e95-def8-4763-870e-7d3ea5751f18. The ticket's configured agent is claude;
  authorship records the actual session identity.
head: 88693816c4de07334feb649b116b2eef7f5992d0
base: 963c515ca3d6723bd56bbd111ce2af94b49adf54
depth: deep
rationale: >-
  The change is a bounded documentation clarification with the full suite
  passing, but independent review has not run yet.
implementation: >-
  Names checkouts._RECEIPT_DIR and the git rev-parse command in the Branch
  creation bullet, explains the risk of publishing unignored .coga/ files,
  and states that receipts are retry evidence whose removal never deletes
  a branch.
deviations: None; the requested explanation is in the specified local-only topic.
limitations: >-
  Verification used Linux and Python 3.12.12; no Python 3.11 or native Windows
  run was performed. Independent review awaits the next workflow step.
files:
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: >-
    Owns the launch branch-preparation details and now documents the receipt
    location and publication rationale. The coga-dev namespace has no packaged twin.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent review is the next peer-review step; implement does not run self-QA.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: 88693816c4de07334feb649b116b2eef7f5992d0
    base: 963c515ca3d6723bd56bbd111ce2af94b49adf54
    detail: >-
      4121 passed, 10 skipped in 572.88s on Linux/Python 3.12.12, pytest 9.1.1.
      The handoff records proof that the tested working tree equals this commit.
  - command: |
      git diff --check
      git diff --check origin/main...HEAD
    status: passed
    head: 88693816c4de07334feb649b116b2eef7f5992d0
    base: 963c515ca3d6723bd56bbd111ce2af94b49adf54
    detail: Both the working change and committed one-file diff had no whitespace errors.
  - command: git diff --exit-code HEAD
    status: passed
    head: 88693816c4de07334feb649b116b2eef7f5992d0
    base: 963c515ca3d6723bd56bbd111ce2af94b49adf54
    detail: Clean tree after commit; tested and committed topic blobs matched exactly.
  - command: coga validate --json
    status: not-run
    detail: No configuration, workflow, task-model, or validation behavior changed.
```
