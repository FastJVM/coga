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

Scope `coga megalaunch` to the current user's own tickets. Today
`run_megalaunch` sweeps *every* active, agent-owned ticket in the repo
regardless of who owns it; on a shared repo that means one person's daily
sweep launches (and spends budget on) tickets owned by other people. Change
the sweep so it only considers tickets owned by the user running it —
`cfg.current_user` — and skips the rest.

Done looks like: a megalaunch run only attempts tickets whose `owner` matches
`cfg.current_user`; tickets owned by anyone else are filtered out (not
launched, and ideally not counted as skip-noise in the run summary). The
recurring `coga/megalaunch/run` task, which runs `auto` on each person's
machine, then naturally only drives that person's work.

## Context

Key code:

- `src/coga/megalaunch.py` — `run_megalaunch()` iterates `list_tasks(cfg)`
  and, for each ticket, decides launch vs skip. The user filter belongs here,
  before the `status`/budget/candidate logic (around the top of the
  `for ref in list_tasks(cfg)` loop, near line 94). Filtering *out* other
  users' tickets entirely (a `continue`, like the existing non-active status
  skip at line 106) keeps them out of `results` so they don't inflate the run
  summary counts — mirror that pattern rather than emitting a new skip
  outcome, unless review prefers an explicit skip reason.
- `cfg.current_user` (`src/coga/config.py:100`, populated at line 329 from
  `coga.local.toml` `user` or a derived default) is the running user.
- Ticket owner lives in the `owner` frontmatter field (`Ticket.owner`). In
  this repo `owner`, `human`, and `assignee` are all `nicktoper`; match on
  `owner` (the canonical responsible-person field). Note the existing
  `assignee` checks are a *separate* concern (agent-vs-human gating) — don't
  conflate the new owner filter with them.

Design points to settle in implement/review:

- Whether to add an escape hatch (e.g. `--user <name>` / `--all-users` on the
  `coga megalaunch` command) for cross-user sweeps, or keep it strictly
  current-user-only for now. Recommend shipping the simple current-user
  default first; add a flag only if the reviewer wants it.
- Backward-compat: existing behavior launched all owners. This narrows it.
  That's the intent, but call it out in the PR.

Keep the packaged template copy in sync per CLAUDE.md if any shipped
template/context changes (the engine change in `src/coga/` is the core; the
recurring `coga/recurring/megalaunch/ticket.md` and its packaged copy likely
need no change). Add/adjust tests under `tests/test_megalaunch*.py` to cover
the owner filter.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
