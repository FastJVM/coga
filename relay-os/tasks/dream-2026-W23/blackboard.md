The blackboard is a notepad to be written to often as the human and agent works through a task.

## Orientation (2026-06-03, interactive run)

Branch `recurring-launch-all`, remote `FastJVM/relay` (gh authed as nicktoper). Working
tree is dirty: `src/relay/scaffold.py` (a non-Dream source change, not mine) plus several
`relay-os/**` log/blackboard files.

### Repo state
- `relay status`: 82 tasks · 4 in_progress · 2 active · 56 draft · **20 done**.
- Worker skills present: `bootstrap/dream/tasks/validate-drift` (P1),
  `bootstrap/dream/tasks/cleanup-orphan-markers` (P5), `retro/done-ticket` (P4),
  and `bootstrap/delete-task` (so cleanup can actually delete).

### Prior / overlapping Dream activity found
- `dream-w23-validate-drift` (done) — a Phase-1 child that already ran today 19:02,
  found 38 issues: 0 direct-fix, 1 PR-proposal (test-autobump large blackboard),
  37 human-needed (mostly draft `missing-workflow` warnings = design state, not drift).
- `dream-dbg-20260603T161005` (in_progress) — a **debug** Dream run that did orientation,
  ran validate-drift, and **paused with a pending scope question to the human**:
  whether to run the full execute-half (Phase 4 deletes ~18-20 done tickets + many PRs).
  That question is still unanswered.
- `dream-dbg-validate-drift`, `dream-w22-cleanup-orphan-markers` — older done children.

## Decision (human, interactive)
- Scope: **Full run (P1–6)**.
- Git/cleanup: **I handle it** — leave `src/relay/scaffold.py` (+ `recurring.py`, `test_recurring.py`)
  untouched; branch all PRs off `origin/main`; note but don't touch the in_progress debug dream task.

## Execution model
- `origin/main` (42c0c53, PR #279) has identical tree content to local HEAD for contexts/skills/tasks
  (verified: empty diffstat). Divergence is commit-history only (squash). So:
  - Decide phases 1–3: read-only against current working tree.
  - Execute phases 4–6: PR work in **isolated git worktrees off origin/main** (deviation from retro
    skill's "no worktree" default, justified by dirty tree + diverged local branch; produces clean PRs).

## Phase 1 — validate-drift  → reported
- Current `relay validate --json`: 38 issues = 35 `missing-workflow` (warn, drafts w/o workflow =
  design state, human-needed), 1 `unknown-assignee` (relay-competition, human-needed),
  1 `missing-step` (error, split-context-to-doc..., human-needed lifecycle),
  1 `large-blackboard` (test-autobump 34KiB, pr-proposal — but MOOT: test-autobump is a done
  ticket Phase 4 deletes).
- Classification: 0 direct-fix, 1 pr-proposal(moot), 37 human-needed.
- Durable child artifact: `dream-w23-validate-drift` (done, ran today 19:02, identical result,
  `--fix` already applied idempotently). Reused rather than re-spawned.

## Findings (Phase 2 knowledge scan + Phase 3 contract audit)

### extract → Phase 4 knowledge PRs
- **K1 — relay/codebase: "Authoring bundled batteries"** (extract; also absorbs gap G1)
  target: `relay-os/contexts/relay/codebase/SKILL.md` (tracked, no packaged twin).
  sources: `provide-a-google-calendar-capability-so-skills-don`,
  `document-bootstrap-ticket-not-in-skills-frontmatte`, `blackboard-for-recurring-task-must-use-the-permant`.
  Two grounded, repeatedly-rediscovered facts with no carrier:
  (a) new bundled batteries live under `src/relay/resources/templates/relay-os/bootstrap/{skills,contexts}/`;
  that tree is covered by `bootstrap/` in the shipped `.gitignore`
  (`src/relay/resources/templates/relay-os/.gitignore:10`), so new files need `git add -f` or they
  silently never commit. Don't author in the live `relay-os/bootstrap/` (gitignored, overwritten on
  `init --update`). (b) a bundled skill declares Python deps in `requirements.txt`;
  `install_skill_requirements` (tail of `install_venv`, `src/relay/commands/update.py:437`) pip-installs
  every `relay-os/**/skills/**/requirements.txt` into `.relay/.venv` on `relay init`/`--update` (after the
  battery is materialized into `relay-os/bootstrap/`).
- **K2 — relay/architecture: add `other-agent` role token** (extract; same edit as stale S1)
  target: `relay-os/contexts/relay/architecture/SKILL.md:34-37` + packaged twin
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md:34-37`
  (sync per CLAUDE.md). source: `bump-backward-possible`. Role-token list reads
  `owner | human | agent`; code (`bump.py:55-65`, `VALID_ASSIGNEE_ROLES`) has a 4th: `other-agent`,
  which resolves to the peer agent (requires two `[agents.*]`) and drives peer-review flips
  (`code/with-review`) and agent-rotation relaunches.

### prune (no durable knowledge) → folded into a Phase 4 knowledge PR `## Pruned`
16 done tickets: relay-dev-update-dbg-20260603T161005, dream-dbg-validate-drift, relay-dev-update-2026-06-03,
dream-w23-validate-drift, atomic-writes-for-ticket-log-and-done-marker-files, test-autobimp,
fail-loud-on-missing-context-or-skill-at-launch, git-sync-c-panic-and-ticket-auth, git-sync-b-cross-branch-to-main,
git-sync-a-helper-and-same-branch, relay-dev-update-2026-05-31, test-autobump, scratch-verify-autorelaunch-chain,
scratch-verify-autoquit-marker, launch-autoquit-when-done-or-relaunch-depending-on, dream-w22-cleanup-orphan-markers.
(git-sync-*/atomic-writes/fail-loud knowledge already in relay/sync + relay/principles; rest are
test/scratch/dbg/digest execution noise.)

### drift → Phase 6 proposal PR(s)
- **D1 — README recurring-blocking claim** (drift, code-reality)
  `README.md:297-298` says a not-`done` prior period blocks the new period's scaffold; code
  (`recurring.py scan_due`/`scaffold_template`) scaffolds independently. Contexts already correct.
- **D2 — README `--mode auto` shown as working** (drift, code-reality)
  `README.md:549` (+44, 231, 442-444) documents `--mode auto`; code rejects it
  (`launch.py:206-213`, `retire.py:51-55` "temporarily disabled"). cli/architecture contexts already note this.
- **D4 — README test count** (drift, code-reality) `README.md:666` says "83 tests"; suite is 516.
  → D1/D2/D4 all in `README.md` → ONE proposal PR.
- **D3 — cli `--all` copy divergence** (drift, copy-divergence) → **no-op**: live
  `relay-os/bootstrap/contexts/relay/cli` is gitignored/materialized; packaged source template already
  documents `recurring --all`. Self-heals on `relay init --update`. Nothing committable.

### noted, not actioned
- `relay/current-direction/SKILL.md` "Open ticket queue" lists tickets no longer on disk — but that
  context is self-described as a transient living document, not a durable contract. Left for human.

## Why I paused before Phase 1
This is interactive mode, the tree is dirty + on a feature branch, there's already a
pending scope decision from the debug run, and the execute half is heavy and outward-facing
(opens multiple PRs against the shared remote that DELETE 20 done ticket dirs, plus
proposal PRs and gap drafts). Asking before committing to that.

## Dream Run Summary

Generated: 2026-06-04T03:49Z · run: dream-2026-W23 (interactive, full P1–6)

| Phase | Result | Notes |
|---|---|---|
| 1 validate-drift | reported | 38 issues (35 missing-workflow=design-state, 1 unknown-assignee, 1 missing-step, 1 large-blackboard). 0 direct-fix, 1 pr-proposal(moot), 37 human-needed. Reused `dream-w23-validate-drift` child (idempotent --fix already applied). |
| 2 knowledge scan | proposed | 20 done tickets read → 2 durable extracts (K1 codebase, K2 architecture), 16 prune, 1 gap (folded into K1). |
| 3 contract audit | proposed | 4 drift: D1/D2/D4 (README) → 1 PR; D3 (cli --all) no-op (gitignored materialized copy; packaged source already correct, self-heals on `init --update`). |
| 4 retro/done-ticket | pr-opened | 2 knowledge PRs deleting all 20 done tickets (3 contributed knowledge, 16 pruned, 1 architecture source). |
| 5 cleanup-orphan-markers | no-op | Skill confirmed: no cleanup-eligible processed markers with surviving dirs. |
| 6 disposition | pr-opened | extract→#280/#281; stale S1→#281; drift→#282; gap→folded into #280. |

### PRs opened
- **#280** — New context: relay/codebase — authoring bundled batteries (+ prune 16 done tickets). https://github.com/FastJVM/relay/pull/280
  Sources w/ knowledge: provide-a-google-calendar-capability-so-skills-don, document-bootstrap-ticket-not-in-skills-frontmatte, blackboard-for-recurring-task-must-use-the-permant. Pruned: 16.
- **#281** — Context: relay/architecture — add other-agent assignee role token. https://github.com/FastJVM/relay/pull/281
  Source: bump-backward-possible. Edits tracked context + packaged twin (sync).
- **#282** — Fix README drift: recurring scaffolding, --mode auto disabled, test count. https://github.com/FastJVM/relay/pull/282

### Draft tickets created
- none (the only gap finding had a clear home and was folded into #280 as durable knowledge).

### Findings tally
- extract: 2 (durable) + 16 no-durable (pruned) = 20 done tickets, all deleted via #280/#281.
- stale: 1 (= K2, in #281).
- gap: 1 (folded into #280).
- drift: 4 → 3 fixed in #282, 1 no-op (D3, self-healing).

### Human-needed / review gates
- All 3 PRs are `pr-required` proposals — human reviews & merges; Dream did not auto-merge.
- Phase 1's 37 human-needed validator items are mostly `missing-workflow` warnings on draft tickets =
  design state (owner picks a workflow), not drift. 1 `missing-step` error on
  `split-context-to-doc-user-accessible-and-editable` is a human-only lifecycle fix.
- Noted-not-actioned: `relay/current-direction` "Open ticket queue" lists tickets no longer on disk
  (transient living doc — left for human to refresh).
- Overlap: in_progress debug task `dream-dbg-20260603T161005` (a parallel debug Dream) left untouched
  per human instruction; its pending scope question is now mooted by this real run.
