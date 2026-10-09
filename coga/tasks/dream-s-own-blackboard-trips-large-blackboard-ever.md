---
title: Dream's own blackboard trips large-blackboard every run
status: in_progress
owner: nicktoper
contexts:
- coga/dream
- coga/period-task
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
launch_generation: e02cd156-1267-4230-84be-37d4aa5efe13
---

## Description

Found by validate-drift-blackboard-hygiene-two-oversized-bl on 2026-10-06. `coga validate --json` reports `large-blackboard` (warn, 51.5 KiB vs 32.0 KiB) for `recurring/dream`. In 2026-W41 the `## Findings` section alone was about 30 KiB, plus about 12.5 KiB of `## Dream Skill: validate-drift` and about 8 KiB of `## Dream Run Summary`.

The flagged file is `coga/tasks/recurring/dream/ticket.md`. That is the *period task* generated for one firing (`status: done`, `contexts: coga/period-task`, `period_generation:`), not the recurring template at `coga/recurring/dream/ticket.md`. Every firing writes a new, similarly sized report onto a fresh period blackboard, so the warning keeps returning. Dream's own Phase 1 then reports it about itself. Hand-trimming one period does nothing for the next.

Options, decided by the owner at the `review-design` gate:
1. **Attachment.** The template body tells Dream to write bulky per-run sections (Findings, validate-drift detail) to a sibling attachment in the period task directory, and only the summary stays on the blackboard.
2. **Skip done period tasks.** Don't run `large-blackboard` on a `done` period task that the next firing will delete.
3. **Exempt.** Exempt recurring period tasks (or their report sections) from `large-blackboard` in some other way.
4. **Accept.** Accept the warning and record the rationale in `docs/contexts/coga/dream/SKILL.md`.

Done when one of the following is merged:
- Option 1, 2 or 3 is implemented with a test covering the new behavior. A `coga validate --json` run after a Dream-sized period blackboard no longer reports `large-blackboard` for `recurring/dream`. The owning contexts are updated in the same PR.
- Or the acceptance (option 4) is recorded in `docs/contexts/coga/dream/SKILL.md`.

## Context

The design step lays out the options with their tradeoffs and recommends one. If the owner picks option 4, `implement` is a docs-only change.

**Period task vs template (the key fact).** `coga/recurring/dream/ticket.md` is the template. It is byte-identical to its packaged twin `src/coga/resources/templates/coga/recurring/dream/ticket.md` (`coga/packaging`), and that twin is where any change to how Dream writes its report must land. `coga/tasks/recurring/dream/` is the per-firing period task. Its blackboard is per-run scratch that the next period deletes (`coga/period-task`, attached). Phase 6 of the template already describes these sections as an index for a task that "is retired and its blackboard with it". A period task has no packaged twin.

**Who writes the oversized sections.**
- The Dream agent writes `## Findings` and `## Dream Run Summary` itself, following the template body: the Phase 2/3 step "Merge into the blackboard" merges the scan's `findings.md`, and Phase 6 appends `## Dream Run Summary`. The scan skills under `bootstrap/dream/scan/` (`scan-protocol`, `knowledge-scan`, `contract-audit`) only write `findings.md` in their scan directory.
- The `## Dream Skill: validate-drift` and `## Dream Skill: cleanup-orphan-markers` sections are rendered by `dream_validate_drift` and `dream_cleanup_orphan_markers`.
- Each writer owns only its own keys (`coga/period-task`).

**The check.**
- `validate._check_one_task` calls `blackboard.blackboard_size_warning` and emits `large-blackboard` (warn). The threshold is `blackboard.BLACKBOARD_WARN_BYTES` (32 KiB), which `launch` also uses for its own warning.
- Dream's validate-drift scan, `dream_validate_drift.classify_issue`, turns `large-blackboard` into a PR proposal for the `coga/blackboard` bloated-blackboard remedy. That is why Dream proposes fixing itself.
- Options 2 and 3 change core validation. Justify them against `coga/extension-model` and `coga/principles`: a lifecycle-based rule (a `done` scratch task) generalizes better than a special case for one recurring job.

**Owner topics to update in the same PR:** `coga/dream` (attached; `## Results and safety` owns the run report). Depending on the option, also `coga/blackboard` (cited: read its bloated-blackboard section), `coga/recurring` (cited: read its period-task/template section) and `coga/period-task`.

**Out of scope:** changing `BLACKBOARD_WARN_BYTES` for all tasks, and trimming other tasks' blackboards.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
