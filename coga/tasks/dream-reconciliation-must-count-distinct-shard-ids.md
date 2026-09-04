---
slug: dream-reconciliation-must-count-distinct-shard-ids
title: Dream reconciliation must count distinct shard ids, not completion lines
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
secrets: null
step: 3 (open-pr)
---

## Description

`bootstrap/dream/scan/scan-protocol` tells Dream to reconcile "the active leaf assignments in
`manifest.md` against the completion lines in `progress.md`", but never says to de-duplicate those
lines by shard id. `progress.md` is append-only and shared by every shard, and a shard can append
its completion line more than once.

That happened in the 2026-08-24 run: `ca-06` wrote `ca-06 complete — 5 findings` twice, a naive
line count read 8/8 while `ca-04` was still working, Dream reconciled early, saw `ca-04` as
never-returned, and superseded a healthy shard. Cost was one wasted retry.

The inverse is the dangerous case: with two shards missing and one duplicated line, the same count
lets Dream declare full corpus coverage while a shard is genuinely absent — the exact failure the
protocol was written to prevent.

Fix: state that reconciliation counts **distinct shard ids**, and that it runs only at the barrier,
never while shards are still reporting. Edit both the live skill and its packaged twin.

## Context

Found by Dream 2026-08-24 by hitting it — this is Dream reporting a defect in its own protocol,
not a corpus finding.

Worth pairing with the related observation from the same run: a shard that goes idle *after* writing
its completion line is fine, and several did. The disk record is what makes that distinguishable
from a shard that died silently — which is the whole reason the protocol exists (see the done
ticket `dream-phases-2-3-cannot-complete-scan-subagents-re`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/756
branch: dream-reconcile-distinct-shards
worktree: /home/n/Code/codex/coga-dream-reconcile-distinct-shards

## Findings — edit surface

`coga/.agent-skills/bootstrap/dream/scan/scan-protocol` is a gitignored symlink
into another checkout's packaged templates, not a second tracked file. So the
ticket's "live skill and its packaged twin" is one tracked file:
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md`.
(Same conclusion the parent ticket `dream-phases-2-3-...` recorded.)

The genuinely-duplicated tracked pairs that also state the reconciliation rule:

- `coga/recurring/dream/ticket.md` + `src/coga/resources/templates/coga/recurring/dream/ticket.md`
  — step 4 "Reconcile before believing the result" is where Dream (not the
  shard) is told what to compare, so the barrier rule belongs here.
- `coga/contexts/coga/architecture/SKILL.md` + its packaged copy — the one-line
  canonical summary "reconciles only active leaf assignments".

## Implemented

Commit `3e49829b` on `dream-reconcile-distinct-shards`, rebased onto
`origin/main` at `3911ff80`.

The rule is stated twice on purpose, because it has two different readers:

- **`scan-protocol/SKILL.md`** (shard-facing + the "What Dream does with this"
  contract) — reconciliation is now against "the **set of distinct shard ids**
  that wrote a completion line", with a new `### Two rules that make
  reconciliation mean what it says` section carrying both the id-set rule (with
  the 2026-08-24 `ca-06`/`ca-04` incident as the worked example, and the
  inverse false-full-coverage case) and the barrier rule. `progress.md`'s bullet
  in "The scan directory" now says nothing in it is unique. The completion-line
  section now tells a shard to re-append rather than risk omitting the line —
  safe precisely because Dream reconciles by id.
- **`recurring/dream/ticket.md`** (both tracked copies) step 4 — Dream, not the
  shard, is the one that waits for the barrier and does the comparison, so the
  "reconcile only at the barrier, once every shard subagent you launched for
  this attempt has returned" instruction lands here. Kept the existing literal
  sentence opener "Compare the active leaf shard rows in `manifest.md`" — an
  existing assertion pins it.
- **`coga/contexts/coga/architecture/SKILL.md`** (both copies) — the canonical
  one-line summary now says reconciliation happens at the barrier and by
  distinct completing shard id rather than by counting lines.
- **`tests/test_dream_worker_templates.py`** — assertions added to the three
  existing tests rather than new ones, matching how this suite already pins
  contract prose. Note the protocol test's `norm` does not strip `**`, so the
  skill prose deliberately avoids emphasis inside the pinned phrases.

## Verification

- `python -m pytest` (venv on 3.12): 2233 passed, 1 failed —
  `tests/test_notification_messages.py::test_recurring_create_is_silent` fails
  with `NotADirectoryError` on `coga/tasks/work.md/ticket.md`. Confirmed
  pre-existing: it fails identically with this branch's changes stashed. Not
  touched here.
- `tests/test_dream_worker_templates.py` + `tests/test_packaging.py`: 18 passed.
- Environment note: the default `python` here is 3.9, which Coga rejects. Tests
  need a 3.11+ interpreter; `tests/test_packaging.py` additionally needs
  `hatchling`, so the run used a scratch 3.12 venv with `.[test]` installed.

## Adjacent — not fixed here

`test_recurring_create_is_silent` above. Fails on clean `main`; worth its own
ticket if it is not already tracked.

## Peer review — 2026-09-04

- Ran `codex review --base main` from the recorded feature worktree. No
  actionable regressions or must-fix findings; the reviewer also ran the 18
  Dream-template and packaging tests successfully. No implementation edits
  or additional fix commit were needed.
- Ran `git fetch origin main`, then `git rebase FETCH_HEAD` unconditionally.
  Rebase completed without conflicts onto `986e1bd3`; the feature commit is
  now `0f10468f`. Incoming commits changed only task state and the audit log.
  Both live/packaged pairs remain byte-identical after the rebase, and
  `git diff main...HEAD --check` passes.
- Installed `.[test]` into the isolated Python 3.12 environment
  `/tmp/coga-dream-review-venv-20260904`. The full suite on the rebased
  feature worktree finished: **2233 passed, 1 failed**, in 151.32 seconds.
  The only failure is the pre-existing notification test below; the Dream
  and packaging tests all pass. Pytest also warned that the sandbox prevented
  writing its optional cache in the feature worktree.
- Independently reproduced `test_recurring_create_is_silent` on primary
  `main` with the same environment: `NotADirectoryError` for
  `coga/tasks/work.md/ticket.md`. The traceback uses primary-checkout source,
  confirming this failure is unrelated to the Dream changes.
- `coga validate --task dream-reconciliation-must-count-distinct-shard-ids --json`
  passes with one valid task and no issues.
- `git range-diff 3911ff80..3e49829b 986e1bd3..HEAD` confirms the reviewed
  patch is unchanged by rebase. The feature branch is clean and one commit
  ahead of the fetched `main`.

Exact verification commands (first from the feature worktree, second from
the primary checkout):

```sh
PYTHONPATH=/home/n/Code/codex/coga-dream-reconcile-distinct-shards/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest
PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent -q
```

## PR

Duplicate shard completion lines could make Dream reconcile early or claim
full coverage while an assigned shard was missing. Require reconciliation at
the barrier and match every active leaf id against distinct completing shard ids.

Update the shared scan protocol, both recurring Dream templates, both architecture
contexts, and the existing contract assertions. Completion records remain valid
when a finished shard goes idle.

Test plan: `python -m pytest` with Python 3.12 and `.[test]`: 2233 passed; the sole failure, `test_recurring_create_is_silent`, reproduces on `main` with the same `NotADirectoryError`. The reviewer also ran `python -m pytest -q tests/test_dream_worker_templates.py tests/test_packaging.py`: 18 passed.
