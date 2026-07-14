---
slug: make-megalaunch-user-specific
title: make megalaunch user specific
status: in_progress
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
step: 4 (review)
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

- Retire `_default_user()` (`src/coga/config.py:224`) **entirely** — deriving a
  name silently is the antipattern we're killing: it hides a real config
  problem (no `user` set) behind a plausible-looking guess. Delete the whole
  function, not just its `load_config` call site.
- `current_user = local.get("user") or _default_user()` (`config.py:329`) is
  the line to change: raise `ConfigError` when `local.get("user")` is
  missing/empty instead of deriving. `current_user` is a `Config` field
  (`config.py:100`). Give the error a clear remedy: run `coga init --user
  <name>`, or add `user = "<name>"` to `coga.local.toml`.
- Rewrite the now-false prose that documents the old "never fatal" contract:
  the `_default_user` docstring goes with the function, and the 4-line comment
  above the call site (`config.py:324–328`) — "A missing `user` is no longer
  fatal: derive one…" — must be replaced with the new fail-loud rationale so
  the code stops describing the opposite of what it does.
- `coga init` must stop deriving too — it's the other half of the same
  antipattern. `_require_user_name(None)` (`src/coga/commands/init.py:72`)
  currently derives from git/OS and warns; change it to fail loudly telling the
  operator to pass `--user NAME`. Remove the `_default_user` import
  (`init.py:34`) and its use at `init.py:85`. Net effect: `coga init --user
  marc` is the one blessed way to set the name, and it still works on a bare
  clone — init writes `user` before anything reads config, so there's no
  chicken-and-egg and the operator is never walled out of the remedy.
- Expect fallout: anything that constructs a `Config` without a `user`
  (tests, fixtures, `example/coga/`, docs) may now need an explicit `user`.
  `example/coga/coga.local.toml` already sets `user = "marc"`, so the smoke
  fixture is fine; temp-dir configs built in tests are the real risk. Grep for
  `load_config`/`current_user` usage and fix fixtures; a helper for tests to
  build a `Config` with a user may be warranted.
- Rollout note for the PR: this is a breaking change for *existing* operators,
  not just bare clones — anyone currently running with no `user` in
  `coga.local.toml` (relying on the git-name derive) starts hard-failing on
  every command until they run `coga init --user <name>` or add the line.

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
  config). Add/adjust tests: config tests for the missing-`user` crash;
  `coga init` tests that a bare `coga init` (no `--user`) now fails loudly and
  that `coga init --user NAME` still succeeds on a bare clone (the escape
  hatch — verify you can actually run coga after it); and
  `tests/test_megalaunch*.py` for the owner filter.

<!-- coga:blackboard -->
## Dev

branch: megalaunch-user-specific
worktree: /home/n/Code/claude/coga-megalaunch-user-specific
pr: https://github.com/FastJVM/coga/pull/523

### Done (open-pr step)

- Pre-push probe: `gh` auth good (nicktoper, https, remote `FastJVM/coga`).
  Branch was 2 commits behind `origin/main` (coga-state files only — `log.md`,
  `digest/spool.md`, task `.md`s — zero source overlap). With the owner's OK,
  merged `origin/main` in (conflict-free), which made the branch current
  (0 behind); source diff vs main intact.
- Pushed `megalaunch-user-specific`; opened PR #523
  (https://github.com/FastJVM/coga/pull/523), base `main`, links the ticket.
- CI: repo has no checks configured for this branch (`gh pr checks 523` →
  "no checks reported"), so there is no CI signal to be green on.

## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.

### Plan (implement step)

Part 1 — config fail-loud:
- Delete `_default_user()` in `src/coga/config.py`; raise `ConfigError` in
  `load_config` when `local.get("user")` is missing/empty (remedy: `coga init
  --user <name>` or add `user = "<name>"` to `coga.local.toml`).
- Rewrite the 4-line "no longer fatal" comment above the call site.
- `coga init`: `_require_user_name(None)` fails loud (`sys.exit(2)`) telling
  operator to pass `--user NAME`; drop the `_default_user` import + use.

Part 2 — megalaunch owner filter:
- In `run_megalaunch`, after `read_ticket`, `continue` when
  `ticket.owner != cfg.current_user` (mirror the status skip; no new outcome).

Tests: config missing-user crash; init bare fails loud + `--user` still works;
megalaunch owner filter excludes other owners without inflating counts.
Fixtures: grep temp-dir configs building coga.local.toml without `user`.

### Done (implement step)

Commit `6adc3004` on branch `megalaunch-user-specific`.

- `src/coga/config.py`: deleted `_default_user()`; `load_config` now raises
  `ConfigError` (with the `coga init --user <name>` / add-`user`-line remedy,
  quoting the exact `coga.local.toml` path) when `user` is missing/empty.
  Rewrote the stale "no longer fatal" comment.
- `src/coga/commands/init.py`: `_require_user_name(None)` now `sys.exit(2)` with
  a "pass `--user NAME`" message; dropped the `_default_user` import + use.
- `src/coga/megalaunch.py`: `run_megalaunch` `continue`s when
  `ticket.owner != cfg.current_user`, right after `read_ticket` (mirrors the
  status skip; no new outcome, so other owners don't inflate counts).
- Tests: rewrote `test_missing_local_toml_fails_loud`,
  `test_missing_user_fails_loud`, `test_init_without_user_fails_loud`; removed
  the obsolete `_default_user` derive tests; added
  `test_megalaunch_only_sweeps_current_users_tickets`.

Verification:
- `python3.12 -m pytest` — 1071 passed, 1 skipped. The single failure
  (`test_bootstrap_script_launch_is_stateless`) is **pre-existing and
  environment-only**: a subprocess-launched `run.py` can't `import coga` under
  this interpreter (coga not pip-installed here). Confirmed it fails identically
  on the unmodified base commit, so it is not from this change.
- End-to-end: `load_config` fails loud on empty `user` and loads with a real
  one; `coga init` (no `--user`) exits 2 and writes nothing.

Notes for later steps / PR:
- Breaking change for existing operators with no `user` in `coga.local.toml`
  (relying on the git-name derive): every command hard-fails until they run
  `coga init --user <name>` or add the line.
- Out of scope: budget still keyed on the shared agent name (e.g. `claude`) —
  this stops *launching* others' tickets but does not isolate per-user token
  budgets. Owner-less tickets (`owner` absent → `None`) are excluded by the
  filter; acceptable per the ticket.
- No packaged-template/example sync needed: changes are package source only;
  `example/coga/coga.local.toml` already sets `user = "marc"`.

### Done (peer-review step)

Native review:
- First `codex review --base main` failed before findings with the known
  sandbox app-server error (`Read-only file system (os error 30)`); reran the
  same command outside the sandbox and got two must-fix P2 findings.

Applied in commit `898d93b7` (`peer-review: apply review findings`):
- Fixed missing-user `ConfigError` recovery text: existing repos are now told
  to add `user = "<name>"` to the actual `coga.local.toml` path; `coga init
  --user <name>` is only described as the fresh-repo path.
- Updated the shipped megalaunch contract to state the silent current-user
  owner filter, including the packaged CLI context and both live/packaged
  `recurring/megalaunch` ticket text.

Verification:
- `python -m pytest tests/test_config.py tests/test_init.py tests/test_megalaunch.py -q`
  — 164 passed.
- `git diff --check` — clean.
- `python -m pytest` — 1071 passed, 1 skipped, 1 failed. The failure is the
  same environment-only `test_bootstrap_script_launch_is_stateless` failure
  from the implement handoff: subprocess `run.py` cannot `import coga` in this
  checkout.

## Usage

{"agent":"claude","cache_creation_input_tokens":257704,"cache_read_input_tokens":6992414,"cli":"claude","input_tokens":23293,"model":"claude-opus-4-8","output_tokens":44450,"provider":"anthropic","schema":1,"session_id":"ceafd926-edbf-4f4e-8eb9-b1df42b1f7f6","slug":"make-megalaunch-user-specific","step":"implement","title":"make megalaunch user specific","ts":"2026-07-05T20:36:48.523682Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2843008,"cli":"codex","input_tokens":299830,"model":"gpt-5.5","output_tokens":14534,"provider":"openai","schema":1,"session_id":"019f33ff-7f2b-77a1-bf1a-e5e91b89355c","slug":"make-megalaunch-user-specific","step":"peer-review","title":"make megalaunch user specific","ts":"2026-07-05T21:47:07.169328Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":121995,"cache_read_input_tokens":1754170,"cli":"claude","input_tokens":19164,"model":"claude-opus-4-8","output_tokens":34632,"provider":"anthropic","schema":1,"session_id":"ce88194f-71e9-41d0-a4ab-bb7b0625943f","slug":"make-megalaunch-user-specific","step":"open-pr","title":"make megalaunch user specific","ts":"2026-07-05T21:52:45.613075Z","usage_status":"ok"}
