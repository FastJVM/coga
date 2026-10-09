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
step: 2 (evaluate-design)
agent: claude
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

### Options weighed (design step)

The warning exists because a blackboard composes into launch prompts
(`blackboard_size_warning`'s own message says so). A `done` period task is not
launched by a normal sweep. The scanner deletes it before creating the next
period (`recurring.py`, the `replace_done` branch logs "deleted completed
prior-period task before <period>"). Only `coga recurring --force` reactivates
it. `commands/launch.py` calls `blackboard_size_warning` itself on that path, so
a forced relaunch keeps its prompt-size warning no matter what validate does.

1. **Attachment.** This touches many surfaces: the template body and its twin
   (the Phase 2/3 "Merge into the blackboard" steps, Phase 4's snapshot of
   `## Findings` and Phase 6), the `scan-protocol`, `knowledge-scan` and
   `contract-audit` skills, `retro/done-ticket` (which consumes "the caller's
   live `## Findings`"), and `tests/test_dream_worker_templates.py`
   assertions. It does not move the recipe-written
   `## Dream Skill: validate-drift` (≈12.5 KiB). Unless that recipe also
   changes, a run with many validate-drift issues can still cross 32 KiB. The
   gain is cosmetic: the bytes move, but nothing composes them into a future
   prompt, because no future prompt reads them.
2. **Skip done period tasks (recommended).** The rule is one lifecycle
   condition in core validation. It covers every recurring job, not only
   Dream, and it suppresses the warning only in the window where it cannot
   matter, after the run and before the scanner deletes the task. The `launch`
   warning stays intact for the one path that relaunches the task. This is a
   rule about a lifecycle state (terminal scratch the runner deletes), not a
   special case for Dream, so it does not conflict with `coga/extension-model`.
   No new module and no new consumer. It also keeps the blackboard as the
   legible index that Phase 6 already describes, which fits
   `coga/principles`.
3. **Exempt by section or by every period task.** Exempting sections means
   validation has to understand Dream's report headings, a Dream-specific
   rule in core. Exempting in-progress period tasks would also hide real
   prompt bloat on a live or forced run. Rejected.
4. **Accept.** The warning keeps returning every week, and Dream's
   validate-drift turns it into a `pr-proposal` against itself each time
   (`dream_validate_drift.classify_issue`, the `large-blackboard` branch).
   Each run then needs a recorded `validate-drift: large-blackboard` decision
   to suppress the refiling. That costs ongoing noise and buys nothing.

The rest of this spec assumes option 2. If the owner picks another option at
`review-design`, the implement step follows that option and this section is
superseded.

### Acceptance criteria

- [ ] `coga validate` does not emit `large-blackboard` for a task that is a
      materialized period task (frontmatter carries a non-empty string
      `period_generation`) **and** has `status: done`.
- [ ] The following still get `large-blackboard`, each covered by a test:
      the same oversized period task while `in_progress`, an oversized
      ordinary `done` task with no `period_generation`, and an oversized task
      whose frontmatter fails to parse (the warning is still emitted next to
      `bad-frontmatter`, as it is today).
- [ ] `coga launch`'s own `blackboard_size_warning` call sites are
      unchanged. `blackboard_size_warning` itself keeps its signature and
      behavior. The rule belongs to validation, not to the size helper.
- [ ] A test builds a Dream-sized (> 32 KiB, default threshold) blackboard on
      a `done` `recurring/<name>` period task and asserts that
      `run(cfg)` / `coga validate --json` reports no `large-blackboard` for it.
- [ ] `docs/contexts/coga/blackboard/SKILL.md` `## Size and its remedy`
      states the exemption and its reason in one or two sentences: a done
      period task is deleted by the next firing and composes into no prompt
      unless forced, and `launch` still warns then. The packaged twin
      `src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md`
      matches byte for byte.
- [ ] `docs/contexts/coga/period-task/SKILL.md` `## Your own blackboard is
      per-run scratch` gets one sentence: a done period's blackboard is not
      size-checked by `coga validate`, so it may hold the full run report.
      Its packaged twin matches.
- [ ] `docs/contexts/coga/dream/SKILL.md` `## Results and safety` notes that
      the run report stays on the period blackboard and that the done period
      is exempt from `large-blackboard`, linking `coga/blackboard`. Its
      packaged twin matches.
- [ ] `python -m pytest` passes, including `tests/test_packaging.py`.
      `coga validate --json` on this repo no longer lists `large-blackboard`
      for `recurring/dream`, while the existing period task is still `done`.

### Proposed shape

1. `src/coga/validate.py`, `_check_one_task()`: keep computing
   `blackboard_size_warning(ref.ticket_path, max_bytes=max_blackboard_bytes)`
   where it is now, but hold the resulting `Issue` instead of appending it
   immediately.
   - On the `bad-frontmatter` early return, append it before returning, so
     the current behavior is preserved.
   - After `ticket` is resolved (from `Ticket.read` or `ticket_override`),
     append it unless `_is_done_period_task(ticket)`.
2. Add a small private predicate in `validate.py`, for example
   `_is_done_period_task(ticket: Ticket) -> bool`. It returns true when
   `ticket.status == "done"` and `ticket.frontmatter.get("period_generation")`
   is a non-empty string. Do not check placement here:
   `_check_period_generation_owner()` already errors when
   `period_generation` sits on a ticket outside `tasks/recurring/`, so a
   misplaced generation still surfaces. Use whatever status accessor
   `Ticket` already exposes. Keep the predicate private to validation, since
   it has one consumer.
3. Tests in `tests/test_validate.py`, next to `test_large_blackboard_warns`.
   Materialize a period task the way the existing `period_generation` tests
   do (`create_task(..., period_generation=...)` under the `recurring`
   directory, as in `test_validate_rejects_an_empty_period_generation`), set
   its status, `replace_blackboard` an oversized region, and assert both the
   exempt case and the warn cases listed in the acceptance criteria. Use
   `max_blackboard_bytes` for the small cases and one default-threshold case
   for the Dream-sized criterion.
4. Docs: make the three topic edits above, each in the live and packaged
   copy. No change to the Dream template, the scan skills, or
   `dream_validate_drift`. With nothing emitted, the classifier has nothing
   to classify.

### Out of scope

- Changing `BLACKBOARD_WARN_BYTES` or the `launch` warning.
- Moving Dream's report into attachments (option 1). If a forced Dream rerun
  ever needs a smaller prompt, that is a separate ticket.
- Exempting `canceled` or `paused` period tasks. The scanner does not
  auto-replace them, and `--force` relaunches a paused one. See the open
  question on the blackboard.
- Trimming the current `coga/tasks/recurring/dream/` blackboard by hand, or
  any other task's blackboard.
- Changing `dream_validate_drift.classify_issue`.

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

## Design notes (design step, 2026-10-08)

- Recommended **option 2**. The rule is `done` + non-empty `period_generation`,
  and it applies in `validate._check_one_task` only. The spec and the full
  options comparison are under `## Description`.
- Key facts verified:
  - The scanner deletes a `done` prior period before it creates the next
    one (`recurring.py`, the `replace_done` path).
  - `--force` reactivates done/paused periods, and `commands/launch.py`
    calls `blackboard_size_warning` itself, so it still warns then.
  - `blackboard_size_warning` measures only the composed blackboard region.
    The current period ticket is 91 KiB in total; most of that is the copied
    template body, which is not measured.
- Option 1 would not move the ≈12.5 KiB `## Dream Skill: validate-drift`
  section, because the core recipe writes it. That section plus the summary
  plus a large Findings attachment index could still approach the threshold.

## Open Questions

- Pick the option at `review-design`. The recommendation is option 2.
- Should `canceled` period tasks also be exempt? The spec says no. The
  scanner keeps them, `--force` refuses them until a human deletes them, and
  they may deserve attention anyway. They are still never launched, though,
  so exempting them would also be defensible.
