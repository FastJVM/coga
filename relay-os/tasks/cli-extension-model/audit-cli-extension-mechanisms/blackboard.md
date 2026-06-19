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
