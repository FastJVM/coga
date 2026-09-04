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
step: 1 (implement)
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
