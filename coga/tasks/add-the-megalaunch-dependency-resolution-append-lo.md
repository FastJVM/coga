---
title: Add the megalaunch dependency-resolution append_log writer to the log-writers
  inventory
status: active
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream recurring/dream, period 2026-W47 (run 20261118T170921Z), Phase 6 disposition. Target docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md is also edited by open PRs #1247 and #1248, neither of which carries this fix; apply it after or on top of those PRs. Phase 2 shard ks-15 and Phase 3 shard ca-02 reported it independently.

Route: open a PR against the target once the overlapping PR(s) have landed or been rebased; the fix is pr-required (human review).

Finding: log-writers inventory misses megalaunch dependency-resolution append (32 vs 33 sites)

- shard: ks-15
- class: stale
- target: docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md
- area: coga-dev/internals/state-publication
- owner: local

The topic claims "The startup-group implementation inventory has **32 direct call sites**" and tells writers to re-inventory all direct `append_log` calls under `src/`. `grep -rn "append_log(" src/` now finds 33: the table omits `coga/megalaunch.py::_publish_partial_dependency_resolution` (appends "resolved finished dependency blockers (still blocked)" under `git.state_lock`, then publishes ticket+log via strict `git.sync_task_state(..., expect={ticket: source_bytes}, strict=True)`; uncertain publish retains local state, refused write restores the ticket). It was added by fa763ff90 (2026-11-10, "Keep unfinished dependency blockers open in megalaunch"), after the topic's last edit (6d1ca237f, 2026-11-03). Add a row for it (megalaunch strict task-plus-log publication; refused write restored, uncertain retained) and update the count to 33.

Finding: log-writers inventory misses megalaunch's dependency-resolution append_log (33 sites, not 32)

- shard: ca-02
- class: drift
- target: docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md
- area: coga-dev/internals
- owner: local

docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md:14 claims "The startup-group implementation inventory has **32 direct call sites**" and the table (lines 18-31) is described as the complete `append_log` writer inventory under `src/`. A grep of `append_log(` under `src/` (excluding the definition) finds 33 call sites; the unlisted one is `src/coga/megalaunch.py:1780` in `_publish_partial_dependency_resolution` ("resolved finished dependency blockers (still blocked)"), added by fa763ff90 on 2026-11-11 after the inventory was last edited (6d1ca237f, 2026-11-03). Its publisher is the strict `git.sync_task_state(..., expect={ticket: source_bytes}, strict=True)` call in the same function, which restores a refused write and keeps an uncertain one as evidence. Add a `coga/megalaunch.py::_publish_partial_dependency_resolution` (1) row and update the count to 33. Source of truth: src/coga/megalaunch.py:1758-1800.

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

## Dev

branch: coga/add-the-megalaunch-dependency-resolution-append-lo
base: main
remote: origin
reviewed: bc4a9bdb31b812e504f8ec9beb941a7607f6c579

## Peer review

- Human confirmed using origin/main after PRs #1247 and #1248 merged. Coga
  published the unblock in 12bc5e02a. The isolated worktree is
  /home/n/Code/coga-log-writers-review, preserving the active checkout.
- Rebased the inventory branch onto origin/main. Current source has 35
  direct append_log calls. Megalaunch now lives in coga_edge and has a
  second writer for failed-start restoration. The two rows and the headline
  count were reconciled in bc4a9bdb3.
- Codex directly reviewed the rebased docs and checked both Megalaunch
  publication paths and the owned rollback helper. Claude wrote the original
  inventory change. Codex authored and reviewed the reconciliation edits.
- After verification, an admitted peer-review launch is required to advance
  if the ticket is still active following unblock.

## PR

```yaml
title: Add missing megalaunch writers to the log-writers inventory
author: claude
author_evidence: >-
  Claude implemented the original dependency-resolution row. Codex updated
  its path and count and added the failed-start restore row during reconciliation.
head: bc4a9bdb31b812e504f8ec9beb941a7607f6c579
base: 12bc5e02a729155c8b1c913abf36b6c1c5503540
depth: skim
rationale: >-
  The docs-only diff records the two megalaunch writes and their existing
  publication and rollback behavior.
implementation: >-
  Add the dependency-resolution and failed-start restore writers in coga_edge
  and update the direct call-site count from 32 to 35.
deviations: >-
  Current main has a second megalaunch writer that the original ticket predates.
limitations: >-
  Native Windows and macOS verification is deferred to release.
files:
  docs/contexts/coga-dev/internals/state-publication/log-writers/SKILL.md: >-
    Add both missing megalaunch writers and reconcile the inventory count.
review:
  reviewer: codex
  kind: self
  status: passed
  head: bc4a9bdb31b812e504f8ec9beb941a7607f6c579
  base: 12bc5e02a729155c8b1c913abf36b6c1c5503540
  detail: >-
    Codex directly reviewed the full diff, independently checking Claude's
    original row and checking its own reconciliation edits. No open findings.
checks:
  - command: /home/n/Code/coga/.venv/bin/python -m pytest -xq -p no:cacheprovider
    status: passed
    head: bc4a9bdb31b812e504f8ec9beb941a7607f6c579
    base: 12bc5e02a729155c8b1c913abf36b6c1c5503540
    detail: >-
      5179 passed, 33 skipped in 1008.70s on Linux with Python 3.12.12,
      with inherited Coga variables cleared,
      an absolute PYTHONPATH pointing to the review worktree's src, and an
      isolated TMPDIR outside any Coga repo. The first run inherited a
      repository-local TMPDIR and a relative PYTHONPATH and failed in fixtures.
  - command: git grep -n -F 'append_log(' HEAD -- src/ | rg -vc 'def append_log'
    status: passed
    head: bc4a9bdb31b812e504f8ec9beb941a7607f6c579
    base: 12bc5e02a729155c8b1c913abf36b6c1c5503540
    detail: "35 source calls. Independently summed the inventory rows to 35."
  - command: git diff --check origin/main...HEAD
    status: passed
    head: bc4a9bdb31b812e504f8ec9beb941a7607f6c579
    base: 12bc5e02a729155c8b1c913abf36b6c1c5503540
    detail: "No whitespace errors."
```

## Blockers

- [x] [2026-11-18 21:07] [agent:codex] id=20261118T210707 Reconcile this inventory after v1/microkernel/move-slack-fyis-to-a-command-ticket (PR #1247) and v1/microkernel/08-residual-command-surfaces (PR #1248) land, or provide a reconciled stacked base for both. Recount append_log calls after incorporating their changes before opening this PR.
  resolved: [2026-11-22 09:23] [human:nicktoper] Confirmed by the human: PRs #1247 and #1248 are merged into origin/main. Reconcile on origin/main in an isolated worktree, preserve the active checkout and existing branches, and recount append_log writers before publication.

- [x] [2026-11-19 11:18] [agent:codex] id=20261119T111841 PRs #1247 (v1/microkernel/move-slack-fyis-to-a-command-ticket) and #1248 (v1/microkernel/08-residual-command-surfaces) are both still open. Resume after both land, or provide the intended reconciled stacked base. Recount append_log call sites on that base before publishing.
  resolved: [2026-11-22 09:23] [human:nicktoper] Confirmed by the human: PRs #1247 and #1248 are merged into origin/main. Reconcile on origin/main in an isolated worktree, preserve the active checkout and existing branches, and recount append_log writers before publication.

- [x] [2026-11-20 18:45] [agent:codex] id=20261120T184549 Both overlapping PRs (#1247 and #1248) merged and are on fetched origin/main, so that is the proposed base for resolving both prior asks. Confirm that resolution and resume peer review from a clean current main checkout. The supplied checkout is occupied by refresh-the-v1-microkernel-task-readmes-after-the on refresh-v1-microkernel-readmes-after-retro with unmerged commit 258ca14c7 and no linked PR. All six unstaged files matched fetched control before blocking. Preserve that branch and commit; rebase the inventory branch and recount writers before publication.
  resolved: [2026-11-22 09:23] [human:nicktoper] Confirmed by the human: PRs #1247 and #1248 are merged into origin/main. Reconcile on origin/main in an isolated worktree, preserve the active checkout and existing branches, and recount append_log writers before publication.


---

## Blocker reminders

- 075595a1991e last_reminded: 2026-11-19 09:03

- 65aaa87819fe last_reminded: 2026-11-20 12:11
