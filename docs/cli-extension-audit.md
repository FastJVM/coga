# CLI extension mechanisms — audit

Ticket 1 of the `cli-alias-line/` line. This is the verified reference that
tickets 2 (`add-recurring-launch-aliases`) and 3 (`propose-declarative-shim-mechanism`)
consume — so its classification has to be right, not assumed.

**Home: `docs/` (evidence), paired with a context (contract).** This doc is the
verb-by-verb *evidence* — design/audit rationale for the alias-line work, not a
rule an agent follows at launch. The durable *rule* it produced — the four-tier
extension model — lives as the `relay/extension-model` context
(`relay-os/contexts/relay/extension-model/SKILL.md`), authored project-local
(sibling to `relay/architecture`/`relay/codebase`), so no bundled-battery
dual-copy sync is incurred. The split mirrors `docs/vision.md` (rationale) vs
`relay/principles` (contract). The operator command reference stays where it is,
the `relay/cli` *context*. Read this for the worked classification; read
`relay/extension-model` for the rule.

## The three extension mechanisms

1. **Pure aliases** — argv rewrites in `_DEFAULT_ALIASES` (shipped to every
   repo) merged with user `[aliases]` from `relay.toml`, user key winning
   (`src/relay/cli.py:125`, `:237`). An alias is rewritten in `main()`
   *before* Typer dispatches (`cli.py:247-254`): `sys.argv` becomes
   `expansion + rest`. There is **no post-dispatch hook**. `_validate_aliases`
   (`cli.py:137-169`) rejects any alias whose name collides with a built-in or
   whose first expansion token isn't a known built-in, and soft-drops the
   legacy `create = "launch bootstrap/ticket"` line.

2. **Built-in commands** — `src/relay/commands/*.py`, registered in
   `cli.py:74-93`. These hold real pre/post logic.

3. **Launch shims / recurring launches** — tickets at
   `relay-os/bootstrap/<name>/ticket.md` (stateless shims) and templates at
   `relay-os/recurring/<name>/` launched via `recurring launch <name>`. These
   are the only place pure passthroughs actually live.

## The rule

> An alias is a pure argv rewrite with **no after-hook**. Anything that
> **drafts-on-the-fly**, **validates after the agent exits**, **git-syncs
> changed files**, or **guards a TTY** cannot be an alias — it needs a
> built-in.

`relay ticket` is the standing proof: it was promoted *out of* the old
`create = "launch bootstrap/ticket"` alias into a built-in precisely because it
drafts a ticket on the fly, validates the authored ticket after the agent
exits, git-syncs changed `tasks/`/`contexts/`/`skills/`, and enforces a TTY —
none of which an argv rewrite can express.

The structural consequence: **aliases can only ever capture a `launch X` or
`recurring launch X` shape, and only when X needs no pre/post logic.** Every
existing default alias is exactly that — `chat` → `launch bootstrap/orient`,
`dream` → `recurring launch dream`, `build` → `launch relay-build`. So the
hunt for new alias candidates is entirely within the shim / recurring-launch
space; no top-level verb is a hidden passthrough.

## Classification table

### CLI verbs (built-in commands)

| Verb | Mechanism | Alias-able? | Why |
|------|-----------|-------------|-----|
| `init` | built-in | No | Scaffolds/refreshes `relay-os/`, clones upstream, installs venv deps. Heavy side effects. |
| `create` / `draft` | built-in | No | Scaffolds a `draft` ticket dir + posts `✨` to Slack + post-write validate. |
| `ticket` | built-in | No | **Canonical proof.** Drafts-on-fly, validates after agent exits, git-syncs, TTY guard. |
| `project` | built-in | No | Interview → scaffold many drafts → post-validate; TTY guard. |
| `launch` | built-in | No | Prompt composition, freshness/merge auto-bump check, supervisor loop, status flip. |
| `status` | built-in | No | Reads tree + renders tables. Logic, not a passthrough to another command. |
| `show` | built-in | No | Reads + Rich-renders ticket/blackboard/log. |
| `bump` | built-in | No | Advances `step:`, appends `log.md`, post-write validate. |
| `automerge` | built-in | No | `gh pr view` per ticket + conditional bump + distinct Slack line. (See gotcha.) |
| `delete` | built-in | No | Resolves slug → runs `bootstrap/delete-task` skill with injected env. Thin, but resolves + executes a script. |
| `retire` | built-in | No | Scaffolds a one-shot `retire-<slug>` task straight to `active` + launches it. |
| `panic` | built-in | No | Writes blackboard marker + Slack + non-zero exit. |
| `slack` | built-in | No | Posts FYI to Slack. |
| `digest` | built-in | No | Spool read → git fetch → render → post → state update. (See digest disambiguation.) |
| `validate` | built-in | No | Static repo/config diagnostic, `--fix` creates missing files. |
| `skill` (group) | built-in | No | `gh skill` wrapper: install/update/remove/status, provenance, digests. |
| `mark` (group) | built-in | No | Status transitions + Slack + workflow gating + post-write validate. |
| `recurring` (group) | built-in | No | Schedule scan, get-or-create, sequential launch, dedup high-water mark. |
| `secret` (group) | built-in | No | Secret resolution/inspection. |

**No CLI verb is an alias-able pure passthrough.** Each is its own
implementation, not a fixed rewrite to another command.

### Bootstrap shims (`relay-os/bootstrap/<name>/ticket.md`)

| Shim | Mechanism today | Alias-able? | Why |
|------|-----------------|-------------|-----|
| `orient` | `chat` default alias → `launch bootstrap/orient` | Yes — already aliased | Pure `launch bootstrap/orient`; no pre/post logic. |
| `ticket` | `relay ticket` built-in | No | The shim exists, but authoring needs draft-on-fly / post-exit validate / git-sync / TTY. |
| `project` | `relay project` built-in | No | Interview + multi-draft scaffold + TTY guard; not a passthrough. |

Only `orient`, `project`, `ticket` are shims (`resolve_bootstrap`); `orient` is
already the `chat` alias and the other two need built-ins. **No un-aliased
shim passthrough remains.**

### Recurring launches (`recurring launch <name>`)

| Template | Mode | Mechanism today | Alias-able? | Why |
|----------|------|-----------------|-------------|-----|
| `dream` | interactive | `dream` default alias → `recurring launch dream` | Yes — already aliased | Pure passthrough. |
| `skill-update` | script | none | **Yes — un-aliased candidate** | Pure `recurring launch skill-update`; no pre/post logic. |
| `autoclose-merged` | script | none | **Yes — un-aliased candidate** | Pure `recurring launch autoclose-merged`; no pre/post logic. (Watch the naming gotcha.) |
| `digest` | script | name occupied by `relay digest` built-in | **No — disqualified by name collision** | `recurring launch digest` *is* a pure passthrough, but the natural alias name `digest` is already a built-in (a different operation). See below. |

(`_rem` and `_template` are `_`-prefixed scaffolding that `relay recurring`
skips — not launchable templates.)

## The concrete finding (verified, not assumed)

**The only un-aliased pure passthroughs available to alias are `skill-update`
and `autoclose-merged`** (both recurring launches). Verified against the code:
`_DEFAULT_ALIASES` already covers `dream`; the three bootstrap shims are either
aliased (`orient`/`chat`) or backed by a logic-bearing built-in
(`ticket`, `project`); and every CLI verb has pre/post logic. That leaves the
two script recurring templates with no shorthand. **This is what tickets 2 and
3 are built on.**

### The third candidate, and why it's disqualified

The ticket asked me to record any third candidate the audit surfaced or
disqualified. There is one: **`digest`**.

`recurring launch digest` is, mechanically, just as pure a passthrough as
`skill-update` and `autoclose-merged`. But it **cannot be aliased under its
natural name**, because `digest` is already a built-in command — and crucially
that built-in is a *different operation*:

- **`relay digest`** (built-in, `src/relay/commands/digest.py`) is the
  **consumer** half of the daily-digest pipeline: read the spool → fetch
  `origin/main` → render Done + Also-merged → post via webhook → empty the
  spool → record the git high-water mark. It is what the digest recurring
  task's `digest/post` **script step runs**.
- **`recurring launch digest`** would *scaffold and launch the recurring
  digest task* — a launch wrapper, not the post logic.

`_validate_aliases` would reject a `digest` alias outright (name collides with
a built-in), so it is disqualified by **name collision**, not by needing
pre/post logic. Tickets 2/3 should **not** attempt to alias `digest`; the
pure-passthrough set for aliasing is exactly the two named above.

## Gotchas

- **`autoclose` (sweep) vs `automerge` (manual) — and they share a module.**
  `relay automerge` (built-in) and the `autoclose-merged` recurring sweep are
  closely related, not unrelated: the sweep step's skill `relay/autoclose/sweep`
  calls `relay.automerge.auto_bump_merged`, and the built-in `relay automerge`
  is the manual surface over the same `relay.automerge` module. Both bump
  final-step / workflow-less tickets whose linked PR has merged — one on a
  schedule, one by hand. The names are one keystroke apart and easy to confuse.
  Ticket 2 should pick the `autoclose-merged` short-alias spelling
  deliberately (e.g. `autoclose`) with this proximity in mind.

- **`bootstrap/import` and `bootstrap/delete-task` are *skills*, not launch
  shims.** Neither has a `ticket.md`, so neither is a `resolve_bootstrap`
  target and neither can be an alias. `bootstrap/delete-task` is the single
  implementation behind `relay delete` (also runnable as a `mode: script`
  step); `bootstrap/import` is the judgment layer used during ticket authoring,
  not a launchable thing. Do not mistake a `bootstrap/skills/...` path for an
  aliasable shim.

- **`_DEFAULT_ALIASES` already ships three, not two.** `chat`, `dream`, **and
  `build`** (`build` → `launch relay-build`). The `relay/cli` context's
  Aliases section still documents only `chat` + `dream` — pre-existing doc
  drift, out of scope for this ticket but worth a follow-up.

## Architecture: how far the ticket model reaches

The flat "alias-able? yes/no" framing above is too coarse — it hides that
"needs logic" does **not** imply "needs a hand-written built-in." Logic can live
as skills in a workflow (`autoclose-merged/sweep` and `digest/post` already
prove command-grade logic runs fine as `mode: script` steps). The real surface
is a four-tier spectrum, ordered by machinery required — reach for the lowest
tier that can express the behavior:

1. **Pure alias** — argv rewrite, no hook on either side, can't create a ticket.
2. **Declarative shim** — `arg → create-draft-with-workflow → launch`. The one
   thing an alias can't do: materialize a ticket from a CLI argument. *Does not
   exist yet* — it's what ticket 3 proposes.
3. **Workflow** — logic on an existing ticket as script/interactive/mixed steps.
   Deterministic pre/post work → script steps; agent-facing process →
   interactive steps.
4. **Built-in** — irreducible Python: acts before a ticket exists, runs outside
   the model, or needs atomicity the workflow machinery can't give.

The tier isn't a matter of taste — it falls out of **determinism × statefulness
× when-it-runs**. *When* relative to a ticket (before it exists / on it / after
an agent exits), whether the work is *deterministic* (script-safe) or
*judgment-bearing* (must be an agent step — never relocate deterministic logic
*into* an agent step), and whether it needs *cross-cutting state or atomicity*
(tier 4).

**Most current built-ins are fused tiers, not irreducible kernel.** `relay
ticket` is the worked example: its authoring conversation is a tier-3
interactive step (the `bootstrap/ticket` shim already), its post-exit validate +
git-sync is a tier-3 script step (same shape as the autoclose sweep), and only
its `arg → draft` bootstrapping (`ticket.py:99-127`) is irreducible — a tier-2
residue. When tier 2 exists, `ticket` collapses to a shim + a mixed workflow
with zero hand-written command logic. `project` and `retire` share that residue.

**The floor — what genuinely can't be a ticket:** pre-ticket bootstrapping
(the tier-2 residue, until tier 2 exists), repo scaffolding (`init`), read-only
diagnostics/rendering (`status`/`show`/`validate` — principle 6 forbids them
mutating), and the kernel chokepoints themselves (`launch`/compose, `bump`,
`mark`, secrets, git, notify). Adopt the microkernel as far as the ticket model
reaches; keep a small built-in floor for the rest.

**Guardrail for ticket 3:** the tier-2 shim mechanism earns its place only while
it expresses the single fixed shape `arg → draft+workflow → launch`. The moment
it grows conditionals or computed args it becomes a mini-DSL in `relay.toml` — a
worse Typer, trading a legible built-in for an opaque config language against the
legibility non-negotiable. Branching logic belongs in a tier-3 skill, not shim
config.

The ratified rule lives in the `relay/extension-model` context; this section is
the audit's path to it.

## Source references

- Alias mechanism + validation: `src/relay/cli.py:125` (`_DEFAULT_ALIASES`),
  `:137-169` (`_validate_aliases`), `:247-254` (argv rewrite in `main()`),
  `:99-105` (`_BUILTIN_COMMANDS`).
- Command registration: `src/relay/cli.py:74-93`.
- `relay ticket` promotion rationale: `src/relay/commands/ticket.py`.
- digest consumer: `src/relay/commands/digest.py`.
- autoclose sweep ↔ automerge module: `relay-os/workflows/autoclose-merged/sweep.md`,
  `relay.automerge.auto_bump_merged`.
- Shims: `relay-os/bootstrap/{orient,project,ticket}/ticket.md`.
- Recurring templates: `relay-os/recurring/{autoclose-merged,digest,dream,skill-update}/`.
- Alias test coverage (not `relay validate`): `tests/test_aliases.py`.
