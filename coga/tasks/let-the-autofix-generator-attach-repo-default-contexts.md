---
title: Let the autofix generator attach repo-default contexts
status: draft
owner: nicktoper
contexts:
- coga/recurring
- coga/codebase
workflow: null
---

## Description

Every ticket the `coga recurring` autofix loop files is born with
`contexts: []`, and a repo has no way to change that. Add an optional
`[autofix] contexts = ["<ref>", ...]` key to the shared config and pass it to
`create_task` in place of the hardcoded empty list, so a repo can say which
contexts every generated `autofix/*` ticket should compose.

**Fix:** `recurring_autofix.create_autofix_ticket` calls `create_task(...,
contexts=[], ...)`. Widen `config._ALLOWED_AUTOFIX_KEYS` to include
`contexts`, parse it in `config._parse_autofix` next to `agent` (a list of
non-empty strings; absent means `[]`, so behaviour is unchanged for every repo
that does not set it), carry it on `Config` beside `autofix_agent`, and use it
in `create_autofix_ticket`. Validating each ref at config load, the way
`[autofix].agent` is checked against `[agents]`, is the same argument as that
key's docstring makes: a typo found only after an unattended sweep is reported
by nothing. Update the packaged `coga/cli` context's autofix-loop operator
knobs, and cover parse + generation in `tests/test_recurring_autofix.py` and
the config tests.

Alternative considered and not preferred: have the analyst choose contexts.
The analyst is text-in/text-out and Coga does every mutation; which contexts a
repo's triage needs is repo policy, not a per-finding judgment.

## Context

Reported from a downstream repo, `FastJVM/admin`, where the evidence lives.

- That repo keeps a local context, `coga/upstream`, whose purpose is routing a
  failure diagnosed there to a fix in this repo; its own description says to
  attach it to every `autofix/*` ticket, because "is this upstream?" is the
  first question each one asks.
- It has been attached by hand twice (2026-09-01, and again 2026-09-16 for the
  four then-live autofix tickets). In between, every generated ticket —
  `build-the-missing-1099-nec-sweep-script-so-its-fir`,
  `put-dream-scan-directories-somewhere-they-survive`,
  `launch-due-recurring-tasks-the-sweep-drops-after-c`,
  `resync-four-coga-files-that-fell-behind-the-2026-0` — was born contextless,
  and 10 of that repo's 12 autofix tickets at the time carried no context. A
  session launched on one never composes the triage guidance it most needs.
- A hand re-attach after each sweep is a standing chore the generator could do
  once from config.
- Verified against `origin/main` on 2026-09-16: `create_autofix_ticket` passes
  `contexts=[]`; `_ALLOWED_AUTOFIX_KEYS` is `{"agent"}`; no existing ticket in
  `coga/tasks/` covers default contexts for generated tickets.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
