The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run: dream-dbg-20260603T211208 (interactive debug Dream)

### Orientation (pre-run)
- `relay validate --json`: ok_count=79. Issues: 1 **error** `missing-step`
  (`split-context-to-doc-user-accessible-and-editable`: workflow set, step missing),
  35 `missing-workflow` warns (all drafts — expected), 1 `large-blackboard` warn
  (`test-autobump`, 34 KiB), 1 `unknown-assignee` warn (`relay-competition`, assignee 'nick').
- Done tickets (Phase 4 retro candidates): 18 —
  atomic-writes-for-ticket-log-and-done-marker-files, blackboard-for-recurring-task-must-use-the-permant,
  bump-backward-possible, document-bootstrap-ticket-not-in-skills-frontmatte, dream-w22-cleanup-orphan-markers,
  dream-w23-validate-drift, fail-loud-on-missing-context-or-skill-at-launch, git-sync-a-helper-and-same-branch,
  git-sync-b-cross-branch-to-main, git-sync-c-panic-and-ticket-auth, launch-autoquit-when-done-or-relaunch-depending-on,
  provide-a-google-calendar-capability-so-skills-don, relay-dev-update-2026-05-31, relay-dev-update-2026-06-03,
  scratch-verify-autoquit-marker, scratch-verify-autorelaunch-chain, test-autobimp, test-autobump.
- Dream worker skills present under `relay-os/bootstrap/skills/`:
  bootstrap/dream/tasks/validate-drift, bootstrap/dream/tasks/cleanup-orphan-markers,
  retro/done-ticket, bootstrap/delete-task (all four found).
- Infra: gh authed (nicktoper), origin=github.com/FastJVM/relay. PRs feasible.

### Decision (human, 2026-06-03)
**Full real run** — open real PRs, delete 18 done tickets via PRs, create gap drafts.
**Slack allowed** — post normal Dream summary/FYIs.

### Mechanism notes
- Script workers launched as child mode:script tasks via ready-made workflows:
  Phase 1 → workflow `dream/validate-drift`; Phase 5 → workflow `dream/cleanup-orphan-markers`.
  Create: `relay draft "<title>" --mode script --workflow <wf>`; run: `relay launch <child>`.
  Worker writes `## Dream Skill: <name>` to the CHILD blackboard; summarize here.

### Phase log
- Phase 1 validate-drift: **done**. Child `dream-p1-validate-drift-dbg-211208`.
  38 issues: 0 direct-fix, 1 PR-proposal, 37 human-needed. No files auto-repaired.
  - PR-proposal: `test-autobump` large-blackboard (34 KiB) → condensation PR (route Phase 6).
  - human-needed: 35× `missing-workflow` (workflow-less drafts = design state, NOT drift, no action);
    `relay-competition` unknown-assignee 'nick'; `split-context-to-doc-user-accessible-and-editable`
    `missing-step` ERROR (workflow set, step missing — lifecycle, human-only).
  - These are deterministic-hygiene results; Dream routes only the actionable ones. The 35
    workflow-less drafts are explicitly design state per the skill — no Dream action.
- Phase 2 knowledge scan: **done** (subagent a34da0eea2b452b0e).
- Phase 3 contract audit: **done** (subagent ad77c18785199c93c).

## Findings

### Phase 2 — knowledge scan (extract / stale / gap)

**extract** (grouped by target area — Phase 4 batches these)

- **DONE_MARKER defuse in composed prompt** — `extract` — ticket `launch-autoquit-when-done-or-relaunch-depending-on` → `relay-os/contexts/relay/architecture/SKILL.md` (Prompt composition).
  Durable mechanism not in architecture: interactive REPL teardown watches a `DONE_MARKER` byte sequence on the PTY (emitted by `relay bump`/`mark done`/`panic` success path). Any injected prompt layer containing that literal sequence must be defused by the composer (`compose._defuse_done_marker`, zero-width joiner) or it SIGTERMs the agent. Add one bullet under "Prompt composition".

- **Per-skill requirements.txt install into the venv** — `extract` — ticket `provide-a-google-calendar-capability-so-skills-don` → `relay-os/contexts/relay/architecture/SKILL.md` (bundled batteries / mode:script env).
  A bundled/project-local skill may ship `requirements.txt`; `install_skill_requirements` (tail of `install_venv` during `relay init`/`--update`) pip-installs every `relay-os/skills/**/requirements.txt` AND `relay-os/bootstrap/skills/**/requirements.txt` into `.relay/.venv`. Also: new files under `src/relay/resources/templates/relay-os/bootstrap/` must be `git add -f` (that bootstrap path is gitignored in consumer repos). Closest home: architecture "bundled batteries".

**gap**

- **git-sync authoring-sync limitations** — `gap` — `relay-os/contexts/relay/sync/SKILL.md` (Known limitations). Source ticket `git-sync-c-panic-and-ticket-auth` (still on disk → also a Phase 4 candidate; AVOID double-PR, coordinate).
  Two known holes deferred as follow-up: (1) `relay ticket` authoring that creates a referenced context/skill support file syncs only the task dir (`git.sync_task_state(ref.path)`), so other checkouts see the ticket edit but not the referenced file; (2) bare `relay ticket` launches the stateless `bootstrap/ticket` shim, so the authoring-sync block doesn't run at all. Home: a "Known limitations" note in `relay/sync` and/or a tracked draft ticket.

- **Recurring runs can mark done without advancing declared state** — `gap` — no carrier; → tracked draft ticket.
  Evidence: `relay-dev-update` daily on 2026-05-26 & 05-31 never advanced `last_commit` (05-31 period blackboard empty — final step never ran), so 06-03 inherited a ~2-week range (~89 commits/~28 PRs to reconcile). The period-task contract is documented but nothing *detects* a run finishing without advancing its declared state key — silent until a human notices a giant digest. Needs design judgment → draft ticket.

**stale**: none. All contexts match repo reality (subagent verified git-sync A/B/C, period-task, current-direction, architecture all current).

**Per-done-ticket durable-knowledge steer for Phase 4** (15 of 18 carry nothing durable):
carry durable → `git-sync-c-panic-and-ticket-auth` (gap→sync), `launch-autoquit-when-done-or-relaunch-depending-on` (extract→arch), `provide-a-google-calendar-capability-so-skills-don` (extract→arch).
nothing durable (already-extracted-in-PR or scratch/smoke) → atomic-writes-*, blackboard-for-recurring-*, bump-backward-possible, document-bootstrap-ticket-*, dream-w22-cleanup-orphan-markers, dream-w23-validate-drift, fail-loud-on-missing-context-*, git-sync-a-*, git-sync-b-*, relay-dev-update-2026-05-31, relay-dev-update-2026-06-03, scratch-verify-autoquit-marker, scratch-verify-autorelaunch-chain, test-autobimp, test-autobump.

### Phase 3 — contract audit (drift)

- **README claims `relay panic` "releases the task lock"** — `drift` — `README.md:561` (also 559-562).
  No task lock exists in Relay (`src/relay/panic.py` only appends blocker + syncs; grep for task_lock/release-lock = nothing). Contradicts `relay/architecture` ("no filesystem mutex"), `relay/project-stage`, `docs/design.md:100`. README is the only living surface still claiming a lock. → fix README.

- **README documents `relay retire --mode auto` as supported** — `drift` — `README.md:549,554-555`.
  `src/relay/commands/retire.py:51-56` rejects `mode == "auto"` ("mode=auto is temporarily disabled..."). Cannot run. (`bootstrap/contexts/relay/cli` already says auto is disabled; only README contradicts.) → fix README.

- **README stale test count** — `drift` — `README.md:666`. Comment says `# 83 tests`; repo has ~545 `def test_`. Minor prose drift. → fix README.

- **Copy divergence: live bootstrap `relay/cli` context missing `--all` section** — `drift` — `relay-os/bootstrap/contexts/relay/cli/SKILL.md` vs packaged `src/relay/resources/templates/.../relay/cli/SKILL.md` (~454 live vs 468 packaged; packaged documents `relay recurring --all` in two blocks).
  `--all` flag is real (`src/relay/commands/recurring.py:39-45`). Packaged is correct; live bootstrap copy is stale. **RESOLVED → no-op:** `relay-os/bootstrap/` is NOT git-tracked in this repo (untracked/generated); the live copy is regenerated from the correct packaged template on `relay init --update`. Self-healing — no PR.

## Prior-run PR overlap (CRITICAL for idempotency)

A prior Dream run left 3 open PRs covering essentially this whole corpus:
- **#280** `dream/retro-codebase-batteries` — new `relay/codebase` context (authoring bundled batteries) + prunes/deletes 17 task dirs (incl. all my Phase-4 candidates except bump-backward-possible).
- **#281** `dream/retro-architecture-other-agent` — `relay/architecture` other-agent assignee token + deletes `bump-backward-possible`.
- **#282** `dream/fix-readme-drift` — README: recurring scaffolding, `--mode auto` disabled, test count.

Effect: **all 18 done tickets are already being deleted by open PRs → 0 eligible for Phase 4.**

## Phase log (cont.)

- Phase 4 retro/done-ticket: **NO-OP**. 0 of 18 eligible (all deleted by open PRs #280/#281).
  Re-running would open duplicate/conflicting PRs; eligibility gate prevented that. No subagent run.
- Phase 5 cleanup-orphan-markers: **no-op** (child `dream-p5-cleanup-orphan-markers-dbg-211208`).
  No cleanup-eligible processed done tickets have surviving dirs (all markers are in unmerged PRs).
- Phase 6 disposition: done (see summary).

## Dream Run Summary

Generated: 2026-06-04T04:30Z. Mode: interactive debug, full real run, Slack allowed.

| Phase | Result |
| --- | --- |
| 1 validate-drift | reported — 38 issues (0 direct-fix, 1 pr-proposal, 37 human-needed); no files repaired |
| 2 knowledge scan | reported — 2 extract, 2 gap, 0 stale |
| 3 contract audit | reported — 4 drift |
| 4 retro/done-ticket | no-op — 0/18 eligible (all in open PRs #280/#281) |
| 5 cleanup-orphan-markers | no-op |
| 6 disposition | proposed — 2 gap drafts created; 2 PR comments; overlaps deferred |

**Findings → disposition (8 total):**
- extract `requirements.txt`/batteries install → **covered** by open PR #280 (relay/codebase). no-op.
- extract `DONE_MARKER` defuse-in-prompt (compose.py:51) → uncaptured; source ticket deleted by #280 → **commented on #280** to fold a note into relay/architecture (#281). [human review gate]
- gap git-sync authoring-sync limitations → **draft** `sync-support-files-and-bare-ticket-shim-authoring`.
- gap recurring runs mark done w/o advancing state → **draft** `detect-recurring-runs-that-mark-done-without-advan`.
- drift README "releases the task lock" → uncovered by #282 (same file) → **commented on #282** to fold in. [human review gate]
- drift README `--mode auto` disabled → **covered** by #282. no-op.
- drift README test count 83→545 → **covered** by #282. no-op.
- drift copy-divergence bootstrap/cli `--all` → **no-op**, untracked generated copy, self-heals on `relay init --update`.
- validate pr-proposal: `test-autobump` large-blackboard (34 KiB) → ticket is deleted by #280, so no condensation needed. no-op.

**Artifacts created this run:**
- Draft: `sync-support-files-and-bare-ticket-shim-authoring`
- Draft: `detect-recurring-runs-that-mark-done-without-advan`
- PR comment: https://github.com/FastJVM/relay/pull/280#issuecomment-4618956227
- PR comment: https://github.com/FastJVM/relay/pull/282#issuecomment-4618956359

**Human review gates:**
1. Before merging #280: fold the `DONE_MARKER` defuse note into relay/architecture (else knowledge lost with launch-autoquit).
2. Before merging #282: also remove README "releases the task lock" clause.
3. validate ERROR `split-context-to-doc-user-accessible-and-editable` missing-step — lifecycle, human-only (rewind/relaunch/hand-edit step).
4. validate warn `relay-competition` unknown-assignee 'nick' — owner decision.

No-op PR opens this run by design: the prior Dream run's open PRs already carry the durable changes; opening duplicates would conflict. Idempotency held.
