# CLI extension mechanisms — audit

The foundational audit of the `cli-extension-model/` line. This is the verified
reference the other tickets in the line (`add-recurring-launch-aliases`,
`move-command-logic-to-tickets`, `design-external-script-service-mechanism`)
consume — so its classification has to be right, not assumed.

**Home: `docs/` (evidence), paired with a context (contract).** This doc is the
verb-by-verb *evidence* — design/audit rationale for the cli-extension-model work,
not a rule an agent follows at launch. The durable *rule* it produced — the
three-homes extension model — lives as the `relay/extension-model` context
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
| `launch` | built-in | No | Prompt composition, supervisor loop, status flip. |
| `status` | built-in | No | Reads tree + renders tables. Logic, not a passthrough to another command. |
| `show` | built-in | No | Reads + Rich-renders ticket/blackboard/log. |
| `bump` | built-in | No | Advances `step:`, appends `log.md`, post-write validate. |
| `automerge` | ~~built-in~~ retired | — | Removed; merged-ticket auto-close is now solely the `autoclose-merged` recurring sweep (`relay/autoclose/sweep` skill → `relay.autoclose.sweep_merged`). (See gotcha.) |
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

- **Merged-ticket auto-close has a single surface now.** The standalone
  `relay automerge` command has been retired: the `autoclose-merged` recurring
  sweep is the sole trigger. Its skill `relay/autoclose/sweep` calls
  `relay.autoclose.sweep_merged` (renamed from `relay.automerge.auto_bump_merged`),
  which bumps final-step / workflow-less tickets whose linked PR has merged.
  Historical note: this used to be two surfaces (a manual command and the
  sweep) over the same module, one keystroke apart and easy to confuse — that
  ambiguity is what the retirement removed.

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
prove command-grade logic runs fine as `mode: script` steps). The refined
conclusion: the surface collapses to **three homes for logic, plus sugar**.

1. **Kernel** — small tested Python that can't be anything else.
2. **Tickets / workflows** — *stateful, reviewable* work as skills / `mode: script`
   steps on a ticket.
3. **External scripts / tools** — *stateless, parameterized* invocations. Two kinds:
   an **external tool** Relay shells out to (`gh`, `op`, `git` — exists, no design),
   and a **Relay-authored external script / service** that lives outside both kernel
   and tickets — a *design target* (no mechanism today; sibling of the tier-2 shim).
4. **Aliases** are not a home — just argv sugar pointing at one of the three.

**The home falls out of the shape, not taste** — four questions: is it a fixed
argv rewrite (alias)? is it a stateless parameterized call (command/external)? is
it stateful reviewable work (ticket)? is it regress/bootstrap-locked or a
mid-flight trust hook (kernel)?

**The kernel is `launch` and its dependency closure** — not a taxonomy. It is
`launch`/compose plus everything `launch` calls or depends on mid-flight (the
`mark`/`bump` state-writes, secret injection, skill verify-at-compose (not yet
built), notify) and the `create` primitive + fresh `init` that must precede a
launch. The test for any
command: does `launch` call it *while running* (kernel), or does a human/cron call
it *to start* a launch (movable)? Nothing else is kernel.

**Most current built-ins are not kernel — they're fused or already external.**
`automerge`/`digest`/`delete` already run as a sweep skill / post step /
delete-task skill. `relay ticket` is the worked fused case: its authoring
conversation is a workflow interactive step (the `bootstrap/ticket` shim already),
its post-exit validate + git-sync is a script step (same shape as the autoclose
sweep), and only its `arg → draft` head (`ticket.py:99-127`) is irreducible — the
tier-2 residue. When the tier-2 shim exists, `ticket` collapses to a shim + a mixed
workflow with zero hand-written command logic. `project` and `retire` share that
residue.

**Ticket vs. command is decided by statefulness, not parameters.** Both can take
arguments; the question is whether the operation is a stateful reviewable unit of
work (`retire` → a retire task) or a stateless one-shot (`skill install`,
`secret get`, `show` → a command). Parameters are legal on a ticket *only when
materialized into its files at creation* (`arg → draft`); transient launch-time
params are forbidden because they break "the prompt is a pure function of the
files on disk" and are the seed of a config DSL.

**Trust boundaries straddle kernel and external** — acquire outside, verify
inside. `gh skill` and `op`/`env` acquire; compose-verify and launch-inject are
the kernel hooks. So `skill install`/`secret get` are external/command; only the
verify/inject hooks are kernel. Secret *values* never flow through the legible
ticket/prompt/git machinery.

**Guardrails:** (1) *No worse Typer* — no transient launch params, and the tier-2
shim stays the single fixed shape `arg → draft+workflow → launch`; conditionals or
computed args make it an illegible `relay.toml` DSL. (2) *No inversion* —
relocating logic out of the kernel moves the substance unchanged (tested
`mode: script` Python), never rewrites a deterministic check as agent judgment.

The ratified rule lives in the `relay/extension-model` context; this section is
the audit's path to it.

## Source references

- Alias mechanism + validation: `src/relay/cli.py:125` (`_DEFAULT_ALIASES`),
  `:137-169` (`_validate_aliases`), `:247-254` (argv rewrite in `main()`),
  `:99-105` (`_BUILTIN_COMMANDS`).
- Command registration: `src/relay/cli.py:74-93`.
- `relay ticket` promotion rationale: `src/relay/commands/ticket.py`.
- digest consumer: `src/relay/commands/digest.py`.
- autoclose sweep + module: `relay-os/workflows/autoclose-merged/sweep.md`,
  `relay.autoclose.sweep_merged`.
- Shims: `relay-os/bootstrap/{orient,project,ticket}/ticket.md`.
- Recurring templates: `relay-os/recurring/{autoclose-merged,digest,dream,skill-update}/`.
- Alias test coverage (not `relay validate`): `tests/test_aliases.py`.
