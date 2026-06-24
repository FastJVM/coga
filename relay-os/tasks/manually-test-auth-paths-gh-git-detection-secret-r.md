---
slug: manually-test-auth-paths-gh-git-detection-secret-r
title: 'Manually test auth paths: gh/git detection, secret resolution, per-task injection'
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
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
step: 2 (human-executes)
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

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Brief (step 1 — brief-and-hand-off)

### Goal
Confirm Relay's three auth/capability paths **fail loud and actionable** when
auth is missing, and resolve correctly when present. Only the human can run
these end-to-end because they touch real `gh`/git creds, a real signed-in
1Password, and machine env. Capture pass/fail + any silent/wrong behavior here.

### Why this is human-only
Each check toggles your *real* credential state (`gh auth logout`, unset env
var, 1Password sign-out). An agent can't safely flip your local auth, so the
middle step (`human-executes`) is yours; the final `verify-read-only` step is
the agent reading back what you recorded.

### Ordered steps to run (record result under each)

**1. gh / git auth detection**
  1. Pick/ensure a ticket whose `## Dev` names a PR, on its final workflow step
     (or no workflow). Run `gh auth logout`, then `relay launch <slug>`.
     EXPECT: loud warning + `gh auth login` hint, launch *continues unverified*.
     FAIL: silent skip, or a stack-trace crash.
  2. `relay automerge` while logged out (or `gh` uninstalled).
     EXPECT: loud `gh` error, no success reported.
  3. Bad/missing git remote → EXPECT actionable hint, not a stack trace.
     (`relay validate --check-github` is the non-destructive probe for this.)
  4. `gh auth login` again, then launch a merged-PR final-step ticket.
     EXPECT: verified path works — auto-bump to done.

**2. Secret resolution (`env:` / `op://`)**
  5. `env:VAR` secret: with VAR set → value resolves on launch. Unset VAR →
     fails loud **naming the Relay secret key, never the value**.
  6. `op://vault/item/field` secret signed out of 1Password → fails loud with
     the op reference named (not silent skip); `op read` non-zero surfaced.
  7. Signed in → value resolves and is injected.
  8. Across all of the above: confirm NO error message leaks the resolved value.
     (`relay secret get <key>` is the human-facing single-key probe.)

**3. Per-task secrets injection (`secrets:` gating)**
  9. `secrets: null`/absent → all configured secrets injected, unset env-backed
     ones skipped (legacy behavior).
  10. `secrets: []` → none injected.
  11. `secrets: [<one key>]` → only that key injected, others withheld.
  12. `mode: script` launch sees injected secrets as env vars; excluded one is
      absent. (A script that echoes `env | grep`-style presence is the check —
      don't print values into the log.)

### Irreversible / state-changing actions to be aware of
- `gh auth logout` / `gh auth login` — changes your real GitHub session. You
  must re-auth at the end (step 4) to leave the machine as you found it.
- 1Password sign-out/sign-in — same: restore your session afterward.
- The successful auto-bump in step 4 **advances a real ticket to done**. Use a
  throwaway/test ticket for that, or be prepared to rewind it.
- Unsetting env vars is shell-local; no persistent change if done in a subshell.
- Everything else (`relay validate`, `relay secret get`, `--prompt-report`) is
  read-only.

### Done check
Every numbered check above run, results recorded here, including any
loud-failure GAP (silent skip / value leak / stack trace). File a follow-up
ticket for each path that fails silently or leaks a value.

### Handoff
Step 1 (this brief) complete → bumping to `human-executes`. Nick runs the
checks and records results below; then bump to `verify-read-only` for the
agent read-back.

---

## Results (fill in during human-executes)
