# Dream run — period 2026-W25

Full run (all 6 phases), interactive, confirmed by nick on 2026-06-17.
Remote: FastJVM/relay (PRs possible).

## Plan / progress

- [x] Phase 1 — validate-drift (child script task `dream-w25-validate-drift`) — **reported**: 18 issues, all `human-needed` (6 `missing-step` errors, 12 `unknown-assignee` warns). 0 auto-fixable. Routes to Phase 6 human-needed notes. Child task done; direct-delete in Phase 4.
- [x] Phase 2 — knowledge scan (subagent) — **reported**: 3 extract (E1/E2/E3), 1 stale (S1), 2 gap (G1/G2). See ## Findings.
- [x] Phase 3 — contract audit (subagent) — **reported**: 3 drift (D1/D2/D3). See ## Findings.
- [x] Phase 4 — retro/done-ticket (25 eligible) — **2 knowledge PRs + 22 direct-deletes**; verified all 25 reconciled, recurring templates survived, main==origin/main. See ## Phase 4 result.
- [x] Phase 5 — cleanup-orphan-markers (child script task `dream-w25-cleanup-orphan-markers`) — **no-op** (no orphan markers on disk). Child left on disk for next run to sweep.
- [x] Phase 6 — disposition + run summary — **proposed**: 3 proposal PRs (#390 S1, #392 D1+D2, #393 D3) + 2 gap draft tickets (G1/G2). See ## Dream Run Summary.

Eligible done tickets at run start (24): supervisor-liveness-watchdog-for-agents-that-never,
session-done-sentinel-leaks-and-agent-stops-respon, resolve-missing-workflow-validator-vs-concept-capt,
dream-w24-cleanup-orphan-markers, add-imported-skill-update-check, recurring/autoclose-merged,
recurring/digest, recurring/skill-update, collapse-recurring-period-tasks-to-one-dir-per-tem,
post-slack-notification-on-mode-script-failures, retire-in-band-done-mrker-not-needed,
marketing/validate-relay-build-onboarding, marketing/relay-crm,
detect-recurring-runs-that-mark-done-without-advan, fix-recurring-templates-not-instantiated,
recover-recurring-runs-orphaned-when-the-superviso, authentication-system,
slack-post-ignores-http-response-so-bad-webhook-fa, restructure-slack-message,
autoclose-merged-recurring-task, rename-slack-to-a-notification-system-with-pluggab,
dedup-duplicate-draft-tickets, establish-marketing-area-inside-relay-os, skip-permissions-option

(Eligibility re-checked per ticket in Phase 4 against on-disk dir + open-PR state.)

Open-PR gate (checked Phase 3 prep): 4 open PRs (#384 #385 #386 #387). Only #384
touches a task dir (`marketing/relay-build-onboarding-flow` — NOT in done set).
→ All 24 eligible done tickets pass the open-PR gate. Also note: #385
`relay/skill-update` is the skill-update PR; #387 ships bootstrap workflows/skills
into the packaged template tree (relevant to Phase 3 copy-divergence findings —
may already be fixing live/packaged drift).

## Findings

### Phase 2 — knowledge scan (corpus overall well-maintained; most done tickets already extracted)

**EXTRACT (durable knowledge to capture before Phase 4 deletes the source):**

- **E1 — Identity/secrets boundary model** · source `authentication-system` · target
  `relay/architecture` (or new `relay/auth` context). Four-boundary model not yet written
  anywhere: (1) Relay never owns human identity — inspects git/ssh-agent/gh, fails with
  setup hints, never stores a PAT; (2) repo/install identity may carry an anonymous
  local-only telemetry ID; (3) capability = ticket-level `secrets:` resolved via
  `env:`/`op://`/literals, fail-loud; (4) v1 ≤1 hosted crossing (telemetry sink), no
  account/login/token/sync backend. `secrets:` field + `op://` prefix-dispatch (no provider
  registry; prefix dispatch in `config.py` is the seam) are durable design rules.
  NOTE: impl child tickets (`1password-…`, `github-auth-preflight-…`) are still draft/open —
  the *contract* is the durable part, not impl detail.

- **E2 — Packaged-template editing gotchas** · sources `add-imported-skill-update-check` +
  `resolve-missing-workflow-validator-vs-concept-capt` · target `relay/codebase`.
  (a) edits to already-tracked files under packaged `bootstrap/` template tree need
  `git add -f` (template `.gitignore` silently drops content edits; `git mv` stages rename
  but later content edits vanish). (b) a new required workflow/skill must be added to
  `VENDORED_WORKFLOW_TEMPLATES` / `VENDORED_SKILL_TEMPLATES` + the recurring-refresh list or
  `relay init --update` won't deliver it. Both bit peer-review rounds.

- **E3 — `relay build` onboarding design verdict** · source
  `marketing/validate-relay-build-onboarding` · target marketing onboarding context (or fold
  into the still-open `marketing/relay-build-onboarding-flow` ticket). Validated design:
  one scripted Q ("What do you want to build?") + agent-led dynamic follow-ups + code-reading
  scan reconciling code-vs-docs (grep before ticketing) → short agreed spec → ~5-ticket batch
  (3–6) with exactly one launchable anchor. Also durable: CLAUDE.md de-risks execution;
  offline/pre-Slack safety load-bearing (`$SLACK_WEBHOOK_URL` posts to real channel without
  `[notification.slack] enabled = false`). Consuming design ticket is OPEN → fold there, don't lose.

- **Already extracted → no new knowledge, direct-delete in Phase 4:**
  `collapse-recurring-period-tasks-to-one-dir-per-tem`, `recover-recurring-runs-orphaned-when-the-superviso`,
  `detect-recurring-runs-that-mark-done-without-advan`, `fix-recurring-templates-not-instantiated`,
  `autoclose-merged-recurring-task`, `restructure-slack-message`,
  `rename-slack-to-a-notification-system-with-pluggab`, `slack-post-ignores-http-response-so-bad-webhook-fa`,
  `post-slack-notification-on-mode-script-failures`, `retire-in-band-done-mrker-not-needed`,
  `session-done-sentinel-leaks-and-agent-stops-respon`, `skip-permissions-option`,
  `supervisor-liveness-watchdog-for-agents-that-never`, `marketing/relay-crm`,
  `establish-marketing-area-inside-relay-os`, `dedup-duplicate-draft-tickets`,
  `resolve-missing-workflow-validator-vs-concept-capt` (knowledge part = E2; ticket itself direct-delete after E2 PR).
  Plus the 3 `recurring/*` period tasks + `dream-w24-cleanup-orphan-markers` (nothing durable).

**STALE:**

- **S1 — current-direction Slack queue outdated** · `relay/contexts/relay/current-direction/SKILL.md`
  `## Open ticket queue (Slack / notifications)` (~L1295–1311). Lists `rename-slack-…` as active +
  five "open Slack drafts"; reality: rename + 2 bug tickets now done, two drafts deleted, only
  `use-slack-as-a-sync-channel-for-tickets` survives (parked v2). Slack-notification work is closed.
  → Phase 6 stale-fix PR: delete/rewrite section to note the rename shipped, only v2 inbound-sync remains.

**GAP:**

- **G1 — automerge `pr:` line format is tribal knowledge** · target `dev/code` context note.
  `relay automerge` only recognizes a *plain* `pr: <url>` line under `## Dev`, not a `- pr:` bullet.
  Rediscovered across ≥6 done tickets. → Phase 6 gap draft ticket (low effort, high recurrence).
- **G2 — cross-machine/sandbox dev-loop friction has no context** · target `relay/codebase` block.
  Repeatedly re-discovered: 3.9 vs 3.11+ venv (`PYTHONPATH=… python3.12 -m pytest`); `codex review`
  needs unsandboxed; `relay validate`/`draft` need writable `.git` (index.lock); repo-wide validate
  shows unrelated drift so `--task <slug>` is the meaningful check. → Phase 6 gap draft ticket.

### Phase 4 result (verified independently against repo)

- **Knowledge PRs (deletions baked in):**
  - **#388** "Architecture context: Relay's four identity/capability boundaries" — extracts E1 into
    `relay/architecture` (+ packaged sync, `git add -f`); deletes source `authentication-system`.
    https://github.com/FastJVM/relay/pull/388
  - **#389** "Codebase context: packaged bootstrap template editing + vendored-refresh delivery gotchas" —
    extracts E2 into `relay/codebase` (repo-local, no sync); deletes sources
    `add-imported-skill-update-check` + `resolve-missing-workflow-validator-vs-concept-capt`.
    https://github.com/FastJVM/relay/pull/389
  - Each knowledge ticket got one `## Retro` marker (status: processed, result: knowledge-pr) inside its PR.
- **E3 dropped → direct-deleted** `marketing/validate-relay-build-onboarding`: the build-onboarding *design
  verdict* is feature-specific and a poor fit for the `marketing/positioning` context (position/voice/proof);
  open PR #384 is actively building that feature, so the verdict belongs in that in-flight ticket. Conservative-bar
  call; recorded here so it's not lost: see Phase 2 E3 for the verdict content.
- **22 direct-deletes on main** (verified gone): supervisor-liveness…, session-done-sentinel…, dream-w24-cleanup-orphan-markers,
  collapse-recurring…, post-slack-notification…, retire-in-band-done-mrker…, marketing/validate-relay-build-onboarding,
  marketing/relay-crm, detect-recurring…, fix-recurring-templates…, recover-recurring…, slack-post-ignores…,
  restructure-slack-message, autoclose-merged-recurring-task, rename-slack…, dedup-duplicate-draft-tickets,
  establish-marketing-area…, skip-permissions-option, dream-w25-validate-drift, + recurring/{autoclose-merged,digest,skill-update}.
- **Reconciliation:** 25/25 (3 in PRs still on main until merge + 22 gone). `relay-os/recurring/*` templates intact
  (last_serviced_period preserved). main == origin/main.

### ⚠ Concurrent external activity observed (not a Dream action)

During Phases 1–4, an external process (committer nicktoper) progressed unrelated tasks on main:
`first-run-works-without-slack-configured` (active→in_progress→step 3 implement) and `relay-cli-shipping`
(step 4→step 5). These interleaved with the retro delete commits but serialized cleanly (linear history, no
conflict, no overlap with Dream's targets). Relevant to the known interactive-recurring-sweep hazard. Phase 6
PRs branch off freshly-fetched origin/main to stay current.

### Phase 3 — contract audit (3 drift findings; canonical contexts/docs otherwise clean)

- **D1 — README `✨` Slack-on-draft claim is false** · `README.md:222` (+ stale docstrings/comment
  `src/relay/commands/create.py:3,41,72`) · code reality. `create_draft()` performs NO Slack post —
  just `typer.echo` + git sync. → Phase 6 drift PR: drop the `✨`/Slack claim from README + create.py
  docstrings, OR wire a real create notification (recommend: drop the claim — activation is silent by design too).
- **D2 — README `🚀` Slack-on-active claim contradicts code** · `README.md:275` · code reality.
  `mark_active()` (`src/relay/mark.py:227`) documents activation is *intentionally Slack-silent*. → Phase 6
  drift PR: remove the "Posts 🚀." note. (Same theme as D1 — bundle into one README Slack-claims PR.)
- **D3 — orphan `dream/skill-update` workflow references a deleted skill** · `relay-os/workflows/dream/skill-update.md`
  · referenced artifact. Names `bootstrap/dream/tasks/skill-update`, which no longer exists (active path
  moved to `bootstrap/skill-update` + `workflows/skill-update/run.md`, used correctly by
  `recurring/skill-update`). Dead-but-tracked; `relay launch`ing it would fail. → Phase 6 drift PR: delete
  the workflow file (+ orphan packaged `.pyc`). NOTE: this workflow is git-tracked (unlike bootstrap mirror).
- **Clean:** all canonical `relay/*` contexts, CLAUDE/AGENTS/docs, bootstrap skills, recurring templates verified
  against code. Copy-divergence only in the gitignored `relay-os/bootstrap/**` mirror (packaged copy is source of
  truth, current) + runtime state in `recurring/*` — neither is tracked-contract drift.

### Scoping map for mutating phases (verified via git ls-files / check-ignore)

- TRACKED editable contexts: `relay-os/contexts/**` (17 files) incl. `relay/architecture,codebase,current-direction,…`.
- TRACKED editable skills: `relay-os/skills/**` (64 files). TRACKED workflows: `relay-os/workflows/**`.
- GITIGNORED mirror (NEVER edit, NEVER PR): `relay-os/bootstrap/**` (0 tracked). It's regenerated by `relay init --update`.
- Packaged source-of-truth: `src/relay/resources/templates/relay-os/**` (tracked).
- **Packaged-sync required ONLY for contexts that have a packaged counterpart.** Checked:
  - `relay/architecture` → HAS packaged copy (`…/bootstrap/contexts/relay/architecture/SKILL.md`) → **edit both**; packaged-tree edits may need `git add -f` (E2 gotcha).
  - `relay/codebase`, `relay/current-direction`, `marketing/positioning` → repo-local, NO packaged copy → no sync.

## Dream Run Summary

Generated: 2026-06-18T04:37:54Z · period 2026-W25 · interactive, full run (nick).

| Phase | Result | Detail |
| --- | --- | --- |
| 1 validate-drift | reported | 18 issues, all `human-needed` (6 missing-step errors, 12 unknown-assignee warns); 0 auto-fixable |
| 2 knowledge scan | reported | 3 extract, 1 stale, 2 gap |
| 3 contract audit | reported | 3 drift |
| 4 retro/done-ticket | pr-opened + direct-fixed | 2 knowledge PRs; 22 done tickets direct-deleted; 25/25 reconciled |
| 5 cleanup-orphan-markers | no-op | no orphan markers on disk |
| 6 disposition | proposed | 3 proposal PRs + 2 gap draft tickets |

**Findings → homes (11 total):**
- 3 extract: E1 auth/secrets boundaries → PR #388 (`relay/architecture` + packaged sync); E2 packaged-template gotchas → PR #389 (`relay/codebase`); E3 relay-build design verdict → dropped to direct-delete (deferred to in-flight feature PR #384; verdict preserved in this blackboard's Phase 2 E3).
- 1 stale: S1 current-direction Slack queue → PR #390.
- 3 drift: D1+D2 false README/create.py Slack claims (✨/🚀) → PR #392; D3 orphan `dream/skill-update` workflow → PR #393.
- 2 gap: G1 automerge bare `pr:` format → draft `document-the-automerge-bare-pr-line-format-require`; G2 sandbox dev-loop friction → draft `document-cross-machine-sandbox-dev-loop-friction-i`.
- 2 already-covered classes (bulk of 24 done tickets) → swept by Phase 4 direct-delete.

**PRs opened (5, all pr-required — Dream never auto-merges):**
- #388 https://github.com/FastJVM/relay/pull/388 — Architecture context: four identity/capability boundaries (deletes `authentication-system`)
- #389 https://github.com/FastJVM/relay/pull/389 — Codebase context: packaged-template editing + vendored-refresh gotchas (deletes 2 tickets)
- #390 https://github.com/FastJVM/relay/pull/390 — Fix stale Slack-notification queue in current-direction
- #392 https://github.com/FastJVM/relay/pull/392 — Fix false Slack claims for draft/active in docs
- #393 https://github.com/FastJVM/relay/pull/393 — Remove orphan dream/skill-update workflow

**Draft tickets created (2):** `document-the-automerge-bare-pr-line-format-require`, `document-cross-machine-sandbox-dev-loop-friction-i` (both `code/with-review`).

**Human-needed / review gates:**
- 18 validate issues need an owner: 6 `missing-step` errors (`drain-pending-auto-tickets…`, `improve-readme-and-doc`, `marketing/auto-width-200`, `v2/autotrigger-ticket-type`, `v2/retire-standalone-relay-automerge…`, `v2/split-context-to-doc…`, `v2/use-worktree-when-starting…`) — relaunch/rewind/hand-edit step; 12 `unknown-assignee` warns (assignee `nick` not a known agent/role) across marketing/* + v2/* + a few root tickets. Lifecycle/routing — Dream cannot fix.
- All 5 PRs await human review/merge.
- E3 design verdict intentionally not extracted (deferred to PR #384's in-flight design).

**Note:** concurrent external commits (first-run-works, relay-cli-shipping, marketing/relay-init-captures-name) landed on main during the run; serialized cleanly, no conflict with Dream's targets. main == origin/main at close.
