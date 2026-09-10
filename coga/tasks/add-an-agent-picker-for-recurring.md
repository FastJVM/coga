---
slug: add-an-agent-picker-for-recurring
title: add an agent picker for recurring
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- dev/code
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 2 (evaluate-design)
launch_generation: pending:98a37dbd-75df-4ef2-8f71-67fbc293fafb
---

## Description

The ticket-authoring interview always launches as `claude`, whatever agent was
picked upstream. Both `coga ticket` and megalaunch's picked-draft authoring pass
resolve the interview's agent with the same chain —
`agent_override or bootstrap_ticket.assignee or ticket.agent or ticket.assignee`
— and the packaged bootstrap ticket ships `assignee: claude`, so that shipped
default outranks the target ticket's own `agent:`. The only way to reach another
agent is to retype `--agent codex` on every single invocation. The motivating
case is switching authoring interviews to `codex` for the hours a Claude quota
is exhausted, without remembering a flag every time.

Two halves, one change: fix the precedence so a chosen agent actually reaches
the interview, and add a durable setting so the choice survives more than one
invocation, with an explicitly-requested picker for one-off switches.

The precedence fix alone does not solve the motivating case. `coga create`
always stamps a valid `agent:` (`create._default_agent_for` falls back to
`Config.default_agent()`, the first-declared `[agents]` block), so for a
targeted `coga ticket <slug>` the ticket's `agent:` is essentially always
`claude` too — reordering just swaps one `claude` for another. And the bare
`coga ticket` invocation, which is the likely one for the quota case, resolves
`ref` and `source_ticket` both to the bootstrap ticket, so reordering changes
nothing there at all. The durable setting is the half that does the work; the
reorder is what makes a deliberately-edited `agent:` mean something.

### Acceptance criteria

- [ ] A single `resolve_authoring_agent()` resolves the authoring agent for
      both consumers (`coga ticket` and megalaunch's `_author_draft`), in this
      order, first non-empty wins:
      1. `agent_override` — `--agent <name>`, `coga megalaunch --agent`, or the
         `coga ticket --pick-agent` picker's answer
      2. `COGA_AUTHORING_AGENT` environment variable
      3. `[authoring] agent` in `coga.local.toml`
      4. the target ticket's own `agent:`
      5. the bootstrap ticket's `assignee:`
- [ ] `source_ticket.assignee` is **dropped** from the chain (see Q4 in Context).
- [ ] With nothing set anywhere, a bare `coga ticket` still resolves `claude`
      via term 5.
- [ ] A ticket whose `agent:` is `codex` gets a `codex` authoring interview from
      `coga ticket <slug>` — the criterion nothing tests today.
- [ ] An unknown name from *any* term fails loud through `Config.agent_type`,
      the way `--agent` fails today, with a message naming which term supplied
      it (env var / `coga.local.toml` / ticket `agent:` / bootstrap ticket) and
      pointing at `--agent` as the override. No silent fallback.
- [ ] `coga ticket --pick-agent` prints a numbered list of the configured agent
      types in `[agents]` declaration order, marks the one that would be
      resolved without the flag, defaults to it on empty input, re-prompts on
      invalid input, and uses the answer as `agent_override`.
- [ ] `--pick-agent` with fewer than two agents configured does not prompt; it
      echoes the single resolved agent and proceeds.
- [ ] `--pick-agent` without a TTY bails with the existing
      `_run_authoring_session` TTY message rather than blocking on a prompt.
- [ ] After a pick, `coga ticket` echoes one line showing how to make the choice
      stick (the `coga.local.toml` key and the env var). The picker itself
      writes no config file.
- [ ] Megalaunch's batched authoring pass never prompts: `_author_draft` gains
      no picker and reaches terms 2-5 only, with `coga megalaunch --agent` as
      term 1. `COGA_AUTHORING_AGENT=codex coga megalaunch` authors every picked
      draft as `codex` with no per-draft question.
- [ ] `_author_draft` stays best-effort: a resolution failure (unknown agent
      from any term) leaves the draft untouched and the run continuing, exactly
      as its `SystemExit` swallow does today.
- [ ] `[authoring] agent` is accepted in `coga.local.toml` only. The table in
      shared `coga.toml` raises a tailored error saying it is machine-local,
      following the `[secrets]`-in-local precedent in `load_config`.
- [ ] An unknown key inside `[authoring]`, or a non-string / empty `agent`,
      raises `ConfigError`.
- [ ] The packaged bootstrap ticket's body no longer tells the operator to swap
      `assignee:` for a one-off agent change, and states what the field means
      now (see Q1 in Context).
- [ ] `docs/reference.md` and the packaged `coga/cli` context document
      `--pick-agent`, the config key, the env var, and the precedence order.
- [ ] `python -m pytest` passes; `coga validate --json` is clean.

### Proposed shape

Work in this order; each step is independently reviewable.

**1. Config — the durable setting.** In `src/coga/config.py`:

- Add `authoring_agent: str = ""` to the `Config` dataclass, near
  `launch_idle_timeout` (both are "defaults read by one subsystem"), with a
  comment saying it is machine-local because quota exhaustion is per-operator,
  and that `COGA_AUTHORING_AGENT` wins over it — mirroring the
  `[launch]` / `COGA_REPL_*` relationship already documented there.
- Add `_ALLOWED_AUTHORING_KEYS: frozenset[str] = frozenset({"agent"})` beside
  the other `_ALLOWED_*` constants, and add `"authoring"` to
  `_ALLOWED_LOCAL_SECTIONS`. Do **not** add it to `_ALLOWED_SHARED_SECTIONS`.
- Add `_parse_authoring(local: dict | None) -> str` beside `_parse_launch`:
  `None` → `""`; non-dict → `ConfigError("[authoring] must be a table ...")`;
  `_reject_unknown_keys(..., _ALLOWED_AUTHORING_KEYS, "[authoring]")`; a
  present `agent` must be a non-empty `str` or raise. It does *not* validate the
  name against `[agents]` — that happens at resolution, so a stale key only
  breaks authoring, not every command.
- In `load_config`, beside the existing tailored migration raises, add
  `if "authoring" in shared:` → `ConfigError` explaining `[authoring]` is
  machine-local and belongs in `coga.local.toml`. Place it before
  `_reject_unknown_sections` so it beats the generic unknown-key message.
- Call `authoring_agent = _parse_authoring(local.get("authoring"))` and pass it
  into the `Config(...)` construction.
- In `src/coga/commands/init.py`, add a commented stanza to
  `LOCAL_TOML_TEMPLATE` documenting the key:
  `# [authoring]` / `# agent = "codex"` with one line of why.

**2. Resolution — one function, two consumers.** In `src/coga/authoring.py`
(the module already named for this concern; `commands/ticket.py` would make
`commands/` hold shared logic, and both consumers already import from
`authoring`):

```python
AUTHORING_AGENT_ENV = "COGA_AUTHORING_AGENT"

def resolve_authoring_agent(
    cfg: Config,
    *,
    source_ticket: Ticket,
    bootstrap_ticket: Ticket,
    agent_override: str | None = None,
) -> str:
    """Pick the agent type that runs a ticket-authoring interview. ..."""
```

It walks the five terms, records which one supplied the winner, validates the
winner with `cfg.agent_type(name)`, and on `ConfigError` re-raises a
`ConfigError` whose message appends the source (e.g. `"... (from
COGA_AUTHORING_AGENT; pass --agent <nickname> to override)"`). All terms empty
raises `ConfigError("No authoring agent configured; pass --agent <nickname>.")`
— the string `ticket()` currently bails with.

Importing `Ticket` into `authoring.py` is cycle-free: `coga/ticket.py` imports
only `yaml` and `coga.atomicio`.

**3. `coga ticket` — wire it up and add the picker.** In
`src/coga/commands/ticket.py`:

- Add `pick_agent: bool = typer.Option(False, "--pick-agent", help=...)`.
- Replace the inline four-term `launch_assignee = (...)` chain and its
  `if not launch_assignee: _bail(...)` with, in this order:
  1. If `pick_agent`: bail with the `_run_authoring_session` TTY message when
     `not _interactive_stdio_has_tty()`; otherwise
     `agent_override = _pick_authoring_agent(cfg, cfg_default) or agent_override`.
  2. `launch_assignee = resolve_authoring_agent(...)`, wrapped in
     `except ConfigError as exc: _bail(str(exc))`.
- The picker needs the would-be default to mark and to use as its prompt
  default, so call `resolve_authoring_agent(..., agent_override=None)` first
  (inside a `try`, tolerating `ConfigError` by marking nothing) and pass the
  result in.
- Add `_pick_authoring_agent(cfg: Config, current: str | None) -> str` — ~25
  lines, `typer.echo` for the numbered list plus a `typer.prompt` loop in the
  `unblock.py` shape. Returns `current` immediately when `len(cfg.agents) < 2`.
  Keeping it in the command module — not in `authoring.py` — is what
  structurally guarantees megalaunch can never prompt.
- After a pick, `typer.echo` the one-line sticky hint naming both
  `[authoring] agent = "<name>"` in `coga.local.toml` and
  `export COGA_AUTHORING_AGENT=<name>`.
- Leave `_run_authoring_session` unchanged, including its own
  `cfg.agent_type()` call (now a cheap re-validation of a known-good name).

Note the resulting message-order change: on a non-TTY invocation with a bad
`COGA_AUTHORING_AGENT`, the agent error now surfaces before the TTY error,
because resolution moved ahead of `_run_authoring_session`. That is the more
useful message; check `tests/test_ticket.py` for anything asserting the old
order.

**4. Megalaunch — same chain, no prompt.** In `src/coga/megalaunch.py`
`_author_draft`, replace the inline chain with `resolve_authoring_agent(...)`
imported from `coga.authoring`. Widen the existing `try` so it catches
`ConfigError` alongside `SystemExit` and returns, preserving the documented
best-effort contract. Nothing else in megalaunch changes;
`_confirm_author_drafts` stays the single batch gate it is.

**5. Bootstrap ticket prose.** In
`src/coga/resources/templates/coga/bootstrap/ticket/ticket.md`, keep
`assignee: claude` and rewrite the two paragraphs that call it the knob to turn.
It is now the **install-level default and last resort**: it governs the bare
`coga ticket` empty interview (where the bootstrap ticket *is* the source
ticket) and any target somehow lacking `agent:`, and a repo can change it for
the whole install by minting a local `coga/bootstrap/ticket/ticket.md`
(`resolve_bootstrap` is local-first). Point one-off and session-length switches
at `--agent`, `--pick-agent`, `COGA_AUTHORING_AGENT`, and `[authoring] agent`
instead. Confirm before editing that `coga/bootstrap/ticket/` still does not
exist, so the file has no packaging twin (see Repo rule in Context).

**6. Docs.** `docs/reference.md` `### coga ticket [TARGET]` — add `--pick-agent`
and a short precedence list. `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
`## coga ticket` — same, in that file's voice. Neither has a live twin under
`coga/contexts/coga/cli/`; re-confirm before editing.

**7. Tests.** New coverage in `tests/test_ticket.py` (ticket `agent:` beats
bootstrap `assignee:`; `--agent` beats everything; env beats config key beats
ticket `agent:`; bare `coga ticket` falls to bootstrap `assignee:`; unknown name
from env and from the config key each bail with the source named; `--pick-agent`
without a TTY bails; picker answer wins with `typer.prompt` monkeypatched;
picker skipped with one agent configured), in `tests/test_megalaunch.py`
(`_author_draft` honors env and ticket `agent:`; `_author_draft` never calls
`typer.prompt` — monkeypatch it to raise; `_author_draft` swallows a resolution
`ConfigError`), and in `tests/test_config.py` (`[authoring] agent` parses from
local; unknown key inside `[authoring]` rejected; `[authoring]` in shared
`coga.toml` raises the tailored error). The two existing tests named under
Context must still pass unmodified.

### Out of scope

- Any remote or cloud agent mode. `src/coga/config.py` still carries
  `mode: "local" | future: "remote" | "cloud"` as a comment and no cloud target
  exists. Quota fallback here means picking a different *local* CLI.
- Writing `coga.local.toml` from the picker. There is no in-place TOML writer in
  core — `coga init` renders the whole file once via `render_local_toml` — and
  adding one to make a prompt self-silencing is new machinery for a file the
  operator can edit directly. The picker prints the line instead.
- A picker on `coga megalaunch` or `coga recurring`. Both already take
  `--agent`, and prompting inside a batch pass is the failure mode this design
  is avoiding.
- Redesigning the `coga recurring --agent` / `coga megalaunch --agent` flags, or
  `coga launch --agent`. Whether the value lands in the spawned interview is in
  scope; reshaping the flags is not.
- Rewriting ticket `assignee:` frontmatter, or persisting the chosen agent onto
  the ticket. The choice stays ephemeral, matching existing `agent_override`
  semantics.
- Making `[authoring]` a shared `coga.toml` table. The install-level lever is
  the bootstrap ticket's `assignee:`.
- `coga recurring`. Despite this ticket's title, the recurring runner spawns no
  authoring interviews: `src/coga/recurring_runner.py` never imports
  `megalaunch`, never references `_author_draft` or `_run_authoring_session`,
  and never touches `bootstrap/ticket`. Its `agent_override` reaches only the
  recipe argv and per-task launches. This change alters no `coga recurring`
  behaviour.

## Context

### Where this lives

Cite symbols, not line numbers — positions below are orientation only.

- `src/coga/commands/ticket.py` — `ticket()` builds `launch_assignee` from the
  chain above and passes it to `_run_authoring_session`. On the bare
  `coga ticket` path (no target), `ref` and `source_ticket` both resolve to the
  bootstrap ticket, so all four current terms name the same file and reordering
  changes nothing there. `_run_authoring_session` and `_authoring_ticket` are
  already imported by `megalaunch`, so this module is already a shared surface.
- `src/coga/megalaunch.py` — `_author_draft` repeats the same chain for drafts
  picked during a megalaunch run, with `agent_override` fed from
  `coga megalaunch --agent`. It is called from exactly one site, the
  picked-draft prep pass (phase 1) in `_run_selection`, itself gated by the
  one-shot `_confirm_author_drafts` prompt in `commands/megalaunch.py`.
- `src/coga/authoring.py` — currently finalization/sync helpers
  (`snapshot_authoring_state`, `finalize_authored`). Imports `Config`, `git`,
  `tasks`, `validate`; no import of `coga.ticket` yet, and no cycle risk in
  adding one.
- `src/coga/config.py` — `Config`, `agent_type`, `default_agent`,
  `load_config`, `_parse_launch`, `_reject_unknown_sections`, and the
  `_ALLOWED_*SECTIONS` frozensets.
- `src/coga/resources/templates/coga/bootstrap/ticket/ticket.md` —
  `assignee: claude`, the value that currently wins.

### Findings from the design pass

- **`resolve_bootstrap` is local-first.** A repo-local
  `coga/bootstrap/ticket/ticket.md` overrides the packaged one, so the
  bootstrap `assignee:` is a real per-install knob, not dead config. In *this*
  repo `coga/bootstrap/` holds only `resolve-conflicts`, so the packaged copy
  is the one in play. `example/coga/` has no `bootstrap/` at all.
- **Every coga-created ticket has a valid `agent:`.** `create.create_task`
  computes it via `_default_agent_for` — the explicit assignee when it names an
  agent type, else `Config.default_agent()` (first-declared `[agents]` block) —
  and rejects creation when no agent types are declared. So term 4 is always
  populated and always a real agent type for a targeted `coga ticket <slug>`,
  which makes term 5 unreachable on that path. Term 5 governs the bare
  no-target interview, where the bootstrap ticket has `assignee:` and no
  `agent:`. That split is the honest answer to Q1.
- **An optional-value `--agent` is not available.** Verified empirically
  against the repo's `.venv` (typer 0.23.2): `typer.Option(None, "--agent",
  is_flag=False, flag_value=...)` still errors `Option '--agent' requires an
  argument`, because typer re-derives `is_flag` from the annotation. Hence a
  separate `--pick-agent` flag rather than a bare `--agent`. A sentinel value
  like `--agent ?` was rejected because `?` is a shell glob.
- **`coga.local.toml` has no in-place writer.** `coga init` renders the whole
  file once (`render_local_toml`, `LOCAL_TOML_TEMPLATE`); `tomllib` is
  read-only and there is no `tomli-w` dependency. This is why the picker prints
  the sticky line instead of writing it.
- **Env-var-beats-config-key is an established idiom.** `[launch]
  idle_timeout` / `max_session` are overridden by `COGA_REPL_IDLE_TIMEOUT` /
  `COGA_REPL_MAX_SESSION`, read in `recurring_runner`, not in `config.py`.
  `COGA_AUTHORING_AGENT` follows that shape and is read in
  `resolve_authoring_agent`, keeping `Config` a pure file-config object.

### Constraints

- `_run_authoring_session` bails unless stdin and stdout are both TTYs
  (`_interactive_stdio_has_tty`). The picker must not fire on a non-TTY path,
  and must not turn megalaunch's batched authoring pass into a per-draft
  interrogation the operator cannot script past.
- `_author_picked_draft` is documented as best-effort prep and deliberately
  swallows `SystemExit` so an unauthorable draft simply stays a draft. Preserve
  that, and extend it to the new `ConfigError`.
- Agent nicknames validate through `Config.agent_type`. An unknown nickname
  should fail the way `--agent` fails today, not silently fall back.
- `coga/coga.toml` configures exactly two agents here, `claude` and `codex`,
  both `mode = "local"`; `coga/coga.local.toml` adds none.
- Agents working this ticket must not edit `coga.toml` or `coga.local.toml`
  (Coga base prompt, Boundaries). Config *schema* changes go in `config.py` and
  the `init` template; test fixtures write their own TOML.
- Keep core minimal. This adds one `Config` field, one parser, one shared
  resolver with two real consumers, and one command-local picker — no new
  module, no new `runner.RECIPES` entry, no launch plugin.

### Answers to the ticket's design questions

1. **What does bootstrap `assignee:` mean afterwards?** An **install-level
   default and last resort**, still live, still validated. It governs the bare
   `coga ticket` empty interview and any target lacking `agent:`; a repo
   changes it for a whole install by minting a local
   `coga/bootstrap/ticket/ticket.md`. Its prose is rewritten to stop
   advertising it as the one-off switch.
2. **When does the picker fire?** Only on explicit `coga ticket --pick-agent`,
   and only with a TTY and ≥2 configured agents. A ticket's own
   `agent:`/`assignee:` neither triggers nor suppresses it — since `coga create`
   stamps `agent:` unconditionally, those fields carry no signal about
   deliberate choice, so conditioning on them would produce either a
   never-firing or an always-firing picker. The durable setting, not a prompt,
   is what carries the operator across a multi-hour quota outage.
3. **What does megalaunch's batched pass do?** Never prompts. It inherits
   `--agent` (term 1) or the sticky default (terms 2-3), and the picker lives in
   the command module so it cannot reach `_author_draft` by construction.
4. **What happens to `source_ticket.assignee`?** **Dropped.** Ticket
   `assignee:` is often a human name (this ticket's is `nicktoper`) and the
   template documents it as `replace-with-human-or-agent-nickname`, while
   `agent:` is documented as `replace-with-agent-nickname`. Handing a human
   name to `cfg.agent_type()` hard-fails. The term is unreachable today because
   `bootstrap_ticket.assignee` always wins; promoting it would turn a latent
   bug into a live one. `agent:` is the field that names an agent type.

### Tests that pin current behaviour

- `tests/test_megalaunch.py` — `test_author_draft_prefers_megalaunch_agent_override`
  asserts `agent_override` wins over a Claude fallback assignee. Survives the
  change (term 1 is still first).
- `tests/test_ticket.py` — `test_ticket_agent_override_codex_gets_kickoff`.
  Survives the change.
- Neither tests ticket-agent-beats-bootstrap. That is the new criterion and
  needs new coverage.

### Existing idioms to reuse

- `typer.prompt` — `src/coga/commands/unblock.py`.
- `typer.confirm` — `_confirm_author_drafts` in `src/coga/commands/megalaunch.py`,
  the one-shot batch gate the picker sits beside rather than inside.
- Tailored pre-emptive `ConfigError` raises before `_reject_unknown_sections` —
  the `[assignees]`, `[megalaunch]`, `[secrets]`, `[slack]` blocks in
  `load_config`.
- `_parse_launch` — the shape for a small table parser with its own
  `_reject_unknown_keys` call.

### Related tickets

- `coga/tasks/the-ticket-interview-never-asks-what-done-means.md` — separate
  interview-quality work; do not fold them together.
- `coga/tasks/bumppy-requires-exactly-two-agents.md` — also touches agent
  selection.

### Repo rule

`tests/test_packaging.py` byte-compares `src/coga/resources/templates/coga/<path>`
against `coga/<path>` for every pair whose live counterpart exists. Verified
during this design pass: `coga/bootstrap/ticket/` does not exist (only
`coga/bootstrap/resolve-conflicts/`), and `coga/contexts/coga/cli/SKILL.md`
does not exist either — so neither the packaged bootstrap ticket nor the
packaged `coga/cli` context has a twin to sync today. Re-confirm both at
implement time before editing them.

<!-- coga:blackboard -->

## Design notes — 2026-09-10

Design step complete. Spec is in `## Description` (acceptance criteria,
proposed shape, out of scope) and `## Context` (findings, answers to the four
questions the ticket parked). No branch, no code.

Verified during the pass, so the implementer need not re-derive:

- `create.create_task` → `_default_agent_for` always stamps a valid `agent:`
  (explicit assignee if it names an agent type, else `Config.default_agent()`).
  So term 4 is always populated for a targeted `coga ticket <slug>`, and the
  bootstrap `assignee:` only ever governs the bare no-target interview. This is
  why the precedence fix alone cannot solve the quota case and the sticky
  default is the load-bearing half.
- `typer.Option(None, "--agent", is_flag=False, flag_value=...)` does **not**
  give an optional-value flag on this repo's typer (0.23.2 in `.venv`) — it
  still errors `Option '--agent' requires an argument`. Ran it. Hence the
  separate `--pick-agent` flag.
- `resolve_bootstrap` is local-first, so bootstrap `assignee:` is a live
  per-install knob, not dead config. `coga/bootstrap/` here holds only
  `resolve-conflicts`; `example/coga/` has no `bootstrap/` at all.
- No packaging twin exists today for either file the spec edits
  (`templates/coga/bootstrap/ticket/ticket.md`,
  `templates/coga/bootstrap/contexts/coga/cli/SKILL.md`) — no live
  `coga/bootstrap/ticket/` and no live `coga/contexts/coga/cli/`.
- No in-place TOML writer exists in core (`coga init` renders the whole local
  file once; `tomllib` is read-only, no `tomli-w` dep). That is the concrete
  reason the picker prints the sticky line rather than persisting it.

Sizing: one PR. ~130 lines across `config.py`, `authoring.py`,
`commands/ticket.py`, `megalaunch.py`, `commands/init.py`, plus the bootstrap
ticket prose, two doc surfaces, and ~12 tests. No split recommended.

## Open Questions

Answers to the ticket's four parked questions are in `## Context` → "Answers to
the ticket's design questions"; they are decided, not open. What remains for
the owner at `review-design` is naming and one scope call:

1. **Names.** `--pick-agent`, `COGA_AUTHORING_AGENT`, and `[authoring] agent`
   in `coga.local.toml`. All three are new public surface and cheap to rename
   now, expensive later. Alternatives considered: `--pick`, `COGA_TICKET_AGENT`,
   and folding the key under a `[ticket]` table (rejected — `[ticket]` in shared
   `coga.toml` is already the extension-fields table, so reusing the name across
   files would be confusing).
2. **Should `[authoring]` also be accepted in shared `coga.toml`?** Spec says
   no: quota exhaustion is per-operator, and the install-level lever already
   exists as the bootstrap ticket's `assignee:`. A team that wants a committed
   authoring default currently has to mint a local
   `coga/bootstrap/ticket/ticket.md`, which is heavier than a config line. If
   the owner wants the lighter path, allowing the table in both files with
   local-over-shared resolution is a small addition to `_parse_authoring`.
3. **Should the picker offer to persist the choice?** Spec says no — it would
   need a new in-place TOML writer in core (see notes above), which the
   microkernel rule argues against for a prompt-silencing convenience. If the
   owner would rather have "pick once, never asked again", that is the change,
   and it makes `--pick-agent` a setup command rather than a one-off override.
