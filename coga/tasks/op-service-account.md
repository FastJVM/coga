---
slug: op-service-account
title: op-service-account
status: draft
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Set up the 1Password **service-account infrastructure** that lets headless coga
jobs (recurring / cron, no TTY) resolve `op://` secret references without an
interactive `op signin`. This is a single unit of work — the SA setup itself.
Tickets that *consume* the secrets are separate and declare their own inline
`secrets:` refs.

### The work
- **SA `coga-recurring-sa`** — headless 1Password identity, auth via
  `OP_SERVICE_ACCOUNT_TOKEN`, read-only scoped to just the `coga-recurring`
  vault (least privilege: a leaked token has a one-vault blast radius).
  *(done — created and scoped 2026-07-19.)*
- **Vault `coga-recurring`** — the container the SA reads. Named distinctly from
  the SA on purpose: an `op://` ref is `op://<vault>/<item>/<field>`, so the
  first segment is the *vault*; the SA name never routes the lookup.
- **Vault items** — `uspto-api-token`, `coga-important-webhook`, each with a
  `credential` field (confirm exact titles against the real items). Future
  headless-job secrets accrue in this vault too.
- **SA token** — stored in the root/admin vault (never the vault it reads: it's
  the key, not a payload, and can never be an `op://` ref). Delivered by hand
  into the cron/systemd env at run time.

### Scope boundaries
- **No coga code change needed.** `_resolve_op_reference` (`src/coga/config.py`)
  shells out to `op read <ref>` and inherits the parent env; `op` auto-uses
  `OP_SERVICE_ACCOUNT_TOKEN` when present. Exporting the token in the job
  process is sufficient.
- **Consumer refs live on other tickets** — a ticket goes where its *subject*
  lives, not where its credentials live.
- **Manual vs. PR-able:** creating the SA / vault / items / token is manual
  (no repo diff — the repo only ever holds pointers). PR-able parts: this
  ticket and secrets-management docs. *(See note below — docs may move to a
  separate ticket.)*

### Done when
- SA + vault + items exist and the SA token is stored in the root/admin vault.
- `coga secret get op://coga-recurring/uspto-api-token/credential` resolves in a
  **clean env** where `OP_SERVICE_ACCOUNT_TOKEN` is the only credential (a
  personal `op` login reads everything → false pass on SA scoping).

## Context

<!-- coga:blackboard -->

## Design notes (from bootstrap/orient chat, 2026-07-19)

Scoping discussion before the ticket body is written. Nothing built yet.

### What this ticket is
The **service-account infrastructure** for headless coga jobs. One ticket — the
SA setup is a single unit of work, not "a few." Consumer jobs that *use* the
secrets are separate tickets (see below).

### The structure
- **Service account:** `coga-recurring-sa` — the headless 1Password *identity*.
  Authenticates via `OP_SERVICE_ACCOUNT_TOKEN` (no interactive `op signin`, no
  TTY), and is scoped read-only to just its vault (least privilege — if the
  token leaks, blast radius is one vault).
- **Vault:** `coga-recurring` — the *container* the SA can read.
- **Distinct names on purpose.** An `op://` ref is `op://<vault>/<item>/<field>`
  — the SA name never appears in the ref, the first segment is the *vault*.
  Naming the SA and vault identically invites the exact confusion of "does the
  SA name route the lookup?" (it doesn't). Vault name describes contents
  (`coga-recurring`), SA name reads like an identity (`coga-recurring-sa`).
- **Items in the vault:** `uspto-api-token`, `coga-important-webhook`, each with
  a `credential` field. Future headless-job secrets accrue here too.

### Coga needs no code change to use this
`_resolve_op_reference` (`src/coga/config.py:1234`) just shells out to
`op read <ref>` and inherits the parent process env. The `op` CLI auto-uses
`OP_SERVICE_ACCOUNT_TOKEN` when present. So the moment the token is exported in
the process that runs the job, every `op://` ref resolves non-interactively.

### The two consumer refs live on OTHER tickets, not here
The secrets are declared inline on the ticket that *consumes* them:
- `headless-uspto-api-important-webhook` → `op://coga-recurring/uspto-api-token/credential`
  and `op://coga-recurring/coga-important-webhook/credential`.
(Item titles above are approximate — confirm against the real 1Password items.)
A ticket goes where its *subject* lives, not where its *credentials* live.

### PR-able vs. manual
- **Manual (your setup, no PR):** create SA + vault, grant access, add items,
  mint token. No repo diff, nothing to review — the repo only ever sees
  pointers, never values.
- **PR-able:** this ticket, the consumer tickets' `secrets:` refs, and any
  docs/context. Fold the pattern docs (a short `coga/contexts/coga/` note or
  README section on adding a headless secret + reffing it) into this ticket's PR.

### Test before it goes live
`coga secret get op://coga-recurring/uspto-api-token/credential` resolves through
the exact path `coga launch` uses — proves the plumbing with no ticket/cron.
**Critical:** test in a *clean env* where `OP_SERVICE_ACCOUNT_TOKEN` is the only
credential (personal `op` login can read everything → false pass; won't prove SA
scoping). `coga validate` does NOT live-resolve `op://` (only checks ref shape,
`validate.py:615`), so consumer refs can be committed before the items exist.

### Decisions
- No `service-account/` subdirectory yet — infra is one ticket; a dir with one
  ticket is over-organizing. Promote with `mkdir + mv` if a 2nd infra ticket
  appears (token→cron delivery, rotation, a 2nd SA).
- **SA token stored in the root/admin vault, NOT `coga-recurring`.** The token is
  the *key* that unlocks the vault, not a payload inside it. Storing it in the
  vault it reads is (a) circular — it can never be an `op://` ref (it's what op
  needs to resolve refs), so it can't be read from the vault it protects; and
  (b) a privilege-layering violation — the key must live above the box it opens.
  It's a human-managed credential, delivered into the cron/systemd env by hand.

### Progress
- **2026-07-19:** SA `coga-recurring-sa` created and scoped to the
  `coga-recurring` vault. SA token saved to the root/admin vault (per decision
  above). Still to do: create the vault items, mint/deliver the token for
  testing, and run the clean-env `coga secret get` proof.

### Open
- **`OP_SERVICE_ACCOUNT_TOKEN` delivery for the eventual cron run.** The token
  can't be an `op://` ref (it's what unlocks op), so it must be exported in the
  cron/systemd environment. Premature to solve now (nothing recurring yet) —
  belongs to the "make the USPTO job recurring" ticket when that exists. For
  manual testing today: export it in your shell.
- Whether the USPTO sync vs. sweep is one ticket or two — your domain call.
