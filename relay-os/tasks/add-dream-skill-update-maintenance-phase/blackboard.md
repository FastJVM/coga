The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: skill-update-phase
worktree: /home/n/Code/codex/relay-skill-update-phase
pr: (not opened yet — opens in code/open-pr step)

## Implemented (step: implement) — committed 24ee488

What landed on `skill-update-phase`:

1. **New bundled worker** `bootstrap/dream/tasks/skill-update/{SKILL.md,run.py}`
   in the SOURCE template tree, **git add -f'd** (bootstrap/ is gitignored).
   - `run.py` shells `relay skill update --all --pr --json`, parses the JSON,
     and buckets results by **raw status** under three headings
     (Updated / Needs follow-up / Skipped). Unknown statuses → follow-up
     (loud, never swallowed). Pure functions (`classify_status`,
     `parse_results`, `render_blackboard_report`, `build_update_command`) are
     unit-tested.
   - SKILL.md has a `## Known Skill Contract` (Action: `pr-required`), mirroring
     the other two workers.
2. **Dream contract** (`dream/ticket.md`, both live + packaged, kept
   byte-identical): inserted **Phase 4 — skill-update** before retro; renumbered
   retro→5, cleanup→6, disposition→7; updated all framing (seven phases, 4–7
   execute, three script workers at Phases 1/4/6, console-progress list, and
   every internal "Phase N" cross-reference).
3. **Engine made in-scope** (`skill_manager.py`): `run_skill_update_pr_flow`
   now commits updates onto a dedicated `relay/skill-update` branch (never the
   caller's branch / `main`), restores the original checkout in a `finally`,
   and opens **no PR** when nothing changed — including the empty-commit case
   where an opaque `gh skill update` reports `changed=True` but leaves no diff
   (`git diff --cached --quiet` guard). `open_or_update_pr` gained an explicit
   `branch` param.

### Tests (all green: full suite 622 passed)
- `test_dream_skill_update.py` (new): classify/parse/render, incl. conflict vs
  skipped-local-adaptation staying distinct, and no-PR rendering.
- `test_dream_skill_scripts.py`: launch test — installs worker into **bootstrap**
  root so `skills/` stays empty (else `relay skill update --all` would invoke
  `gh skill`); asserts the section + "PR: none opened".
- `test_dream_worker_templates.py`: seven-phase renumber + skill-update contract.
- `test_skill_manager.py`: rewrote the #143 PR-flow test for branch/commit/
  restore; added empty-results skip + empty-commit skip tests.
- `test_packaging.py`: passes (wheel ships the new pure-data skill dir).

### Notes for review / open-pr step
- Engine scope was expanded on nick's explicit call ("make the engine in
  scope") — beyond the ticket's original "engine out of scope" note. The PR
  body should call this out.
- Re-run idempotency of the `--pr` branch (force-push / existing-PR body edit
  on a second run) is **not** hardened here — first-run clean-PR is the target;
  the existing `open_or_update_pr` early-returns on an existing PR before
  pushing, so a second run updates the body but not the commit. Left as-is
  (pre-existing #143 behavior); flag if review wants more.

## Origin

Split from `close-imported-skill-provenance-conflict-and-dream` on nick's
decision — this is gap 4 of the `add-imported-skill-update-check` audit (the
Dream skill-update maintenance phase), separated because it is template +
bundled-worker-skill authoring rather than CLI code+tests. The underlying
`relay skill update --all --pr` flow already exists (shipped in #143); this
ticket only adds the Dream worker + phase that calls it. Independent of the
sibling at the code level — can land in any order.

## Investigation (step: implement)

Read the existing two workers + the dream contract + the update engine. Key facts:

- **Files to create** (source template tree, force-add): `src/relay/resources/
  templates/relay-os/bootstrap/skills/bootstrap/dream/tasks/skill-update/{SKILL.md,run.py}`.
- **Contract to edit in BOTH copies** (currently byte-identical): live
  `relay-os/recurring/dream/ticket.md` + packaged
  `src/relay/resources/templates/relay-os/recurring/dream/ticket.md`.
- **Statuses the updater currently emits** (`skill_manager.py`): `updated`,
  `unchanged`, `skipped-bundled`, `skipped-local-adaptation`, `failed`,
  `delegated`, `local-override`, `package-backed`. No `conflict` yet (that's the
  sibling's gap 3). Decision: worker buckets by **raw status string** (one
  group per status), so `conflict` and `skipped-local-adaptation` are inherently
  separate the moment the sibling lands — no special-casing, satisfies the
  "bucket conflict separately" note for free.
- **`--json` shape**: `{counts, results:[{name,source_type,status,message,
  changed,details}], verification, pr_url}`.
- **`--pr` flow gap (the fork below)**: `run_skill_update_pr_flow` →
  `open_or_update_pr` pushes the *current* branch + `gh pr create`, but **never
  commits** the updated skill files, and runs git from `cfg.repo_root.parent`.
  So a bare `relay skill update --all --pr` from the control-plane checkout on
  `main` would (a) try to push `main` and (b) open an effectively empty PR. The
  commit/branch step is not in the shipped engine, and the engine is out of
  scope for this ticket.

### Decisions (from nick, interactive)

1. **Engine is IN SCOPE** (overrides the ticket's "engine out of scope" note).
   Fix the `--pr` flow so `relay skill update --all --pr` produces a clean,
   real PR: (a) never commit/push `main` — use a dedicated branch; (b) commit
   the changed skill files; (c) when nothing changed, open no PR at all
   (no empty-PR failure). Keep the change focused; update the one affected
   #143 test and add new coverage.
2. **Phase slot: BEFORE retro.** New order:
   1 validate-drift, 2 knowledge scan, 3 contract audit,
   **4 skill-update (NEW)**, 5 retro/done-ticket, 6 cleanup-orphan-markers,
   7 disposition+summary. Execute half = 4–7. Three script workers now at
   Phases 1, 4, 6. Update the "six phases"→"seven", "1–3 decide / 4–6 execute"
   →"4–7 execute", and "two script workers (Phases 1 and 5)"→"three (Phases 1,
   4, 6)" framing.

### Test shape to mirror
`tests/test_dream_skill_scripts.py` (CliRunner `launch` of a `mode: script`
task, assert the `## Dream Skill: <name>` section lands) and
`tests/test_dream_worker_templates.py` (static contract assertions on SKILL.md
+ ticket.md). Will add a `skill-update` case to each.
