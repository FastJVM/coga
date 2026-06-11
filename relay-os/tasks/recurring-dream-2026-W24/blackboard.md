The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run plan — Dream 2026-W24 (started 2026-06-11)

Seven phases per the ticket body. Pre-flight survey results:

- Live worker skills present: `bootstrap/dream/tasks/validate-drift`,
  `bootstrap/dream/tasks/cleanup-orphan-markers` (plus workflows
  `dream/validate-drift`, `dream/cleanup-orphan-markers`).
- **Drift found pre-flight:** packaged templates
  (`src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/`)
  ship five Dream skills, but the live copy under
  `relay-os/bootstrap/skills/bootstrap/dream/` is missing three:
  `scan/knowledge-scan`, `scan/contract-audit`, `tasks/skill-update`.
  There is also no `dream/skill-update` workflow under `relay-os/workflows/`.
  → Phases 2/3 will run from the packaged skill copies (same contract);
  Phase 4 cannot launch as specified (no live skill, no workflow) — record
  result and route the drift in Phase 7.
- Open PRs: one (`ticket/establish-marketing-area-fill` — "establish
  marketing area inside relay-os"). No open PR touches task directories or
  Retro markers.
- Done tickets on disk (13 candidates for Phase 5, eligibility to be
  re-checked at phase time): lift-dream-subagent-scan-contract-into-reusable-sk,
  add-bootstrap-skill-for-importing-external-skills,
  recurring-sweep-runs-dream-cleanup-phase-last-and,
  dream-sweeps-done-recurring-period-tickets, add-dev-unit-test-writing-skill,
  slack-webhook-is-env-only-despite-toml-comment-imp, rewrite-slack-messages,
  close-imported-skill-provenance-conflict-and-dream,
  install-init-skills-via-skill-downloader,
  dream-recurring-persist-done-stop-inline-delete,
  session-done-sentinel-leaks-and-agent-stops-respon,
  add-dream-skill-update-maintenance-phase
  (recurring-dream-2026-W24 is this run — excluded).

## Pre-flight repair — diverged main (resolved)

`relay draft` for the Phase 1 child task hit the repo's pre-existing
main/origin-main divergence (14 local ticket-state commits vs 12 remote,
including merged PRs #335/#336). Finished the rebase relay's sync started:
all conflicts were in append-only `log.md` / ticket-state files where the
replayed local commit was an older snapshot of state already on origin
(verified replay side added zero unique lines each time) — kept upstream,
rebased to origin/main + 7 unique commits, pushed.

Side effects handled:
- Autostash apply put the `stream-agent-progress…` bootstrap notes on the
  wrong blackboard (`establish-marketing-area-inside-relay-os` — identical
  baseline blob, real dir renamed to `tasks/auto/` by PR #335). Moved the
  notes to `relay-os/tasks/auto/stream-agent-progress…/blackboard.md`,
  reverted the wrong file.
- Two stale `autostash` entries from Jun 10 failed syncs remain in
  `git stash list`; their content is already in the working tree /
  history. Left untouched — flag as human-needed in run summary.
- Several task `log.md` files contain multi-line `[git] sync failed …`
  noise blocks from yesterday's failed autostash syncs (now committed
  upstream). Noted as a contract-audit input.

## Phase log

### Phase 1 — validate-drift: reported (no-op on repairs)

Child script task `dream-w24-validate-drift` ran `relay validate --json --fix`
and completed `done`. Result: **67 issues — 0 direct-fix, 0 pr-proposal,
67 human-needed**. Breakdown:

- ~50 × `missing-workflow` (warn) on draft tickets — design state, not drift;
  owner picks workflows via `relay ticket <slug>`.
- 12 × `unknown-assignee` (warn) — assignee 'nick' not a known agent type
  (acceptance-criteria, clean-uncommitted-work, identify-blocking-issues,
  init-questions, issue-inbox-slack, relay-crm, relay-discord,
  relay-forces-https, relay-model-selection, relay-project-command,
  relay-uninstall, remote-default-origin).
- 3 × `stuck-in-progress` (warn): recover-recurring-runs-orphaned-when-the-superviso
  (idle 142.7h), session-done-sentinel-leaks-and-agent-stops-respon (122.0h),
  simplify-repl-supervisor-drop-pty-for-sentinel-pol (110.6h).
- 1 × `missing-step` (error): split-context-to-doc-user-accessible-and-editable
  — workflow set but `step:` missing; lifecycle correction is human-only.
- 1 × `unfrozen-workflow` (warn): improve-readme-and-doc.

No safe repairs were needed (no missing blackboard/log files). Full detail in
`relay-os/tasks/dream-w24-validate-drift/blackboard.md`.

### Phase 2 — knowledge scan: reported

Subagent ran the `bootstrap/dream/scan/knowledge-scan` contract (packaged copy
— live copy missing, see pre-flight drift note). 11 findings returned: 4
extract, 1 stale, 6 gap. Written under `## Findings` below.

## Findings

### Knowledge-scan and contract-audit skills now defined but not materialized
- class: stale
- target: relay-os/bootstrap/skills/bootstrap/dream/
- area: relay/architecture

The Dream recurring task references `bootstrap/dream/scan/knowledge-scan` and
`bootstrap/dream/scan/contract-audit` skills in Phases 2–3, and the packaged
template at `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/dream/scan/`
contains both. The live copy under `relay-os/bootstrap/skills/bootstrap/dream/`
is missing them, so this run fell back to the packaged copies. The
packaged-only vs both-copies distinction is undocumented, and fresh
`relay init` does not materialize these newer bundled skills without
`relay init --update`.

### Skill-update phase not wired and no workflow defined
- class: gap
- target: bootstrap/dream/tasks/skill-update + relay-os/workflows/dream/
- area: relay/architecture, relay/codebase

Phase 4 (skill-update) is in the Dream contract and has a packaged worker
skill, but there is no live copy in `relay-os/bootstrap/skills/` and no
workflow at `relay-os/workflows/dream/skill-update.md`, so Phase 4 cannot
launch as specified. Routed in Phase 7.

### Session-done sentinel and agent silence bugs unresolved
- class: gap
- target: session-done-sentinel-leaks-and-agent-stops-respon
- area: relay/principles

Ticket is `in_progress` (step: review), idle 122h, documenting two coupled
bugs: the session-done teardown marker leaks to visible output without
tearing down the session, and the agent goes silent on a present human after
`done` — violating the interactive-mode contract. Needs unblocking or
escalation (status note; also surfaced by Phase 1 stuck-in-progress).

### Bootstrap skill authoring needs clarified in contexts
- class: extract
- target: relay/codebase
- area: relay/codebase

`add-bootstrap-skill-for-importing-external-skills` and
`add-dream-skill-update-maintenance-phase` both re-discovered: bundled battery
files must be authored in `src/relay/resources/templates/relay-os/bootstrap/`
(live `relay-os/bootstrap/` is gitignored) and **must be force-added with
`git add -f`**. Add an explicit checklist to `relay/codebase` under
"Authoring bundled batteries".

### Recurring lifecycle redesign stages 1-2 still paused
- class: gap
- target: dream-recurring-persist-done-stop-inline-delete
- area: relay/current-direction

Stages 1–2 of the recurring lifecycle redesign are paused at step 1 while
stage 3 (Dream deleting done recurring tickets) landed. Two-ticket temporal
coupling makes status unclear to agents; either unblock stages 1–2 or split
into independent stages. (Status note for owner.)

### Managed-skill installation design resolved but not fully scoped
- class: extract
- target: relay/architecture
- area: relay/architecture

`install-init-skills-via-skill-downloader` (done, PR #334) resolved the
two-tier model: Tier 1 preinstalled package-backed skills in
`bootstrap/skills/`; Tier 2 optional installer-managed skills in
`relay-os/skills/`. Centralize this in `relay/architecture` under "Bundled
batteries".

### Slack webhook and message conventions landed
- class: extract
- target: relay/sync
- area: relay/codebase

`slack-webhook-is-env-only-despite-toml-comment-imp` and
`rewrite-slack-messages` (done, PRs #330/#321) established: webhook configured
via `[slack].webhook = "env:SLACK_WEBHOOK_URL"`; uniform message format
(title, `→` transitions, parenthetical asides, Slack link syntax for PRs).
`relay/sync` documents webhook config but not the message format convention —
add a `## Message format convention` section.

### Imported skill provenance and conflict handling complete
- class: extract
- target: relay/codebase
- area: relay/codebase

`close-imported-skill-provenance-conflict-and-dream` (done, PR #329):
URL-backed skills refuse overwrite when locally adapted (unless `--force`),
preserve `local_adaptation_notes` across clean updates, report `conflict`
when both locally adapted and upstream-changed. Document
`.relay-source.json` metadata, the dirty-overwrite guard, `--force`, and the
conflict status under a "Skill provenance and adaptation" subsection of
`relay/codebase`.

### Multi-tool orchestration pattern not documented
- class: gap
- target: relay/patterns
- area: relay/architecture

The Dream parent-orchestrates-child-script-tasks pattern (child `mode: script`
tasks + worker skills + `## Dream Skill:` blackboard sections + parent
aggregation) is the canonical multi-step housekeeping shape but is not
documented as a Relay pattern. Candidate for a `relay/patterns` addition.

### Dream contract scope needs explicit statement on when phases skip
- class: extract
- target: relay-os/recurring/dream/ticket.md
- area: relay/codebase

The "phase failing does not permit a replacement" rule is exercised this run
(Phase 4 blocked, later phases continue). Make the phase dependency structure
explicit in the Dream template body.

### Slack opt-out not mentioned in all workflows
- class: gap
- target: relay/sync
- area: relay/sync

`relay/sync` documents `[slack].enabled = false` opt-out but not that posts
degrade silently when disabled/misconfigured. Add an explicit degradation
note.

### Stale materialized bootstrap tree (root cause for several drifts)
- class: drift
- target: relay-os/bootstrap/ (gitignored, materialized)
- truth: copy divergence

Contract-audit findings verified and root-caused by the parent run: the
materialized `relay-os/bootstrap/` tree is stale relative to the installed
package. Missing: `bootstrap/dream/scan/knowledge-scan`,
`bootstrap/dream/scan/contract-audit`, `bootstrap/dream/tasks/skill-update`.
Stale content: `bootstrap/contexts/relay/cli/SKILL.md` and
`bootstrap/contexts/relay/architecture/SKILL.md` (315 vs 333 lines packaged).
The live tracked `relay-os/contexts/relay/architecture/SKILL.md` is byte-identical
to the packaged copy, and `contexts/relay/architecture` is on init's
OBSOLETE_PATHS consolidation list, so `relay init --update` is the designed,
lossless refresh — but it also prunes tracked consolidated paths (a commit on
main), so Dream does not run it autonomously. **Routed: human-needed —
recommend `relay init --update`.**

### Missing dream/skill-update workflow (PR-able)
- class: drift
- target: relay-os/workflows/dream/skill-update.md (missing)
- truth: missing artifact

The Dream template Phase 4 requires a child script task whose workflow step
references `bootstrap/dream/tasks/skill-update`; the sibling workflows
`dream/validate-drift.md` and `dream/cleanup-orphan-markers.md` exist (tracked,
live-only — workflows have no packaged counterpart) but the skill-update one
was never authored when `add-dream-skill-update-maintenance-phase` shipped.
**Routed: proposal PR adding the workflow file, mirroring the siblings.**

### Contract-audit false positive (recorded for transparency)

The audit flagged `contexts/relay/architecture` referencing `relay/cli` which
exists only under `bootstrap/contexts/`. Verified against `src/relay/paths.py`:
context refs resolve local-first then fall back to bootstrap, so cross-tree
references are by design. Dropped.

### Phase 3 — contract audit: reported

Subagent ran the `bootstrap/dream/scan/contract-audit` contract (packaged
copy). 5 raw findings; after parent verification: 2 durable drift findings
(stale materialized bootstrap tree — collapses 4 raw findings; missing
dream/skill-update workflow) + 1 false positive dropped. Recorded above under
`## Findings`.

### Phase 4 — skill-update: human-needed (blocked, no replacement run)

Cannot launch as specified: the worker skill
`bootstrap/dream/tasks/skill-update` is absent from the materialized
`relay-os/bootstrap/` tree (refreshes via `relay init --update`, human-needed)
AND `relay-os/workflows/dream/skill-update.md` does not exist (tracked file —
fix goes through the Phase 7 proposal PR). Per the dispatch contract, the
phase result is recorded and no replacement maintenance was invented. Note:
imported skills under `relay-os/skills/` (browser/*, google-agents-cli-*,
anthropic/*) were therefore NOT update-checked this run.

### Phase 5 — retro/done-ticket: pr-opened + direct-fixed

One subagent run over all 12 eligible done tickets (frontmatter-verified;
open PR #338 only touches the draft `establish-marketing-area-inside-relay-os`,
no overlap). Result:

**4 knowledge PRs** (each: 1 source ticket, 1 logical knowledge file +
packaged mirror where one exists, `## Retro` marker + source deletion in-PR):
- PR #339 — relay/sync: uniform Slack message format conventions
  (from rewrite-slack-messages).
- PR #340 — relay/cli (packaged copy): imported-skill adaptation guard,
  `--force`, `conflict` status (from close-imported-skill-provenance-conflict-and-dream).
- PR #341 — relay/architecture: Dream's prompt-only scan skills
  (from lift-dream-subagent-scan-contract-into-reusable-sk).
- PR #342 — relay/current-direction: eval/ticket-diagnostic keep-decision
  (from maybe-remove-ticket-diagnostic).

**8 direct-deleted** (no durable knowledge; `Ticket: <slug> — deleted` commits
on main, pushed): add-bootstrap-skill-for-importing-external-skills,
add-dev-unit-test-writing-skill, add-dream-skill-update-maintenance-phase,
dream-sweeps-done-recurring-period-tickets, dream-w24-validate-drift,
install-init-skills-via-skill-downloader,
recurring-sweep-runs-dream-cleanup-phase-last-and,
slack-webhook-is-env-only-despite-toml-comment-imp.

Phase 2's four extract suggestions: three verified already-covered on disk
(battery authoring gotcha, two-tier skill model, webhook env contract) — the
source tickets' own PRs had landed them; one (Slack message format) became
PR #339. Slack FYIs posted per PR. The 4 knowledge-PR ticket dirs remain on
disk until their PRs merge (by design).

### Phase 6 — cleanup-orphan-markers: no-op

Child script task `dream-w24-cleanup-orphan-markers` ran and found no
cleanup-eligible processed done tickets with surviving directories (expected:
Phase 5 deletes in-PR or direct-deletes).

### Phase 7 — disposition: pr-opened + proposed

- drift "missing dream/skill-update workflow" → **PR #343** (adds
  `relay-os/workflows/dream/skill-update.md`, mirrors siblings; pr-required).
- drift "stale materialized bootstrap tree" → **human-needed**: run
  `relay init --update` (it also prunes consolidated tracked paths, e.g.
  `contexts/relay/architecture` — a main commit — so Dream did not run it).
- gap "orchestration pattern undocumented" → **draft ticket**
  `document-parent-orchestrates-child-script-tasks-pa` (code/with-review),
  description carries the full proposal.
- gap "slack silent degradation note for relay/sync" → overlaps PR #339
  (edits relay/sync); per contract, noted as overlap and deferred to that
  PR's review rather than opening a conflicting PR.
- gap "session-done sentinel bugs" and gap "recurring lifecycle stages 1–2
  paused" → already tracked by their own on-disk tickets
  (session-done-sentinel-leaks-and-agent-stops-respon, in_progress/stuck;
  dream-recurring-persist-done-stop-inline-delete, paused). No new artifact;
  surfaced in human-needed below.
- extract "Dream phase-dependency note" → dropped as already covered: the
  template's "a phase failing does not permit a replacement" rule already
  encodes it and was exercised cleanly this run.

## Dream Run Summary

Generated: 2026-06-11T18:54:14+00:00 (run started ~17:45 UTC)

| Phase | Result |
| --- | --- |
| 1 validate-drift | reported (67 issues: 0 direct-fix, 0 pr-proposal, 67 human-needed) |
| 2 knowledge scan | reported (11 findings: 4 extract, 1 stale, 6 gap) |
| 3 contract audit | reported (2 drifts after verification; 1 false positive dropped) |
| 4 skill-update | human-needed (blocked: worker skill not materialized + workflow missing; no replacement run) |
| 5 retro/done-ticket | pr-opened ×4 + direct-fixed ×8 (12/12 eligible done tickets processed) |
| 6 cleanup-orphan-markers | no-op |
| 7 disposition | pr-opened ×1 + proposed ×1 draft ticket |

Artifacts:
- Knowledge PRs: [#339](https://github.com/FastJVM/relay/pull/339) relay/sync
  Slack message format · [#340](https://github.com/FastJVM/relay/pull/340)
  relay/cli skill adaptation guard/conflict ·
  [#341](https://github.com/FastJVM/relay/pull/341) relay/architecture Dream
  scan skills · [#342](https://github.com/FastJVM/relay/pull/342)
  relay/current-direction ticket-diagnostic keep-decision.
- Proposal PR: [#343](https://github.com/FastJVM/relay/pull/343) add
  `dream/skill-update` workflow (unblocks Phase 4 next run).
- Draft ticket: `document-parent-orchestrates-child-script-tasks-pa`.
- Direct-deleted (8, no durable knowledge, commits on main): see Phase 5 log.

Human-needed / review gates:
1. Review+merge PRs #339–#343 (Dream never auto-merges). #339 also carries
   the deferred relay/sync silent-degradation note as a review comment-level
   overlap.
2. Run `relay init --update` to refresh the stale materialized
   `relay-os/bootstrap/` tree (missing Dream scan/skill-update workers, stale
   cli/architecture bootstrap contexts). Note it prunes consolidated tracked
   paths — review its diff before committing.
3. Imported skills were NOT update-checked this run (Phase 4 blocked).
4. validate-drift: 12 unknown-assignee 'nick' tickets, 3 stuck-in-progress
   (recover-recurring-runs… 142.7h, session-done-sentinel… 122h,
   simplify-repl-supervisor… 110.6h), 1 missing-step error
   (split-context-to-doc-user-accessible-and-editable), ~50 workflow-less
   drafts (design state).
5. Pre-flight: resolved the diverged main (rebased onto origin/main, pushed);
   two stale Jun-10 `autostash` entries remain in `git stash list` — content
   superseded, safe to drop after a human glance.
