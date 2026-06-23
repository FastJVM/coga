The blackboard is a notepad to be written to often as the human and agent works through a task.

## Tier-2 shim design (2026-06-23, zach + claude) — restating Nico's ticket spec

The "committed design" the Done= asks for. ELABORATES Nico's sketch in the ticket
body; does not change it. Scope: the GENERIC `arg → create-draft → launch`
mechanism. Greet-first is NOT here — Nico built it in PR #423 (see "Relationship").

### 1. The shim's declarative schema (Nico's sketch, verbatim)
```toml
[shims.ticket]
launch = "bootstrap/ticket"
draft_if_missing = true
validate_after = true
sync = ["tasks", "contexts", "skills"]
require_tty = true
```
Each field = one tested `ticket.py` behavior:
- `launch` — the authoring entry to launch. **Routes through `spawn_agent_session(...)`**,
  the single shared spawn path PR #423 built; per-command options
  (discussion / kickoff / secrets-env / prompt_suffix) are arguments to it.
- `draft_if_missing` — `create_draft(arg)` when arg isn't an existing ticket.
- `validate_after` — post-session `validate_task_dir` + the draft-must-have-a-workflow gate.
- `sync` — snapshot/diff/git-sync of tasks/contexts/skills.
- `require_tty` — the interactive-TTY check.

### 2. Dispatch — the cli.py around-hook
`cli.py main()` rewrites argv BEFORE Typer today — there is no after-hook. The shim
needs a real **around-hook**: for a shim-name command, resolve arg →
(draft_if_missing) → launch → validate_after + sync. This is the ONE new mechanism
Pass 2 builds.

### 3. Which commands migrate
`ticket`, then `project`, then `retire` — BUT see §4: only `ticket` fits cleanly.

### 4. What stays bespoke (analysis 2026-06-23, read ticket.py/project.py/retire.py)
The three "fused heads" LOOK alike but their `arg` means three different things, so
only ONE fits the shim's `arg → create-draft-from-arg → launch` shape:

| Command | the `arg` is… | creates… | fits `draft_if_missing`? |
|---|---|---|---|
| `ticket`  | the new title (or existing slug) | one draft, from the arg | YES — clean fit |
| `project` | a *seed* for a brainstorm | many drafts, by the *skill* | NO — shim creates nothing |
| `retire`  | an existing *done* task | a separate fixed-template wrapper task | NO — arg must exist |

Shared (→ runner / fields): config load, resolve target, TTY check (`require_tty`),
spawn (now `spawn_agent_session`, post-#423), post-validate (`validate_after`), `sync`.
Tier-3 skills (untouched): the `ticket`/`project` interviews, the `retro` skill.

Bespoke residue:
- `ticket`: ~none. Edit-existing status check + in_progress/done caution + workflow
  gate are deterministic → shared-runner Python / `validate_after`.
- `project`: the seed handling (appended to the prompt, NOT materialized — check vs
  the params-into-files rule), drafts created by the skill (`draft_if_missing` off),
  and it validates a new SET of drafts, not one target.
- `retire`: the "must exist + be done" precheck and the fixed-template wrapper-task
  create (not draft-from-arg).

**OPEN — for Nico:** the shim fits `ticket`; `project`/`retire` share only the outer
frame (resolve → [create *something*] → launch → validate/sync) and differ in the
"create" step. Either (a) keep the shim ONE fixed shape (= `ticket`'s) and let
`project`/`retire` keep their distinct create-logic as bespoke Python on the shared
frame, or (b) give the shim a flexible "create" step — which risks "no worse Typer".
The guardrail points at (a). His call.

### 5. Order (Nico's)
- **First (no new mechanism):** reads → stateless script shims
  (status / show / recurring list / skill status); `recurring` scan → Dream-shaped task.
- **Last (gated on the shim):** the fused heads — `ticket`, then `project` / `retire`.

### Guardrails (from relay/extension-model)
- **No inversion** — relocate the tested Python UNCHANGED; never rewrite a
  deterministic check as agent judgment.
- **No worse Typer** — keep the single fixed shape `arg → draft → launch`; no
  conditionals / computed args / validation in `relay.toml`.

### Relationship to greet-first / the launch mechanism (UPDATED post-PR #423)
Greet-first + the launch-consolidation are DONE by Nico in **PR #423**
(`agent-session-options`), which **supersedes #417** and **closes
`finish-relay-ticket-greet-first-land-pr-417`**. It routes `launch`/`ticket`/`project`
through ONE shared spawn, `spawn_agent_session(...)`, with per-command differences
(greet-first `kickoff="Begin"`, secrets-env, discussion, `project`'s seed via
`prompt_suffix`) as explicit arguments.

What this means here: #423 built the consolidated spawn path the shim's `launch` step
routes through — it touched only the SPAWN (compose → spawn → log), NOT the front
(`arg → create-draft`) or back (`validate/sync`) this shim owns. So the shim's scope
is unchanged and its launch dependency is now built. Greet-first is no longer in this
ticket's scope (the earlier "shim first → greet-first second" plan is moot).
