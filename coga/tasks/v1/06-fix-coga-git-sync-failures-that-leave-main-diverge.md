---
title: Fix coga git sync failures that leave main diverged from origin
status: in_progress
owner: nicktoper
contexts:
- coga/state-publication
- coga-dev/internals/state-publication
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 1 (design)
agent: claude
launch_generation: pending:b888f4ef-9308-48d7-8781-159a34eb9aaf
---

## Description

Coga's automatic git sync keeps failing in the Multiply checkout
(`~/Code/multiply`), and on 2026-09-29 a failure left local `main` diverged
from `origin/main`, forcing a manual reset. Diagnose each failure class
against the **current** Coga revision, fix what is fixable in code, and record
an explicit decision for the rest, so sync either succeeds or fails loudly
with a remedy and never leaves `main` diverged. Do not assume Coga's sandbox
makes `.git` read-only: on the owner's machine `.git` is read-write, so a
"Read-only file system" error comes from whatever sandbox the failing process
ran in, and that process has to be identified.

Done when:

- Every failure class from the recount (see Context) is either fixed or
  explicitly accepted, with the reason written down in the design spec's
  per-class disposition; a durable decision (for example the `/tmp` ENOSPC
  one) also lands in `coga-dev/internals/state-publication` in the same PR. If the fix is an
  owner-side `coga.toml` / `coga.local.toml` or agent-CLI settings change, the
  design names it as an open question for the `review-design` gate; the owner
  applying it counts as fixed.
- The divergence case is confirmed covered: PR #948 already realigns local
  `main` over state-only commits control carries. Confirm it covers *a failed
  publish followed by a later sync* by citing the existing test in
  `tests/test_git.py`, or add only the missing regression test, asserting
  `main` ends level with origin and any refusal is loud and names what to run.
- Owner-run check at the final `review` gate (not the agent's job): after the
  owner installs the PR build in Multiply, a launched Codex session and a
  launched Claude session each finish a step with normal network access and
  add no `[git] sync failed` line for the classes marked fixed. The owner
  attaches the `coga/log.md` excerpt to the PR, noting each session's agent
  sandbox and network settings so a passing run doesn't hide the setting
  that caused the failures.

## Context

### Incident (2026-09-29)

Evidence comes from Multiply (`~/Code/multiply`, its `coga/log.md`), a
consumer repo; the fix lands here in Coga. Local `main` was 1 ahead / 5
behind `origin/main` with uncommitted `coga/log.md` and ticket edits, all of
which had already reached origin through separate sync commits; the working
tree was byte-identical to `origin/main`. Fixed by hand with
`git branch backup/main-94da4bda HEAD && git reset origin/main`. The
`backup/main-94da4bda` branch still exists in Multiply as a repro artifact;
after #948 it reproduces an already-handled case.

**Already fixed since:** PR #948 (`f7fde464b`, merged 2026-10-05) made
`git.fast_forward_control` realign local control when
`git._local_control_subsumed` proves every local-only commit is Coga state
control already carries (`git._realign_control`); otherwise
`git._divergence_message` refuses with a `git pull --rebase --autostash`
remedy. Tests: `tests/test_git.py` ("hand commit was realigned away", the
"realigning a state-only divergence" block). Do not add another realignment
path; reuse this one.

### Failure classes — recount, don't trust

Recount from Multiply with:

```
grep "\[git\] sync failed" ~/Code/multiply/coga/log.md
```

As of 2026-11-02: 263 lines (68 in Aug, 163 in Sep, 32 in Oct), `[coga]` slug
= repo-wide sweep, other slugs = ticket-scoped sync. Classes seen:

| Class | Window | Notes |
| --- | --- | --- |
| `git fetch` / push → `Could not resolve host: github.com` | 08-14 → 09-21; 4 push failures in Oct | Network unavailable in the publishing process; DNS failure alone does not prove sandbox denial |
| `git hash-object` → `unable to create temporary file: Read-only file system` | 09-22 → 10-14 (27 in Oct) | Process ran where `.git` objects were not writable. Check whether the current revision still produces it; last seen 10-14 |
| `git add` → `.git/index.lock: Read-only file system` | 08-26 | Same shape, `~/Code/codex/multiply` checkout |
| `git rm --cached` → `/tmp/coga-git-index-*.lock: No space left on device` | 10-27 | New class: temp-index write on a full `/tmp`. Decide fix vs. accept; the design may split it into its own ticket if the fix is more than small |
| Rebase conflict (`1678fe5`), rebase blocked by untracked files, autostash reapply failure | 08-19, 09-13, 09-17 | Predate #848 "Simplify git sync" (`1210b7c39`, 2026-09-21); current `git.py` has no rebase/autostash sync path, only a hint string. Confirm and record as resolved |

The fetch → `hash-object` switch lines up with #848: once publish writes
objects before fetching, a restricted session fails on `hash-object` first.
This may be one cause seen through two code paths. Check which Coga version
Multiply runs (owner machine had `coga 0.4.1` on 2026-11-02) against when each
failure was logged.

### What to find out

Start with the version check: Multiply's `coga` version against each
failure's date. #848 and #948 both shipped in `v0.4.1` (tagged
2026-10-20), and the October `hash-object` failures (last 10-14) predate
it. The design reports how many failures remain after the owner installed
0.4.1, per class. If the agent's sandbox cannot read `~/Code/multiply`,
ask the owner to paste the grep output (that denial is itself evidence
for question 1).

1. Which process and environment ran each `hash-object` / `index.lock` /
   network failure, and why `.git` was unwritable or the network unreachable
   there. It is not clearly Codex-specific: failing entries include
   `[agent:claude] advanced … → codex` (09-22 10:32) and
   `[human:nicktoper] advanced … → codex` (09-29 08:59). Neither repo's
   `[agents.claude]` / `[agents.codex]` sets a sandbox flag, so check both
   CLIs' defaults and user-level settings, and the operator/agent fields
   around each failure. Agents may not edit `coga.toml` / `coga.local.toml`;
   propose changes to the owner. EROFS errors already report the checkout
   path (`test_erofs_hash_failure_keeps_git_stderr_and_the_location`).
2. Against current code (post-#948 and the end-of-command sweep), whether a
   failed in-session sync can still become a later local commit duplicating
   what reached origin.
3. Whether moving publication out of the sandbox (e.g. the supervisor syncing
   after session exit) is needed. If so, record it as a follow-up ticket —
   a pending-publication / deferred-retry state is out of scope here (it would
   change the `coga/state-publication` contract). Any such follow-up must
   keep a visible pending state, actionable recovery, strict caller
   semantics, and uncertain-push handling; a deferred write is never reported
   as published.

### Code pointers

- `git.sync_task_state`, `git.publish` and its `hash-object` call;
  `git.ObjectWriteError`, raised from `git._hash_blob`.
- `git.py` writes `sync failed: …` under the `git` tag through
  `git.record_sync_failure` and `git.sync_failure_report`. Literal
  `[git] sync failed` sites: `recurring_runner.py`,
  `commands/recurring.py`. `mark.py`, `commands/mark.py` and `authoring.py`
  catch `git.GitError` and report through `git.py`'s helper.

### Cited, not attached

- `coga-dev/internals/git-refresh` (`docs/contexts/coga-dev/internals/git-refresh/SKILL.md`):
  read "The realignment proof", "`fast_forward_control`" and "`refresh`".
  Attach it only if the design changes realignment.
- `coga/checkouts/sandbox-clone` and `coga/checkouts/launch-boundary`
  (`docs/contexts/coga/checkouts/`): the sandbox and checkout boundary, for
  question 1.
- `coga-dev/internals/git-regressions` and `coga-dev/internals/spool-merge`:
  only if the fix touches the provenance check or the `log.md` union merge.

### Related

- Multiline Git stderr breaking log lines was fixed in #985
  (`keep-multiline-audit-messages-on-one-log-line`).
- Unsourced counts relayed on 2026-10-07 (no checkout or query) were dropped;
  the recount above supersedes them.
- Previous ref: `fix-coga-git-sync-failures-that-leave-main-diverge` (renamed
  2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
