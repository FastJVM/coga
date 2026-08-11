---
slug: service-account-scoping-single-vault-rule-conflict
title: 'Service account scoping: single-vault rule conflicts with trust-tiered vaults'
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
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

- Distinct from `secrets-instructions-correction`, which is about the *shape*
  of the `secrets:` frontmatter (list of single-key entries, not a mapping).
  This ticket is about which vaults one credential may span.
- Raised from `FastJVM/admin` by Zach, 2026-08-11.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
