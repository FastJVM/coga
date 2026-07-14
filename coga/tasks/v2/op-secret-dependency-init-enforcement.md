---
slug: v2/op-secret-dependency-init-enforcement
title: Decide whether `op` should be enforceable at init (vs launch-only)
status: draft
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Follow-up to the secrets refactor (inline per-ticket `op://` / `env:` secrets)
and the `relay init` dependency check.

### Current behavior (shipped)

- `relay init` hard-requires **`git`** and **`gh`** (crashes if missing).
- **`op` (1Password CLI) is intentionally NOT checked at init.** Forcing every
  operator to install `op` up front is too harsh — most repos never use an
  `op://` secret. Instead, `op` is enforced **at launch**: when a ticket
  declares an `op://vault/item/field` secret and `op` is missing (or `op read`
  fails), the launch fails loud naming the reference (never the value). This
  "check when actually needed" path eases installation.

### Open question for v2

Should a repo be able to *opt in* to requiring `op` up front, so a team that
knows it uses 1Password fails fast at `init` instead of at the first op-backed
launch? The shape discussed:

1. A flag in `relay.toml` — e.g. `[init] require_op = true` (default `false`,
   shared so it's a repo-wide declaration that "this repo uses op secrets").
2. A `relay init` option — e.g. `relay init --require-op` — that writes the
   flag.
3. When the flag is set, the init dependency check also crashes on a missing
   `op`. The launch-time crash stays unconditional regardless of the flag (it
   is the real safety net; the flag only moves the failure earlier).

### Why deferred

The launch-time check is sufficient and correct for v1, and keeps onboarding
light (no 1Password install unless a ticket actually needs it). The upfront
opt-in enforcement is a convenience for op-heavy teams, not a correctness
requirement — so it can wait.

### Done when

A decision is recorded (build the opt-in flag, or keep launch-only), and if
built: the `relay.toml` flag, the `relay init` option, the gated init check,
docs (`relay/cli`, `relay/architecture`, README External CLI Tools), and tests.

### Pointers

- `_check_external_dependencies` + the requirements manifest in
  `src/relay/commands/init.py`.
- `_resolve_op_reference` / `select_launch_secrets` in `src/relay/config.py`
  (the launch-time op crash).
- Sibling v2 ticket: `gh-merge-requirement`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
