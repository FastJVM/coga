---
slug: service-account-scoping-single-vault-rule-conflict
title: 'Service account scoping: single-vault rule conflicts with trust-tiered vaults'
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/secrets
- coga/architecture
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
step: 2 (human-owns-and-finishes)
---

## Description

`coga/contexts/coga/secrets` states two rules that cannot both hold once a repo
keeps secrets in more than one vault. Which one wins is a design decision, not
a doc fix — hence a question rather than a patch.

From the same section:

> **Service account** — the headless 1Password identity. Authenticates via
> `OP_SERVICE_ACCOUNT_TOKEN`, read-only, **scoped to a single vault**. A leaked
> token can read that one vault and nothing else.

> **Vault** — the container the SA reads. Secrets will accrue in **vaults named
> by their trust level**.

Trust-tiered vaults imply a repo will eventually hold refs in more than one of
them. A service account scoped to a single vault cannot resolve those refs.

## Context

**Why two service accounts is not the escape hatch.** `OP_SERVICE_ACCOUNT_TOKEN`
is one environment variable, and `coga launch` resolves a ticket's `op://` refs
by shelling out to `op`, which reads that variable. Coga has no vault → token
mapping. So with two SAs:

- a ticket declaring refs in two tiers resolves one and fails the other;
- a single-tier ticket still fails whenever the profile exports the other SA's
  token;
- the operator cannot choose per invocation, because `coga launch` owns the
  invocation.

**And the choice is close to irreversible.** 1Password fixes a service
account's vault access **at creation** — there is no way to add a vault later.
Widening scope means a new account, a rotated token, and re-delivery to every
machine and cron environment. Whichever model coga endorses, a repo that
follows it and later outgrows it pays that cost.

## The worked example

`FastJVM/admin` hit this on 2026-08-11 and resolved it by diverging from the
single-vault rule. Its vaults are now `coga-low-trust` (Slack incoming
webhook), `coga-medium-trust` (no occupant yet), `coga-high-trust` (Brex user
token, which reads every company transaction) and `root-level` (the SA token
itself, human-only).

One service account, `coga-secrets`, reads all three trust vaults. Verified end
to end: `brex_missing_gl.py --dry-run` resolved its token through
`coga secret get` and reached the Brex API with nobody signed in.

Admin's own context records the cost of that choice explicitly, since the vault
names would otherwise imply a containment they do not provide:

> **Vaults classify, they do not contain.** One service account reads every
> vault the automation needs, so a leaked service-account token reaches all of
> them regardless of tiering. What the tiers buy is legible classification,
> separate *human* access grants, and independent rotation — not containment
> for the automation itself.

## The question

Which model does coga endorse?

1. **One SA per repo, spanning tiers** (what admin does). Tiers become
   classification and human-access boundaries, not blast-radius boundaries for
   the automation. The single-vault sentence in `coga/contexts/coga/secrets`
   gets rewritten.
2. **One SA per vault, strictly.** Then coga needs a vault → token mapping so a
   launch can pick the right credential per ref, and the docs should say that a
   ticket must not declare refs across tiers until it exists.
3. **Single vault per repo, no tiering.** Simplest, and consistent with the
   current sentence — but it drops the trust-level naming the same section
   recommends.

Option 2 is the only one that preserves the stated security property, and it is
the only one that needs code.

## Notes

- Distinct from `launch-activates-before-preflight` (was
  `secrets-instructions-correction`), which a malformed `secrets:` block only
  triggered — that ticket is about `coga launch` durably activating a draft
  before the preflights that refuse it. This ticket is about which vaults one
  credential may span.
- Raised from `FastJVM/admin` by Zach, 2026-08-11.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Agent draft — decision memo (2026-08-15)

### Proposed decision

Endorse **option 1 for v1**, stated as **one read-only service account per Coga
repo / automation purpose, scoped to all and only the non-root vaults that
repo's headless work needs**.

Keep trust-tiered vaults, but name their boundary honestly: they classify
sensitivity and provide separate human grants, audit surfaces, and rotation
units. They do **not** contain compromise of the repo service-account token.
The root-level vault that stores the SA token remains human-only and must never
be readable by that SA.

Do not add vault-to-token routing yet. Treat stronger per-tier isolation as a
separate execution-isolation design, not as a small extension of secret lookup.

### Why this is the v1 recommendation

| Model | Works with today's one-token launch | SA-token blast radius | Operational/code cost | Future vault cost |
| --- | --- | --- | --- | --- |
| 1. One repo SA spanning tiers | Yes; proven in `FastJVM/admin` | Every automation vault granted to that SA | One credential; no routing code | New SA + token redistribution, because 1Password scope is immutable |
| 2. One SA per vault | No | One vault **only if** credentials and child environments are also isolated | Token mapping, per-ref selection, source-token scrubbing, config/docs/tests | Add one SA and mapping without rotating unrelated tiers |
| 3. One vault per repo | Yes | The repo vault | Simplest | Loses useful human-access and rotation separation |

Option 1 matches the concrete operating need and Coga's current execution
boundary: one repo launcher with one ambient `OP_SERVICE_ACCOUNT_TOKEN`. It
also follows the current project-stage rule against adding a credential router
for a hypothetical boundary. Option 3 is simpler only by discarding benefits
the worked example already uses. Option 2 is defensible if cross-tier token
containment is a hard requirement, but then the current runtime model—not just
the wording—must change.

Current 1Password documentation supports the factual premises: a service
account may be granted selected **multiple** vaults, its access and permissions
are immutable after creation, and 1Password recommends one service account per
purpose with only the vaults that purpose needs:

- <https://www.1password.dev/service-accounts/get-started>
- <https://www.1password.dev/get-started/secure-developers>

### Important weak spot outside the stated three-way choice

`src/coga/config.py:build_launch_env()` starts from the full parent environment
and scrubs only variables named by ticket `env:` references. It does not scrub
`OP_SERVICE_ACCOUNT_TOKEN`. No later removal was found at the launch,
megalaunch, or recurring-recipe call sites. Consequently, a spawned agent or
recipe can invoke `op` directly with the repo SA and read any vault that SA can
read, even when the ticket declares only one secret.

That conflicts with `coga/architecture`'s statement that the ticket-level
`secrets:` list defines task capability. Before durable docs imply that
declared refs contain a worker, Coga should make one of these explicit:

1. **Recommended invariant:** Coga may use the SA token while resolving
   declared refs, but removes it before spawning the agent/recipe. The child
   receives only resolved aliases. This needs a focused follow-up code ticket,
   including an answer for nested Coga commands that may need notification
   credentials.
2. **Weaker documented model:** every worker inherits repo-wide 1Password
   authority, and `secrets:` controls convenience/injection rather than
   capability. This is consistent with current behavior but materially widens
   the trust boundary.

Vault-to-token mapping would not fix this by itself. If all tier tokens are
delivered into one parent environment and inherited by the child, mapping can
increase the number of exposed root credentials while providing no worker
containment. A correct option-2 design would need at least per-reference token
selection, scrubbing of every token source before spawn, explicit behavior for
cross-tier tickets, and tests proving a low-tier worker cannot use a high-tier
credential.

### Candidate durable wording if the human accepts option 1

> **Service account** — the headless 1Password identity. Authenticates via
> `OP_SERVICE_ACCOUNT_TOKEN` and is read-only. Use one service account per Coga
> repo / automation purpose by default, granting it only the vaults that
> purpose's headless work needs and never the root-level vault that stores its
> token. A leaked token can read every vault granted to that account.
>
> **Vaults** — containers named by trust level. For the repo service account,
> tiers classify secrets; they do not contain a leaked SA token. They still
> provide legible sensitivity, separate human access grants, audit boundaries,
> and independent secret rotation.

### Human judgment requested

Confirm or revise two decisions independently:

1. v1 identity model: option 1 (recommended) versus accepting the option-2
   implementation cost for genuine per-tier token containment.
2. worker capability model: scrub the raw SA token after resolution
   (recommended) versus explicitly granting every worker repo-wide vault
   access.

### Verification

- `git diff --check` passed.
- `coga validate --json` found no issue for this task. The repo-wide command
  still exits 1 on unrelated pre-existing `v2/` ticket errors (`missing-step`
  and `unsynthesized-draft-blackboard`); its other findings are warnings.
