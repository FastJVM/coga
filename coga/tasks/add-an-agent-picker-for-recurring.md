---
slug: add-an-agent-picker-for-recurring
title: add an agent picker for recurring
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (design)
---

## Description

The ticket-authoring interview always launches as `claude`, whatever agent was
picked upstream. Both `coga ticket` and megalaunch's picked-draft authoring pass
resolve the interview's agent with the same chain —
`agent_override or bootstrap_ticket.assignee or ticket.agent or ticket.assignee`
— and the bootstrap ticket ships `assignee: claude`, so that hardcoded default
outranks the target ticket's own `agent:`. The only way to reach another agent
is to retype `--agent codex` on every single invocation.

Two halves, one change:

1. **Fix the precedence** so a chosen agent actually reaches the interview: the
   target ticket's own `agent:` beats the bootstrap ticket's default, and
   `bootstrap_ticket.assignee` becomes a last-resort fallback rather than the
   first winner. Note that megalaunch's half of this already works —
   `agent_override` is the first term in both chains and `tests/test_megalaunch.py`
   asserts it. The remaining work is one clause.
2. **Add a sticky default plus a picker.** A per-invocation prompt alone is the
   wrong shape: quota exhaustion lasts hours, so prompting would tax every
   `coga ticket` forever. Give the authoring agent a durable setting — a key in
   `coga.local.toml` or an env var — and keep an interactive picker for one-off
   overrides. With nothing set anywhere, the default stays `claude`.

The motivating case is switching authoring interviews to `codex` when the Claude
quota is exhausted, without having to remember a flag on every invocation.

## Context

### Where this lives

Cite symbols, not line numbers — positions below are orientation only.

- `src/coga/commands/ticket.py` — `ticket()` builds `launch_assignee` from the
  chain above and passes it to `_run_authoring_session`. Note the bare
  `coga ticket` path (no target): `ref` and `source_ticket` both resolve to the
  bootstrap ticket, so all four terms of the chain name the same file and
  reordering changes nothing there. The picker is the only mechanism for the
  no-target invocation — which is likely the common one for the quota case.
- `src/coga/megalaunch.py` — `_author_draft` repeats the same chain for drafts
  picked during a megalaunch run, with `agent_override` fed from
  `coga megalaunch --agent`. It is called from exactly one site, the
  picked-draft prep pass in `_select_and_launch`.
- `src/coga/resources/templates/coga/bootstrap/ticket/ticket.md` —
  `assignee: claude`, the value that currently wins. There is no repo-local
  `coga/bootstrap/ticket/`, so this packaged copy is the only one; changing it
  is a shipped-default change, not a local override.

### Constraints

- `_run_authoring_session` bails unless stdin and stdout are both TTYs
  (`_interactive_stdio_has_tty`). The picker must not fire on a non-TTY path,
  and must not turn megalaunch's batched authoring pass into a per-draft
  interrogation the operator cannot script past.
- `_author_picked_draft` is documented as best-effort prep and deliberately
  swallows `SystemExit` so an unauthorable draft simply stays a draft. Preserve
  that.
- Agent nicknames validate through `Config.agent_type`. An unknown nickname
  should fail the way `--agent` fails today, not silently fall back.
- `coga/coga.toml` configures exactly two agents here, `claude` and `codex`,
  both `mode = "local"`; `coga/coga.local.toml` adds none.
- The last term of the chain, `source_ticket.assignee`, is a latent bug the
  reorder would *promote*. Ticket `assignee:` is often a human name (this
  ticket's is `nicktoper`), and handing that to `cfg.agent_type()` hard-fails.
  It is unreachable today because `bootstrap_ticket.assignee` always wins.
  Decide what that term should be before moving it up.
- The bootstrap ticket's own body currently documents `assignee:` as the knob
  to turn: "swap the `assignee` to whichever effective agent type you have
  configured". Demoting the field to a last-resort fallback makes that prose
  false, so the same change has to rewrite it — and say what `assignee:` there
  means afterwards (install-level default, or dead field).

### Tests that pin current behaviour

- `tests/test_megalaunch.py` (~4360-4402) — asserts `agent_override` wins over a
  Claude fallback assignee. Survives the change.
- `tests/test_ticket.py` — `test_ticket_agent_override_codex_gets_kickoff`.
  Survives the change.
- Neither tests ticket-agent-beats-bootstrap. That is the new criterion and
  needs new coverage.

### Existing idioms to reuse

- `typer.prompt` — `src/coga/commands/unblock.py`.
- `typer.confirm` — `_confirm_author_drafts` in `src/coga/commands/megalaunch.py`,
  which is already the "should I author drafts?" gate the picker would sit
  beside. Reuse the shape rather than inventing a bespoke picker.

### Out of scope

- Any remote or cloud agent mode. `src/coga/config.py` still carries
  `mode: "local" | future: "remote" | "cloud"` as a comment and no cloud target
  exists. Quota fallback here means picking a different *local* CLI.
- Redesigning the `coga recurring --agent` / `coga megalaunch --agent` flags.
  They exist and are plumbed; whether the value lands in the spawned interview
  is in scope, reshaping the flags is not.
- Rewriting ticket `assignee:` frontmatter. The chosen agent stays ephemeral,
  matching existing `agent_override` semantics.
- `coga recurring`. Despite this ticket's title, the recurring runner spawns no
  authoring interviews: `src/coga/recurring_runner.py` never imports
  `megalaunch`, never references `_author_draft` or `_run_authoring_session`,
  and never touches `bootstrap/ticket`. Its `agent_override` reaches only the
  recipe argv and per-task launches. This change alters no `coga recurring`
  behaviour.

### Related tickets

- `coga/tasks/the-ticket-interview-never-asks-what-done-means.md` — separate
  interview-quality work; do not fold them together.
- `coga/tasks/bumppy-requires-exactly-two-agents.md` — also touches agent
  selection.

### Questions for the design step

These are unresolved on purpose; answer them in the spec before implementing.

1. **What does `assignee:` on the bootstrap ticket mean afterwards?** Its own
   body currently tells the operator to swap that field to their configured
   agent type. Demoting it to a last-resort fallback makes that prose false, so
   the same change rewrites it. Is the field then an install-level default, a
   dead field, or deleted outright?
2. **When does the picker fire?** Does a ticket's own `agent:`/`assignee:` count
   as "already chosen"? `coga create` stamps `assignee:` on every draft, so
   counting it means the picker almost never fires; not counting it means it
   fires on nearly every invocation. These are different products.
3. **What does megalaunch's batched authoring pass do?** Prompt once for the
   whole pass, or never prompt and inherit `--agent` / the sticky default only?
   It must not become a per-draft interrogation the operator cannot script past.
4. **What happens to the `source_ticket.assignee` term?** See the latent bug
   under Constraints — it should probably be dropped rather than promoted.

### Repo rule

`tests/test_packaging.py` byte-compares `src/coga/resources/templates/coga/<path>`
against `coga/<path>` for every pair whose live counterpart exists.
`coga/bootstrap/ticket/` has no live counterpart today, so editing the packaged
bootstrap ticket currently has no twin to sync — confirm that still holds before
changing it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
