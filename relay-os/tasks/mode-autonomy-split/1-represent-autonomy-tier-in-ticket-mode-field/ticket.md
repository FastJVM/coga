---
title: Represent autonomy tier in ticket mode field
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- autonomy/triage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Split the conflated `mode` field into two orthogonal fields, and hard-migrate the
whole repo to the new vocabulary. **This ticket is the representation +
migration only — it preserves current launch behavior.** Actually unblocking
unattended execution is the follow-up
`2-unblock-unattended-execution-mode-autonomy-auto`.

Today `mode` is a single enum (`interactive` / `auto` / `script`) that conflates
two independent questions. Factor it into a clean 2×2:

- **`mode: agent | script`** — *is there an agent/LLM?* `agent` = agent-driven
  (today's `interactive`/`auto`), `script` = deterministic skill script, no LLM.
- **`autonomy: interactive | auto`** — *is a human at the wheel?* `interactive`
  = attended/TTY, `auto` = unattended/headless.

| | `mode: agent` | `mode: script` |
|---|---|---|
| `autonomy: interactive` | attended agent *(today's `interactive`)* | attended script (needs input) |
| `autonomy: auto` | unattended agent *(today's `auto`)* | unattended/recurring script |

This is where the autonomy decision the triage tier produces gets its enforced
home: `fully-automated → autonomy: auto`, the other three tiers →
`autonomy: interactive`. The four-tier vocabulary stays advisory at authoring
time (per `wire-autonomy-triage-into-impl-ready-workflows`); the binary
`autonomy` field is its coarse, enforced projection.

**Behavior is preserved exactly.** Every place that gates on the old `mode`
values is re-keyed to the new fields with identical effect — in particular
`autonomy: auto` stays blocked at launch (the `auto` hard-bail is re-keyed, not
removed), `retire` keeps its auto ban, and recurring keeps refusing auto. This
ticket is a pure refactor + migration; the reviewer's job is "nothing broke and
the vocabulary is consistent everywhere." Removing those blocks and building the
unattended run path is the follow-up.

Defaults are backwards-compatible: a ticket with neither field = `agent` +
`interactive`, identical to today's default `interactive` behavior.

## Context

Split out of `wire-autonomy-triage-into-impl-ready-workflows`, which wired
`autonomy/triage` into `bootstrap/ticket` at authoring time but deliberately
left the structured representation to this ticket. This ticket was then itself
split (per the evaluator review in `blackboard.md`): representation/migration
here; execution-unblocking in the follow-up.

**Verified live state of `mode` (the older "auto disabled may be stale" note is
NOT stale — auto is actively hard-bailed):**

- `src/relay/ticket.py:116` — `mode` defaults to `interactive`;
  `CANONICAL_TICKET_KEYS` at `ticket.py:26–40`.
- `src/relay/validate.py:64` — `VALID_MODES = {"interactive", "auto", "script"}`;
  schema check at `validate.py:473–481`.
- `src/relay/commands/launch.py:267–279` — `auto` hard-bails (exit 2). TTY check
  `_interactive_stdio_has_tty()` at `281`; PTY done-marker supervisor
  (`run_with_done_marker`) at `485`; all keyed on `mode == "interactive"`. The
  `--mode` override option + validator at `88–92` / `145–146`.
- `src/relay/commands/launch_script.py:150` — `subprocess.run(...)`, no
  stdin/stdout redirection (attended scripts inherit the terminal).
- `src/relay/compose.py:151–165` — interactive vs auto prompt layer; `script`
  composes no prompt.
- `src/relay/recurring.py:480–545` — `_effective_mode()` refuses `auto`; threaded
  through `create_recurring_instance` (`effective_mode=`, `mode=` at 354/377/510).
- **Other `mode` consumers (must all migrate — these were missed in an earlier
  draft, caught by the cold evaluator):**
  - `src/relay/commands/create.py:26–29, 47–50` — `--mode` option default +
    "interactive, auto, or script" help.
  - `src/relay/create.py:31, 135, 176` — `create_task(mode=...)` → frontmatter/log.
  - `src/relay/commands/retire.py:29–33, 51–58` — its **own** `--mode auto` ban /
    `--mode must be 'interactive'` check, independent of launch.py.
  - `src/relay/commands/status.py:29, 130, 202–214` — `mode` column + `--order-by
    mode`.
  - `src/relay/retrofit.py:162–173` — canonical field-ordering list (insert
    `autonomy`).
- Tests: `tests/test_launch_auto.py`, `tests/test_launch_script.py`,
  `tests/test_compose.py`, `tests/test_validate.py` (plus create/retire/recurring
  tests touching mode).

**Migration scope:** ~125 ticket/fixture/template files (≈114 `mode: interactive`,
≈11 `mode: script`, **0 `mode: auto`** live today). Legacy→new mapping:
`interactive → (agent, interactive)`, `auto → (agent, auto)`,
`script → (script, interactive)`.

**Owner's taxonomy note:** `script` = a launch; `auto` = script + `claude -p`.

**Back-compat decision: hard migrate (no dual vocabulary).** Rewrite every file
in the PR; the validator accepts only the new values after migration. Single
vocabulary, per Relay's legibility principle.

**Out of scope:** unblocking unattended execution / output capture / recurring
opt-in (→ `2-unblock-unattended-execution-mode-autonomy-auto`); remote/cloud
dispatch (a later "when mature" ticket).

## Approach

1. **Data model** (`ticket.py`) — add `autonomy` to `CANONICAL_TICKET_KEYS`
   (default `interactive`); `mode` values become `agent | script` (default
   `agent`).
2. **Validation + migration** (`validate.py`) — `VALID_MODES = {"agent",
   "script"}`, new `VALID_AUTONOMY = {"interactive", "auto"}`; hard-migrate every
   existing `mode` value in the repo (tickets, fixtures, `example/`, both template
   copies). Validator rejects legacy values after migration.
3. **Launch dispatch** (`launch.py`) — re-key the `(mode, autonomy)` gates with
   identical behavior: re-key the TTY check (`281`), the PTY supervisor (`485`),
   and **keep** the auto hard-bail but re-key it to `autonomy == "auto"`. Decide
   the `--mode` override CLI option + validator (`88–92`/`145–146`): split into
   `--mode` / `--autonomy` (recommended) and update its allowed values.
4. **Other CLI consumers** — migrate `commands/create.py` (`--mode` default/help,
   add `--autonomy`), `create.py` (`create_task` signature + frontmatter/log),
   `commands/retire.py` (re-key its own auto ban — preserved, not removed),
   `commands/status.py` (`mode` column + ordering; add an `autonomy` column),
   `retrofit.py` (insert `autonomy` into field ordering).
5. **Prompt composition** (`compose.py`) — interactive-vs-auto layer keys on
   `autonomy`, not `mode`; `mode: script` still composes nothing.
6. **Recurring** (`recurring.py`) — `_effective_mode` resolution produces both
   `mode` and `autonomy`; the auto refusal is **preserved** (re-keyed to
   `autonomy == "auto"`) — its removal is the follow-up.
7. **Contexts / templates / docs** (keep `relay-os/` and
   `src/relay/resources/templates/` in sync per CLAUDE.md) — update
   `_template/ticket.md` (both copies); document the enforced tier→autonomy
   mapping in `relay-os/contexts/autonomy/triage/SKILL.md`; update the `mode`
   references in `bootstrap/ticket/SKILL.md`.
8. **Tests** — `test_validate.py` (new field + legacy values now error),
   `test_compose.py` (re-key), `test_launch_auto.py` (auto still blocked, now via
   `autonomy`), plus create/retire/recurring tests for the migrated vocabulary.
   Whole suite green; behavior unchanged.
