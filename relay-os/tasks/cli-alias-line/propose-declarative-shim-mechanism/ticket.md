---
title: Propose declarative shim mechanism
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/architecture
  - relay/codebase
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

**Ticket 3 of 3 in `cli-alias-line/`. Depends on
`audit-cli-extension-mechanisms` — its conclusion is this proposal's evidence.**

The audit's expected conclusion is that *most* CLI verbs can't be aliases,
because an alias is a pure argv rewrite with no pre/post hook. That sets up the
real question: **how do we make logic-bearing commands declarative anyway,
instead of hand-writing a bespoke command module each time?**

Write a design proposal for a **declarative shim mechanism**: a config-driven
shim that can express the pre/post logic a command like `relay ticket` needs —
draft-if-missing, post-run validation, git-sync of changed
`tasks/contexts/skills`, TTY guard — as data rather than a ~320-line
`commands/*.py`. Sketch shape, e.g.:

```toml
[shims.ticket]
launch = "bootstrap/ticket"
draft_if_missing = true
validate_after = true
sync = ["tasks", "contexts", "skills"]
require_tty = true
```

This is where "make `relay ticket` more powerful" actually lives: you can't make
`ticket` both more powerful *and* a plain alias, but you can make the *shim
mechanism* powerful enough to subsume it.

The proposal should cover: motivation (the audit finding), the declarative
schema, how dispatch would change in `cli.py` (`main()` rewrites argv pre-Typer
today — a shim needs a real around-hook), which existing commands could migrate
onto it (`ticket`, possibly `project`/`delete`), what stays bespoke, migration
path, and risks (config-schema surface, validation parity with the current
hand-written `ticket.py`).

Done = a committed markdown design proposal (home it sensibly — `docs/` or a
relay context; say which and why). **The proposal is the deliverable.** Building
the shim runner is a separate follow-up ticket, created only if you greenlight
this proposal.

## Context

- The exemplar to subsume: `src/relay/commands/ticket.py` (~320 lines). Read it
  to enumerate exactly the pre/post behaviors a declarative shim must express
  (`create_draft` on missing target, post-run `validate_task_dir` +
  workflow-presence gate, snapshot/diff/git-sync of `tasks/contexts/skills`,
  TTY check, caution banners).
- Why a plain alias can't do it: `src/relay/cli.py` `main()` rewrites `sys.argv`
  *before* Typer dispatches (~242–251) — there is no after-hook. A shim
  mechanism has to add one.
- History worth citing: `relay ticket` was the `create = "launch
  bootstrap/ticket"` alias before it was promoted to a built-in (the legacy line
  is now soft-dropped by `_validate_aliases`). The proposal is, in effect, "how
  to get alias-like ergonomics back without losing the logic that forced the
  promotion."

**Out of scope:** implementing the runner, migrating any command, or touching
`relay ticket`. Those are follow-ups gated on this proposal being accepted.
