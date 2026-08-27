---
slug: bumppy-requires-exactly-two-agents
title: Layer [agents.*] from coga.local.toml and resolve other-agent with 3+ agents
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

Zach hit two halves of the same wall adding a local-llm agent type. This ticket
fixes both, because neither half alone makes a third agent usable.

**Half one — you cannot declare a third agent locally.** `_parse_agents`
(`src/coga/config.py`) hard-rejects any `[agents.<name>]` table in
`coga.local.toml` with "coga.local.toml no longer supports [agents.<name>]
overrides". There is no way to add an agent type without committing it to
`coga.toml`. Make `[agents.*]` layer the way the rest of the config already
does: read `coga.toml`, overlay `coga.local.toml`, last writer wins, merged at
the **key** level.

**Half two — a third agent breaks every peer review.** `resolve_other_agent`
(`src/coga/bump.py`) resolves the `other-agent` role token by taking the single
`[agents.*]` entry that is not the ticket's own `agent:`, and raises
`AssigneeResolutionError` unless exactly one candidate remains. Three agents
means every `other-agent` resolution fails loud. Give the token an explicit way
to name the peer: an optional per-agent `peer` key, e.g.
`[agents.claude] peer = "codex"`. When the ticket's agent declares a `peer`,
resolution returns it; when it doesn't, fall back to today's exactly-one
inference, so two-agent repos keep working with no config change and no
migration.

These were originally two tickets. `parse-agents-rejects-cogalocaltoml` held
half one and is merged here by owner decision: both are the same report, both
are config-layer changes, and `peer` has to survive the local/shared merge that
half one introduces, so designing them apart risks a seam.

## Context

#### The bug is live, not hypothetical

The original report said nothing uses `other-agent` today. That is true only of
repo-local `coga/workflows/`. The bundled batteries do use it:

- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md` —
  `peer-review` step, `assignee: other-agent`. This is the default workflow for
  code changes in this repo, and this ticket's own workflow.
- `src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md` —
  same shape.

**61 files under `coga/tasks/` carry `assignee: other-agent` frozen into a
workflow snapshot** — 33 draft, 6 paused, 3 in_progress, 1 active, 1 blocked
(44 non-terminal), plus 13 done and 4 canceled. Role tokens resolve at bump
time against current config, not at freeze time, so the day a third
`[agents.*]` becomes loadable, those tickets fail on the bump into
`peer-review` — mid-workflow, after the implement step's work is already done.

`coga/coga.toml` declares exactly two agents (`[agents.claude]`,
`[agents.codex]`). That is the only reason this is not already broken, and half
one of this ticket removes that accidental protection — which is why both
halves ship together.

### Half one — layer `[agents.*]` from `coga.local.toml`

#### Where the behavior lives

- `_parse_agents(raw, local_raw)` in `src/coga/config.py`. It validates the
  shared tables, then loops `local_raw` only to re-raise the removed-key
  migration error, and finally raises unconditionally on any non-empty
  `local_raw`.
- Its single call site, already passing both tables.
- `_ALLOWED_LOCAL_SECTIONS` already contains `agents` — allowlisted purely so
  the tailored rejection fires instead of a generic unknown-key error. It stays.

#### Merge semantics

Overlay at the **key** level, not the table level. A local `[agents.claude]`
carrying only `cli` overrides `cli` and inherits `file`, `mode`, `name_flag`,
`session_id_flag`, `discussion`, `analyze` (and `peer`) from `coga.toml`.
Table-level replacement would make that snippet fail "agents.claude.file is
required", which is not what an override means.

This should make `_parse_agents` **shorter**, not longer: merge the raw dicts
per agent name first, then run the existing validation once over each merged
table. That deletes the trailing rejection and the duplicated
`_REMOVED_AGENT_KEYS` loop over `local_raw`.

Four details the naive merge gets wrong — each a decided requirement, not an
open question:

1. **Preserve declaration order.** `Config.default_agent()` returns
   `next(iter(self.agents))` and `tests/test_config.py` guards it. Merge shared
   names first in their `coga.toml` order, then append local-only names; never
   rebuild the dict from `local_raw` first or re-sort.
2. **Run the removed-key check before the required-key check** on the merged
   table. Today the local removed-key loop runs independently of `cli`/`file`,
   so a *local-only* agent carrying a stale `auto` still gets the migration
   error. Merge naively and it instead reports `agents.<name>.cli is required`.
   The existing fixture overrides a name that exists in shared, so it would
   still pass — this regression is invisible to the suite unless a test is
   added for it.
3. **Name the source file in the unknown-key error too.** `_reject_unknown_keys`
   is currently passed a bare `f"[agents.{name}]"` label. After merging, a typo
   in `coga.local.toml` would report with no file named. Track which file each
   rejected key came from and label it, matching the removed-key error.
4. **Keep a non-dict guard.** The existing `if not isinstance(data, Mapping):
   continue`. Without it, `agents.foo = "bar"` makes `"cli" not in "bar"` a
   substring test that succeeds into a nonsense `agents.foo.cli is required`.

Required keys (`cli`, `file`) are checked against the merged table, so a
local-only agent must supply both and a partial override need not.

#### Precedent

Same layering `[notification.slack].webhook` / `.important_webhook` already use
— local wins, no warning (`coga/contexts/coga/sync/SKILL.md`). Decided: **no**
provenance affordance. Do not add a `coga validate` report or a launch-time
notice about locally-defined agents; keep this a parser change.

`[layout]` is the counterexample and stays rejected in `coga.local.toml` —
where a repo keeps its prose is a fact about the repo. Agent types are a fact
about the machine (which CLI binaries are installed), so they layer.

#### Accepted tradeoff

A committed ticket's `agent: <name>` can now resolve to a different binary per
machine, and a local-only agent name only works on the machine that declares
it. That is the point of the change; do not litigate it in review.

### Half two — `peer` and `other-agent` resolution

#### Call sites

Four places resolve the token today; all four must keep working:

- `coga.bump.resolve_other_agent` — the resolver itself.
- `coga.bump.resolve_step_assignee` — dispatches `other-agent` to it.
- `coga.commands.bump.bump` — reads `new_step.get("assignee")` from the frozen
  snapshot, then resolves, on a forward bump.
- `coga.create.create_task` — resolves `wf.steps[0].assignee` at activation
  when `--workflow` is passed.

A **fifth is imminent**: `activation-does-not-resolve-step-1-s-assignee-role`
proposes making `coga.mark._freeze_workflow_ref` resolve step 1's role exactly
as `create_task` does, most naturally by extracting a shared helper out of
`create.py`. Read that ticket before editing `create.py` — if it lands first,
`peer` support belongs in the extracted helper, not duplicated.

`megalaunch` mentions `other-agent` only in comments about rotation and reads
`ticket.assignee` literally — correctly out of scope.

`VALID_ASSIGNEE_ROLES` lives in `src/coga/workflow.py` and is the shared
vocabulary (`owner` | `human` | `agent` | `other-agent`); the token set itself
does not change.

#### The config edits `peer` actually requires

Not just "a new key" — `[agents.*]` has a fixed schema with a fail-loud guard,
so two symbols in `src/coga/config.py` must change together:

- **`AgentType`** is a frozen dataclass; `peer` is a new field (`str | None`,
  defaulting to unset).
- **`_ALLOWED_AGENT_KEYS`** is a `frozenset` fed to `_reject_unknown_keys`,
  which raises `ConfigError` on any unlisted key in `[agents.*]`. **Adding
  `peer` to a `coga.toml` without adding it here breaks every `coga`
  command**, not just the bump.

#### Decided resolution rules

- **No silent guessing.** A three-agent repo with no `peer` declared must still
  raise `AssigneeResolutionError` with an actionable message naming the fix
  (`add peer = "<type>" to [agents.<agent>]`), not pick arbitrarily.
- **Two-agent repos need zero config.** With `peer` unset, `resolve_other_agent`
  is byte-identical in both success and error paths, so all 61 frozen snapshots
  and the existing `test_other_agent_*` tests are untouched.
- **Explicit beats inference.** In a two-agent repo a declared `peer` overrides
  the inference even if they disagree. Stated rule, not just a test case.
- **An invalid `peer` fails at load time**, as a `ConfigError` — consistent with
  the uniformly fail-at-load config code around it. This is decided; do not
  defer it to resolution time.
- **Validate `peer` after the parse loop completes, not inside it.**
  `_parse_agents` builds its output incrementally while iterating in TOML
  declaration order, so checking a forward reference inside the loop breaks the
  ordinary case (`[agents.claude] peer = "codex"` with `codex` declared second).
- **Self-peer is rejected.** `[agents.claude] peer = "claude"` is a
  `ConfigError`; an agent cannot review itself through this token.
- **`peer` is one-directional per agent.** In a three-agent repo, `claude`
  declaring `peer = "codex"` does nothing for codex-authored tickets, which
  still fail loud until codex declares its own. That is correct behavior, not a
  gap — say so in the docs.
- **`peer` must survive the half-one merge** and be settable from a local agent
  table, which is the natural way a third-agent machine wires itself up.

#### Why a per-agent `peer` and not a per-ticket `reviewer:`

Weighed and rejected for this cut: a per-ticket `reviewer:` field, and a
workflow-level declaration. A global per-agent `peer` bakes one reviewer per
agent type into committed repo policy, so a three-agent repo cannot route
claude to codex on infra tickets and to local-llm on prose. Accepted: it is the
smallest thing that unblocks a third agent, and a per-ticket override can layer
on later without breaking it. Record this rationale in the doc update — it
belongs in the context, not only in the ticket.

### Scope

In scope:

1. `[agents.*]` layers `coga.local.toml` over `coga.toml` at key level, per
   half one and its four details.
2. The `peer` key: `AgentType` field, `_ALLOWED_AGENT_KEYS` entry, load-time
   validation (after the loop; rejects unknown target and self-peer).
3. `resolve_other_agent` prefers a declared `peer`, falls back to inference,
   fails loud otherwise. All four call sites keep working.
4. A `coga validate` check that flags a workflow declaring `other-agent` that
   cannot resolve against current config. **Owner decision: `severity="error"`,
   deliberately.** See the risk note below — it is a known, accepted
   consequence, not an oversight to be "fixed" to a warning in review.
5. Docs, contexts, and fixtures updated in the same PR, per `CLAUDE.md`.

Out of scope:

- **Do not rewrite the frozen `other-agent` snapshots on the 61 existing
  tickets.** They are correct as-is and must keep resolving under the new rule.
  That they need no migration is an acceptance criterion, not work to do.
- **Do not edit this repo's `coga/coga.toml` or `coga/coga.local.toml`** (base
  prompt prohibition). `example/coga/` is a different file and is fair game.
- Changing the `VALID_ASSIGNEE_ROLES` vocabulary or adding new role tokens.
- A per-ticket `reviewer:` field (weighed and deferred, above).
- Any provenance affordance for locally-declared agents (decided against).

#### Risk note on scope item 4 — read before implementing

`assert_task_valid` runs on **every** Coga-owned task mutation:
`bump.advance_step` calls it mid-transition. An error-severity issue for an
unresolvable `other-agent` step anywhere in a frozen snapshot means that, on a
three-agent machine with no `peer` declared, all 44 non-terminal tickets become
unmutatable — `coga bump` at *any* step, `coga mark done`, launch's ticket
writes. Today's failure is confined to the one bump that actually enters
`peer-review`, so this converts a narrow failure into a repo-wide freeze,
including on tickets you only want to close.

The owner has weighed this and chosen error severity anyway: the loud failure
is the point, and the declared-`peer` escape hatch is one config line. Implement
it as an error. If you believe it is wrong, raise it with the owner — do not
quietly downgrade it.

Note also that `_check_step_shape(task_label, idx, step)` in
`src/coga/validate.py` takes neither `cfg` nor the ticket's `agent:`, so
resolving a role token from there requires changing its signature and threading
both through every caller. `validate.py` also has no `coga/workflows/` sweep
today — scope this check to workflows reachable through a ticket, not a new
repo-wide workflow scan.

### Docs, contexts, and fixtures

Per `CLAUDE.md`, a behavior change updates its matching context in the same PR,
and shipped contexts exist in two places that must stay in sync.

Prose that this change makes **flatly wrong** and must be corrected:

- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md`
  and `.../docs/with-review.md` — both say `other-agent` "needs exactly two
  agent types configured to be unambiguous. With one type, or three or more,
  the bump fails loud rather than guessing." This is the most user-visible
  statement of the rule. These are **single copies, not twins** —
  `bootstrap_workflow_path` resolves straight to the package.
- `coga/contexts/coga/architecture/SKILL.md` — "it needs two configured
  `[agents.*]`", plus a new sentence beside the `[layout]` paragraph stating
  that `[agents.*]`, unlike `[layout]`, layers local-over-shared, and why. Its
  packaged twin at
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`
  is byte-identical today; apply the same edit.
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/principles/SKILL.md`
  and `.../cli/SKILL.md` — also stale on the two-agent rule.
- `docs/concepts.md` — the assignee-role and `[agents.*]` sections. **No
  packaged twin exists**; `docs/` is not packaged. Single copy.
- `coga/workflows/_template.md` and its twin
  `src/coga/resources/templates/coga/workflows/_template.md` — the `assignee:`
  explainer. (It also omits `other-agent` from its role list entirely; fixing
  that is welcome here.)

Fixture:

- `example/coga/` — add a local-only agent type to the seeded fixture so the
  smoke path exercises an addition, not just an override.
  `example/coga/coga.local.toml` is tracked (`.gitignore`'s entry is
  root-anchored `/coga.local.toml`), so the edit lands in git. This makes
  `example/` a three-agent repo, which is exactly the shape the old
  `resolve_other_agent` fails on — with half two in the same PR that is the
  point, and the fixture becomes live coverage of the new path. Give it a
  `peer` so it resolves.

Optional: `coga/contexts/coga/codebase/SKILL.md` describes `coga.local.toml` as
"machine-local (NEVER committed; secrets here)" and could gain "agent types".

### Testing

There is **no `tests/test_bump.py`** — do not create one. The existing coverage
lives in `tests/test_commands.py`: helper `_add_second_agent` plus
`test_other_agent_resolves_to_the_peer_on_bump`,
`test_other_agent_flips_with_the_coder`,
`test_other_agent_step_one_resolves_at_create_time`, and
`test_other_agent_fails_loud_without_exactly_two_agents` (this last one needs
its name and body revisited — the condition it asserts is no longer the whole
rule). `tests/test_launch.py` holds the agent-rotation relaunch fixtures.

Two tests assert the current half-one behavior and must **invert**:

- `test_launch_rejects_local_agent_override` in `tests/test_launch.py` — the
  fixture (`[agents.claude] cli = "claude-nightly"` in `coga.local.toml`) must
  now launch with the overridden cli.
- `test_local_agent_overrides_are_rejected` in `tests/test_config.py` —
  identical fixture, matches `"no longer supports"`.

The removed-key regression guard in `tests/test_config.py` uses an unanchored
regex `coga\.local\.toml has removed key\(s\)`, so whatever the rewritten
message says must keep that substring contiguous.

New coverage to add — half one: local-only addition; partial override
inheriting unspecified keys; declaration order unchanged by a local-only
addition; local-only agent with a removed key still getting the migration error
(detail 2); unknown key in a local agent table rejected *and naming the file*
(detail 3). Half two: two agents with no `peer` (inference, unchanged); three
agents with `peer` declared; three agents without `peer` (raises, message names
the fix); `peer` naming an unconfigured type (load-time `ConfigError`);
self-peer rejected; `peer` set on a two-agent repo (explicit beats inference);
`peer` set from a local agent table and surviving the merge; and the validate
check firing at error severity.

Run `python -m pytest` and `coga validate --json`.

### Related

- `coga/tasks/parse-agents-rejects-cogalocaltoml.md` — **merged into this
  ticket** by owner decision; its full content is absorbed above.
- `coga/tasks/activation-does-not-resolve-step-1-s-assignee-role.md` — touches
  the same `create.py` resolution path and adds a fifth call site. Read it
  before editing `create.py`.

<!-- coga:blackboard -->

## Evaluator review

## Verdict

Solid ticket. The diagnosis is correct, the fallback design is sound, and a cold agent could start today. Everything below is a genuine gap, not polish.

## 1. Can a cold agent start immediately?

Yes for the *what*, no for the *where*. The Description names the symptom, the symbol, and the fix in three sentences. But the two config edits the change actually requires are never named:

- `AgentType` (`src/coga/config.py`) is a frozen dataclass; `peer` has to be added as a field.
- `_ALLOWED_AGENT_KEYS` (`src/coga/config.py`) is a `frozenset` fed to `_reject_unknown_keys`, which raises `ConfigError` on any unlisted key in `[agents.*]`. **Adding `peer` to `coga.toml` without adding it here breaks every single `coga` command**, not just the bump.

The ticket says only "the new key rides the existing `[agents.*]` table alongside `cli`, `file`, `mode`, and `discussion`." That's true but understates it: unknown keys in `[agents.*]` are *rejected*, deliberately, as a documented fail-loud guard. Name both symbols in the ticket.

## 2. Workflow fit

`code/with-review` is right — Python behavior change, testable, peer review earns its keep on a config-schema change with twin-sync obligations. No mismatch. Worth noting the recursion: this ticket's own `peer-review` step is the code path being fixed. It resolves fine today (two agents in `coga/coga.toml`), so no bootstrap problem.

## 3. `contexts: []` — right call, with one hole

Correct. `coga/contexts/coga/architecture/SKILL.md` is 72K, `sync` 56K, `recurring` 48K, `codebase` 24K. Attaching architecture would have taken the composed prompt from 15 KiB to ~87 KiB to deliver two relevant paragraphs. Copying the facts into `## Context` is the right trade here and the copied facts check out.

The hole is the config mechanics in §1 above — that's what an implementer would have gone to a context for and won't find. `CLAUDE.md` is auto-loaded, so the microkernel and twin-sync rules are covered.

## 4. Factual errors

**The "~25 live tickets" figure is wrong, by roughly half.** Actual counts under `coga/tasks/`: 61 files carry `assignee: other-agent` in a frozen snapshot. By status: 33 draft, 6 paused, 3 in_progress, 1 active, 1 blocked (= 44 non-terminal), plus 13 done and 4 canceled. This strengthens the ticket's argument, but it's the headline severity number and it should be right — and it's cited again in the design constraints ("what makes the ~25 frozen snapshots a non-issue").

**The call-site list is accurate for today** — verified all four: `bump.resolve_other_agent`, `bump.resolve_step_assignee`, `commands.bump.bump` (reads `new_step.get("assignee")` from the frozen snapshot, then resolves), `create.create_task` (`wf.steps[0].assignee`). `megalaunch` mentions `other-agent` only in comments about rotation and reads `ticket.assignee` literally — correctly excluded.

**`tests/test_bump.py` does not exist.** The Testing section directs the implementer to a file that isn't there. The existing coverage lives in `tests/test_commands.py` — helper `_add_second_agent` plus `test_other_agent_resolves_to_the_peer_on_bump`, `test_other_agent_flips_with_the_coder`, `test_other_agent_step_one_resolves_at_create_time`, `test_other_agent_fails_loud_without_exactly_two_agents` — and in `tests/test_launch.py` (agent-rotation relaunch fixtures). Those are the tests that must be updated; a fresh `test_bump.py` alongside them would fragment coverage.

**"Every one of these has a packaged twin" is false for `docs/concepts.md`** — `docs/` is not packaged; there is no `concepts.md` anywhere under `src/coga/resources/`. The other two do have twins (`.../bootstrap/contexts/coga/architecture/SKILL.md`, `.../templates/coga/workflows/_template.md`).

**The doc touchpoint list omits its own strongest evidence.** The Context section correctly identifies `bootstrap/workflows/code/with-review.md` and `docs/with-review.md`, but scope item 4 doesn't list them. Both contain prose that this change makes flatly wrong: *"`other-agent` needs exactly two agent types configured to be unambiguous. With one type, or three or more, the bump fails loud rather than guessing."* That's the most user-visible statement of the rule. Also stale after the change: `coga/contexts/coga/architecture/SKILL.md` ("it needs two configured `[agents.*]`") and the packaged `bootstrap/contexts/coga/{principles,cli}/SKILL.md`. Note these bootstrap workflow files are single copies, not twins — `bootstrap_workflow_path` resolves straight to the package.

## 5. Scope — item 3 is a second ticket, and it's dangerous as written

Items 1, 2, and 4 are one tight ticket. Item 3 (the `coga validate` check) should be split, for two reasons:

**It would make things worse, not better.** `assert_task_valid` runs on *every* Coga-owned task mutation — `bump.advance_step` calls it mid-transition. A new `severity="error"` issue for an unresolvable `other-agent` step anywhere in a frozen snapshot means that, the day a third agent lands without `peer`, all 44 live tickets become unmutatable: `coga bump` at *any* step, `coga mark done`, launch's ticket writes. Today's failure is confined to the one bump that actually enters `peer-review`. The proposed check converts a narrow failure into a repo-wide freeze — including on tickets you just want to close. If item 3 stays, it must be a warning-severity issue surfaced by `coga validate` only, or scoped to the step being entered. The ticket doesn't say which, and the default reading ("error", like the neighboring role-token check) is the harmful one.

**"repo-local or frozen on a ticket" is net-new surface.** `src/coga/validate.py` has no `coga/workflows/` sweep at all — it loads a workflow only via a ticket's `workflow:` name, and shape-checks frozen snapshots through `_check_step_shape`. And `_check_step_shape(task_label, idx, step)` takes neither `cfg` nor the ticket's `agent:`, so you cannot resolve a role token from there without changing its signature and threading both through every caller. "The existing role-token check sits in `coga.validate` next to its `VALID_ASSIGNEE_ROLES` use; extend around there" reads as a one-liner and isn't.

## 6. Assumptions to question before launch

**The sibling ticket is missing from Related, and it's the more important of the two.** `coga/tasks/parse-agents-rejects-cogalocaltoml.md` is the same Zach local-llm report, explicitly cites `src/coga/bump.py:44`, and calls this ticket "the sibling ticket below" — but this ticket doesn't point back. It matters concretely: `_parse_agents` currently hard-raises on *any* `[agents.*]` table in `coga.local.toml`, so today a third agent can only arrive by committing to `coga.toml`. Once the sibling lands and local tables overlay shared ones key-by-key, `peer` has to survive that merge and `_reject_unknown_keys` has to run against local agent tables too (it currently doesn't — the local loop only checks `_REMOVED_AGENT_KEYS`). Also note the out-of-scope line "do not edit `coga.local.toml` to seed `peer` keys" is currently moot: you can't put agent config there at all. Sequence these two deliberately, or state which lands first.

**A fifth call site is imminent.** `activation-does-not-resolve-step-1-s-assignee-role` proposes making `coga.mark._freeze_workflow_ref` resolve step 1's role "exactly as `create_task` does" — most naturally by extracting a shared helper out of `create.py`. The "four call sites, all must keep working" framing goes stale the moment that lands. The Related note to read it first is good; make the collision explicit.

**Where does an invalid `peer` fail?** "Validate it and fail loud on a typo" doesn't say whether that's a `ConfigError` at load time (bricks `coga status`, `coga digest`, everything) or an `AssigneeResolutionError` at resolution time (bricks only the bump). That's a real fork and the implementer will guess. Given the surrounding config code is uniformly fail-at-load, load-time is the consistent answer — but say so.

**Forward references will bite at load time.** `_parse_agents` builds `out` incrementally while iterating `raw.items()` in TOML declaration order. Validating `peer` inside that loop breaks the ordinary case — `[agents.claude] peer = "codex"` where `codex` is declared second. The check has to run after the loop completes.

**Two unspecified cases.** Self-peer (`[agents.claude] peer = "claude"`) should presumably be rejected; the ticket is silent. And `peer` is one-directional per agent: in a three-agent repo, `claude` declaring `peer = "codex"` does nothing for codex-authored tickets, which still fail. That's the correct fail-loud behavior, but it should be stated, along with whether a one-sided declaration warrants a validate warning.

**Does the fallback truly preserve behavior?** Yes — with `peer` unset, `resolve_other_agent` is byte-identical in both the success and error paths, so all 44 live snapshots and the existing `test_other_agent_*` tests are untouched. One deliberate new behavior worth naming: in a two-agent repo, a declared `peer` now silently overrides inference and could disagree with it. The Testing section already covers this case ("explicit beats inference"); just make it a stated rule rather than a test case.

**Is `peer` the right primitive at all?** A per-agent global `peer` bakes one reviewer per agent type into committed repo policy. A three-agent repo that wants claude reviewed by codex on infra tickets and by local-llm on prose tickets can't express that; a per-ticket `reviewer:` field or a workflow-level declaration could. The global key is probably the right first cut — it's the smallest thing that unblocks Zach — but the ticket doesn't record that the alternative was weighed. Per `CLAUDE.md`, that "why" belongs in the doc/context update (item 4), not only in the interview.

## 7. Prompt size

`base_prompt` (`prompt.md`) is 1858 / 3824 tokens = **49%**, over the 40% flag — but it's the shared base prompt, not this ticket's to trim. The ticket's own layers (`## Context` 1118 + `## Description` 196 = 1314, ~34%) are proportionate to the depth, and the Context is doing real work. No trim needed here.
