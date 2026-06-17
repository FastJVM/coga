---
title: authentication system
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
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
   duplicate — fold them in or keep them as the implementation tickets. A third
   implementation concern folds in here: a **1Password-backed secret provider**
   so secrets resolve on demand from `op` rather than only via env injection at
   launch. Concrete shape (settled 2026-06-17, folded in from the now-deleted
   `add-a-way-to-query-a-declared-secret-on-demand` draft):
   - Add an `op://vault/item/field` indirection scheme as a third branch in
     `_resolve_secret_value` (`src/relay/config.py` ~840-865), alongside `env:`
     and literals. `op read` consumes 1Password's native secret-reference URI
     verbatim, so no parsing on our side.
   - Resolution shells to `op read "<ref>"` on demand and fails loud if `op` is
     missing / unauthenticated / the item doesn't resolve (inherit the
     fail-loud behavior from the sibling ticket).
   - Keep it 1Password-only. Use the existing prefix dispatch as the only
     "pluggability" seam — a future provider is one more `elif` branch, **not**
     a plugin registry or provider-interface abstraction (legible over clever,
     per `relay/principles`).
   - Expose a thin `relay secret get <key>` CLI over the shared resolver so a
     human can verify `op` auth without launching a task.
   - Depends on the `secrets:` declaration field from
     `fail-loud-when-an-env-indirected-secret-is-missing` landing first.

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
