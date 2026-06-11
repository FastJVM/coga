The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: skill-update-recurring
worktree: /home/n/Code/codex/relay-skill-update-recurring
pr: (pending — opens in the code/open-pr step)

## Scope discovery (2026-06-10)

Most of this ticket was already built before this session:

- `relay skill install / install-local / install-url / status / update
  [--all] [--pr] / remove` all exist in `src/relay/skill_manager.py` +
  `src/relay/commands/skill.py` (landed via PRs #327/#329), including
  provenance (`.relay-source.json`), conflict-skipping, and the one-PR flow.
- Dream already has a Phase 4 that launches a `mode: script` child running
  `relay skill update --all --pr` via the package-backed battery skill
  `bootstrap/dream/tasks/skill-update`.

## Decision (human, this session)

Nick wants the skill updater as a **standalone recurring task**, not a Dream
phase — rationale: many small recurring tasks are easier to debug/fix than
one fat Dream pass. Confirmed via interview:

- Remove Phase 4 from Dream entirely (single owner: the new recurring task).
- Weekly cadence (same as Dream ran it).
- `mode: script` like the digest recurring task — immune to the temporary
  mode=auto freeze and trivially debuggable.

## Plan

1. Rename battery skill `bootstrap/dream/tasks/skill-update` →
   `bootstrap/skill-update` (packaged tree under
   `src/relay/resources/templates/relay-os/bootstrap/skills/`). Reword the
   Dream framing in SKILL.md/run.py; blackboard report header
   `## Dream Skill: skill-update` → `## Skill Update`.
   GOTCHA: new files under the packaged `bootstrap/` need `git add -f`
   (template .gitignore ignores bootstrap/).
2. New one-step workflow `skill-update/run` (live
   `relay-os/workflows/skill-update/run.md` + packaged copy) referencing
   `bootstrap/skill-update`, mirroring `digest/post`.
3. New recurring template `relay-os/recurring/skill-update/` (+ packaged
   copy, mirroring dream's packaged-template precedent): weekly Monday 9am,
   `mode: script`, `workflow: skill-update/run`. Packaging the template +
   workflow avoids orphaning the battery skill in fresh-init repos once the
   Dream phase is gone.
4. Dream template (live + packaged): remove Phase 4, renumber phases 5–7 →
   4–6, fix cross-references.
5. Update tests: `test_dream_skill_update.py` (packaged path),
   `test_dream_worker_templates.py` (contract assertions),
   `test_dream_skill_scripts.py` (refs + header assertion). Check for tests
   asserting Dream phase numbering.
6. Update this ticket's Description/Acceptance criteria (Dream wording →
   standalone recurring task) — control-plane edit, separate from code PR.
7. `python -m pytest` + `relay validate --json`.

Out of scope here: any change to `skill_manager.py` behavior — the CLI is
done and tested.

## Implementation result (2026-06-10, implement step)

Committed on `skill-update-recurring` (single commit, `54e1921`):

- `relay-os/recurring/skill-update/` + packaged copy: weekly Monday-9am
  `mode: script` template, `workflow: skill-update/run`. No owner/assignee in
  frontmatter (matches the dream template, which also omits them).
- `relay-os/workflows/skill-update/run.md` + packaged copy: one-step script
  workflow → `bootstrap/skill-update`.
- Battery skill renamed `bootstrap/dream/tasks/skill-update` →
  `bootstrap/skill-update`; Dream framing reworded; blackboard report header
  `## Dream Skill: skill-update` → `## Skill Update`.
- Dream template (live + packaged): Phase 4 removed, now six phases;
  phases 5–7 renumbered to 4–6, all cross-references fixed.
- Tests: `test_dream_skill_update.py` renamed to `test_skill_update.py`,
  absorbing the contract test from `test_dream_worker_templates.py` and the
  script-launch test from `test_dream_skill_scripts.py`; added a
  recurring-template wiring test. Dream tests now assert skill-update is
  ABSENT from the Dream body.
- Ticket body Description/operating model/AC updated from "Dream maintenance
  step" to the standalone recurring task (human-redirected this session).

Verification:

- `python -m pytest` in the worktree: 629 passed.
- `python -m relay.validate --json`: no new issues; the 5 errors present are
  pre-existing (worktree lacks the gitignored materialized `bootstrap/`, plus
  one old missing-step error) and identical without this change.
- example/ fixture: no dream/skill-update references — nothing to update.

Gotcha hit (worth remembering): edits to already-tracked files under the
packaged `bootstrap/` templates still need `git add -f` — `git mv` stages the
rename, but subsequent content edits are ignored by the template .gitignore
and silently drop out of the commit. Caught because the rename showed 100%
similarity; amended with `git add -f`.

For the next steps: CLI behavior (`skill_manager.py`) was deliberately
untouched — it predates this ticket (PRs #327/#329) and is already tested.

## Handoff note (for the next implement-step session)

The implement step's work is COMPLETE — committed and verified (see
"Implementation result" above). This session ran against the ticket while it
was still `draft`, so `relay bump` refused; the ticket was marked `active`
afterward. If you are a fresh agent launched on the `implement` step: do not
redo any work. Verify the commit exists on `skill-update-recurring`
(`git log skill-update-recurring -1`), then run
`relay bump add-imported-skill-update-check` and exit.
