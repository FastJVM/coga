# CLI extension mechanisms — audit

The foundational audit of the `cli-extension-model/` line. This is the verified
reference the other tickets in the line (`add-recurring-launch-aliases`,
`move-command-logic-to-tickets`, `design-external-script-service-mechanism`)
consume — so its classification has to be right, not assumed.

**Home: `docs/` (evidence), paired with a context (contract).** This doc is the
verb-by-verb *evidence* — design/audit rationale for the cli-extension-model work,
not a rule an agent follows at launch. The durable *rule* it produced — the
three-homes extension model — lives as the `coga/extension-model` context
(`coga/contexts/coga/extension-model/SKILL.md`), authored project-local
(sibling to `coga/architecture`/`coga/codebase`), so no bundled-battery
dual-copy sync is incurred. The split mirrors `docs/vision.md` (rationale) vs
`coga/principles` (contract). The operator command reference stays where it is,
the `coga/cli` *context*. Read this for the worked classification; read
`coga/extension-model` for the rule.

## The three extension mechanisms

1. **Pure aliases** — argv rewrites in `DEFAULT_ALIASES` (shipped to every
   repo) merged with user `[aliases]` from `coga.toml`, user key winning.
   `src/coga/aliases.py` owns the defaults, built-in inventory, validation, and
   legacy migration; `src/coga/cli.py` registers placeholders and rewrites
   `sys.argv` to `expansion + rest` before Typer dispatches. There is **no
   post-dispatch hook**.

2. **Built-in command heads** — `src/coga/commands/*.py`, registered in
   `cli.py:74-93`. These hold the irreducible command-shaped parts: argument
   resolution, guards, and calls into kernel/script-shaped modules when an
   alias has no hook point.

3. **Bootstrap command tickets / recurring launches** — package-backed or
   repo-local tickets at `bootstrap/<name>/ticket.md` are stateless command
   definitions; templates at `coga/recurring/<name>/` are launched via
   `recurring launch <name>`. Script command tickets receive trailing
   arguments as `COGA_ARG_1..N` plus `COGA_ARGC`; agent command tickets receive
   an explicit `## Launch arguments` JSON array.

## The rule

> An alias is a pure argv rewrite with **no after-hook**. Its target may still
> carry logic — including a stateless command ticket — but the alias itself
> cannot draft, validate, sync, or own a lifecycle transition.

`coga ticket` is the standing proof: it was promoted *out of* the old
`create = "launch bootstrap/ticket"` alias into a built-in command head because
it drafts a ticket on the fly, validates the authored ticket after the agent
exits, git-syncs changed `tasks/`/`contexts/`/`skills/`, and enforces a TTY —
none of which an argv rewrite can express. The authoring interview itself is
the `bootstrap/ticket` launch target, and the post-exit validation/sync phase
now lives in `coga.authoring` plus the script-shaped `coga/ticket/finalize`
skill; the command remains only because the pre/post hook is irreducible.

The structural consequence: aliases may capture any fixed argv rewrite whose
first token is a real built-in. Current defaults cover bootstrap launches,
recurring launches, the `build` task, and the `megalaunch --pick` spelling.
Parameterized command tickets remain fixed alias targets because the caller's
remaining argv passes through unchanged.

## Classification table

### CLI verbs (built-in commands)

| Verb | Mechanism | Alias-able? | Why |
|------|-----------|-------------|-----|
| `init` | built-in | No | Scaffolds `coga/`, vendors the running CLI into `.coga/.venv`, installs venv deps. Heavy side effects. |
| `create` / `draft` | built-in | No | Scaffolds a raw `draft` ticket and validates it; raw creation is intentionally Slack-silent. |
| `ticket` | thin built-in head + `coga.authoring` finalize | No | **Canonical proof.** Drafts-on-fly, launches the authoring interview, then calls extracted validate/git-sync finalization; TTY guard. |
| `project` | built-in | No | Interview → scaffold many drafts → post-validate; TTY guard. |
| `launch` | built-in | No | Prompt composition, supervisor loop, status flip. |
| `status` | built-in | No | Reads tree + renders tables. Logic, not a passthrough to another command. |
| `show` | built-in | No | Reads + Rich-renders ticket/blackboard/log. |
| `bump` | built-in | No | Advances `step:`, appends `log.md`, post-write validate. |
| `automerge` | ~~built-in~~ retired | — | Removed; merged-ticket auto-close is now solely the `autoclose-merged` recurring sweep (`coga/autoclose/sweep` skill → `coga.autoclose.sweep_merged`). (See gotcha.) |
| `delete` | built-in | No | Resolves slug → runs `bootstrap/delete-task` skill with injected env. Thin, but resolves + executes a script. |
| `retire` | built-in | No | Scaffolds a one-shot `retire-<slug>` task straight to `active` + launches it. |
| `block` / `unblock` | built-in | No | Records/resolves concrete blocker asks, owns blocked-state transitions, syncs state, and notifies. |
| `slack` | built-in | No | Posts FYI to Slack. |
| `digest` | built-in | No | Spool read → git fetch → render → post → state update. (See digest disambiguation.) |
| `validate` | built-in | No | Static repo/config diagnostic, `--fix` creates missing files. |
| `skill` (group) | built-in | No | `gh skill` wrapper: install/update/remove/status, provenance, digests. |
| `mark` (group) | built-in | No | Status transitions + Slack + workflow gating + post-write validate. |
| `recurring` (group) | thin built-in scan head + `bootstrap/recurring-scan` / `coga.recurring_runner` | No | The public head owns flags/env; the extracted runner still does schedule scan, get-or-create, sequential launch, dedup high-water mark. |
| `secret` (group) | built-in | No | Secret resolution/inspection. |

**No CLI verb is an alias-able pure passthrough.** Each is its own
implementation, not a fixed rewrite to another command.

### Bootstrap Launch Tickets (`bootstrap/<name>/ticket.md` Package Resources)

| Bootstrap ticket | Mechanism today | Alias-able? | Why |
|------|-----------------|-------------|-----|
| `orient` | `chat` default alias → `launch bootstrap/orient` | Yes — already aliased | Pure `launch bootstrap/orient`; no pre/post logic. |
| `ticket` | `coga ticket` command head + `coga/ticket/finalize` | No | The bootstrap ticket exists, but authoring needs draft-on-fly / post-exit validate / git-sync / TTY. The validate/sync substance is script-shaped, not an alias hook. |
| `project` | `coga project` built-in | No | Interview + multi-draft scaffold + TTY guard; not a passthrough. |
| `recurring-scan` | `coga recurring` command head + `coga.recurring_runner` | No | The bootstrap script target exists, but the public command parses `--interactive` / `--force` and passes them through an explicit env contract before launch; `--all <path>` dispatches that normal command across discovered repos. |
| `browser-automation` | unaliased `launch bootstrap/browser-automation` | Not currently | Intentional agent-backed orchestration entry point; it remains available through its full launch spelling. |
| `open-pr` | `open-pr` default alias → `launch bootstrap/open-pr` | Yes — already aliased | Stateless script command ticket; the target task ref reaches `COGA_ARG_1`. |
| `resolve-conflicts` | `resolve-conflicts` default alias → `launch bootstrap/resolve-conflicts` | Yes — already aliased | Stateless agent command ticket; its optional PR selector reaches the `## Launch arguments` block. |

The packaged bootstrap-ticket inventory is `orient`, `project`, `ticket`,
`recurring-scan`, `browser-automation`, `open-pr`, and `resolve-conflicts`.
Browser automation is the one intentionally unaliased launch target.

### Recurring launches (`recurring launch <name>`)

| Template | Mode | Mechanism today | Alias-able? | Why |
|----------|------|-----------------|-------------|-----|
| `dream` | interactive | `dream` default alias → `recurring launch dream` | Yes — already aliased | Pure passthrough. |
| `skill-update` | script | `skill-update` default alias → `recurring launch skill-update` | Yes — already aliased | Pure passthrough. |
| `autoclose-merged` | script | `autoclose` default alias → `recurring launch autoclose-merged` | Yes — already aliased | Pure passthrough under the shorter public name. |
| `digest` | script | name occupied by `coga digest` built-in | **No — disqualified by name collision** | `recurring launch digest` *is* a pure passthrough, but the natural alias name `digest` is already a built-in (a different operation). See below. |

(`_`-prefixed directories under `coga/recurring/` are skipped by
`coga recurring` — parked, not launchable, templates.)

## The concrete finding (verified, not assumed)

**One unaliased bootstrap launch target remains intentionally.**
`DEFAULT_ALIASES` covers `chat`, `dream`, `build`, `skill-update`,
`autoclose`, `pick`, `open-pr`, and `resolve-conflicts`.
`bootstrap/browser-automation` remains available only through its explicit
launch spelling; it is orchestration rather than a stable top-level verb.

### The third candidate, and why it's disqualified

The ticket asked me to record any third candidate the audit surfaced or
disqualified. There is one: **`digest`**.

`recurring launch digest` is, mechanically, just as pure a passthrough as
`skill-update` and `autoclose-merged`. But it **cannot be aliased under its
natural name**, because `digest` is already a built-in command — and crucially
that built-in is a *different operation*:

- **`coga digest`** (built-in, `src/coga/commands/digest.py`) is the
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
  `coga automerge` command has been retired: the `autoclose-merged` recurring
  sweep is the sole trigger. Its skill `coga/autoclose/sweep` calls
  `coga.autoclose.sweep_merged` (renamed from `coga.automerge.auto_bump_merged`),
  which bumps final-step / workflow-less tickets whose linked PR has merged.
  Historical note: this used to be two surfaces (a manual command and the
  sweep) over the same module, one keystroke apart and easy to confuse — that
  ambiguity is what the retirement removed.

- **`bootstrap/import` and `bootstrap/delete-task` are *skills*, not launch
  tickets.** Neither has a `ticket.md`, so neither is a `resolve_bootstrap`
  target and neither can be an alias. `bootstrap/delete-task` is the single
  implementation behind `coga delete` (also runnable as a script
  step); `bootstrap/import` is the judgment layer used during ticket authoring,
  not a launchable thing. Do not mistake a `bootstrap/skills/...` path for an
  aliasable bootstrap ticket.

- **`DEFAULT_ALIASES` ships eight.** `chat`, `dream`, `build`,
  `skill-update`, `autoclose`, `pick`, `open-pr`, and `resolve-conflicts`.
  The last two demonstrate script-backed and agent-backed command tickets.

## Architecture: how far the ticket model reaches

The flat "alias-able? yes/no" framing above is too coarse — it hides that
"needs logic" does **not** imply "needs a hand-written built-in." Logic can live
as skills in a workflow (`autoclose-merged/sweep` and `digest/post` already
prove command-grade logic runs fine as script steps). The refined
conclusion: the surface collapses to **three homes for logic, plus sugar**.

1. **Kernel** — small tested Python that can't be anything else.
2. **Tickets / workflows** — *stateful, reviewable* work as skills / script
   steps on a ticket.
3. **Stateless command tickets / external tools** — parameterized invocations
   with no per-run lifecycle. Coga-authored verbs use local-first bootstrap
   command tickets; existing third-party behavior stays in tools such as
   `gh`, `op`, and `git`.
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
delete-task skill. `coga ticket` is the worked collapsed case: its authoring
conversation is the `bootstrap/ticket` launch target already, its post-exit
validate + git-sync lives in `coga.authoring` and is exposed as the
`coga/ticket/finalize` script skill (same shape as the autoclose sweep), and the
`arg → draft` head in `commands/ticket.py` is irreducible. The command calls the
finalize module inline after the single-shot interview to preserve the stateless,
concurrent-safe bootstrap launch target; no generic shim or workflow-step state
was introduced. `project` and `retire` share that irreducible head.

**Ticket vs. command is decided by statefulness, not parameters.** Stateful
work materializes inputs into task files. Stateless command tickets accept
trailing launch arguments without creating run state: scripts receive
`COGA_ARG_1..N` / `COGA_ARGC`, while agent commands receive a JSON argument
block in the composed prompt.

**Trust boundaries straddle kernel and external** — acquire outside, verify
inside. `gh skill` and `op`/`env` acquire; compose-verify and launch-inject are
the kernel hooks. So `skill install`/`secret get` are external/command; only the
verify/inject hooks are kernel. Secret *values* never flow through the legible
ticket/prompt/git machinery.

**Guardrails:** (1) *No worse Typer* — aliases stay fixed argv rewrites and
command tickets own argument interpretation; conditionals or computed args in
`coga.toml` would make an illegible config DSL. (2) *No inversion* — relocating
logic out of the kernel moves the substance unchanged, never rewriting a
deterministic check as agent judgment.

The ratified rule lives in the `coga/extension-model` context; this section is
the audit's path to it.

## Source references

- Alias defaults, built-in inventory, validation, and legacy migration:
  `src/coga/aliases.py`.
- Alias registration and argv rewrite: `src/coga/cli.py`.
- Command registration: `src/coga/cli.py`.
- `coga ticket` promotion rationale: `src/coga/commands/ticket.py`.
- digest consumer: `src/coga/commands/digest.py`.
- autoclose sweep + module: `coga/workflows/autoclose-merged/sweep.md`,
  `coga.autoclose.sweep_merged`.
- Bootstrap tickets: package
  `bootstrap/{browser-automation,open-pr,orient,project,recurring-scan,resolve-conflicts,ticket}/ticket.md`.
- Recurring templates: `coga/recurring/{autoclose-merged,digest,dream,skill-update}/`.
- Alias test coverage (not `coga validate`): `tests/test_aliases.py`.
