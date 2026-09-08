---
slug: service-account-scoping-single-vault-rule-conflict
title: 'Service account scoping: single-vault rule conflicts with trust-tiered vaults'
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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

**Settled 2026-09-08** — the owner's answer is recorded under `## Context`: one
service account with one automation vault, plus a separate follow-up for
scrubbing the token before spawn. What remains is the doc edit.

## Context

### Decision (2026-09-08, owner)

Both open calls are settled. Neither matches the agent memo's recommendation
verbatim; the memo's option-1 proposal is superseded and archived on the
blackboard.

**1. Vault shape — one service account, one vault.** There will be exactly one
Coga repo backed by 1Password and exactly one read-only service account, and
that account is granted **one** automation vault. The other trust-named vaults
exist for human password/access management; the SA is never granted them, and
never the root-level vault that holds its own token.

So the single-vault sentence **stands** for the service account — the stated
security property is preserved and no vault-to-token routing is needed. What
was actually wrong is the adjacent implication that trust tiering describes the
*automation's* grant. It does not: here the tiers are a human-access taxonomy,
and the SA's blast radius is exactly its one vault. A ticket must not declare
`op://` refs outside that automation vault, because nothing will resolve them.

**2. Worker capability — scrub the token.** Coga should use
`OP_SERVICE_ACCOUNT_TOKEN` to resolve a ticket's declared refs and then remove
it before spawning the agent or recipe, so the child sees only the resolved
destination aliases. That makes `secrets:` a real capability bound rather than
an injection convenience. It is a code change to `config.build_launch_env()`
and belongs in its own ticket — **out of scope here**. That ticket now exists:
`scrub-the-service-account-token-from-the-launch-ch` (draft, `code/with-review`).
Until it lands, durable
docs must keep saying plainly that a launched worker inherits the token and can
read the whole vault regardless of what its ticket declared.

### What the doc step has to write

- `coga/contexts/coga/secrets/SKILL.md` is **repo-local only** — there is no
  packaged twin under `src/coga/resources/templates/`, so it is a single edit.
  `coga/contexts/coga/architecture/SKILL.md` does have a packaged twin and must
  be kept in sync if its "declaration, not a sandbox" wording is touched.
- Under `## The service account and its vault`, replace the block-quoted
  "Open decision — do not read a recommendation into the above" paragraph with
  the settled model: one SA, one automation vault, never the root-level vault.
- In the same section, the **Vault** bullet currently ends "Whether they also
  bound the *automation's* blast radius depends on how many vaults one account
  is granted." That hedge is now answered: they do not bound it because they
  are not granted to the SA at all. Trust-named vaults are a human access
  taxonomy; the SA's blast radius is its one automation vault.
- Keep the single-vault security claim, now true as stated, and keep the
  existing honest text about the token surviving into the child environment —
  the scrub is a future ticket, not current behavior.
- Fix the "Adding a headless secret" recipe, whose step 2 example ref and
  step 3 `coga secret get` verification both hardcode `op://coga-low-trust/...`.
  With one automation vault a tier-named example is misleading; its step 1
  ("Create the item in a vault based on the trust level") needs the same fix.

### Background: why two service accounts is not the escape hatch

`OP_SERVICE_ACCOUNT_TOKEN`
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

## The question — answered 2026-09-08

Which model does coga endorse? **Option 3, in the narrow form recorded under
`## Context`: one service account, one automation vault.** Options 1 and 2 are
kept below as the reasoning that was considered.

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

Option 2 was the only one that preserved the stated security property *while
keeping tiered automation vaults*, and the only one needing code. The owner
removed that premise instead: the automation only ever needs one vault, so
option 3 preserves the same property for free.

## Notes

- Distinct from `launch-activates-before-preflight` (was
  `secrets-instructions-correction`), which a malformed `secrets:` block only
  triggered — that ticket is about `coga launch` durably activating a draft
  before the preflights that refuse it. This ticket is about which vaults one
  credential may span.
- Raised from `FastJVM/admin` by Zach, 2026-08-11.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Current state (2026-09-08) — step 3 complete

Step 2 (`human-owns-and-finishes`) produced the decision; both calls are
recorded under `## Context` in the ticket body. Step 3 (`report-to-coga`) has
now landed the doc edit those decisions called for.

- **Vault shape:** one service account, one automation vault. Other
  trust-named vaults are human password/access only and are never granted to
  the SA. The single-vault security claim survives intact.
- **Worker capability:** scrub `OP_SERVICE_ACCOUNT_TOKEN` before spawn — agreed
  in principle, deferred to its own code ticket
  (`scrub-the-service-account-token-from-the-launch-ch`). Not this ticket's
  scope, and the doc still says plainly that a launched worker inherits the
  token.

## Step 3 report — what shipped

**Artifact:** `coga/contexts/coga/secrets/SKILL.md`, one file, repo-local only.
Confirmed by search that no packaged twin exists under
`src/coga/resources/templates/`, so no sync edit was needed.
`coga/contexts/coga/architecture/SKILL.md` was **not** touched — its
"declaration, not a sandbox" wording is still accurate under the settled model,
so its packaged twin needed no sync either.

Four changes, all inside `## The service account and its vault` and
`## Adding a headless secret`:

1. **Service account bullet** — restored the explicit security claim, now true
   as stated: read-only, *scoped to a single automation vault*; "a leaked token
   reads that one vault and nothing else."
2. **Vault bullet** — replaced the hedge ("Whether they also bound the
   automation's blast radius depends on how many vaults one account is
   granted") with the answer: trust tiers are a **human** access taxonomy and do
   not bound the automation's blast radius, because they are never granted to
   the SA at all.
3. **Open-decision block quote** — deleted, replaced by two paragraphs stating
   the settled model (one repo, one read-only SA, one automation vault, never
   the root-level vault; a ticket must not declare `op://` refs outside that
   vault because nothing resolves them) plus the irreversibility warning
   (1Password fixes vault access at creation, so a second vault is a migration
   — new account, rotated token, re-delivery to every machine and cron env).
4. **"Adding a headless secret" recipe** — step 1 now says to create the item in
   the automation vault and warns that an item filed in a human trust-named
   vault is unreadable to the SA; steps 2 and 3 replaced the misleading
   hardcoded `op://coga-low-trust/...` with `op://<automation-vault>/...`. No
   concrete vault name is recorded anywhere in the repo, so the placeholder
   matches the file's existing `<item>/<field>` style.

One wording tightening outside the checklist: the "Scoping bounds the grant,
not the process" paragraph said an inherited token lets an agent read "every
vault that service account can reach." Under the settled model that phrasing
implies a plurality that no longer exists, so it now reads "the whole
automation vault, regardless of which single item its ticket declared." The
honest inheritance claim itself is unchanged — the scrub is still a future
ticket, not current behavior.

**Verification:** `coga validate --json` — 45 issues, 4 errors, all four
pre-existing `unsynthesized-draft-blackboard` errors on unrelated `v2/` drafts.
No issue references the secrets context or this task. Also grepped the repo for
`coga-low-trust` and "Open decision": no remaining hits outside `coga/log.md`
history and an unrelated ticket's own section heading.

## Durable findings that survive the decision

**`build_launch_env()` does not scrub the SA token.**
`src/coga/config.py:build_launch_env()` starts from the full parent environment
and removes only variables named by ticket `env:` references. Nothing at the
launch, megalaunch, or recurring-recipe call sites removes
`OP_SERVICE_ACCOUNT_TOKEN` afterwards. A spawned agent or recipe can therefore
run `op` directly and read the whole automation vault even when its ticket
declares one secret. This is the basis of the deferred scrub ticket, and until
that lands the docs must not imply `secrets:` bounds a worker.

**1Password facts confirmed against current docs.** A service account may be
granted multiple vaults; its access and permissions are immutable after
creation; 1Password recommends one service account per purpose holding only the
vaults that purpose needs.

- <https://www.1password.dev/service-accounts/get-started>
- <https://www.1password.dev/get-started/secure-developers>

## Superseded designs

### 2026-08-15 — agent memo recommending option 1 (one SA spanning tiers)

Superseded 2026-09-08. The memo recommended endorsing option 1: one read-only
SA per Coga repo scoped to all and only the non-root vaults that repo's
headless work needs, with tiers demoted to classification-only and the honest
caveat that they do not contain a leaked SA token. Its reasoning was sound
given its premise — that the automation would need refs in more than one tier —
but the owner removed that premise: there is one Coga repo on 1Password, one
SA, and one automation vault, with the trust-named vaults reserved for human
access. Option 3 therefore preserves the original security property at no cost,
and the candidate wording the memo drafted ("A leaked token can read every
vault granted to that account") is not the wording to ship.

The memo's comparison table, which remains useful if the premise ever returns:

| Model | Works with today's one-token launch | SA-token blast radius | Operational/code cost | Future vault cost |
| --- | --- | --- | --- | --- |
| 1. One repo SA spanning tiers | Yes; proven in `FastJVM/admin` | Every automation vault granted to that SA | One credential; no routing code | New SA + token redistribution, because 1Password scope is immutable |
| 2. One SA per vault | No | One vault **only if** credentials and child environments are also isolated | Token mapping, per-ref selection, source-token scrubbing, config/docs/tests | Add one SA and mapping without rotating unrelated tiers |
| 3. One vault per repo | Yes | The repo vault | Simplest | Loses useful human-access and rotation separation |

A correct option-2 design would have needed per-reference token selection,
scrubbing of every token source before spawn, explicit behavior for cross-tier
tickets, and tests proving a low-tier worker cannot use a high-tier credential.
Vault-to-token mapping alone would not have helped: delivering every tier token
into one parent environment increases exposed credentials without containing
the worker.
