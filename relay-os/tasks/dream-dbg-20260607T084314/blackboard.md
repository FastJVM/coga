The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run Plan (dream-dbg-20260607T084314)

Started 2026-06-07. Interactive [debug] Dream run.

### Pre-run survey
- `relay validate --json`: ok_count=71, 0 errors. All issues are `missing-workflow`
  WARNINGS on draft tickets — benign (drafts legitimately have no workflow). No
  deterministic fixes pending.
- Eligible done tickets for Phase 4 retro: exactly **1** — `digest-dbg-20260606T222205`.
  (digest-dbg-20260607T084314 already deleted; that's the only other digest.)
- Open PRs from a prior Dream run: **#312** (drift: Retro per-run cap) and **#313**
  (drift: cleanup-orphan-markers no longer gates on delete-task). Phase 3 must NOT
  re-find these two drifts — they're already in flight.
- `bootstrap/delete-task` skill EXISTS now → Phase 5 cleanup can actually delete,
  but should find no candidates (knowledge PRs delete in-PR).
- gh authed (nicktoper), remote FastJVM/relay.

### Phase status
- [x] P1 validate-drift (script child `dream-p1-validate-drift`) — 42 issues, ALL human-needed
- [x] P2 knowledge scan (subagent) — 0 extract, 2 stale, 3 gap
- [x] P3 contract audit (subagent) — 3 drift, all = stale gitignored mirror (not source drift)
- [x] P4 retro/done-ticket — 1 ticket direct-deleted (no durable knowledge)
- [x] P5 cleanup-orphan-markers (script child `dream-p5-...`) — no-op
- [x] P6 disposition + run summary

### P1 validate-drift result
Child task `dream-p1-validate-drift` (done). 42 issues, all `human-needed`, 0 auto-fixed:
- 40× `missing-workflow` (warn) on draft tickets — design state, not drift. No action.
- 2× `missing-step` (ERROR): `relay-additions-spec`, `split-context-to-doc-user-accessible-and-editable`
  — `workflow:` set but `step:` missing. Human-only lifecycle correction. → run summary human-needed.
- 1× `unknown-assignee` (warn): `relay-competition` assignee 'nick' not a known agent/role. → human-needed.

CLEANUP OBLIGATION: child script tasks (dream-p1-*, dream-p5-*) are Dream machinery and
must be `relay delete`d at end of run so next Dream's Phase 4 doesn't retro them.

## Findings

All Phase-2/Phase-3 findings VERIFIED against code before disposition. Source of truth
for the drifts: `src/relay/`.

### D1 — `drift` — live bootstrap `architecture` context stale vs packaged (launch auto-activate + sentinel)
Target: `relay-os/bootstrap/contexts/relay/architecture/SKILL.md` (lines ~143-145, 157-159, 171, 202-227)
The live copy says `relay launch` only flips an already-`active` ticket and there is "no
auto-flip from draft", and gives the older sentinel/defuse description. The PACKAGED copy
(`src/relay/resources/templates/.../architecture/SKILL.md`) correctly documents inline
`mark active` of draft/paused/done on launch, and the session-id-bound done-marker. Code
truth: `src/relay/commands/launch.py:204,475` (`_auto_activate`), `commands/bump.py:215` &
`commands/mark.py:169` (`emit_done_marker(session_id=...)`). Fix = resync live→packaged.
NOTE: this file is also Phase-2 stale finding S1 (sentinel order) — same file, folded here,
no separate PR.

### D2 — `drift` — live bootstrap `cli` context stale vs packaged (launch status requirement)
Target: `relay-os/bootstrap/contexts/relay/cli/SKILL.md` (lines ~99-101, 107-112)
Live says launch "Requires `status: active` or `in_progress` — drafts must be activated
via `relay mark active` first". Packaged says launch accepts any status and activates
draft/paused/done inline. Code truth: `launch.py:202-204,475-489`. Fix = resync live→packaged.

### D3 — `drift` — live bootstrap `patterns` context stale vs packaged (recurring ledger location)
Target: `relay-os/bootstrap/contexts/relay/patterns/SKILL.md` (lines ~50-51)
Live implies the recurring period ledger line lives in the spooled blackboard. Packaged
says it lives in the template's `log.md`, never the blackboard. Code truth:
`src/relay/recurring.py:471-477` (`_record_run` appends to `log_path`/`log.md`).
Fix = resync live→packaged. (Aside: recurring.py:32-33 docstring still says blackboard
"doubles as the period ledger" — internal doc inconsistency, NOT in scope; an existing
draft `document-recurring-template-live-vs-packaged-sync` already tracks sync discipline.)

→ DISPOSITION D1+D2+D3 (REVISED — see Dream Run Summary): `relay-os/bootstrap/` is GITIGNORED
   (`relay-os/.gitignore:14`), a regenerable mirror. Packaged source of truth + tracked
   composed contexts already correct. NO PR (it would be empty). Direct-fixed the local mirror
   instead. `resolve_context_path` reads tracked `relay-os/contexts/` first; only `cli` (no
   tracked copy) was serving stale text at runtime.

### S2 — `stale` (LOW CONFIDENCE, NOT ACTIONED) — current-direction timestamp
Target: `relay-os/contexts/relay/current-direction/SKILL.md`
Subagent flagged the 2026-06-01 last-updated stamp as stale and speculated about playbook-
rename deferral. A stale date alone is not contract drift; the rest is speculative. No PR.
Reported only; a human can refresh the posture doc.

### G3 — `gap` (DUPLICATE, NOT ACTIONED) — concept-exploration / workflow-less drafts
Already tracked by existing drafts `document-workflow-less-concept-capture-drafts-as-s`
and `resolve-missing-workflow-validator-vs-concept-capt`. No new ticket — would duplicate.

### G4 — `gap` (DUPLICATE/COVERED, NOT ACTIONED) — interactive-mode "human present overrides status"
Already covered by the shipped interactive-mode context (composed into prompts) and tracked
by drafts `session-done-sentinel-leaks-and-agent-stops-respon` (in_progress) /
`session-done-sentinel-from-mark-done-bump-leaks-in`. No new ticket.

### G5 — `gap` (THIN/COVERED, NOT ACTIONED) — recurring-task authoring guide
`relay/recurring` context exists and `relay-os/recurring/_template/ticket.md` already carries
inline authoring guidance (mode meanings, copy-the-dir instructions, `_` skip rule). Gap is
largely filled. No new ticket.

### EXTRACT — none
Only done ticket `digest-dbg-20260606T222205` holds no durable knowledge (verifying in P4).

## Findings


## Dream Run Summary

Generated: 2026-06-07 (interactive [debug] Dream run, full real run authorized by nick).

| Phase | Result | Detail |
|-------|--------|--------|
| 1 validate-drift | reported | 42 issues, all human-needed; 0 auto-fixed |
| 2 knowledge scan | reported | 0 extract, 2 stale, 3 gap |
| 3 contract audit | reported | 3 "drift" — all = stale gitignored bootstrap mirror, not source drift |
| 4 retro/done-ticket | direct-fixed | 1 done ticket direct-deleted (no durable knowledge) |
| 5 cleanup-orphan-markers | no-op | no orphaned processed-marker directories |
| 6 disposition | direct-fixed | mirror refreshed locally; 0 PRs, 0 draft tickets |

### Findings & disposition
- **3 contract-audit "drifts"** (`relay-os/bootstrap/contexts/relay/{architecture,cli,patterns}/SKILL.md`):
  the live bootstrap copies were stale vs the packaged templates (launch auto-activation,
  session-id-bound done-marker, recurring-ledger-in-log). KEY: `relay-os/bootstrap/` is
  **gitignored** (`relay-os/.gitignore:14`) — a regenerable mirror copied as a unit from
  `src/relay/resources/templates/...` by `relay update`. The packaged source of truth was
  ALREADY correct, and the tracked composed contexts (`relay-os/contexts/relay/architecture`,
  `patterns`) were already correct too. `resolve_context_path` (paths.py:65) reads local
  tracked contexts first, so architecture/patterns had ZERO runtime impact; only `cli` (no
  tracked local copy) fell back to the stale mirror. → **Direct-fixed locally** (refreshed the
  3 mirror files from the package). **No PR** — there is no source-control change to propose;
  a PR would be empty. This is the correct call: a Dream `drift` PR only applies when the live
  copy is tracked. (Debug note: the contract-audit subagent over-reported a gitignored mirror
  as source drift — worth tightening Phase 3's scope to skip gitignored paths.)
- **2 stale** (P2): S1 architecture-sentinel folded into the above (same file). S2
  current-direction timestamp — low-confidence (a stale date isn't drift) → reported only,
  no PR. A human can refresh the posture doc.
- **3 gap** (P2): G3 concept-exploration drafts, G4 interactive-mode human-presence, G5
  recurring-authoring guide — ALL already tracked by existing drafts
  (`document-workflow-less-concept-capture-drafts-as-s`,
  `resolve-missing-workflow-validator-vs-concept-capt`,
  `session-done-sentinel-leaks-and-agent-stops-respon` /
  `session-done-sentinel-from-mark-done-bump-leaks-in`) or already covered by shipped
  contexts (interactive-mode context; `relay/recurring` + `_template/ticket.md` inline guide).
  → **No new tickets** — would duplicate.
- **0 extract**: only done ticket held no durable knowledge.

### human-needed (from Phase 1 validate-drift, surfaced for owner)
- `relay-additions-spec`: `missing-step` (ERROR) — `workflow:` set but `step:` missing. Lifecycle fix is human-only.
- `split-context-to-doc-user-accessible-and-editable`: `missing-step` (ERROR) — same.
- `relay-competition`: `unknown-assignee` (warn) — assignee 'nick' not a known agent/role.
- 40× `missing-workflow` (warn) on drafts — benign design state, no action.

### Artifacts
- PRs opened: **none**.
- Draft tickets created: **none**.
- Direct fixes: 3 gitignored bootstrap-mirror files refreshed (local only); 1 done ticket deleted.
- Pre-existing in-flight (not from this run): PRs #312, #313 (prior Dream drift fixes).
- Child script tasks `dream-p1-validate-drift`, `dream-p5-cleanup-orphan-markers` deleted at run end.
