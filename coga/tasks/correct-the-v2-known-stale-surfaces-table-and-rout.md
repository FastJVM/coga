---
slug: correct-the-v2-known-stale-surfaces-table-and-rout
title: Correct the v2 known-stale-surfaces table and route future Dream gap findings
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

The `coga/tasks/v2/README.md` known-stale-surfaces table has a defect that misroutes readers, and
the parking area has no recorded answer for where future Dream `gap` findings should go. This is the
PR-shaped half of the v2 triage: file edits only, no lifecycle writes, no cancels.

Three deliverables:

- **Fix the `relay-os/… -> coga/…` rename row.** As written it sends readers to `workflows/code/*`
  paths that do not exist in the repo.
- **Decide whether `script:` warrants a row at all**, and if so write it accurately (see Context —
  the obvious version of this row would be false).
- **Record where future Dream `gap` findings go** instead of decaying in this directory.

Also clears 2 of the 4 `coga validate` errors via the two blackboard syntheses named in Context.

## Context

### Shared background (all three v2 triage tickets)

This ticket is one of three split out of `triage-the-v2-parking-area-empty-descriptions-prem`
(canceled 2026-09-02). Siblings: `correct-the-v2-known-stale-surfaces-table-and-rout`,
`adjudicate-the-eight-premise-dead-v2-drafts`, `interview-the-owner-on-the-17-title-only-v2-stubs`.

Origin: Dream 2026-08-24, Phase 2 knowledge scan (shards 06, 09, 11, 12), classified `gap`.
Re-verified against `main` 2026-09-02 plus an independent cold review. **Where these notes and the
original Dream findings disagree, these notes win.**

**The contract for this directory is `coga/tasks/v2/README.md`.** Read it first — it defines the
two-question premise check (does the subject still exist? do the surfaces it names still resolve?)
and records the `decide-the-fate-of-two-premise-dead-v2-drafts-whos` cancellation precedent.

**Counting `v2/` correctly.** `coga status v2 --all` reports **81 tasks**. Do not count with
`ls coga/tasks/v2/*.md` — that returns 76, counting the `cleanup-core-commands/` directory as one
entry and missing its six children. The Dream scan's "~75" and "18" are both this artifact.

**`coga validate` state.** 4 ERRORs repo-wide, all `unsynthesized-draft-blackboard`, all under
`v2/`. The rule fires only on `status == "draft"` (`src/coga/validate.py:447`), so each clears by
cancelling or synthesizing. Everything else `coga validate` prints is a WARN. Two errors clear in
`correct-the-v2-known-stale-surfaces-table-and-rout`, two in
`adjudicate-the-eight-premise-dead-v2-drafts`. **A green validate is never a reason to cancel a
draft** — it is a consequence of correct verdicts, never an input to them.

### The table defect that is real and unqualified

The `relay-os/…`, `relay-os/contexts/…` row maps to `coga/`, `coga/contexts/…`. That is correct for
contexts but misleading for workflow refs: **`coga/workflows/code/` does not exist.** The `code/*`
workflows resolve only from `src/coga/resources/templates/coga/bootstrap/workflows/code/`.
`coga/workflows/` itself does exist and holds repo-local workflows (autoclose-merged, branch-sweep,
digest, skill-update, build, direct), so the row cannot simply be deleted — it needs to distinguish
repo-local from packaged.

### The `script:` field — do not write the obvious row

15 drafts in `v2/` carry `script:`, all of them `script: null`. An earlier version of this work
claimed core "has no reader" for the field. **That is wrong and would have put false prose into the
contract file.** `src/coga/ticket.py:74-80` is a bounded migration that pops `script` when its value
is `None`, so all 15 are already handled and self-heal on the next write through core.

If a row is added at all, the accurate text is: "`script:` — Gone; a bounded migration in
`src/coga/ticket.py:74` strips `script: null` on next write." Confirm with the owner whether that
earns a row — the honest answer may be no, since the field is inert and self-clearing. Note this is
a *different* surface from the `mode: script` row the table already carries.

### The two blackboard syntheses

`measure-relay-prompt-scope-and-agent-precision` (4,215-char blackboard) and
`use-worktree-when-starting-a-dev-task` both fail `coga validate` with
`unsynthesized-draft-blackboard`. Synthesize both. "Synthesize" is defined in
`coga/contexts/coga/architecture/SKILL.md` (~lines 720-730): fold durable content from the
blackboard up into the ticket body, or move deliberate launch notes under a `## Production notes`
heading, which the validator accepts as the alternative. Read that passage before starting — it is
not attached as a context because the file is 59 KB.

Phase 1 `validate-drift` originally proposed synthesis for four drafts. Only these two keep that
route; the other two (`autotrigger-ticket-type`, `split-context-to-doc-user-accessible-and-editable`)
are adjudicated in `adjudicate-the-eight-premise-dead-v2-drafts` and must not be synthesized here.

### Where future `gap` findings go

The v2 README records that two drafts it cancelled as premise-dead "were themselves Dream `gap`
findings originally." Findings parked here decay — that is the standing pattern this ticket names.
The decision is durable routing policy, so it lands in a file, not in a ticket: write it into
`coga/tasks/v2/README.md`, and if it changes Dream's own behavior, also the roadmap's "Deferred
work" section. **Confirm the target and the policy with the owner before writing** — this is the one
judgment call in an otherwise mechanical ticket.

### Out of scope

Any `coga mark canceled` call, and any verdict on the 8-draft premise cohort or the 17 stubs. Those
are the two sibling tickets. If triaging the table surfaces a draft you believe is premise-dead,
note it for the sibling ticket rather than acting on it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
