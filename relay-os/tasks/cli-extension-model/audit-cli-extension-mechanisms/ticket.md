---
title: Audit CLI extension mechanisms
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/codebase
- relay/architecture
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
---

## Description

**The foundational ticket in `cli-extension-model/`. Run this first — the other
tickets in the line consume its output.**

Audit Relay's three CLI extension mechanisms and classify every command so
it's clear which ones could be cheap aliases and which must stay built-ins:

- **pure aliases** — argv rewrites in `_DEFAULT_ALIASES` / `[aliases]`
  (`src/relay/cli.py`)
- **built-in commands** — `src/relay/commands/*.py` registered in `cli.py`
- **launch shims / recurring launches** — `relay-os/bootstrap/<name>/` and
  `relay-os/recurring/<name>/`

For every current CLI verb, bootstrap shim, and recurring launch, classify it
as *alias-able* (a pure passthrough) or *needs-a-built-in* (requires pre/post
logic), with the reason. State the rule plainly: an alias is a pure argv
rewrite with **no after-hook**, so anything that drafts-on-the-fly, validates
after the agent exits, git-syncs, or guards a TTY cannot be an alias.

Deliverable: a committed markdown audit doc (pick a sensible home — a
`relay/cli`-style context under `relay-os/contexts/`, or `docs/`; decide and
say why in the doc). The doc must include:

1. The classification table (verb → mechanism → alias-able? → why).
2. The expected concrete finding — that the only un-aliased *pure passthroughs*
   are `skill-update` and `autoclose-merged` (recurring launches) — **verified,
   not assumed**. If the audit surfaces a third candidate or disqualifies one,
   record that; tickets 2 and 3 depend on this being right.
3. The gotchas: `bootstrap/import` and `bootstrap/delete-task` are *skills*,
   not launch shims, so they can't be aliases; and the `autoclose` (sweep
   merged PRs) vs `automerge` (mark a merged task done) naming proximity.

Done = the audit doc is committed and its classification + the
pure-passthrough finding are verified against the actual code.

## Context

Reconnaissance already done during ticket authoring (verify, don't trust):

- **Alias mechanism** — `src/relay/cli.py`: `_DEFAULT_ALIASES` (shipped to every
  repo) merged with user `[aliases]` from `relay.toml` (user key wins). An alias
  is a pure argv rewrite (`expansion + rest`) done in `main()` *before* Typer
  dispatches (lines ~242–251) — there is no post-dispatch hook. `_validate_aliases`
  (lines ~132–165) rejects aliases that collide with `_BUILTIN_COMMANDS` or expand
  to unknown targets, and soft-drops the legacy `create = "launch bootstrap/ticket"`.
  Current defaults: `chat` → `launch bootstrap/orient`, `dream` →
  `recurring launch dream`.
- **`relay ticket` is the proof the rule matters** — `src/relay/commands/ticket.py`
  (~320 lines) was promoted *from* the `create` alias to a built-in because it
  drafts-on-the-fly, validates the authored ticket after the agent exits,
  git-syncs changed `tasks/contexts/skills`, and enforces a TTY. None of that is
  expressible as an argv rewrite.
- **Launch shims** are tickets at `relay-os/bootstrap/<name>/ticket.md`
  (`resolve_bootstrap`). Only `orient`, `project`, `ticket` exist — `orient` is
  `chat`, `project` is a built-in, `ticket` is a built-in. No new bootstrap-shim
  aliases available.
- **Recurring launches** run via `recurring launch <name>` from
  `relay-os/recurring/<name>/`. Real ones: `autoclose-merged`, `digest`, `dream`,
  `skill-update`. `digest` is a built-in, `dream` is aliased → leaving
  `skill-update` and `autoclose-merged`.
- **Tests/sync** — alias coverage lives in `tests/test_aliases.py` (a
  `_DEFAULT_ALIASES` round-trip test ~line 209), NOT `relay validate`. If the doc
  lands as a shipped relay context, keep the live `relay-os/` and packaged
  `src/relay/resources/templates/relay-os/` copies in sync (CLAUDE.md).

**Out of scope:** shipping the aliases (that's ticket 2,
`add-recurring-launch-aliases`) and building the declarative-shim mechanism
(that's the follow-up the ticket 3 proposal sets up). This ticket only audits
and documents.
