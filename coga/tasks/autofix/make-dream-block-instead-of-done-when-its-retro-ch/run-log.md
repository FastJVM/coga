# Recurring sweep — 2026-08-31 14:17:11

- repo: coga
- mode: bare sweep
- templates scanned: 7
- tasks run: 6
- problems: 0

## Scan

```
autoclose-merged     ready (Mon 08:00)          launch
blocker-reminders    ready (Mon 10:00)          launch
branch-sweep         ready (Mon 07:00)          launch
digest               ready (Mon 09:00)          launch
dream                ready (Mon 09:00)          launch
resolve-conflicts    ready (Mon 08:00)          skip (paused)
skill-update         ready (Mon 09:00)          launch
```

## Task outcomes

### recurring/branch-sweep — completed

- template: `branch-sweep`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-W36

`coga run branch-sweep` exited 0. Preconditions held: `gh` authed as
nicktoper, `git worktree prune`/list succeeded (pruned the stale
`/tmp/coga-minimal-base-plugin` registration).

Deleted (8 local, 1 remote):
`codex/minimal-base-plugin`, `codex/plugin-debug-mode` (+ its remote ref),
`codex/retro-retire-leftover-design-ticket-worktrees-and-branch-knowledge`,
`coga/skill-update`, `dream/fix-agent-guide-config-paths`,
`dream/fix-communication-readme-pipeline-range`,
`dream/fix-dream-template-sharded-scans`,
`dream/fix-recurring-recipe-dispatch-claim`,
`dream/record-committed-multiply-toml-opt-out`.

Skipped, live ticket: `codex/dogfood-updater`, `codex/v1-telemetry-sender`.

Skipped, `skipped-worktree-pinned` (merged but held by a live worktree —
non-fatal, by design): `codex/co-design-dialogue-skill`,
`codex/codex-m-dogfood`, `codex/codex-m-silent-launch`,
`codex/launch-gates-skill`, `codex/multiply-probe-harness`,
`codex/stop-git-delta-smoke`. Four of the six sit in `/tmp` worktrees; they
will keep recurring here until those worktrees are retired.

Skipped, unmerged with no merged PR (residual manual pass):
`codex/marketplace-plugin-product-boundary`,
`codex/multiply-liveness-receipt`, `codex/session-start-banner`.

A post-sweep `git fetch --prune` cleared several stale remote-tracking refs
(origin refs for the dream/* and co-design/silent-launch/stop-git-delta
branches). Those upstream branches were already gone — GitHub's
delete-on-merge, not this sweep — so the sweep's one logged remote delete is
the accurate count.
```

### recurring/autoclose-merged — completed

- template: `autoclose-merged`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run note — sweep 2026-08-31

`coga run autoclose` exited 0. One ticket closed:

- `v1/updater/1-dogfood-updater` — PR #30 merged, ticket was on its final
  workflow step, marked `done` (log line: `auto-bumped on merge of PR #30 → done`).

No mid-workflow merges were found, so nothing was left alone as suspicious.
The closed ticket still records a feature checkout, so the sweep appended the
retire follow-up section below; `coga retire` remains the human's to run.

Nothing durable to carry to the next firing — the parent blackboard keeps no
cross-run cursor for this task.

## Autoclose Sweep: retire follow-ups

Generated: 2026-08-31T21:18:53+00:00
Task: `recurring/autoclose-merged`

1 auto-closed ticket(s) still have a recorded feature checkout. Autoclose never removes one — `coga retire` owns the worktree and branch safety proofs:

- `v1/updater/1-dogfood-updater` "1-Dogfood updater": worktree `/tmp/multiply-dogfood-updater`, branch `codex/dogfood-updater` — `coga retire v1/updater/1-dogfood-updater`
```

### recurring/digest — completed

- template: `digest`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-08-31

Ran `coga run digest` — the recipe owns the whole flush, so this session had
nothing to decide.

- Posted: 19 items for period 2026-08-31 (6 spool Done records + merged commits).
- Spool drained: `consumed_through` advanced to `1f17aa8c2374`, consumed prefix
  trimmed, newest record kept as the anchor.
- Git high-water advanced in the parent's `### Digest State`:
  `last_commit: ef1b50f`, range `00fd245..ef1b50f` (46 commits scanned,
  13 reported after the state-sync filter).

Nothing anomalous; no gotchas worth extracting.
```

### recurring/skill-update — completed

- template: `skill-update`
- ticket status after the run: done

What the run wrote to its blackboard:

```
[... truncated ...]
pgrade coga`
- `bootstrap/dream/tasks/validate-drift`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/import`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/skill-update`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/build-automation`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/dochub`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/playwright`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `code/address-pr-comments`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `code/design`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `code/implement`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `code/open-pr`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `code/self-qa`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/autoclose/sweep`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/blockers/remind`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/branch-sweep/sweep`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/calendar-reminder`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/digest/flush`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/gmail`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/google-calendar`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/show`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/ticket/finalize`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `retro/done-ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`

## Run notes (2026-W36)

Verified after the recipe ran:

- Pruned stale remote-tracking refs (`git remote prune origin`) **before** the
  run, pre-empting last week's (2026-W35) push rejection. Nothing was stale
  this time, but the prune is cheap insurance.
- PR #32 is a draft against `main` from `coga/skill-update`. Content is a clean
  upstream `v1.4.1 → v1.4.2` bump of the 7 `google-agents-cli-*` skills
  (`github-ref`, `github-tree-sha`, `version`, and the pinned-version install
  hints). No local adaptations touched.
- 0 follow-up statuses, so the recipe exited 0 as designed.

### Gotchas

- `git diff main..coga/skill-update` overstates the PR: the branch is cut from
  the pre-run `main`, so commits that land on `main` afterwards (e.g. coga's own
  `Sync coga state`) read as deletions. Diff against the merge-base
  (`git diff $(git merge-base main coga/skill-update) coga/skill-update`) to see
  what the PR actually changes — GitHub already does this.
```

### recurring/blocker-reminders — completed

- template: `blocker-reminders`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run 2026-08-31

- Period from `coga/log.md`: `created recurring/blocker-reminders for 2026-08-31`.
- `coga run blocker-reminders` → `[blockers] no unresolved blockers to remind.` (exit 0).
- Cross-checked independently: `grep -rl "^status: blocked" coga/tasks/` matched nothing;
  `coga status` shows 35 tasks (2 in_progress, 1 active, 31 draft, 1 paused), none blocked.
- No reminders posted, no watermarks written, no files changed (`git status --porcelain` empty).
- No cross-run state to advance: the parent declares no `state_keys`, and reminder
  dedup lives on each blocked task's own `## Blocker reminders` watermark by design.
```

### recurring/dream — completed

- template: `dream`
- ticket status after the run: done

What the run wrote to its blackboard:

```
[... truncated ...]
g/skill-update` was **not** direct-deleted: its blackboard carried a real reusable gotcha under `### Gotchas`, so it went through knowledge PR #34 per the `coga/period-task` context. Dream's own template says the opposite; that contradiction is finding `stale`-21 and is fixed in PR #38.

### Draft tickets created (6)

`record-the-codex-cli-invocation-constraints-as-a-c`, `give-the-empty-v1-stub-tickets-a-body-or-retire-th`, `mark-imported-third-party-skills-as-reference-only`, `carry-the-apply-the-register-amendment-step-in-a-w`, `record-the-two-self-qa-hazards-from-done-ticket-bl`, `repair-ticket-referents-when-a-referent-is-renamed` — all on `draft-for-human`, each with a real body carrying its finding.

Six further `gap` findings were **not** ticketed: they already have tracked draft tickets
(`record-agent-harness-capability-boundaries-as-a-sk`, `record-the-bounded-local-record-and-fail-open-cont`,
`record-the-repo-verification-battery-as-a-durable`, `add-decision-register-authoring-style-context`,
`preserve-owner-decisions-not-to-act-beyond-the-tic`, `define-tuning-set-discipline-for-the-v1-continuati`).
A seventh (`skill-update` shared-branch push hygiene) is carried by PR #34's new context.

### human-needed

1. **Two audit-trail lines are unpushed.** `coga/log.md` lines recording the PR #33 and #34 Slack posts exist only on local branch `dream/retro-2026-W36-1788212557` (worktree `/tmp/dream-retro-2026-W36`). Both `git cherry-pick` and `git push` of that branch were denied by the permission classifier, so Dream could not land them. **The worktree and branch were deliberately preserved rather than removed** — deleting them would destroy the lines. The copied `coga.local.toml` was removed. To finish: push the branch, or let the next coga sync reconcile, then `git worktree remove /tmp/dream-retro-2026-W36 && git branch -D dream/retro-2026-W36-1788212557`.
2. **Slack `important_webhook` unresolved** (Phase 1). Recurring failure alerts cannot route until `[notification.slack].important_webhook` is configured. Needs environment access; Dream does not touch secrets or machine-local config.
3. **`v1/1b-lifecycle-experiments` blackboard is 53.4 KiB** (Phase 1), above the 32 KiB warning and included in every launch prompt. Needs a reviewed condensation that preserves current decisions and blockers.
4. **9 done tickets are retirement debt**, each recording a real feature checkout, so they are not Retro input and Dream did not touch them: `v1/1-base-plugin`, `v1/1b-lifecycle-experiments`, `v1/2b-stop-gated-git-delta-optimization-smoke`, `v1/add-isolated-codex-test-install`, `v1/clarify-production-and-probe-package-boundary`, `v1/codex-m-untouchable`, `v1/updater/1-dogfood-updater`, `add-a-co-design-dialogue-skill-for-design-tickets`, `add-a-launch-gates-skill-for-ticket-launch-precond`. Each needs a human-typed `coga retire <slug>`.
   **This blocks 5 of the 7 `extract` findings** — the durable knowledge in `v1/2b`, `v1/1b`, `v1/1-base-plugin`, `v1/add-isolated-codex-test-install` and `add-a-launch-gates-skill-…` cannot be extracted until those tickets retire. Only the 2 extracts on `v1/3-telemetry` and `recurring/skill-update` landed this run.

### Deferred by overlap (not fixed, intentionally)

- `multiply/v1-architecture` (3 `stale` findings) — open PR **#31** already modifies that file. Left for its review.
- The 7 `google-agents-cli-*` skills (6 `stale` + 1 `drift`, incl. the `agents-cli-observability` dead pointer and the "Always active" claim) — open PR **#32** modifies all seven. The retention question itself belongs to the live `decide-the-fate-of-the-imported-google-agents-cli` ticket, corrected by PR #39.

### Note on this checkout

Another session was writing to the primary checkout during this run (`coga/tasks/v1/telemetry/1-sending-infrastructure.md` at 14:53, `coga/tasks/v0/7-reporting.md` later). Both were committed by coga's own sync, not by Dream, and are on `main`. Dream committed only its six gap-ticket bodies.
```

## Sweep notes

- launching 6 due task(s) sequentially
