---
title: dream should be able to use codex instead of claude
status: draft
owner: nicktoper
agent: claude
contexts:
  - dev/code
workflow: code/design-then-implement
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
proposed spelling is `[defaults] agent = "<type>"`; the design step may pick a
better name but must justify it.

Done when: setting the key to `codex` (in either file) makes
`Config.default_agent()` — and therefore ticket activation, `coga create` into
a live status, `coga retire`'s default, the autofix fallback, and a
`coga recurring` sweep's Dream period task — resolve `codex` without any
`[agents.*]` reorder; a local value overrides the shared one; an unset key keeps
today's first-declared behaviour byte-for-byte; `coga recurring --agent codex`
is verified (by test) to launch the Dream period task as `codex`; the contexts
and docs that describe the default are updated; `python -m pytest` passes and
`coga validate --json` is clean.

## Context

**Current mechanism.** `config.Config.default_agent` returns the first entry of
`cfg.agents` (TOML declaration order over the merged shared+local tables). Its
consumers: `bump` (activation stamps `agent:` from it), `create._select_main_agent`
(via `resolve_main_agent(..., allow_prospective_default=True)` for a live
create), `commands/retire._default_agent`, and
`recurring_autofix._analyze_agent` (the fallback after `--agent` and
`[autofix] agent`). Routing the new key through `default_agent()` itself is the
intent, so every consumer changes together with one edit — do not add a
parallel resolver.

**Config parsing.** Top-level tables are allow-listed in
`config._ALLOWED_SHARED_SECTIONS` and `config._ALLOWED_LOCAL_SECTIONS`; unknown
sections/keys fail via `_reject_unknown_sections` / `_reject_unknown_keys`.
The new table goes in **both** allow-lists. Model the parser on
`config._parse_autofix` (`[autofix] agent`), which already validates a named
agent type against the effective `[agents]` table at config load so a typo
fails loud there, not mid-sweep. Precedence: local value, then shared value,
then first-declared `[agents.*]`. A value naming an agent not in the effective
merged `[agents]` table must raise `ConfigError`.

**The flag already exists.** `coga recurring --agent <type>` (sweep-wide) and
`coga recurring launch <name> --agent <type>` are implemented in
`commands/recurring.py` and threaded as `agent_override` through
`recurring_runner`. `coga dream` is an alias for `coga recurring launch dream`.
The human's ask is specifically the `coga recurring --agent` sweep form. No new
flag is expected — verify and add test coverage if missing; if it turns out not
to reach Dream, fix it.

**Precedence with other agent knobs, for docs.** `--agent` > `[autofix] agent`
> new default key > first-declared, for the autofix analyst. For a recurring
agent-backed launch: `--agent` > the period ticket's `agent:` (stamped from
`default_agent()` at activation). Frozen `agent:` on already-activated tickets
is not rewritten by changing the default — same rule as reordering today.

**Contexts/docs to update (read and edit, not attached):**
`coga/contexts/coga/architecture/SKILL.md` — the paragraph stating `agent` is
filled from `Config.default_agent()` "the first agent declared in the effective
merged configuration", and the section listing fixed-schema tables that raise
on unknown keys. `coga/contexts/coga/recurring/SKILL.md` — the autofix
"Which agent type analyzes" precedence bullet. Also the packaged twins under
`src/coga/resources/templates/coga/` (byte-identity enforced by
`tests/test_packaging.py`), the `coga init` config templates if they document
agent tables, and `docs/` pages that describe the default. Grep for
"first-declared" / "first agent declared".

**Related, not in scope.** `add-an-agent-picker-for-recurring` (in progress,
despite its title) adds a machine-local `[authoring] agent` key and
`COGA_AUTHORING_AGENT` for the `coga ticket` interview only; its bottom
fallback is the bootstrap ticket's `assignee:`, not `default_agent()`. Keep the
two keys independent; mention the relationship in docs if both land.
Making Dream's skills actually work under `codex` (they assume Claude's Agent
tool for subagents) is a separate ticket — out of scope here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
