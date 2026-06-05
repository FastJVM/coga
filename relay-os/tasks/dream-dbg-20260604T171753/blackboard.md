# Dream run — dream-dbg-20260604T171753

Mode: interactive (debug). Scope decision: **full autonomous run** — all 6
phases, real PRs, delete the eligible done tickets, scaffold gap tickets, then
self-delete.

## Orientation (done)

- Remote: `FastJVM/relay` (https), `gh` authed as nicktoper. PRs can be opened.
- All four Dream worker skills resolve via `relay-os/bootstrap/skills/`:
  - `bootstrap/dream/tasks/validate-drift`
  - `bootstrap/dream/tasks/cleanup-orphan-markers`
  - `retro/done-ticket`
  - `bootstrap/delete-task` (the delete gate IS installed)
- Child script-task mechanism: `relay draft "<t>" --mode script --workflow
  dream/<wf>` → `relay mark active <slug>` → `relay launch <slug>` (runs run.py).
- Eligible done tickets (status: done, dir present): **3**
  - `document-the-blackboard-producer-consumer-pattern`
  - `recurring-catch-up-for-missed-runs-launch-auto-tem`
  - `stop-overloading-relay-slack`

## Phase status

1. validate-drift — DONE → reported. Child: `dream-validate-drift-dbg-20260604t171753`.
   39 issues, 0 direct-fix, 0 pr-proposal, 39 human-needed. Safe-repair: no files created.
   - 37× `missing-workflow` (warn) on drafts — by-design design state, not actionable.
   - 1× `unknown-assignee` (warn): `relay-competition` assignee 'nick'. human-needed.
   - 1× `missing-step` (ERROR): `split-context-to-doc-user-accessible-and-editable`
     — `workflow:` set but `step:` missing. Lifecycle = human-only. human-needed.
2. knowledge scan — DONE. 3 extract candidates (all done tickets), all verified
   against code. F1 catch-up reclassified (unbuilt); F2/F3 already-captured.
   stale (1) and gap (3) dropped after review.
3. contract audit — DONE. Subagent's 2 "drift" were false positives (gitignored
   mirror). Correct sweep found 1 real drift (F6 principles) + 1 cosmetic (F7).
4. retro/done-ticket — DONE. No knowledge PR (nothing extractable). One
   delete-only prune PR #285 (F2+F3). F1 left in place per human.
5. cleanup-orphan-markers — DONE → no-op. Child task ran clean, deleted.
6. disposition + run summary — DONE. F6 → proposal PR #286. Summary below.

## Findings

All subagent findings were independently verified against code/diffs before
disposition (the Phase 3 subagent had the copy-divergence *direction*
backwards; verified real, direction corrected).

### F1 — Catch-up ticket marked `done` but feature NEVER BUILT [escalated]
- class: was extract → reclassified after code verification
- target ticket: `recurring-catch-up-for-missed-runs-launch-auto-tem` (done)
- VERIFIED AGAINST CODE: the catch-up backlog feature is NOT implemented.
  - `Config` has no `recurring_max_catchup` field (config.py).
  - `scan_due` computes a single `_last_firing`/`period_key` per template — no
    missed-period enumeration, no cap, no oldest-first recovery (recurring.py).
  - Zero hits for `catchup`/`max_catchup` anywhere in `src/`. No catch-up tests.
  - recurring.py history is #276 (--all), #277 (idle-timeout), #283 (body
    preserve) — no catch-up PR ever landed.
  - The auto→interactive + no-TTY-skip *part* DID land (via #277 etc.) and is
    already documented in the packaged contexts being synced by F4/F5.
- Disposition: do NOT extract catch-up "knowledge" (would document a phantom
  feature = new drift). Do NOT silently prune/delete the ticket — that erases
  the spec of unbuilt work mislabeled `done`. ESCALATED to human (see below).

### F2 — Blackboard producer/consumer pattern [extract — already captured]
- class: extract → Phase 4 retro (expected: prune)
- target ticket: `document-the-blackboard-producer-consumer-pattern` (done)
- summary: Knowledge already landed in `relay/patterns` (PR #284 merged). Ticket
  carries no NEW durable knowledge → expect no-new-durable-knowledge prune.

### F3 — Daily digest Slack batching [extract — already captured]
- class: extract → Phase 4 retro (expected: prune)
- target ticket: `stop-overloading-relay-slack` (done)
- summary: Two-tier Slack model already in `relay/sync` + `relay/patterns`
  (PR #275 merged). No NEW durable knowledge → expect prune.

### F4/F5 — WITHDRAWN (false positives)
- The Phase 3 subagent (and my first verification) diffed the GITIGNORED
  generated mirror `relay-os/bootstrap/` (a local cache refreshed by
  `relay init --update`, 0 files tracked) against the packaged template.
  That mirror being stale is operational, not a tracked-contract drift.
- The TRACKED dogfood context `relay-os/contexts/relay/architecture/SKILL.md`
  is IDENTICAL to the tracked packaged copy → no drift. There is no tracked
  `relay/cli` dogfood context at all (cli ships only as a packaged template).
- Lesson recorded: copy-divergence must compare TRACKED pairs, not the
  gitignored `relay-os/bootstrap/` mirror. Re-ran the correct sweep myself.

### F6 — Packaged relay/principles template behind live rewrite [drift] ✅PR
- class: drift → Phase 6 proposal PR #286 (resync diverged tracked pair)
- target: `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/principles/SKILL.md`
- summary: Live `relay-os/contexts/relay/principles/SKILL.md` was rebuilt around
  the "think better" root in #253 (2026-05-30); the packaged template (last
  touched 2026-05-06) never got the rewrite, so `relay init` ships stale
  principles. Resync packaged ← live. PR #286 (pr-required, human disposes).

### F7 — google-agents-cli-workflow copy pair: cosmetic only [no-op]
- Tracked live vs packaged differ by one trailing space + one blank line.
  Cosmetic noise on a vendored skill. Not worth a PR. Noted, no action.

### Operational FYI (not a Dream PR)
- This dogfood repo's gitignored `relay-os/bootstrap/` mirror is stale relative
  to the package (it predates the same #253-era updates). Refresh locally with
  `relay init --update`. Nothing tracked is wrong; no PR.

### Reviewed and dropped (recorded for the human)
- DROPPED [stale] recurring context "Defaults to `auto`": subagent conflated
  the template `mode:` field default with the runtime `mode_override`. Field
  default is not contradicted by code. Too weak for a PR.
- DROPPED [gap×3] REM formalization / recurring-template lifecycle / dream-skill
  contract template: speculative doc ideas, no evidence of a *repeated* pattern
  or struggle in the corpus (the bar for `gap`). Secrets-per-skill is already
  tracked by ticket `pass-secrets-to-skills-with-per-skill-scope`. Not
  scaffolding draft tickets for these — would add noise to a 37-draft backlog.


## Dream Run Summary

Generated: 2026-06-05T00:49:27+0000 (debug run, interactive, full autonomous scope)

| Phase | Result | Notes |
| --- | --- | --- |
| 1 validate-drift | reported | 39 issues, 0 direct-fix/0 pr-proposal/39 human-needed. 37× missing-workflow (draft design state), 1× unknown-assignee (relay-competition), 1× missing-step ERROR (split-context-to-doc...). No files repaired. |
| 2 knowledge scan | reported | 3 extract candidates (done tickets); verified. 1 stale + 3 gap dropped after review. |
| 3 contract audit | reported | 1 real drift (F6 principles); subagent's 2 were false positives (gitignored mirror); 1 cosmetic (F7). |
| 4 retro/done-ticket | pr-opened | No knowledge PR; one delete-only prune PR #285 (F2+F3). F1 left in place. |
| 5 cleanup-orphan-markers | no-op | No orphaned processed markers. |
| 6 disposition | pr-opened | F6 → proposal PR #286. Findings routed. |

### Findings (counts)
- extract: 3 — F1 catch-up (escalated, see below), F2 blackboard-pattern + F3 slack-digest (pruned, already captured).
- stale: 1 — dropped (weak; field-default vs runtime-override conflation).
- gap: 3 — dropped (no repeated-pattern evidence; one already ticketed).
- drift: 1 real (F6 principles → PR #286) + 1 cosmetic (F7, no-op). F4/F5 withdrawn (false positives).

### PRs opened
- **#285** — Prune done tickets with no new durable knowledge (deletes F2+F3 dirs; markers in PR history). https://github.com/FastJVM/relay/pull/285
- **#286** — Resync packaged relay/principles template with the live rewrite (F6 drift). https://github.com/FastJVM/relay/pull/286

### Draft tickets created
- None (no gap findings survived review).

### human-needed / review gates
- **F1 — done-but-unbuilt ticket** `recurring-catch-up-for-missed-runs-launch-auto-tem`: marked `done` but its core feature (missed-period catch-up + `max_catchup`) is NOT in `src/relay/`. Per human decision (this run): reported only, ticket left untouched on disk. Needs an owner call on whether to reopen/rebuild or close as abandoned.
- Both PRs (#285, #286) are pr-required — human reviews and merges; Dream never auto-merges.
- validate-drift human-needed items: `split-context-to-doc-user-accessible-and-editable` (missing-step ERROR, lifecycle = human-only) and `relay-competition` (unknown-assignee 'nick').
- Operational: refresh stale local `relay-os/bootstrap/` mirror with `relay init --update` (not a PR).
