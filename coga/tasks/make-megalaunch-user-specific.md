---
slug: make-megalaunch-user-specific
title: make megalaunch user specific
status: draft
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

> Note: this review was run against the owner-filter-only version of the
> ticket. It flagged the silent-no-op risk from the derived `current_user`
> fallback; that flag is what drove the decision to *also* make `current_user`
> config-or-crash globally (part 1 of the current Description). The review
> below predates that expansion but remains accurate on the filter itself.

## Evaluation: `make-megalaunch-user-specific`

**Verdict: launchable. Description and code-pointers are accurate; a few assumptions should be surfaced before the reviewer commits to `owner`.**

### 1. Description clarity — Yes
A picked-up agent could start cold. The problem (shared-repo sweep spends budget on others' tickets), the fix (`ticket.owner == cfg.current_user` filter, `continue` to keep them out of `results`), and the "done" condition are all concrete. Code pointers verified: `run_megalaunch` loop starts at megalaunch.py:94, `read_ticket` at :98, the mirror-me status skip at :106. `Ticket.owner` exists (ticket.py:144, returns `frontmatter.get("owner")`). `cfg.current_user` field is config.py:100, populated config.py:329 (`local.get("user") or _default_user()`). All claims check out.

One imprecision: the ticket says place the filter "near line 94" (top of the for loop), but `ticket.owner` requires the `read_ticket` at :98 to have run — the earliest valid spot is after :101, i.e. right beside the :106 status skip. The "mirror line 106" guidance lands the implementer in the right place regardless, so this is cosmetic.

### 2. Workflow (`code/with-review`) — Good fit
Small, localized engine change plus tests, but carrying two real judgment calls (None-owner handling; the optional `--user`/`--all-users` escape hatch). Those deserve a reviewer, so `with-review` over plain `code` is the right call.

### 3. Contexts — Inline is the right call
The facts are localized to one function and two config lines; the inline `## Context` is thorough and correct. No dedicated context is warranted. (If anything, the reviewer should glance at `codebase/SKILL.md` for the `tests/test_megalaunch.py` expectations, but attaching it isn't necessary.)

### 4. Scope — Reasonable, single ticket
Engine filter + tests is one unit of work. The escape-hatch flag is correctly deferred as optional. Not bundled.

### 5. Assumptions to question before launch

- **`owner` vs `human` vs `assignee` — `owner` is correct, and self-consistent.** `assignee` names the *agent* (claude) and drives the existing agent-gate/budget logic — filtering on it would be a category error, and the ticket rightly warns against conflating them. Between `owner` (accountable, ticket.py:144) and `human` (the human *worker*, ticket.py:149), `owner` is the stronger choice because **create-time sets `owner = cfg.current_user`** (create.py:67, commands/create.py:94). So the field being filtered and the value filtering it come from the *same source*, making the match self-consistent by construction. `human` is the only other defensible option but has no such guarantee.

- **The load-bearing risk is `current_user` resolution, not the field choice.** Both entry points (`commands/megalaunch.py:23` and the recurring script `coga/skills/coga/megalaunch/run/run.py`) call a fresh `load_config()`, so in the recurring `auto` context `cfg.current_user` correctly resolves to the machine operator — the intent holds. **But** if a machine has no `coga.local.toml` `user`, config falls back to `_default_user()` = `git config user.name` (config.py:224–255). If that derived string (e.g. `"Nick Toper"`) doesn't exactly equal the `owner` token written into tickets (e.g. `"nicktoper"`), the filter silently drops **every** ticket and megalaunch launches nothing — a silent no-op, the worst failure mode for an unattended sweep. The match is exact-string/case-sensitive. Reviewer should decide: require `user` in `coga.local.toml`, or at minimum document that owner tokens and `current_user` must agree.

- **None-owner handling is unspecified.** `ticket.owner` returns `None` when the field is absent. `ticket.owner == cfg.current_user` will exclude owner-less tickets entirely. Probably fine, but it's an undecided edge the implementer will hit — worth an explicit line in the ticket.

- **Budget accounting stays global (scope note, not a blocker).** The motivation cites "spends budget on other people's tickets." This fix stops *launching* others' tickets, but `budget_state` (megalaunch.py:353) is keyed on the shared agent name (`claude`) across all repo usage records — person B's sweep still counts person A's `claude` spend against the same budget. That's arguably out of scope, but since the ticket frames the problem partly as budget, one sentence clarifying that per-user budget isolation is *not* part of this change would prevent a scope-creep argument in review.
