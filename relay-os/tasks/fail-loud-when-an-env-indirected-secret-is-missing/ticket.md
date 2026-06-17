---
title: Scope secret injection to declared per-task secrets and fail loud on missing
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
---

## Description

Priority: medium. Security/correctness footgun in the secrets path.

`_resolve_secret_value` resolves `env:VAR` indirection by
`os.environ.get("VAR", "")` (`config.py:850`) — a **missing env var resolves to
an empty string, not an error**. The comment claims secrets are "validated at
launch time when needed," but no such validation exists: `launch.py:325`
just does `env.update(cfg.secrets)`, injecting the empty value. A typo like
`env:STRPE_KEY` silently injects an empty secret, and the downstream tool fails
later with a confusing, unrelated error. (Grep over trusting these line
numbers — they drift.)

This directly contradicts Relay's fail-loud principle. A declared secret that
points at an unset env var should be a hard, named error at the point it is
needed (launch, before the agent starts), not a silent empty string.

### Scoping: which secrets does a launch need?

There is a single global `[secrets]` table in `relay.local.toml`, and every
launch path blanket-injects all of it (`env.update(cfg.secrets)` in
`launch.py`, `launch_script.py`, `ticket.py`, `delete.py`, `project.py`).
Nothing scopes secrets to a task today, so a naive "fail if any declared
`env:VAR` is unset" rule would over-block: a multi-project shell that exported
only the secret today's task needs would be refused launch over an unrelated,
unexported secret. Fail-loud must not become fail-annoying.

Resolution (decided with the human): add a per-ticket required-secrets list,
and use that same list to scope *which* secrets get injected (least privilege —
"don't hand the agent more than it asked for").

This ticket covers declaration (the field) + least-privilege injection +
fail-loud. A **separate** ticket covers a way to *query/retrieve* a secret on
demand (CLI/helper) — out of scope here.

### Migration / backward-compat decision (human to confirm)

Strict least-privilege would mean a ticket with empty/absent `secrets:` gets
**no** secrets injected — which would break any existing task that today relies
on an ambient secret it never declared (every current ticket has no `secrets:`).
To avoid a silent breakage, **opt-in scoping**:

- `secrets:` **absent / null** → legacy behavior: blanket-inject the whole
  `[secrets]` table (no change, no breakage), but still apply the empty-string
  fix (item 4) so unset vars are never injected as `""`.
- `secrets:` **a declared list** → strict least-privilege: inject **only** the
  listed keys, fail-loud (item 3) on any that are undeclared/unset, inject
  nothing else.

A future ticket can flip the default to strict once tickets broadly declare.

### Fix

0. **Least-privilege injection (the "don't ask more" piece).** When a ticket
   declares a `secrets:` list, the launch env is built from *only* those keys —
   undeclared secrets in `[secrets]` are not injected into the agent process.
   Absent/null list keeps legacy blanket-inject (see migration note above).

1. **New canonical ticket frontmatter field `secrets:`** — a YAML list of
   secret *keys* (the names under `[secrets]` in `relay.local.toml`) that this
   task requires. `null` / `[]` means the task needs none. The field is
   nullable so a human accepts and enforces it deliberately; only the listed
   keys are enforced for that launch.
   - **Two separate registrations, both required** (easy to do only one):
     add it to `_RESERVED_TICKET_FIELD_NAMES` (`config.py:364`, the
     repo-extension collision guard) **and** to `OPTIONAL_TASK_KEYS` in
     `validate.py` (~line 79) — **not** `REQUIRED_TASK_KEYS`, or every existing
     ticket fails validation as a missing-required-key. Then add it to both
     ticket templates: `relay-os/tasks/_template/ticket.md` and the packaged
     copy under `src/relay/resources/templates/relay-os/`.
   - **Absent == null == [].** Existing tickets have no `secrets:` key.
     Enforcement must read it defensively (`get("secrets") or []`) so an
     absent or null field enforces nothing — never iterate a `None` (that
     `TypeError`s and breaks launching every legacy ticket).
2. **Hard fail at `relay launch`** — for each key in the ticket's `secrets:`
   list, fail (exit non-zero, no agent spawned) if the key is not declared in
   `[secrets]`, or if its `env:VAR` indirection points at an unset env var.
   These are two distinct named errors (undeclared key vs unset env var); a
   key with a literal non-`env:` value can't be "unset" and passes. The
   message names both the secret key and the missing env var.
3. **Stop silent empty-string injection (independent of the list)** — unset
   `env:` secrets must no longer resolve to `""` and get injected. Distinguish
   "unset env var" from "empty literal" in `_resolve_secret_value` /
   `_resolve_secrets` (`config.py:840-865`) and never inject a secret whose env
   var is unset. Update the misleading docstrings there that claim validation
   happens "at launch time when needed" (it didn't).
4. **`relay validate` warn** — flag tickets whose declared `secrets:` keys map
   to env vars that are unset in the current environment, or to keys absent
   from `[secrets]`. Warn, not error — env differs per shell.

Acceptance: launching a task that requires a secret resolving to an unset
`env:VAR` exits non-zero with a message naming the secret key and the env var;
a task that declares `secrets:` gets only those keys injected (undeclared
secrets absent from its env); a task with no `secrets:` keeps legacy inject-all
but never receives an empty-string secret; the new `secrets:` field is
validated; covered by config + launch tests.

## Context

Code pointers:
- `src/relay/config.py:840-865` — `_resolve_secret_value` / `_resolve_secrets`
  (the `os.environ.get(VAR, "")` footgun and the misleading docstrings).
- `src/relay/config.py:364` — `_RESERVED_TICKET_FIELD_NAMES` (register the new
  field here so it can't collide with a repo extension).
- `src/relay/commands/launch.py:325` — `env.update(cfg.secrets)` injection
  point; the hard-fail check goes before this. Note the same blanket inject
  exists in `launch_script.py:131`, `ticket.py:173`, `delete.py:62`,
  `project.py:106` — decide which paths enforce (launch is the agent-spawning
  one named in acceptance; the others may warrant the same guard).
- `relay-os/tasks/_template/ticket.md` + the packaged template under
  `src/relay/resources/templates/relay-os/` — keep both in sync (per CLAUDE.md).

Also note `extra_local` (`config.py:225`) silently retains arbitrary unknown
local keys — no typo protection there either; worth a warn in the same pass.
