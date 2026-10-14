---
title: dream should be able to use codex instead of claude
status: active
owner: nicktoper
agent: claude
contexts:
- dev/code
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
step: 1 (design)
---

## Description

Today the only way to make Dream (and any other agent-backed recurring job,
or any newly activated ticket) run on `codex` rather than `claude` is to
reorder the `[agents.*]` tables in `coga.toml` — the "default agent" is
implicit, whichever table is declared first. Add an explicit, named
repo-wide default-agent key so an operator can switch the default to `codex`
without reordering tables, and confirm the existing
`coga recurring --agent <type>` sweep flag reaches Dream.

The key lives in shared `coga.toml` as the team default and may also be set in
machine-local `coga.local.toml`, where it wins — so one operator can switch
their machine to `codex` (e.g. while a Claude quota is exhausted) without
editing a committed file. `Config.default_agent()` honours the key first and
falls back to first-declared `[agents.*]` only when it is unset anywhere. The
proposed spelling is a top-level scalar `default_agent = "<type>"`, matching
the existing top-level `default_status = "draft"`; the design step may pick a
different shape but must justify it.

Done when: setting the key to `codex` (in either file) makes
`Config.default_agent()` — and therefore ticket activation, `coga create` into
a live status, `coga retire`'s default, the autofix fallback, and a
`coga recurring` sweep's next newly materialized Dream period task — resolve
`codex` without any `[agents.*]` reorder; a local value overrides the shared one; an unset key keeps
today's first-declared behaviour byte-for-byte; `coga recurring --agent codex`
reaching the Dream launch is covered by test (one already exists, see
Context); the contexts, docs, and docstrings named under Context that describe
the default are updated; `python -m pytest` passes and `coga validate --json`
is clean.

## Context

**Current mechanism.** `config.Config.default_agent` returns the first entry of
`cfg.agents` (TOML declaration order over the merged shared+local tables). Its
consumers: `mark._select_main_agent` (activation stamps `agent:` from it),
`create._select_main_agent` (via `bump.resolve_main_agent(...,
allow_prospective_default=True)` for a live create),
`commands/retire._default_agent`, `recurring_autofix._analyze_agent` (the
fallback after `--agent` and `[autofix] agent`), and
`authoring.resolve_authoring_agent`'s last term (the `coga ticket`
interviewer falls back to `Config.default_agent()`). Routing the new key through `default_agent()` itself is the
intent, so every consumer changes together with one edit — do not add a
parallel resolver.

**Why a machine-local value matters.** `config._parse_agents` merges shared
`[agents.*]` tables first, then local; a local-only type is appended last and a
local table cannot reorder shared ones. So today there is *no* machine-local way
to change the default at all.

**Every read of the default flips together.** Besides the consumers above,
`validate`, `commands/common`, `megalaunch`, `views`, `launch_script`, and
`commands/launch` call `resolve_main_agent(...,
allow_prospective_default=True)`, so status/show/compose/validate/launch
report the new default, and `resolve_other_agent` derives the peer from the main agent, so
the `other-agent` peer flips too. Cover these in tests and docs.

**Frozen period tickets keep their agent.** The Dream template
(`coga/recurring/dream/ticket.md`) sets no `agent:`; `recurring` materializes
the period task via `create_task(status="active")`, so its `agent:` comes from
`default_agent()`. But an already-materialized period ticket has `agent:`
frozen, and a forced rerun / `coga dream` in the same period reactivates it
(`recurring_runner` → `mark_active`) keeping the old agent. The key takes effect
from the next newly materialized period — pin that with a test.

**Config parsing.** Top-level tables are allow-listed in
`config._ALLOWED_SHARED_SECTIONS` and `config._ALLOWED_LOCAL_SECTIONS`; unknown
sections/keys fail via `_reject_unknown_sections` / `_reject_unknown_keys`.
The new table goes in **both** allow-lists. Model the parser on
`config._parse_autofix` (`[autofix] agent`), which already validates a named
agent type against the effective `[agents]` table at config load so a typo
fails loud there, not mid-sweep. Precedence: local value, then shared value,
then first-declared `[agents.*]`. A value naming an agent not in the effective
merged `[agents]` table must raise `ConfigError`. Design must decide: a
*shared* value naming a type defined only in some operator's local file would
fail on other clones — acceptable, or reject/warn? Note `[autofix]` is
shared-only, so a local-capable default key is a deliberate asymmetry.

**The flag already exists.** `coga recurring --agent <type>` (sweep-wide) and
`coga recurring launch <name> --agent <type>` are implemented in
`commands/recurring.py` and threaded as `agent_override` through
`recurring_runner`. `coga dream` is an alias for `coga recurring launch dream`.
The human's ask is specifically the `coga recurring --agent` sweep form. No new
flag is expected. `tests/test_recurring.py::test_bare_recurring_passes_agent_override_to_agent_tasks`
already runs `coga recurring --agent codex` on the `dream_repo` fixture and
asserts the override reaches the launch — extend it only if it does not
assert the launched agent is `codex`; do not duplicate it.

**`coga init` reorders tables today.** `commands/init._offer_agent_cli` /
`_make_default_agent` make a detected agent CLI the default by moving its
`[agents.*]` table first in the new `coga.toml`. Design must decide whether
init writes the new key instead (simpler, and the reason the key exists) or
keeps reordering; `coga/init` documents the current behaviour.

**Precedence with other agent knobs, for docs.** `--agent` > `[autofix] agent`
> new default key > first-declared, for the autofix analyst. For a recurring
agent-backed launch: `--agent` > the period ticket's `agent:` (stamped from
`default_agent()` at activation). Frozen `agent:` on already-activated tickets
is not rewritten by changing the default — same rule as reordering today.

**Contexts/docs to update (read and edit, not attached).** Each has a packaged
twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`
(byte-identity enforced by `tests/test_packaging.py`):
- `docs/contexts/coga/agents/SKILL.md` — owns the default ("The first declared
  type is the default … so a team lists its default first"). Primary owner of
  the new key's description.
- `docs/contexts/coga/configuration/SKILL.md` — owns the top-level key set and
  the "Unknown keys fail loud" rule; add the key and its local/shared
  precedence.
- `docs/contexts/coga/tickets/SKILL.md` — the `agent` field paragraph
  ("first agent in merged config") and the authoring-agent precedence list.
- `docs/contexts/coga/recurring/autofix/SKILL.md` — the "Which agent type
  analyzes" precedence bullet.
- `docs/contexts/coga/init/SKILL.md` — the paragraph on init reordering the
  chosen agent's table first.
- `src/coga/resources/templates/coga/coga.toml` (the `coga init` template) —
  add a commented example.
- Docstrings/comments saying "first-declared": `Config.default_agent`,
  `config.py` near the `[autofix]` parser, `create.py`, `recurring_autofix.py`,
  `authoring.py`, `commands/init.py`.
Grep `first-declared`, `first declared`, `first agent` across `docs/`, `src/`,
and `coga/` before finishing.

**Related, not in scope.** The landed `add-an-agent-picker-for-recurring` work
added a machine-local `[authoring] agent` key and `COGA_AUTHORING_AGENT` for
the `coga ticket` interviewer; its last fallback is `Config.default_agent()`,
so the new key also changes the default interviewer when nothing more specific
is set. Keep `[authoring] agent` independent and document the relationship in
`coga/agents`.
Making Dream's skills actually work under `codex` (they assume Claude's Agent
tool for subagents) is a separate ticket — out of scope here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
