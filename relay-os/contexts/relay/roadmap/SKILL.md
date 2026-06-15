---
name: relay/roadmap
description: The sequenced execution plan for relay — what to build next, grouped into dependency-ordered waves, with the critical path called out. Read this to know where a ticket sits and what gates it. Sequencing only; for the "why" behind decisions see relay/current-direction.
---

# Relay — roadmap

Last updated: 2026-06-15.

This is the **execution order**, not the full backlog. Tickets are grouped into
dependency-ordered waves; within a wave, order is roughly by leverage. A
ticket's slug is given so you can `relay show <slug>`. Status tags
(`[in_progress]`, `[active]`, `[new]`) reflect the last update — verify with
`relay status` before acting.

This context is **sequencing only**. The reasoning behind individual decisions
lives in `relay/current-direction`; the principles a change must respect live
in `relay/principles`.

## Critical path (the short version)

1. Finish the in-flight work (Wave 0) so the board is legible.
2. Ship installability (Wave 1) — a stranger still can't `pipx install` Relay;
   that gates the launch.
3. `auto/stream-agent-progress` is the **single highest-leverage unlock** — it
   re-enables `mode: auto` and thereby the entire nightly-drain vision (Wave 2).
4. The single-file format rewrite (Wave 3) is high-blast-radius — do it when the
   board is calm, after Wave 0's file-model work settles.

## Wave 0 — Finish in-flight + clear the board

Land what's already moving before opening new fronts.

- `collapse-recurring-period-tasks-to-one-dir-per-tem` [in_progress] — one dir
  per template under `tasks/recurring/`, period in the blackboard.
- `resolve-missing-workflow-validator-vs-concept-capt` [in_progress] — validator
  coherence (surfaced as a Dream gap).
- `session-done-sentinel-leaks-and-agent-stops-respon` [in_progress] — teardown
  bug; breaks unattended runs.
- `automation-triage` + `wire-autonomy-triage-into-impl-ready-workflows`
  [in_progress] — autonomy tiers and authoring-time classification.
- `cli-document` [in_progress] — onboarding doc.
- **Dedup pass** — consolidate duplicate drafts so the board is legible before
  planning later waves. Tracked by the `dedup-duplicate-draft-tickets` ticket.
  Run it deliberately; it is destructive (`relay delete`) and propose-then-
  confirm.

## Wave 1 — Make Relay installable by outsiders (the launch gate)

Everything here blocks "a stranger can install and run it." Repo-public is the
keystone for the marketing/install half.

1. `relay-forces-https` [active] + `remote-default-origin` [active] — respect
   SSH users and non-`origin` remotes; real users have varied git setups.
2. `relay-cli-shipping` [active] — `relay init` must ship `workflows/` +
   `skills/code`, or a fresh repo can't run the core process out of the box.
3. `one-line-install` [active] — the `pipx install` story.
4. `relay-uninstall` [active] — easy removal lowers the trial barrier.
5. `marketing/relay-discord` [active] → make the repo public (prerequisite) →
   `marketing/launch-relay-product-launch-comms` [active].

## Wave 2 — Autonomy + token-utilization track

Strict dependency chain; build bottom-up. This is the big new bet: use spare
overnight token budget to run flagged-ready tickets unattended.

1. `track-usage-of-llm` [active] — foundational per-session usage primitive;
   everything below consumes it.
2. `represent-autonomy-tier-in-ticket-mode-field` — the "ready for execution"
   flag.
3. `auto/stream-agent-progress-in-auto-mode-and-recurring-l` — **hard blocker**;
   re-enables `mode: auto` (currently disabled because it buffers stdout).
4. `async-park-and-continue-on-block` [new] — a blocked ticket parks cleanly and
   the sweep keeps going instead of stalling the night.
5. `drain-pending-auto-tickets-with-leftover-session-b` — the budget-aware drain
   loop.
6. `nightly-auto-drain-run-for-ready-tickets` [new] — assembles 1–5 into the
   scheduled overnight run (wires `relay-os/scripts/cron.sh`; Relay does not
   manage cron itself).
7. Payoffs: `autoroute-agent-based-on-remaining-usage`, `model-selector`.

## Wave 3 — Single-file task format (high blast radius)

- `single-file-task-format-section-aware-compose-filt` [new] — merge the
  three-file task layout into one file + a section-aware compose filter so only
  working sections load (audit history excluded). Sequence **after** Wave 0's
  recurring/validator work, since it rewrites the same file-model. Design step
  first; likely splits into format+migration → compose filter → writer
  migration → docs rewrite.

## Wave 4 — PM / planning features (product depth)

- `relay-project-command` [active] — interview → ordered draft tickets (seeds
  from a vision doc too).
- `acceptance-criteria` [active] + `identify-blocking-issues` [active] —
  definition-of-done + cross-ticket dependencies.
- `issue-inbox-slack` [active] — actionable Slack inbox; pairs with
  `async-park-and-continue-on-block`.

## Wave 5 — Robustness & hygiene (mostly polish, lower urgency)

The dedup half moved up into Wave 0. What remains is genuine polish:

- Security / PII / per-skill secrets (`manage-security-and-pii`,
  `pass-secrets-to-skills-with-per-skill-scope`,
  `fail-loud-when-an-env-indirected-secret-is-missing`).
- Container/VM isolation (`launch-tasks-in-container-or-vm`).
- The `document-*` knowledge-base batch — do this **after** Wave 3, or you will
  clean up docs you are about to rewrite.

Dev-loop git hygiene (`use-worktree-when-starting-a-dev-task`,
`clean-uncommitted-work`, branch cleanup) is a dogfooding investment that can be
pulled forward to run alongside Wave 1 — it speeds every later ticket because we
build Relay with Relay.

## What this context does NOT cover

- The reasoning behind decisions / what was deferred and why — see
  `relay/current-direction`.
- The principles a change must not violate — see `relay/principles`.
- The full backlog — see `relay status`.
