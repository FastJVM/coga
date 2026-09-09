---
slug: adjudicate-parked-and-active-tickets-whose-premise
title: Adjudicate parked and active tickets whose premises have moved
status: draft
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
secrets: null
step: 1 (implement)
---

## Description

Dream's knowledge scan found eleven tickets whose stated premise no longer
matches the repo. Each needs a verdict — rewrite, narrow, cancel with a reason,
or close as done-by-other-means — and none of them is a context edit, which is
why they are collected here rather than in a proposal PR.

**Premise-dead parked drafts** (the subject or surface no longer exists):
- `v2/pass-secrets-to-skills-with-per-skill-scope` — the `[secrets]`
  bulk-inject model it is entirely about now fails loud in `src/coga/config.py`
  ("no longer supported. Secrets are now declared inline on each ticket's
  `secrets:` frontmatter"). The residue worth preserving in a cancellation is
  the finer ask: per-*skill* rather than per-ticket scope, and the
  agent-versus-script-mode asymmetry.
- `v2/audit-rules-md-usage-across-relay-and-decide-wheth` — audits a "Global
  rules" prompt layer, `coga/rules.md`, a `rules_path()` and a `compose.py`
  rules layer, none of which exist anywhere in the repo. Its "Known facts
  (verified — do not re-derive)" block is now confidently wrong.
- `v2/file-locking-for-concurrent-task-mutation` — its central evidence is that
  "no mutual-exclusion primitive exists" and that `fcntl` appears once, for an
  ioctl. `src/coga/git.py` now takes a real `fcntl.flock(LOCK_EX)` / `LOCK_UN`
  pair, and the architecture context describes the worktree branch checkout as
  doubling as the concurrency lock.
- `v2/debug-surface-for-recurring-tasks-streamed-output` — built entirely on the
  template `mode:` field, which appears zero times in the recurring context
  (determinism is now selected by the reserved `ticket.py` sibling), and depends
  on a ticket `enforce-mode-auto-for-recurring-templates` that does not exist.
- `v2/wire-recurring-sweep-into-system-cron` — asserts "the cron entry point
  already ships — `relay-os/scripts/cron.sh`"; no `cron.sh` exists anywhere.

The last two are **not** in the cohort of `adjudicate-the-eight-premise-dead-v2-drafts`,
so nothing currently routes them.

**Parked drafts whose deliverable already shipped:**
- `v2/document-workflow-less-concept-capture-drafts-as-s` — asks for
  architecture prose that `coga/contexts/coga/architecture/SKILL.md` now
  carries; the sibling it names is gone from `coga/tasks/` entirely.
- `v2/overload-ticket-locally-easily` — both halves landed in architecture and
  extension-model. Residue is one sentence: `coga ticket` injects a hardcoded
  `bootstrap/ticket` ref that an alias cannot redirect, so dropping a local
  `coga/skills/bootstrap/ticket/SKILL.md` substitutes your own interview.
- `v2/split-context-to-doc-user-accessible-and-editable` — the larger question
  it fences off as out of scope is live and past its design step in
  `redo-documentation-dir-and-merge-it-with-context-b`. Leaving it armed invites
  a narrow move against a design the owner is about to gate.
- `v2/docs-and-contt-block-should-be-merged` — empty description, empty context,
  no workflow; its title duplicates that same live ticket, which already
  classifies it as such.
- `v2/implement-accepted-ticket-interview-improvements` — routes the implementer
  to the "Ranked changes" section of a blackboard whose ticket no longer exists
  on disk, so the wording it defers to is reachable only through git history.

**An active ticket that is nearly discharged:**
- `vendored-skills-carry-no-coga-source-json-so-coga` (`status: active`, step 1)
  — its premise has moved from three directions. `.coga-source.json` now exists
  (`coga/skills/clarity/`); the skill-update template was rewritten with `gh`
  delegation in PR #743 *after* the ticket's last edit; and its "the twin is not
  in `IDENTICAL_LIVE_PACKAGED_PAIRS`" warning is false since twins are derived.
  Its only outstanding requirement is naming `ATTRIBUTION.md` / `NOTICE.txt` as
  the hand-vendored provenance substitute. Leaving it active advertises merged
  work.

## Context

Per `coga/tasks/v2/README.md`, the outcome for a premise-dead draft is a
cancellation **with a recorded reason** naming what replaced it, not a silent
delete and not a rewrite that preserves a dead frame.

**Guard, and it matters here:** a green `coga validate` is never a reason to
cancel a draft — it is a consequence of correct verdicts, never an input to
them. Two of the four standing `unsynthesized-draft-blackboard` errors sit on
drafts in this list, so ruling them dead is the cheapest route to a green gate.
Do not take it.

Re-verify each premise before ruling on it; these were checked on 2026-09-08 by
a scan shard, not by the person who will act.

Overlaps to reconcile rather than duplicate: `adjudicate-the-eight-premise-dead-v2-drafts`
(existing cohort — add the two strays rather than ruling them here if that
ticket is live), `interview-the-owner-on-the-17-title-only-v2-stubs`,
`correct-the-v2-known-stale-surfaces-table-and-rout`, and the sibling
`the-v2-parking-area-premise-check-has-four-holes`, which fixes the contract
that would have caught most of these earlier.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
