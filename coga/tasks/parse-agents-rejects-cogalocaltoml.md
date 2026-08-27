---
slug: parse-agents-rejects-cogalocaltoml
title: parse-agents-rejects-cogalocaltoml
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

`_parse_agents` hard-rejects any `[agents.<name>]` table in `coga.local.toml`
with "coga.local.toml no longer supports [agents.<name>] overrides". Zach hit
this testing a local-llm agent: there is no way to add an agent type without
committing it to `coga.toml`.

Make `[agents.*]` load the way the rest of the config already layers: read
`coga.toml`, then overlay `coga.local.toml` on top, last writer wins. A local
table for a name absent from `coga.toml` **adds** that agent; a local table for
a name present in `coga.toml` **overrides** the keys it names. Machine-local
agent types stop needing a commit.

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
- `tests/test_launch.py:1755` — `test_launch_rejects_local_agent_override`
  asserts the current rejection. It inverts: the same fixture
  (`[agents.claude] cli = "claude-nightly"` in `coga.local.toml`) must now
  launch with the overridden cli.

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
through the same required-key check, `_REMOVED_AGENT_KEYS` check,
`_reject_unknown_keys(_ALLOWED_AGENT_KEYS)`, and string-type checks the shared
path already runs.

Two error-message details to preserve:

- The removed-key migration error (`auto`, `skip_permissions`,
  `skip_permissions_argv`) must still name the file the key actually came from,
  so a stale key in `coga.local.toml` does not report as a `coga.toml` problem.
  The architecture context calls this carve-out out by name.
- Required keys (`cli`, `file`) are checked against the merged table, so a
  local-only agent must supply both and a partial override need not.

### Precedent

This is the same layering `[notification.slack].webhook` /
`.important_webhook` already use — local wins, no warning
(`coga/contexts/coga/sync/SKILL.md:346`). Decided: **no** provenance
affordance. Do not add a `coga validate` report or a launch-time notice about
locally-defined agents; keep this a parser change.

`[layout]` is the counterexample and stays rejected in `coga.local.toml` — where
a repo keeps its prose is a fact about the repo. Agent types are a fact about
the machine (which CLI binaries are installed), so they layer.

### Accepted tradeoff

A committed ticket's `agent: <name>` can now resolve to a different binary per
machine, and a local-only agent name only works on the machine that declares
it. That is the point of the change; do not litigate it in review.

### Out of scope

- `bump.py:44` requires exactly two agent types for `assignee: other-agent`, so
  a third declared agent breaks any workflow using that token. That is the
  sibling ticket `bumppy-requires-exactly-two-agents` — leave it alone here,
  but do not add a *new* two-agent assumption in this change.
- Do not touch this repo's own `coga.toml` / `coga.local.toml` (base prompt
  prohibition). The `example/` fixture below is a different file and is fair
  game.

### Docs and fixtures to update in the same PR

Per `CLAUDE.md`: a behavior change updates its matching context in the same PR,
and shipped contexts exist in two places that must stay in sync.

1. `coga/contexts/coga/architecture/SKILL.md:305-330` — the "Config loading
   fails loud on unknown keys" section lists `[agents.<name>]` under the
   known-but-rejected carve-out. Rewrite so it describes the layered load, and
   keep the removed-key migration error in the carve-out list.
2. `src/coga/resources/templates/coga/` — mirror any context/template edit into
   the packaged copy so a freshly-initialized repo ships the same docs. Check
   for a packaged `coga.toml` comment about local agent tables too.
3. `example/coga/` — add a local-only agent type to the seeded fixture so the
   smoke path exercises an addition, not just an override.

### Verification

`python -m pytest` and `coga validate --json`. Cover in tests: local-only
addition; partial override of a shared agent (inherits the unspecified keys);
removed key in `coga.local.toml` still raising the migration error naming that
file; unknown key in a local agent table still rejected.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
