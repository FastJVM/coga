---
slug: make-megalaunch-user-specific
title: make megalaunch user specific
status: active
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
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
secrets: null
script: null
step: 1 (implement)
---

## Description

Two linked changes so `coga megalaunch` only drives the running user's own
work:

1. **Make the current user come from config or crash (global).** Today
   `cfg.current_user` silently derives a name from `git config user.name` (then
   the OS username) when `coga.local.toml` sets no `user`. That derived guess
   is treated as a bug: it can disagree with the `owner` tokens written into
   tickets, and for an unattended sweep a wrong `me` fails silently. Change
   `load_config` so a missing/empty `user` in `coga.local.toml` is a hard
   `ConfigError` — the user is always read from config, never guessed. This is
   a deliberate reversal of the current "never wall anyone out" fallback and
   applies to *every* command (a bare clone with no `coga.local.toml` will now
   error until `coga init --user <name>` is run).

2. **Scope the megalaunch sweep to that user.** `run_megalaunch` currently
   attempts *every* active, agent-owned ticket regardless of owner; on a shared
   repo one person's daily sweep launches (and spends budget on) other people's
   tickets. Filter the sweep to tickets whose `owner` matches
   `cfg.current_user` and skip the rest.

Done looks like: `coga` commands fail loudly with a clear message when
`coga.local.toml` has no `user`; and a megalaunch run only attempts tickets
whose `owner == cfg.current_user`, with other owners filtered out (not
launched, not counted as skip-noise). The recurring `coga/megalaunch/run`
task then only drives the machine operator's own work.

## Context

Key code — config change (part 1):

- `_default_user()` (`src/coga/config.py:224`) is the fallback to retire. Its
  docstring deliberately never crashes so `--help`/read-only work on a bare
  clone; that guarantee is being dropped on purpose.
- `current_user = local.get("user") or _default_user()` (`config.py:329`) is
  the line to change: raise `ConfigError` when `local.get("user")` is
  missing/empty instead of deriving. `current_user` is a `Config` field
  (`config.py:100`). Give the error a clear remedy (run `coga init --user
  <name>`, or add `user = "<name>"` to `coga.local.toml`).
- `coga init --user <name>` already writes `user` into `coga.local.toml`, so
  the durable path exists — this just makes it mandatory.
- Expect fallout: anything that constructs a `Config` without a `user`
  (tests, fixtures, `example/coga/`, docs) may now need an explicit `user`.
  Grep for `load_config`/`current_user` usage and fix fixtures; a helper for
  tests to build a `Config` with a user may be warranted.

Key code — megalaunch filter (part 2):

- `src/coga/megalaunch.py` — `run_megalaunch()` iterates `list_tasks(cfg)`
  (loop at line 94) and decides launch vs skip per ticket. Add the owner
  filter right after `read_ticket` (line 98), beside the existing non-active
  status skip at line 106 — a `continue` when `ticket.owner != cfg.current_user`
  keeps other owners out of `results` so they don't inflate summary counts.
  Mirror that skip pattern rather than emitting a new skip outcome, unless
  review prefers an explicit reason.
- Match on the `owner` frontmatter field (`Ticket.owner`), the canonical
  responsible-person field — and the same source `coga create` writes from
  `cfg.current_user`, so the filter is self-consistent by construction. The
  existing `assignee` checks are a separate concern (agent-vs-human gating);
  don't conflate them with the owner filter.
- Owner-less tickets: `ticket.owner` is `None` when absent, so the filter
  excludes them. That's acceptable (part 1 guarantees a real `current_user`);
  confirm in review.

Design points / notes:

- No `--user`/`--all-users` escape hatch for now — strictly current-user.
  Add one later only if a reviewer wants cross-user sweeps.
- Out of scope: budget stays keyed on the shared agent name (e.g. `claude`),
  so this stops *launching* others' tickets but does not isolate per-user
  token budgets. Call that out in the PR.
- Keep the packaged template copy in sync per CLAUDE.md if any shipped
  template/example changes (e.g. adding `user` to `example/coga/`'s local
  config). Add/adjust tests: config tests for the missing-`user` crash, and
  `tests/test_megalaunch*.py` for the owner filter.

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
