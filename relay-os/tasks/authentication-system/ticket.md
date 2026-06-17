---
title: authentication system
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Relay has no coherent story for "who is this / what is this allowed to do" once
it leaves the author's laptop. For the v1 launch surface we need an
authentication/identity design that covers four distinct concerns. They are
related but **not one implementation** — the first design step should decide
which ship for v1 and which split into their own tickets (several already
exist; see Context).

Scopes to cover:

1. **Telemetry / install identity** — an anonymous, opt-out, no-PII way to
   sign or rate-limit install pings so the count is trustworthy without
   identifying users. Pairs with `anonymous-install-telemetry-opt-out-no-pii`.
2. **Hosted backend / API account** — if any v1 feature phones home (telemetry
   sink, future sync), define the account/token model: signup, token issuance,
   storage, revocation. This is the heaviest scope and carries the principle
   tension (hosted backend vs. local-first); justify anything that crosses that
   line.
3. **Git / GitHub credential handling** — standardize how Relay discovers and
   uses git/GitHub auth (PAT, `gh` CLI, SSH agent) so PR/open-pr/automerge work
   on a stranger's machine without bespoke setup. Connects to
   `relay-forces-https` / `remote-default-origin`.
4. **Per-skill secrets / env indirection** — scoped secret passing to skills
   and fail-loud on missing secrets. This scope is **already ticketed**:
   `pass-secrets-to-skills-with-per-skill-scope` and
   `fail-loud-when-an-env-indirected-secret-is-missing`. Reference, don't
   duplicate — fold them in or keep them as the implementation tickets.

Design output: a one-page model of identity/auth boundaries (local user, the
repo, skills, any hosted endpoint), a decision on which scopes are v1-blocking
vs. deferrable, and a split into implementation tickets. Respect local-first /
legible-state principles — secrets stay in `relay.local.toml` / `env:` indirection,
nothing real committed.

## Context

- Selected scope (all four) confirmed by owner on 2026-06-16.
- Overlapping existing tickets to fold in / reference rather than duplicate:
  `anonymous-install-telemetry-opt-out-no-pii`,
  `pass-secrets-to-skills-with-per-skill-scope`,
  `fail-loud-when-an-env-indirected-secret-is-missing`,
  `add-a-first-class-relay-config-directory-for-machi`.
- Principle tension on scope 2 (hosted backend) — see `relay/principles` and
  the telemetry ticket's same tension. Keep local-first unless there is no
  alternative, and document the payload + a trivial disable.
- Roadmap: Wave 1 (launch gate). This is a **design-first umbrella** — expect it
  to split.
