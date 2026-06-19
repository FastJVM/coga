---
title: 'Manually test auth paths: gh/git detection, secret resolution, per-task injection'
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/architecture
  - relay/cli
skills: []
workflow:
  name: autonomy/human-only
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: human
  - name: verify-read-only
    skills: []
    assignee: agent
secrets: null
step: 1 (brief-and-hand-off)
---

## Description

Manual verification of Relay's auth/capability paths. These all touch the
local operator's real credentials (`gh` token, signed-in 1Password, machine
env), so only the human can run them end-to-end — hence `autonomy/human-only`.
The goal is to confirm each path **fails loud and actionable** when auth is
missing and resolves correctly when present.

Scope is the three boundaries below. For each, run the listed checks and record
pass/fail + any wrong/silent behavior in the blackboard.

### 1. gh / git auth detection

- With `gh` logged out (`gh auth logout`), run `relay launch <slug>` on a
  ticket whose `## Dev` names a PR: the freshness check must emit a **loud
  warning** with a `gh auth login` hint and continue unverified — not a silent
  skip, not a hard crash.
- `relay automerge` with `gh` logged out / not installed: surfaces the `gh`
  error loudly, does not report success.
- Confirm git transport uses the configured remote and that a bad/missing
  remote fails with an actionable hint rather than a stack trace.
- Re-auth (`gh auth login`) and confirm the verified path works (auto-bump of a
  merged-PR final-step ticket).

### 2. Secret resolution (`env:` / `op://`)

- `env:VAR` indirection: set, then unset the var — launch resolves the value
  when set, and **fails loud naming the Relay secret key** (never the value)
  when unset/required.
- `op://vault/item/field`: signed out of 1Password → launch fails loud with the
  op reference named, not a silent skip; `op read` non-zero is surfaced.
- Signed in → value resolves and is injected.
- Confirm error messages reference the Relay secret key / reference, never leak
  the resolved secret value.

### 3. Per-task secrets injection (`secrets:` gating)

- `secrets: null` (or absent) → legacy behavior: all configured secrets
  injected, unset env-backed values skipped.
- `secrets: []` → no secrets injected.
- `secrets: [<one key>]` → only that `[secrets]` key injected, others withheld.
- Verify a `mode: script` launch sees the injected secrets as env vars and an
  excluded one is absent.

Out of scope: the `skip_permissions` auto-mode policy (auto launches are
temporarily disabled anyway).

### Done check

Every check above run, with results (and any loud-failure gaps) captured in the
blackboard. File follow-up tickets for any path that fails silently or leaks a
value.

## Context

