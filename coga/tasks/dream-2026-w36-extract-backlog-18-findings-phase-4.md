---
slug: dream-2026-w36-extract-backlog-18-findings-phase-4
title: 'Dream 2026-W36 extract backlog: 18 findings Phase 4 could not consume'
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

Carrier ticket. Dream 2026-W36's Phase 2 knowledge scan classified 18 findings as
`extract` — durable knowledge sitting in a done ticket that belongs in a context or skill.
Phase 6 routes `extract` findings to Phase 4, which opens the knowledge PRs.

**Phase 4 could not consume any of them.** Every one names a source ticket that either
carries a real `## Dev` branch and worktree (retirement debt, deliberately left on disk so
the human-typed `coga retire <slug>` stays valid) or is `status: canceled` (which
`retro/done-ticket` refuses). Phase 4's seven eligible tickets were all period tickets
carrying nothing durable, and were direct-deleted.

The source tickets are all still on disk, so the *knowledge* is safe. This ticket exists
because the *findings* were not — Dream's blackboard is deleted at the next firing.

**This is a backlog, not a single change.** The right first move is triage: decide which of
the 18 are worth landing, group them into coherent knowledge PRs by target context, and
split into sibling tickets if that is cleaner than one pass. Several may be better handled
by the `coga retire` flow for their source ticket, which would consume the evidence
naturally.

The routing hole that produced this is ticketed separately as
`dream-findings-have-three-routing-holes-that-lose`.

## Context

Citations name symbols and files, not line numbers. Each item gives the source ticket and
the target area; the full finding paragraphs are in the Dream 2026-W36 blackboard
(`coga/tasks/recurring/dream/ticket.md`, `## Findings`) **until that task is retired at the
next firing** — copy anything you need from it before then, or recover it from git history.

**Target `coga/codebase` (5)**

1. `autoclose-should-name-the-retire-follow-up` — peer review's microkernel refinement: do
   not promote a helper to core while its duplicate consumers stay unmigrated.
   `append_report` exists as three byte-identical private copies in `skill_update.py`,
   `dream_validate_drift.py`, and `dream_cleanup_orphan_markers.py`; the rule is
   "consolidate the real consumers, don't add a fifth". The naive reading of the current
   context ("three consumers, therefore promote") gives the opposite answer.
2. `bumppy-requires-exactly-two-agents` — validate-before-write for lifecycle mutations:
   build a prospective `Ticket`, validate via `assert_task_valid(..., ticket_override=...)`,
   then commit. Three writers converted (in `mark.py` and `bump.py`); `mark_active`,
   `mark_in_progress`, `mark_blocked` and `mark_paused` still write-then-validate.
3. `select-session-conduct-instead-of-appending-a-cont` — `coga launch --prompt-report`
   reads as a report but runs under the mutating `launch` command and is swept, so it
   published three working-tree doc edits to `origin/main`. The codebase context's
   "read-only commands are safe" list invites exactly the wrong inference.
4. `megalaunch-only-shows-one-page` — inside a feature worktree a bare `python -m pytest`
   imports the *primary* checkout's source via the editable-install `.pth`.
   `PYTHONPATH=$PWD/src` is the default invocation, not a repair for a broken install.
5. `rewrite-coga-base-prompt-and-agent-mode-block` — authoring rules for
   `src/coga/resources/prompt*.md`: an abridged restatement inside a prompt resource is
   often the only version an agent sees, and a guard split across two resources can be
   deleted wholesale in one commit with tests still green.

**Target `coga/recurring` (3)**

6. `recurring-last-serviced-period-compares-as-a-strin` — how to suppress a new template's
   first firing.
7. `migrate-recurring-templates-to-ticket-py-shims-and` — why a `ticket.py`-backed step
   keeps `assignee: agent`.
8. `fix-the-autofix-analyst` — **two of that ticket's three specified defects are still
   live** in `src/coga/recurring_autofix.py`: the failure detail is built as
   `(result.stderr or result.stdout or "")`, so a benign stderr warning hides the real
   cause on stdout; and the analyst subprocess passes no `stdin`, so piped bytes are
   grafted onto the analysis prompt. This one is a **bug carrier**, not just knowledge —
   it likely deserves its own ticket.

**Target `dev/code` (2)** — both from `launch-ignores-the-recorded-worktree-stranding-bla`

9. `coga launch` never chooses the agent's working directory: `run_with_done_marker` takes
   no `cwd` and there is no `os.chdir` in `src/coga/`. `worktree:` authorizes the
   single-checkout assist; it does not place anything.
10. The `requires: branch` gate is cheaply satisfiable by hand-copying the lines, and
    `open-pr`'s "commit or stash them" remediation steers an agent into committing the
    stranded duplicate onto the feature branch, manufacturing a `ticket.md` merge conflict.

**One each**

11. `put-build-back` → `coga/architecture`: a `--agent` override propagates across directly
    consecutive frozen agent steps and stops at a role change or human assist.
12. `remove-legacy-config-compatibility-shims` → `coga/extension-model`: alias-validation
    failure modes, including the `coga init` / `coga recurring --all` recovery exemption.
13. `ship-a-shared-recurring-reminder-engine-battery` (canceled) → `coga/period-task` +
    `coga/codebase` gotchas: cross-run state writers must use the fence-aware
    `coga.blackboard` / `coga.taskfile` API; a bare append destroys a fence on a file that
    ends at one, breaking every blackboard reader at once.
14. `move-cogacontext-to-roodoc-so-its-easier-for-human` → `coga/sync`: an experiment that
    mutates tracked repo state and is exercised through Coga commands publishes itself on
    the first command; run it with `[git] enabled = false` or in a throwaway clone.
15. `put-build-back` → `coga/project-stage`: two more delete-then-restore cycles for the
    bias-toward-deletion precedent list, plus the partial-revert procedure both produced.
16. `dream-phases-2-3-cannot-complete-scan-subagents-re` → `retro/done-ticket`: Phase 4 is
    the one Dream phase with no on-disk progress contract, and it is the destructive one.
17. `reconcile-recurring-wrapper-tty-admission-guidance` → `code/with-review`: the workflow
    never says the peer review must have returned and been read before `coga bump`. PR #723
    merged while its review was still running; the review then returned six actionable
    regressions in merged code, two of them P1 lifecycle races.
18. `megalaunch-only-shows-one-page` → `code/self-qa`: no rule covers surfaces automated
    tests structurally cannot reach; a recorded manual sweep should be a gate and an
    undrivable terminal a blocker.

Filed by Dream 2026-W36, Phase 6 disposition.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
