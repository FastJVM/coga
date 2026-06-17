---
title: Scope secret injection to declared per-task secrets and fail loud on missing
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
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

### Injection model (decided with the human)

Two decisions pin this down:

**`relay launch` is the *only* place secrets are injected.** Today five paths
blanket-inject (`launch.py`, `launch_script.py`, `ticket.py`, `delete.py`,
`project.py`). Decision: secrets flow through the launch chokepoint **only** —
strip secret injection from the management/other paths. ⚠️ **Risk to verify:**
those paths inject for a reason today — notably `launch_script.py:74` documents
that `mode: script` runs receive secrets as env vars. The implementer must
either (a) fold script-mode secret delivery into the same launch chokepoint so
script tasks still get their (scoped) secrets, or (b) confirm each stripped path
genuinely needs none and note what was verified. Do **not** silently break
script-mode secrets.

**Three cases for the `secrets:` field** (note `[]` ≠ null — they differ):

- `secrets:` **absent / null** → legacy behavior: blanket-inject the whole
  `[secrets]` table (no change, no breakage for existing tickets), but still
  apply the empty-string fix (item 3) so unset vars are never injected as `""`.
- `secrets:` **explicit empty list `[]`** → **strict: inject nothing.** A
  deliberate lockdown — the task gets zero secrets. Distinct from null.
- `secrets:` **a non-empty list** → strict least-privilege: inject **only** the
  listed keys, fail-loud (item 2) on any undeclared/unset, inject nothing else.

Rationale: strict-on-absent would silently break existing tasks relying on
ambient undeclared secrets; opt-in via a declared list (or explicit `[]`) lets a
human lock a task down deliberately. A future ticket can flip the *default* to
strict once tickets broadly declare.

### Fix

0. **Least-privilege injection (the "don't ask more" piece).** Secrets are
   injected only at the `relay launch` chokepoint (other paths stripped — see
   injection model above). When a ticket declares a non-empty `secrets:` list,
   the launch env is built from *only* those keys; explicit `[]` injects none;
   absent/null keeps legacy blanket-inject.

1. **New canonical ticket frontmatter field `secrets:`** — a YAML list of
   secret *keys* (the names under `[secrets]` in `relay.local.toml`) that this
   task requires. The field is nullable so a human accepts and enforces it
   deliberately. Note the three-way semantics: absent/null = legacy blanket,
   explicit `[]` = inject nothing, non-empty list = exactly those keys (see
   injection model above).
   - **Two separate registrations, both required** (easy to do only one):
     add it to `_RESERVED_TICKET_FIELD_NAMES` (`config.py:364`, the
     repo-extension collision guard) **and** to `OPTIONAL_TASK_KEYS` in
     `validate.py` (~line 79) — **not** `REQUIRED_TASK_KEYS`, or every existing
     ticket fails validation as a missing-required-key. Then add it to both
     ticket templates: `relay-os/tasks/_template/ticket.md` and the packaged
     copy under `src/relay/resources/templates/relay-os/`.
   - **Absent/null differ from `[]` — don't collapse them.** Existing tickets
     have no `secrets:` key. The injection-*mode* branch must distinguish
     `None`/absent (→ blanket) from `[]` (→ inject nothing) from a non-empty
     list (→ those keys); do **not** use `get("secrets") or []` for that
     decision (it folds `[]` into None). The `or []` idiom is fine only for the
     fail-loud *iteration* (no keys → nothing to check) — never iterate a
     `None` directly (that `TypeError`s and breaks launching legacy tickets).
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
   - **This is a data-model change to `cfg.secrets`, not a one-line fix.**
     Secrets are resolved eagerly at config-load (`config.py:223`), so by the
     time any inject site or fail-loud check runs, `cfg.secrets` is already a
     flat `{key: ""}` dict — the original `env:VAR` reference and the
     unset-vs-empty-literal distinction are **gone**. Item 2's "name the missing
     env var" and item 4's validate-warn both need that lost information.
     Implementation must either stop resolving eagerly (carry raw refs forward)
     or have `_resolve_secrets` **retain provenance** (e.g. a sentinel/`None`
     for unset + the original var name). Every consumer of `cfg.secrets` is
     affected — treat this as the load-bearing change.
4. **`relay validate` + field-shape validation.**
   - **Shape (error):** `secrets:` must be a list of strings; a scalar or
     non-string entry is a validation error. The frontmatter is otherwise
     free-form, so this type check must be added explicitly (registering in
     `_RESERVED_TICKET_FIELD_NAMES` / `OPTIONAL_TASK_KEYS` does *not* type it).
   - **Env presence (warn):** flag tickets whose declared `secrets:` keys map
     to env vars unset in the current environment, or to keys absent from
     `[secrets]`. Warn, not error — env differs per shell.

Acceptance: launching a task that requires a secret resolving to an unset
`env:VAR` exits non-zero with a message naming the secret key and the env var;
a task that declares `secrets:` gets only those keys injected (undeclared
secrets absent from its env); a task with no `secrets:` keeps legacy inject-all
but never receives an empty-string secret; a non-list `secrets:` value is a
validation error and unset declared keys produce a validate warning; covered by
config + launch + validate tests.

## Context

Code pointers:
- `src/relay/config.py:840-865` — `_resolve_secret_value` / `_resolve_secrets`
  (the `os.environ.get(VAR, "")` footgun and the misleading docstrings).
- `src/relay/config.py:364` — `_RESERVED_TICKET_FIELD_NAMES` (register the new
  field here so it can't collide with a repo extension).
- `src/relay/commands/launch.py:325` — `env.update(cfg.secrets)` injection
  point; the hard-fail + least-privilege scoping go here. Per the injection
  model, this is the **only** site that injects secrets: strip the same blanket
  inject from `launch_script.py:131`, `ticket.py:173`, `delete.py:62`,
  `project.py:106`. Verify what each relied on first — `launch_script.py:74`
  documents script-mode secret env vars, so script-mode delivery must be folded
  into the launch chokepoint, not dropped.
- `relay-os/tasks/_template/ticket.md` + the packaged template under
  `src/relay/resources/templates/relay-os/` — keep both in sync (per CLAUDE.md).

Also note `extra_local` (`config.py:225`) silently retains arbitrary unknown
local keys — no typo protection there either; worth a warn in the same pass.
