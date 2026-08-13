---
slug: decide-the-fate-of-two-premise-dead-v2-drafts-whos
title: Decide the fate of two premise-dead v2 drafts whose subject no longer exists
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
    skills: []
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

Filed by the Dream run of 2026-W31 (Phase 2 knowledge scan, finding F12, class
`stale`).

Dream does not change ticket lifecycle state on its own — cancelling a draft is a
human decision — so this finding is parked here rather than actioned.

## The problem

Two parked drafts are **premise-dead**: the thing they ask someone to document no
longer exists. Anyone who picks either one up would write prose describing a
removed design.

### 1. `coga/tasks/v2/document-parent-orchestrates-child-script-tasks-pa.md`

Asks to document "deterministic phases run as child `mode: script` tasks, each
with a one-step workflow referencing a worker skill" as the canonical
housekeeping pattern. That is the exact shape **PR #650 deleted**. Dream's
deterministic phases now invoke registered recipes directly from the parent task,
and the recipes inherit the parent's `COGA_TASK_*`.

### 2. `coga/tasks/v2/document-interactive-recurring-sweep-hazard-in-rel.md`

Is entirely about the `mode:` frontmatter field (`script` / `auto` /
`interactive`) and the two open tickets that were meant to settle it. **The field
is gone.** `coga/contexts/coga/recurring/SKILL.md` now documents the surviving
true constraint: "Agent work needs a TTY; recipes and complete scripts can be
headless."

Both were themselves prior Dream `gap` findings, which is worth noting: a gap
ticket that sits long enough can outlive its own subject.

## The decision needed

For each ticket, one of:

- **Cancel** with a reason (`coga mark canceled`), or
- **Rewrite** against the current shape. For #1 that would mean documenting the
  phase-list-plus-subagent-scan pattern in `coga/patterns` — but only if that
  pattern is actually wanted as a reusable convention. For #2 there is likely
  nothing left to salvage.

## Incidental

Both tickets, like most of `coga/tasks/v2/`, still say "relay" / `relay-os`
throughout — they predate the rename, and the paths they cite do not resolve.
That is a broader cleanup question for the whole `v2/` parking area, not just
these two.

## Context

### Scope note from Dream 2026-W33

Dream's knowledge scan confirmed the broader half this draft already names: the `coga/tasks/v2/` parking area systematically references pre-rename `relay`/`relay-os` surfaces that no longer resolve (`src/relay/`, `relay-os/contexts/...`, `relay launch`, `mode: script`, `relay panic`, `[secrets]` bulk-inject — e.g. in `document-recurring-template-live-vs-packaged-sync`, `measure-relay-prompt-scope-and-agent-precision`, `wire-recurring-sweep-into-system-cron`, `pass-secrets-to-skills-with-per-skill-scope`). Anyone pulling a v2 draft forward inherits instructions against a repo that no longer exists. Fold the v2-wide relay-reference sweep into this draft's decision rather than opening a separate artifact.

<!-- coga:blackboard -->

## Premise verification (2026-08-13)

Both premise-dead claims confirmed against current `main` before deciding:

- **`mode:` ticket field is gone.** `coga/contexts/coga/recurring/SKILL.md:118`
  states "there is no `mode` field. A known `recipe:` selects deterministic
  recipe…". The only `mode` left in `src/coga/` is `Config.mode`
  (`config.py:38`, `"local" | "remote" | "cloud"`) and megalaunch's selection
  mode — neither is ticket frontmatter. Grep for `mode: script` outside
  `tasks/v2/` returns only this ticket and Dream's own routing note.
- **Child-script-task orchestration is gone.** `coga/tasks/recurring/dream/ticket.md:71-74`
  — "The two deterministic phases (1 and 5) run registered recipes directly
  from … then invoke the exact `coga run` command below. The recipe inherits
  this [task's env]." No child tasks, no worker skills, no one-step workflows.

## Decision

Cancel both. Reasons recorded per ticket:

- **`v2/document-interactive-recurring-sweep-hazard-in-rel` → cancel.** The
  entire ticket is about the `mode:` field and the two open tickets meant to
  settle it. The field was removed, which is the strongest possible form of
  `enforce-mode-auto-for-recurring-templates` landing; the ticket's own text
  says to "close as a duplicate" in that case. The surviving true constraint
  (agent work needs a TTY; recipes and complete scripts can be headless) is
  already documented in `coga/recurring`. Nothing left to salvage.
- **`v2/document-parent-orchestrates-child-script-tasks-pa` → cancel, not
  rewrite.** The shape it asks to canonize was deleted. The rewrite option was
  conditional — "only if that pattern is actually wanted as a reusable
  convention" — and it is not: the phase-list-plus-subagent-scan shape has
  exactly one consumer (Dream), which documents its own convention in place
  (`recurring/dream/ticket.md:65-69`, "Adding or removing a Dream phase is a
  normal change to this template… If you want a different maintenance loop,
  make another task with its own body and ordered phase list"). Promoting a
  one-consumer shape into `coga/patterns` would contradict the same
  ≥2-consumers bar CLAUDE.md applies to core code. If a second maintenance
  loop ever appears, that is the moment to name the pattern.

**Correction — where the cancellations actually landed.** I ran both
`coga mark canceled` calls from the feature checkout intending the disposition
to travel through the PR and the owner's `review` step. It does not:
`coga mark canceled` syncs ticket state to `origin/main` immediately, the same
way `bump` does. Both cancel commits are on `origin/main` now (`d8f1c776`,
`2935dc04`) and the Slack broadcasts have already fired; the later rebase
skipped them as already-applied. So the PR carries **only** the README and the
roadmap edit.

That is coga's designed behavior for state transitions, not something the
branch can hold back — a ticket's `status` is live repo state, not PR content.
The consequence for the owner: the two cancellations are already in effect and
reviewing this PR does not gate them. Reversing either one means
`coga mark active v2/<slug>` (allowed from `draft`/`paused`, so a canceled
ticket needs a hand-edit or a revert of its commit), not a PR rejection.
Flagging it rather than reverting, because reverting would leave the audit log
and the Slack record describing a cancellation that did not stick.

## v2-wide relay sweep (folded in per Dream 2026-W33)

46 of 83 recognized drafts under `coga/tasks/v2/` mention `Relay` or `relay`.
**Decision: warn, do not
rename.** A mechanical `relay`→`coga` rewrite would convert dead surfaces into
live-looking ones (`relay panic` → `coga panic`, which does not exist;
`relay draft … --mode script`, `[secrets]` bulk-inject, `relay-os/contexts/…`),
hiding staleness instead of flagging it. That is the opposite of legibility.

Landing instead: `coga/tasks/v2/README.md` — already a supported non-task file
(`src/coga/tasks.py:125`, `_NON_TASK_FILES`), so it does not become a phantom
task — carrying the parking-area contract and the concrete dead-surface
checklist, plus a pointer from `coga/contexts/coga/roadmap` "Deferred work",
which already owns the pull-forward rule.

No packaged copy to sync: `src/coga/resources/templates/coga/contexts/` ships
only `_template` and `browser`, and the packaged `tasks/` tree has no `v2/`.

## Dev

pr: https://github.com/FastJVM/coga/pull/686
branch: v2-premise-dead-drafts
worktree: /home/n/Code/claude/coga-v2-premise-dead-drafts

Branch contents (rebased onto `origin/main`, 0 commits behind):
`coga/tasks/v2/README.md` (new, 68 lines) + a 9-line addition to
`coga/contexts/coga/roadmap/SKILL.md`. The two cancel commits are already
upstream — see the correction above.

Verification run in the feature checkout:
- `python3.12 -m pytest` → 1578 passed, 1 skipped. (Note for later steps: the
  default `python` on this box is 3.9 and `src/coga/__init__.py` hard-refuses
  it, so `python -m pytest` fails at conftest import. Use `python3.12`.)
- `coga validate --json` → 0 errors, 0 warnings.
- `coga status v2` → no `README` row, confirming the new file is treated as
  directory documentation and not a phantom task.

No example-fixture update needed: this change is documentation only — no task
layout, prompt composition, or workflow semantics changed.

## Peer review (2026-08-13)

Required `codex review --base main` completed with two P2 findings, both fixed
in `coga/tasks/v2/README.md`:

- `relay panic` was incorrectly described as having no replacement. The table
  now routes blocker-oriented uses to `coga block --task <slug> --reason "…"`
  and names its state/notification/session effects.
- The `mode:` row carried forward the already-deleted generic script-launch
  seam. It now states the current contract: agent work needs a TTY and only a
  registered recipe can run headlessly.

The review's inventory also clarified the relay count above: 46 is the
case-insensitive `Relay`/`relay` count across 83 recognized v2 drafts; a
lowercase-only grep finds 45 and misses `clean-uncommitted-work.md`.

## Final peer-review verification (2026-08-13)

- Committed the review fixes, fetched `origin main`, and rebased onto the
  fetched head unconditionally. The replay was clean.
- Final branch commits: `d601b02c` (implementation) and `3181dbde`
  (peer-review fixes); branch is clean, 0 behind and 2 ahead of `origin/main`.
- Post-rebase `python3.12 -m pytest` → 1716 passed, 1 skipped. Pytest emitted
  only its sandbox cache-write warning; the suite exited 0.
- `PYTHONPATH=$PWD/src python3.12 -m coga validate --json --task
  decide-the-fate-of-two-premise-dead-v2-drafts-whos` → 1 task OK, no issues.
- `git diff --check origin/main...HEAD` → clean.

## PR

### Summary

- Document `coga/tasks/v2/` as a parking area of dated artifacts whose premises
  and named surfaces must be checked against current `main` before pull-forward.
- Catalog the known pre-rename `Relay` surfaces and their current disposition,
  warning against a mechanical rename that would turn dead interfaces into
  plausible-looking instructions.
- Link the roadmap's deferred-work rule to the new parking-area contract and
  record premise-dead cancellation as a normal outcome.

The two lifecycle cancellations themselves already synced directly to
`origin/main` through Coga state transitions; this PR intentionally contains
only the durable README and roadmap guidance.

### Test plan

`python3.12 -m pytest` (1716 passed, 1 skipped); `PYTHONPATH=$PWD/src python3.12 -m coga validate --json --task decide-the-fate-of-two-premise-dead-v2-drafts-whos` (1 task OK, no issues).
