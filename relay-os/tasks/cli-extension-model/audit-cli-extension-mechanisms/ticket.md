---
slug: cli-extension-model/audit-cli-extension-mechanisms
title: Audit CLI extension mechanisms
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/architecture
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
---

## Description

**The foundational ticket in `cli-extension-model/`. Run this first — the other
tickets in the line consume its output.**

Audit Relay's three CLI extension mechanisms and classify every command so
it's clear which ones could be cheap aliases and which must stay built-ins:

- **pure aliases** — argv rewrites in `_DEFAULT_ALIASES` / `[aliases]`
  (`src/relay/cli.py`)
- **built-in commands** — `src/relay/commands/*.py` registered in `cli.py`
- **launch shims / recurring launches** — `relay-os/bootstrap/<name>/` and
  `relay-os/recurring/<name>/`

For every current CLI verb, bootstrap shim, and recurring launch, classify it
as *alias-able* (a pure passthrough) or *needs-a-built-in* (requires pre/post
logic), with the reason. State the rule plainly: an alias is a pure argv
rewrite with **no after-hook**, so anything that drafts-on-the-fly, validates
after the agent exits, git-syncs, or guards a TTY cannot be an alias.

Deliverable: a committed markdown audit doc (pick a sensible home — a
`relay/cli`-style context under `relay-os/contexts/`, or `docs/`; decide and
say why in the doc). The doc must include:

1. The classification table (verb → mechanism → alias-able? → why).
2. The expected concrete finding — that the only un-aliased *pure passthroughs*
   are `skill-update` and `autoclose-merged` (recurring launches) — **verified,
   not assumed**. If the audit surfaces a third candidate or disqualifies one,
   record that; tickets 2 and 3 depend on this being right.
3. The gotchas: `bootstrap/import` and `bootstrap/delete-task` are *skills*,
   not launch shims, so they can't be aliases; and the `autoclose` (sweep
   merged PRs) vs `automerge` (mark a merged task done) naming proximity.

Done = the audit doc is committed and its classification + the
pure-passthrough finding are verified against the actual code.

## Context

Reconnaissance already done during ticket authoring (verify, don't trust):

- **Alias mechanism** — `src/relay/cli.py`: `_DEFAULT_ALIASES` (shipped to every
  repo) merged with user `[aliases]` from `relay.toml` (user key wins). An alias
  is a pure argv rewrite (`expansion + rest`) done in `main()` *before* Typer
  dispatches (lines ~242–251) — there is no post-dispatch hook. `_validate_aliases`
  (lines ~132–165) rejects aliases that collide with `_BUILTIN_COMMANDS` or expand
  to unknown targets, and soft-drops the legacy `create = "launch bootstrap/ticket"`.
  Current defaults: `chat` → `launch bootstrap/orient`, `dream` →
  `recurring launch dream`.
- **`relay ticket` is the proof the rule matters** — `src/relay/commands/ticket.py`
  (~320 lines) was promoted *from* the `create` alias to a built-in because it
  drafts-on-the-fly, validates the authored ticket after the agent exits,
  git-syncs changed `tasks/contexts/skills`, and enforces a TTY. None of that is
  expressible as an argv rewrite.
- **Launch shims** are tickets at `relay-os/bootstrap/<name>/ticket.md`
  (`resolve_bootstrap`). Only `orient`, `project`, `ticket` exist — `orient` is
  `chat`, `project` is a built-in, `ticket` is a built-in. No new bootstrap-shim
  aliases available.
- **Recurring launches** run via `recurring launch <name>` from
  `relay-os/recurring/<name>/`. Real ones: `autoclose-merged`, `digest`, `dream`,
  `skill-update`. `digest` is a built-in, `dream` is aliased → leaving
  `skill-update` and `autoclose-merged`.
- **Tests/sync** — alias coverage lives in `tests/test_aliases.py` (a
  `_DEFAULT_ALIASES` round-trip test ~line 209), NOT `relay validate`. If the doc
  lands as a shipped relay context, keep the live `relay-os/` and packaged
  `src/relay/resources/templates/relay-os/` copies in sync (CLAUDE.md).

**Out of scope:** shipping the aliases (that's ticket 2,
`add-recurring-launch-aliases`) and building the declarative-shim mechanism
(that's the follow-up the ticket 3 proposal sets up). This ticket only audits
and documents.

<!-- relay:blackboard -->

# Audit CLI extension mechanisms — blackboard

## Plan
Single-step `direct/body` task. Verify the ticket's reconnaissance against the
actual code, then commit a markdown audit doc classifying every CLI verb,
bootstrap shim, and recurring launch as alias-able vs needs-a-built-in.

## Doc home decision
`docs/cli-extension-audit.md`. Reasoning: this is design/audit rationale that
feeds the 3-ticket alias line (tickets 2 + 3 consume it), not behavioral domain
knowledge an oriented agent needs composed into its prompt at launch. The
operator reference already exists as the `relay/cli` *context*
(`bootstrap/contexts/relay/cli`). Shipping a second CLI **context** would also
force the live + packaged dual-copy sync burden (CLAUDE.md) for a doc whose
audience is the alias-line work, not launched agents. `docs/` is the right home.

## Verified findings (code-checked, not trusted from recon)

- `_DEFAULT_ALIASES` (src/relay/cli.py:125) ships THREE defaults now, not two:
  `chat` → `launch bootstrap/orient`, `dream` → `recurring launch dream`,
  **`build` → `launch relay-build`**. Recon only listed chat + dream. The
  `relay/cli` context (bootstrap copy) also still documents only chat + dream —
  noting as drift, out of scope to fix here.
- Alias mechanism = pure argv rewrite in `main()` (cli.py:247-254), before
  Typer dispatch. No post-dispatch hook. `_validate_aliases` (137-169) rejects
  collisions with `_BUILTIN_COMMANDS` and unknown targets; soft-drops legacy
  `create = "launch bootstrap/ticket"`.
- Built-in commands registered cli.py:74-93: init, create, draft, ticket,
  project, launch, status, show, bump, automerge, delete, retire, panic, slack,
  digest, validate + groups skill, mark, recurring, secret.
- Bootstrap shims (have ticket.md): orient, project, ticket. orient = `chat`
  alias. project + ticket each have a built-in command (NOT pure passthroughs —
  draft-on-fly / post-exit validate / git-sync / TTY guard).
- `bootstrap/import` and `bootstrap/delete-task` are SKILLS (no ticket.md), not
  shims → cannot be aliases. delete-task is wrapped by `relay delete`; import is
  the judgment layer used during ticket authoring.
- Recurring templates (non-`_`): autoclose-merged, digest, dream, skill-update
  (also `_rem`, `_template` scaffolding — skipped). All mode:script except dream
  (interactive).

## The pure-passthrough finding (verified)
The only un-aliased pure passthroughs *available to alias* are
**`skill-update`** and **`autoclose-merged`** (recurring launches). Confirmed.

REFINEMENT the ticket anticipated ("if the audit surfaces a third candidate or
disqualifies one, record that"): `recurring launch digest` IS a pure passthrough
too, but the natural alias name `digest` is already a built-in command — and
that built-in is a *different operation* (the spool→git→post consumer script run
by the digest task's script step, src/relay/commands/digest.py), NOT a launch of
the recurring task. So digest is a third candidate **disqualified by name
collision**, not by needing pre/post logic. Tickets 2/3 should not try to alias
`digest`.

## Gotchas confirmed
- `automerge` (built-in, manual ticket-bump) vs `autoclose-merged`/`autoclose`
  (recurring sweep). VERIFIED they share `relay.automerge`: the sweep step's
  skill `relay/autoclose/sweep` calls `relay.automerge.auto_bump_merged`; the
  built-in `relay automerge` is the manual surface over the same module. Name
  proximity is a real footgun for ticket 2's short-alias choice.
- import / delete-task are skills, not shims.

## Architecture pivot (human-directed, in session)
Discussion with the human upgraded the binary "alias vs built-in" framing into a
4-tier extension spectrum (microkernel-vs-mix). Tiers: (1) pure alias, (2)
declarative shim [doesn't exist — ticket 3], (3) workflow [script/interactive/
mixed skill steps], (4) built-in [irreducible floor]. Tier chosen by
determinism × statefulness × when-it-runs. Most built-ins (ticket/project/retire)
are *fused* tiers; only their `arg→draft` bootstrapping is irreducible (= tier 2).
Floor = init, status/show/validate (read-only), launch/bump/mark/secrets/git/
notify kernel. Guardrail for ticket 3: shim stays `arg→draft+workflow→launch`
only, no DSL.

Decision (human-confirmed): authored this as a NEW project-local context
`relay-os/contexts/relay/extension-model/SKILL.md` (sibling to architecture/
codebase — NOT a bundled battery, so no force-add/dual-copy). Split: audit doc =
evidence, context = ratified contract (mirrors docs/vision.md vs relay/principles).
Folded the 4-tier section into docs/cli-extension-audit.md too.

## Tickets 2 & 3 (human asked — do we redo?)
NO redo. Ticket 2 (add 2 aliases, code/with-review) stays — it's tier-1 work,
independent. Ticket 3 (propose-declarative-shim, direct/body) gets a LIGHT
rescope (next, pending review): add relay/extension-model to its contexts + the
no-DSL guardrail. NOT done in this ticket.

## Out of scope (explicitly deferred)
"Redesign all commands+skills against the extension model" = a separate
relay-project-sized program, GATED on this context landing (it's the rubric).
Human kicks it off via `relay project` later. Not this ticket, not the alias line.

## Status
Phase 1 deliverables written: docs/cli-extension-audit.md (audit + 4-tier
section) + relay-os/contexts/relay/extension-model/SKILL.md. Next: validate,
branch, commit, push, open PR, relay mark done.
