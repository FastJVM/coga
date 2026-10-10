---
title: Stop publish union merges from re-adding log lines already on control
status: draft
owner: nicktoper
workflow: null
---

## Description

`git.publish` can add a second copy of a `coga/log.md` line that is already on control. Fix the base selection so union-merged paths never re-add a line that control already has. Done when the reproduction below lands a single copy, existing union behaviour (concurrent appends on both sides survive) is unchanged, and `coga/internals/spool-merge` describes the new contract.

## Context

Split out of `prevent-duplicate-session-usage-records-from-infla` (2026-10-09). That ticket dedupes usage records at read time (`usage.load_records`, exact JSON message text). This one fixes the writer-side root cause.

- Mechanism: `git._build_tree` merges `merge=union` paths with `_merge_union_bytes(current=<control>, base=<merge-base(HEAD, control)>, other=<working>)`. When HEAD lags a line already on control, and that line sits at a different position in the working copy, `git merge-file --union` emits it twice. Reproduced: base `A`, control `A X Y`, working `A Z X` → `A X Y Z X`. Same-position cases (working `A X Z`) keep one copy.
- Evidence: across this repo, magicator, multiply, and thinkpick, 24 duplicated usage records. Each extra copy came from a later single-parent publish commit (`Log: …`, `Sync coga state`, `Ticket: …`), never from a merge commit or a double write. Example: `c8a3cdfda` re-adds a record that its parent `276448100` had already added.
- Affects every `log.md` line (audit lines such as `launched` too) and `retires.md`, not only usage records.
- Changes the state-publication contract. Owning topics: `coga/internals/spool-merge` and `coga/internals/state-publication`.
- Related: `tell-agents-never-to-git-commit-coga-task-and-log` covers the squash-merged-PR variant (#732, `81cefcb7f`).
- Do not rewrite existing logs. Historical duplicates are handled by reader dedupe.

Concept-capture draft: no workflow chosen yet. Run `coga ticket stop-publish-union-merges-from-re-adding-log-lines` to finish it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
