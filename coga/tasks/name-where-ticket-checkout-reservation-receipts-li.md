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
step: 3 (open-pr)
agent: claude
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
- Original implementation commit: `88693816c4de07334feb649b116b2eef7f5992d0`.
  The implementation suite passed (4121 passed, 10 skipped); the review below
  records the rebased revision and fresh verification.

## Peer review

- Direct Codex review **completed** in launch
  `ba49c89b-2461-4a12-96fc-179ae11e3ab3`, covering head
  `471f992dc28e00d80489556c515010a9ff193e80` against base
  `f432db35b974aa17aee3c3ec2d8c031f38d200ec`. No must-fix findings or source
  edits. Checked the complete one-file diff against `_RECEIPT_DIR`,
  `_receipt_path`, `_reserve_and_create`, `_discard_receipt`, and existing
  reservation regression tests. The local-only topic has no packaged twin;
  the change adds no interactive surface needing a terminal check.
- Actual author and reviewer are both Codex, so this is **self-review** under
  the PR preparation identity rule. The fresh review session and the ticket's
  configured Claude agent do not establish independent authorship.
- Rebased onto current main before reviewing, then pushed with an explicit
  `--force-with-lease` against the original implementation commit. Final
  fetches confirmed main still at the base above. Returned this checkout to
  clean, current `main` before writing the handoff. The topic blob remains
  `04fed2e77c22ac421f554d102b6169451b970957`; no fixes changed the reviewed tree.
- The full suite passed on that exact head/base: **4121 passed, 10 skipped in
  390.89s**, Linux/Python 3.12.12, pytest 9.1.1. The command is in `## PR`.
  Final whitespace and clean-tree checks passed. PR creation remains the next
  mechanical step; no PR has been opened. The read-only PR formatter accepted
  the preparation as `[skim · A:codex R:codex(self)]` with no evidence gaps;
  frontmatter and ticket intent remain byte-identical to control.
- Earlier verification attempts on the same head/base encountered environment
  problems, now superseded by the full passing run:
  - `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest` exhausted
    `/tmp`'s 1,048,576 inodes: 1 failed, 1395 passed, 10 skipped, 2725 errors
    in 202.81s. Moved only this session's generated `pytest-76` tree onto the
    repository filesystem, preserving the failure log.
  - Retrying with
    `TMPDIR=/home/n/Code/coga/.venv/receipt-peer-review-vmbladan/tmp` exposed
    fixture failures because the temporary contexts inherited the host
    checkout's `.venv` ignore rule; interrupted that run. The focused command
    `TMPDIR=/home/n/Code/coga/.venv/receipt-peer-review-vmbladan/tmp PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --tb=short tests/test_compose.py::test_compose_includes_all_sections`
    confirmed this with 1 failed in 0.25s and the explicit ignored-context
    diagnostic. The final run used an on-disk temporary directory outside any
    Git checkout. No product change was needed.
  Logs are retained in `.venv/receipt-peer-review-vmbladan/`:
  `failed-pytest.log`, `pytest.log` (interrupted), and `pytest-isolated.log`
  (complete passing run).

## PR

```yaml
title: Document ticket checkout reservation receipt storage
author: codex
author_evidence: >-
  Actual implementing agent was Codex, coga-launch
  3a462e95-def8-4763-870e-7d3ea5751f18. The ticket's configured agent is claude;
  authorship records the actual session identity.
head: 471f992dc28e00d80489556c515010a9ff193e80
base: f432db35b974aa17aee3c3ec2d8c031f38d200ec
depth: skim
rationale: >-
  Bounded documentation clarification matching the existing implementation.
  Direct review completed without findings and the full suite passed on the
  final rebased revision. Read the self-review and platform limitations.
implementation: >-
  Names checkouts._RECEIPT_DIR and the git rev-parse command in the Branch
  creation bullet, explains the risk of publishing unignored .coga/ files,
  and states that receipts are retry evidence whose removal never deletes
  a branch.
deviations: None; the requested explanation is in the specified local-only topic.
limitations: >-
  Verification used Linux/Python 3.12.12; no Python 3.11 or native Windows run
  was performed. Both author and reviewer were Codex, so no independent review
  is claimed. Earlier test attempts hit /tmp inode exhaustion and then ignore
  rules inherited by fixtures under .venv; the final complete run passed with
  an on-disk TMPDIR outside any Git checkout. Peer-review notes retain the
  failed/interrupted attempts and their evidence.
files:
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: >-
    Owns the launch branch-preparation details and now documents the receipt
    location and publication rationale. The coga-dev namespace has no packaged twin.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 471f992dc28e00d80489556c515010a9ff193e80
  base: f432db35b974aa17aee3c3ec2d8c031f38d200ec
  detail: >-
    Direct review completed in coga-launch ba49c89b-2461-4a12-96fc-179ae11e3ab3
    after the final rebase. Checked the full diff, receipt implementation,
    regression tests, packaging classification, and PR #1106 ancestry.
    No must-fix findings; no fixes were needed. Actual author and reviewer
    identities are both Codex, so this is self-review.
checks:
  - command: TMPDIR=/home/n/Code/coga-review-hwuipnvu PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: 471f992dc28e00d80489556c515010a9ff193e80
    base: f432db35b974aa17aee3c3ec2d8c031f38d200ec
    detail: >-
      4121 passed, 10 skipped in 390.89s on Linux/Python 3.12.12, pytest 9.1.1.
      Ran on the clean rebased branch; no subsequent source edit or rebase.
      Used an isolated temporary directory after the environmental failures
      recorded under Peer review. The complete log is
      .venv/receipt-peer-review-vmbladan/pytest-isolated.log.
  - command: |
      git diff --check
      git diff --check origin/main...HEAD
    status: passed
    head: 471f992dc28e00d80489556c515010a9ff193e80
    base: f432db35b974aa17aee3c3ec2d8c031f38d200ec
    detail: Working tree and final one-file branch diff had no whitespace errors.
  - command: git diff --exit-code HEAD
    status: passed
    head: 471f992dc28e00d80489556c515010a9ff193e80
    base: f432db35b974aa17aee3c3ec2d8c031f38d200ec
    detail: Clean tested tree after the suite, before pushing and returning to main.
  - command: coga validate --json
    status: not-run
    detail: No configuration, workflow, task-model, or validation behavior changed.
```
