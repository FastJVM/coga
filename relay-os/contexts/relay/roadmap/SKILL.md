---
name: relay/roadmap
description: The sequenced execution plan for relay — the v1 launch milestone and everything deferred to v2, with the critical path called out. Read this to know whether a ticket is in the v1 cut or deferred, and what gates it. Sequencing only; for the "why" behind decisions see relay/current-direction.
---

# Relay — roadmap

Last updated: 2026-06-16.

The backlog is split into two milestones plus one orthogonal track:

- **v1** — the launch cut: a stranger can install Relay, run the core loop,
  trust the first run, and let it work unattended. The 24 tickets below.
- **v2** — everything else. Physically parked under `relay-os/tasks/v2/`, so a
  v2 ticket's ref is `v2/<slug>`. Not scheduled against the launch; pulled up
  into v1 only by explicit decision.
- **marketing/** — orthogonal. The `marketing/*` tickets (launch comms, Discord,
  uninstall, onboarding, demos…) run on their own axis and are **not** part of
  the v1/v2 engineering split. They are neither listed here nor parked in v2.

Status tags reflect the last update — verify with `relay status` before acting.
This context is **sequencing only**; the reasoning behind decisions lives in
`relay/current-direction`, and the principles a change must respect live in
`relay/principles`.

## Critical path (the short version)

1. Land the in-flight autonomy-triage work so the board is legible.
2. Ship installability — a stranger still can't `pipx install` Relay; that gates
   the launch.
3. `auto/stream-agent-progress` is the **single highest-leverage unlock** — it
   re-enables `mode: auto` and thereby the entire unattended-drain vision. The
   whole autonomy chain in v1 sits behind it.
4. The single-file task-format rewrite is high-blast-radius; sequence it when
   the board is calm.

## v1 — the launch cut (26 tickets)

### In-flight (1)

- `wire-autonomy-triage-into-impl-ready-workflows` [active] — autonomy tiers +
  authoring-time classification; the last in-flight straggler.

### Installability — the launch gate (7)

A stranger must be able to install and run Relay out of the box.

- `relay-forces-https` [active] + `remote-default-origin` [active] — respect SSH
  users and non-`origin` remotes.
- `relay-cli-shipping` [active] — `relay init` must ship `workflows/` +
  `skills/code`, plus the recurring templates, or a fresh repo can't run the
  core process.
- `one-line-install` [active] — the `pipx install` story.
- `register-a-real-domain-for-relay` [draft] — a real domain for the install
  one-liner and README links; blocks final launch copy.
- `improve-readme-and-doc` [draft] — a README a stranger can land on and run
  from.
- `anonymous-install-telemetry-opt-out-no-pii` [draft] — opt-out, no-PII install
  count so we can tell if launch landed. Carries a principle tension (phones
  home); see the ticket.

### Auth (1)

- `authentication-system` [draft] — design-first umbrella over four scopes:
  telemetry/install identity, hosted-backend account+token, git/GitHub
  credential handling, and per-skill secrets (the last folds in the v2 tickets
  `v2/pass-secrets-to-skills-with-per-skill-scope` + the v1
  `fail-loud-when-an-env-indirected-secret-is-missing`). Expect it to split
  at the design step.

### Recurring in cron (2)

- `wire-recurring-sweep-into-system-cron` [draft] — the recurring sweep
  (digest/dream/skill-update) only fires when a human runs `relay recurring`;
  `scripts/cron.sh` ships but nothing installs it into a scheduler. Give a fresh
  install a documented one-step way to turn the sweep on. Scheduling only — the
  budget-aware drain loop is a separate v1 ticket (below).
- `enforce-mode-auto-for-recurring-templates` [draft] — no-TTY safety: under
  cron only `mode: auto`/`script` templates launch; an interactive template
  scaffolds but fails to launch. Pairs with the cron ticket.

### First-run correctness (4)

Bugs a stranger hits on day one — in scope precisely because of the v1 promise.

- `first-run-works-without-slack-configured` [draft] — a fresh install with no
  Slack still works.
- `fail-loud-on-unrecognized-config-sections-instead` [draft] — config errors
  fail loud, not silently.
- `slack-post-ignores-http-response-so-bad-webhook-fa` [draft] — a bad webhook
  fails loud instead of silently swallowing the error.
- `fail-loud-when-an-env-indirected-secret-is-missing` [draft] — a missing
  `env:VAR` secret resolves to `""` instead of erroring (`config.py:435`); a
  stranger mis-setting a secret fails silently. Same family as the two above;
  also feeds the `authentication-system` per-skill-secrets scope.

### Flow simplification (1)

- `implicit-activation-inrpogress` [draft] — drop the explicit "mark active"
  step: launching a ticket activates it. draft → (running) → done. Scope is the
  activation step only; auto-advancing workflow bumps is deferred
  (`v2/why-ai-asks-me-to-bump-instead-of-doing-it`).

### Single-file task format (1)

- `single-file-task-format-section-aware-compose-filt` [draft] — merge the
  three-file task layout into one file + a section-aware compose filter so only
  working sections load. High blast radius; sequence when the board is calm.
  Pulled into v1 by owner decision (operator-ergonomics win). Likely splits at
  design: format+migration → compose filter → writer migration → docs rewrite.

### Prompt quality (2)

- `improve-prompt-for-relay-launch` [draft] + `improve-prompt-for-relay-ticket`
  [draft] — tighten the launch/ticket-authoring prompts.

### Autonomy chain (7)

The big bet: use spare overnight token budget to run flagged-ready tickets
unattended. Strict dependency chain; `auto/stream-agent-progress` is the hard
blocker, so this lands late in v1.

- `session-done-sentinel-from-mark-done-bump-leaks-in` [draft] —
  reliability prerequisite: a child `relay mark done`/`bump` leaks the
  session-done sentinel and tears down the supervised run. Unattended runs can't
  be trusted until this is fixed; the sibling `session-done-sentinel-leaks…` is
  already done.

1. `track-usage-of-llm` [active] — foundational per-session usage primitive;
   everything below consumes it.
2. `represent-autonomy-tier-in-ticket-mode-field` [draft] — the
   "ready for unattended execution" flag; consumes the autonomy-triage work.
3. `auto/stream-agent-progress-in-auto-mode-and-recurring-l` [draft] — **hard
   blocker**; re-enables `mode: auto` (currently disabled — it buffers stdout).
4. `async-park-and-continue-on-block` [draft] — a blocked ticket parks cleanly
   and the sweep keeps going instead of stalling.
5. `drain-pending-auto-tickets-with-leftover-session-b` [draft] — the
   budget-aware drain loop.
6. `nightly-auto-drain-run-for-ready-tickets` [draft] — assembles 1–5 into the
   scheduled overnight run (wires `relay-os/scripts/cron.sh`, pairing with the
   recurring-in-cron ticket; Relay does not manage cron itself).

## v2 — deferred backlog

Everything under `relay-os/tasks/v2/`. Not scheduled against the launch. The
broad buckets (see `relay status` / the directory for the authoritative list):

- **Docs / knowledge-base** — the `document-*` batch, context-splitting and
  file-access cleanups, the `rules.md` audit. Do these after the single-file
  format rewrite or you will clean up docs you are about to rewrite.
- **PM / planning features** — `acceptance-criteria`, `identify-blocking-issues`,
  `relay-design-repositories`, `issue-inbox-slack`, ticket-spec splitting,
  subprojects.
- **Recurring bugfixes** — debug-surface, git issues, template instantiation,
  Dream persistence, standalone-automerge retirement.
- **Security / secrets / PII** — `manage-security-and-pii`, per-skill secret
  scoping, a first-class machine-local config dir. (Several feed the v1
  `authentication-system` design; fail-loud-on-missing-secret was promoted to
  v1.)
- **Compose / validation** — frontmatter stripping, prompt token budget,
  symlink-view exclusion, SKILL.md and hand-edit validation.
- **Git hygiene / dev-loop** — sync-with-main lift, uncommitted-work cleanup,
  worktree-per-task. A dogfooding investment that can be pulled forward to run
  alongside v1 since we build Relay with Relay.
- **Autonomy payoffs** — `autoroute-agent-based-on-remaining-usage`,
  `model-selector` (genuinely post-v1).
- **Robustness / isolation** — file locking, container/VM isolation, timestamp
  precision.
- **Skills, prompts, naming, CI** — skill search, sibling-split discipline,
  `minimal-ci-run-pytest-on-prs-and-tags`, the workflow→playbook rename, and the
  rest.

## What this context does NOT cover

- The reasoning behind decisions / what was deferred and why — see
  `relay/current-direction`.
- The principles a change must not violate — see `relay/principles`.
- The full backlog — see `relay status` (and `relay-os/tasks/v2/` for v2).
