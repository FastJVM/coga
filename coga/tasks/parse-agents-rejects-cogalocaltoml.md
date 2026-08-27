---
slug: parse-agents-rejects-cogalocaltoml
title: parse-agents-rejects-cogalocaltoml
status: canceled
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

`_parse_agents` hard-rejects any `[agents.<name>]` table in `coga.local.toml`
with "coga.local.toml no longer supports [agents.<name>] overrides". Zach hit
this testing a local-llm agent: there is no way to add an agent type without
committing it to `coga.toml`.

Make `[agents.*]` load the way the rest of the config already layers: read
`coga.toml`, then overlay `coga.local.toml` on top, last writer wins. A local
table for a name absent from `coga.toml` **adds** that agent; a local table for
a name present in `coga.toml` **overrides** the keys it names.

Scope note so the reporter is not surprised: this makes a third agent type
*loadable*, not yet *usable* end to end. `src/coga/bump.py:44` still requires
exactly two configured agents to resolve `assignee: other-agent`, which every
`code/with-review` ticket hits. That half is the sibling ticket below.

## Context

### Where the behavior lives

- `src/coga/config.py:526` — `_parse_agents(raw, local_raw)`. It validates the
  shared tables, then loops `local_raw` only to re-raise the removed-key
  migration error, and finally raises unconditionally on any non-empty
  `local_raw` (lines 583-587).
- `src/coga/config.py:305` — the single call site, already passing both tables.
- `src/coga/config.py:435` — `_ALLOWED_LOCAL_SECTIONS` already contains
  `agents`; it is allowlisted purely so the tailored rejection fires instead of
  a generic unknown-key error. It stays.

### Merge semantics

Overlay at the **key** level, not the table level. A local
`[agents.claude]` carrying only `cli` overrides `cli` and inherits `file`,
`mode`, `name_flag`, `session_id_flag`, `discussion`, `analyze` from
`coga.toml`. Table-level replacement would make that snippet fail
"agents.claude.file is required", which is not what an override means.

This should make `_parse_agents` **shorter**, not longer: merge the raw dicts
per agent name first, then run the existing validation once over each merged
table. That deletes the trailing rejection and the duplicated
`_REMOVED_AGENT_KEYS` loop over `local_raw`, since the merged table goes
through the same checks the shared path already runs.

Four details the naive merge gets wrong — each is a decided requirement, not an
open question:

1. **Preserve declaration order.** `Config.default_agent()`
   (`src/coga/config.py:175-184`) returns `next(iter(self.agents))` and
   `tests/test_config.py:293` guards it. Merge shared names first in their
   `coga.toml` order, then append local-only names; never rebuild the dict
   from `local_raw` first or re-sort.
2. **Run the removed-key check before the required-key check** on the merged
   table. Today the local removed-key loop (`config.py:571-582`) runs
   independently of `cli`/`file`, so a *local-only* agent carrying a stale
   `auto` still gets the migration error. Merge naively and it instead reports
   `agents.<name>.cli is required`. The existing fixture
   (`tests/test_config.py:274-283`) overrides a name that exists in shared, so
   it would still pass — this regression is invisible to the suite unless a
   test is added for it.
3. **Name the source file in the unknown-key error too.** `config.py:542`
   currently passes a bare `f"[agents.{name}]"` label. After merging, a typo in
   `coga.local.toml` would report with no file named. Track which file each
   rejected key came from and label it, matching the removed-key error's
   behavior.
4. **Keep a non-dict guard.** `config.py:572` currently does
   `if not isinstance(data, Mapping): continue`. Without it, `agents.foo = "bar"`
   makes `"cli" not in "bar"` a substring test that succeeds into a nonsense
   `agents.foo.cli is required`.

Required keys (`cli`, `file`) are checked against the merged table, so a
local-only agent must supply both and a partial override need not.

### Precedent

This is the same layering `[notification.slack].webhook` /
`.important_webhook` already use — local wins, no warning
(`coga/contexts/coga/sync/SKILL.md:344-348`). Decided: **no** provenance
affordance. Do not add a `coga validate` report or a launch-time notice about
locally-defined agents; keep this a parser change.

`[layout]` is the counterexample and stays rejected in `coga.local.toml` — where
a repo keeps its prose is a fact about the repo. Agent types are a fact about
the machine (which CLI binaries are installed), so they layer.

### Accepted tradeoff

A committed ticket's `agent: <name>` can now resolve to a different binary per
machine, and a local-only agent name only works on the machine that declares
it. That is the point of the change; do not litigate it in review.

### Tests that assert the current behavior

Two tests must invert, not one:

- `tests/test_launch.py:2316` — `test_launch_rejects_local_agent_override`.
  Same fixture (`[agents.claude] cli = "claude-nightly"` in `coga.local.toml`)
  must now launch with the overridden cli.
- `tests/test_config.py:273` — `test_local_agent_overrides_are_rejected`.
  Identical fixture, matches `"no longer supports"`.

`tests/test_config.py:240-270` is the regression guard for the removed-key
carve-out. Its regex `coga\.local\.toml has removed key\(s\)` is unanchored,
so whatever the rewritten message says must keep that substring contiguous.

New coverage to add: local-only addition; partial override inheriting the
unspecified keys; declaration order unchanged by a local-only addition;
local-only agent with a removed key still getting the migration error (detail 2
above); unknown key in a local agent table rejected *and naming the file*
(detail 3).

### Out of scope

- `src/coga/bump.py:44` (`if len(others) != 1:`) requires exactly two agent
  types for `assignee: other-agent`. That is the sibling ticket
  `bumppy-requires-exactly-two-agents` — leave it alone here, but do not add a
  *new* two-agent assumption in this change.
- Do not touch this repo's own `coga.toml` / `coga.local.toml` (base prompt
  prohibition). `example/coga/` is a different file and is fair game.

### Docs and fixtures to update in the same PR

Per `CLAUDE.md`: a behavior change updates its matching context in the same PR,
and shipped contexts exist in two places that must stay in sync.

1. `coga/contexts/coga/architecture/SKILL.md` — **add**, do not rewrite. The
   local-table rejection was never documented, so there is nothing to correct.
   The "Config loading fails loud on unknown keys" section (line 352 onward)
   stays accurate as-is: its `[agents.<name>]` mention is about *unknown keys*,
   and the removed-key carve-out still holds. The new sentence belongs beside
   the `[layout]` paragraph at **line 349-350**, which is already the passage
   explaining which tables are per-machine and which are repo policy — state
   there that `[agents.*]`, unlike `[layout]`, layers local-over-shared, and
   why.
2. `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`
   — the packaged mirror. Verified byte-identical to the repo copy today, same
   line numbers; apply the same edit. Checked and needing **no** change:
   `src/coga/resources/templates/coga/coga.toml:15-19` and
   `example/coga/coga.local.toml`'s trailing comment only warn about the
   removed headless keys, which stays true.
3. `example/coga/` — add a local-only agent type to the seeded fixture so the
   smoke path exercises an addition, not just an override.
   `example/coga/coga.local.toml` is tracked (`.gitignore` line 3 is
   root-anchored `/coga.local.toml`), so the edit lands in git. Safe today —
   nothing in `example/` uses `other-agent`, and
   `example/coga/workflows/code/with-review.md` is the example's own copy with
   no such step — but it makes `example/` a three-agent repo, which is exactly
   the shape `src/coga/bump.py:44` fails on. Leave a comment on the fixture line
   pointing at the sibling ticket so the tripwire is labeled.

Optional, nice-to-have: `coga/contexts/coga/codebase/SKILL.md:109` describes
`coga.local.toml` as "machine-local (NEVER committed; secrets here)" and could
gain "agent types".

### Verification

`python -m pytest` and `coga validate --json`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Merge note

Folded into `coga/tasks/bumppy-requires-exactly-two-agents.md` and canceled.
Both tickets came from the same local-llm report, and the `peer` key added
there has to survive the local/shared `[agents.*]` merge specified here, so
the owner merged them rather than sequence them. The full content above is
absorbed into that ticket's `## Context`; work it there, not here.
