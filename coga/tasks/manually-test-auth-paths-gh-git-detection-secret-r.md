---
slug: manually-test-auth-paths-gh-git-detection-secret-r
title: 'Manually test auth paths: gh/git detection, secret resolution, per-task injection'
status: done
autonomy: interactive
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

- With `gh` logged out (`gh auth logout`), `relay launch <slug>` must **fail
  loud, never hang**: the launch-entry push-auth preflight refuses with "git
  push access … is unavailable" (and the git sync runs non-interactively so a
  credential-less push fails fast instead of blocking on a prompt). [Note: the
  old launch-time gh "freshness check / warn-and-continue" was retired (#414);
  the shipped behavior is fail-fast + refuse — see #426.]
- `relay automerge` with `gh` logged out / not installed: surfaces the `gh`
  error loudly, does not report success.
- Confirm git transport uses the configured remote and that a bad/missing
  remote fails with an actionable hint rather than a stack trace.
- Re-auth (`gh auth login`) and confirm the verified path works (auto-bump of a
  merged-PR final-step ticket).

### 2. Secret resolution (`env:` / `op://`) — inline per-ticket (no `[secrets]` catalog)

Secrets are declared inline on the ticket as `secrets: [{NAME: <ref>}]` where
`<ref>` is `env:VAR` or `op://vault/item/field` (PR #428 dropped the central
catalog).

- `env:VAR`: with VAR set → launch resolves and injects it as env var `NAME`;
  with VAR unset → **fails loud naming the env var** (never the value).
- `op://vault/item/field`: signed in → value resolves (live `op read`) and is
  injected; `op` missing / not signed in / `op read` non-zero → fails loud with
  the **reference** named, never a silent skip.
- Error messages reference the secret name / reference, never the resolved value.
- `relay secret get <ref>` (an `op://…` or `env:VAR` reference) is the
  human-facing single-reference probe.

### 3. Per-task secrets injection (`secrets:` gating)

- `secrets: null` (or absent) **or** `secrets: []` → no secrets injected.
  (There is no `[secrets]` catalog, so there is no "inject all" blanket.)
- `secrets: [{NAME: <ref>}]` → only the declared name(s) injected as env vars;
  the source `env:VAR` is scrubbed from the child; anything not declared is
  withheld.
- Verify a `script`-mode launch sees the injected secrets as env vars and an
  excluded one is absent (a script that echoes presence — not values).

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

> Note: the "Brief" numbered steps above were written against the pre-refactor
> model (gh freshness warning, `[secrets]` catalog, `null` = inject-all). They
> are **superseded** by the updated `## Description` checks — the testing this
> session surfaced bugs that were fixed, and the secrets model itself changed.

### Check 1 — gh / git auth detection
- **1.1 logged-out launch → PASS (behavior changed + bug fixed).** Original
  expectation (loud gh-freshness warning + continue) described retired behavior
  (#414). Found instead: launch's git sync **hung on an interactive credential
  prompt**. Fixed in **PR #426** — git sync is now non-interactive
  (`GIT_TERMINAL_PROMPT=0`), so a credential-less push fails fast/loud; and a
  new launch-entry **push-auth preflight refuses** to start when push access is
  broken (no agent spawned). Verified live (loud `terminal prompts disabled`,
  no hang) + unit tests.
- 1.2 `relay automerge` logged out / gh missing → surfaces `gh` error loudly:
  path intact (`autoclose.sweep_merged(quiet=False)` raises `GhError`). NOT
  re-run live this session (would need `gh auth logout`).
- 1.3 bad/missing remote → `relay validate --check-github` is the actionable
  probe (`github_preflight`, non-interactive). Not re-run live.
- 1.4 re-auth → verified path / merged-PR auto-bump. Not re-run live.

### Check 2 — secret resolution — PASS
- `op://` resolves live through relay: `relay secret get op://Employee/Namecheap/username`
  → printed `ntoper` (real `op read` via relay's exact path). ✅
- `op` missing / `op read` non-zero → launch crashes loud naming the reference,
  no agent spawned, value never leaked — covered by merged unit tests
  (`test_launch_*` op paths, `test_secret_*`). ✅
- `env:VAR` unset → fail loud naming the var — demonstrated live via
  `select_launch_secrets` (`ticket secret 'NEEDED' references env var
  'DEFINITELY_UNSET_VAR' but it is not set`). ✅
- `relay secret get <literal>` → clean rejection (PR #431). ✅

### Check 3 — per-task gating / injection — PASS (resolution layer live)
Demonstrated live via `build_launch_env` (relay's real path):
- declared secret injected under its scoped env-var name ✅
- source `env:VAR` scrubbed from the child env ✅
- non-secret env var still inherited ✅
- `secrets: []` injects nothing ✅
- unset `env:` var fails loud, names the var ✅
End-to-end `script`-mode delivery covered by merged `test_launch_script` tests.

### Follow-ups filed (v2)
- `op-secret-dependency-init-enforcement` — should `op` be enforceable at init?
- `op-service-account-auth-for-unattended-secrets` — service-account token so
  `op://` resolves unattended (no per-call prompt).

### Shipped this session
PR #426 (git-launch fail-loud), #428 (inline `op://`/`env:` secrets, drop
catalog), #430 (init requires git+gh; deps manifest) — all merged. #431 (secret
get literal wording) open.
